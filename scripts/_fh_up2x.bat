@echo off
chcp 65001 >nul
set W=C:\minimax+comfyUI\scripts
set V=C:\minimax+comfyUI\output\video
set IN=%V%\FINAL_40s_fenghuo.mp4
set OUT=%V%\FINAL_40s_fenghuo_2x.mp4
if not exist "%W%\frames_fh" mkdir "%W%\frames_fh"
if not exist "%W%\frames_fh_out" mkdir "%W%\frames_fh_out"
del /q "%W%\frames_fh\*.png" 2>nul
del /q "%W%\frames_fh_out\*.png" 2>nul
echo [1/3] extracting frames...
ffmpeg -y -v error -i "%IN%" "%W%\frames_fh\%%06d.png"
if errorlevel 1 goto :fail
echo [2/3] realesrgan x4 upscaling...
"%W%\realesrgan\realesrgan-ncnn-vulkan.exe" -i "%W%\frames_fh" -o "%W%\frames_fh_out" -n realesrgan-x4plus -s 4 -f png
if errorlevel 1 goto :fail
echo [3/3] reassembling 2688x1536 with audio...
ffmpeg -y -v error -framerate 24 -i "%W%\frames_fh_out\%%06d.png" -i "%IN%" -vf scale=2688:1536 -map 0:v -map 1:a -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p -c:a copy -shortest "%OUT%"
if errorlevel 1 goto :fail
echo UP2X_DONE exit=0
goto :eof
:fail
echo UP2X_FAILED exit=1
