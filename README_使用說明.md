# MiniMax H3 + ComfyUI 使用說明

> 最後更新：2026-09-01
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

## 七、常見問題

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

