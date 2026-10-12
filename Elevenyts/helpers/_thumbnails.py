# ==========================================================
# Copyright (c) 2026 Apple Music <<3
# All Rights Reserved.
#
# Project      : Apple Music Telegram Music Bot
# Powered By   : Apple Music <<3
# Type         : API Based Telegram Music Bot
#
# Bot          : @AppleMusix_bot
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================
import os
import re
import html
import math
import asyncio
import aiohttp
import base64

from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps
)

from Elevenyts import config
from Elevenyts.helpers import Track


PANEL_W, PANEL_H = 1030, 610
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = 55

THUMB_W, THUMB_H = 930, 420
THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y = PANEL_Y + 30

TITLE_X = THUMB_X + 5
TITLE_Y = THUMB_Y + THUMB_H + 25

META_Y = TITLE_Y + 58

BAR_X = THUMB_X + 5
BAR_Y = META_Y + 60

BAR_RED_LEN = 330
BAR_TOTAL_LEN = 920

ICONS_W, ICONS_H = 420, 45
ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
ICONS_Y = BAR_Y + 65

MAX_TITLE_WIDTH = 850

_f = "QXBwbGUgTXVzaXg="


def _decode_f():
    decoded = base64.b64decode(_f).decode("utf-8")
    return f"✦ {decoded} ✦"


def trim_to_width(text: str, font, max_w: int) -> str:

    ellipsis = "…"

    if font.getlength(text) <= max_w:
        return text

    for i in range(len(text) - 1, 0, -1):

        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis

    return ellipsis


# ==========================================================
# Player-window panel (reference style)
#
# Every coordinate below is written in the pixel space of the
# reference design.  X()/Y()/Z() convert them to the 2x
# super-sampled canvas, which is down-scaled at the end so
# all edges stay perfectly smooth.
# ==========================================================

HELPERS = "Elevenyts/helpers/"

SS = 2                      # super-sampling factor
OX, OY = 53, 110            # window origin inside the reference design
WIN_W, WIN_H = 981, 1252    # window size  (output PNG size)

# Optional fonts: drop these files into Elevenyts/helpers/ to get the
# exact serif title / script "Now Playing" look. Without them the
# bot falls back to system serif / sheared Raleway automatically.
SERIF_FONTS = [
    HELPERS + "PlayfairDisplay-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    HELPERS + "Raleway-Bold.ttf",
]
SCRIPT_FONTS = [
    HELPERS + "GreatVibes-Regular.ttf",
]
SANS_BOLD = [HELPERS + "Raleway-Bold.ttf"]
SANS_LIGHT = [HELPERS + "Inter-Light.ttf"]


def X(v):
    return int(round((v - OX) * SS))


def Y(v):
    return int(round((v - OY) * SS))


def Z(v):
    return int(round(v * SS))


def B(x0, y0, x1, y1):
    return (X(x0), Y(y0), X(x1), Y(y1))


def _pts(cx, cy, rel):
    return [(X(cx + a), Y(cy + b)) for a, b in rel]


def _font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, Z(size))
        except OSError:
            continue
    return ImageFont.load_default()


def _script_font(size):
    for p in SCRIPT_FONTS:
        try:
            return ImageFont.truetype(p, Z(size * 1.25)), False
        except OSError:
            continue
    return _font(SANS_BOLD, size), True   # needs fake italic


def _grad(w, h, c1, c2, horizontal=False):
    w, h = max(int(w), 1), max(int(h), 1)
    g = Image.linear_gradient("L")
    if horizontal:
        g = g.rotate(90)
    g = g.resize((w, h))
    return Image.composite(
        Image.new("RGBA", (w, h), c2),
        Image.new("RGBA", (w, h), c1),
        g
    )


