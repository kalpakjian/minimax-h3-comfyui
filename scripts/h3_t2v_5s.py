# -*- coding: utf-8 -*-
"""Build & submit a 5s MiniMax-H3 T2V turbo workflow via ComfyUI API."""
import json, urllib.request, time, os, copy

HOST = "http://127.0.0.1:8188"
OUT_COMFY = r"C:\minimax+comfyUI\ComfyUI\output"

PROMPT = (
    "Cinematic shot: a sleek silver robot slowly walking through a rain-soaked "
    "neon alley at night, purple and cyan neon signs reflecting on wet pavement, "
    "gentle camera push-in. Atmospheric synthwave music with soft bass pulse, "
    "light rain sound effects. Moody, cinematic, 24fps."
)

def nid(n): return n  # node id

# Build simple linear graph, no math expression (hardcode 124 frames)
nodes = []

def add(type_, cls, attrs, inputs=None):
    node = {"type": type_}
    if cls is not None: node["class_type"] = cls
    node["inputs"] = inputs or {}
    for k,v in attrs.items(): node["inputs"][k] = v
    nodes.append(node)
    return len(nodes)-1

# 0 UNET
unet = add("UNETLoader","UNETLoader",
    {"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"})
# 1 video vae
vvae = add("VAELoader","VAELoader",{"vae_name":"minimax_h3_video_vae_fp16.safetensors"})
# 2 audio vae
avae = add("VAELoader","VAELoader",{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"})
# 3 clip
clip = add("CLIPLoader","CLIPLoader",
    {"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"})
# 4 turbo lora
lora = add("MiniMaxH3TurboLoRA","MiniMaxH3TurboLoRA",
    {"lora_name":"minimax_h3_turbo_v4_step600_ema.safetensors","strength":1.0,"low_vram":False},
    {"model":[unet,"0"]})
# 5 image2video cond + latent (this works for t2v too, prompt only)
cond = add("MiniMaxH3ImageToVideo","MiniMaxH3ImageToVideo",
    {"prompt":PROMPT,"width":1344,"height":768,"length":124},
    {"clip":[clip,"0"],"vae":[vvae,"0"]})
# 6 turbo sampler
sampler = add("MiniMaxH3TurboSampler","MiniMaxH3TurboSampler",{})
# 7 random noise
noise = add("RandomNoise","RandomNoise",{"noise_seed":123456})
# 8 basic scheduler - 4 steps simple, denoise 1
sched = add("BasicScheduler","BasicScheduler",{"scheduler":"simple","steps":4,"denoise":1.0},
    {"model":[lora,"0"]})
# 9 basic guider
guider = add("BasicGuider","BasicGuider",{},
    {"model":[lora,"0"],"conditioning":[cond,"0"]})
# 10 sampler custom advanced
samp = add("SamplerCustomAdvanced","SamplerCustomAdvanced",{},
    {"noise":[noise,"0"],"guider":[guider,"0"],"sampler":[sampler,"0"],
     "sigmas":[sched,"0"],"latent_image":[cond,"1"]})
# 11 vaedecode video
vdec = add("VAEDecode","VAEDecode",{},{"samples":[samp,"0"],"vae":[vvae,"0"]})
# 12 vaedecode audio
adec = add("VAEDecodeAudio","VAEDecodeAudio",{},{"samples":[samp,"0"],"vae":[avae,"0"]})
# 13 create video node (CreateVideo) - need schema
# Let's check: sample uses SaveVideo with VIDEO input directly from VAEDecode? 
# Actually CreateVideo combines images+audio->VIDEO. Let's verify.
# We'll build with a CreateVideo node if present.

# query CreateVideo schema
def object_info():
    with urllib.request.urlopen(HOST+"/object_info", timeout=30) as r:
        return json.loads(r.read().decode())
info = object_info()
print("CreateVideo in info:", "CreateVideo" in info)
if "CreateVideo" in info:
    print(json.dumps(info["CreateVideo"]["input"], ensure_ascii=False)[:400])

workflow = {"": {"inputs": {}, "class_type": ""}}  # placeholder
print("\nBuilt %d nodes" % len(nodes))
# print node list for reference
for i,n in enumerate(nodes): print(i, n["type"])
