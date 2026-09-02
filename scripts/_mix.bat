@echo off
ffmpeg -y -i C:\minimax+comfyUI\output\video\FINAL_40s.mp4 -i C:\minimax+comfyUI\output\piano_acestep_v1.mp3 -filter_complex "[1:a]atrim=0:40.576,aresample=44100,afade=t=out:st=37.5:d=3[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest C:\minimax+comfyUI\output\video\FINAL_40s_piano.mp4
