"""Render the repo's generated images: the README banner and the Odoo app icon.

The banner is schematic, not a screenshot: a booking card walking the
salon.booking state machine while the loyalty ledger posts its entry.

Run: python3 docs/make_assets.py
"""

import pathlib
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 2  # supersampling factor, downsampled at the end for clean edges
W, H = 1000 * S, 372 * S
FRAMES, FPS = 60, 15

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
REGULAR, BOLD, MEDIUM, LIGHT = 0, 1, 10, 7

INK = (245, 240, 244)
MUTED = (150, 132, 146)
DIM = (98, 84, 96)
PURPLE = (113, 75, 103)      # Odoo brand purple
LILAC = (201, 166, 190)
GREEN = (61, 199, 138)
AMBER = (232, 168, 78)
CARD = (44, 31, 46)
EDGE = (69, 51, 71)

STATES = [
    ("DRAFT", DIM),
    ("CONFIRMED", LILAC),
    ("IN SERVICE", AMBER),
    ("DONE", GREEN),
]

BOARD_X, BOARD_Y = 40 * S, 126 * S
COL_W, COL_GAP, COL_H = 214 * S, 20 * S, 138 * S
CARD_W, CARD_H = 190 * S, 104 * S


def font(size, index=REGULAR):
    return ImageFont.truetype(FONT, size * S, index=index)


F_TITLE = font(30, BOLD)
F_SUB = font(12, MEDIUM)
F_COL = font(10, BOLD)
F_CARD = font(13, BOLD)
F_BODY = font(11, REGULAR)
F_TINY = font(9, MEDIUM)
F_PILL = font(9, BOLD)


def ease(t):
    """Cubic ease-in-out on a 0..1 progress value."""
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def background():
    img = Image.new("RGB", (W, H), (20, 14, 24))
    d = ImageDraw.Draw(img)
    for y in range(H):  # vertical gradient
        t = y / H
        d.line([(0, y), (W, y)], fill=lerp((32, 21, 37), (17, 12, 21), t))
    # soft purple glow behind the title
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([-200 * S, -240 * S, 560 * S, 200 * S], fill=(74, 45, 68))
    glow = glow.filter(ImageFilter.GaussianBlur(90 * S))
    return Image.blend(img, Image.blend(img, glow, 0.55), 0.6)


def pill(d, xy, text, fg, bg, f=F_PILL, pad=(9, 5)):
    x, y = xy
    w = d.textlength(text, font=f)
    box = [x, y, x + w + pad[0] * 2 * S, y + 17 * S]
    d.rounded_rectangle(box, radius=9 * S, fill=bg)
    d.text((x + pad[0] * S, y + pad[1] * S - 1 * S), text, font=f, fill=fg)
    return box[2] - box[0]


def draw_header(d):
    d.text((40 * S, 28 * S), "Salon ERP", font=F_TITLE, fill=INK)
    d.text(
        (40 * S, 72 * S),
        "Bookings · Staff · Services · Loyalty",
        font=F_SUB,
        fill=MUTED,
    )
    # right-aligned build tags
    tags = [("ODOO 19.0", LILAC, (58, 38, 54)), ("LGPL-3", MUTED, (40, 30, 42))]
    x = W - 40 * S
    for text, fg, bg in reversed(tags):
        w = d.textlength(text, font=F_PILL) + 18 * S
        pill(d, (x - w, 40 * S), text, fg, bg)
        x -= w + 8 * S


def draw_columns(d, active):
    for i, (label, color) in enumerate(STATES):
        x = BOARD_X + i * (COL_W + COL_GAP)
        live = i == active
        d.rounded_rectangle(
            [x, BOARD_Y, x + COL_W, BOARD_Y + COL_H],
            radius=10 * S,
            fill=(35, 24, 38) if live else (28, 19, 31),
            outline=lerp(EDGE, color, 0.55) if live else EDGE,
            width=(2 if live else 1) * S,
        )
        d.ellipse(
            [x + 14 * S, BOARD_Y - 20 * S, x + 21 * S, BOARD_Y - 13 * S],
            fill=color if live else DIM,
        )
        d.text(
            (x + 28 * S, BOARD_Y - 23 * S),
            label,
            font=F_COL,
            fill=color if live else DIM,
        )


