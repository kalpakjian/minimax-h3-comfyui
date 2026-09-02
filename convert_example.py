# -*- coding: utf-8 -*-
"""Convert example GUI-workflow to API prompt, filling widgets from object_info,
then fix model filenames to what actually exists on disk."""
import json, urllib.request

HOST="http://127.0.0.1:8188"
INFO=json.loads(urllib.request.urlopen(HOST+"/object_info",timeout=30).read().decode())

# filename maps from actual disk listing
FIX={
 "minimax_h3_turbo_4step_ema_ckpt500.safetensors":"minimax_h3_turbo_v4_step600_ema.safetensors",
 "minimax_h3_fl2va_int8_convrot.safetensors":"minimax_h3_fl2va_pruned_int8_convrot.safetensors",
 "qwen3vl_32b_minimax_h3_int8_convrot.safetensors":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
}

wf=json.load(open(r"C:\minimax+comfyUI\ComfyUI\custom_nodes\ComfyUI-MiniMax-H3-Turbo\example_workflows\minimax_h3_t2v_turbo.json",encoding="utf-8"))

# Build ordering of widget inputs per class from object_info
def input_names(class_type):
    spec=INFO.get(class_type,{}).get("input",{})
    names=[]
    for section in (spec.get("required",{}), spec.get("optional",{})):
        for n,_ in section.items():
            names.append(n)
    return names

prompt={}
for node in wf["nodes"]:
    nid=node["id"]; cls=node["type"]
    linked={}
    for link in wf["links"]:
        _,f,fo,t,ti,_=link
        if t==nid:
            linked[ti]=[f,fo]
    entry={"class_type":cls,"inputs":dict(linked)}
    # fill widgets in order matching input_names
    wnames=input_names(cls)
    widgets=node.get("widgets_values") or []
    # node.properties may hold some (e.g. SaveVideo). We'll assign sequentially to non-linked input names.
    wi=0
    for nm in wnames:
        if nm in linked or wi>=len(widgets):
            continue
        entry["inputs"][nm]=widgets[wi]; wi+=1
    # apply fixes
    if cls in ("UNETLoader","VAELoader","CLIPLoader"):
        for nm,v in entry["inputs"].items():
            if isinstance(v,str) and v in FIX:
                entry["inputs"][nm]=FIX[v]
                print(f"node {nid} {cls}: {nm} -> {FIX[v]}")
    prompt[nid]=entry

json.dump(prompt,open(r"C:\minimax+comfyUI\example_api_fixed.json","w",encoding="utf-8"),indent=2)
print("Converted nodes:",len(prompt))
# Show key nodes
for nid in [127,128,119,120,134,135,130,92,131]:
    if nid in prompt:
        print(nid, json.dumps(prompt[nid],ensure_ascii=False)[:400])