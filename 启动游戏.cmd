@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if errorlevel 1 goto :failed
set "PROJECT_PYTHON=C:\Users\liyh\.conda\envs\1\python.exe"
if not exist "%PROJECT_PYTHON%" (
  echo 未找到指定 Python，请检查 README 中配置的路径：
  echo %PROJECT_PYTHON%
  echo 检查路径后再运行。
  goto :failed
)
set "PYTHONUTF8=1"
set "GAMEPLAY_VERSION=upgrade"
set "SQLITE_PATH=./data/game-v3.2.sqlite"
echo 正在启动免费演示模式。
echo 首次使用请按 README.md 安装依赖。
"%PROJECT_PYTHON%" -m scripts.dev --provider mock --open-browser
set "RUN_EXIT=%ERRORLEVEL%"
if not "%RUN_EXIT%"=="0" (
  echo.
  echo Game startup or runtime stopped with exit code %RUN_EXIT%.
  echo 端口占用请先停止已有游戏；缺少依赖请按 README.md 安装步骤处理。
  pause
)
exit /b %RUN_EXIT%
:failed
echo.
echo 启动失败，请查看上方信息及 README.md。
pause
exit /b 1
