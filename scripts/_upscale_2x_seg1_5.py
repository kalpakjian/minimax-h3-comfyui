# -*- coding: utf-8 -*-
"""2x upscale FINAL_seg1_5_loop_piano.mp4 (1344x768 -> 2688x1536)."""
import os, subprocess, sys, glob

SCRIPTS = r"C:\minimax+comfyUI\scripts"
SRC = r"C:\minimax+comfyUI\output\video\FINAL_seg1_5_loop_piano.mp4"
OUT = r"C:\minimax+comfyUI\output\video\FINAL_seg1_5_loop_piano_2x.mp4"
FIN = os.path.join(SCRIPTS, "realesrgan", "frames_in")
FOUT = os.path.join(SCRIPTS, "realesrgan", "frames_out")
ENH = os.path.join(SCRIPTS, "realesrgan", "realesrgan-ncnn-vulkan.exe")
MODEL = "realesr-animevideov3-x2"

def sh(cmd):
    print(">>>", " ".join(cmd)[:180], flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", (r.stderr or "")[-2000:], flush=True)
        raise SystemExit(f"cmd failed rc={r.returncode}")
    return r

for d in (FIN, FOUT):
    if os.path.isdir(d):
        for f in glob.glob(os.path.join(d, "*")):
            try:
                os.remove(f)
            except OSError:
                pass
    os.makedirs(d, exist_ok=True)

sh(["ffmpeg", "-y", "-i", SRC, os.path.join(FIN, "%06d.png")])
n_in = len(glob.glob(os.path.join(FIN, "*.png")))
print("[step1] frames in:", n_in, flush=True)

sh([ENH, "-i", FIN, "-o", FOUT, "-n", MODEL, "-s", "2", "-f", "png"])
n_out = len(glob.glob(os.path.join(FOUT, "*.png")))
print("[step2] frames out:", n_out, flush=True)

sh([
    "ffmpeg", "-y",
    "-framerate", "24", "-i", os.path.join(FOUT, "%06d.png"),
    "-i", SRC,
    "-map", "0:v", "-map", "1:a",
    "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
    "-c:a", "copy", "-shortest", OUT,
])
print("DONE", flush=True)
print("output:", OUT, flush=True)
print("size MB:", round(os.path.getsize(OUT) / 1e6, 2), flush=True)
