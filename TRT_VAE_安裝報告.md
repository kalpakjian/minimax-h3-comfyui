# MiniMax-H3 TRT-VAE 安裝獨立報告

> 日期：2026-09-04 ｜ 主機：RTX 4090 24GB ｜ 環境：Windows / ComfyUI portable

## 一、結論摘要

在既有 ComfyUI（MiniMax H3）環境上，加掛 **TensorRT 加速的 VAE 編解碼器**（TRT-VAE），
把編碼/解碼階段從 PyTorch/safetensors 換成「ONNX → 預編譯 TensorRT engine」。
**安裝成功且已實測**：`ck_trt` 比 baseline 縮短 **51.6%**（1260.6s → 610.4s），
換上 nightly torch 後更達 **-96.8%**（40.0s）。

> **2026-10-16 覆核（cu132 / CUDA 13.2）**：舊 engine 仍可載入（TRT 版本、GPU、driver 均未變），但已照第六節重編一次（**76.8 s**）；
> 重編後同條件 warm 執行 **12.45 s**（舊 engine 12.3 s、fp16 VAE 中位 15.75 s）——見第八節。

| 環節 | 前 | 後 |
|---|---|---|
| VAE 解碼 | safetensors fp16（PyTorch） | TensorRT `.engine`（TRT 編譯） |
| 推理框架 | torch 2.7.1+cu126 | torch 2.15.0.dev20260903+cu130 → **2.16.0.dev20261007+cu132**（nightly）/ 2.14.1+cu132（stable）+ TRT 11.2.1.2 |
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

