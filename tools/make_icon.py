#!/usr/bin/env python3
"""
Make the app icons from your logo, or a placeholder from the brand initials.

    python tools/make_icon.py                 # uses brand/logo.png if present, else initials
    python tools/make_icon.py --logo my.png   # use a specific image

Writes brand/icons/app.ico (window, taskbar, installer) and brand/icons/app_inactive.ico
(the grey tray icon shown while the phone is not registered). Needs Pillow:  pip install pillow
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

KIT = Path(__file__).resolve().parent.parent
SIZES = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]
FONTS = ["DejaVuSans-Bold.ttf", "segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf"]


def hex_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(size: int):
    for f in FONTS:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def placeholder(name: str, primary, accent) -> Image.Image:
    s = 1024  # draw large, scale down for sharp small sizes
    # rounded-square shape, used as a mask so the accent corner stays inside it
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((32, 32, s - 32, s - 32), radius=220, fill=255)
    art = Image.new("RGBA", (s, s), primary + (255,))
    ImageDraw.Draw(art).ellipse((s - 330, s - 330, s + 330, s + 330), fill=accent + (255,))
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.paste(art, (0, 0), mask)
    d = ImageDraw.Draw(img)
    words = name.split()
    ini = (words[0][0] + (words[1][0] if len(words) > 1 else "")).upper()
    f = font(500 if len(ini) == 1 else 430)
    box = d.textbbox((0, 0), ini, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((s - w) / 2 - box[0], (s - h) / 2 - box[1] - 20), ini, font=f, fill=(255, 255, 255, 255))
    return img


def from_logo(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    return canvas.resize((1024, 1024), Image.LANCZOS)


def grey(img: Image.Image) -> Image.Image:
    r, g, b, a = img.split()
    l = ImageOps.grayscale(Image.merge("RGB", (r, g, b)))
    l = l.point(lambda v: int(v * 0.75 + 40))
    return Image.merge("RGBA", (l, l, l, a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logo", type=Path, default=KIT / "brand" / "logo.png")
    ap.add_argument("--brand", type=Path, default=KIT / "brand" / "brand.json")
    args = ap.parse_args()
    b = json.loads(args.brand.read_text(encoding="utf-8"))
    out = KIT / "brand" / "icons"
    out.mkdir(parents=True, exist_ok=True)

    if args.logo.is_file():
        big = from_logo(args.logo)
        src = f"logo {args.logo.name}"
    else:
        big = placeholder(b["name"], hex_rgb(b.get("colour", "#0b6e4f")), hex_rgb(b.get("accent", "#f2a900")))
        src = "placeholder initials"

    big.save(out / "app.ico", sizes=SIZES)
    grey(big).save(out / "app_inactive.ico", sizes=SIZES)
    big.resize((256, 256), Image.LANCZOS).save(out / "app-256.png")
    print(f"Icons written to {out} (from {src})")


if __name__ == "__main__":
    main()
