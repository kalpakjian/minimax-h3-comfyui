# ============================================================
#  run_nightly.ps1 — Minimax H3 nightly 批次一鍵啟動
#  流程：卸載所有 Ollama 模型（釋放 VRAM）→ 確保 ComfyUI server
#        在跑 → 執行 _redo40.py 批次 → 完成後彈窗 + 提示音通知
#
#  用法：
#    powershell -File scripts\run_nightly.ps1                # 由 seg1 跑全部 4 段
#    powershell -File scripts\run_nightly.ps1 -StartSeg 3     # 由 seg3 起跑
#    powershell -File scripts\run_nightly.ps1 -NoStop         # 不卸載 ollama（不建議）
#    powershell -File scripts\run_nightly.ps1 -ReloadModel orca-cyber-27b-uncensored
#    powershell -File scripts\run_nightly.ps1 -DryRun         # 只做前置檢查，不跑批次
#    powershell -File scripts\run_nightly.ps1 -Swap           # 4 段批次完成後追加置換+校色 stage
#    powershell -File scripts\run_nightly.ps1 -SwapOnly       # 只跑置換+校色 stage（不跑 4 段批次）
#
#  Swap stage：scripts\_swap_nightly.py（config: scripts\_swap_nightly_config.json）
#    S1 Character Swap（ref2va + swap LoRA + 4-step turbo + TRT VAE，失敗自動換 std VAE）
#    S2 校色：逐 channel gain/offset 最小二乘對齊 source，ffmpeg rawvideo pipe 重編
# ============================================================
param(
    [int]$StartSeg = 1,                 # 起始段落 (1-4)
    [switch]$NoStop,                    # 跳過 ollama 卸載
    [string]$ReloadModel = "",          # 批次完成後預載的 ollama 模型（可選）
    [switch]$DryRun,                    # 前置檢查後直接結束
    [switch]$Swap,                      # 批次完成後跑置換+校色 stage
    [switch]$SwapOnly                   # 只跑置換+校色 stage（跳過 4 段批次）
)

$ErrorActionPreference = "Stop"
$ROOT    = "D:\AI\ComfyUI"
$PY      = Join-Path $ROOT "python_embeded_nightly\python.exe"
$BATCH   = Join-Path $ROOT "scripts\_redo40.py"
$RESULTS = Join-Path $ROOT "logs\redo40_results.txt"
$HOSTURL = "http://127.0.0.1:8188"

function Get-FreeVRAM {
    (nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | Select-Object -First 1)
}

Write-Host "==== Nightly Batch Launcher ====" -ForegroundColor Cyan

# ---------- 前置檢查 ----------
if (-not (Test-Path $PY))    { throw "nightly python 不存在：$PY" }
if (-not (Test-Path $BATCH)) { throw "批次腳本不存在：$BATCH" }
if (-not $SwapOnly) {
    for ($n = $StartSeg; $n -le 4; $n++) {
        $payload = Join-Path $ROOT ("scripts\_submit_payload_seg{0}.json" -f $n)
        if (-not (Test-Path $payload)) { throw "缺少 payload：$payload" }
    }
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Write-Warning "ffmpeg 不在 PATH，段落串接可能失敗" }
if ($Swap -or $SwapOnly) {
    foreach ($f in ("scripts\_swap_nightly.py", "scripts\_swap_nightly_config.json", "scripts\_swap_payload_base.json")) {
        $p = Join-Path $ROOT $f
        if (-not (Test-Path $p)) { throw "Swap stage 缺少檔案：$p" }
    }
}

# ---------- 1) 卸載所有 Ollama 模型 ----------
if (-not $NoStop) {
    $before = Get-FreeVRAM
    $rows = & ollama ps 2>$null | Select-Object -Skip 1 |
            Where-Object { $_ -match '\S' } | ForEach-Object { ($_ -split '\s{2,}')[0] }
    if ($rows) {
        foreach ($m in $rows) {
            Write-Host "  ollama stop $m" -ForegroundColor Yellow
            $ErrorActionPreference = "Continue"   # ollama spinner 走 stderr，EAP=Stop 會誤殺
            & ollama stop $m 2>$null | Out-Null
            $ErrorActionPreference = "Stop"
        }
        Start-Sleep -Seconds 3
        $after = Get-FreeVRAM
        Write-Host ("  VRAM 釋放：{0} MB -> {1} MB（釋出 {2} MB）" -f $before, $after, ($after - $before))
    } else {
        Write-Host "  Ollama 無已載入模型"
    }
} else {
    Write-Host "  [NoStop] 跳過 ollama 卸載" -ForegroundColor DarkGray
}

