# Real-time Screen Detecting Translator

**[한국어](#한국어) | [English](#english)**

---

## 한국어

화면의 원하는 영역을 드래그로 선택하면 실시간으로 번역해주는 도구입니다.
API 키 없이 무료로 동작합니다. (Tesseract OCR + Google Translate)

### 다운로드 및 실행

👉 [**Releases**](https://github.com/JunDeve/Real-time-Screen-Detecting-Translator/releases) 에서 `ScreenTranslator.exe` 다운로드 후 더블클릭

- Python·별도 설치 불필요 — exe 하나로 실행
- Windows 10/11 64bit 전용
- 중복 실행 방지: 이미 실행 중이면 새로 실행해도 트레이의 기존 인스턴스만 유지됩니다

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

- 우클릭 → 번역 시작/종료, 사용법, jundeve.com, 종료
- `[[[` 로 번역 활성화 / `]]]` 로 번역 종료

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
- 일부 환경에서는 관리자 권한으로 실행해야 단축키(`[[[`, `]]]`) 감지가 동작합니다

---

### 개발자 / 직접 빌드

소스에서 직접 실행하거나 exe를 재빌드하려는 경우입니다.

```bash
pip install -r requirements.txt
python main.py        # 소스 직접 실행
```

**exe 재빌드:**

```bash
pyinstaller build_exe.spec
# 빌드 전 프로젝트 폴더에 tesseract/ 와 tessdata/(eng, kor) 가 있어야 합니다
# 결과물: dist/ScreenTranslator.exe
```

설정은 `config.py` 에서 변경합니다.

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

---

## English

A tool that translates any selected area of your screen in real time.
No API key required. (Tesseract OCR + Google Translate)

### Download & Run

👉 Download `ScreenTranslator.exe` from [**Releases**](https://github.com/JunDeve/Real-time-Screen-Detecting-Translator/releases) and double-click it.

- No Python, no installation — runs as a single exe
- Windows 10/11 64bit only
- Single-instance: launching again while it's already running just keeps the existing tray instance

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

- Right-click → start/stop, usage guide, jundeve.com, exit
- Activate with `[[[`, stop with `]]]`

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
- Some environments require running as administrator for the `[[[` / `]]]` hotkeys to be detected

---

### Developers / Building from source

To run from source or rebuild the exe:

```bash
pip install -r requirements.txt
python main.py        # run from source
```

**Rebuild the exe:**

```bash
pyinstaller build_exe.spec
# tesseract/ and tessdata/ (eng, kor) must exist in the project folder before building
# Output: dist/ScreenTranslator.exe
```

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
