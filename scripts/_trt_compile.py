# -*- coding: utf-8 -*-
"""Compile MiniMax-H3 TRT VAE engines via ComfyUI API (one-off job).

Usage: python_embeded\\python.exe scripts\\_trt_compile.py
"""
import json, urllib.request, time, sys, os

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")

G = {
 "1": {"class_type": "MiniMaxH3TRTCompilerNode",
       "inputs": {"decoder_onnx": "minimax_h3_vae_decoder.onnx",
                  "encoder_onnx": "minimax_h3_vae_encoder.onnx",
                  "delete_onnx_after_compile": False}},
}

def post(obj):
    req = urllib.request.Request(HOST+"/prompt", data=json.dumps(obj).encode(),
                                 headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code)
        print(e.read().decode("utf-8","replace")[:2000])
        raise

def get(u):
    with urllib.request.urlopen(u, timeout=30) as r:
        return json.loads(r.read().decode())

print("Submitting TRT compile job ...")
resp = post({"prompt": G, "client_id": "trt-compile"})
if "error" in resp:
    print("QUEUE ERR", json.dumps(resp["error"], ensure_ascii=False)); sys.exit(1)
pid = resp["prompt_id"]; print("prompt_id:", pid)
t0 = time.time()
while True:
    time.sleep(15)
    try:
        hist = get(HOST+"/history/"+pid)
    except Exception:
        continue
    if pid not in hist:
        continue
    h = hist[pid]; st = h.get("status", {})
    status = st.get("status_str", "unknown")
    if status == "error":
        for m in st.get("messages", []):
            if m[0] == "execution_error":
                print("EXEC ERR:", m[1].get("exception_message"))
                print("\n".join(m[1].get("traceback", [])))
        sys.exit(1)
    if st.get("completed") or status == "success":
        print("COMPILE DONE in %.1fs" % (time.time()-t0))
        break
