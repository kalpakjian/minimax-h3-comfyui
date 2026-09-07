# MiniMax H3 + ComfyUI Nightly（本地設置備註）

> 本機環境：`C:\minimax+comfyUI`，已啟用 nightly 分支 + CK-Attention + TRT VAE

## 最近改動

### write_payloads.py：默認 `low_vram=false`

**日期**：2026-09-07  
**檔案**：`scripts/write_payloads.py`（skill 路徑：`C:\Users\princ\.agents\skills\minimax-h3-comfyui\scripts\write_payloads.py`）

- **改動前**：`"low_vram": True`
- **改動後**：`"low_vram": False`
- **原因**：RTX 4090 24GB 在 1344×768 解析度下無需開啟低顯存模式；關閉後性能更穩定，避免不必要的模型 offload。

## 當前驗證流程

1. 確認 `http://127.0.0.1:8188` 存活
2. `write_payloads.py` 生成 seg JSON（含 identity lock + Turbo 6 steps）
3. `run_pipeline.py` 背景執行 T2V → I2V 接龍 → ffmpeg concat
4. 輸出：`output/video/FINAL_<project>.mp4`

## 硬體參數

| 項目 | 數值 |
|------|------|
| GPU | NVIDIA GeForce RTX 4090 24GB |
| 解析度 | 1344 × 768（16:9，1.0 MP）|
| 幀率 | 24 fps |
| 每段長度 | ~10 秒（243 幀）|
| 採樣步數 | 6 steps（Turbo v4）|
| 平均每段耗時 | ~215 秒 |
| VAE 加速 | TRT（TensorRT）|

## 參考

- skill 路徑：`C:\Users\princ\.agents\skills\minimax-h3-comfyui\`
- 報告範例：見 `output/video/FINAL_ct_生成報告.md`
