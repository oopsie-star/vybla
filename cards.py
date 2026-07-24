"""1080x1920 story-card generator (Pillow)."""
import os
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import BOT_USERNAME

W, H = 1080, 1920
ASSETS = os.path.join(os.path.dirname(__file__), "assets")
FONT_PATHS = [
    os.path.join(ASSETS, "Montserrat-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
]
LOGO_PATH = os.path.join(ASSETS, "logo.png")

# 12 gradient presets (top RGB -> bottom RGB).
GRADIENTS = {
    "purple_pink": ((124, 58, 237), (236, 72, 153)),
    "red_black":   ((220, 38, 38), (10, 10, 10)),
    "blue_cyan":   ((37, 99, 235), (34, 211, 238)),
    "black_gray":  ((17, 17, 17), (75, 85, 99)),
    "sunset":      ((249, 115, 22), (219, 39, 119)),
    "mint":        ((16, 185, 129), (5, 150, 105)),
    "gold":        ((245, 158, 11), (120, 53, 15)),
    "indigo":      ((79, 70, 229), (30, 27, 75)),
    "rose":        ((244, 63, 94), (76, 5, 25)),
    "teal":        ((13, 148, 136), (8, 51, 68)),
    "violet":      ((139, 92, 246), (30, 27, 75)),
    "slate":       ((51, 65, 85), (15, 23, 42)),
}
MODE_GRADIENT = {
    "compliment": "purple_pink",
    "redflag": "red_black",
    "crush": "blue_cyan",
    "custom": "black_gray",
    "voice": "indigo",
}


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:  # Pillow >= 10.1 supports sized default font
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _gradient(top: tuple, bottom: tuple) -> Image.Image:
    base = Image.new("RGB", (1, H))
    for y in range(H):
        r = y / (H - 1)
        base.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * r) for i in range(3)))
    return base.resize((W, H))


def _draw_text_block(draw: ImageDraw.ImageDraw, text: str, font, cy: int):
    """Center-wrap text horizontally, vertically centered around cy, with shadow."""
    wrapped = textwrap.fill(text, width=18)
    lines = wrapped.split("\n")
    ascent, descent = font.getmetrics()
    line_h = int((ascent + descent) * 1.15)
    total_h = line_h * len(lines)
    y = cy - total_h // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2
        draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0, 160))   # shadow
        draw.text((x, y), line, font=font, fill=(255, 255, 255))          # text
        y += line_h


def _circle_avatar(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGBA").resize((size, size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


def generate_vibe_card(text: str, mode: str, avatar_path: str | None = None,
                       watermark: bool = True) -> str:
    """Render a card and return its filesystem path (PNG)."""
    grad_key = MODE_GRADIENT.get(mode, "black_gray")
    top, bottom = GRADIENTS[grad_key]
    card = _gradient(top, bottom).convert("RGBA")

    # subtle darkening vignette for text legibility
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 60))
    card = Image.alpha_composite(card, overlay)
    draw = ImageDraw.Draw(card)

    top_of_text = 360
    # avatar circle near the top
    if avatar_path and os.path.exists(avatar_path):
        try:
            av = _circle_avatar(Image.open(avatar_path), 200)
            ring = Image.new("RGBA", (216, 216), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((0, 0, 216, 216), fill=(255, 255, 255, 255))
            ring.paste(av, (8, 8), av)
            card.paste(ring, ((W - 216) // 2, 150), ring)
            top_of_text = 460
        except Exception:
            pass

    _draw_text_block(draw, text, _font(70), cy=(top_of_text + H - 260) // 2)

    if watermark:
        wm_font = _font(34)
        wm = f"VYBLA • t.me/{BOT_USERNAME}"
        bbox = draw.textbbox((0, 0), wm, font=wm_font)
        draw.text(((W - (bbox[2] - bbox[0])) // 2, H - 110), wm, font=wm_font,
                  fill=(255, 255, 255, 210))
        if os.path.exists(LOGO_PATH):
            try:
                logo = Image.open(LOGO_PATH).convert("RGBA")
                logo.thumbnail((90, 90))
                card.paste(logo, ((W - logo.width) // 2, H - 210), logo)
            except Exception:
                pass

    out = tempfile.NamedTemporaryFile(suffix=".png", delete=False,
                                      dir=tempfile.gettempdir())
    card.convert("RGB").save(out.name, "PNG")
    out.close()
    return out.name
