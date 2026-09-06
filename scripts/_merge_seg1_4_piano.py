# -*- coding: utf-8 -*-
"""Merge seg1-4 (silent video) + piano_acestep_v1.mp3 into FINAL_40s_piano.mp4.
Writes UTF-8 (no BOM) concat list, then runs ffmpeg concat + audio overlay.
"""
import os, subprocess, sys
root = r"C:\minimax+comfyUI\output\video"
parts = ["seg1_ref_00002_.mp4", "seg2_ref_00002_.mp4", "seg3_ref_00003_.mp4", "seg4_ref_00003_.mp4"]
piano = r"C:\minimax+comfyUI\output\piano_acestep_v1.mp3"
out = root + r"\FINAL_seg1_4_piano.mp4"
list_file = root + r"\_concat_seg1_4.txt"

# total video duration
import subprocess
def dur(p):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1", root+"\\"+p], capture_output=True, text=True)
    return float(r.stdout.strip())
total = sum(dur(p) for p in parts)
print("total video duration:", total)

# write UTF-8 no-BOM concat list
with open(list_file, "w", encoding="utf-8") as f:
    for p in parts:
        f.write(f"file '{root}\\{p}'\n")
print("concat list:", list_file)

# ffmpeg: concat video, then mux piano trimmed to total with fade-out
cmd = [
    "ffmpeg","-y",
    "-f","concat","-safe","0","-i",list_file,
    "-i",piano,
    "-filter_complex",
    f"[1:a]atrim=0:{total:.3f},aresample=48000,afade=t=out:st={total-3:.3f}:d=3[aout]",
    "-map","0:v","-map","[aout]",
    "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",
    out,
]
print("running ffmpeg concat+music ...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("returncode:", res.returncode)
if res.returncode != 0:
    print("STDERR:", res.stderr[-2000:])
else:
    print("OK output:", out)
    print("size MB:", round(os.path.getsize(out)/1e6, 2))