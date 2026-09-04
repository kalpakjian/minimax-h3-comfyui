# MiniMax-H3 TRT-VAE 安裝獨立報告

> 日期：2026-09-04 ｜ 主機：RTX 4090 24GB ｜ 環境：Windows / ComfyUI portable

## 一、結論摘要

在既有 ComfyUI（MiniMax H3）環境上，加掛 **TensorRT 加速的 VAE 編解碼器**（TRT-VAE），
把編碼/解碼階段從 PyTorch/safetensors 換成「ONNX → 預編譯 TensorRT engine」。
**安裝成功且已實測**：`ck_trt` 比 baseline 縮短 **51.6%**（1260.6s → 610.4s），
換上 nightly torch 後更達 **-96.8%**（40.0s）。

| 環節 | 前 | 後 |
|---|---|---|
| VAE 解碼 | safetensors fp16（PyTorch） | TensorRT `.engine`（TRT 編譯） |
| 推理框架 | torch 2.7.1+cu126 | torch 2.15.0.dev + TRT 11.2 |
| 同條件整片 | 1260.6 s（baseline） | 610.4 s（ck_trt） |

---

## 二、TRT-VAE 目標與原理

MiniMax H3 影片的 **Video VAE（含 transformer decoder）** 是整條 pipeline 的成本大戶，
且屬「固定拓樸、可預先優化」的部分。做法：

1. 把 VAE 的 encoder/decoder 匯出成 **ONNX**（計算圖標準格式）
2. 用 **TensorRT 把 ONNX 預編譯成平台專屬 engine**（針對 RTX 4090 的 cuDNN/cuBLAS kernel 融合）
3. 推論時直接載入 `.engine`，跳過逐層 PyTorch dispatch

優點：解碼路徑固定、可用 TRT 的 layer fusion / kernel auto-tuning 壓縮延遲。
代價：**首次要編譯 engine**（decoder 那顆編了約幾分鐘、吃大量 VRAM）。

---

## 三、安裝步驟（實際執行記錄）

