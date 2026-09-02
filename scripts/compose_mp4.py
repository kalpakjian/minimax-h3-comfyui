#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Combine split-frame PNGs (from SaveImage) + audio (wav) into a final MP4.
Usage: python compose_mp4.py <frames_dir> <audio.wav> <out.mp4> [fps] [width] [height]"""
import sys, os, glob, subprocess

def main():
    if len(sys.argv) < 4:
        print("usage: compose_mp4.py <frames_dir_or_glob> <audio.ext> <out.mp4> [fps=24] [W] [H]")
        sys.exit(1)
    frames_glob, audio, out = sys.argv[1], sys.argv[2], sys.argv[3]
    fps = int(sys.argv[4]) if len(sys.argv) > 4 else 24
    if os.path.isdir(frames_glob):
        files = sorted(glob.glob(os.path.join(frames_glob, "*.png")))
    else:
        files = sorted(glob.glob(frames_glob))
    if not files:
        print("no frames found for", frames_glob)
        sys.exit(1)
    # H=width/height for scale filter if given
    scale = None
    if len(sys.argv) > 6:
        scale = "scale=%s:%s" % (sys.argv[5], sys.argv[6])
    print("frames:", len(files), "fps:", fps, "audio:", audio)
    # ffmpeg: image sequence + audio
    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i"]
    # use pattern if frames named sequentially 00000/00001...
    # detect pattern
    import re
    if all(re.search(r'\d+', os.path.basename(f)) for f in files):
        first = files[0]; last = files[-1]
        m0 = re.search(r'(\d+)', os.path.basename(first))
        m1 = re.search(r'(\d+)', os.path.basename(last))
        digits = len(m0.group(1))
        # build pattern with %0{digits}d
        base = os.path.lang(os.path.dirname(first)) if False else os.path.dirname(first)
        stem = os.path.basename(first)
        pattern = re.sub(r'\d+', '%%0%dd' % digits, stem, count=1)
        pat = os.path.join(base, pattern)
        cmd.extend([pat])
    else:
        # concat frames via list
        listf = os.path.join(os.path.dirname(out), "_frames.txt")
        with open(listf, "w") as f:
            for fi in files:
                f.write("file '%s'\n" % os.path.abspath(fi).replace("\\","/"))
        cmd.append("-f"); cmd.append("concat"); cmd.append("-safe"); cmd.append("0")
        cmd.append("-i"); cmd.append(listf)
    cmd += ["-i", audio]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps)]
    if scale: cmd += ["-vf", scale]
    cmd += ["-c:a", "aac", "-shortest", out]
    print("RUN:", " ".join(cmd[:18]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-1500:] if r.stdout else "")
    print(r.stderr[-2500:] if r.stderr else "")
    print("exit", r.returncode, "->", out, os.path.getsize(out) if os.path.exists(out) else "MISSING")

if __name__ == "__main__":
    main()