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
            output = f"cache/{song.id}_full.png"

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
            # Compact reference-style 16:9 player.
            player_w, player_h = 930, 523

            with Image.open(temp) as src:
                source = src.convert("RGBA")

                # Soft cinematic background.
                bg = ImageOps.fit(
                    source,
                    (player_w, player_h),
                    method=Image.Resampling.LANCZOS
                )
                bg = bg.filter(ImageFilter.GaussianBlur(26))
                bg = ImageEnhance.Brightness(bg).enhance(0.30)
                bg = ImageEnhance.Contrast(bg).enhance(1.12)
                bg = Image.alpha_composite(
                    bg,
                    Image.new("RGBA", (player_w, player_h), (4, 12, 22, 125))
                )

                card = Image.new("RGBA", (player_w, player_h), (12, 22, 34, 248))
                draw = ImageDraw.Draw(card)

                # Artwork: large, clean and gapless inside the player.
                art_w = 430
                art_h = 489
                art = ImageOps.fit(
                    source,
                    (art_w, art_h),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5)
                )
                art = ImageEnhance.Color(art).enhance(1.08)
                art_mask = Image.new("L", art.size, 0)
                ImageDraw.Draw(art_mask).rounded_rectangle(
                    (0, 0, art_w - 1, art_h - 1),
                    radius=24,
                    fill=255
                )
                card.paste(art, (17, 17), art_mask)

                # Right player section.
                rx = 482
                rw = player_w - rx - 30

                title = trim_to_width(
                    str(song.title or "Unknown Track"),
                    self.title_font,
                    rw
                )
                artist = trim_to_width(
                    str(song.channel_name or "Apple Musix"),
                    self.regular_font,
                    rw
                )

                draw.text(
                    (rx, 62),
                    title,
                    fill=(248, 250, 252),
                    font=self.title_font
                )
                draw.text(
                    (rx, 112),
                    artist,
                    fill=(190, 208, 225),
                    font=self.regular_font
                )

                # Progress bar and timestamps.
                bar_x = rx
                bar_w = rw
                bar_y = 178

                draw.rounded_rectangle(
                    (bar_x, bar_y, bar_x + bar_w, bar_y + 7),
                    radius=5,
                    fill=(92, 108, 124)
                )
                played_w = int(bar_w * 0.22)
                draw.rounded_rectangle(
                    (bar_x, bar_y, bar_x + played_w, bar_y + 7),
                    radius=5,
                    fill=(245, 248, 252)
                )
                draw.ellipse(
                    (bar_x + played_w - 7, bar_y - 4,
                     bar_x + played_w + 7, bar_y + 10),
                    fill=(250, 252, 255)
                )

                draw.text(
                    (bar_x, 194),
                    "0:00",
                    fill=(205, 216, 228),
                    font=self.regular_font
                )

                duration = str(getattr(song, "duration", "") or "")
                duration_text = f"-{duration}" if duration else "-:--"
                db = draw.textbbox((0, 0), duration_text, font=self.regular_font)
                draw.text(
                    (bar_x + bar_w - (db[2] - db[0]), 194),
                    duration_text,
                    fill=(205, 216, 228),
                    font=self.regular_font
                )

                # Manual playback icons: avoids broken/boxed Unicode glyphs.
                cy = 285
                cx = rx + bar_w // 2

                # Previous: triangle + vertical bar.
                draw.polygon(
                    [(cx - 112, cy), (cx - 88, cy - 20), (cx - 88, cy + 20)],
                    fill=(248, 250, 252)
                )
                draw.polygon(
                    [(cx - 88, cy), (cx - 64, cy - 20), (cx - 64, cy + 20)],
                    fill=(248, 250, 252)
                )
                draw.rectangle(
                    (cx - 120, cy - 21, cx - 115, cy + 21),
                    fill=(248, 250, 252)
                )

                # Pause.
                draw.rounded_rectangle(
                    (cx - 10, cy - 25, cx - 1, cy + 25),
                    radius=3,
                    fill=(248, 250, 252)
                )
                draw.rounded_rectangle(
                    (cx + 8, cy - 25, cx + 17, cy + 25),
                    radius=3,
                    fill=(248, 250, 252)
                )

                # Next: two triangles + vertical bar.
                draw.polygon(
                    [(cx + 64, cy - 20), (cx + 88, cy), (cx + 64, cy + 20)],
                    fill=(248, 250, 252)
                )
                draw.polygon(
                    [(cx + 88, cy - 20), (cx + 112, cy), (cx + 88, cy + 20)],
                    fill=(248, 250, 252)
                )
                draw.rectangle(
                    (cx + 116, cy - 21, cx + 121, cy + 21),
                    fill=(248, 250, 252)
                )

                # Volume icon + volume bar.
                vy = 358
                draw.polygon(
                    [(rx, vy + 5), (rx + 13, vy + 5), (rx + 28, vy - 10),
                     (rx + 28, vy + 25), (rx + 13, vy + 10), (rx, vy + 10)],
                    fill=(225, 235, 244)
                )
                draw.arc(
                    (rx + 18, vy - 4, rx + 50, vy + 22),
                    start=300,
                    end=60,
                    fill=(225, 235, 244),
                    width=3
                )
                vol_x = rx + 58
                vol_w = bar_w - 58
                draw.rounded_rectangle(
                    (vol_x, vy + 7, vol_x + vol_w, vy + 13),
                    radius=4,
                    fill=(92, 108, 124)
                )
                draw.rounded_rectangle(
                    (vol_x, vy + 7, vol_x + int(vol_w * 0.68), vy + 13),
                    radius=4,
                    fill=(245, 248, 252)
                )
                # Signature.
                draw.text(
                    (28, player_h - 39),
                    "Apple Musix <<3",
                    fill=(80, 185, 240),
                    font=self.signature_font
                )

                # Rounded outer card.
                mask = Image.new("L", card.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, player_w - 1, player_h - 1),
                    radius=30,
                    fill=255
                )

                final = Image.new("RGBA", (player_w, player_h), (6, 14, 24, 255))
                final.paste(card, (0, 0), mask)

                final.save(output)

            try:
                os.remove(temp)
            except OSError:
                pass

            return output



        except Exception:
            return config.DEFAULT_THUMB
