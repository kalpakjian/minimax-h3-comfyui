# -*- coding: utf-8 -*-
import json, urllib.request
HOST="http://127.0.0.1:8188"
d=json.loads(urllib.request.urlopen(HOST+"/object_info",timeout=30).read().decode())
cv=d.get("CreateVideo",{})
sv=d.get("SaveVideo",{})
print("CreateVideo output types:", json.dumps(cv.get("output_type") or cv.get("output_name") or cv.get("output"), ensure_ascii=False))
print("CreateVideo output_name:", cv.get("output_name"))
print("CreateVideo input required:", json.dumps(cv.get("input",{}).get("required",{}), ensure_ascii=False))
# find how VIDEO is declared
for k in ["CreateVideo","SaveVideo","VAEDecodeAudio"]:
    n=d.get(k,{})
    print("===",k,"===")
    print("  output_name:", n.get("output_name"))
    print("  output_is_list:", n.get("output_is_list"))
    print("  output:", n.get("output"))
    req=n.get("input",{}).get("required",{})
    for inp,spec in req.items():
        if isinstance(spec,list) and len(spec) and isinstance(spec[0],str):
            print("   input",inp,"type:",spec[0])