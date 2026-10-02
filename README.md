# MiniMax H3 × ComfyUI

> 把 **MiniMax H3（海螺）視頻生成模型** 完整跑在 ComfyUI portable 環境下的工作流、生成腳本與操作文檔。
> 含 **角色置換 LoRA**、**Turbo 低步數加速**、**TRT-VAE（TensorRT）加速**，以及原生音頻生成。
>
> ⚠️ 本 repo **只收錄 工作流 / 腳本 / 文檔**，所有模型權重（`*.safetensors`、`*.onnx`、`*.engine`、`*.pth`…）都經 [.gitignore](.gitignore) 排除、**不會上傳**。模型請自行放到 `ComfyUI\models\` 對應子目錄。

---

## 一、這是什麼

這是一套針對 **RTX 4090（24GB VRAM）** 調校過的 ComfyUI 生產配置，主要用途：

- **文生視頻 / 首尾幀生視頻（T2V / I2V）**：MiniMax H3 主模型 `fl2va`
- **參考圖生視頻 / 角色置換（Ref2V / Character Swap）**：H3 主模型 `ref2va` + 角色置換 LoRA
- **長片接龍**：多段 10s 分段生成 → 尾幀銜接 → concat 拼接（已實作 30s、40s、50s 循環片）
- **原生音頻**：H3 一次同時產出畫面 + 音軌（視頻 VAE + 音頻 VAE）
- **配樂生成**：MiniMax Music 3（歌曲）／ ACE-Step 1.5（純器樂、精準秒數）
- **提速**：Turbo LoRA（4–6 步）＋ CK-Attention ＋ TRT-VAE，同條件比 baseline 快 **−96.8%**（1260s → 40s）
- **後製**：標題／壓黑／音效、Real-ESRGAN 2×/4× 超分

---

## 二、硬體與環境

| 項目 | 數值 |
|------|------|
| GPU | NVIDIA GeForce RTX 4090 24GB |
| 系統 | Windows / ComfyUI portable |
| ComfyUI | 0.34.0（根目錄） |
| 啟動環境 | `python_embeded_nightly\`（nightly 分支，與原 `python_embeded\` 分離，可回退） |
| torch | 2.15.0.dev（CUDA 13 nightly） |
| 注意力加速 | `--use-ck-attention`（CK-Attention / comfy-kitchen） |
| VAE 加速 | TRT（TensorRT 11.2，ONNX → engine 預編譯） |
| 原生解析度 | 1344 × 768（16:9，~1.03 MP） |
| 採樣步數 | 4–6 步（Turbo LoRA） |
| 自訂節點 | `ComfyUI-MiniMax-H3-Turbo`、`ComfyUI-H3VAE_TRT`、KJNodes 等 |

**日常啟動（nightly + CK-Attention）：**

```powershell
D:\AI\ComfyUI\python_embeded_nightly\python.exe D:\AI\ComfyUI\main.py --listen 127.0.0.1 --port 8188 --use-ck-attention
```

啟動後瀏覽器開 **http://127.0.0.1:8188**。

---

## 三、模型 & LoRA 清單（各自功能）★

> 位置皆在 `ComfyUI\models\` 下；下表「大小」為本機實測。

### 3.1 LoRA（`models\loras\`）

| 檔案 | 大小 | 功能 | 用在哪 |
|---|---|---|---|
| **`minimax_h3_turbo_v4_step600_ema.safetensors`** | 0.7 GB | **Turbo 加速 LoRA（v4 / step600 / EMA）**：把 H3 主模型蒸餾成**低步數（4–6 步）**即可出片，取代完整 diffusion。配合 `MiniMaxH3TurboLoRA` + `MiniMaxH3TurboSampler`。T2V/I2V 通用。 | 所有 H3 主生成線路 |
| **`minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors`** | 1.8 GB | **Ref2V 4-step Turbo LoRA**：專為「**參考圖→視頻**」(reference-to-video) 路徑的 4 步快速生成，bf16 精度。配合 `MiniMaxH3ReferenceToVideo`。 | 角色置換 / 參考圖生視頻 |
| **`h3_character_swap_pro4500_1000.safetensors`** | 148 MB | **角色置換 LoRA**：把**源片裡的人物替換成目標角色**（保留原始動作／鏡頭）。與 `ref2va` 主模型 + ref2v turbo LoRA 一起用；置換後另做逐 channel gain/offset 最小二乘**校色**對齊源片。 | nightly 角色置換 stage（`_swap_nightly.py`） |

### 3.2 主模型 DiT（`models\diffusion_models\`）

| 檔案 | 大小 | 功能 |
|---|---|---|
| **`minimax_h3_fl2va_pruned_int8_convrot.safetensors`** | 20 GB | **H3 主模型（First/Last-frame → Video + Audio）**：文生視頻、首尾幀生視頻，INT8 量化 pruned。用於 T2V / I2V / loop-bridge（同時餵 first + last 幀做循環銜接）。 |
| **`minimax_h3_ref2va_pruned_int8_convrot.safetensors`** | 20 GB | **H3 主模型（Reference → Video + Audio）**：參考圖生視頻、角色置換，INT8 pruned。配 `MiniMaxH3ReferenceToVideo`。 |
| `minimax_music3_dit_fp16.safetensors` | 4.6 GB | **MiniMax Music 3 DiT**：歌曲／音樂生成模型（給 captions 出旋律，非純器樂精控）。 |
| `qwen_image_2.1_int8_convrot.safetensors` | 6.9 GB | **Qwen-Image 2.1**：文生圖（INT8）。配 `qwen_image_2.1_vae_bf16`。 |
| `acestep_v1.5_turbo.safetensors` | 4.5 GB | **ACE-Step 1.5 Turbo**：音樂生成，支援 `instrumental=true`（純器樂）＋精準 `duration=` 秒數，適合配樂。 |

### 3.3 文本編碼器（`models\text_encoders\`）

| 檔案 | 大小 | 功能 |
|---|---|---|
| **`qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors`** | 14.6 GB | **H3 主文本編碼器（越獄／heretic 版）**：NVFP4 量化、去限制，`CLIPLoader type=minimax`。出自教學文章 https://www.freedidi.com/25246.html 。 |
| **`qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`** | 14.6 GB | **H3 文本編碼器（AWQ 量化版）**：NVFP4 家族的 AWQ 版本。**workflow 中實際指定用此檔**（T2V/I2V 主線路與角色置換都用 awq 版）。 |
| `qwen3vl_8b_bf16.safetensors` | 16.3 GB | **Qwen3-VL 8B（bf16）**：視覺語言編碼器，備用／其他用途。 |
| `minimax_music3_text_encoder_pruned_int8_convrot.safetensors` | 8.6 GB | **Music 3 文本編碼器**：搭配 Music 3 DiT 出音樂。 |
| `qwen_0.6b_ace15.safetensors` | 1.2 GB | **ACE-Step 文本編碼器（0.6B）**：ACE-Step 1.5 用。 |
| `qwen_1.7b_ace15.safetensors` | 3.5 GB | **ACE-Step 文本編碼器（1.7B）**：ACE-Step 1.5 用（較精細）。 |

### 3.4 VAE（`models\vae\`）

| 檔案 | 大小 | 功能 |
|---|---|---|
| **`minimax_h3_video_vae_fp16.safetensors`** | 4.8 GB | **H3 視頻 VAE（fp16，PyTorch 路徑）**：標準視頻 latent 編解碼。T2V/I2V 主線路預設。 |
| `minimax_h3_video_vae_int8_convrot.safetensors` | 2.6 GB | **H3 視頻 VAE（INT8）**：省顯存版，角色置換 pipeline 使用。 |
| **`minimax_h3_audio_vae_fp32.safetensors`** | 0.6 GB | **H3 音頻 VAE（fp32）**：解碼 H3 原生音軌（`VAEDecodeAudio`）。 |
| `minimax_h3_vae_decoder.onnx` + `.onnx.data` | 4.6 GB | **TRT-VAE 解碼器 ONNX 來源**：`.onnx.data` 權重 4.6GB，**不可刪**（刪了無法重編 engine）。 |
| `minimax_h3_vae_decoder.engine` | 4.5 GB | **TRT-VAE 解碼器 TensorRT engine**：針對 4090 預編譯，配 `MiniMaxH3TRTVAELoader`，大幅壓縮解碼延遲。 |
| `minimax_h3_vae_encoder.onnx` | 0.34 GB | **TRT-VAE 編碼器 ONNX**（目前未啟用編碼優化，`encoder=None`）。 |
| `minimax_h3_vae_encoder.engine` | 0.34 GB | **TRT-VAE 編碼器 engine**（預備，未掛上節點）。 |
| `ace_1.5_vae.safetensors` | 0.3 GB | **ACE-Step VAE**。 |
| `minimax_music3_dav.safetensors` | 0.2 GB | **Music 3 VAE**。 |
| `qwen_image_2.1_vae_bf16.safetensors` | 0.6 GB | **Qwen-Image VAE**。 |

### 3.5 超分（`models\upscale_models\`）

| 檔案 | 大小 | 功能 |
|---|---|---|
| `4x-UltraSharp.pth` | 64 MB | **4× 超分（ESRGAN 系）**。腳本另用 `realesr-animevideov3-x2`、`realesrgan-x4plus` 做影片 2×/4× 超分（模型在 `scripts\realesrgan\`，已 gitignore）。 |

### 3.6 模型搭配（哪幾顆一起用）

| 任務 | 主模型 | LoRA | 文本編碼器 | VAE |
|---|---|---|---|---|
| **T2V / I2V（主線路）** | `fl2va_pruned_int8` | `turbo_v4_step600_ema` | `..._awq` | `video_vae_fp16` ＋ `audio_vae_fp32` |
| **loop-bridge（循環片）** | `fl2va_pruned_int8` | `turbo_v4_step600_ema` | `..._awq` | 同上；first + last 幀都餵 `fl2va` |
| **角色置換 / 參考圖生視頻** | `ref2va_pruned_int8` | `h3_character_swap` ＋ `ref2v_turbo_4step` | `..._awq` | `video_vae_int8` ＋ `audio_vae_fp32`（＋ TRT engine） |
| **音樂（歌曲）** | `music3_dit_fp16` | — | `music3_text_encoder` | `music3_dav` |
| **音樂（純器樂，精確秒數）** | `acestep_v1.5_turbo` | — | `qwen_1.7b_ace15`（或 0.6b） | `ace_1.5_vae` |
| **文生圖** | `qwen_image_2.1_int8` | — | `qwen3vl_8b_bf16` | `qwen_image_2.1_vae_bf16` |

> **H3 同時產出畫面＋音頻**：pipeline 內 `VAEDecode`（視頻）＋ `VAEDecodeAudio`（音頻）→ `CreateVideo`（video + audio）→ `SaveVideo`（mp4/h264）。

---

## 四、快速上手

### 方式 A：網頁 UI
1. 啟動伺服器 → 開 http://127.0.0.1:8188
2. `CLIPLoader` 選 `qwen3vl_32b_minimax_h3_nvfp4_awq`（或 heretic 版），`UNETLoader` 選 `minimax_h3_fl2va_pruned_int8_convrot`
3. 載入 `workflows\` 的工作流 → 改提示詞 → Queue

### 方式 B：腳本（API 提交）

腳本向 `http://127.0.0.1:8188/prompt` 提交 workflow JSON，與路徑無關；改 `PROMPT` / `width/height/length` 即可調整：

```powershell
# T2V / I2V
python_embeded_nightly\python.exe scripts\run_h3_fast.py    # 快速版（864x480、6 步、含音頻）
python_embeded_nightly\python.exe scripts\run_h3_min.py     # 最小測試
python_embeded_nightly\python.exe scripts\monitor_h3.py     # 監看進度

# 角色置換 + 校色
powershell -File scripts\run_nightly.ps1 -Swap              # 4 段批次 + 置換+校色
powershell -File scripts\run_nightly.ps1 -SwapOnly          # 只跑置換+校色
powershell -File scripts\run_nightly.ps1 -DryRun -Swap      # 前置檢查（不實際提交）

# 長片接龍（背景非阻塞）
python_embeded_nightly\python.exe scripts\_redo40.py 1      # 從 seg1 起跑 4 段
```

生成結果在 `ComfyUI\output\video\`。

---

## 五、生成管線概覽

**T2V / I2V 主線路**（對應 `workflows\fenghuo_5s_workflow_api.json`）：

```
UNETLoader(fl2va) ──┐
                    ├─> MiniMaxH3TurboLoRA(turbo_v4) > MiniMaxH3TurboSampler > SamplerCustomAdvanced
CLIPLoader(awq) ────┤                                                                               |
VAELoader(video) ───┤                                                                               v
VAELoader(audio) ───┘                    MiniMaxH3ImageToVideo(prompt, W*H, length) > VAEDecode + VAEDecodeAudio
                                                                            > CreateVideo(video+audio) > SaveVideo(.mp4)
