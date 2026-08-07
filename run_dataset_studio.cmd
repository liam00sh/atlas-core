@echo off
setlocal
cd /d "%~dp0"
python -m atlas_dataset_studio %*
endlocal
