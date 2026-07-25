@echo off
title ScreenParser API Server

echo.
echo ==========================================
echo Starting Qwen 3.5 Vision API...
echo ==========================================
echo.

"D:\Download\Projects\qwen 3.5 4b\koboldcpp.exe" ^
 --model "D:\Download\Projects\qwen 3.5 4b\Qwen3.5-4B-UD-Q4_K_XL.gguf" ^
 --mmproj "D:\Download\Projects\qwen 3.5 4b\mmproj-BF16.gguf" ^
 --jinja ^
 --jinjathink false ^
 --threads 8 ^
 --port 5001 ^
 --host 127.0.0.1

pause
