# -*- coding: utf-8 -*-
"""Redo the 4-segment 40s video with the nightly+CK+TRT config.

Original payloads (_submit_payload_seg1..4.json) are used unchanged except
the video VAEDecode is swapped to the TRT engine loader. Segments chain by
extracting each output's last frame as the next segment's first-frame image.
If TRT decode fails for a shape, that segment auto-retries with standard VAE.

Usage: python_embeded_nightly\\python.exe scripts\\_redo40.py
Log:   logs\\redo40_results.txt
"""
import json, urllib.request, urllib.error, time, sys, os, datetime, subprocess

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
ROOT = r"C:\minimax+comfyUI"
SCRIPTS = os.path.join(ROOT, "scripts")
LOG = os.path.join(ROOT, "logs", "redo40_results.txt")

def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get(u, timeout=60):
    with urllib.request.urlopen(u, timeout=timeout) as r:
        return json.loads(r.read().decode())

def post(obj, timeout=120):
    req = urllib.request.Request(HOST + "/prompt", data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        log("HTTP %d: %s" % (e.code, e.read().decode("utf-8", "replace")[:1500]))
        raise

def wait_queue_idle():
    for _ in range(120):
        q = get(HOST + "/queue")
        if not q.get("queue_running") and not q.get("queue_pending"):
            return
        time.sleep(5)
    raise RuntimeError("queue never went idle")

def load_payload(n):
    with open(os.path.join(SCRIPTS, "_submit_payload_seg%d.json" % n),
              encoding="utf-8-sig") as f:
        graph = json.load(f)["prompt"]
    # Sanitize corrupted image links: first_frame/last_frame must be node
    # links (list) or absent. Some exported payloads carry stale ints here,
    # which crash MiniMaxH3ImageToVideo with "'int' object is not subscriptable".
    node = graph.get("131", {})
    for key in ("first_frame", "last_frame"):
        val = node.get("inputs", {}).get(key)
        if val is not None and not isinstance(val, list):
            log("seg%d sanitized node131.%s (was %r)" % (n, key, val))
            del node["inputs"][key]
    return graph


def patch_trt(graph):
    graph["2t"] = {"class_type": "MiniMaxH3TRTVAELoader",
                   "inputs": {"decoder": "minimax_h3_vae_decoder.engine",
                              "encoder": "None"}}
    std_id = None
    for nid, node in graph.items():
        ct = node.get("class_type", "")
        if ct == "VAELoader" and "video_vae" in str(node["inputs"].get("vae_name", "")):
            std_id = nid
        if ct == "VAEDecode":
            node["inputs"]["vae"] = ["2t", 0]
    return std_id

def patch_chain(graph, n):
    if n <= 1:
        return
    img = "seg%d_last_frame.png" % (n - 1)
    found = False
    for nid, node in graph.items():
        if node.get("class_type") in ("LoadImage", "LoadImageOutput"):
            node["inputs"]["image"] = img
            found = True
            log("seg%d LoadImage node %s -> %s" % (n, nid, img))
    if not found:
        raise RuntimeError("seg%d has no LoadImage node" % n)

def run_segment(n):
    wait_queue_idle()
    graph = load_payload(n)
    patch_trt(graph)
    patch_chain(graph, n)
    log("seg%d submitting (TRT VAE) ..." % n)
    t0 = time.time()
    resp = post({"prompt": graph, "client_id": "redo40-seg%d" % n})
    if "error" in resp:
        raise RuntimeError("seg%d queue error: %s" % (n, json.dumps(resp["error"], ensure_ascii=False)[:500]))
    pid = resp["prompt_id"]
    log("seg%d prompt_id=%s" % (n, pid))
    hist, status, err_detail = {}, None, ""
    while time.time() - t0 < 5400:
        time.sleep(15)
        try:
            hist = get(HOST + "/history/" + pid)
        except Exception:
            continue
        if pid not in hist:
            continue
        st = hist[pid].get("status", {})
        status = st.get("status_str")
        if status == "error":
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    err_detail = str(m[1].get("exception_message", ""))[:300]
            break
        if st.get("completed") or status == "success":
            break
    elapsed = time.time() - t0
    mode = "trt"
    if status != "success":
        log("seg%d TRT FAILED (%.0fs): %s -- retrying with standard VAE" % (n, elapsed, err_detail))
        graph = load_payload(n)
        patch_chain(graph, n)
        wait_queue_idle()
        mode = "std"
        t0 = time.time()
        resp = post({"prompt": graph, "client_id": "redo40-seg%d-std" % n})
        if "error" in resp:
            raise RuntimeError("seg%d retry queue error: %s" % (n, json.dumps(resp["error"], ensure_ascii=False)[:500]))
        pid = resp["prompt_id"]
        log("seg%d retry prompt_id=%s" % (n, pid))
        while time.time() - t0 < 5400:
            time.sleep(15)
            try:
                hist = get(HOST + "/history/" + pid)
            except Exception:
                continue
            if pid not in hist:
                continue
            st = hist[pid].get("status", {})
            status = st.get("status_str")
            if status == "error":
                for m in st.get("messages", []):
                    if m[0] == "execution_error":
                        err_detail = str(m[1].get("exception_message", ""))[:300]
                raise RuntimeError("seg%d failed on std VAE too: %s" % (n, err_detail))
            if st.get("completed") or status == "success":
                break
        elapsed = time.time() - t0
        if status != "success":
            raise RuntimeError("seg%d timed out" % n)
    outs = hist[pid].get("outputs", {})
    video_file = None
    for nid, o in outs.items():
        for val in o.values():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and str(item.get("filename", "")).endswith(".mp4"):
                        video_file = item
    if not video_file:
        raise RuntimeError("seg%d no mp4 in outputs: %s" % (n, json.dumps(outs, ensure_ascii=False)[:300]))
    sub = video_file.get("subfolder", "video")
    tail = os.path.join(sub.replace("/", os.sep), video_file["filename"])
    path = os.path.join(ROOT, "output", tail)
    if not os.path.exists(path):
        alt = os.path.join(ROOT, "ComfyUI", "output", tail)
        if os.path.exists(alt):
            path = alt
    size_mb = os.path.getsize(path) / 1048576.0 if os.path.exists(path) else -1
    log("seg%d DONE %.0fs -> %s (%.1f MB, mode=%s)" % (n, elapsed, video_file["filename"], size_mb, mode))
    if n < 4:
        last_png = os.path.join(ROOT, "input", "seg%d_last_frame.png" % n)
        cmd = ["ffmpeg", "-y", "-v", "error", "-sseof", "-0.05", "-i", path,
               "-frames:v", "1", "-update", "1", last_png]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(last_png):
            raise RuntimeError("seg%d last-frame extract failed: %s" % (n, r.stderr[:300]))
        log("seg%d last frame -> %s" % (n, last_png))
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("RESULT seg%d elapsed=%.0fs file=%s size=%.1fMB mode=%s\n" %
                (n, elapsed, video_file["filename"], size_mb, mode))
    return video_file["filename"]

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    files = {}
    for n in range(start, 5):
        files[n] = run_segment(n)
    log("ALL SEGMENTS DONE: %s" % files)

if __name__ == "__main__":
    main()

