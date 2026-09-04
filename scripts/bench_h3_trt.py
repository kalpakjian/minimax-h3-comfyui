# -*- coding: utf-8 -*-
"""Benchmark: H3 T2V with TRT VAE decode (same seed/settings as bench_h3.py).

Only difference vs bench_h3.py: video VAE for VAEDecode comes from
MiniMaxH3TRTVAELoader (compiled .engine) instead of the fp16 safetensors VAE.

Usage: python_embeded\\python.exe scripts\\bench_h3_trt.py <label>
"""
import json, urllib.request, time, sys, os, datetime

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
LABEL = sys.argv[1] if len(sys.argv) > 1 else "trt"
RESULT_FILE = os.environ.get("COMFY_BENCH_LOG", r"C:\minimax+comfyUI\logs\bench_results.txt")

PROMPT = ("A beautiful young woman wearing a white bathrobe walks slowly toward the camera, "
          "soft warm bathroom lighting, gentle steam, elegant beige tiled walls, cinematic. "
          "Gentle ambient music.")

G = {
 "1":{"class_type":"UNETLoader","inputs":{"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"}},
 "2":{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_video_vae_fp16.safetensors"}},
 "2a":{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"}},
 "2t":{"class_type":"MiniMaxH3TRTVAELoader","inputs":{"decoder":"minimax_h3_vae_decoder.engine","encoder":"None"}},
 "3":{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"}},
 "4":{"class_type":"MiniMaxH3TurboLoRA","inputs":{"model":["1",0],"lora_name":"minimax_h3_turbo_v4_step600_ema.safetensors","strength":1.0,"low_vram":True}},
 "5":{"class_type":"MiniMaxH3TurboSampler","inputs":{}},
 "6":{"class_type":"RandomNoise","inputs":{"noise_seed":731159}},
 "7":{"class_type":"BasicScheduler","inputs":{"model":["4",0],"scheduler":"simple","steps":4,"denoise":1.0}},
 "8":{"class_type":"BasicGuider","inputs":{"model":["4",0],"conditioning":["9",0]}},
 "9":{"class_type":"MiniMaxH3ImageToVideo","inputs":{"clip":["3",0],"vae":["2",0],"prompt":PROMPT,"width":864,"height":480,"length":73}},
 "10":{"class_type":"SamplerCustomAdvanced","inputs":{"noise":["6",0],"guider":["8",0],"sampler":["5",0],"sigmas":["7",0],"latent_image":["9",1]}},
 "11":{"class_type":"VAEDecode","inputs":{"samples":["10",0],"vae":["2t",0]}},
 "11a":{"class_type":"VAEDecodeAudio","inputs":{"samples":["10",0],"vae":["2a",0]}},
 "12":{"class_type":"CreateVideo","inputs":{"images":["11",0],"audio":["11a",0],"fps":24}},
 "13":{"class_type":"SaveVideo","inputs":{"video":["12",0],"filename_prefix":"video/bench_%s" % LABEL,"format":"mp4","codec":"h264"}},
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

def main():
    get(HOST+"/object_info")
    print("Submitting benchmark [%s] ..." % LABEL)
    t0 = time.time()
    resp = post({"prompt": G, "client_id": "bench-%s" % LABEL})
    if "error" in resp:
        print("QUEUE ERR", json.dumps(resp["error"], ensure_ascii=False))
        sys.exit(1)
    pid = resp["prompt_id"]
    print("prompt_id:", pid)
    status = "unknown"; h = {}
    timeout = 7200
    while time.time()-t0 < timeout:
        time.sleep(10)
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
    line = "%s label=%-14s elapsed=%8.1fs status=%s" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), LABEL, elapsed, status)
    print(line)
    print("outputs:", json.dumps(h.get("outputs", {}), ensure_ascii=False)[:500])
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    sys.exit(0 if status == "success" else 1)

if __name__ == "__main__":
    main()
