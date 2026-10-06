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
import asyncio
import aiohttp
import base64

from PIL import (
    Image,
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


class Thumbnail:

    def __init__(self):

        try:

            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf",
                42
            )

            self.regular_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf",
                24
            )

            self.signature_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf",
                28
            )

        except OSError:

            self.title_font = ImageFont.load_default()
            self.regular_font = ImageFont.load_default()
            self.signature_font = ImageFont.load_default()

    async def save_thumb(self, output_path: str, url: str):

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as resp:

                with open(output_path, "wb") as f:
                    f.write(await resp.read())

        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:

        try:

            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_full_v5.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_sync,
                temp,
                output,
                song,
                size
            )

        except Exception:
            return config.DEFAULT_THUMB

    def _generate_sync(
        self,
        temp: str,
        output: str,
        song: Track,
        size=(1280, 720)
    ) -> str:

        try:
            # Premium reference-style music card.
            # Keep the existing 930x523 output size; all visual positions
            # below are scaled to match the supplied reference image.
            player_w, player_h = 930, 523

            with Image.open(temp) as src:
                source = src.convert("RGBA")

                # One fixed background for the entire card.
                bg_color = (7, 31, 24, 255)
                card = Image.new("RGBA", (player_w, player_h), bg_color)
                draw = ImageDraw.Draw(card)

                # Soft inner highlight, while keeping the background color fixed.
                # Clean card: no visible outer border.


                # Artwork: TRUE SQUARE cover.
                # The player always shows a 1:1 cover area.  The source is
                # proportionally resized and softly extended to the square
                # so the cover never becomes a visible 16:9 rectangle.
                art_size = 360
                art_x, art_y = 42, 72

                # Build a square background from the same artwork.
                square_bg = ImageOps.fit(
                    source,
                    (art_size, art_size),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5)
                )
                square_bg = square_bg.filter(ImageFilter.GaussianBlur(10))
                square_bg = ImageEnhance.Color(square_bg).enhance(0.9)
                square_bg = ImageEnhance.Brightness(square_bg).enhance(0.72)

                # Put the complete original artwork over the square canvas.
                # No stretching: its aspect ratio is preserved.
                art = ImageOps.contain(
                    source,
                    (art_size, art_size),
                    method=Image.Resampling.LANCZOS
                )
                art = ImageEnhance.Color(art).enhance(1.05)

                art_box = square_bg.copy()
                ax = (art_size - art.width) // 2
                ay = (art_size - art.height) // 2
                art_box.alpha_composite(art, (ax, ay))

                art_mask = Image.new("L", (art_size, art_size), 0)
                ImageDraw.Draw(art_mask).rounded_rectangle(
                    (0, 0, art_size - 1, art_size - 1),
                    radius=22,
                    fill=255
                )
                card.paste(art_box, (art_x, art_y), art_mask)

                # Right-side song information — scaled to the supplied
                # reference image.  The artwork block above is intentionally
                # untouched.
                rx = 463
                rw = player_w - rx - 42

                now_font = ImageFont.truetype(
                    "Elevenyts/helpers/Raleway-Bold.ttf", 22
                )
                title_font = ImageFont.truetype(
                    "Elevenyts/helpers/Raleway-Bold.ttf", 38
                )
                artist_font = ImageFont.truetype(
                    "Elevenyts/helpers/Inter-Light.ttf", 27
                )
                small_font = ImageFont.truetype(
                    "Elevenyts/helpers/Inter-Light.ttf", 22
                )

                accent = (48, 211, 154, 255)
                artist_color = (120, 228, 181, 255)
                muted = (171, 201, 190, 255)
                white = (250, 252, 251, 255)
                dark = (7, 31, 24, 255)

                draw.text(
                    (rx, 109),
                    "NOW PLAYING",
                    fill=accent,
                    font=now_font
                )

                title = trim_to_width(
                    str(song.title or "Unknown Track"),
                    title_font,
                    rw
                )
                artist = trim_to_width(
                    str(song.channel_name or "Apple Musix"),
                    artist_font,
                    rw
                )

                draw.text(
                    (rx, 154),
                    title,
                    fill=white,
                    font=title_font
                )

                draw.text(
                    (rx, 215),
                    artist,
                    fill=artist_color,
                    font=artist_font
                )

                duration = str(getattr(song, "duration", "") or "")
                duration_label = (
                    f"Duration  •  {duration}"
                    if duration
                    else "Duration  •  --:--"
                )
                draw.text(
                    (rx, 267),
                    duration_label,
                    fill=muted,
                    font=small_font
                )

                # Compact reference-style Play pill.
                pill_x, pill_y = rx, 323
                pill_w, pill_h = 206, 50

                draw.rounded_rectangle(
                    (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
                    radius=25,
                    fill=accent
                )

                py = pill_y + pill_h // 2
                draw.polygon(
                    [
                        (pill_x + 43, py - 13),
                        (pill_x + 43, py + 13),
                        (pill_x + 66, py)
                    ],
                    fill=dark
                )

                draw.text(
                    (pill_x + 91, pill_y + 7),
                    "Play",
                    fill=dark,
                    font=ImageFont.truetype(
                        "Elevenyts/helpers/Raleway-Bold.ttf", 25
                    )
                )

                # Reference music icon in the upper-right corner.
                mx, my = player_w - 92, 58
                draw.rectangle(
                    (mx - 2, my + 12, mx + 4, my + 50),
                    fill=accent
                )
                draw.rectangle(
                    (mx + 20, my + 5, mx + 26, my + 43),
                    fill=accent
                )
                draw.polygon(
                    [
                        (mx - 2, my + 12),
                        (mx + 26, my + 5),
                        (mx + 26, my + 14),
                        (mx - 2, my + 21)
                    ],
                    fill=accent
                )
                draw.ellipse(
                    (mx - 16, my + 43, mx + 6, my + 59),
                    fill=accent
                )
                draw.ellipse(
                    (mx + 9, my + 36, mx + 31, my + 52),
                    fill=accent
                )

                # Rounded outer card.
                mask = Image.new("L", card.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, player_w - 1, player_h - 1),
                    radius=30,
                    fill=255
                )

                final = Image.new("RGBA", (player_w, player_h), bg_color)
                final.paste(card, (0, 0), mask)
                final.save(output)

            try:
                os.remove(temp)
            except OSError:
                pass

            return output




        except Exception:
            return config.DEFAULT_THUMB
