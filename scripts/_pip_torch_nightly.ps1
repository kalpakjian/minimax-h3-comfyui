# Upgrade torch to latest nightly cu130 in the isolated python_embeded_nightly env
$py = 'C:\minimax+comfyUI\python_embeded_nightly\python.exe'
$log = 'C:\minimax+comfyUI\logs\_pip_torch_nightly.log'
"start $(Get-Date)" | Out-File $log -Encoding utf8
& $py -m pip install --disable-pip-version-check --upgrade --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130 2>&1 | Out-File $log -Append -Encoding utf8
"pip exit=$LASTEXITCODE $(Get-Date)" | Out-File $log -Append -Encoding utf8
& $py -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'available', torch.cuda.is_available())" 2>&1 | Out-File $log -Append -Encoding utf8
