# -*- coding: utf-8 -*-
"""Submit bathrobe_api.json and monitor."""
import json, urllib.request, time, sys
HOST="http://127.0.0.1:8188"
G=json.load(open(r"C:\minimax+comfyUI\bathrobe_api.json",encoding="utf-8"))
# JSON keys are strings; ensure link node-ids are ALSO strings so prompt[o_id]
# matches dict keys (JSON round-trip makes int keys strings; links must match).
def str_links(entry):
    for inp,v in list(entry["inputs"].items()):
        if isinstance(v,list) and len(v)==2 and isinstance(v[0],(int,str)):
            entry["inputs"][inp]=[str(v[0]),v[1]]
    return entry
G={str(k)[0:] if not isinstance(k,str) else k: str_links(v) for k,v in G.items()}
def post(obj):
    req=urllib.request.Request(HOST+"/prompt",data=json.dumps(obj).encode(),headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP",e.code,"\n",e.read().decode("utf-8","replace")[:3000]);raise
def get(u):
    with urllib.request.urlopen(u,timeout=30) as r:
        return json.loads(r.read().decode())
print("Submitting...")
resp=post({"prompt":G,"client_id":"bathrobe-5s"})
if "error" in resp:
    print("QUEUE ERR",json.dumps(resp["error"],ensure_ascii=False));sys.exit(1)
pid=resp["prompt_id"];print("prompt_id:",pid)
t0=time.time();timeout=3600
while time.time()-t0<timeout:
    time.sleep(15)
    try: hist=get(HOST+"/history/"+pid)
    except Exception: continue
    if pid not in hist: continue
    h=hist[pid];st=h.get("status",{});status=st.get("status_str","unknown")
    if status=="error":
        for m in st.get("messages",[]):
            if m[0]=="execution_error":print("EXEC ERR:",str(m[1].get("exception_message",""))[:3000])
        break
    if st.get("completed") or status=="success": break
else:
    print("TIMEOUT");sys.exit(1)
print("STATUS",status,"elapsed %.1fs"%(time.time()-t0))
print("outputs:",json.dumps(h.get("outputs",{}),ensure_ascii=False)[:2000])
if status!="success":
    for m in st.get("messages",[]):print("MSG",m[0],str(m[1])[:700])
    sys.exit(1)