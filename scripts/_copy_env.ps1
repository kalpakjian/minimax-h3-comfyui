# Copy python_embeded -> python_embeded_nightly (isolated env for torch nightly upgrade)
$src = 'C:\minimax+comfyUI\python_embeded'
$dst = 'C:\minimax+comfyUI\python_embeded_nightly'
$log = 'C:\minimax+comfyUI\logs\_copy_env.log'
"start $(Get-Date)" | Out-File $log -Encoding utf8
robocopy $src $dst /E /NFL /NDL /NJH /NJS /MT:16 | Out-Null
"robocopy exit=$LASTEXITCODE $(Get-Date)" | Out-File $log -Append -Encoding utf8
if ($LASTEXITCODE -le 7) {
    "copy OK $(Get-Date)" | Out-File $log -Append -Encoding utf8
} else {
    "copy FAILED $(Get-Date)" | Out-File $log -Append -Encoding utf8
}
