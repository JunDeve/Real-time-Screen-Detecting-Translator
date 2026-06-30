"""스플래시 이미지(splash.png) 생성 — 빌드 시 1회만 실행하는 보조 스크립트."""
from PIL import Image, ImageDraw, ImageFont
import os

BASE = os.path.dirname(os.path.abspath(__file__))
W, H = 360, 200

img = Image.new("RGBA", (W, H), (24, 24, 24, 255))
draw = ImageDraw.Draw(img)

# 테두리
draw.rectangle([0, 0, W - 1, H - 1], outline=(0, 170, 255, 255), width=2)

# 아이콘
try:
    icon = Image.open(os.path.join(BASE, "icon.ico")).convert("RGBA")
    icon = icon.resize((64, 64), Image.LANCZOS)
    img.paste(icon, (W // 2 - 32, 36), icon)
except Exception as e:
    print("icon load failed:", e)

# 텍스트
def _font(size):
    for name in ("malgun.ttf", "C:\\Windows\\Fonts\\malgun.ttf", "C:\\Windows\\Fonts\\malgunbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

title_font = _font(16)
sub_font   = _font(11)

title = "Screen Translator"
sub   = "불러오는 중...  Loading..."

tb = draw.textbbox((0, 0), title, font=title_font)
draw.text(((W - (tb[2] - tb[0])) // 2, 112), title, fill="white", font=title_font)

sb = draw.textbbox((0, 0), sub, font=sub_font)
draw.text(((W - (sb[2] - sb[0])) // 2, 140), sub, fill="#aaaaaa", font=sub_font)

out = os.path.join(BASE, "splash.png")
img.save(out)
print("saved:", out)
