"""
화면 번역기 - Screen Translator
켜기   : [[[ ([ 3번 빠르게)
끄기   : ]]] (] 3번 빠르게) 또는 닫기 버튼
동작   : 화면 어두워짐 -> 드래그로 영역 선택 -> 우측에 번역 결과 표시
         선택 박스 이동/리사이즈 가능, 변경 시 자동 재번역
번역   : Windows 내장 OCR + Google Translate (무료, API 키 불필요)
"""

import tkinter as tk
import threading
import time
import sys
import os
import ctypes
import numpy as np

import keyboard
import mss
from PIL import Image, ImageDraw
from deep_translator import GoogleTranslator
import pystray
import pytesseract

# PyInstaller 스플래시(번들 exe 압축 해제~트레이 준비 사이의 로딩 화면).
# 소스에서 python main.py로 직접 실행할 때는 모듈이 없으므로 조용히 무시한다.
try:
    import pyi_splash
except ImportError:
    pyi_splash = None

from config import (
    TARGET_LANG,
    TRIPLE_KEY_OPEN, TRIPLE_KEY_CLOSE, TRIPLE_INTERVAL,
    DEBOUNCE_MS, PANEL_WIDTH, POLL_MS, CHANGE_THRESHOLD,
)

# ── Tesseract 경로 설정 ──────────────────────────────────────
# PyInstaller 번들 실행 시: sys._MEIPASS/tesseract
# 일반 실행 시: 프로젝트 폴더 기준 또는 Program Files
def _find_tesseract() -> str:
    # 1) PyInstaller 번들 내부
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "tesseract", "tesseract.exe")
    # 2) 프로젝트 폴더 내 tesseract/
    local = os.path.join(os.path.dirname(__file__), "tesseract", "tesseract.exe")
    if os.path.exists(local):
        return local
    # 3) 기본 설치 경로
    default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default):
        return default
    return "tesseract"  # PATH에 있으면 동작

def _tessdata_dir() -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "tessdata")
    return os.path.join(os.path.dirname(__file__), "tessdata")

pytesseract.pytesseract.tesseract_cmd = _find_tesseract()
os.environ["TESSDATA_PREFIX"] = _tessdata_dir()

# target_lang → OCR 소스 언어 (번역 방향의 반대)
_OCR_LANG = {"ko": "eng", "en": "kor"}

# 투명 처리에 사용할 색상 (이 색상이 윈도우에서 완전 투명 처리됨)
_TRANS  = "#fefefe"
_BORDER = "#00aaff"
_HANDLE = 10
_EDGE   = 14


# ── Tesseract OCR ────────────────────────────────────────────
def ocr_image(img: Image.Image, target_lang: str = "ko") -> str:
    lang = _OCR_LANG.get(target_lang, "eng")
    try:
        text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
        return text.strip()
    except Exception:
        return ""


# ── 번역 ─────────────────────────────────────────────────────
def do_translate(text: str, target_lang: str = "ko") -> str:
    if not text:
        return "[인식된 텍스트 없음]"
    try:
        translated = GoogleTranslator(
            source="auto", target=target_lang
        ).translate(text)
        return translated or text
    except Exception as e:
        return f"[번역 오류: {e}]\n\n원문:\n{text}"


# ── OCR + 번역 (일반 호출용) ─────────────────────────────────
def translate_image(img: Image.Image, target_lang: str = "ko") -> str:
    return do_translate(ocr_image(img, target_lang), target_lang)


# ── 백슬래시 3회 감지 ────────────────────────────────────────
class TripleKeyDetector:
    def __init__(self, key: str, callback):
        self._times: list[float] = []
        self._cb = callback
        keyboard.on_press_key(key, self._hit)

    def _hit(self, _):
        now = time.time()
        self._times = [t for t in self._times if now - t <= TRIPLE_INTERVAL]
        self._times.append(now)
        if len(self._times) >= 3:
            self._times.clear()
            self._cb()


