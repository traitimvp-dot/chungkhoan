@echo off
cd /d "%~dp0.."

echo Dang kich hoat moi truong ao...
call "%USERPROFILE%\.venv\Scripts\activate.bat"

echo Dang chay cap nhat thong tin co ban (Profile)...
python scripts\update_profile.py

echo Hoan thanh!
exit
