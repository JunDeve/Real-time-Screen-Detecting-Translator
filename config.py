# ── 번역 설정 ──────────────────────────────────────────────
# Google Translate 언어 코드
# 한국어='ko'  영어='en'  일본어='ja'  중국어(간체)='zh-CN'
TARGET_LANG = "ko"

# EasyOCR 인식 언어 목록 (인식할 언어를 미리 지정)
# 자주 쓰는 언어만 넣을수록 빠름
# 'en'=영어  'ko'=한국어  'ja'=일본어  'ch_sim'=중국어간체
OCR_LANGS = ["en", "ko"]

# ── 단축키 설정 ────────────────────────────────────────────
TRIPLE_KEY_OPEN  = "["    # [[[ 3번 빠르게 = 활성화
TRIPLE_KEY_CLOSE = "]"    # ]]] 3번 빠르게 = 종료
TRIPLE_INTERVAL  = 0.5    # 0.5초 이내 3번 입력
DEBOUNCE_MS      = 800    # 박스 변경 후 재번역 대기(ms)
PANEL_WIDTH      = 340    # 번역 패널 너비(px)
