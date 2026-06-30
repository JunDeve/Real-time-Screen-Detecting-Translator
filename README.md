# Real-time Screen Detecting Translator

**[한국어](#한국어) | [English](#english)**

---

## 한국어

화면의 원하는 영역을 드래그로 선택하면 실시간으로 번역해주는 도구입니다.
API 키 없이 무료로 동작합니다. (Tesseract OCR + Google Translate)

### 다운로드 (Python 불필요)

👉 [**Releases**](https://github.com/JunDeve/Real-time-Screen-Detecting-Translator/releases) 에서 `ScreenTranslator.exe` 다운로드 후 바로 실행

- 별도 설치 없음, 더블클릭으로 실행
- Windows 10/11 64bit 전용

### 설치 및 실행 (개발자 / Python 사용자)

1. `install.bat` 더블클릭
2. 설치 완료 후 탐색기가 자동으로 열리고 `screen_translator.bat` 선택됨
3. `screen_translator.bat` 더블클릭하여 실행

> ⚠️ Python이 설치되어 있어야 합니다. 없다면 https://www.python.org/downloads/ 에서 설치 후 진행하세요.

### 사용법

| 동작 | 단축키 / 방법 |
|------|--------------|
| 번역 활성화 | `[` 를 빠르게 3번 (`[[[`) |
| 번역 종료 | `]` 를 빠르게 3번 (`]]]`) 또는 툴바 ✕ 버튼 |
| 영역 선택 | 화면이 어두워지면 드래그로 번역할 영역 지정 |
| 박스 이동 | 툴바 `⠿ 이동` 부분 드래그 |
| 박스 리사이즈 | 박스 테두리 8방향 핸들 드래그 |
| 언어 전환 | 툴바 `EN→KO` / `KO→EN` 버튼 클릭 |
| 번역 패널 이동 | 번역 패널 헤더 드래그 (이후 박스 추적 중단) |
| 박스 추적 복원 | 패널 헤더의 📌 버튼 클릭 |
| 번역 결과 복사 | 번역 패널 하단 `복사` 버튼 |
| 프로그램 종료 | 트레이 아이콘 우클릭 → 종료 |

### 트레이 아이콘

실행 후 우측 하단 시스템 트레이에 아이콘이 표시됩니다.

- 반투명 = 대기 중 (`[[[` 로 활성화)
- 선명 = 번역 박스 활성 상태
- 우클릭 → 번역 시작/종료, 사용법, jundeve.com, 종료

### 설정 변경

`config.py` 에서 변경 가능합니다.

```python
TARGET_LANG      = "ko"   # 기본 번역 언어 (ko=한국어, en=영어)
TRIPLE_KEY_OPEN  = "["    # 활성화 키
TRIPLE_KEY_CLOSE = "]"    # 종료 키
TRIPLE_INTERVAL  = 0.5    # 연속 입력 인정 시간(초)
DEBOUNCE_MS      = 800    # 박스 변경 후 재번역 대기(ms)
PANEL_WIDTH      = 340    # 번역 패널 너비(px)
POLL_MS          = 1500   # 화면 감지 주기(ms)
CHANGE_THRESHOLD = 8      # 픽셀 변화 감지 민감도
```

### 변화 감지 방식

```
1단계 — 픽셀 비교 (거의 무료)
  └ 변화 없음 → 전부 스킵
  └ 변화 있음 → 2단계

2단계 — OCR 실행 후 텍스트 비교
  └ 텍스트 동일 → 번역 스킵
  └ 텍스트 다름 → 번역 실행
```

### 주의사항

- Windows 전용
- `keyboard` 라이브러리는 일부 환경에서 관리자 권한 필요
- exe 재빌드: `pyinstaller build_exe.spec` (tesseract/, tessdata/ 폴더 필요)

---

## English

A tool that translates any selected area of your screen in real time.
No API key required. (Tesseract OCR + Google Translate)

### Download (No Python required)

👉 Download `ScreenTranslator.exe` from [**Releases**](https://github.com/JunDeve/Real-time-Screen-Detecting-Translator/releases) and run it directly.

- No installation needed, just double-click
- Windows 10/11 64bit only

### Setup (Developers / Python users)

1. Double-click `install.bat`
2. After installation, Explorer opens automatically with `screen_translator.bat` selected
3. Double-click `screen_translator.bat` to run

> ⚠️ Python must be installed. Get it at https://www.python.org/downloads/

### How to Use

| Action | Shortcut / Method |
|--------|------------------|
| Activate translation | Press `[` three times quickly (`[[[`) |
| Stop translation | Press `]` three times (`]]]`) or click ✕ in toolbar |
| Select area | Screen dims — drag to define translation region |
| Move box | Drag the `⠿ 이동` handle in toolbar |
| Resize box | Drag any of the 8 edge/corner handles |
| Toggle language | Click `EN→KO` / `KO→EN` in toolbar |
| Move translation panel | Drag panel header (stops auto-follow) |
| Re-attach panel | Click 📌 in panel header |
| Copy result | Click `복사` button at bottom of panel |
| Exit app | Right-click tray icon → Exit |

### Tray Icon

After launch, an icon appears in the system tray (bottom-right).

- Dimmed = idle (activate with `[[[`)
- Full brightness = translation active
- Right-click → start/stop, usage guide, jundeve.com, exit

### Configuration

Edit `config.py` to adjust settings:

```python
TARGET_LANG      = "ko"   # Default language (ko=Korean, en=English)
TRIPLE_KEY_OPEN  = "["    # Activation key
TRIPLE_KEY_CLOSE = "]"    # Stop key
TRIPLE_INTERVAL  = 0.5    # Key sequence timeout (seconds)
DEBOUNCE_MS      = 800    # Retranslate delay after box change (ms)
PANEL_WIDTH      = 340    # Translation panel width (px)
POLL_MS          = 1500   # Screen poll interval (ms)
CHANGE_THRESHOLD = 8      # Pixel change sensitivity
```

### Change Detection

```
Stage 1 — Pixel diff (near-zero cost)
  └ No change → skip everything
  └ Changed → Stage 2

Stage 2 — OCR + text diff
  └ Same text → skip translation
  └ Different text → translate
```

### Notes

- Windows only
- `keyboard` library may require admin privileges in some environments
- Rebuild exe: `pyinstaller build_exe.spec` (requires tesseract/ and tessdata/ folders)
