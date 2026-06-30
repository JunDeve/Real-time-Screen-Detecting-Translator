# Real-time Screen Detecting Translator

화면의 원하는 영역을 드래그로 선택하면 실시간으로 번역해주는 도구입니다.  
API 키 없이 무료로 동작합니다. (Tesseract OCR + Google Translate)

---

## 다운로드 (Python 불필요)

> **일반 사용자 추천**: Python 설치 없이 바로 실행 가능한 exe 파일

👉 [**Releases**](https://github.com/JunDeve/Real-time-Screen-Detecting-Translator/releases) 에서 `ScreenTranslator.exe` 다운로드 후 바로 실행

- 별도 설치 없음, 더블클릭으로 실행
- Windows 10/11 64bit 전용 (약 308MB)

---

## 설치 및 실행 (개발자 / Python 사용자)

### 처음 사용하는 경우 (설치 필요)

1. `install.bat` 더블클릭
2. 설치가 완료되면 탐색기가 자동으로 열리고 `screen_translator.bat` 가 선택됨
3. `screen_translator.bat` 더블클릭하여 실행

> ⚠️ Python이 설치되어 있어야 합니다. 없다면 https://www.python.org/downloads/ 에서 설치 후 진행하세요.

### 이미 설치된 경우

```
screen_translator.bat  더블클릭
```

백그라운드에서 조용히 실행되며 콘솔창이 뜨지 않습니다.

---

## 사용법

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

### 동작 흐름

```
[[[ 입력 → 화면 어두워짐 → 드래그로 영역 선택
→ 선택 박스 + 번역 패널 생성
→ 박스 이동/리사이즈 시 자동 재번역
→ ]]] 또는 닫기 버튼으로 종료
```

### 트레이 아이콘

실행 후 우측 하단 시스템 트레이에 아이콘이 표시됩니다.

- 회색 원 = 대기 중 (`[[[` 로 활성화)
- 초록 원 = 번역 박스 활성 상태

---

## 설정 변경

`config.py` 에서 변경 가능합니다.

```python
TARGET_LANG      = "ko"   # 기본 번역 언어 (ko=한국어, en=영어)
TRIPLE_KEY_OPEN  = "["    # 활성화 키
TRIPLE_KEY_CLOSE = "]"    # 종료 키
TRIPLE_INTERVAL  = 0.5    # 연속 입력 인정 시간(초)
DEBOUNCE_MS      = 800    # 박스 변경 후 재번역 대기(ms)
PANEL_WIDTH      = 340    # 번역 패널 너비(px)
POLL_MS          = 1500   # 화면 감지 주기(ms) — 숫자 낮을수록 빠름
CHANGE_THRESHOLD = 8      # 픽셀 변화 감지 민감도 — 낮을수록 민감
```

---

## 의존성

- [pytesseract](https://github.com/madmaze/pytesseract) + [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — 로컬 텍스트 인식 (영어/한국어)
- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google Translate 무료 연동
- [keyboard](https://github.com/boppreh/keyboard) — 전역 단축키
- [mss](https://github.com/BoboTiG/python-mss) — 화면 캡처
- [pystray](https://github.com/moses-palmer/pystray) — 시스템 트레이 아이콘
- Pillow, numpy, tkinter

---

## 변화 감지 방식 (2단계 필터)

박스가 열려 있는 동안 주기적으로 화면을 감시하며, 불필요한 작업을 최소화합니다.

```
1단계 — 픽셀 비교 (거의 무료)
  └ 변화 없음 → 전부 스킵
  └ 변화 있음 → 2단계

2단계 — OCR 실행 후 텍스트 비교
  └ 텍스트 동일 (배경만 바뀜) → 번역 스킵
  └ 텍스트 다름 → 번역 실행
```

### 대략적인 CPU 사용량

| 상황 | CPU |
|------|-----|
| 박스 없음 (대기 중) | ~0% |
| 화면 변화 없음 | ~0% (픽셀 비교만) |
| 배경만 바뀜 (텍스트 동일) | 갱신 주기마다 코어 1개 20~50% 순간 |
| 텍스트 바뀜 (번역 실행) | 갱신 주기마다 코어 1개 50~80% 순간 |

> Tesseract는 이미지 1장당 약 0.1~0.5초 소요 (EasyOCR 대비 훨씬 가벼움)  
> 갱신 주기를 길게 (1.5s~3s) 설정할수록 부담이 줄어듭니다.

---

## 주의사항

- Windows 전용 (tkinter `-transparentcolor` 기능 사용)
- `keyboard` 라이브러리는 관리자 권한 없이도 동작하나, 일부 환경에서는 관리자 권한 필요
- exe 빌드: `pyinstaller build_exe.spec` (tesseract/, tessdata/ 폴더 필요)
