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
            with Image.open(temp) as temp_img:
                base = ImageOps.fit(
                    temp_img.convert("RGBA"),
                    size,
                    method=Image.Resampling.LANCZOS
                )

            bg = base.filter(ImageFilter.GaussianBlur(28))
            bg = ImageEnhance.Brightness(bg).enhance(0.22)
            bg = ImageEnhance.Contrast(bg).enhance(1.25)

            bg = Image.alpha_composite(
                bg,
                Image.new("RGBA", size, (5, 12, 20, 150))
            )

            panel = Image.new(
                "RGBA",
                (PANEL_W, PANEL_H),
                (10, 22, 34, 238)
            )
            panel_draw = ImageDraw.Draw(panel)

            panel_draw.rounded_rectangle(
                (0, 0, PANEL_W - 1, PANEL_H - 1),
                radius=42,
                fill=(10, 22, 34, 238),
                outline=(55, 145, 220, 180),
                width=2
            )

            # Header: Now Playing + YouTube + Apple Musix.
            panel_draw.text(
                (35, 22),
                "♫",
                fill=(40, 190, 255),
                font=self.signature_font
            )
            panel_draw.text(
                (78, 18),
                "Now Playing",
                fill=(85, 215, 255),
                font=self.title_font
            )

            yt_x = PANEL_W - 330
            panel_draw.rounded_rectangle(
                (yt_x, 25, yt_x + 70, 68),
                radius=12,
                fill=(255, 30, 45)
            )
            panel_draw.polygon(
                [(yt_x + 29, 34), (yt_x + 29, 59), (yt_x + 48, 46.5)],
                fill="white"
            )
            panel_draw.text(
                (yt_x + 92, 24),
                "Apple Musix <<3",
                fill=(190, 205, 225),
                font=self.signature_font
            )

            panel_draw.line(
                (30, 82, PANEL_W - 30, 82),
                fill=(45, 85, 120),
                width=2
            )

            # Main player surface.
            card_x, card_y = 30, 105
            card_w, card_h = PANEL_W - 60, 355

            panel_draw.rounded_rectangle(
                (card_x, card_y, card_x + card_w, card_y + card_h),
                radius=30,
                fill=(12, 30, 47, 245),
                outline=(38, 83, 115, 190),
                width=2
            )

            # Full song artwork: large, complete image with no cropping.
            with Image.open(temp) as art_src:
                art = ImageOps.pad(
                    art_src.convert("RGBA"),
                    (card_w - 10, card_h - 10),
                    method=Image.Resampling.LANCZOS,
                    color=(18, 24, 32, 255),
                    centering=(0.5, 0.5)
                )

            art_mask = Image.new("L", art.size, 0)
            ImageDraw.Draw(art_mask).rounded_rectangle(
                (0, 0, art.size[0], art.size[1]),
                radius=26,
                fill=255
            )
            panel.paste(art, (card_x + 5, card_y + 5), art_mask)

            # Subtle bottom gradient so the artwork remains visible while
            # the player information stays readable.
            shade = Image.new("RGBA", art.size, (0, 0, 0, 0))
            shade_draw = ImageDraw.Draw(shade)
            shade_draw.rectangle(
                (0, int(art.size[1] * 0.68), art.size[0], art.size[1]),
                fill=(5, 15, 24, 155)
            )
            panel.alpha_composite(shade, (card_x + 5, card_y + 5))

            text_x = card_x + 30
            title = trim_to_width(
                str(song.title or "Unknown Track"),
                self.title_font,
                card_w - 60
            )
            artist = trim_to_width(
                str(song.channel_name or "Apple Musix"),
                self.regular_font,
                card_w - 60
            )

            panel_draw.text(
                (text_x, card_y + card_h - 105),
                title,
                fill=(245, 248, 252),
                font=self.title_font
            )
            panel_draw.text(
                (text_x, card_y + card_h - 70),
                artist,
                fill=(185, 205, 225),
                font=self.regular_font
            )

            progress_y = card_y + card_h - 35
            progress_w = card_w - 60
            panel_draw.rounded_rectangle(
                (text_x, progress_y, text_x + progress_w, progress_y + 7),
                radius=6,
                fill=(90, 110, 130)
            )
            panel_draw.rounded_rectangle(
                (text_x, progress_y, text_x + int(progress_w * 0.22), progress_y + 7),
                radius=6,
                fill=(245, 248, 252)
            )
            # Signature and track metadata below the player.
            clean_title = re.sub(r"\s+", " ", str(song.title or "Unknown Track")).strip()
            clean_title = trim_to_width(clean_title, self.title_font, 850)

            meta_y = PANEL_H - 128
            panel_draw.rounded_rectangle(
                (35, meta_y, PANEL_W - 35, meta_y + 62),
                radius=18,
                fill=(18, 39, 59, 245)
            )
            panel_draw.text(
                (58, meta_y + 12),
                "♪",
                fill=(55, 190, 255),
                font=self.signature_font
            )
            panel_draw.text(
                (100, meta_y + 12),
                clean_title,
                fill=(235, 242, 250),
                font=self.regular_font
            )

            panel_draw.text(
                (PANEL_W - 245, meta_y + 12),
                "YouTube",
                fill=(190, 205, 225),
                font=self.regular_font
            )

            panel_draw.text(
                (35, PANEL_H - 52),
                "Apple Musix <<3",
                fill=(95, 185, 245),
                font=self.signature_font
            )

            bg.paste(panel, (PANEL_X, PANEL_Y), panel)

            bg.save(output)

            try:
                os.remove(temp)
            except OSError:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB
