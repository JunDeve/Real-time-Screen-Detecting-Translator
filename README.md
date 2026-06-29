# Real-time Screen Detecting Translator

화면의 원하는 영역을 드래그로 선택하면 실시간으로 번역해주는 도구입니다.  
API 키 없이 무료로 동작합니다. (EasyOCR + Google Translate)

---

## 실행 방법

1. 의존성 설치

```bash
pip install -r requirements.txt
```

2. 실행

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

### 동작 흐름

```
[[[ 입력 → 화면 어두워짐 → 드래그로 영역 선택
→ 선택 박스 + 번역 패널 생성
→ 박스 이동/리사이즈 시 자동 재번역
→ ]]] 또는 닫기 버튼으로 종료
```

---

## 설정 변경

`config.py` 에서 변경 가능합니다.

```python
TARGET_LANG      = "ko"          # 기본 번역 언어 (ko=한국어, en=영어)
OCR_LANGS        = ["en", "ko"]  # 인식할 언어 목록
TRIPLE_KEY_OPEN  = "["           # 활성화 키
TRIPLE_KEY_CLOSE = "]"           # 종료 키
TRIPLE_INTERVAL  = 0.5           # 연속 입력 인정 시간(초)
DEBOUNCE_MS      = 800           # 박스 변경 후 재번역 대기(ms)
PANEL_WIDTH      = 340           # 번역 패널 너비(px)
```

---

## 의존성

- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — 로컬 텍스트 인식
- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google Translate 무료 연동
- [keyboard](https://github.com/boppreh/keyboard) — 전역 단축키
- [mss](https://github.com/BoboTiG/python-mss) — 화면 캡처
- Pillow, numpy, tkinter

---

## 주의사항

- Windows 전용 (tkinter `-transparentcolor` 기능 사용)
- 최초 실행 시 EasyOCR 모델 다운로드로 수십 초 소요될 수 있음
- `keyboard` 라이브러리는 관리자 권한 없이도 동작하나, 일부 환경에서는 관리자 권한 필요
