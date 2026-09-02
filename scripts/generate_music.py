# -*- coding: utf-8 -*-
import json, time, urllib.request, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = "http://127.0.0.1:8188"
LOG = r"C:\minimax+comfyUI\generation.log"

def log(m):
    line = time.strftime("%H:%M:%S") + "  " + m
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())

caption = r"""Upbeat modern Chinese Mandopop dance-pop, around 108 BPM, extremely catchy and addictive, bright and energetic but slightly nostalgic. A youthful, warm and charismatic male lead vocal with a clean intimate tone, emotional verses, rhythmic delivery in the pre-chorus, and a powerful sing-along chorus. The melody should be simple, instantly memorable, and easy for listeners to hum after one listen. Use a punchy modern pop drum groove, deep rounded bass, bright synth plucks, warm electric piano, subtle acoustic guitar textures, wide synth pads, rhythmic claps, and a polished commercial pop production. Start with a short atmospheric intro, build tension gradually through the verse and pre-chorus, then explode into a huge melodic chorus with layered backing vocals and octave harmonies. The chorus must contain a highly repetitive earworm hook centered around "今晚别睡 / 别睡 / 再爱一回", with strong rhythmic emphasis and a melody that feels satisfying when repeated. Add tasteful vocal chops, call-and-response backing vocals, short instrumental fills, and a memorable post-chorus instrumental hook. Keep the verses relatively sparse so the chorus feels much bigger. The bridge should briefly strip the drums down, creating emotional anticipation, then return to the final chorus with additional harmonies, ad-libs, and a bigger arrangement. End with a short repeating vocal hook that feels like the song could continue forever. Overall feeling: euphoric, romantic, youthful, warm, carefree, slightly nostalgic, radio-friendly, highly replayable, instantly singable, catchy from the first chorus. Avoid overly complex melodies, excessive vocal runs, dark atmosphere, heavy rock elements, or overly aggressive EDM drops. Prioritize melody, groove, vocal clarity, and an unforgettable chorus."""

lyrics = r"""[Intro]
今晚的风
吹过你的脸
灯亮了一点
心跳快一点
嘿
你看着我
我看着你
这一秒
刚刚好

[Verse 1]
城市的霓虹还没睡
我们沿着街一直追
你说今天不想回
我说那就再走一回
耳机里的歌刚刚好
晚风把烦恼都吹掉
你笑起来的那一秒
整个世界突然变小

[Pre Chorus]
别问明天会怎样
别管时间有多忙
这一刻就在身旁
就让心跳替我们回答

[Chorus]
今晚别睡
别睡 别睡
让月亮陪我们到天黑
今晚别睡
别睡 别睡
有你在身边什么都对
再靠近一点点
再爱一回
再疯狂一点点
也无所谓
今晚别睡
别睡 别睡
我只想和你
一直到天亮都不回

[Post Chorus / Hook]
啦啦啦啦
别睡 别睡
啦啦啦啦
再爱一回
啦啦啦啦
别睡 别睡
今晚我们
不说再见

[Verse 2]
街角的灯忽明忽灭
你的影子落在我肩
我们说过好多誓言
却没有一句需要兑现
你说人生不过几年
何必总想着明天
如果快乐就在眼前
那就把这一秒留给永远

[Pre Chorus]
别问明天会怎样
别管世界有多忙
这一刻就在身旁
就让心跳替我们回答

[Chorus]
今晚别睡
别睡 别睡
让月亮陪我们到天黑
今晚别睡
别睡 别睡
有你在身边什么都对
再靠近一点点
再爱一回
再疯狂一点点
也无所谓
今晚别睡
别睡 别睡
我只想和你
一直到天亮都不回

[Bridge]
如果时间真的会停
我希望停在这里
没有人催
没有人追
只有你和我
还有这一首歌
哦——
就这一晚
就这一晚
让所有遗憾
都走远

[Final Chorus]
今晚别睡
别睡 别睡
让月亮陪我们到天黑
今晚别睡
别睡 别睡
有你在身边什么都对
再靠近一点点
再爱一回
再疯狂一点点
也无所谓
今晚别睡
别睡 别睡
我只想和你
一直到天亮都不回

[Final Hook]
别睡
别睡
今晚别睡
别睡
别睡
再爱一回
别睡
别睡
今晚别睡
你别走
我别回
一直到天亮
都不说再见

[Outro]
今晚别睡……
别睡……
再爱一回……"""

prompt = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_music3_dit_fp16.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors", "type": "minimax"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_music3_dav.safetensors"}},
    "4": {"class_type": "MiniMaxMusic3TextEncode", "inputs": {
        "clip": ["2", 0], "caption": caption, "lyrics": lyrics,
        "seed": 20260818, "max_duration": 240.0, "cfg_scale": 1.0, "top_k": 32 }},
    "5": {"class_type": "EmptyMiniMaxMusic3LatentAudio", "inputs": {"seconds": 240.0, "batch_size": 1}},
    "6": {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 0],
        "latent_image": ["5", 0], "seed": 20260818, "steps": 6, "cfg": 1.0,
        "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0 }},
    "7": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
    "8": {"class_type": "SaveAudioMP3", "inputs": {"audio": ["7", 0], "filename_prefix": "jinwan_bieshui", "quality": "320k"}},
}

log("Submitting MiniMax Music 3 generation...")
try:
    resp = post(HOST + "/prompt", {"prompt": prompt, "client_id": "music-gen"})
except Exception as e:
    log("QUEUE FAILED: %s" % e); raise SystemExit(1)
if "error" in resp:
    log("QUEUE ERROR: " + json.dumps(resp["error"], ensure_ascii=False)); raise SystemExit(1)
pid = resp["prompt_id"]
log("Queued, prompt_id=%s (max 240s). Generating..." % pid)
for i in range(300):
    time.sleep(2)
    try:
        hist = post(HOST + "/history/" + pid, {})
    except Exception:
        continue
    if pid in hist:
        h = hist[pid]
        for nid, out in h.get("outputs", {}).items():
            if "audio" in out:
                for a in out["audio"]:
                    log("DONE audio file: " + a.get("filename", ""))
        st = h.get("status", {})
        if st.get("status_str") == "success":
            log("STATUS: success")
        elif st.get("status_str") == "error":
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    log("EXEC ERROR: " + str(m[1].get("exception_message", ""))[:2000])
            log("STATUS: error")
        break
else:
    log("TIMEOUT waiting")
log("Finished.")