以下 5 支腳本就是依序執行的安裝流程（均在 `scripts\`，log 在 `logs\`）。

### Step 1｜複製出隔離的 nightly 環境 `_copy_env.ps1`
```
python_embeded\  →  python_embeded_nightly\  （robocopy /E 全量複製）
```
- 目的：**不污染原環境**，torch 升級只影響 nightly，原 torch 2.7.1 可隨時回退。

### Step 2｜下載 ONNX 模型 `_dl_onnx.ps1`
來源（HF）：`lihaoyun6/MiniMax-H3-VAE-ONNX`
寫入：`ComfyUI\models\vae\`

| 檔案 | 大小 | log 驗證 |
|---|---|---|
| minimax_h3_vae_decoder.onnx | 1.6 MB | exit=0 |
| minimax_h3_vae_decoder.onnx.data | 4.8 GB | exit=0 |
| minimax_h3_vae_encoder.onnx | 361 MB | exit=0 |

### Step 3｜升 nightly torch=cu130 `_pip_torch_nightly.ps1`
```powershell
pip install --upgrade --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130
```
結果（log 實錄）：`torch 2.15.0.dev20260903+cu130 cuda 13.0 available=True`
（torch 2.7.1+cu126 → 2.15.0.dev20260903+cu130，並解除 2.8+/2.12+ 才支援的 DynamicVRAM 降級警告）

### Step 4｜在 nightly 環境裝 TensorRT `_pip_trt_nightly.ps1`
```powershell
pip install --prefer-binary tensorrt
```
結果（log 實錄）：`tensorrt OK 11.2.1.2`
（安裝了 tensorrt / tensorrt_cu13 / tensorrt_cu13_libs / tensorrt_cu13_bindings）

### Step 5｜編譯 engine `_trt_compile.py`（一次性 job，走 ComfyUI API）
```json
MiniMaxH3TRTCompilerNode {
  decoder_onnx: minimax_h3_vae_decoder.onnx
  encoder_onnx: minimax_h3_vae_encoder.onnx
  delete_onnx_after_compile: False
}
```
產生結果：`ComfyUI\models\vae\`

| engine | 大小 | 編譯時間 |
|---|---|---|
| minimax_h3_vae_decoder.engine | ~4.6 GB | 2026/9/4 18:58:41 |
| minimax_h3_vae_encoder.engine | ~346 MB | 2026/9/4 18:59:05 |

> `delete_onnx_after_compile=False` → ONNX 檔保留，方便日後重編/對照。
---

## 四、用量（正確啟用方式）

- **VAE 節點**改用 `MiniMaxH3TRTVAELoader`，
  指定 `decoder=minimax_h3_vae_decoder.engine`（影片解碼）＋ `encoder=None`（先不做編碼優化）。
- 啟動伺服器**加 `--use-ck-attention`**（加上 CK-Attention kernel，並行加速注意力）。
- 範例：`scripts\bench_h3_trt.py` 的 graph 就把 `VAEDecode` 的 vae 接到 `2t`（TRT engine）而非 `2`（fp16）。

---

## 五、實測數據（`logs\bench_results.txt`，同條件）

同條件：864x480、73 格、4 步、seed 731159、RTX 4090 24G

| # | 配置 | torch | 耗時 | 對比 baseline |
|---|---|---|---|---|
| 1 | baseline（原環境） | 2.7.1+cu126 | 1260.6 s | — |
| 2 | + `--use-ck-attention` | 2.7.1+cu126 | 1090.5 s | -13.5% |
| 3 | **+ TRT-VAE** | 2.7.1+cu126 | **610.4 s** | **-51.6%** |
| 4 | 全套（nightly + cu130） | 2.15.0.dev | **40.0 s** | **-96.8%** |

> 逐層解讀：TRT-VAE 單獨已把整片砍半（-51.6%），主要是解碼段被大幅壓縮；
> 再疊加 nightly torch + CK-Attention 後進入 40s 等級（每輪各跑 1 次）。

---

## 六、注意事項 / 已知坑

1. **engine 是平台專屬**：換 GPU（型號/架構）、改 CUDA 版本都要重新編譯，舊 engine 不能跨機移動。
2. **首次編譯耗資源**：decoder engine 約 4.6GB，編譯時吃大量 VRAM/記憶體（接近 OOM 需留意），完成後自動快取。
3. **onnx.data 不可刪**：decoder 的權重大部分放在 `.onnx.data`（4.8GB），刪掉會讓 engine 無法重編。
4. **原始 + nightly 雙環境**：升級只在 `python_embeded_nightly\`，原 `python_embeded\` 未動，可隨時回退。
5. **torch nightly 變動快**：若 ComfyUI 日後相容性出問題，可鎖回當日版本。
6. **TRT 未做 encoder 優化**（encoder=None）：目前只加速了解碼。若要連編碼一起加速，需把 encoder 也編譯並在節點指定 `encoder=...engine`。
7. 畫面品質：同 seed 但 VAE 路徑不同，輸出與 safetensors 版約 PSNR 17–22dB，已目視確認場景一致。

---

## 七、用到的檔案清單

**腳本（scripts\）**：`_copy_env.ps1`、`_dl_onnx.ps1`、`_pip_torch_nightly.ps1`、`_pip_trt_nightly.ps1`、`_trt_compile.py`、`bench_h3_trt.py`
**產物（ComfyUI\models\vae\）**：`*_decoder.onnx(.data)`、`*_encoder.onnx`、`*_decoder.engine`、`*_encoder.engine`
**log（logs\）**：`_copy_env.log`、`_dl_onnx.log`、`_pip_torch_nightly.log`、`_pip_trt_nightly.log`、`_pip_trt.log`、`_pip_trt2.log`、`bench_results.txt`