# -*- coding: utf-8 -*-
"""Music3 v2 fair-test batch for fenghuo trailer.
Fixes vs v1: cfg_scale 1.5, top_k 50, trimmed caption, 22s latent, 4 seeds.
"""
import json, time, urllib.request, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
LOG = r"C:\minimax+comfyUI\logs\fenghuo_music_v2.log"
DURATION = 22.0
SEEDS = [731159, 20260905, 884422, 314159]

CAPTION = (
    "Epic ancient Chinese war film trailer score, instrumental only. "
    "Deep taiko war drums, mournful bamboo flute, dark low strings and brass. "
    "Slow desolate open, builds to dense drums and driving strings, "
    "climaxes with massive orchestral crescendo of pounding drums and soaring horns. "
    "Grand, tragic, tense. No vocals, no lyrics, no modern pop, no electronic dance."
)


def log(m):
    line = time.strftime("%H:%M:%S") + "  " + m
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def post(url, obj, timeout=120):
    req = urllib.request.Request(
        url, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())

def make_prompt(seed, idx):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "minimax_music3_dit_fp16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors",
            "type": "minimax"}},
        "3": {"class_type": "VAELoader", "inputs": {
            "vae_name": "minimax_music3_dav.safetensors"}},
        "4": {"class_type": "MiniMaxMusic3TextEncode", "inputs": {
            "clip": ["2", 0], "caption": CAPTION, "lyrics": "",
            "seed": seed, "max_duration": 240.0, "cfg_scale": 1.5, "top_k": 50}},
        "5": {"class_type": "EmptyMiniMaxMusic3LatentAudio", "inputs": {
            "seconds": DURATION, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": 6, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "7": {"class_type": "VAEDecodeAudio", "inputs": {
            "samples": ["6", 0], "vae": ["3", 0]}},
        "8": {"class_type": "SaveAudioMP3", "inputs": {
            "audio": ["7", 0],
            "filename_prefix": "fenghuo_m3_v2_s%d" % idx,
            "quality": "320k"}},
    }


def wait_prompt(pid, label, timeout_s=1800):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        time.sleep(5)
        try:
            hist = get(HOST + "/history/" + pid)
        except Exception as e:
            log("%s history poll err: %s" % (label, e))
            continue
        if pid not in hist:
            continue
        h = hist[pid]
        st = h.get("status", {})
        status_str = st.get("status_str", "?")
        files = []
        for nid, out in h.get("outputs", {}).items():
            if "audio" in out:
                for a in out["audio"]:
                    files.append(a.get("filename", ""))
        if status_str == "success":
            log("%s DONE files=%s" % (label, files))
            return True, files
        if status_str == "error":
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    msg = str(m[1].get("exception_message", ""))[:1500]
                    log("%s EXEC ERROR: %s" % (label, msg))
            return False, []
        if int(time.time() - t0) % 60 < 6:
            log("%s still running... %ds" % (label, int(time.time() - t0)))
    log("%s TIMEOUT after %ds" % (label, timeout_s))
    return False, []


def main():
    open(LOG, "w", encoding="utf-8").write("")
    log("=== Music3 v2 fair-test batch start ===")
    log("CAPTION: %s" % CAPTION)
    log("DURATION=%.1fs cfg_scale=1.5 top_k=50 seeds=%s" % (DURATION, SEEDS))
    try:
        get(HOST + "/system_stats", timeout=10)
        log("ComfyUI alive")
    except Exception as e:
        log("ComfyUI DOWN: %s" % e)
        raise SystemExit(1)

    results = []
    for i, seed in enumerate(SEEDS, 1):
        label = "s%d(seed=%d)" % (i, seed)
        log("Submitting %s ..." % label)
        try:
            resp = post(HOST + "/prompt", {
                "prompt": make_prompt(seed, i),
                "client_id": "music-v2-%d" % i,
            })
        except Exception as e:
            log("%s QUEUE FAILED: %s" % (label, e))
            results.append((label, False, []))
            continue
        if "error" in resp or resp.get("node_errors"):
            log("%s QUEUE ERROR: %s" % (label, json.dumps(resp, ensure_ascii=False)[:800]))
            results.append((label, False, []))
            continue
        pid = resp["prompt_id"]
        log("%s queued prompt_id=%s" % (label, pid))
        ok, files = wait_prompt(pid, label)
        results.append((label, ok, files))

    log("=== BATCH SUMMARY ===")
    all_ok = True
    for label, ok, files in results:
        log("  %s -> %s %s" % (label, "OK" if ok else "FAIL", files))
        if not ok:
            all_ok = False
    log("ALL_OK=%s" % all_ok)
    raise SystemExit(0 if all_ok else 2)


if __name__ == "__main__":
    main()