# ---------- 2) 確保 ComfyUI server 在跑 ----------
$serverUp = $false
try { $null = Invoke-WebRequest "$HOSTURL/system_stats" -TimeoutSec 3 -UseBasicParsing; $serverUp = $true } catch {}
if (-not $serverUp) {
    Write-Host "  ComfyUI server 未啟動，用 nightly 環境啟動中..." -ForegroundColor Yellow
    Start-Process -FilePath $PY -ArgumentList @('main.py','--listen','127.0.0.1','--port','8188','--use-ck-attention') `
        -WorkingDirectory $ROOT -WindowStyle Minimized
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 3
        try { $null = Invoke-WebRequest "$HOSTURL/system_stats" -TimeoutSec 3 -UseBasicParsing; $serverUp = $true; break } catch {}
    }
    if (-not $serverUp) { throw "ComfyUI server 180 秒內未能啟動" }
}
Write-Host "  ComfyUI server：OK ($HOSTURL)"

if ($DryRun) {
    Write-Host "[DryRun] 前置檢查完成，不執行批次。" -ForegroundColor Green
    exit 0
}

# ---------- 3) 執行 4 段批次（SwapOnly 時跳過）----------
$exit = 0
$done = $false
$swapOk = $false
if (-not $SwapOnly) {
    $t0 = Get-Date
    Write-Host ("==== 開始批次 seg{0}-4  @ {1:HH:mm:ss} ====" -f $StartSeg, $t0) -ForegroundColor Cyan
    & $PY $BATCH $StartSeg 2>&1 | Tee-Object -Variable batchOut | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }
    $elapsed = (Get-Date) - $t0

    # ---------- 4) 批次結果判斷 ----------
    $done = (Test-Path $RESULTS) -and ((Get-Content $RESULTS -Tail 5 -EA SilentlyContinue) -match 'ALL SEGMENTS DONE')
    $status = if ($done) { "成功" } elseif ($exit -ne 0) { "失敗（exit=$exit）" } else { "未見完成標記，請檢查 log" }
    $tailMsg = if ($RESULTS -and (Test-Path $RESULTS)) { (Get-Content $RESULTS -Tail 2) -join ' | ' } else { '無結果檔' }
    Write-Host ("==== 批次{0}，耗時 {1:mm\分ss\秒} ====" -f $status, $elapsed) -ForegroundColor $(if ($done) {'Green'} else {'Red'})
}

# ---------- 4b) 可選：置換 + 校色 stage（nightly 置換系列）----------
$swapMsg = "未跑"
$swapElapsed = New-TimeSpan
if ($Swap -or $SwapOnly) {
    $SWAPPY = Join-Path $ROOT "scripts\_swap_nightly.py"
    $t1 = Get-Date
    Write-Host "==== 開始置換 stage（Swap + 校色）====" -ForegroundColor Cyan
    $null = & $PY $SWAPPY 2>&1 | ForEach-Object { Write-Host "  $_" }
    $swapExit = $LASTEXITCODE
    $swapElapsed = (Get-Date) - $t1
    $swTail = Get-Content (Join-Path $ROOT "logs\swap_nightly_results.txt") -Tail 3 -EA SilentlyContinue
    $swapOk = $swTail -match 'ALL SWAP SEGMENTS DONE'
    $swapMsg = if ($swapOk) { "成功（耗時 {0} 分 {1} 秒）" -f [int]$swapElapsed.TotalMinutes, [int]$swapElapsed.Seconds }
              else { "失敗（exit=$swapExit）" }
    if (-not $swapOk) { $exit = 1 }
    Write-Host ("==== 置換 stage {0} ====" -f $swapMsg) -ForegroundColor $(if ($swapOk) {'Green'} else {'Yellow'})
}

# ---------- 5) 通知 ----------
$batchOk  = if ($SwapOnly) { $true } else { $done }
$swapCond = if ($Swap -or $SwapOnly) { $swapOk } else { $true }
$allOk = ($exit -eq 0) -and $batchOk -and $swapCond
[console]::beep(880, 300); [console]::beep(1320, 500)
$popup = New-Object -ComObject WScript.Shell
$batchLine = if ($SwapOnly) { "" } else { "Minimax H3 nightly 批次：$status`n耗時 $([int]$elapsed.TotalMinutes) 分 $([int]$elapsed.Seconds) 秒`n" }
$swapLine  = if ($Swap -or $SwapOnly) { "置換+校色：$swapMsg`n" } else { "" }
$tailLine  = if ($SwapOnly) { "" } else { "`n$tailMsg" }
$null = $popup.Popup(
    "$batchLine$swapLine$tailLine",
    0, "Nightly Batch 完成", $(if ($allOk) {64} else {16}))

# ---------- 5) 可選：預載 ollama 模型 ----------
if ($ReloadModel) {
    Write-Host "  預載 ollama 模型：$ReloadModel"
    $ErrorActionPreference = "Continue"
    & ollama run $ReloadModel "ready" 2>$null | Out-Null
    $ErrorActionPreference = "Stop"
}
exit $exit
