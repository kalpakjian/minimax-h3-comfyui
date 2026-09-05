# fix broken line in _run_music_c_plan.ps1
p = r"C:\minimax+comfyUI\scripts\_run_music_c_plan.ps1"
with open(p, "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.lstrip().startswith("$block = ") and "vol -join" in line:
        out.append('  $volLines = @($vol | ForEach-Object { $_.Line })\n')
        out.append('  $volText = [string]::Join([Environment]::NewLine, $volLines)\n')
        out.append('  $block = "---- $($c.Name) ----`r`n$probe`r`n$volText`r`n"\n')
        i += 1
        # skip following Add-Content / L lines we will rewrite? keep them but fix vol join ones
        continue
    if '($vol -join' in line:
        out.append('  L ("  " + ($volText -replace "`r?`n"," | "))\n')
        i += 1
        continue
    out.append(line)
    i += 1

with open(p, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(out)
print("fixed", p)
for n, l in enumerate(out[112:122], start=113):
    print(f"{n}:{l.rstrip()}")
