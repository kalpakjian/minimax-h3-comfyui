# -*- coding: utf-8 -*-
"""MiniMax H3 T2V — 還原 bathrobe_bathtub_t2v_5s (00002) 設定，僅 CLIP→AWQ、low_vram→bypass。
輸出帶音訊 mp4 (CreateVideo+SaveVideo, video/MiniMax_H3_00002_style)。"""
import json, urllib.request, time, sys
HOST = "http://127.0.0.1:8188"

PROMPT = ("A beautiful Chinese young woman wearing nothing walks slowly toward the camera. "
          "The camera glides backward in front of her, so her front side and face are always fully visible to the viewer, never her back. "
          "She keeps gentle eye contact with the camera the whole time. As she approaches, a white bathtub is revealed in the background behind her. "
          "Soft warm bathroom lighting, light steam rising from the water, elegant beige tiled walls, cinematic frontal tracking shot.\n"
          "Audio: gentle ambient spa music, quiet water rippling, soft room tone.")

G = {
 "1":  {"class_type":"UNETLoader","inputs":{"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"}},
 "2":  {"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_video_vae_fp16.safetensors"}},
 "2a": {"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"}},
 "3":  {"class_type":"CLIPLoader","inputs":{"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"}},
 "4":  {"class_type":"MiniMaxH3TurboLoRA","inputs":{"model":["1",0],"lora_name":"minimax_h3_turbo_v4_step600_ema.safetensors","strength":1.0,"low_vram":True}},
 "5":  {"class_type":"MiniMaxH3TurboSampler","inputs":{}},
 "6":  {"class_type":"RandomNoise","inputs":{"noise_seed":731159}},
 "7":  {"class_type":"BasicScheduler","inputs":{"model":["4",0],"scheduler":"simple","steps":6,"denoise":1.0}},
 "8":  {"class_type":"BasicGuider","inputs":{"model":["4",0],"conditioning":["9",0]}},
 "9":  {"class_type":"MiniMaxH3ImageToVideo","inputs":{"clip":["3",0],"vae":["2",0],"prompt":PROMPT,"width":864,"height":480,"length":240}},
 "10": {"class_type":"SamplerCustomAdvanced","inputs":{"noise":["6",0],"guider":["8",0],"sampler":["5",0],"sigmas":["7",0],"latent_image":["9",1]}},
 "11": {"class_type":"VAEDecode","inputs":{"samples":["10",0],"vae":["2",0]}},
 "11a":{"class_type":"VAEDecodeAudio","inputs":{"samples":["10",0],"vae":["2a",0]}},
 "12": {"class_type":"CreateVideo","inputs":{"images":["11",0],"audio":["11a",0],"fps":24,"bit_depth":8}},
 "13": {"class_type":"SaveVideo","inputs":{"video":["12",0],"filename_prefix":"video/MiniMax_H3_00002_style","format":"mp4","codec":"h264"}},
}

def post(obj):
    req=urllib.request.Request(HOST+"/prompt",data=json.dumps(obj).encode(),headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP",e.code,"\n",e.read().decode("utf-8","replace")[:2000]);raise
def get(u):
    with urllib.request.urlopen(u,timeout=30) as r:
        return json.loads(r.read().decode())

print("Submitting (00002-style: AWQ + bypass, 864x480 length=73, with audio)...")
resp=post({"prompt":G,"client_id":"h3-00002style"})
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
            if m[0]=="execution_error":
                print("EXEC ERR:",m[1].get("exception_message"))
                print("\n".join(m[1].get("traceback",[])))
        break
    if st.get("completed") or status=="success": break
else:
    print("TIMEOUT");sys.exit(1)
print("STATUS",status,"elapsed %.1fs"%(time.time()-t0))
print("outputs:",json.dumps(h.get("outputs",{}),ensure_ascii=False)[:1200])
if status!="success": sys.exit(1)