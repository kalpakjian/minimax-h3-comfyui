@echo off
set W=C:\minimax+comfyUI\scripts
set V=C:\minimax+comfyUI\output\video
mkdir "%W%\frames_in" 2>nul
mkdir "%W%\frames_out" 2>nul
echo [1/3] extracting frames...
ffmpeg -y -i "%V%\FINAL_38s_xfade.mp4" "%W%\frames_in\%%06d.png" > "%W%\_step1.log" 2>&1
echo [2/3] upscaling 4x...
"%W%\realesrgan\realesrgan-ncnn-vulkan.exe" -i "%W%\frames_in" -o "%W%\frames_out" -n realesrgan-x4plus -s 4 -f png > "%W%\_step2.log" 2>&1
echo [3/3] reassembling 864x480 with audio...
ffmpeg -y -framerate 24 -i "%W%\frames_out\%%06d.png" -i "%V%\FINAL_38s_xfade.mp4" -vf scale=864:480 -map 0:v -map 1:a -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p -c:a copy -shortest "%V%\FINAL_38s_upscaled.mp4" > "%W%\_step3.log" 2>&1
echo ALL DONE exit=%ERRORLEVEL%
