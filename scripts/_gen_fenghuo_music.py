# -*- coding: utf-8 -*-
"""Generate ~30.5s original epic ancient-Chinese war trailer soundtrack via MiniMax Music3.
Instrumental only, no vocals. Launches in background (server keeps running if shell times out).
"""
import json, time, urllib.request, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
LOG = r"C:\minimax+comfyUI\logs\fenghuo_music.log"
DURATION = 30.5

def log(m):
    line = time.strftime("%H:%M:%S") + "  " + m
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())

caption = ("Epic cinematic historical war film trailer instrumental, ancient Chinese northern frontier battlefield. "
           "Opens slow and low with deep taiko war drums, low dark strings and a mournful desolate bamboo flute over "
           "a vast lonely desert steppe under a setting sun. Slowly builds with increasingly dense war drums, "
           "low brass and fast driving strings. At the climactic battle the music erupts into a massive epic orchestral "
           "crescendo with pounding drums, roaring horns and soaring strings, grand and tragic, tense and layered. "
           "Then it suddenly cuts to near-silence leaving only the sound of wind blowing sand, before a final thunderous "
           "drum hit. Large-scale historical war epic orchestral film score feel: grand, mournful, tense, dramatic, with a "
           "clear build and release. No modern pop, no electronic dance, instrumental only, no vocals, no lyrics.")

prompt = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_music3_dit_fp16.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors", "type": "minimax"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_music3_dav.safetensors"}},
    "4": {"class_type": "MiniMaxMusic3TextEncode", "inputs": {
        "clip": ["2", 0], "caption": caption, "lyrics": "",
        "seed": 731159, "max_duration": 240.0, "cfg_scale": 1.0, "top_k": 32}},
    "5": {"class_type": "EmptyMiniMaxMusic3LatentAudio", "inputs": {"seconds": DURATION, "batch_size": 1}},
    "6": {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 0],
        "latent_image": ["5", 0], "seed": 731159, "steps": 6, "cfg": 1.0,
        "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
    "7": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
    "8": {"class_type": "SaveAudioMP3", "inputs": {"audio": ["7", 0], "filename_prefix": "fenghuo_trailer", "quality": "320k"}},
}

log("Submitting MiniMax Music3 fenghuo trailer generation (%.1fs)..." % DURATION)
try:
    resp = post(HOST + "/prompt", {"prompt": prompt, "client_id": "music-fenghuo"})
except Exception as e:
    log("QUEUE FAILED: %s" % e); raise SystemExit(1)
if "error" in resp:
    log("QUEUE ERROR: " + json.dumps(resp["error"], ensure_ascii=False)); raise SystemExit(1)
pid = resp["prompt_id"]
log("Queued, prompt_id=%s" % pid)
while True:
    time.sleep(3)
    try:
        hist = post(HOST + "/history/" + pid, {})
    except Exception:
        continue
    if pid in hist:
        h = hist[pid]
        st = h.get("status", {})
        for nid, out in h.get("outputs", {}).items():
            if "audio" in out:
                for a in out["audio"]:
                    log("DONE audio: " + a.get("filename", ""))
        log("STATUS: " + str(st.get("status_str")))
        if st.get("status_str") == "error":
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    log("EXEC ERROR: " + str(m[1].get("exception_message", ""))[:1500])
        break