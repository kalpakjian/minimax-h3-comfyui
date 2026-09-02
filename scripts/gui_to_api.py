# -*- coding: utf-8 -*-
"""Reliably convert a GUI workflow JSON to an API prompt dict.
For each node: fill inputs from links; then fill non-linked widget inputs
by walking object_info required+optional order and popping widgets_values."""
import json, urllib.request, sys

HOST="http://127.0.0.1:8188"
SRC=r"C:\minimax+comfyUI\ComfyUI\user\default\workflows\bathrobe_bathtub_t2v_5s.json"
OUT=r"C:\minimax+comfyUI\bathrobe_api.json"

INFO=json.loads(urllib.request.urlopen(HOST+"/object_info",timeout=60).read().decode())

def input_order(class_type):
    s=INFO.get(class_type,{}).get("input",{})
    ln=[]
    for sec in (s.get("required",{}),s.get("optional",{})):
        for n in sec: ln.append(n)
    return ln

def input_is_list(class_type):
    s=INFO.get(class_type,{})
    return bool(s.get("is_input_list"))

wf=json.load(open(SRC,encoding="utf-8"))
# map link -> (from_node, slot)
linkmap={}
for L in wf["links"]:
    _,f,fo,t,ti,typ=L
    linkmap[t]=(f,ti,fo)   # to_node -> (from, to_input_pos? we use name)

# key links by from-node output-uses later
# build per-node: {input_name: [from_node, from_slot]}
prompt={}
skip_types=set()
for node in wf["nodes"]:
    nid=node["id"]; cls=node["type"]
    # skip non-executable notes / missing node types
    if cls not in INFO:
        skip_types.add(cls)
        continue
    entry={"class_type":cls,"inputs":{}}
    # connected inputs: node["inputs"] has name+link
    connected={}
    for inp in node.get("inputs",[]):
        nm=inp.get("name"); lk=inp.get("link")
        if lk is not None:
            # find link in links arr by its id
            for L in wf["links"]:
                if L[0]==lk:
                    connected[nm]=[L[1],L[2]]  # [from_node, from_slot]
                    break
    entry["inputs"]=dict(connected)
    # fill widgets for non-connected inputs by order
    order=input_order(cls)
    widgets=list(node.get("widgets_values") or [])
    wi=0
    for nm in order:
        if nm in connected:
            continue
        if wi>=len(widgets):
            break
        entry["inputs"][nm]=widgets[wi]; wi+=1
    prompt[nid]=entry

json.dump(prompt,open(OUT,"w",encoding="utf-8"),indent=2)
print("converted",len(prompt),"nodes ->",OUT)
# sanity print key nodes
for nid in sorted(prompt):
    e=prompt[nid]
    if e["class_type"] in ("MiniMaxH3TurboLoRA","CreateVideo","SaveVideo","MiniMaxH3ImageToVideo","BasicScheduler","ComfyMathExpression","ResolutionSelector"):
        print(nid,e["class_type"],json.dumps(e["inputs"],ensure_ascii=False)[:260])