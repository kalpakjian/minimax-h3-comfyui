# -*- coding: utf-8 -*-
"""Concat seg1-4 + seg5_loop (silent video copy), then mix piano_acestep_v1."""
import os, subprocess, sys, io, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = r"C:\minimax+comfyUI"
VID = os.path.join(ROOT, "output", "video")
PIANO = os.path.join(ROOT, "output", "piano_acestep_v1.mp3")
LIST = os.path.join(VID, "_concat_seg1_5.txt")
SILENT = os.path.join(VID, "FINAL_seg1_5_loop_silent.mp4")
OUT = os.path.join(VID, "FINAL_seg1_5_loop_piano.mp4")

# Prefer user's accepted takes
segs = [
    "seg1_ref_00002_.mp4",
    "seg2_ref_00002_.mp4",
    "seg3_ref_00003_.mp4",
    "seg4_ref_00003_.mp4",
]

# latest seg5
seg5s = sorted(glob.glob(os.path.join(VID, "seg5_loop*.mp4")), key=os.path.getmtime)
if not seg5s:
    print("ERROR: no seg5_loop*.mp4 found")
    sys.exit(1)
seg5 = seg5s[-1]
print("seg5:", os.path.basename(seg5), round(os.path.getsize(seg5)/1e6, 2), "MB")

paths = [os.path.join(VID, s) for s in segs] + [seg5]
for p in paths:
    if not os.path.isfile(p):
        print("MISSING", p)
        sys.exit(1)
    print("ok", os.path.basename(p), round(os.path.getsize(p)/1e6, 2), "MB")

# UTF-8 no BOM concat list, forward slashes
lines = [f"file '{p.replace(chr(92), '/')}'" for p in paths]
with open(LIST, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print("list written", LIST)

# concat copy
r = subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", LIST, "-c", "copy", SILENT],
    capture_output=True, text=True
)
if r.returncode != 0:
    print("concat failed, re-encode")
    print(r.stderr[-1500:])
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", LIST,
         "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-an", SILENT],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(r.stderr[-2000:])
        sys.exit(1)
print("silent:", SILENT, round(os.path.getsize(SILENT)/1e6, 2), "MB")

# duration of silent
prob = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=nk=1:nw=1", SILENT],
    capture_output=True, text=True
)
dur = float(prob.stdout.strip())
print("duration", dur)

if not os.path.isfile(PIANO):
    print("ERROR missing piano", PIANO)
    sys.exit(1)

# mix piano, fade out last 3s, shortest = video
fade_st = max(0.0, dur - 3.0)
r = subprocess.run([
    "ffmpeg", "-y",
    "-i", SILENT,
    "-i", PIANO,
    "-filter_complex",
    f"[1:a]atrim=0:{dur},afade=t=out:st={fade_st}:d=3[a]",
    "-map", "0:v", "-map", "[a]",
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
    "-shortest", OUT
], capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-2000:])
    sys.exit(1)

print("OUT", OUT, round(os.path.getsize(OUT)/1e6, 2), "MB")
# probe
pr = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries",
     "format=duration,size:stream=codec_name,width,height,r_frame_rate",
     "-of", "default=noprint_wrappers=1", OUT],
    capture_output=True, text=True
)
print(pr.stdout)
