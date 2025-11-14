@echo off
setlocal enabledelayedexpansion

echo Checking for changes...

:: بررسی اینکه آیا چیزی برای commit هست یا نه
git status --porcelain > temp_status.txt

:: اگر فایل خالی باشد یعنی هیچ تغییری نیست
for /f %%i in ('findstr /r "." temp_status.txt ^| find /c /v ""') do set changes=%%i
del temp_status.txt

if "%changes%"=="0" (
    echo --------------------------------
    echo No changes found. Skipping commit.
    echo --------------------------------
    pause
    exit /b
)

echo Changes detected. Proceeding...

:: فایل شمارنده
set counterFile=commit_counter.txt

if not exist %counterFile% (
    echo 1 > %counterFile%
)

:: خواندن شمارنده
set /p count=<%counterFile%

set commitMsg=commit-%count%

echo Adding files...
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
echo Next commit number: %count%
echo ------------------------------
pause
