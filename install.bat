@echo off
title Screen Translator - Installing...
color 0B

echo.
echo  ====================================
echo   Screen Translator - Setup
echo  ====================================
echo.

cd /d "%~dp0"

echo  [1/3] Installing Python packages...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] pip failed.
    echo  Make sure Python is installed: https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

echo.
echo  [2/3] Installing Tesseract OCR engine...
winget install UB-Mannheim.TesseractOCR --silent
if %errorlevel% neq 0 (
    echo  Tesseract may already be installed, continuing...
)

echo.
echo  [3/3] Downloading language data (EN + KO)...
if not exist "tessdata" mkdir tessdata

if not exist "tessdata\eng.traineddata" (
    curl -L "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata" -o "tessdata\eng.traineddata"
)
if not exist "tessdata\kor.traineddata" (
    curl -L "https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata" -o "tessdata\kor.traineddata"
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
