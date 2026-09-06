# -*- coding: utf-8 -*-
"""Submit seg5 loop bridge: first_frame=seg4 last, last_frame=seg1 first.
Silent audio; 1344x768, 10s, 6 steps, low_vram=True. Direct API, no GUI.
"""
import json, urllib.request, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROMPT = (
    "Continuous seamless loop bridge. Start exactly from the opening frame: "
    "the same young japanese woman standing beside the white bathtub, "
    "plush white towel wrapped around her, warm golden bathroom light. "
    "She slowly turns and walks back through the elegant beige-tiled bathroom, "
    "steam fading, soft warm light shifting gently, and gradually settles into "
    "the exact pose and framing of the final target frame — the same woman at "
    "the start of the sequence, same outfit, same composition, ready to loop. "
    "Camera holds steady warm frontal framing, face and body consistent, "
    "cinematic, fluid relaxed motion, no jump cuts. "
    "Do not reset identity; morph continuously from the first frame into the last frame.\n\n"
    "Audio: silent."
)

FIRST = "seg4_last_frame.png"
LAST = "seg1_first_frame.png"
LENGTH = 243
SEED = 20240906
PREFIX = "video/seg5_loop"

api = {
    "119": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
    "120": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
    "121": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["125", 0], "vae": ["120", 0]}},
    "122": {"class_type": "VAEDecode", "inputs": {"samples": ["125", 0], "vae": ["119", 0]}},
    "124": {"class_type": "BasicScheduler", "inputs": {"model": ["134", 0], "scheduler": "simple", "steps": 6, "denoise": 1}},
    "125": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["129", 0], "guider": ["126", 0], "sampler": ["135", 0], "sigmas": ["124", 0], "latent_image": ["131", 1]}},
    "126": {"class_type": "BasicGuider", "inputs": {"model": ["134", 0], "conditioning": ["131", 0]}},
    "127": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
    "128": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
    "129": {"class_type": "RandomNoise", "inputs": {"noise_seed": SEED}},
    "130": {"class_type": "CreateVideo", "inputs": {"images": ["122", 0], "audio": ["121", 0], "fps": 24, "bit_depth": 8}},
    "131": {
        "class_type": "MiniMaxH3ImageToVideo",
        "inputs": {
            "clip": ["128", 0],
            "vae": ["119", 0],
            "width": 1344,
            "height": 768,
            "length": LENGTH,
            "prompt": PROMPT,
            "first_frame": ["140", 0],
            "last_frame": ["141", 0],
        },
    },
    "134": {
        "class_type": "MiniMaxH3TurboLoRA",
        "inputs": {
            "model": ["127", 0],
            "lora_name": "minimax_h3_turbo_v4_step600_ema.safetensors",
            "strength": 1,
            "low_vram": True,
        },
    },
    "135": {"class_type": "MiniMaxH3TurboSampler", "inputs": {}},
    "140": {"class_type": "LoadImage", "inputs": {"image": FIRST}},
    "141": {"class_type": "LoadImage", "inputs": {"image": LAST}},
    "92": {
        "class_type": "SaveVideo",
        "inputs": {
            "video": ["130", 0],
            "filename_prefix": PREFIX,
            "format": "auto",
            "codec": "auto",
        },
    },
}

body = {"prompt": api, "client_id": "seg5_loop"}
req = urllib.request.Request(
    "http://127.0.0.1:8188/prompt",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    print("SUBMITTED prompt_id:", r.get("prompt_id"))
    if r.get("node_errors"):
        print("node_errors:", json.dumps(r["node_errors"], ensure_ascii=False))
except urllib.error.HTTPError as e:
    print("SUBMIT FAILED:")
    print(e.read().decode("utf-8", "replace")[:2000])
    sys.exit(1)

print("first_frame:", FIRST)
print("last_frame:", LAST)
print("prefix:", PREFIX, "| 1344x768 | 10s | steps=6 | low_vram=True | seed:", SEED)
