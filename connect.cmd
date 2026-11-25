@echo off
setlocal
where ma-ru >nul 2>&1
if errorlevel 1 goto use_uv
call ma-ru connect
if errorlevel 1 pause
exit /b
:use_uv
where uv >nul 2>&1
if errorlevel 1 (
  echo Install uv: https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)
uv run --no-project --python 3.13 --with "%~dp0." ma-ru connect
if errorlevel 1 pause
