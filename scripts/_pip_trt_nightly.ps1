# Install tensorrt into nightly env too (uses pip cache; nightly copy predates TRT install)
$py = 'C:\minimax+comfyUI\python_embeded_nightly\python.exe'
$log = 'C:\minimax+comfyUI\logs\_pip_trt_nightly.log'
"start $(Get-Date)" | Out-File $log -Encoding utf8
& $py -m pip install --disable-pip-version-check --prefer-binary tensorrt 2>&1 | Out-File $log -Append -Encoding utf8
"pip exit=$LASTEXITCODE $(Get-Date)" | Out-File $log -Append -Encoding utf8
& $py -c "import tensorrt as trt; print('tensorrt OK', trt.__version__)" 2>&1 | Out-File $log -Append -Encoding utf8
