# Full plan C overnight runner: Music3 v2 batch -> ACE-Step -> convert -> summary
$ErrorActionPreference = "Continue"
$root = "C:\minimax+comfyUI"
$log = "$root\logs\_run_music_c_plan.log"
$pyNightly = "$root\python_embeded_nightly\python.exe"
if (-not (Test-Path $pyNightly)) { $pyNightly = "$root\python_embeded\python.exe" }
$acePy = "C:\Users\princ\ACE-Step-1.5\.venv\Scripts\python.exe"
$aceDir = "C:\Users\princ\ACE-Step-1.5"
$marker = "$root\logs\_jobs_done.marker"

function L($m) {
  $line = (Get-Date -Format "HH:mm:ss") + "  " + $m
  Add-Content -Path $log -Value $line -Encoding UTF8
  Write-Output $line
}

Remove-Item $marker -ErrorAction SilentlyContinue
"" | Set-Content $log -Encoding UTF8
L "=== PLAN C START ==="
L "python=$pyNightly"
L "acePy=$acePy"

# ---- Phase 1: Music3 v2 ----
L "PHASE1 Music3 v2 batch submitting..."
$m3Out = "$root\logs\fenghuo_music_v2_stdout.log"
$m3Err = "$root\logs\fenghuo_music_v2_stderr.log"
$p1 = Start-Process -FilePath $pyNightly `
  -ArgumentList "`"$root\scripts\_gen_fenghuo_music_v2.py`"" `
  -WorkingDirectory $root `
  -WindowStyle Hidden `
  -RedirectStandardOutput $m3Out `
  -RedirectStandardError $m3Err `
  -PassThru
L "Music3 runner pid=$($p1.Id)"
$deadline = (Get-Date).AddMinutes(90)
while (-not $p1.HasExited) {
  if ((Get-Date) -gt $deadline) {
    L "Music3 runner TIMEOUT - killing"
    try { Stop-Process -Id $p1.Id -Force } catch {}
    break
  }
  Start-Sleep -Seconds 15
}
L "Music3 runner exit=$($p1.ExitCode)"
if (Test-Path "$root\logs\fenghuo_music_v2.log") {
  L "--- music_v2.log tail ---"
  Get-Content "$root\logs\fenghuo_music_v2.log" -Tail 30 | ForEach-Object { L ("  " + $_) }
}

# ---- Phase 2: ACE-Step ----
L "PHASE2 ACE-Step fenghuo..."
if (-not (Test-Path $acePy)) {
  L "ACE python missing: $acePy"
} else {
  $aceOut = "$root\logs\ace_fenghuo_stdout.log"
  $aceErr = "$root\logs\ace_fenghuo_stderr.log"
  # snapshot existing flacs so we can detect new ones
  $before = @{}
  Get-ChildItem "$aceDir\output" -Filter *.flac -ErrorAction SilentlyContinue | ForEach-Object { $before[$_.FullName] = $true }

  $p2 = Start-Process -FilePath $acePy `
    -ArgumentList "cli.py","-c","fenghuo_config.toml" `
    -WorkingDirectory $aceDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $aceOut `
    -RedirectStandardError $aceErr `
    -PassThru
  L "ACE runner pid=$($p2.Id)"
  $deadline2 = (Get-Date).AddMinutes(30)
  while (-not $p2.HasExited) {
    if ((Get-Date) -gt $deadline2) {
      L "ACE TIMEOUT - killing"
      try { Stop-Process -Id $p2.Id -Force } catch {}
      break
    }
    Start-Sleep -Seconds 10
  }
  L "ACE runner exit=$($p2.ExitCode)"
  L "--- ace stdout tail ---"
  if (Test-Path $aceOut) { Get-Content $aceOut -Tail 40 | ForEach-Object { L ("  " + $_) } }
  L "--- ace stderr tail ---"
  if (Test-Path $aceErr) { Get-Content $aceErr -Tail 40 | ForEach-Object { L ("  " + $_) } }

  # convert new flacs to mp3 in minimax output
  $newFlacs = Get-ChildItem "$aceDir\output" -Filter *.flac -ErrorAction SilentlyContinue |
    Where-Object { -not $before.ContainsKey($_.FullName) } |
    Sort-Object LastWriteTime
  if (-not $newFlacs) {
    # fallback: newest 2 flacs from last 2 hours
    $newFlacs = Get-ChildItem "$aceDir\output" -Filter *.flac -ErrorAction SilentlyContinue |
      Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-2) } |
      Sort-Object LastWriteTime
  }
  $i = 1
  foreach ($f in $newFlacs) {
    $dest = "$root\output\fenghuo_ace_v$i.mp3"
    L "ffmpeg convert $($f.Name) -> $dest"
    $fflog = "$root\logs\_ace_ff_$i.log"
    cmd /c "ffmpeg -y -i `"$($f.FullName)`" -c:a libmp3lame -b:a 320k `"$dest`" > `"$fflog`" 2>&1"
    L "  exit=$LASTEXITCODE size=$((Get-Item $dest -EA SilentlyContinue).Length)"
    $i++
  }
}

# ---- Phase 3: probe all candidates ----
L "PHASE3 ffprobe all candidates"
$cands = @()
$cands += Get-ChildItem "$root\output\fenghuo_m3_v2_*.mp3" -ErrorAction SilentlyContinue
$cands += Get-ChildItem "$root\output\fenghuo_ace_v*.mp3" -ErrorAction SilentlyContinue
$cands += Get-Item "$root\output\fenghuo_trailer_00001.mp3" -ErrorAction SilentlyContinue
$summary = "$root\logs\fenghuo_music_c_summary.txt"
"Music C-plan candidates $(Get-Date -Format o)" | Set-Content $summary -Encoding UTF8
foreach ($c in $cands) {
  $probe = cmd /c "ffprobe -v error -show_entries format=duration,size,bit_rate -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 `"$($c.FullName)`" 2>&1"
  $vol = cmd /c "ffmpeg -i `"$($c.FullName)`" -af volumedetect -f null NUL 2>&1" | Select-String "mean_volume|max_volume"
  $volLines = @($vol | ForEach-Object { $_.Line })
  $volText = [string]::Join([Environment]::NewLine, $volLines)
  $block = "---- $($c.Name) ----`r`n$probe`r`n$volText`r`n"
  Add-Content $summary $block -Encoding UTF8
  L ("PROBE " + $c.Name)
  L ("  " + ($probe -join " | "))
  L ("  " + ($volText -replace "`r?`n"," | "))
}

# also list Music3 outputs that may land under ComfyUI/output
$extra = Get-ChildItem "$root\ComfyUI\output" -Filter "fenghuo_m3_v2_*.mp3" -ErrorAction SilentlyContinue
foreach ($c in $extra) {
  $dest = "$root\output\$($c.Name)"
  if (-not (Test-Path $dest)) { Copy-Item $c.FullName $dest -Force; L "copied $($c.Name) -> output\" }
}

L "=== PLAN C DONE ==="
"done $(Get-Date -Format o)" | Set-Content $marker -Encoding UTF8
