@echo off
title Screen Translator - Installing...
color 0B

echo.
echo  ====================================
echo   Screen Translator - Setup
echo  ====================================
echo.
echo  Installing required packages...
echo  Please wait.
echo.

cd /d "%~dp0"
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Installation failed.
    echo  Please make sure Python is installed.
    echo  Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

echo.
echo  ====================================
echo   Installation complete!
echo  ====================================
echo.
echo  Double-click [screen_translator.bat] to run.
echo.

explorer /select,"%~dp0screen_translator.bat"

pause