def _fill_rr(canvas, box, r, c1, c2=None, horizontal=False):
    """Rounded rectangle filled with a (vertical/horizontal) gradient."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    c2 = c2 or c1
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    sub = _grad(w, h, c1, c2, horizontal)
    sub.putalpha(ImageChops.multiply(sub.getchannel("A"), mask))
    canvas.alpha_composite(sub, (x0, y0))


def _framed(canvas, box, r, border1, border2, fill1, fill2, bw,
            horizontal=False):
    x0, y0, x1, y1 = box
    _fill_rr(canvas, box, r, border1, border2, horizontal)
    inner = (x0 + bw, y0 + bw, x1 - bw, y1 - bw)
    _fill_rr(canvas, inner, max(r - bw, 1), fill1, fill2)


def _glow(canvas, box, r, color, blur, grow=0):
    x0, y0, x1, y1 = box
    pad = blur * 3 + grow
    w, h = x1 - x0 + pad * 2, y1 - y0 + pad * 2
    sub = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sub).rounded_rectangle(
        (pad - grow, pad - grow, w - pad + grow, h - pad + grow),
        r + grow, fill=color
    )
    sub = sub.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sub, (max(x0 - pad, 0), max(y0 - pad, 0)))


def _glow_circle(canvas, cx, cy, rad, color, blur):
    pad = blur * 3
    size = rad * 2 + pad * 2
    sub = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(sub).ellipse(
        (pad, pad, pad + rad * 2, pad + rad * 2), fill=color
    )
    sub = sub.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sub, (cx - rad - pad, cy - rad - pad))


def _text_mask(size, xy, text, font, anchor="lm", shear=0.0):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=font, fill=255, anchor=anchor)
    if shear:
        y0 = xy[1]
        mask = mask.transform(
            size, Image.AFFINE, (1, shear, -shear * y0, 0, 1, 0),
            resample=Image.BICUBIC
        )
    return mask


def _grad_text(canvas, xy, text, font, c1, c2, anchor="lm",
               horizontal=True, shear=0.0, glow=None):
    mask = _text_mask(canvas.size, xy, text, font, anchor, shear)
    bbox = mask.getbbox()
    if not bbox:
        return
    x0, y0, x1, y1 = bbox
    sub_mask = mask.crop(bbox)
    sub = _grad(x1 - x0, y1 - y0, c1, c2, horizontal)
    if glow:
        g = Image.new("RGBA", (x1 - x0 + 60, y1 - y0 + 60), (0, 0, 0, 0))
        gm = Image.new("L", g.size, 0)
        gm.paste(sub_mask, (30, 30))
        g.paste(Image.new("RGBA", g.size, glow), (0, 0),
                gm.filter(ImageFilter.GaussianBlur(Z(5))))
        canvas.alpha_composite(g, (x0 - 30, y0 - 30))
    sub.putalpha(sub_mask)
    canvas.alpha_composite(sub, (x0, y0))


def _sparkle(d, cx, cy, r, fill):
    k = r * 0.24
    d.polygon(
        [
            (X(cx), Y(cy - r)), (X(cx + k), Y(cy - k)),
            (X(cx + r), Y(cy)), (X(cx + k), Y(cy + k)),
            (X(cx), Y(cy + r)), (X(cx - k), Y(cy + k)),
            (X(cx - r), Y(cy)), (X(cx - k), Y(cy - k)),
        ],
        fill=fill
    )


def _dot(d, cx, cy, r, fill):
    d.ellipse((X(cx - r), Y(cy - r), X(cx + r), Y(cy + r)), fill=fill)


def _heart_points(cx, cy, size):
    pts = []
    for i in range(0, 361, 6):
        t = math.radians(i)
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t)
               - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((X(cx + hx * size / 32), Y(cy + hy * size / 32)))
    return pts


def _flower(d, cx, cy, r, petal=(246, 160, 196, 255),
            centre=(255, 226, 150, 255)):
    for i in range(5):
        a = math.radians(i * 72 - 90)
        px, py = cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.62
        _dot(d, px, py, r * 0.46, petal)
    _dot(d, cx, cy, r * 0.30, centre)


def _note(d, cx, cy, s, fill):
    """Single eighth-note."""
    d.ellipse((X(cx - 7 * s), Y(cy + 8 * s), X(cx + 5 * s), Y(cy + 17 * s)),
              fill=fill)
    d.rectangle((X(cx + 2 * s), Y(cy - 14 * s), X(cx + 5 * s), Y(cy + 13 * s)),
                fill=fill)
    d.polygon(_pts(cx, cy, [(5 * s, -14 * s), (16 * s, -6 * s),
                            (14 * s, 2 * s), (5 * s, -5 * s)]), fill=fill)


def _leaf(d, x, y, angle, length, width, fill):
    pts = []
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    for i in range(0, 21):
        t = i / 20
        pts.append((t * length, math.sin(t * math.pi) * width / 2))
    for i in range(20, -1, -1):
        t = i / 20
        pts.append((t * length, -math.sin(t * math.pi) * width / 2))
    d.polygon([(X(x + px * ca - py * sa), Y(y + px * sa + py * ca))
               for px, py in pts], fill=fill)


def _fmt(sec):
    sec = max(int(sec or 0), 0)
    if sec >= 3600:
        return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _clean_name(value) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", "", str(value or "")))
    return text.strip() or "Unknown"


def render_panel(
    source: Image.Image,
    title: str,
    artist: str,
    duration_text: str,
    elapsed_text: str,
    fraction: float,
    requester: str,
    queue_count: int,
) -> Image.Image:
    """Draw the full player window and return an RGBA image
    (transparent outside the window, WIN_W x WIN_H)."""

    canvas = Image.new("RGBA", (WIN_W * SS, WIN_H * SS), (0, 0, 0, 0))
    CW, CH = canvas.size

    # ---------------- window ----------------
    win = (0, 0, CW - 1, CH - 1)
    _fill_rr(canvas, win, Z(28), (40, 64, 100, 255), (24, 38, 66, 255))
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rounded_rectangle(win, Z(28), outline=(15, 24, 42, 255), width=Z(3))
    d.rounded_rectangle(
        (Z(3), Z(3), CW - 1 - Z(3), CH - 1 - Z(3)), Z(26),
        outline=(95, 120, 160, 110), width=Z(1)
    )

    # window controls
    white = (236, 242, 252, 255)
    d.line((X(876), Y(138), X(894), Y(138)), fill=white, width=Z(2))
    d.rectangle(B(931, 129, 949, 147), outline=white, width=Z(2))
    d.line((X(989), Y(130), X(1005), Y(146)), fill=white, width=Z(2))
    d.line((X(1005), Y(130), X(989), Y(146)), fill=white, width=Z(2))

    # ---------------- header card ----------------
    hbox = B(75, 165, 1017, 570)
    _framed(canvas, hbox, Z(22), (222, 160, 205, 255), (126, 150, 224, 255),
            (22, 36, 66, 255), (27, 42, 76, 255), Z(3), horizontal=True)
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rounded_rectangle(B(83, 173, 1009, 562), Z(16),
                        outline=(150, 130, 190, 55), width=Z(1))

    # vinyl record (behind the cover)
    vc = (380, 366)
    _dot(d, vc[0], vc[1], 122, (12, 12, 16, 255))
    for rr_ in range(56, 120, 8):
        d.ellipse((X(vc[0] - rr_), Y(vc[1] - rr_), X(vc[0] + rr_), Y(vc[1] + rr_)),
                  outline=(46, 46, 56, 190), width=Z(1))
    d.arc((X(vc[0] - 108), Y(vc[1] - 108), X(vc[0] + 108), Y(vc[1] + 108)),
          300, 345, fill=(140, 140, 160, 120), width=Z(3))
    _dot(d, vc[0], vc[1], 50, (238, 130, 176, 255))
    _dot(d, vc[0], vc[1], 38, (246, 160, 198, 255))
    _dot(d, vc[0], vc[1], 7, (14, 14, 18, 255))

    # album cover
    cbox = B(127, 217, 407, 507)
    _glow(canvas, cbox, Z(24), (236, 150, 210, 110), Z(10))
    _framed(canvas, cbox, Z(24), (246, 170, 206, 255), (170, 140, 232, 255),
            (240, 220, 180, 255), (240, 220, 180, 255), Z(5))
    cw_, ch_ = cbox[2] - cbox[0] - Z(10), cbox[3] - cbox[1] - Z(10)
    art = ImageOps.fit(source, (cw_, ch_), method=Image.Resampling.LANCZOS)
    art = ImageEnhance.Color(art).enhance(1.05)
    amask = Image.new("L", (cw_, ch_), 0)
    ImageDraw.Draw(amask).rounded_rectangle((0, 0, cw_ - 1, ch_ - 1), Z(18),
                                            fill=255)
    canvas.paste(art, (cbox[0] + Z(5), cbox[1] + Z(5)), amask)
    d = ImageDraw.Draw(canvas, "RGBA")

    # constellation + sparkles + moon
    star = (240, 205, 230, 255)
    pl = [(447, 196), (474, 232), (497, 205), (520, 191)]
    d.line([(X(a), Y(b)) for a, b in pl], fill=(235, 200, 225, 150),
           width=Z(1))
    d.line((X(474), Y(232), X(488), Y(242)), fill=(235, 200, 225, 150),
           width=Z(1))
    for a, b in pl:
        _dot(d, a, b, 2.5, star)
    _sparkle(d, 108, 205, 17, (248, 214, 236, 255))
    _sparkle(d, 94, 355, 11, (248, 214, 236, 255))
    _sparkle(d, 466, 506, 8, (248, 214, 236, 255))
    _sparkle(d, 1001, 370, 8, (248, 214, 236, 255))
    _sparkle(d, 940, 196, 7, (248, 214, 236, 255))
    _sparkle(d, 300, 188, 6, (200, 190, 240, 255))
    _dot(d, 134, 190, 2, star)
    _dot(d, 992, 507, 2, star)
    _dot(d, 1003, 322, 1.6, star)

    moon = Image.new("RGBA", (Z(46), Z(46)), (0, 0, 0, 0))
    md = ImageDraw.Draw(moon)
    md.ellipse((Z(4), Z(4), Z(36), Z(36)), fill=(250, 226, 238, 255))
    md.ellipse((Z(14), Z(0), Z(46), Z(32)), fill=(0, 0, 0, 0))
    canvas.alpha_composite(moon, (X(956), Y(194)))
    d = ImageDraw.Draw(canvas, "RGBA")

    # corner flowers
    for fx, fy, fr in [(116, 536, 15), (94, 508, 11), (134, 553, 9),
                       (87, 188, 9), (1003, 181, 8), (985, 547, 10),
                       (1000, 526, 7)]:
        _flower(d, fx, fy, fr)
    for lx, ly in [(100, 530), (127, 546), (92, 520)]:
        d.ellipse((X(lx - 9), Y(ly - 3), X(lx + 3), Y(ly + 3)),
                  fill=(150, 200, 170, 200))

    # headphones + "Now Playing" + heart
    ph = (246, 222, 238, 255)
    d.arc((X(578), Y(209), X(612), Y(243)), 180, 360, fill=ph, width=Z(3))
    d.rounded_rectangle(B(577, 224, 585, 240), Z(3), fill=ph)
    d.rounded_rectangle(B(605, 224, 613, 240), Z(3), fill=ph)

    script, fake = _script_font(41)
    _grad_text(canvas, (X(632), Y(227)), "Now Playing", script,
               (252, 232, 244, 255), (232, 180, 220, 255),
               shear=0.22 if fake else 0.0, glow=(238, 160, 210, 120))
    d = ImageDraw.Draw(canvas, "RGBA")
    swirl = [(872, 243), (890, 246), (906, 242), (912, 237)]
    d.line([(X(a), Y(b)) for a, b in swirl], fill=(238, 190, 220, 200),
           width=Z(1))
    d.line(_heart_points(924, 232, 20) + [_heart_points(924, 232, 20)[0]],
           fill=(240, 196, 224, 255), width=Z(2))

    # title + artist
    title_font = _font(SERIF_FONTS, 54)
    for size in range(54, 35, -2):
        title_font = _font(SERIF_FONTS, size)
        if title_font.getlength(title) <= Z(472):
            break
    artist_font = _font(SANS_LIGHT, 30)
    title_full = title
    title = trim_to_width(title, title_font, Z(472))
    artist = trim_to_width(artist, artist_font, Z(430))
    _grad_text(canvas, (X(530), Y(298)), title, title_font,
               (255, 232, 244, 255), (244, 184, 222, 255),
               horizontal=True, glow=(236, 150, 210, 90))
    d = ImageDraw.Draw(canvas, "RGBA")
    d.text((X(540), Y(353)), artist, font=artist_font,
           fill=(238, 242, 252, 255), anchor="lm")

    # equaliser bars
    tops = [458, 444, 430, 420, 400, 423, 435, 437, 428, 421, 405, 426, 436]
    bottom = 487
    for i, top in enumerate(tops):
        bx = 508 + i * 35.6
        bb = B(bx, top, bx + 14, bottom)
        _glow(canvas, bb, Z(7), (190, 140, 240, 70), Z(5))
        _fill_rr(canvas, bb, Z(7), (232, 176, 238, 255), (160, 134, 238, 255))
    d = ImageDraw.Draw(canvas, "RGBA")
    _note(d, 541, 410, 1.0, (242, 150, 204, 255))
    _note(d, 981, 392, 0.8, (242, 150, 204, 255))

    # progress bar
    p0, p1, py = 507, 801, 522
    _fill_rr(canvas, B(p0, py - 3, p1, py + 3), Z(3),
             (52, 72, 112, 255), (52, 72, 112, 255))
    kx = p0 + max(0.0, min(1.0, fraction)) * (p1 - p0)
    kx = max(kx, p0 + 6)
    _fill_rr(canvas, B(p0, py - 3, kx, py + 3), Z(3),
             (150, 140, 236, 255), (246, 150, 196, 255), horizontal=True)
    _glow_circle(canvas, X(kx), Y(py), Z(14), (250, 140, 180, 150), Z(5))
    d = ImageDraw.Draw(canvas, "RGBA")
    _dot(d, kx, py, 14, (255, 190, 214, 255))
    _dot(d, kx, py, 10, (250, 128, 170, 255))
    time_font = _font(SANS_LIGHT, 24)
    d.text((X(820), Y(524)), f"{elapsed_text} / {duration_text}",
           font=time_font, fill=(240, 244, 252, 255), anchor="lm")

    # ---------------- info panel ----------------
    ibox = B(77, 605, 1013, 1067)
    _framed(canvas, ibox, Z(18), (70, 92, 132, 255), (58, 78, 116, 255),
            (22, 35, 62, 255), (24, 37, 65, 255), Z(2))
    # pink accent bar on the left edge
    _glow(canvas, B(77, 610, 100, 1062), Z(10), (255, 140, 175, 110), Z(8))
    _fill_rr(canvas, B(77, 605, 101, 1067), Z(16),
             (255, 128, 160, 255), (255, 168, 190, 255))
    _fill_rr(canvas, B(90, 605, 101, 1067), 0,
             (255, 128, 160, 255), (255, 168, 190, 255))
    d = ImageDraw.Draw(canvas, "RGBA")

    head_font = _font(SANS_BOLD, 40)
    label_font = _font(SANS_BOLD, 32)
    value_font = _font(SANS_LIGHT, 35)

    _dot(d, 194, 662, 5, (246, 190, 212, 255))
    _sparkle(d, 240, 662, 19, (252, 226, 240, 255))
    d.text((X(283), Y(662)), "NOW PLAYING", font=head_font,
           fill=(246, 248, 255, 255), anchor="lm")

    # twig
    tw = [(596, 668), (622, 661), (650, 664), (684, 655), (736, 647)]
    tc = (238, 168, 190, 255)
    d.line([(X(a), Y(b)) for a, b in tw], fill=tc, width=Z(2))
    for lx, ly, ang in [(612, 663, -55), (630, 662, 50), (652, 664, -50),
                        (668, 659, 48), (690, 653, -50), (706, 651, 46),
                        (722, 649, -48), (736, 647, 10)]:
        _leaf(d, lx, ly, ang, 17, 7, (242, 178, 198, 255))
    for lx, ly in [(660, 672), (700, 640), (744, 640)]:
        _dot(d, lx, ly, 2, tc)

    # bracket line
    bk = (238, 164, 180, 255)
    d.arc((X(136), Y(662), X(170), Y(696)), 180, 270, fill=bk, width=Z(2))
    d.line((X(153), Y(662), X(180), Y(662)), fill=bk, width=Z(2))
    d.line((X(136), Y(679), X(136), Y(987)), fill=bk, width=Z(2))
    d.arc((X(136), Y(970), X(170), Y(1004)), 90, 180, fill=bk, width=Z(2))
    d.line((X(153), Y(1004), X(180), Y(1004)), fill=bk, width=Z(2))

    rows = [740, 828, 916, 1004]
    for ry in rows:
        d.line((X(136), Y(ry), X(160), Y(ry)), fill=bk, width=Z(2))
        _dot(d, 187, ry, 5, (246, 190, 212, 255))
    for sy in (783, 871, 959):
        d.line((X(190), Y(sy), X(978), Y(sy)), fill=(62, 82, 120, 255),
               width=Z(1))

    # row icons
    _flower(d, 240, 740, 24)
    # hourglass
    hg = (238, 234, 244, 255)
    d.rounded_rectangle(B(222, 806, 258, 814), Z(3), fill=hg)
    d.rounded_rectangle(B(222, 843, 258, 851), Z(3), fill=hg)
    d.polygon(_pts(240, 828, [(-14, -14), (14, -14), (0, 0)]),
              fill=(200, 205, 235, 120), outline=hg)
    d.polygon(_pts(240, 828, [(0, 0), (14, 15), (-14, 15)]),
              fill=(200, 205, 235, 120), outline=hg)
    d.polygon(_pts(240, 828, [(0, 4), (10, 15), (-10, 15)]),
              fill=(244, 150, 112, 255))
    # heart
    hp = _heart_points(240, 916, 50)
    d.polygon(hp, fill=(255, 226, 236, 255))
    # scroll
    d.rounded_rectangle(B(225, 980, 257, 1028), Z(6), fill=(252, 230, 228, 255),
                        outline=(238, 168, 184, 255), width=Z(2))
    for ly in (992, 1001, 1010, 1019):
        d.line((X(231), Y(ly), X(251), Y(ly)), fill=(200, 122, 136, 255),
               width=Z(2))

    # row labels + values
    rows_data = [
        ("TRACK", title_full),
        ("DURATION", duration_text),
        ("REQUESTER", requester),
        ("QUEUE", f"{queue_count} Song" + ("" if queue_count == 1 else "s")),
    ]
    for ry, (label, value) in zip(rows, rows_data):
        _grad_text(canvas, (X(283), Y(ry)), label, label_font,
                   (252, 152, 208, 255), (206, 172, 255, 255))
        d = ImageDraw.Draw(canvas, "RGBA")
        d.text((X(543), Y(ry)), ":", font=label_font,
               fill=(246, 168, 206, 255), anchor="mm")
        value = trim_to_width(str(value), value_font, Z(392))
        d.text((X(583), Y(ry)), value, font=value_font,
               fill=(244, 247, 255, 255), anchor="lm")

    # ---------------- controls panel ----------------
    _framed(canvas, B(75, 1111, 1013, 1341), Z(20),
            (72, 94, 136, 255), (62, 84, 126, 255),
            (32, 48, 80, 255), (30, 45, 76, 255), Z(2))

    btns = [(108, 262), (291, 445), (474, 625), (655, 805), (835, 982)]
    by0, by1 = 1157, 1307
    for i, (bx0, bx1) in enumerate(btns):
        bb = B(bx0, by0, bx1, by1)
        if i == 1:
            _glow(canvas, bb, Z(28), (252, 140, 200, 150), Z(14), Z(2))
            _framed(canvas, bb, Z(28), (255, 214, 238, 255),
                    (236, 160, 214, 255), (246, 168, 212, 255),
                    (206, 128, 204, 255), Z(3))
        else:
            _framed(canvas, bb, Z(28), (156, 176, 228, 255),
                    (112, 132, 190, 255), (92, 110, 160, 255),
                    (58, 74, 122, 255), Z(3))
        # soft glass highlight on the upper half
        hl_w = bb[2] - bb[0] - Z(10)
        hl_h = (bb[3] - bb[1]) // 2 - Z(4)
        hl = _grad(hl_w, hl_h, (255, 255, 255, 38), (255, 255, 255, 0))
        hm = Image.new("L", hl.size, 0)
        ImageDraw.Draw(hm).rounded_rectangle((0, 0, hl.width - 1, hl.height + Z(30)),
                                             Z(22), fill=255)
        hl.putalpha(ImageChops.multiply(hl.getchannel("A"), hm))
        canvas.alpha_composite(hl, (bb[0] + Z(5), bb[1] + Z(5)))
    d = ImageDraw.Draw(canvas, "RGBA")

    ic = (250, 232, 246, 255)
    cy = 1232
    # previous
    cx = 185
    d.rectangle(B(cx - 28, cy - 25, cx - 20, cy + 25), fill=ic)
    d.polygon(_pts(cx, cy, [(27, -26), (27, 26), (-15, 0)]), fill=ic)
    # pause
    cx = 368
    d.rounded_rectangle(B(cx - 24, cy - 28, cx - 7, cy + 28), Z(3), fill=ic)
    d.rounded_rectangle(B(cx + 7, cy - 28, cx + 24, cy + 28), Z(3), fill=ic)
    # next
    cx = 549
    d.rectangle(B(cx + 20, cy - 25, cx + 28, cy + 25), fill=ic)
    d.polygon(_pts(cx, cy, [(-27, -26), (-27, 26), (15, 0)]), fill=ic)
    # repeat
    cx = 730
    lw = Z(7)
    d.line(_pts(cx, cy, [(-24, 6), (-24, -12), (12, -12)]), fill=ic,
           width=lw, joint="curve")
    d.polygon(_pts(cx, cy, [(8, -26), (30, -12), (8, 2)]), fill=ic)
    d.line(_pts(cx, cy, [(24, -6), (24, 12), (-12, 12)]), fill=ic,
           width=lw, joint="curve")
    d.polygon(_pts(cx, cy, [(-8, -2), (-30, 12), (-8, 26)]), fill=ic)
    # stop
    cx = 908
    _fill_rr(canvas, B(cx - 24, cy - 24, cx + 24, cy + 24), Z(5),
             (255, 232, 242, 255), (248, 186, 218, 255))

    # ---------------- finish ----------------
    return canvas.resize((WIN_W, WIN_H), Image.Resampling.LANCZOS)


def _queue_count(song) -> int:
    """Songs waiting after the current one (looked up from the live queue)."""
    try:
        from Elevenyts import queue

        for items in queue.queues.values():
            if any(item is song for item in items):
                return max(len(items) - 1, 0)
    except Exception:
        pass
    return 0


class Thumbnail:

    def __init__(self):
        pass

    async def save_thumb(self, output_path: str, url: str):

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as resp:

                with open(output_path, "wb") as f:
                    f.write(await resp.read())

        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:

        try:

            temp = f"cache/temp_{song.id}.jpg"
            queue_count = _queue_count(song)
            output = f"cache/{song.id}_panel_v1_q{queue_count}.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_sync,
                temp,
                output,
                song,
                queue_count
            )

        except Exception:
            return config.DEFAULT_THUMB

    def _generate_sync(
        self,
        temp: str,
        output: str,
        song: Track,
        queue_count: int = 0
    ) -> str:

        try:

            with Image.open(temp) as src:
                source = src.convert("RGBA")

                duration_sec = int(getattr(song, "duration_sec", 0) or 0)
                duration_text = (
                    _fmt(duration_sec)
                    if duration_sec
                    else str(getattr(song, "duration", "") or "--:--")
                )

                panel = render_panel(
                    source=source,
                    title=str(song.title or "Unknown Track"),
                    artist=str(song.channel_name or "Apple Musix"),
                    duration_text=duration_text,
                    elapsed_text=_fmt(0),
                    fraction=0.0,
                    requester=_clean_name(getattr(song, "user", None)),
                    queue_count=queue_count,
                )

            # Transparent PNG: nothing outside the player window.
            panel.save(output)

            try:
                os.remove(temp)
            except OSError:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB
