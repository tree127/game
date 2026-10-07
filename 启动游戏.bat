@echo off
cd /d "%~dp0"
echo 正在用 Python 3.14.6 启动 俄罗斯方块...
echo.
py -3.14 "俄罗斯方块.py"
set code=%errorlevel%
echo.
echo ==== 程序已退出, 退出码: %code% ====
if exist "俄罗斯方块_错误日志.txt" (
  echo.
  echo ---- 错误日志 ----
  type "俄罗斯方块_错误日志.txt"
)
echo.
pause