def draw_card(d, x, y, accent, paid):
    d.rounded_rectangle(
        [x, y, x + CARD_W, y + CARD_H], radius=9 * S, fill=CARD, outline=EDGE, width=1 * S
    )
    d.rounded_rectangle([x, y, x + 4 * S, y + CARD_H], radius=2 * S, fill=accent)
    d.text((x + 16 * S, y + 13 * S), "BK2609-0042", font=F_CARD, fill=INK)
    d.text((x + 16 * S, y + 34 * S), "Anna Reed", font=F_BODY, fill=MUTED)
    d.text((x + 16 * S, y + 51 * S), "Signature Haircut · 45 min", font=F_TINY, fill=DIM)
    d.text((x + 16 * S, y + 68 * S), "Maya · 10:00", font=F_TINY, fill=DIM)
    label, fg, bg = (
        ("PAID", GREEN, (24, 52, 40)) if paid else ("UNPAID", AMBER, (56, 41, 24))
    )
    w = d.textlength(label, font=F_PILL) + 18 * S
    pill(d, (x + CARD_W - w - 14 * S, y + 66 * S), label, fg, bg)


def draw_ledger(d, reveal):
    y = 288 * S
    d.text((40 * S, y), "salon.loyalty.ledger", font=F_TINY, fill=DIM)
    d.line([(40 * S, y + 18 * S), (W - 40 * S, y + 18 * S)], fill=(46, 33, 48), width=1 * S)
    if reveal <= 0:
        d.text((40 * S, y + 32 * S), "awaiting checkout…", font=F_BODY, fill=DIM)
        return
    fade = lambda c: lerp((28, 19, 31), c, reveal)
    d.text((40 * S, y + 32 * S), "earn", font=F_BODY, fill=fade(GREEN))
    d.text((100 * S, y + 32 * S), "Anna Reed", font=F_BODY, fill=fade(INK))
    d.text(
        (230 * S, y + 32 * S),
        "Points earned for BK2609-0042",
        font=F_BODY,
        fill=fade(MUTED),
    )
    d.text((W - 190 * S, y + 32 * S), "+10 pts", font=F_CARD, fill=fade(GREEN))
    d.text((W - 96 * S, y + 32 * S), "bal 34", font=F_BODY, fill=fade(MUTED))


