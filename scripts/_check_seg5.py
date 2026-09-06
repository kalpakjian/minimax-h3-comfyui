# -*- coding: utf-8 -*-
import json, urllib.request, io, sys, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pid = "e6ef7ecd-f3c0-4620-9f1c-5c98bd629111"
q = json.loads(urllib.request.urlopen("http://127.0.0.1:8188/queue").read())
print("running", len(q.get("queue_running", [])), "pending", len(q.get("queue_pending", [])))
hist = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{pid}").read())
print("in_hist", pid in hist)
if pid in hist:
    st = hist[pid].get("status", {})
    print("status", st.get("status_str"), "completed", st.get("completed"))
    if st.get("messages"):
        for m in st["messages"][-5:]:
            print("msg", m[0] if isinstance(m, (list, tuple)) else m)
files = sorted(glob.glob(r"C:\minimax+comfyUI\output\video\seg5_loop*.mp4"), key=os.path.getmtime)
for f in files:
    print("file", os.path.basename(f), round(os.path.getsize(f) / 1e6, 2), "MB")
