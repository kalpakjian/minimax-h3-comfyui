# -*- coding: utf-8 -*-
"""Test submit partial graphs to isolate the failing node. --phase 1..4"""
import json, urllib.request, sys
HOST="http://127.0.0.1:8188"
PROMPT="test robot"

BASE={
 1:{"class_type":"UNETLoader","inputs":{"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"}},
 2:{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_video_vae_fp16.safetensors"}},
 3:{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"}},
 4:{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"}},
 5:{"class_type":"MiniMaxH3TurboLoRA","inputs":{"model":[1,"0"],"lora_name":"minimax_h3_turbo_v4_step600_ema.safetensors","strength":1.0,"low_vram":False}},
 6:{"class_type":"MiniMaxH3TurboSampler","inputs":{}},
 7:{"class_type":"RandomNoise","inputs":{"noise_seed":20240831}},
 8:{"class_type":"BasicScheduler","inputs":{"model":[5,"0"],"scheduler":"simple","steps":4,"denoise":1.0}},
 9:{"class_type":"BasicGuider","inputs":{"model":[5,"0"],"conditioning":[11,"0"]}},
 10:{"class_type":"SamplerCustomAdvanced","inputs":{"noise":[7,"0"],"guider":[9,"0"],"sampler":[6,"0"],"sigmas":[8,"0"],"latent_image":[11,"1"]}},
 11:{"class_type":"MiniMaxH3ImageToVideo","inputs":{"clip":[4,"0"],"vae":[2,"0"],"prompt":PROMPT,"width":1344,"height":768,"length":124}},
 12:{"class_type":"VAEDecode","inputs":{"samples":[10,"0"],"vae":[2,"0"]}},
 13:{"class_type":"VAEDecodeAudio","inputs":{"samples":[10,"0"],"vae":[3,"0"]}},
}

def submit(G,label):
    req=urllib.request.Request(HOST+"/prompt",data=json.dumps({"prompt":G,"client_id":"iso-%s"%label}).encode(),headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            d=json.loads(r.read().decode());print("## %s OK queued"%label);return d["prompt_id"]
    except urllib.error.HTTPError as e:
        body=e.read().decode("utf-8","replace")
        print("## %s FAILED" % label)
        print(body[:1200]);return None

# Phase A: just latent gen + vaedecode video only (no CreateVideo/SaveVideo)
Ga=dict(BASE)
sub=submit(Ga,"A_video_decode_only")
if sub: print("A queued id",sub)

# Phase B: add VAEDecodeAudio
Gb=dict(BASE)
sub=submit(Gb,"B_with_audio_decode")

# Phase C: add CreateVideo
Gc=dict(BASE)
Gc[14]={"class_type":"CreateVideo","inputs":{"images":[12,"0"],"audio":[13,"0"],"fps":24.0,"bit_depth":8}}
submit(Gc,"C_create_video")

# Phase D: add SaveVideo
Gd=dict(Gc)
Gd[15]={"class_type":"SaveVideo","inputs":{"video":[14,"0"],"filename_prefix":"video/MiniMax_H3_5s","format":"auto","codec":{"key":"auto","inputs":{"required":{}}}}}
submit(Gd,"D_save_video")