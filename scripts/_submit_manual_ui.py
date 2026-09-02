# -*- coding: utf-8 -*-
"""Convert user-saved UI workflow (seg2 manual) -> API payload and submit."""
import json, urllib.request, sys

UI = r"C:\minimax+comfyUI\user\default\workflows\seg2_side_profile_manual.json"
BASE = r"C:\minimax+comfyUI\scripts\_submit_payload_seg2.json"

ui = json.load(open(UI, encoding="utf-8-sig"))
nodes = {n["type"]: n for n in ui["nodes"]}
def w(t): return nodes[t]["widgets_values"]

prompt = w("MiniMaxH3ImageToVideo")[0]
seconds = w("PrimitiveFloat")[0]
ar, mp, mult = w("ResolutionSelector")[:3]
seed = w("RandomNoise")[0]
prefix = w("SaveVideo")[0]
img = w("LoadImage")[0]
clip_name, unet_name, lora_name = w("CLIPLoader")[0], w("UNETLoader")[0], w("MiniMaxH3TurboLoRA")[0]

print("--- user settings ---")
print("seconds:", seconds, "| MP:", mp, "| seed:", seed, "| image:", img)
print("prefix:", prefix)
print("prompt head:", prompt[:120].replace("\n", " "))
# auto-fix obvious typo that would hurt generation
if "baht tub" in prompt:
    prompt = prompt.replace("baht tub", "bathtub")
    print("[fixed typo: baht tub -> bathtub]")

body_file = json.load(open(BASE, encoding="utf-8-sig"))
api = body_file["prompt"] if "prompt" in body_file else body_file
api["131"]["inputs"]["prompt"] = prompt
api["133"]["inputs"]["value"] = float(seconds)
api["115"]["inputs"] = {"aspect_ratio": ar, "megapixels": float(mp), "multiple": int(mult)}
api["129"]["inputs"]["noise_seed"] = int(seed)
api["92"]["inputs"]["filename_prefix"] = prefix
api["128"]["inputs"]["clip_name"] = clip_name
api["127"]["inputs"]["unet_name"] = unet_name
api["134"]["inputs"]["lora_name"] = lora_name
api["140"]["inputs"]["image"] = img
api["131"]["inputs"].pop("last_frame", None)
api["131"]["inputs"]["first_frame"] = ["140", 0]

body = {"prompt": api, "client_id": "cline-submit"}
req = urllib.request.Request("http://127.0.0.1:8188/prompt",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    print("SUBMITTED, prompt_id:", r.get("prompt_id"), "errors:", r.get("node_errors"))
except urllib.error.HTTPError as e:
    print("SUBMIT FAILED:"); print(e.read().decode("utf-8", "replace")[:1500]); sys.exit(1)