def frame(i):
    """Timeline: settle, three slides with holds, then the ledger posts."""
    img = background()
    d = ImageDraw.Draw(img)
    draw_header(d)

    steps = [(6, 16), (22, 32), (38, 48)]  # (slide start, slide end) per hop
    pos, active = 0.0, 0
    for hop, (a, b) in enumerate(steps):
        if i >= b:
            pos, active = hop + 1.0, hop + 1
        elif i > a:
            t = ease((i - a) / (b - a))
            pos, active = hop + t, hop + (1 if t > 0.5 else 0)

    draw_columns(d, active)
    x = BOARD_X + 12 * S + pos * (COL_W + COL_GAP)
    accent = lerp(STATES[max(0, active - 1)][1], STATES[active][1], pos % 1 or 1)
    draw_card(d, x, BOARD_Y + 14 * S, accent, paid=i >= 32)
    draw_ledger(d, min(1.0, max(0.0, (i - 48) / 8)))
    return img.resize((W // S, H // S), Image.LANCZOS)


def make_hero_banner():
    """Wide static README hero: wordmark, strapline, spec pills, scissors mark."""
    k = 2
    w, h = 1280 * k, 340 * k
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp((42, 27, 39), (18, 13, 22), y / h))

    # Soft brand glow behind the right-hand mark.
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [w - 620 * k, -220 * k, w + 180 * k, h + 180 * k], fill=(96, 58, 88)
    )
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(120 * k)), 0.5)
    d = ImageDraw.Draw(img)

    # Oversized scissors mark, bleeding off the right edge.
    mark = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mark)
    cx, cy, sc = 1105 * k, 170 * k, 2.45 * k
    px = lambda x, y: (cx + (x - 70) * sc, cy + (y - 70) * sc)
    for a, b in (((55, 93), (101, 29)), ((85, 93), (39, 29))):
        md.line([px(*a), px(*b)], fill=90, width=int(8 * sc))
        for pt in (a, b):
            r = 4 * sc
            x, y = px(*pt)
            md.ellipse([x - r, y - r, x + r, y + r], fill=90)
    for ox in (42, 98):
        x, y = px(ox, 106)
        r = 18 * sc
        md.ellipse([x - r, y - r, x + r, y + r], outline=90, width=int(7 * sc))
    img.paste(Image.new("RGB", (w, h), (255, 255, 255)), mask=mark)
    d = ImageDraw.Draw(img)

    d.text((72 * k, 88 * k), "Salon ERP", font=ImageFont.truetype(FONT, 62 * k, index=BOLD), fill=INK)
    d.text(
        (76 * k, 168 * k),
        "Appointments  ·  Staff scheduling  ·  Service catalogue  ·  Loyalty ledger",
        font=ImageFont.truetype(FONT, 17 * k, index=MEDIUM),
        fill=(178, 156, 172),
    )
    x = 74 * k
    f = ImageFont.truetype(FONT, 11 * k, index=BOLD)
    for text, fg, bg in (
        ("ODOO 19.0", LILAC, (62, 40, 58)),
        ("PYTHON 3.12+", (168, 190, 210), (38, 46, 58)),
        ("MULTI-COMPANY", (150, 200, 178), (30, 50, 43)),
        ("LGPL-3", MUTED, (44, 33, 46)),
    ):
        tw = d.textlength(text, font=f) + 26 * k
        d.rounded_rectangle([x, 212 * k, x + tw, 240 * k], radius=14 * k, fill=bg)
        d.text((x + 13 * k, 219 * k), text, font=f, fill=fg)
        x += tw + 10 * k

    out = pathlib.Path(__file__).parent / "banner.png"
    img.resize((w // k, h // k), Image.LANCZOS).save(out, optimize=True)
    print(out.name, out.stat().st_size // 1024, "KB")


def make_icon():
    """Odoo Apps tile: scissors on the brand purple."""
    k, size = 6, 140  # k = supersampling
    img = Image.new("RGB", (size * k, size * k), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(size * k):  # purple gradient tile
        d.line([(0, y), (size * k, y)], fill=lerp((138, 92, 126), (86, 55, 78), y / (size * k)))
    mask = Image.new("L", (size * k, size * k), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size * k - 1, size * k - 1], radius=30 * k, fill=255
    )
    tile = Image.new("RGB", (size * k, size * k), (255, 255, 255))
    tile.paste(img, mask=mask)

    d = ImageDraw.Draw(tile)
    w = 8 * k
    for (x0, y0), (x1, y1) in (((55, 93), (101, 29)), ((85, 93), (39, 29))):
        d.line([(x0 * k, y0 * k), (x1 * k, y1 * k)], fill=(255, 255, 255), width=w)
        for px, py in ((x0, y0), (x1, y1)):  # round the blade ends
            d.ellipse(
                [px * k - w // 2, py * k - w // 2, px * k + w // 2, py * k + w // 2],
                fill=(255, 255, 255),
            )
    for cx in (42, 98):  # finger rings
        r = 18 * k
        d.ellipse(
            [cx * k - r, 106 * k - r, cx * k + r, 106 * k + r],
            outline=(255, 255, 255),
            width=7 * k,
        )
    out = pathlib.Path(__file__).parent.parent / "static/description/icon.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    tile.resize((size, size), Image.LANCZOS).save(out)
    print(out.name, out.stat().st_size // 1024, "KB")


def main():
    make_hero_banner()
    make_icon()
    out = pathlib.Path(__file__).parent / "salon-erp.gif"
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(FRAMES):
            frame(i).save(f"{tmp}/f{i:03d}.png")
        run = lambda *a: subprocess.run(a, check=True, capture_output=True)
        run("ffmpeg", "-y", "-i", f"{tmp}/f%03d.png",
            "-vf", "palettegen=max_colors=128:stats_mode=full", f"{tmp}/pal.png")
        run("ffmpeg", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%03d.png",
            "-i", f"{tmp}/pal.png",
            "-lavfi", "paletteuse=dither=bayer:bayer_scale=3", "-loop", "0", str(out))
    print(out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
