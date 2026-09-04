# ONNX model downloader for ComfyUI-H3VAE_TRT
$log = 'C:\minimax+comfyUI\logs\_dl_onnx.log'
$base = 'https://huggingface.co/lihaoyun6/MiniMax-H3-VAE-ONNX/resolve/main/'
$dst = 'C:\minimax+comfyUI\ComfyUI\models\vae\'
"start $(Get-Date)" | Out-File $log -Encoding utf8
foreach ($f in 'minimax_h3_vae_decoder.onnx','minimax_h3_vae_decoder.onnx.data','minimax_h3_vae_encoder.onnx') {
    "downloading $f $(Get-Date)" | Out-File $log -Append -Encoding utf8
    & curl.exe -sL --retry 3 -o ($dst + $f) ($base + $f)
    $size = 0
    if (Test-Path ($dst + $f)) { $size = (Get-Item ($dst + $f)).Length }
    "done $f exit=$LASTEXITCODE size=$size $(Get-Date)" | Out-File $log -Append -Encoding utf8
}
"all done $(Get-Date)" | Out-File $log -Append -Encoding utf8
