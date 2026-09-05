# MiniMax H3 + ComfyUI 使用說明

# MiniMax H3 提速更新報告（2026-09-04）

對照松音 FB 貼文的三個提速項目，全部完成並實測。

## 基準測試結果（同條件：864x480、73 格、4 步、seed 731159、RTX 4090 24G）

| # | 配置 | torch | 耗時 | 對比基準 |
|---|------|-------|------|---------|
| 1 | baseline（原環境） | 2.7.1+cu126 | 1260.6 s | — |
| 2 | + `--use-ck-attention` | 2.7.1+cu126 | 1090.5 s | **-13.5%** |
| 3 | + TRT-VAE | 2.7.1+cu126 | 610.4 s | **-51.6%** |
| 4 | 全套（nightly 環境） | 2.15.0.dev20260903+cu130 | **40.0 s** | **-96.8%** |

> 每輪各跑 1 次。輸出影片已抽帧目視檢查，均為正常畫面（非黑屏/壞圖）。

## 做了什麼

1. **獨立 nightly 環境**：`python_embeded_nightly\`（複製自原 python_embeded，未動原環境）
   - torch 2.15.0.dev20260903+cu130（CUDA 13 nightly）
   - 解除了舊 torch 的 DynamicVRAM 降級警告（2.8+/2.12+ 才支援）
2. **`--use-ck-attention`**：CK-Attention（comfy-kitchen 0.2.31 原本就裝好，只差啟動旗標）
3. **TRT-VAE**：custom_nodes\ComfyUI-H3VAE_TRT + ONNX encoder/decoder
   （models\vae\minimax_h3_vae_*.onnx），首次使用會自動編譯並快取 TensorRT engine

## 日常啟動方式（改用這個）

```
C:\minimax+comfyUI\python_embeded_nightly\python.exe C:\minimax+comfyUI\main.py --listen 127.0.0.1 --port 8188 --use-ck-attention
```

- TRT-VAE：workflow 裡 VAE 解碼節點改用 MiniMaxH3TRTVAE 節點（參考 scripts\bench_h3_trt.py）
- 原環境 `python_embeded\` 完全未動，可隨時回退

## 注意事項

- torch nightly 每日更新，若日後 ComfyUI 更新有相容問題，可鎖回當日版本
- PSNR 對比各輪輸出約 17-22dB：同 seed 但 attention kernel / VAE 解碼路徑不同，畫面有差異屬正常，已目視確認場景一致
- 測速腳本：scripts\bench_h3.py（baseline/ck）、bench_h3_trt.py（TRT），結果記錄於 logs\bench_results.txt

# MiniMax H3 40 秒長片重作記錄（2026-09-05）

用 nightly+TRT 配置把 4 段接龍長片改用**模型原生解析度**重作，並解決先前解析度不一致的問題。

## 這次做了什麼

1. **解析度統一為 1344×768（原生 16:9，~1.03 MP）**
   - 先前 seg1 用 864×480、seg2~4 用 736×416 混用，合併需縮放
   - 查證 `MiniMaxH3ImageToVideo` 節點預設即 1344×768，是最貼近模型訓練分布的解析度
   - 4 段 payload 的 `ResolutionSelector(node 115)` 全部設為 `megapixels=1.0`、`aspect_ratio=16:9`、`multiple=64`

2. **提示詞統一**：seg1/seg2 的 "wearing nothing" → "wearing bikini"；4 段皆改為靜音（No audio）

3. **非阻塞長任務執行**（解決先前 seg2「看似卡住」問題）
   - 根因：前台跑 `_redo40.py` 會被工具 30 秒逾時殺掉，但 ComfyUI 伺服器繼續跑，導致 `redo40_results.txt` 停在 submitting
   - 解法：用 `Start-Process -RedirectStandardOutput/-RedirectStandardError -PassThru` 背景啟動，改輪詢 `/history/{prompt_id}` 或 `logs\redo40_results.txt`，不再前台等待

## 長片重作實測（1344×768、6 步、243 幀/段、RTX 4090）

| 段落 | 耗時 | 產出 |
|---|---|---|
| seg1 | 195 s | MiniMax_H3_10s_00018_.mp4 |
| seg2 | 210 s | MiniMax_H3_10s_00019_.mp4 |
| seg3 | 210 s | MiniMax_H3_10s_00020_.mp4 |
| seg4 | 210 s | MiniMax_H3_10s_00021_.mp4 |

- 4 段無縫 concat 合併 + 混入鋼琴配樂 → `output\video\FINAL_40s_1344.mp4`（1344×768，~12.4 MB，40.5 s）
- 解析度提升到原生後每段採樣 ~25s/it，4 段約 12 分鐘（對比 736×416 每段 60s，但換取完整畫質）

## 執行方式（長片接龍，背景 + 非阻塞）

```powershell
# 從指定段落起跑（1 = 全部 4 段），背景執行
$out='logs\seg_run.log'; $err='logs\seg_err.log'
$p = Start-Process 'C:\minimax+comfyUI\python_embeded_nightly\python.exe' `
  -ArgumentList '"C:\minimax+comfyUI\scripts\_redo40.py" 1' `
  -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