# ── 전체화면 선택 오버레이 ──────────────────────────────────
class SelectionOverlay:
    def __init__(self, root, on_select, on_cancel=None):
        self._root = root
        self._on_select = on_select
        self._on_cancel = on_cancel
        self._sx = self._sy = 0
        self._rect = None

        self.win = tk.Toplevel(root)
        self.win.attributes("-fullscreen", True)
        self.win.attributes("-alpha", 0.38)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="black")
        self.win.lift()
        self.win.focus_force()

        self.cv = tk.Canvas(self.win, bg="black",
                            cursor="crosshair", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        sw = self.win.winfo_screenwidth()
        self.cv.create_text(
            sw // 2, 38,
            text="드래그하여 번역할 영역 선택    |    ESC: 취소",
            fill="white", font=("Malgun Gothic", 13),
        )

        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",       self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.win.bind("<Escape>", lambda _: self._cancel())

        # 포커스 이슈 대비 전역 ESC 훅
        keyboard.add_hotkey("esc", self._cancel, suppress=False)

    def _cancel(self):
        try:
            keyboard.remove_hotkey("esc")
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass
        if self._on_cancel:
            self._on_cancel()

    def _press(self, e):
        self._sx, self._sy = e.x_root, e.y_root
        if self._rect:
            self.cv.delete(self._rect)

    def _drag(self, e):
        if self._rect:
            self.cv.delete(self._rect)
        ox = self._sx - self.win.winfo_rootx()
        oy = self._sy - self.win.winfo_rooty()
        self._rect = self.cv.create_rectangle(
            ox, oy, e.x, e.y,
            outline=_BORDER, width=2,
            fill="#003366", stipple="gray25",
        )

    def _release(self, e):
        try:
            keyboard.remove_hotkey("esc")
        except Exception:
            pass
        x1 = min(self._sx, e.x_root)
        y1 = min(self._sy, e.y_root)
        x2 = max(self._sx, e.x_root)
        y2 = max(self._sy, e.y_root)
        self.win.destroy()
        if x2 - x1 > 20 and y2 - y1 > 20:
            self._on_select({"left": x1, "top": y1,
                             "width": x2 - x1, "height": y2 - y1})


# ── 이동/리사이즈 가능한 선택 박스 ─────────────────────────
_TOOLBAR_H  = 30   # 툴바 높이
_SETTINGS_H = 32   # 설정 바 높이


# ── 설정 바 (갱신 주기 + 민감도) ────────────────────────────
class SettingsBar:
    _POLLS = [("0.5s", 500), ("1s", 1000), ("1.5s", 1500), ("3s", 3000)]
    _SENS  = [("높음", 3), ("보통", 8), ("낮음", 20)]

    def __init__(self, root, on_change, poll_ms, threshold):
        self._root      = root
        self._on_change = on_change   # callback(poll_ms, threshold)
        self._poll_ms   = poll_ms
        self._threshold = threshold

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#111111")

        # 갱신 주기
        tk.Label(self.win, text="갱신", bg="#111111", fg="#666666",
                 font=("Malgun Gothic", 8), padx=6).pack(side="left")
        self._poll_btns = {}
        for label, ms in self._POLLS:
            btn = tk.Button(
                self.win, text=label,
                bg="#1e1e1e", fg="#aaaaaa",
                activebackground="#004466", activeforeground="white",
                relief="flat", font=("Malgun Gothic", 8),
                padx=7, pady=2, cursor="hand2", bd=0,
                command=lambda m=ms: self._set_poll(m),
            )
            btn.pack(side="left", padx=1, pady=4)
            self._poll_btns[ms] = btn

        # 구분선
        tk.Label(self.win, text="│", bg="#111111", fg="#333333",
                 font=("Malgun Gothic", 9)).pack(side="left", padx=4)

        # 민감도
        tk.Label(self.win, text="민감도", bg="#111111", fg="#666666",
                 font=("Malgun Gothic", 8), padx=4).pack(side="left")
        self._sens_btns = {}
        for label, val in self._SENS:
            btn = tk.Button(
                self.win, text=label,
                bg="#1e1e1e", fg="#aaaaaa",
                activebackground="#004466", activeforeground="white",
                relief="flat", font=("Malgun Gothic", 8),
                padx=7, pady=2, cursor="hand2", bd=0,
                command=lambda v=val: self._set_sens(v),
            )
            btn.pack(side="left", padx=1, pady=4)
            self._sens_btns[val] = btn

        self._refresh_buttons()

    def _set_poll(self, ms):
        self._poll_ms = ms
        self._refresh_buttons()
        self._on_change(self._poll_ms, self._threshold)

    def _set_sens(self, val):
        self._threshold = val
        self._refresh_buttons()
        self._on_change(self._poll_ms, self._threshold)

    def _refresh_buttons(self):
        for ms, btn in self._poll_btns.items():
            active = ms == self._poll_ms
            btn.config(bg="#005580" if active else "#1e1e1e",
                       fg="white"   if active else "#aaaaaa")
        for val, btn in self._sens_btns.items():
            active = val == self._threshold
            btn.config(bg="#005580" if active else "#1e1e1e",
                       fg="white"   if active else "#aaaaaa")

    def place(self, x, y, w):
        self.win.geometry(f"{w}x{_SETTINGS_H}+{x}+{y}")

    def destroy(self):
        try:
            self.win.destroy()
        except Exception:
            pass


class SelectionBox:
    """
    구조:
      [툴바] ← 이동 핸들(드래그) + 언어 토글 + 닫기 버튼  (박스 바깥 위쪽)
      [박스] ← 투명 인테리어 + 8방향 리사이즈 핸들
    """
    _CURSORS = {
        "nw": "size_nw_se", "se": "size_nw_se",
        "ne": "size_ne_sw", "sw": "size_ne_sw",
        "n":  "size_ns",    "s":  "size_ns",
        "e":  "size_we",    "w":  "size_we",
    }

    def __init__(self, root, bbox, on_change, on_move, on_close,
                 on_lang_toggle, lang_label: str,
                 on_settings, poll_ms, threshold):
        self._root           = root
        self._on_change      = on_change
        self._on_move        = on_move
        self._on_close       = on_close
        self._on_lang_toggle = on_lang_toggle
        self._on_settings    = on_settings
        self._poll_ms        = poll_ms
        self._threshold      = threshold
        self._debounce       = None
        self._dd             = {}
        self._td             = {}
        self._settings_bar   = None

        self.x = bbox["left"]
        self.y = bbox["top"]
        self.w = bbox["width"]
        self.h = bbox["height"]

        # ── 툴바 (박스 바깥 위쪽) ──
        self.bar = tk.Toplevel(root)
        self.bar.overrideredirect(True)
        self.bar.attributes("-topmost", True)
        self.bar.configure(bg="#1a1a1a")

        # 이동 핸들 레이블
        move_lbl = tk.Label(
            self.bar, text="⠿  이동", bg="#1a1a1a", fg="#888888",
            font=("Malgun Gothic", 9), cursor="fleur", padx=10,
        )
        move_lbl.pack(side="left", fill="y")
        move_lbl.bind("<ButtonPress-1>",   self._bar_press)
        move_lbl.bind("<B1-Motion>",       self._bar_drag)
        move_lbl.bind("<ButtonRelease-1>", lambda _: self._td.clear())

        # 닫기 버튼
        close_btn = tk.Button(
            self.bar, text="✕  닫기",
            bg="#1a1a1a", fg="#888888",
            activebackground="#cc3333", activeforeground="white",
            relief="flat", font=("Malgun Gothic", 9),
            padx=10, cursor="hand2", bd=0,
            command=self._close,
        )
        close_btn.pack(side="right", fill="y")

        # 언어 토글 버튼
        self._lang_var = tk.StringVar(value=lang_label)
        lang_btn = tk.Button(
            self.bar, textvariable=self._lang_var,
            bg="#1a1a1a", fg="#00aaff",
            activebackground="#003355", activeforeground="#00ccff",
            relief="flat", font=("Malgun Gothic", 9, "bold"),
            padx=10, cursor="hand2", bd=0,
            command=self._toggle_lang,
        )
        lang_btn.pack(side="right", fill="y")

        # 설정 버튼
        tk.Button(
            self.bar, text="⚙",
            bg="#1a1a1a", fg="#888888",
            activebackground="#222222", activeforeground="white",
            relief="flat", font=("Arial", 10),
            padx=8, cursor="hand2", bd=0,
            command=self._toggle_settings,
        ).pack(side="right", fill="y")

        # ── 선택 박스 (투명) ──
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", _TRANS)

        self.cv = tk.Canvas(self.win, bg=_TRANS, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self._apply_geometry()
        self._draw()

        self.cv.bind("<Motion>",          self._motion)
        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",       self._drag)
        self.cv.bind("<ButtonRelease-1>", lambda _: self._dd.clear())

    # ── 위치/크기 적용 ──
    def _apply_geometry(self):
        bar_y = max(0, self.y - _TOOLBAR_H)
        self.bar.geometry(f"{self.w}x{_TOOLBAR_H}+{self.x}+{bar_y}")
        self.win.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        if self._settings_bar:
            self._settings_bar.place(self.x, self.y + self.h, self.w)

    # ── 선택 박스 그리기 ──
    def _draw(self):
        self.cv.delete("all")
        w, h, s = self.w, self.h, _HANDLE

        self.cv.create_rectangle(1, 1, w-1, h-1,
                                  outline=_BORDER, width=2, fill=_TRANS)

        for px, py in [
            (0, 0),    (w//2, 0),   (w, 0),
            (0, h//2),               (w, h//2),
            (0, h),    (w//2, h),   (w, h),
        ]:
            self.cv.create_rectangle(
                px-s//2, py-s//2, px+s//2, py+s//2,
                fill=_BORDER, outline="white", width=1,
            )

    # ── 설정 바 토글 ──
    def _toggle_settings(self):
        if self._settings_bar:
            self._settings_bar.destroy()
            self._settings_bar = None
        else:
            self._settings_bar = SettingsBar(
                self._root,
                on_change=self._on_settings,
                poll_ms=self._poll_ms,
                threshold=self._threshold,
            )
            self._settings_bar.place(self.x, self.y + self.h, self.w)

    # ── 언어 토글 ──
    def _toggle_lang(self):
        new_label = self._on_lang_toggle()
        self._lang_var.set(new_label)

    # ── 툴바 드래그 (이동) ──
    def _bar_press(self, e):
        self._td = {
            "sx": e.x_root, "sy": e.y_root,
            "ox": self.x,   "oy": self.y,
        }

    def _bar_drag(self, e):
        if not self._td:
            return
        self.x = self._td["ox"] + e.x_root - self._td["sx"]
        self.y = self._td["oy"] + e.y_root - self._td["sy"]
        self._apply_geometry()
        self._notify_move()
        self._schedule()

    # ── 박스 리사이즈 ──
    def _dir(self, x, y) -> str:
        m = _EDGE
        w, h = self.w, self.h
        L = x < m;  R = x > w-m
        T = y < m;  B = y > h-m
        if T and L: return "nw"
        if T and R: return "ne"
        if B and L: return "sw"
        if B and R: return "se"
        if T:       return "n"
        if B:       return "s"
        if L:       return "w"
        if R:       return "e"
        return ""

    def _motion(self, e):
        d = self._dir(e.x, e.y)
        self.cv.configure(cursor=self._CURSORS.get(d, "arrow"))

    def _press(self, e):
        d = self._dir(e.x, e.y)
        if not d:
            return
        self._dd = {
            "dir": d,
            "sx": e.x_root, "sy": e.y_root,
            "ox": self.x,   "oy": self.y,
            "ow": self.w,   "oh": self.h,
        }

    def _drag(self, e):
        dd = self._dd
        if not dd:
            return
        dx = e.x_root - dd["sx"]
        dy = e.y_root - dd["sy"]
        d  = dd["dir"]
        x, y, w, h = dd["ox"], dd["oy"], dd["ow"], dd["oh"]

        if   d == "se": w += dx; h += dy
        elif d == "sw": x += dx; w -= dx; h += dy
        elif d == "ne": w += dx; y += dy; h -= dy
        elif d == "nw": x += dx; y += dy; w -= dx; h -= dy
        elif d == "e":  w += dx
        elif d == "w":  x += dx; w -= dx
        elif d == "s":  h += dy
        elif d == "n":  y += dy; h -= dy

        self.x, self.y = int(x), int(y)
        self.w, self.h = max(int(w), 60), max(int(h), 40)
        self._apply_geometry()
        self._draw()
        self._notify_move()
        self._schedule()

    def _notify_move(self):
        bbox = {"left": self.x, "top": self.y,
                "width": self.w, "height": self.h}
        self._on_move(bbox)

    def _schedule(self):
        if self._debounce:
            self._root.after_cancel(self._debounce)
        bbox = {"left": self.x, "top": self.y,
                "width": self.w, "height": self.h}
        self._debounce = self._root.after(
            DEBOUNCE_MS, lambda: self._on_change(bbox))

    def _close(self):
        self.bar.destroy()
        self.win.destroy()
        self._on_close()

    def destroy(self):
        if self._settings_bar:
            self._settings_bar.destroy()
            self._settings_bar = None
        try:
            self.bar.destroy()
            self.win.destroy()
        except Exception:
            pass


# ── 번역 결과 패널 ──────────────────────────────────────────
class TranslationPanel:
    def __init__(self, root, bbox):
        self._root       = root
        self._hd         = {}
        self._user_moved = False   # 수동 이동 시 True → 박스 추적 중단

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#1c1c1c")

        # 헤더 (드래그로 패널 이동)
        hdr = tk.Frame(self.win, bg="#2a2a2a", height=28)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="번역", bg="#2a2a2a", fg="#888888",
                 font=("Malgun Gothic", 9)).pack(side="left", padx=8, pady=4)
        tk.Button(hdr, text="×", bg="#2a2a2a", fg="#888888",
                  activebackground="#cc3333", activeforeground="white",
                  relief="flat", font=("Arial", 11, "bold"),
                  command=self.close, cursor="hand2",
                  bd=0, padx=8).pack(side="right")

        # 핀 해제 버튼 (수동 이동 후 박스 따라다니기 복원, 평소엔 숨김)
        self._pin_btn = tk.Button(
            hdr, text="📌", bg="#2a2a2a", fg="#aaaaaa",
            activebackground="#333333",
            relief="flat", font=("Arial", 9),
            command=self._unpin, cursor="hand2",
            bd=0, padx=6,
        )

        hdr.bind("<ButtonPress-1>",   self._hdr_press)
        hdr.bind("<B1-Motion>",       self._hdr_drag)
        hdr.bind("<ButtonRelease-1>", self._hdr_release)

        # 텍스트 영역
        self.txt = tk.Text(
            self.win, wrap="word",
            bg="#1c1c1c", fg="#e8e8e8",
            font=("Malgun Gothic", 11),
            relief="flat", padx=12, pady=10,
            insertbackground="white",
            state="disabled",
        )
        self.txt.pack(fill="both", expand=True)

        # 하단 버튼
        bar = tk.Frame(self.win, bg="#222222", pady=6)
        bar.pack(fill="x")
        tk.Button(bar, text="복사", command=self._copy,
                  bg="#0078d4", fg="white", activebackground="#005fa3",
                  relief="flat", font=("Malgun Gothic", 9),
                  padx=14, pady=3, cursor="hand2", bd=0,
                  ).pack(side="left", padx=10)

        self._reposition(bbox)
        self.set_loading()

    def _reposition(self, bbox):
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        pw = PANEL_WIDTH
        ph = max(bbox["height"], 160)
        px = bbox["left"] + bbox["width"] + 16
        py = bbox["top"]

        if px + pw > sw:
            px = max(0, bbox["left"] - pw - 16)
        if py + ph > sh:
            py = max(0, sh - ph - 40)

        self.win.geometry(f"{pw}x{ph}+{px}+{py}")

    def follow(self, bbox):
        """박스 이동/리사이즈 시 호출 — 수동 이동 전까지만 따라감."""
        if not self._user_moved:
            self._reposition(bbox)

    def set_loading(self):
        self._write("번역 중...")

    def set_text(self, text):
        self._write(text)

    def _write(self, text):
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", text)
        self.txt.config(state="disabled")

    def _copy(self):
        txt = self.txt.get("1.0", "end").strip()
        self._root.clipboard_clear()
        self._root.clipboard_append(txt)

    def _hdr_press(self, e):
        self._hd = {"sx": e.x_root, "sy": e.y_root,
                    "wx": self.win.winfo_x(), "wy": self.win.winfo_y(),
                    "moved": False}

    def _hdr_drag(self, e):
        if not self._hd:
            return
        nx = self._hd["wx"] + e.x_root - self._hd["sx"]
        ny = self._hd["wy"] + e.y_root - self._hd["sy"]
        self.win.geometry(f"+{nx}+{ny}")
        self._hd["moved"] = True

    def _hdr_release(self, e):
        if self._hd.get("moved"):
            self._user_moved = True
            self._pin_btn.pack(side="right")   # 📌 버튼 표시
        self._hd.clear()

    def _unpin(self):
        """박스 추적 복원."""
        self._user_moved = False
        self._pin_btn.pack_forget()

    def close(self):
        try:
            self.win.destroy()
        except Exception:
            pass


# ── 트레이 아이콘 이미지 생성 ────────────────────────────────
def _icon_path() -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "icon.ico")
    return os.path.join(os.path.dirname(__file__), "icon.ico")

def _make_tray_image(active: bool = False) -> Image.Image:
    # 활성/비활성 모두 완전 불투명 (반투명 처리 제거)
    return Image.open(_icon_path()).convert("RGBA").resize((64, 64), Image.LANCZOS)


# ── 메인 앱 ────────────────────────────────────────────────
def _lang_label(target: str) -> str:
    return "EN→KO" if target == "ko" else "KO→EN"


class ScreenTranslator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self._active      = False
        self._box         = None
        self._panel       = None
        self._target_lang = TARGET_LANG
        self._last_bbox   = None
        self._last_arr    = None
        self._last_text   = None
        self._poll_id     = None
        self._poll_ms     = POLL_MS
        self._threshold   = CHANGE_THRESHOLD
        self._tray        = None

    # ── 트레이 아이콘 ──
    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("jundeve.com", self._open_site),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("번역 시작  ([[[)", self._tray_activate),
            pystray.MenuItem("번역 종료  (]]])", self._tray_deactivate),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("사용법 보기", self._open_readme),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._exit_app),
        )
        self._tray = pystray.Icon(
            "ScreenTranslator",
            _make_tray_image(active=False),
            "Screen Translator",
            menu,
        )
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _tray_idle(self):
        if self._tray:
            self._tray.icon  = _make_tray_image(active=False)
            self._tray.title = "Screen Translator"

    def _tray_active(self):
        if self._tray:
            self._tray.icon  = _make_tray_image(active=True)
            self._tray.title = "Screen Translator"

    def _open_site(self, icon=None, item=None):
        import webbrowser
        webbrowser.open("https://jundeve.com/")

    def _open_readme(self, icon=None, item=None):
        import webbrowser
        webbrowser.open("https://github.com/JunDeve/Real-time-Screen-Detecting-Translator#readme")

    def _tray_activate(self, icon=None, item=None):
        self.root.after(0, self._activate)

    def _tray_deactivate(self, icon=None, item=None):
        self.root.after(0, self._deactivate)

    def _exit_app(self, icon=None, item=None):
        # 트레이 콜백 스레드에서 호출됨 → 트레이만 여기서 멈추고
        # Tk 위젯 정리는 반드시 메인 스레드로 위임 (Tk는 스레드 안전하지 않음)
        if self._tray:
            self._tray.stop()
            self._tray = None
        self.root.after(0, self._do_exit)

    def _do_exit(self):
        # 메인 스레드: 키보드 후킹 해제 + 위젯 정리 후 종료 메시지
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self._cleanup()
        self._show_exit_msg()

    def _shutdown(self):
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        # 남아있는 데몬 스레드(keyboard 리스너 등)와 무관하게 즉시 종료
        os._exit(0)

    def _show_exit_msg(self):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg="#1e1e1e")
        tk.Label(win, text="Screen Translator 종료됨",
                 bg="#1e1e1e", fg="#aaaaaa",
                 font=("Segoe UI", 11, "bold"), padx=20, pady=10).pack()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{sw - w - 24}+{sh - h - 64}")
        win.after(1500, self._shutdown)

    def _activate(self):
        if self._active:
            return
        self._active = True
        self._tray_active()
        self.root.after(0, lambda: SelectionOverlay(
            self.root, self._on_selected, self._on_overlay_cancelled))

    def _on_selected(self, bbox):
        self._active = False
        self._cleanup()
        self.root.after(150, lambda: self._build_ui(bbox))

    def _on_overlay_cancelled(self):
        self._active = False
        self._tray_idle()

    def _build_ui(self, bbox):
        self._last_bbox = bbox
        self._last_arr  = None
        self._last_text = None
        self._panel = TranslationPanel(self.root, bbox)
        self._box   = SelectionBox(
            self.root, bbox,
            on_change=self._on_box_changed,
            on_move=self._on_box_moved,
            on_close=self._cleanup,
            on_lang_toggle=self._toggle_lang,
            lang_label=_lang_label(self._target_lang),
            on_settings=self._on_settings_changed,
            poll_ms=self._poll_ms,
            threshold=self._threshold,
        )
        self._do_translate(bbox)
        self._start_poll()

    def _on_box_moved(self, bbox):
        """박스 이동 중 즉시 호출 — 패널 위치만 갱신 (번역 없음)."""
        self._last_bbox = bbox
        if self._panel:
            self._panel.follow(bbox)

    def _on_box_changed(self, bbox):
        """디바운스 후 호출 — 재번역."""
        self._last_bbox = bbox
        self._last_arr  = None   # 박스 변경 시 캐시 초기화
        self._last_text = None
        if self._panel:
            self._panel.set_loading()
        self._do_translate(bbox)

    def _start_poll(self):
        self._stop_poll()
        self._poll_id = self.root.after(self._poll_ms, self._poll)

    def _stop_poll(self):
        if self._poll_id:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None

    def _poll(self):
        if not self._box or not self._panel or not self._last_bbox:
            return
        bbox = self._last_bbox

        def worker():
            try:
                with mss.mss() as sct:
                    raw = sct.grab({
                        "left":   bbox["left"],
                        "top":    bbox["top"],
                        "width":  bbox["width"],
                        "height": bbox["height"],
                    })
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                arr = np.array(img, dtype=np.float32)

                # ── 1단계: 픽셀 비교 (매우 빠름) ──
                if self._last_arr is not None and self._last_arr.shape == arr.shape:
                    diff = np.mean(np.abs(arr - self._last_arr))
                    if diff <= self._threshold:
                        return   # 변화 없음 → OCR 스킵
                self._last_arr = arr

                # ── 2단계: OCR 실행 후 텍스트 비교 ──
                text = ocr_image(img, self._target_lang)
                if text == self._last_text:
                    return   # 배경만 바뀜 → 번역 스킵
                self._last_text = text

                # ── 3단계: 번역 ──
                result = do_translate(text, self._target_lang)
                self.root.after(0, self._show_result, result)

            except Exception:
                pass
            finally:
                # 다음 폴링 예약
                self.root.after(0, self._start_poll)

        threading.Thread(target=worker, daemon=True).start()

    def _on_settings_changed(self, poll_ms: int, threshold: int):
        self._poll_ms   = poll_ms
        self._threshold = threshold
        self._start_poll()   # 새 주기로 즉시 재시작

    def _toggle_lang(self) -> str:
        self._target_lang = "en" if self._target_lang == "ko" else "ko"
        self._last_text   = None   # 언어 바뀌면 텍스트 캐시 초기화 → 재번역 강제
        label = _lang_label(self._target_lang)
        if self._last_bbox and self._panel:
            self._panel.set_loading()
            self._do_translate(self._last_bbox)
        return label

    def _do_translate(self, bbox):
        target = self._target_lang

        def worker():
            try:
                with mss.mss() as sct:
                    raw = sct.grab({
                        "left":   bbox["left"],
                        "top":    bbox["top"],
                        "width":  bbox["width"],
                        "height": bbox["height"],
                    })
                img    = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                result = translate_image(img, target)
            except Exception as e:
                result = f"오류:\n{e}"
            self.root.after(0, self._show_result, result)

        threading.Thread(target=worker, daemon=True).start()

    def _show_result(self, text):
        if self._panel:
            self._panel.set_text(text)

    def _cleanup(self):
        self._stop_poll()
        self._last_arr  = None
        self._last_text = None
        self._tray_idle()
        if self._box:
            try:
                self._box.destroy()
            except Exception:
                pass
            self._box = None
        if self._panel:
            self._panel.close()
            self._panel = None

    def _deactivate(self):
        """]]]: 현재 번역 세션 종료."""
        self.root.after(0, self._cleanup)

    def run(self):
        self._setup_tray()
        TripleKeyDetector(TRIPLE_KEY_OPEN,  self._activate)
        TripleKeyDetector(TRIPLE_KEY_CLOSE, self._deactivate)
        if pyi_splash:
            pyi_splash.close()   # 트레이·단축키 준비 완료 → 로딩 화면 닫기
        self.root.after(300, self._show_startup_msg)
        self.root.mainloop()

    def _show_startup_msg(self):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg="#1e1e1e")
        tk.Label(win, text="Screen Translator 시작됨",
                 bg="#1e1e1e", fg="white",
                 font=("Segoe UI", 11, "bold"), padx=20, pady=8).pack()
        tk.Label(win, text="우측 하단 트레이 아이콘에서 확인하세요\n[[[ 켜기     ]]] 끄기",
                 bg="#1e1e1e", fg="#aaaaaa",
                 font=("Segoe UI", 9), padx=20, pady=4).pack()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{sw - w - 24}+{sh - h - 64}")
        win.after(2500, win.destroy)


# ── 단일 인스턴스 보장 (중복 실행 방지) ──────────────────────
# 핸들을 전역에 보관해야 GC로 뮤텍스가 해제되지 않음
_INSTANCE_MUTEX = None
_MUTEX_NAME     = "Global\\JunDeve_ScreenTranslator_SingleInstance"

def _ensure_single_instance() -> bool:
    """이미 실행 중이면 False. 처음 실행이면 True."""
    global _INSTANCE_MUTEX
    ERROR_ALREADY_EXISTS = 183
    kernel32 = ctypes.windll.kernel32
    _INSTANCE_MUTEX = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    return kernel32.GetLastError() != ERROR_ALREADY_EXISTS


if __name__ == "__main__":
    if not _ensure_single_instance():
        # 이미 실행 중 → 안내 후 종료 (콘솔 없는 창 모드 대비 MessageBox 사용)
        ctypes.windll.user32.MessageBoxW(
            0,
            "Screen Translator가 이미 실행 중입니다.\n우측 하단 트레이 아이콘을 확인하세요.",
            "Screen Translator",
            0x40,  # MB_ICONINFORMATION
        )
        sys.exit(0)

    app = ScreenTranslator()
    app.run()