```

**長片接龍**：純文生 → ffmpeg 取**尾幀**（`-vf reverse -frames:v 1`）→ 下一段 `first_frame` 銜接 → 重複 → `ffmpeg concat`（UTF-8 無 BOM list，重編碼）。銜接品質用 `scripts\_diff_check.py` 算 RMS（<10 為完美）。

**角色置換**：`LoadVideo` 源片 → `ref2va` + `h3_character_swap` LoRA + `ref2v_turbo_4step` LoRA + `MiniMaxH3TRTVAELoader` → 出 swap 片 → 逐 channel gain/offset 最小二乘**校色**對齊源片 → 重編（音軌保留）。

---

## 六、目錄結構

```
minimax-h3-comfyui\
├── README.md               ← 本檔（主頁面：模型 & LoRA 清單 + 快速上手）
├── README_使用說明.md        ← 完整使用說明、實戰踩坑、長片/後製流程
├── H3_TURBO_SETUP.md        ← nightly + CK-Attention + TRT-VAE 本地設置備註
├── TRT_VAE_安裝報告.md       ← TRT-VAE 安裝 5 步驟 + 實測數據
├── convert_example.py       ← GUI workflow → API prompt 轉換（修正模型檔名）
├── workflows\               ← ComfyUI 工作流（API 格式）
│   ├── fenghuo_5s_workflow_api.json   # T2V/I2V 主線路範例（fl2va + turbo + 音頻）
│   ├── h3_5s_api.json
│   ├── h3_5s_webm_audio.json
│   ├── h3_t2v_5s_workflow.json
│   └── bathrobe_api_fixed.json
├── scripts\                 ← 生成／測速／後製腳本
│   ├── bench_h3.py / bench_h3_trt.py   # 測速（baseline / CK / TRT）
│   ├── run_h3_*.py                    # T2V/I2V 各種跑法
│   ├── run_nightly.ps1               # 一鍵啟動器（-Swap / -SwapOnly / -DryRun）
│   ├── _redo40.py                     # 40s 長片 4 段接龍（背景）
│   ├── _fenghuo30.py / _fenghuo_diff.py  # 30s 接龍 + 銜接驗證
│   ├── _swap_nightly.py / _swap_payload_base.json / _swap_nightly_config.json  # 角色置換+校色
│   ├── _gen_ace_piano50s_3more.py      # ACE-Step 批次純器樂
│   ├── _trt_compile.py                 # TRT engine 一次性編譯
│   └── *.bat / *_merge*.py             # ffmpeg concat / 超分 / 混音後製
└── prompts\                 ← 提示詞範本
    ├── 烽火邊關_war_trailer_v1.txt      # 簡中
    └── 烽火邊關_war_trailer_v1_繁中.txt  # 繁中（分段式 0-4s/4-8s… 每段一鏡頭）