# 輪詢 logs\redo40_results.txt 直到出現 ALL SEGMENTS DONE，或查 /history/{prompt_id}
```

## 注意
- 解析度升到 1344×768 後每段 60s（736×416）→ ~210s（原生），換取完整畫質
- 合併用無 BOM list 檔：PowerShell `Set-Content -Encoding utf8` 會加 BOM 讓 ffmpeg concat 報錯，改用 `[System.IO.File]::WriteAllLines` 寫 UTF8 無 BOM
- 完成後中間產物（_noL_*.mp4、segN_last_frame.png）可刪
---


> 最後更新：2026-09-05
> 本機配置：RTX 4090 (24GB VRAM) ｜ ComfyUI 0.34.0（portable 版）

## 一、這個資料夾是什麼？

這是一套 **portable 版 ComfyUI**，已完整安裝 **MiniMax H3 視頻生成模型**
（含越獄/去限制版文本編碼器，出自教學文章：https://www.freedidi.com/25246.html），
並已成功生成過視頻。

## 二、資料夾結構（一看就懂版）

```
C:\minimax+comfyUI\
├── ComfyUI\            ← ★ 程式主體（千萬不要改名/搬動內部！）
│   ├── models\         ← ★ 所有模型都在這裡
│   │   ├── text_encoders\      文本編碼器（含越獄版）
│   │   ├── diffusion_models\   H3 主模型
│   │   ├── vae\                視頻/音頻 VAE
│   │   └── loras\              Turbo 加速 LoRA
│   ├── custom_nodes\   自訂節點（ComfyUI-MiniMax-H3-Turbo、KJNodes）
│   ├── input\  output\ 輸入圖 / 生成結果輸出
│   └── user\  temp\    使用者設定與暫存
├── scripts\            ← 我自己寫的生成腳本（*.py）
├── workflows\          ← 我的工作流 JSON（API 格式）
├── logs\               ← 生成日誌
├── .backup_h3_preupdate\ ← 更新前備份（新版穩定後可刪除）
├── python_embeded\     ← 內建 Python（啟動伺服器用）
└── main.py             ← 伺服器入口
```

> ⚠️ 外層資料夾 + 內層 ComfyUI 是 portable 版的標準雙層結構，不是重複安裝，
> 重新整理或改名內層會導致模型路徑全部失效。

## 三、如何啟動

在 `C:\minimax+comfyUI` 目錄下執行：

```
python_embeded\python.exe main.py
```

啟動後瀏覽器打開：**http://127.0.0.1:8188**

## 四、模型清單（全部已就位）

位置：`ComfyUI\models\`（下表省略前綴）

| 用途 | 檔案 | 大小 |
|---|---|---|
| ★ 越獄文本編碼器 | text_encoders\qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors | 14.6 GB |
| 文本編碼器（原版 INT8） | text_encoders\minimax_music3_text_encoder_pruned_int8_convrot.safetensors | 8.6 GB |
| 文本編碼器（AWQ 版） | text_encoders\qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors | 14.6 GB |
| ★ H3 主模型 | diffusion_models\minimax_h3_fl2va_pruned_int8_convrot.safetensors | 19.5 GB |
| 音樂 DiT | diffusion_models\minimax_music3_dit_fp16.safetensors | 4.6 GB |
| 視頻 VAE | vae\minimax_h3_video_vae_fp16.safetensors | 4.9 GB |
| 音頻 VAE | vae\minimax_h3_audio_vae_fp32.safetensors | 0.6 GB |
| Turbo LoRA | loras\minimax_h3_turbo_v4_step600_ema.safetensors | — |

## 五、如何生成視頻（兩種方式）

### 方式 A：網頁 UI
1. 啟動伺服器 → 開 http://127.0.0.1:8188
2. 載入工作流，CLIPLoader 選 `qwen3vl_32b_heretic_minimax_h3_nvfp4`（越獄版）
   或 `..._awq` 版，UNETLoader 選 `minimax_h3_fl2va_pruned_int8_convrot`
3. 輸入提示詞 → Queue

### 方式 B：腳本（API 提交）
1. 啟動伺服器
2. 執行 `scripts\` 下的腳本，例如：
   - `python scripts\run_h3_fast.py` — 快速版（864x480、6 步、含音頻，約 1 小時）
   - `python scripts\run_h3_min.py` — 最小測試
   - `python scripts\monitor_h3.py` — 監看進度
3. 生成結果在 `ComfyUI\output\video\`

> 腳本原理：向 http://127.0.0.1:8188/prompt 提交工作流 JSON，與腳本所在路徑無關。
> 想改提示詞/解析度/秒數，直接編輯腳本內的 `PROMPT`、`width/height/length`。

## 六、多段長片生成（連貫拼接，30 秒實戰經驗）

MiniMax H3 單次生成最長約 **15 秒**（124–362 幀，越長越不穩）。想生成更長片段，
**必須分拆多段、首尾銜接、再拼接**。以下為已成功跑通的 30 秒（3×10s）完整流程與踩坑紀錄。

### 完整流程（3×10 秒範例）

1. **寫提示詞**：每段是獨立的文生視頻，用「同一世界觀 + 各自動作段落」，
   並在兩段都明確描述相同場景/人物/鏡頭方向，銜接才自然。
2. **第 1 段**：純文生視頻（無參考圖），243 幀（10s）。
3. **截尾幀**：用 ffmpeg 精確取最後一幀當銜接參考（**必須用下面「正確取幀」的寫法**）：
   ```
   ffmpeg -y -i segN.mp4 -vf reverse -frames:v 1 -q:v 1 segN_last.png
   ```
   ⚠️ 千萬別用 `-sseof -0.15`（會跳到遠處關鍵幀，參考圖會拿錯，接縫崩壞）。
4. **第 N+1 段**：在工作流加 `LoadImage` 節點載入該尾幀，接到
   `MiniMaxH3ImageToVideo` 的 **`first_frame`** 輸入，模型會從該畫面繼續動。
5. **重複 2–4** 直到所有段完成。
6. **拼接**：ffmpeg 重新編碼合併（各段音頻編碼不一，`-c copy` 可能失敗，用重編碼）：
   ```
   ffmpeg -y -f concat -safe 0 -i list.txt -c:v libx264 -crf 18 -c:a aac -b:a 192k out.mp4
   ```
   `list.txt` 每行 `file '路徑'`。

### 銜接驗證（不靠目測，用數據）

截出「第 N 段尾幀」vs「第 N+1 段首幀」，用腳本 `scripts\_diff_check.py` 算 RMS 像素差：
- **RMS < 10**  ✅ 完美銜接（這次實測 = 4.3）
- **RMS 60+**  ❌ first_frame 沒生效或參考圖拿錯

若想偷看內容判斷，自行播放 `ComfyUI\output\video\` 底下各段確認。

### 這段任務踩過的坑（重要！）

| 坑 | 症狀 | 解法 |
|---|---|---|
| **`python_embeded\python311._pth` 寫死內層路徑** | 伺服器一直跑舊碼 0.33.1，first_frame 靜默失效、兩段明顯不連 | 改成指向根目錄，讓新版 0.34.0（含 first_frame 錨點）啟用 |
| **ffmpeg `-sseof` 取幀** | 取到遠處關鍵幀，參考圖錯 | 改用 `-vf reverse -frames:v 1` 精確取真尾幀 |
| **payload 殘留 `last_frame`** | 新版代碼把它當圖片輸入 → `TypeError: int not subscriptable` | 提交前移除無用的 `last_frame` 欄位 |
| **OOM** | first_frame 錨點額外用顯存，243 幀 爆 24GB | 用 `--lowvram` 啟動伺服器；模型會分塊搬移、速度變慢（每步 15–20 分） |
| **再次 TypeError** | 從上一份 payload 複製時把殘留 `last_frame` 帶過去 | 每次提交前檢查 input keys，確認只剩 `first_frame` |

### 速度和時長實測
- 5 秒(73 幀)≈ 48 分 / 10 秒(243 幀)≈ 47 分 —— **幀數幾乎不影響時間**（瓶頸在採樣步的固定成本）
- 帶 first_frame 錨點 + `--lowvram` ≈ 每步 15–20 分，每段約 70–90 分
- 30 秒（2×15s 會 OOM）→ 用 **3×10s**（243 幀/段）最穩

## 七、配樂生成（ACE-Step v1.5，實戰經驗）

### 為影片配連續背景音樂的正確流程
1. **用 ACE-Step 生成一條完整音樂**（不要用 Music3，見下方踩坑）
2. **ffmpeg 混入影片**（影片流 copy 零損失，音頻替換 + 結尾淡出）

### Music3（MiniMax Music3）的教訓 ❌
- Music3 是**歌曲模型**（天生為人聲+歌詞設計），要求它生成「純器樂」會失敗：
  出現人聲狀雜音、中段停頓、環境聲、無旋律
- **caption 不支援否定語法**：寫 "no drums / no vocals" 反而注入這些概念
- **避免場景比喻**：寫 "piano in the next room" 會生成隔牆悶音（聽起來像水管聲）
- 模型檔本身是正版（SHA256 已驗證），問題出在模型定位與提示詞方式

### ACE-Step v1.5 的正確用法 ✅
安裝位置：`C:\Users\princ\ACE-Step-1.5\`（.venv + checkpoints 已就緒）

1. **寫 TOML 配置**（例如 `piano_config.toml`）：
   ```toml
   task_type = "text2music"
   caption = "Gentle relaxed solo piano, soft warm tone, slow tempo 65 BPM, ..."
   lyrics = "[Instrumental]"     # ← 官方純器樂模式，這是 Music3 做不到的
   instrumental = true
   duration = 40.6               # ← 直接指定時長，一次生成
   inference_steps = 8           # turbo 模型 8 步即可
   seed = 20260906
   thinking = false              # ← 必加！否則 CoT 互動流程會卡住等輸入
   use_cot_lyrics = false        # ← 必加！跳過 LM 草稿編輯
   ```
2. **執行**（背景執行，輸出導 log）：
   ```
   cd C:\Users\princ\ACE-Step-1.5
   .venv\Scripts\python.exe cli.py -c piano_config.toml
   ```
   turbo 模型 8 步推理，40 秒音頻約 1~2 分鐘
3. **輸出位置**：`ACE-Step-1.5\output\*.flac`（無損），轉 MP3：
   `ffmpeg -y -i xxx.flac -c:a libmp3lame -b:a 320k out.mp3`
4. **混入影片**（參考 `scripts\_mix.bat`）：
   ```
   ffmpeg -y -i video.mp4 -i music.mp3 -filter_complex
   "[1:a]atrim=0:40.576,aresample=44100,afade=t=out:st=37.5:d=3[aout]"
   -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest out.mp4
   ```

### 混音/拼接的坑（重要！）
| 坑 | 解法 |
|---|---|
| 輸出打不開（High 4:4:4 profile） | 來源段是 yuv444p，拼接時**必須加 `-pix_fmt yuv420p`** 或 filter 結尾 `format=yuv420p` |
| acrossfade 後總長變短，音畫不同步 | 交叉疊化會吃掉重疊時間，需用 `atempo` 對齊（**放慢用 <1.0**，如 0.9109；方向算反了會更短） |
| PowerShell 跑 ffmpeg 帶 `[0:v]` 的 filter | PS 會誤解析 `[ ]`，**改寫成 .bat 或用 `-filter_complex_script 檔案`** |
| PowerShell 誤報 ffmpeg 錯誤 | ffmpeg 把進度寫到 stderr，PS 顯示為紅字錯誤；用 `cmd /c "... > log.txt 2>&1"` 捕獲後看 exit code |
| GBK 控制台編碼 | ACE-Step CLI 結尾打印 ✅ emoji 會 UnicodeEncodeError——**音頻其實已保存**，檢查 output\ 即可 |
| 循環加長音樂 | `asplit=N` 複製音頻 + acrossfade 循環疊化 + `atrim` 修剪到目標長度（可讓一段 10 秒音樂貫穿全片） |

### 成片清單（本專案）
| 檔案 | 說明 |
|---|---|
| `output\video\FINAL_40s_piano.mp4` | ⭐ 最終版：40 秒畫面 + ACE-Step 鋼琴曲貫穿 |
| `output\video\FINAL_40s_seg1music.mp4` | 第一段音樂循環加長版 |
| `output\video\FINAL_40s_origmusic.mp4` | 四段原音樂疊化串接版 |



## 八、畫質提升（AI 超分，736→864 實戰）

### 決策：超分 vs 重新生成
- **內容已滿意、不想重新抽卡** → 超分（幾分鐘，內容 100% 不變）
- **追求原生細節、願意重新驗收動作** → 用 864×480 重新生成（`--lowvram`，2~2.5 小時）
- 736→864 只有 1.17 倍，ESRGAN 超分效果很好；倍率越大越建議重新生成

### 超分管線（`scripts\_upscale_pipeline.bat`）
三步全自動（911 幀約 3~4 分鐘，RTX 4090）：
```
1. ffmpeg 抽幀 → frames_in\*.png
2. realesrgan-ncnn-vulkan.exe -i frames_in -o frames_out -n realesrgan-x4plus -s 4 -f png
3. ffmpeg 合成回影片（scale=864:480）+ 保留原音頻
```
- 工具位置：`C:\minimax+comfyUI\scripts\realesrgan\`（ncnn-vulkan 版，GPU 加速、免 Python 依賴）
- 超分模型：`realesrgan-x4plus`（寫實影片用；動畫風格改 `realesr-animevideov3`）

### 超分管線的坑
| 坑 | 解法 |
|---|---|
| `realesrgan-ncnn-vulkan` **不支援 .mp4 輸出**（invalid outputpath extension） | 必須走「抽幀 → 超分 → 合成」三步 |
| ffmpeg 圖片序列輸出失敗（No such file or directory） | **輸出目錄必須先建立**（bat 開頭 mkdir） |
| 911 幀 4x PNG 約 12GB | 完成後刪除 `frames_in\` `frames_out\` |
| 拼接/後製輸出打不開 | 記得 `-pix_fmt yuv420p` |

## 九、常見問題

- **生成速度**：864x480、6 步採樣，普通模式每步約 12 分鐘；`--lowvram` 每步 15–20 分（H3TURBO LoRA 加速版）
- **顯存不夠？** 長片（帶 first_frame）+ 243 幀建議用 `--lowvram` 啟動伺服器；也可降低解析度，先生小圖再高清化
- **負面提示詞**：H3 無獨立負面輸入框，寫在提示詞裡用「避免：...」即可
- **提示詞範本**：參考教學文章的「烽火邊關」分段式寫法（0-4秒/4-8秒... 每段一鏡頭）
- **版本**：已更新至最新 code（根目錄 0.34.0，`python311._pth` 已修正指向根目錄），`logs\startup_out.log` 可看採樣日誌
- **如何更新**：在根目錄執行 `git pull`，再執行 `python_embeded\python.exe -m pip install -r requirements.txt`
- **啟動（跑長片建議）**：
  ```
  python_embeded\python.exe C:\minimax+comfyUI\main.py --listen 127.0.0.1 --port 8188 --lowvram
  ```

---

# 《烽火邊關》30s 史詩戰爭預告片（2026-09-05）

用 **nightly + CK-Attention + TRT-VAE** 生成 3×10s 接龍，再後製標題／壓黑／音效，並 Real-ESRGAN 2× 超分。

## 成片

| 檔案 | 規格 | 說明 |
|---|---|---|
| `output\video\FINAL_40s_fenghuo.mp4` | 1344×768，約 35.5s | 1× 最終版 |
| `output\video\FINAL_40s_fenghuo_2x.mp4` | **2688×1536**，約 35.4s | 2× 超分最終版 ⭐ |
| `output\video\_noL_fenghuo.mp4` | 1344×768，30.4s | 三段 concat 底片（含原生環境音） |
| `output\video\Fenghuo_10s_0000{1,2,3}_.mp4` | 各 ~10s | H3 分段原始輸出 |

## 生成管線（畫面）

1. **啟動 nightly 伺服器**
   ```
   C:\minimax+comfyUI\python_embeded_nightly\python.exe C:\minimax+comfyUI\main.py --listen 127.0.0.1 --port 8188 --use-ck-attention
   ```
2. **三段 API payload**：`scripts\_fenghuo_seg1.json` ~ `_fenghuo_seg3.json`
   - 1344×768、243 幀、6 步、Turbo LoRA、TRT-VAE
   - 敘事：邊關遠景→女將→城門／箭雨→廝殺→蓄勢→騎兵衝鋒
3. **接龍執行**：`scripts\_fenghuo30.py`（TRT 置換 + first_frame 銜接 + 背景輪詢）
4. **銜接檢查**：`scripts\_fenghuo_diff.py`（尾幀 vs 次段首幀 RMS）
5. **concat**：`scripts\_fh_concat_list.txt` → `_noL_fenghuo.mp4`

## 後製管線（標題 + 音效）

| 步驟 | 腳本 | 作用 |
|---|---|---|
| 金楷標題 PNG | `scripts\_fh_title_png.py` | 標楷體 `kaiu.ttf` + 亮金填色／描邊／陰影 → `_fh_title.png` |
| 後製合成 | `scripts\_fh_post5.bat` + `_fh_post5_fc.txt` | 見下方時間軸 |
| 2× 超分 | `scripts\_fh_up2x.bat` | 抽幀 → realesrgan-x4plus → 2688×1536 + 複製音軌 |

### 最終時間軸（約 35.5s）

| 時間 | 畫面 | 聲音 |
|---|---|---|
| 0 – 27.2s | 原片 | 全片原生環境音 |
| 27.2 – 27.8s | 金楷「烽火邊關」**淡入** | 繼續 |
| 28.0 – 33.0s | **5 秒壓黑** + 標題緩放大（約 1.0→1.75×） | t≈28 起交叉淡入 **seg3 後段** 環境音延續 |
| 31.5 – 32.5s | 近黑 + 大字 | 音量約 1s 淡出 |
| **32.5 – 結束** | 標題淡出 → 黑 | **最後約 3 秒靜音** |

### 音效決策（重要）

- **不使用** MiniMax Music3 / ACE-Step 獨立配樂（試聽均不滿意）
- 正片保留 H3 原生戰場環境音
- 片尾黑屏用 **第三段** `Fenghuo_10s_00003_.mp4` 音軌後段延續，避免空鏡無聲
- 最後 3 秒刻意靜音收束

### Music3 踩坑備註（若再試配樂）

| 坑 | 說明 |
|---|---|
| `cfg_scale=1.0` | 等於關掉 AR 引導，曲子平淡同質；上游預設 **1.5**，`top_k` 預設 **50** |
| caption 過長 | 形容詞堆疊會被平均化；宜 ~50 詞結構化 |
| latent 長於 AR 自然停點 | DiT 後段 pad 零條件 → 尾段無結構嗡鳴；`seconds` 宜貼近模型自然長度 |
| 無 instrumental / 固定時長 | 要純器樂+精準秒數優先 **ACE-Step**（`instrumental=true`, `duration=`） |

## 重跑後製／2×（不重生成畫面）

```bat
REM 1x 後製（標題+壓黑+seg3 尾音）
C:\minimax+comfyUI\scripts\_fh_post5.bat

REM 2x 超分（輸入 FINAL_40s_fenghuo.mp4）
C:\minimax+comfyUI\scripts\_fh_up2x.bat
```

### 後製／超分注意

- PowerShell 對 ffmpeg `[0:v]` filter 易誤解析 → **用 .bat 或 `-filter_complex_script`**
- concat list 必須 **UTF-8 無 BOM**
- 超分暫存：`scripts\frames_fh\`、`scripts\frames_fh_out\`（完成後刪，可數 GB）
- 輸出記得 `-pix_fmt yuv420p`

