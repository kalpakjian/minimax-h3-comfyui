@echo off
chcp 65001 >nul
set V=C:\minimax+comfyUI\output\video
set T=%V%\_fh_title.png
set IN=%V%\_noL_fenghuo.mp4
set OUT=%V%\FINAL_40s_fenghuo.mp4
set FC=%~dp0_fh_post4_fc.txt
echo [1/1] gold title fade+zoom + 5s black + native audio ...
ffmpeg -y -v error -i "%IN%" -loop 1 -t 35.5 -i "%T%" -filter_complex_script "%FC%" -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p -c:a aac -b:a 192k -t 35.42 "%OUT%"
if errorlevel 1 goto :fail
echo POST4_OK exit=0
goto :eof
:fail
echo POST4_FAILED exit=1
