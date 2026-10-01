# -*- coding: utf-8 -*-
"""Nightly series stage: Character Swap + color match (swap + color grade).

Wired into run_nightly.ps1 (-Swap after the 4-seg batch, -SwapOnly standalone).
Can also be run directly:

    python_embeded_nightly\\python.exe scripts\\_swap_nightly.py            # submit swap for config seeds + color match
    python_embeded_nightly\\python.exe scripts\\_swap_nightly.py <mp4>     # skip submit: color-match an existing swap output
    python_embeded_nightly\\python.exe scripts\\_swap_nightly.py --dry     # print the plan only

Stages:
  S1 Submit the H3 Character Swap workflow (ref2va int8 + character-swap LoRA
     + 4-step turbo + TRT VAE) from scripts\\_swap_payload_base.json with the
     config's source video / replacement image / seed. If execution fails,
     retry once with the standard VAE (TRT node stripped).
  S2 Color-correct the swapped clip against the source video: per-channel
     gain/offset fitted by least squares on sampled matched frames, applied
     through ffmpeg rawvideo pipes (audio stream preserved).

Config : scripts\\_swap_nightly_config.json
Outputs: <prefix>_NNNNN_.mp4   raw swap (SaveVideo prefix auto-increments,
                               existing files are NEVER overwritten)
         <name>_cc.mp4         color-corrected
Log    : logs\\swap_nightly_results.txt
"""
import json, os, sys, time, random, datetime, subprocess
import urllib.request, urllib.error

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy missing - run with python_embeded_nightly\\python.exe")
    sys.exit(2)

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
ROOT = r"D:\AI\ComfyUI"
SCRIPTS = os.path.join(ROOT, "scripts")
CFG = os.path.join(SCRIPTS, "_swap_nightly_config.json")
BASE = os.path.join(SCRIPTS, "_swap_payload_base.json")
LOG = os.path.join(ROOT, "logs", "swap_nightly_results.txt")