```

> 注意：`ComfyUI\`、`models\`、`python_embeded\*`、`logs\`、`output\`、`input\` 等皆為本機環境產物，**不在本 repo**（已 gitignore）。

---

## 七、相關文檔

- **[README_使用說明.md](README_使用說明.md)** — 完整使用說明、資料夾結構、長片接龍、循環片、配樂、後製、踩坑紀錄（最詳盡）
- **[H3_TURBO_SETUP.md](H3_TURBO_SETUP.md)** — nightly 本地設置、硬體參數、驗證流程
- **[TRT_VAE_安裝報告.md](TRT_VAE_安裝報告.md)** — TRT-VAE 安裝 5 步驟、原理、實測數據、注意事項

---

## 八、注意事項

- **模型不上传**：`.gitignore` 排除所有權重檔；新 clone 需自備模型到 `ComfyUI\models\`。
- **TRT engine 平台專屬**：換 GPU 型號／架構、改 CUDA 版本都需重編 engine（`_trt_compile.py`），舊 engine 不能跨機移動；首次編譯吃大量 VRAM。
- **`.onnx.data` 不可刪**：decoder 權重 4.6GB 在其中，刪了無法重編。
- **雙環境可回退**：nightly 升級只在 `python_embeded_nightly\`，原 `python_embeded\`（torch 2.7.1）未動。
- **TRT 目前只加速解碼**（`encoder=None`）；要連編碼一起加速需另把 encoder 掛上。
- **長片建議 `--lowvram`**：帶 first_frame 的 243 幀長片顯存吃緊時加此旗標。
- **更新 ComfyUI**：根目錄 `git pull` → `python_embeded\python.exe -m pip install -r requirements.txt`。

---

> 最後更新：2026-10-02 ｜ 本機：RTX 4090 24GB ｜ ComfyUI 0.34.0（portable）