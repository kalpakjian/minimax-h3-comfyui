# MiniMax H3 + ComfyUI Nightly（本地設置備註）

> 本機環境：`D:\AI\ComfyUI`，nightly 分支 + CK-Attention + TRT VAE
> **狀態（2026-10-08 起）：nightly 通道，stable 品質——已驗證為正式生產環境。**

## 2026-10-16：cu132 世代 TRT engine 重編 + 最新跑分

**結論**：cu132（nightly `2.16.0.dev20261007+cu132`）下 **ONNX→TRT 照用**。舊 cu130 engine 其實仍可載入（TRT 版本/GPU/driver 未變），
但照 `TRT_VAE_安裝報告.md` 重編一次（**76.8 s**）後同速無退步，故 engine 已更新為 cu132 版。

**最新跑分**（864×480、73 格、4 步、`--use-ck-attention`、warm、server 端 `exec`）：

| 配置 | exec | n |
|---|---|---|
| TRT-VAE（新 cu132 engine） | median **12.45 s**（12.2–12.7） | 4 |
| TRT-VAE（舊 cu130 engine） | median **12.3 s**（12.1–12.7） | 3 |
| fp16 VAE（無 TRT） | median **15.75 s**（12.9–20.2） | 6 |
| 冷啟動參考（含模型載入） | 29.1 s（TRT） | 1 |

- 舊表 `1260.6 s → 40.0 s` 是 torch 2.7.1 / cu130 世代的數字；cu132 世代同條件已到 **12–13 s warm / ~29 s cold**。
- TRT 相對優勢由 **−51.6%** 收斂到個位數 %（interleaved 12.2 s vs 12.9 s）：cu132 + nightly 下**解碼已非瓶頸**；
  但 engine 4.85 GB < fp16 VAE 5.21 GB，24 GB 卡仍值得開。
- 量測方式升級：`bench_h3_trt.py` / `bench_h3_fine.py` 現在同時記 `elapsed`（client，含排隊）與 **`exec`（server 端 execution_start→success，無排隊/輪詢誤差）**，
  並輸出 server 的 `pytorch_version`；**每輪務必換 seed**（否則 ComfyUI 重用上游快取）。
- 詳細過程（備份、`POST /free`、engine 新舊大小）見 `TRT_VAE_安裝報告.md` 第八節。

## 2026-10-08：nightly 正名為生產環境

**結論**：`python_embeded_nightly`（torch 2.16.0.dev20261007+cu132，CUDA 13.2，cuDNN 92600）即日起為正式生產環境；
`python_embeded`（stable，torch 2.14.1+cu132，已修復）保留作備援。

**依據**：

| 項目 | 證據 |
|---|---|
| A/B 同速 | 864×480、73 幀、Turbo 4 steps、含音訊，各 3 次取 median：stable **12.1s** vs nightly **12.0s**（差異 −0.8%，屬噪聲） |
| 獨挑大樑 | stable 環境因 torchvision 損壞（0.22.1+cu126 vs torch 2.14.1+cu132）**無法啟動**，近期所有生產（含今晨 redo40）皆由 nightly 執行 |
| 長期穩定 | nightly 已承載烽火邊關等多段生產（~215s/10s 段，Turbo 6 steps + TRT VAE），無異常 |

**附帶修復**：
- `python_embeded`：torchvision `0.22.1+cu126` → `0.29.1+cu132`（配對 torch 2.14.1），現可正常啟動，列為備援
- torchaudio（2.7.1+cu126）在 stable 仍損壞，但 ComfyUI 未使用它（音訊輸出正常），暫不處理
- 新增 `scripts/bench_h3_fine.py`（1 秒解析度 + seed 參數防執行快取）：每次測試必須換 seed，否則 ComfyUI 重用上游節點輸出，測到的是快取值

**注意**：通道仍是 nightly（PyTorch 官方定義為預覽版）；但此 pin 定的 build 在本工作負載上已驗證等速且長期穩定，故升格為生產預設。將來更新 nightly build 後需重跑 A/B。

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
| torch（生產） | 2.16.0.dev20261007+cu132（nightly）／2.14.1+cu132（stable 備援） |
| TRT | 11.2.1.2；engine 2026-10-16 於 cu132 重編（76.8 s） |
| 解析度 | 1344 × 768（16:9，1.0 MP）|
| 幀率 | 24 fps |
| 每段長度 | ~10 秒（243 幀）|
| 採樣步數 | 6 steps（Turbo v4）|
| 平均每段耗時 | ~215 秒 |
| VAE 加速 | TRT（TensorRT）|

## 參考

- skill 路徑：`C:\Users\princ\.agents\skills\minimax-h3-comfyui\`
- 報告範例：見 `output/video/FINAL_ct_生成報告.md`