> **2026-10-16 在 cu132 環境重編**（TRT 11.2.1.2，`delete_onnx_after_compile=False`，ONNX 三檔保留）：
> decoder 4,849,917,284 B（07:52:09）、encoder 362,597,804 B（07:52:37），**全程 76.8 s**；
> 舊 engine 先備份到 `models\vae\_engine_bak_cu130_20260904\`。詳見第八節。

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
>
> ⚠️ 本表是 **2026-09-04 舊世代 torch** 的歷史數據（慢路徑下 VAE 解碼占比極高，故 TRT 收益巨大）。
> **cu132 世代的最新跑分見第八節**——同條件已縮到 12–13 s，TRT 的相對優勢同步收斂。

---

## 六、注意事項 / 已知坑

1. **engine 是平台專屬**：換 GPU（型號/架構）、改 CUDA 版本都要重新編譯，舊 engine 不能跨機移動。
   （2026-10-16 實測補充：cu130 → cu132 在 **TRT 版本、GPU、driver 未變**的前提下，舊 engine **仍可反序列化並正常出片**；
   但重編只要 ~77 s，仍建議照編一次，避免日後 TRT/driver 更新時踩雷。）
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
**2026-10-16 覆核新增**：`_trt_compile_cu132.log`、`bench_results_trt.txt`、`bench_results_fp16.txt`

---

## 八、2026-10-16 覆核：cu132（CUDA 13.2）重編實測

### 8.1 背景與三個問題

環境由 `cu130 + torch 2.15.0.dev20260903` 換到 **cu132**（nightly `2.16.0.dev20261007+cu132`、stable `2.14.1+cu132`），
舊 engine 是 2026-09-04 在 cu130 下編的。

| 問題 | 實測答案 |
|---|---|
| cu132 還能不能用 ONNX→TRT？ | **可以**，`MiniMaxH3TRTVAELoader` 照常載入 `.engine` 出片 |
| 舊 engine 一定要重編嗎？ | **不一定要**：TRT 11.2.1.2 / sm_89 / driver 617.42 都沒變，舊 engine 仍可反序列化；但重編只要 76.8 s，已照做 |
| 重編後有沒有變快？ | 與舊 engine **同速**（warm median 12.45 s vs 12.3 s，差異在量測離散內），**沒有退步** |

### 8.2 重編步驟（照第三節 Step 2~5）

1. ONNX 三檔保留不刪（`decoder.onnx` 1.6 MB、`decoder.onnx.data` 4.8 GB、`encoder.onnx` 361 MB）
2. TRT 兩環境都已是 `tensorrt 11.2.1.2`（`pip install --prefer-binary tensorrt` 無需重裝）
3. 先 `POST /free`（`unload_models=true, free_memory=true`）卸載模型：VRAM 22.1 GB → 1.9 GB（避免編譯 OOM）
4. 備份舊 engine → `models\vae\_engine_bak_cu130_20260904\`
5. `$env:COMFY_HOST="http://127.0.0.1:8188"`；`python_embeded\python.exe scripts\_trt_compile.py`
   → job `3969f2a9-…`，server 端 **execution 76.8 s** 完成 decoder + encoder

| engine | 舊（2026-09-04, cu130） | 新（2026-10-16, cu132） |
|---|---|---|
| minimax_h3_vae_decoder.engine | 4,849,896,724 B | 4,849,917,284 B |
| minimax_h3_vae_encoder.engine | 362,517,876 B | 362,597,804 B |

### 8.3 同條件跑分（864×480、73 格、4 步、`--use-ck-attention`、warm）

量測方式：`scripts\bench_h3_trt.py`（TRT-VAE）/ `scripts\bench_h3_fine.py`（fp16 VAE）。
本次起兩支腳本除 `elapsed`（client 端，含排隊與輪詢）外，另記 **`exec`＝server 端 `execution_start`→`execution_success`**（無排隊/輪詢誤差）與 server 的 `pytorch_version`；每輪換 seed（否則 ComfyUI 重用快取）。

| 配置 | torch | exec（warm） | n |
|---|---|---|---|
| **cu132 + TRT-VAE（新 engine）** | 2.16.0.dev20261007+cu132 | 12.2 / 12.3 / 12.6 / 12.7 s（median **12.45 s**） | 4 |
| cu132 + TRT-VAE（舊 cu130 engine） | 同上 | 12.1 / 12.3 / 12.7 s（median **12.3 s**） | 3 |
| cu132 + fp16 VAE（無 TRT） | 同上 | 12.9 / 13.8 / 15.2 / 16.3 / 19.9 / 20.2 s（median **15.75 s**） | 6 |
| 冷啟動參考（模型未載入） | 同上 | TRT 29.1 s、舊 engine 31.3 s | 各 1 |

解讀：

- **TRT 仍較快**：中位數 12.45 s vs 15.75 s（**−21%**）；貼身 interleaved 對照（同一分鐘、只換 VAE 節點）為 12.2 s vs 12.9 s（**−5%**）。
- **優勢已收斂**：舊世代 −51.6% 是因為 torch 2.7.1 慢路徑下解碼占比極高；cu132 + nightly 這一代**解碼已不是瓶頸**，收益回到個位數 %。
- **仍值得開**：engine 4.85 GB < fp16 VAE 5.21 GB，24 GB 卡顯存更省；解碼路徑與 torch 版本脫鉤（本次換 cu132 即證明）。
- **離散偏大**：19–20 s 樣本在 TRT / fp16 兩邊都出現（含一次 TRT 19.2 s，見 `/history`），來源是 24 GB 顯存下 DiT / CLIP / VAE 換入換出，非 VAE 路徑本身——比較請看 median，並用 interleaved 對照。

### 8.4 生產量級跑分（1344×768、243 格、6 步、Turbo v4）

腳本：`scripts\bench_h3_prod.py <label> [seed] [trt|fp16]`——與生產 payload（`scripts\_fenghuo_seg1.json`）同構：
fl2va int8 + turbo LoRA（`low_vram=true`）+ `BasicScheduler` 6 steps + video/audio VAE + `CreateVideo`/`SaveVideo`；
差別只在 `VAEDecode` 的 VAE 來源可切換（TRT engine / fp16 safetensors），seed 每輪換。

| 配置 | torch | exec | n |
|---|---|---|---|
| **TRT-VAE（新 cu132 engine）** | 2.16.0.dev20261007+cu132 | **199.5 s** | 1 |
| fp16 VAE（無 TRT） | 2.16.0.dev20261007+cu132 | 200.9 s | 1 |

- 199.5 s 與既有記錄「~215 s／10 秒段落（1344×768、6 步、TRT VAE）」同級 ⇒ cu132 重編後**生產速度沒有退步**。
- 生產量級下 **TRT 與 fp16 幾乎同速**（199.5 s vs 200.9 s，差 0.7%）：243 格／1344×768 的主成本是 DiT 取樣，解碼只佔小段。
  此時 TRT 的價值是**顯存與路徑穩定**（engine 4.85 GB < fp16 VAE 5.21 GB、解碼不隨 torch 版本變動），不是省時間。
- 生產量級 VRAM 峰值約 **23.5 / 24.5 GB**（`--use-ck-attention`、未加 `--lowvram`）；這也是長片建議 `--lowvram` 的原因。
- TRT 解碼在此量級走節點內建的**時序分塊 + 256 px 空間切塊**（`minimax_trt_node.py`），243 格不必一次進 VRAM。