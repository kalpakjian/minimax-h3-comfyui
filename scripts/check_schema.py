# -*- coding: utf-8 -*-
"""Check CreateVideo schema availability."""
import json, urllib.request

HOST = "http://127.0.0.1:8188"
def object_info():
    with urllib.request.urlopen(HOST+"/object_info", timeout=30) as r:
        return json.loads(r.read().decode())
info = object_info()
print("CreateVideo in info:", "CreateVideo" in info)
if "CreateVideo" in info:
    print("CreateVideo input:", json.dumps(info["CreateVideo"]["input"], ensure_ascii=False))
    print("CreateVideo output:", json.dumps(info["CreateVideo"].get("output_name") or info["CreateVideo"].get("output"), ensure_ascii=False))
# SaveVideo schema details
sv = info.get("SaveVideo", {})
print("SaveVideo input:", json.dumps(sv.get("input", {}), ensure_ascii=False)[:600])