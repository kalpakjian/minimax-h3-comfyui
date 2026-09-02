# -*- coding: utf-8 -*-
"""Build & submit a 5s MiniMax-H3 T2V turbo workflow via ComfyUI API."""
import json, urllib.request, time, os, sys

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
OUT_COMFY = r"C:\minimax+comfyUI\ComfyUI\output"

PROMPT = (
    "Cinematic shot: a sleek silver robot slowly walking through a rain-soaked "
    "neon alley at night, purple and cyan neon signs reflecting on wet pavement, "
    "gentle camera push-in, light rain. Atmospheric synthwave music with soft bass "
    "pulse, subtle rain ambience. Moody, cinematic, 24fps."
)

def post(url, obj, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8","replace")
        print("HTTP %s body:"%e.code)
        print(body[:3000])
        raise

def get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())

# ---- build graph ----
G = {}  # node_id -> node
def nd(node_id, cls, attrs, inputs):
    G[node_id] = {"class_type": cls, "inputs": dict(inputs)}
    for k,v in attrs.items():
        G[node_id]["inputs"][k] = v

# 0 UNET
nd(0,"UNETLoader",{"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"},{})
# 1 video vae
nd(1,"VAELoader",{"vae_name":"minimax_h3_video_vae_fp16.safetensors"},{})
# 2 audio vae
nd(2,"VAELoader",{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"},{})
# 3 clip
nd(3,"CLIPLoader",{"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"},{})
# 4 turbo lora  (model <- 0)
nd(4,"MiniMaxH3TurboLoRA",{"lora_name":"minimax_h3_turbo_v4_step600_ema.safetensors","strength":1.0,"low_vram":False},{"model":[0,"0"]})
# 5 cond+latent (t2v via ImageToVideo with prompt only) clip<-3 vae<-1
nd(5,"MiniMaxH3ImageToVideo",{"prompt":PROMPT,"width":1344,"height":768,"length":124},{"clip":[3,"0"],"vae":[1,"0"]})
# 6 turbo sampler
nd(6,"MiniMaxH3TurboSampler",{}, {})
# 7 random noise
nd(7,"RandomNoise",{"noise_seed":123456},{})
# 8 basic scheduler  model<-4  simple 4 steps
nd(8,"BasicScheduler",{"scheduler":"simple","steps":4,"denoise":1.0},{"model":[4,"0"]})
# 9 basic guider  model<-4 cond<-5
nd(9,"BasicGuider",{}, {"model":[4,"0"],"conditioning":[5,"0"]})
# 10 sampler custom advanced
nd(10,"SamplerCustomAdvanced",{},
  {"noise":[7,"0"],"guider":[9,"0"],"sampler":[6,"0"],"sigmas":[8,"0"],"latent_image":[5,"1"]})
# 11 vaedecode video  samples<-10
nd(11,"VAEDecode",{}, {"samples":[10,"0"],"vae":[1,"0"]})
# 12 vaedecode audio  samples<-10
nd(12,"VAEDecodeAudio",{}, {"samples":[10,"0"],"vae":[2,"0"]})
# 13 create video  images<-11 audio<-12 fps24
nd(13,"CreateVideo",{"fps":24.0,"bit_depth":8},{"images":[11,"0"],"audio":[12,"0"]})
# 14 save video
nd(14,"SaveVideo",{"filename_prefix":"video/MiniMax_H3_5s","format":"auto","codec":{"key":"auto","inputs":{"required":{}}}},{ "video":[13,"0"]})

wf = {"prompt": G, "client_id":"h3-t2v-5s"}
with open(r"C:\minimax+comfyUI\h3_t2v_5s_workflow.json","w",encoding="utf-8") as f:
    json.dump(G, f, ensure_ascii=False, indent=2)
print("Workflow bytes:", len(json.dumps(G)))

# ---- submit ----
print("Submitting to", HOST)
resp = post(HOST+"/prompt", wf)
if "error" in resp:
    print("QUEUE ERROR:", json.dumps(resp["error"], ensure_ascii=False))
    sys.exit(1)
pid = resp["prompt_id"]
print("Queued prompt_id:", pid)

# ---- wait ----
t0=time.time(); timeout=2400
while time.time()-t0 < timeout:
    time.sleep(10)
    try:
        hist=get(HOST+"/history/"+pid)
    except Exception:
        continue
    if pid not in hist: continue
    h=hist[pid]; st=h.get("status",{}); status=st.get("status_str","unknown")
    if status=="error":
        for m in st.get("messages",[]):
            if m[0]=="execution_error":
                print("EXEC ERROR:", str(m[1].get("exception_message",""))[:3000])
        break
    if st.get("completed") or status=="success":
        break
else:
    print("TIMEOUT")
    sys.exit(1)
print("STATUS:", status, "elapsed %.1fs"%(time.time()-t0))
print("Outputs:", json.dumps(h.get("outputs",{}), ensure_ascii=False)[:2000])
if status!="success":
    # dump execution messages
    for m in st.get("messages",[]): print("MSG:", m[0], str(m[1])[:400])
    sys.exit(1)