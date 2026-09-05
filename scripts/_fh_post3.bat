@echo off
chcp 65001 >nul
set V=C:\minimax+comfyUI\output\video
set T=%V%\_fh_title.png
set IN=%V%\_noL_fenghuo.mp4
set OUT=%V%\FINAL_30s_fenghuo.mp4
echo [1/1] overlay title PNG + native env audio + fades (NO music)...
ffmpeg -y -v error -i "%IN%" -loop 1 -t 30.5 -i "%T%" -filter_complex "[1:v]format=rgba[ti];[0:v][ti]overlay=0:0:enable='between(t,27.2,30.42)',fade=t=out:st=29.5:d=0.9[v];[0:a]afade=t=out:st=29.5:d=0.9[a]" -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p -c:a aac -b:a 192k -shortest "%OUT%"
if errorlevel 1 goto :fail
echo POST_OK exit=0
goto :eof
:fail
echo POST_FAILED exit=1
