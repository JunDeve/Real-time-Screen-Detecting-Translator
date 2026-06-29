@echo off
chcp 65001 > nul
title 화면 번역기 - 설치 중...
color 0B

echo.
echo  ╔══════════════════════════════════════╗
echo  ║     화면 번역기 설치 프로그램        ║
echo  ╚══════════════════════════════════════╝
echo.
echo  필요한 프로그램을 자동으로 설치합니다.
echo  인터넷 연결이 필요합니다.
echo.
echo  ─────────────────────────────────────
echo  [1/2] Python 패키지 설치 중...
echo  ─────────────────────────────────────
echo.

cd /d "%~dp0"
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo  [오류] 설치 중 문제가 발생했습니다.
    echo  Python이 설치되어 있는지 확인해주세요.
    echo  https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

echo.
echo  ─────────────────────────────────────
echo  [2/2] 설치 완료!
echo  ─────────────────────────────────────
echo.
echo  아래 버튼을 클릭하면 번역기가 실행됩니다.
echo.

:: 설치 완료 후 폴더 열기 (실행 파일 바로 보임)
explorer /select,"%~dp0screen_translator.bat"

echo  폴더가 열렸습니다.
echo  [screen_translator.bat] 을 더블클릭하여 실행하세요.
echo.
pause