def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get(u, timeout=60):
    with urllib.request.urlopen(u, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post(obj, timeout=120):
    req = urllib.request.Request(HOST + "/prompt",
                                 data=json.dumps(obj).encode(),
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


def load_cfg():
    with open(CFG, encoding="utf-8-sig") as f:
        return json.load(f)


def build_prompt(cfg, seed):
    with open(BASE, encoding="utf-8-sig") as f:
        p = json.load(f)
    p["139"]["inputs"]["file"] = cfg["source_video"]
    p["137"]["inputs"]["image"] = cfg["replacement_image"]
    p["138"]["inputs"]["value"] = cfg.get("prompt",
        "Replace only the person in <Video 1> with the character in <Picture 1>. "
        "Preserve the source video's camera, framing, background, lighting, objects. "
        "Match the person's position, scale, pose, and movement throughout the clip. "
        "Do not show the reference sheet or its background.")
    p["136"]["inputs"]["width"] = int(cfg.get("width", 768))
    p["136"]["inputs"]["height"] = int(cfg.get("height", 768))
    p["132"]["inputs"]["value"] = float(cfg.get("length_s", 15))
    p["129"]["inputs"]["noise_seed"] = int(seed)
    p["92"]["inputs"]["filename_prefix"] = cfg.get("prefix", "video/H3_SwapNightly")
    return p


def strip_trt(p):
    p = json.loads(json.dumps(p))
    p.pop("2t", None)
    if "122" in p:
        p["122"]["inputs"]["vae"] = ["119", 0]
    return p


def wait_swap(pid, timeout=4800):
    """Return (ok, [mp4 filenames], err_detail)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(15)
        try:
            hist = get(HOST + "/history/" + pid)
        except Exception:
            continue
        if pid not in hist:
            continue
        st = hist[pid].get("status", {})
        status = st.get("status_str")
        err = ""
        for m in st.get("messages", []):
            if m[0] in ("execution_error", "execution_interrupted"):
                err = str(m[1].get("exception_message", ""))[:400]
        if status == "error":
            return False, [], err or "status=error"
        if st.get("completed") or status == "success":
            files = []
            for nid, o in hist[pid].get("outputs", {}).items():
                for key, items in o.items():
                    if isinstance(items, list):
                        for it in items:
                            # only real outputs (SaveVideo); LoadVideo echoes
                            # the INPUT filename with type "input" - ignore
                            if (isinstance(it, dict) and it.get("type") == "output"
                                    and str(it.get("filename", "")).endswith(".mp4")):
                                files.append(it["filename"])
            return (len(files) > 0, files, "")
    return False, [], "timed out after %ds" % int(time.time() - t0)


def run_swap(cfg, seed):
    for mode in ("trt", "std"):
        p = build_prompt(cfg, seed)
        if mode == "std":
            p = strip_trt(p)
            log("seed=%d retrying with standard VAE (TRT stripped)" % seed)
        wait_queue_idle()
        t0 = time.time()
        resp = post({"prompt": p, "client_id": "swap-nightly-%d-%s" % (seed, mode)})
        if "error" in resp:
            raise RuntimeError("submit failed: %s" % json.dumps(resp["error"], ensure_ascii=False)[:500])
        pid = resp["prompt_id"]
        log("seed=%d submitted (mode=%s) prompt_id=%s" % (seed, mode, pid))
        ok, files, err = wait_swap(pid)
        if ok:
            log("seed=%d DONE %.0fs -> %s" % (seed, time.time() - t0, files[0]))
            return os.path.join(ROOT, "output", files[0])
        log("seed=%d failed (mode=%s): %s" % (seed, mode, err[:300]))
    raise RuntimeError("seed=%d failed on TRT and standard VAE" % seed)


def pick_seeds(cfg):
    n = int(cfg.get("seed_count", 1))
    s = cfg.get("seed", "random")
    rnd = random.Random()
    if s in (None, "random"):
        return [rnd.randint(1, 2 ** 31 - 1) for _ in range(n)]
    base = int(s)
    return [base + i for i in range(n)]


# ------------------------------------------------- S2: color match (grade)
def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,avg_frame_rate,nb_frames:format=duration",
                        "-of", "json", path], capture_output=True, text=True, timeout=60)
    d = json.loads(r.stdout)
    st = d["streams"][0]
    num, den = st["avg_frame_rate"].split("/")
    fps = float(num) / float(den)
    n = st.get("nb_frames")
    if not n:
        dur = float(d.get("format", {}).get("duration", 0))
        n = int(round(dur * fps))
    return {"w": int(st["width"]), "h": int(st["height"]), "fps": fps, "n": int(n)}


def read_frame(path, t_sec, w, h, scale=None):
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "%.4f" % t_sec, "-i", path]
    if scale:
        cmd += ["-vf", "scale=%d:%d:flags=lanczos" % scale]
    cmd += ["-frames:v", "1", "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, timeout=120)
    need = w * h * 3
    if len(r.stdout) < need:
        raise RuntimeError("frame read short: %s @ %.2fs (%d bytes)" % (os.path.basename(path), t_sec, len(r.stdout)))
    return np.frombuffer(r.stdout[:need], np.uint8).reshape(h, w, 3)


def fit_match(src, out, w, h, fps, sample):
    """Per-channel gain/offset fit mapping swap(out) -> source(src).

    The swap output is a RE-RENDER: the swapped person region (and a few
    frames of timing drift) do not pixel-align with the source, so a plain
    least squares over all pixels collapses. Instead use residual-weighted
    least squares: pixels where the two frames already agree (background,
    lighting, static objects) carry the fit; mismatched pixels are damped.
    """
    meta_s, meta_o = ffprobe(src), ffprobe(out)
    n = min(meta_s["n"], meta_o["n"])
    idx = sorted({int(x) for x in np.linspace(0, n - 1, min(sample, n))})
    scale_s = (w, h) if (meta_s["w"], meta_s["h"]) != (w, h) else None
    A_list, B_list = [], []   # A = out (swap, what we grade), B = src (target)
    for i in idx:
        t = i / fps
        Bf = read_frame(src, t, w, h, scale_s).astype(np.float64).reshape(-1, 3)
        Af = read_frame(out, t, w, h, None).astype(np.float64).reshape(-1, 3)
        m = min(len(Af), len(Bf))
        A_list.append(Af[:m])
        B_list.append(Bf[:m])
    A = np.concatenate(A_list, 0)
    B = np.concatenate(B_list, 0)
    step = max(1, len(A) // 400000)
    A, B = A[::step], B[::step]
    gain, bias = np.ones(3), np.zeros(3)
    sigma2 = 15.0 ** 2
    for _ in range(2):  # iterate: refit on current residual weights
        # per-pixel weight from squared L2 color distance (1D, per pixel)
        resid = np.square(B - (A * gain + bias)).sum(axis=1)
        wts = np.exp(-resid / (2 * sigma2 * 3))
        for c in range(3):
            ac = A[:, c]
            bc = B[:, c]
            N = wts.sum()
            sA = (wts * ac).sum()
            sB = (wts * bc).sum()
            sAA = (wts * ac * ac).sum()
            sAB = (wts * ac * bc).sum()
            det = sAA * N - sA * sA
            if det < 1e-6:
                continue
            m = (sAB * N - sA * sB) / det
            bb = (sB * sAA - sA * sAB) / det
            gain[c] = min(2.0, max(0.5, m))
            bias[c] = min(60.0, max(-60.0, bb))
    return gain, bias


def apply_match(out, dst, w, h, fps, gain, bias, strength, crf, has_audio):
    cmd_in = ["ffmpeg", "-v", "error", "-i", out, "-an",
              "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (w, h), "-"]
    cmd_out = ["ffmpeg", "-y", "-v", "error", "-i", out,
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (w, h),
               "-r", "%.4f" % fps, "-i", "-", "-map", "1:v:0"]
    if has_audio:
        cmd_out += ["-map", "0:a:0", "-c:a", "copy", "-shortest"]
    cmd_out += ["-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
                "-pix_fmt", "yuv420p", dst]
    r_in = subprocess.Popen(cmd_in, stdout=subprocess.PIPE)
    r_out = subprocess.Popen(cmd_out, stdin=subprocess.PIPE)
    frame = w * h * 3
    cnt = 0
    rc = -1
    try:
        while True:
            chunk = r_in.stdout.read(frame)
            if not chunk:
                break
            arr = np.frombuffer(chunk, np.uint8).astype(np.float32).reshape(h, w, 3)
            y = arr + (arr * gain + bias - arr) * strength
            r_out.stdin.write(np.clip(y, 0, 255).astype(np.uint8).tobytes())
            cnt += 1
            if cnt % 48 == 0:
                print("    color match: %d frames" % cnt, flush=True)
        r_out.stdin.close()
        r_in.wait()
        rc = r_out.wait()
    finally:
        for p in (r_in, r_out):
            if p.poll() is None:
                p.kill()
    if rc != 0 or not os.path.exists(dst):
        raise RuntimeError("color-match encode failed rc=%s" % rc)
    log("color match applied: %d frames -> %s" % (cnt, os.path.basename(dst)))


def color_match(out, src, cfg):
    cm = cfg.get("color_match", {})
    if not cm.get("enabled", True):
        log("color match disabled by config")
        return None
    meta = ffprobe(out)
    w, h, fps = meta["w"], meta["h"], meta["fps"]
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=codec_name", "-of", "json", out],
                       capture_output=True, text=True, timeout=60)
    has_audio = len(json.loads(r.stdout).get("streams", [])) > 0
    sample = int(cm.get("sample_frames", 15))
    strength = float(cm.get("strength", 0.85))
    crf = int(cm.get("crf", 18))
    t0 = time.time()
    gain, bias = fit_match(src, out, w, h, fps, sample)
    dst = out[:-4] + "_cc.mp4"
    log("gain=%s bias=%s strength=%.2f sample=%d (fit %.0fs)" %
        (np.round(gain, 4).tolist(), np.round(bias, 2).tolist(), strength, sample, time.time() - t0))
    apply_match(out, dst, w, h, fps, gain, bias, strength, crf, has_audio)
    return dst


# -------------------------------------------------------------------- main
def main():
    args = [a for a in sys.argv[1:] if a]
    dry = "--dry" in args
    direct = next((a for a in args if not a.startswith("-")), None)
    cfg = load_cfg()
    if not os.path.exists(BASE):
        sys.exit("base payload missing: " + BASE)

    if dry:
        print("[DryRun] config ok. source=%s ref=%s %dx%d %.0fs prefix=%s" %
              (cfg["source_video"], cfg["replacement_image"],
               cfg.get("width", 768), cfg.get("height", 768),
               cfg.get("length_s", 15), cfg.get("prefix")))
        if direct:
            print("[DryRun] will color-match existing file: %s" % direct)
        else:
            print("[DryRun] will submit seeds: %s (count=%d)" %
                  (cfg.get("seed", "random"), cfg.get("seed_count", 1)))
        return

    results = {}
    if direct:
        if not os.path.exists(direct):
            sys.exit("no such file: " + direct)
        results[os.path.basename(direct)] = direct
    else:
        if not os.path.exists(os.path.join(ROOT, "input", cfg["source_video"])):
            sys.exit("source video missing: input\\" + cfg["source_video"])
        if not os.path.exists(os.path.join(ROOT, "input", cfg["replacement_image"])):
            sys.exit("replacement image missing: input\\" + cfg["replacement_image"])
        for seed in pick_seeds(cfg):
            results["seed_%d" % seed] = run_swap(cfg, seed)

    src = os.path.join(ROOT, "input", cfg["source_video"])
    for name, path in results.items():
        try:
            dst = color_match(path, src, cfg)
        except Exception as e:
            log("color match FAILED for %s: %s" % (name, e))
            continue
        if dst:
            results[name] = dst
    log("ALL SWAP SEGMENTS DONE: %s" % json.dumps(results, ensure_ascii=False))
    for k, v in results.items():
        print("RESULT %s -> %s" % (k, v))


if __name__ == "__main__":
    main()
