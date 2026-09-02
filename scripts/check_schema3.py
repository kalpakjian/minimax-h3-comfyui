# -*- coding: utf-8 -*-
import json, urllib.request
HOST="http://127.0.0.1:8188"
d=json.loads(urllib.request.urlopen(HOST+"/object_info",timeout=30).read().decode())
for n in ["SaveVideo","CreateVideo","VAEDecode","BasicScheduler"]:
    node=d.get(n,{})
    req=node.get("input",{}).get("required",{})
    opt=node.get("input",{}).get("optional",{})
    print("===",n,"===")
    print("  required:", [k for k in req])
    print("  optional:", [k for k in opt])
    if n=="SaveVideo":
        print("  full codec:", json.dumps(req.get("codec"), ensure_ascii=False))
        print("  has crf?", "crf" in req or "crf" in opt)