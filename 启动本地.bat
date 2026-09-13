@echo off
chcp 65001 >nul
title AI Job Agent - 启动器

set ROOT=%~dp0

echo.
echo   正在启动本地服务（你自己用的那套，账号 yangtao）
echo   ------------------------------------------------
echo   后端  http://127.0.0.1:8000
echo   前端  http://localhost:5173
echo.
echo   会弹出两个黑窗口，别关它们。
echo   要停止：把那两个窗口关掉就行。
echo.

start "AI Job Agent - 后端 8000" cmd /k "cd /d %ROOT%backend && venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"

start "AI Job Agent - 前端 5173" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo   后端在加载语义模型，约 20 秒...
echo   等它好了会自动打开浏览器。
echo.

:wait
timeout /t 3 >nul
curl.exe -s -m 3 http://127.0.0.1:8000/health | findstr /C:"\"status\":\"ok\"" >nul
if errorlevel 1 goto wait

start "" http://localhost:5173

echo   已打开浏览器。这个窗口可以关了。
timeout /t 5 >nul
