# -*- coding: utf-8 -*-
"""Submit a 5s H3 T2V turbo workflow that saves video frames (webp) + audio separately.
Bypasses CreateVideo/SaveVideo VIDEO-type validation entirely."""
import json, urllib.request, time, sys
HOST="http://127.0.0.1:8188"
PROMPT=("Cinematic shot: a sleek silver robot slowly walking through a rain-soaked "
 "neon alley at night, purple and cyan neon signs reflecting on wet pavement, "
 "gentle camera push-in, light rain. Atmospheric synthwave music, soft bass pulse. Moody, cinematic.")

G={
 1:{"class_type":"UNETLoader","inputs":{"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"}},
 2:{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_video_vae_fp16.safetensors"}},
 3:{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"}},
 4:{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"}},
 5:{"class_type":"MiniMaxH3TurboLoRA","inputs":{"model":[1,"0"],"lora_name":"minimax_h3_turbo_v4_step600_ema.safensors" if False else "minimax_h3_turbo_v4_step600_ema.safetensors"}},
}
}
print("placeholder")