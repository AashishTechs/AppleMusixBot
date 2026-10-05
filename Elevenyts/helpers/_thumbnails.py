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

            # Full artwork: preserve the complete source image, no crop.
            art_size = 295
            art_x, art_y = card_x + 25, card_y + 30
            with Image.open(temp) as art_src:
                art = ImageOps.pad(
                    art_src.convert("RGBA"),
                    (art_size, art_size),
                    method=Image.Resampling.LANCZOS,
                    color=(18, 24, 32, 255),
                    centering=(0.5, 0.5)
                )

            art_mask = Image.new("L", art.size, 0)
            ImageDraw.Draw(art_mask).rounded_rectangle(
                (0, 0, art_size, art_size),
                radius=24,
                fill=255
            )
            panel.paste(art, (art_x, art_y), art_mask)

            text_x = art_x + art_size + 28
            title = trim_to_width(
                str(song.title or "Unknown Track"),
                self.title_font,
                540
            )
            artist = trim_to_width(
                str(song.channel_name or "Apple Musix"),
                self.regular_font,
                540
            )

            panel_draw.text(
                (text_x, card_y + 38),
                title,
                fill=(245, 248, 252),
                font=self.title_font
            )
            panel_draw.text(
                (text_x, card_y + 98),
                artist,
                fill=(160, 180, 205),
                font=self.regular_font
            )

            # Progress bar.
            progress_y = card_y + 150
            progress_x = text_x
            progress_w = 515
            panel_draw.rounded_rectangle(
                (progress_x, progress_y, progress_x + progress_w, progress_y + 8),
                radius=6,
                fill=(70, 90, 112)
            )
            progress_len = int(progress_w * 0.22)
            panel_draw.rounded_rectangle(
                (progress_x, progress_y, progress_x + progress_len, progress_y + 8),
                radius=6,
                fill=(235, 245, 255)
            )
            panel_draw.ellipse(
                (
                    progress_x + progress_len - 10,
                    progress_y - 6,
                    progress_x + progress_len + 10,
                    progress_y + 14
                ),
                fill=(245, 248, 252)
            )

            panel_draw.text(
                (progress_x, progress_y + 18),
                "0:00",
                fill=(155, 175, 200),
                font=self.regular_font
            )
            end_text = "LIVE" if getattr(song, "is_live", False) else str(song.duration or "0:00")
            end_w = panel_draw.textlength(end_text, font=self.regular_font)
            panel_draw.text(
                (progress_x + progress_w - end_w, progress_y + 18),
                end_text,
                fill=(155, 175, 200),
                font=self.regular_font
            )

            # Previous / pause / next controls.
            controls_y = card_y + 238
            cx = text_x + 255

            panel_draw.polygon(
                [(cx - 135, controls_y + 12), (cx - 105, controls_y - 8), (cx - 105, controls_y + 32)],
                fill="white"
            )
            panel_draw.polygon(
                [(cx - 108, controls_y + 12), (cx - 78, controls_y - 8), (cx - 78, controls_y + 32)],
                fill="white"
            )

            panel_draw.rounded_rectangle(
                (cx - 18, controls_y - 12, cx - 4, controls_y + 36),
                radius=5,
                fill="white"
            )
            panel_draw.rounded_rectangle(
                (cx + 8, controls_y - 12, cx + 22, controls_y + 36),
                radius=5,
                fill="white"
            )

            panel_draw.polygon(
                [(cx + 105, controls_y + 12), (cx + 75, controls_y - 8), (cx + 75, controls_y + 32)],
                fill="white"
            )
            panel_draw.polygon(
                [(cx + 132, controls_y + 12), (cx + 102, controls_y - 8), (cx + 102, controls_y + 32)],
                fill="white"
            )

            # Volume bar.
            vol_y = card_y + 315
            panel_draw.polygon(
                [(text_x + 10, vol_y + 8), (text_x + 25, vol_y - 3), (text_x + 25, vol_y + 19), (text_x + 10, vol_y + 8)],
                fill=(190, 210, 230)
            )
            panel_draw.rounded_rectangle(
                (text_x + 70, vol_y + 5, text_x + 455, vol_y + 11),
                radius=5,
                fill=(70, 95, 120)
            )
            panel_draw.rounded_rectangle(
                (text_x + 70, vol_y + 5, text_x + 260, vol_y + 11),
                radius=5,
                fill=(175, 205, 230)
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
