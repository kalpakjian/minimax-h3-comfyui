@echo off
chcp 65001 >nul
set V=C:\minimax+comfyUI\output\video
set T=%V%\_fh_title.png
set IN=%V%\_noL_fenghuo.mp4
set S3=%V%\Fenghuo_10s_00003_.mp4
set OUT=%V%\FINAL_40s_fenghuo.mp4
set FC=%~dp0_fh_post5_fc.txt
echo [1/1] post5: title+5s black + seg3 tail audio from t=28 ...
ffmpeg -y -v error -i "%IN%" -loop 1 -t 35.5 -i "%T%" -i "%S3%" -filter_complex_script "%FC%" -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p -c:a aac -b:a 192k -ar 32000 -ac 2 -t 35.42 "%OUT%"
if errorlevel 1 goto :fail
echo POST5_OK exit=0
goto :eof
:fail
echo POST5_FAILED exit=1
