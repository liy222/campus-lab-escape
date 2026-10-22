@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
set "PYTHONUTF8=1"
set "GAMEPLAY_VERSION=v5"
set "SQLITE_PATH=./data/game-v5.sqlite"
"C:\Users\liyh\.conda\envs\1\python.exe" -B -X utf8 -m scripts.run_v5 --open-browser
set "RUN_EXIT=%ERRORLEVEL%"
if not "%RUN_EXIT%"=="0" (
  echo V5 launcher exited with code %RUN_EXIT%.
  pause
)
popd
exit /b %RUN_EXIT%
