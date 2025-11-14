@echo off
echo ------------------------------
echo   Auto Git Push by Masoud
echo ------------------------------

REM گرفتن پیام کامیت از ورودی
set /p commitMsg="Enter commit message: "

echo Adding files...
git add .

echo Committing...
git commit -m "%commitMsg%"

echo Pushing to GitHub...
git push origin main

echo ------------------------------
echo   Done! Repo Updated ✔
echo ------------------------------
pause
