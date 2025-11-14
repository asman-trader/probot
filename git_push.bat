@echo off
setlocal enabledelayedexpansion

:: نام فایل شمارنده
set counterFile=commit_counter.txt

:: اگر فایل شمارنده وجود ندارد، از 1 شروع کن
if not exist %counterFile% (
    echo 1 > %counterFile%
)

:: خواندن عدد فعلی
set /p count=<%counterFile%

echo Current commit number: %count%
set commitMsg=commit-%count%

echo Adding all files...
git add .

echo Creating commit: %commitMsg%
git commit -m "%commitMsg%"

echo Pushing to GitHub...
git push origin main

:: افزایش شمارنده
set /a count=count+1
echo %count% > %counterFile%

echo ------------------------------
echo Done! Commit created: %commitMsg%
echo Next commit number saved: %count%
echo ------------------------------
pause
