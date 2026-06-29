"""
화면 번역기 — Screen Translator
단축키 : \\\ (백슬래시 3번 빠르게)
동작   : 화면 어두워짐 → 드래그로 영역 선택 → 원본 우측에 번역 결과 표시
         선택 박스는 이동 / 리사이즈 가능 → 변경 시 자동 재번역
ESC    : 취소

번역 방식: EasyOCR (로컬 텍스트 인식) + Google Translate (무료, API 키 불필요)
"""

import tkinter as tk
import threading
import time
import numpy as np

import keyboard
import mss
from PIL import Image
import easyocr
from deep_translator import GoogleTranslator

from config import (
    TARGET_LANG, OCR_LANGS,
    TRIPLE_KEY_OPEN, TRIPLE_KEY_CLOSE, TRIPLE_INTERVAL,
    DEBOUNCE_MS, PANEL_WIDTH, POLL_MS, CHANGE_THRESHOLD,
)

# EasyOCR 리더 — 앱 시작 시 한 번만 로드 (수 초 소요)
print("OCR 모델 로딩 중...")
_reader = easyocr.Reader(OCR_LANGS, gpu=False, verbose=False)
print("OCR 모델 로드 완료.")

# 투명 처리에 사용할 색상 (이 색상이 윈도우에서 완전 투명 처리됨)
_TRANS  = "#fefefe"
_BORDER = "#00aaff"
_HANDLE = 10   # 핸들 크기(px)
_EDGE   = 14   # 리사이즈 감지 여백(px)


# ── OCR + 번역 ──────────────────────────────────────────────
def translate_image(img: Image.Image, target_lang: str = "ko") -> str:
    arr = np.array(img)
    results = _reader.readtext(arr, detail=0, paragraph=True)
    text = "\n".join(results).strip()

    if not text:
        return "[인식된 텍스트 없음]"

    try:
        translated = GoogleTranslator(
            source="auto", target=target_lang
        ).translate(text)
        return translated or text
    except Exception as e:
        return f"[번역 오류: {e}]\n\n원문:\n{text}"


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
    def __init__(self, root, on_select):
        self._root = root
        self._on_select = on_select
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
        self.win.bind("<Escape>", lambda _: self.win.destroy())

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
        x1 = min(self._sx, e.x_root)
        y1 = min(self._sy, e.y_root)
        x2 = max(self._sx, e.x_root)
        y2 = max(self._sy, e.y_root)
        self.win.destroy()
        if x2 - x1 > 20 and y2 - y1 > 20:
            self._on_select({"left": x1, "top": y1,
                             "width": x2 - x1, "height": y2 - y1})


# ── 이동/리사이즈 가능한 선택 박스 ─────────────────────────
_TOOLBAR_H = 30   # 툴바 높이

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
                 on_lang_toggle, lang_label: str):
        self._root           = root
        self._on_change      = on_change
        self._on_move        = on_move        # 즉시 호출 (패널 위치 갱신용)
        self._on_close       = on_close
        self._on_lang_toggle = on_lang_toggle
        self._debounce       = None
        self._dd             = {}   # 리사이즈 드래그 데이터
        self._td             = {}   # 툴바 드래그 데이터

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
        self._last_arr    = None   # 직전 캡처 이미지 (변화 감지용)
        self._poll_id     = None   # after() 핸들

    def _activate(self):
        if self._active:
            return
        self._active = True
        self.root.after(0, lambda: SelectionOverlay(self.root, self._on_selected))

    def _on_selected(self, bbox):
        self._active = False
        self._cleanup()
        self.root.after(150, lambda: self._build_ui(bbox))

    def _build_ui(self, bbox):
        self._last_bbox = bbox
        self._last_arr  = None
        self._panel = TranslationPanel(self.root, bbox)
        self._box   = SelectionBox(
            self.root, bbox,
            on_change=self._on_box_changed,
            on_move=self._on_box_moved,
            on_close=self._cleanup,
            on_lang_toggle=self._toggle_lang,
            lang_label=_lang_label(self._target_lang),
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
        if self._panel:
            self._panel.set_loading()
        self._do_translate(bbox)

    def _start_poll(self):
        self._stop_poll()
        self._poll_id = self.root.after(POLL_MS, self._poll)

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

                changed = False
                if self._last_arr is None or self._last_arr.shape != arr.shape:
                    changed = True
                else:
                    diff = np.mean(np.abs(arr - self._last_arr))
                    changed = diff > CHANGE_THRESHOLD

                if changed:
                    self._last_arr = arr
                    result = translate_image(img, self._target_lang)
                    self.root.after(0, self._show_result, result)
            except Exception:
                pass
            # 다음 폴링 예약
            self.root.after(0, self._start_poll)

        threading.Thread(target=worker, daemon=True).start()

    def _toggle_lang(self) -> str:
        self._target_lang = "en" if self._target_lang == "ko" else "ko"
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
        self._last_arr = None
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
        print("=" * 44)
        print("  화면 번역기 실행 중")
        print("  켜기     : [[[  ([ 3번 빠르게)")
        print("  끄기     : ]]]  (] 3번 빠르게) 또는 닫기 버튼")
        print(f"  번역 언어: {self._target_lang}  (툴바 EN<->KO 버튼으로 전환)")
        print("=" * 44)
        TripleKeyDetector(TRIPLE_KEY_OPEN,  self._activate)
        TripleKeyDetector(TRIPLE_KEY_CLOSE, self._deactivate)
        self.root.mainloop()


if __name__ == "__main__":
    app = ScreenTranslator()
    app.run()
