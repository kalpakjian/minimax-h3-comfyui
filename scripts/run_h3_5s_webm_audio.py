# -*- coding: utf-8 -*-
"""Generate 5s H3 T2V turbo: saves animated WEBP (video frames) via SaveAnimatedWEBP,
bypassing the CreateVideo/SaveVideo VIDEO-type validation that is erroring."""
import json, urllib.request, time, sys
HOST="http://127.0.0.1:8188"
PROMPT=("Cinematic shot: a sleek silver robot slowly walking through a rain-soaked "
 "neon alley at night, purple and cyan neon signs reflecting on wet pavement, "
 "gentle camera push-in, light rain. Atmospheric synthwave music, soft bass pulse. "
 "Moody, cinematic lighting, 24fps.")

G={
 1:{"class_type":"UNETLoader","inputs":{"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"}},
 2:{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_video_vae_fp16.safetensors"}},
 3:{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"}},
 4:{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"}},
 5:{"class_type":"MiniMaxH3TurboLoRA","inputs":{"model":[1,"0"],"lora_name":"minimax_h3_turbo_v4_step600_ema.safetensors","strength":1.0,"low_vram":False}},
 6:{"class_type":"MiniMaxH3TurboSampler","inputs":{}},
 7:{"class_type":"RandomNoise","inputs":{"noise_seed":20240831}},
 8:{"class_type":"BasicScheduler","inputs":{"model":[5,"0"],"scheduler":"simple","steps":6,"denoise":1.0}},
 9:{"class_type":"BasicGuider","inputs":{"model":[5,"0"],"conditioning":[11,"0"]}},
 10:{"class_type":"SamplerCustomAdvanced","inputs":{"noise":[7,"0"],"guider":[9,"0"],"sampler":[6,"0"],"sigmas":[8,"0"],"latent_image":[11,"1"]}},
 11:{"class_type":"MiniMaxH3ImageToVideo","inputs":{"clip":[4,"0"],"vae":[2,"0"],"prompt":PROMPT,"width":1344,"height":768,"length":124}},
 12:{"class_type":"VAEDecode","inputs":{"samples":[10,"0"],"vae":[2,"0"]}},
 13:{"class_type":"VAEDecodeAudio","inputs":{"samples":[10,"0"],"vae":[3,"0"]}},
 14:{"class_type":"SaveAnimatedWEBP","inputs":{"images":[12,"0"],"filename_prefix":"video/MiniMax_H3_5s","fps":24.0,"lossless":False,"quality":90,"method":"default"}},
 15:{"class_type":"SaveAudio","inputs":{"audio":[13,"0"],"filename_prefix":"audio/MiniMax_H3_5s"}},
}

def post(obj):
    req=urllib.request.Request(HOST+"/prompt",data=json.dumps(obj).encode(),headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP",e.code,"\n",e.read().decode("utf-8","replace")[:1500]);raise
def get(u):
    with urllib.request.urlopen(u,timeout=30) as r:
        return json.loads(r.read().decode())

print("Submitting...")
resp=post({"prompt":G,"client_id":"h3-5s"})
if "error" in resp:
    print("QUEUE ERR",json.dumps(resp["error"],ensure_ascii=False));sys.exit(1)
pid=resp["prompt_id"];print("prompt_id:",pid)
t0=time.time();timeout=3600
while time.time()-t0<timeout:
    time.sleep(15)
    try: hist=get(HOST+"/history/"+pid)
    except Exception: continue
    if pid not in hist: continue
    h=hist[pid];st=h.get("status",{});status=st.get("status_str","unknown")
    if status=="error":
        for m in st.get("messages",[]):
            if m[0]=="execution_error":print("EXEC ERR:",str(m[1].get("exception_message",""))[:3000])
        break
    if st.get("completed") or status=="success": break
else:
    print("TIMEOUT");sys.exit(1)
print("STATUS",status,"elapsed %.1fs"%(time.time()-t0))
print("outputs:",json.dumps(h.get("outputs",{}),ensure_ascii=False)[:2000])
if status!="success":
    for m in st.get("messages",[]):print("MSG",m[0],str(m[1])[:800])
    sys.exit(1)