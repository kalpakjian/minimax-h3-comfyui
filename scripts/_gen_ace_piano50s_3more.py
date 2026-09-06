# -*- coding: utf-8 -*-
"""Generate 3 more ACE-Step ~50s bathroom piano variants, convert to mp3."""
import os, sys, io, time, subprocess, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ACE_DIR = r"C:\Users\princ\ACE-Step-1.5"
ACE_PY = os.path.join(ACE_DIR, r".venv\Scripts\python.exe")
OUT_DIR = os.path.join(ACE_DIR, "output")
DEST = r"C:\minimax+comfyUI\output"
LOG = r"C:\minimax+comfyUI\logs\ace_piano50s_3more.log"

configs = [
    ("piano_bathroom_50s_v3.toml", "piano_acestep_bathroom_50s_v3"),
    ("piano_bathroom_50s_v4.toml", "piano_acestep_bathroom_50s_v4"),
    ("piano_bathroom_50s_v5.toml", "piano_acestep_bathroom_50s_v5"),
]


def log(m):
    line = time.strftime("%H:%M:%S") + "  " + m
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def existing_flacs():
    return {p: os.path.getmtime(p) for p in glob.glob(os.path.join(OUT_DIR, "*.flac"))}


os.makedirs(os.path.dirname(LOG), exist_ok=True)
open(LOG, "w", encoding="utf-8").close()
log("START 3 more ACE piano 50s")

for cfg, prefix in configs:
    before = existing_flacs()
    log(f"RUN {cfg}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(
        [ACE_PY, "cli.py", "-c", cfg],
        cwd=ACE_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # emoji print may fail on gbk but still exit non-zero sometimes; check new flacs
    log(f"  exit={p.returncode}")
    if p.stderr:
        tail = "\n".join(p.stderr.strip().splitlines()[-8:])
        log("  stderr_tail:\n" + tail)
    time.sleep(1)
    after = existing_flacs()
    new_files = sorted(
        [p for p in after if p not in before or after[p] > before.get(p, 0)],
        key=lambda x: after[x],
    )
    # prefer truly new by mtime last 2 min
    now = time.time()
    new_files = [p for p in new_files if now - after[p] < 180]
    new_files = sorted(new_files, key=lambda x: after[x])
    if not new_files:
        # fallback newest 2
        allf = sorted(glob.glob(os.path.join(OUT_DIR, "*.flac")), key=os.path.getmtime)
        new_files = allf[-2:]
        log(f"  fallback newest flacs: {[os.path.basename(x) for x in new_files]}")
    else:
        log(f"  new flacs: {[os.path.basename(x) for x in new_files]}")

    # take the first new (or both: use first as main for this version)
    src = new_files[-1] if new_files else None
    if not src:
        log("  ERROR no flac")
        continue
    # if 2 new, use the later one as this version's pick (batch often 2)
    if len(new_files) >= 2:
        # save both as prefix and prefix_b
        for i, flac in enumerate(new_files[-2:]):
            tag = prefix if i == 0 else prefix + "b"
            dest = os.path.join(DEST, tag + ".mp3")
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", flac, "-c:a", "libmp3lame", "-b:a", "320k", dest],
                capture_output=True, text=True
            )
            log(f"  mp3 {tag}.mp3 rc={r.returncode} size={os.path.getsize(dest) if os.path.isfile(dest) else 0}")
    else:
        dest = os.path.join(DEST, prefix + ".mp3")
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-c:a", "libmp3lame", "-b:a", "320k", dest],
            capture_output=True, text=True
        )
        log(f"  mp3 {prefix}.mp3 rc={r.returncode} size={os.path.getsize(dest) if os.path.isfile(dest) else 0}")

log("DONE")
