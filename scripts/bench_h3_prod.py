# -*- coding: utf-8 -*-
"""Benchmark: production-scale H3 T2V segment (1344x768, 243 frames, 6 steps).

Mirrors the production payload (scripts\\_fenghuo_seg1.json): fl2va int8 + turbo
LoRA (low_vram=true) + BasicScheduler 6 steps + video/audio VAE + CreateVideo +
SaveVideo. The decode VAE is selectable, everything else is identical:

    python_embeded\\python.exe scripts\\bench_h3_prod.py <label> [seed] [trt|fp16]

3rd arg defaults to "trt" = MiniMaxH3TRTVAELoader (compiled .engine);
"fp16" = plain VAELoader (minimax_h3_video_vae_fp16.safetensors).

Notes:
- The fp16 video VAE still feeds MiniMaxH3ImageToVideo (conditioning), exactly as
  in production; only the VAEDecode node switches.
- Seed does not change the workload (same shapes/steps), only content — pass a new
  seed each run or ComfyUI reuses its execution cache (see H3_TURBO_SETUP.md).
- Log line carries elapsed (client) + exec (server-side execution_start ->
  execution_success) + the server's pytorch_version, same format as
  bench_h3_trt.py / bench_h3_fine.py.
"""
import json, urllib.request, time, sys, os, datetime

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
LABEL = sys.argv[1] if len(sys.argv) > 1 else "prod"
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 9001
VAE_MODE = (sys.argv[3] if len(sys.argv) > 3 else "trt").lower()
RESULT_FILE = os.environ.get("COMFY_BENCH_LOG", r"D:\AI\ComfyUI\logs\bench_results_prod.txt")

WIDTH, HEIGHT, LENGTH, STEPS = 1344, 768, 243, 6

PROMPT = ("A beautiful young woman wearing a white bathrobe walks slowly toward the camera, "
          "soft warm bathroom lighting, gentle steam, elegant beige tiled walls, cinematic. "
          "Gentle ambient music.")

if VAE_MODE == "trt":
    DECODE_VAE = {"class_type": "MiniMaxH3TRTVAELoader",
                  "inputs": {"decoder": "minimax_h3_vae_decoder.engine", "encoder": "None"}}
elif VAE_MODE == "fp16":
    DECODE_VAE = {"class_type": "VAELoader",
                  "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}}
else:
    raise SystemExit("VAE mode must be 'trt' or 'fp16', got %r" % VAE_MODE)

G = {
 "1":{"class_type":"UNETLoader","inputs":{"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"}},
 "2":{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_video_vae_fp16.safetensors"}},
 "2a":{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"}},
 "2d":DECODE_VAE,
 "3":{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"}},
 "4":{"class_type":"MiniMaxH3TurboLoRA","inputs":{"model":["1",0],"lora_name":"minimax_h3_turbo_v4_step600_ema.safetensors","strength":1.0,"low_vram":True}},
 "5":{"class_type":"MiniMaxH3TurboSampler","inputs":{}},
 "6":{"class_type":"RandomNoise","inputs":{"noise_seed":SEED}},
 "7":{"class_type":"BasicScheduler","inputs":{"model":["4",0],"scheduler":"simple","steps":STEPS,"denoise":1.0}},
 "8":{"class_type":"BasicGuider","inputs":{"model":["4",0],"conditioning":["9",0]}},
 "9":{"class_type":"MiniMaxH3ImageToVideo","inputs":{"clip":["3",0],"vae":["2",0],"prompt":PROMPT,"width":WIDTH,"height":HEIGHT,"length":LENGTH}},
 "10":{"class_type":"SamplerCustomAdvanced","inputs":{"noise":["6",0],"guider":["8",0],"sampler":["5",0],"sigmas":["7",0],"latent_image":["9",1]}},
 "11":{"class_type":"VAEDecode","inputs":{"samples":["10",0],"vae":["2d",0]}},
 "11a":{"class_type":"VAEDecodeAudio","inputs":{"samples":["10",0],"vae":["2a",0]}},
 "12":{"class_type":"CreateVideo","inputs":{"images":["11",0],"audio":["11a",0],"fps":24}},
 "13":{"class_type":"SaveVideo","inputs":{"video":["12",0],"filename_prefix":"video/benchprod_%s" % LABEL,"format":"mp4","codec":"h264"}},
}

def post(obj):
    req = urllib.request.Request(HOST+"/prompt", data=json.dumps(obj).encode(),
                                 headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code)
        print(e.read().decode("utf-8","replace")[:2000])
        raise

def get(u):
    with urllib.request.urlopen(u, timeout=30) as r:
        return json.loads(r.read().decode())

def server_exec_seconds(h):
    """Server-side execution time (execution_start -> execution_success), seconds.

    Immune to client poll granularity and to queue wait, unlike `elapsed`.
    """
    ts = {}
    for m in h.get("status", {}).get("messages", []):
        if m[0] in ("execution_start", "execution_success"):
            ts[m[0]] = m[1].get("timestamp")
    if "execution_start" in ts and "execution_success" in ts:
        return (ts["execution_success"] - ts["execution_start"]) / 1000.0
    return None

def server_torch_version():
    try:
        return get(HOST + "/system_stats").get("system", {}).get("pytorch_version", "?")
    except Exception:
        return "?"

def main():
    get(HOST+"/object_info")
    torchv = server_torch_version()
    print("Submitting production benchmark [%s] vae=%s %dx%d/%d frames/%d steps torch=%s ..." % (
        LABEL, VAE_MODE, WIDTH, HEIGHT, LENGTH, STEPS, torchv))
    t0 = time.time()
    resp = post({"prompt": G, "client_id": "benchprod-%s" % LABEL})
    if "error" in resp:
        print("QUEUE ERR", json.dumps(resp["error"], ensure_ascii=False))
        sys.exit(1)
    pid = resp["prompt_id"]
    print("prompt_id:", pid)
    status = "unknown"; h = {}
    timeout = 14400
    while time.time()-t0 < timeout:
        time.sleep(5)
        try:
            hist = get(HOST+"/history/"+pid)
        except Exception:
            continue
        if pid not in hist:
            continue
        h = hist[pid]; st = h.get("status", {})
        status = st.get("status_str", "unknown")
        if status == "error":
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    print("EXEC ERR:", m[1].get("exception_message"))
                    print("\n".join(m[1].get("traceback", [])))
            break
        if st.get("completed") or status == "success":
            break
    elapsed = time.time()-t0
    exec_s = server_exec_seconds(h)
    line = "%s label=%-14s vae=%-4s %dx%d/%d/%dstep elapsed=%8.1fs exec=%7.1fs torch=%-24s status=%s" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), LABEL, VAE_MODE,
        WIDTH, HEIGHT, LENGTH, STEPS, elapsed,
        exec_s if exec_s is not None else -1.0, torchv, status)
    print(line)
    print("outputs:", json.dumps(h.get("outputs", {}), ensure_ascii=False)[:500])
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    sys.exit(0 if status == "success" else 1)

if __name__ == "__main__":
    main()

