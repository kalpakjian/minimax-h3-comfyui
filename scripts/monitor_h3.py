#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Monitor ComfyUI H3 generation. Poll every 5 min. Exit on: all-done, error, or server down."""
import json, time, urllib.request, sys

HOST = "http://127.0.0.1:8188"
POLL = 300  # 5 min

def get(path):
    with urllib.request.urlopen(HOST + path, timeout=20) as r:
        return json.loads(r.read().decode())

def snapshot():
    try:
        q = get("/queue")
        h = get("/history")
    except Exception as e:
        return {"alive": False, "err": str(e)}
    running = len(q.get("queue_running", []))
    pending = len(q.get("queue_pending", []))
    errors = []
    for pid in list(h.keys())[-5:]:
        st = h[pid].get("status", {})
        if st.get("status_str") == "error":
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    errors.append(m[1].get("exception_message", "")[:300])
    return {"alive": True, "running": running, "pending": pending, "errors": errors}

print("monitor started, poll every %ds" % POLL, flush=True)
while True:
    time.sleep(POLL)
    s = snapshot()
    if not s["alive"]:
        print("SERVER_DOWN: %s" % s["err"], flush=True)
        sys.exit(2)
    if s["errors"]:
        print("ERROR_DETECTED: %s" % " | ".join(s["errors"]), flush=True)
        sys.exit(3)
    if s["running"] == 0 and s["pending"] == 0:
        print("ALL_DONE: queue empty (running=0 pending=0)", flush=True)
        sys.exit(0)
    print("STILL_RUNNING: running=%d pending=%d" % (s["running"], s["pending"]), flush=True)