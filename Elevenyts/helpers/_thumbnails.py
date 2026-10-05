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
            # Compact 16:9 player card, matching the reference-style
            # Telegram music panel. The artwork and controls are rendered
            # inside one image; the NOW PLAYING info remains outside this image.
            panel_w, panel_h = 930, 523

            with Image.open(temp) as src:
                source = src.convert("RGBA")

                # Soft blurred background behind the player content.
                bg = ImageOps.fit(
                    source,
                    (panel_w, panel_h),
                    method=Image.Resampling.LANCZOS
                )
                bg = bg.filter(ImageFilter.GaussianBlur(24))
                bg = ImageEnhance.Brightness(bg).enhance(0.28)
                bg = ImageEnhance.Contrast(bg).enhance(1.10)

                # Dark translucent overlay for a premium player look.
                overlay = Image.new("RGBA", (panel_w, panel_h), (8, 15, 24, 105))
                bg = Image.alpha_composite(bg, overlay)

                # Full player surface — no outer padding.
                player = Image.new(
                    "RGBA",
                    (panel_w, panel_h),
                    (12, 22, 34, 245)
                )

                # Artwork occupies the left side of the compact 16:9 card.
                art_w = int(panel_w * 0.48)
                art_h = panel_h - 34
                art = ImageOps.fit(
                    source,
                    (art_w, art_h),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5)
                )

                art_mask = Image.new("L", art.size, 0)
                ImageDraw.Draw(art_mask).rounded_rectangle(
                    (0, 0, art.size[0] - 1, art.size[1] - 1),
                    radius=24,
                    fill=255
                )
                player.paste(art, (17, 17), art_mask)

                draw = ImageDraw.Draw(player)

                # Right-side player controls.
                info_x = art_w + 42
                title = trim_to_width(
                    str(song.title or "Unknown Track"),
                    self.title_font,
                    panel_w - info_x - 35
                )
                artist = trim_to_width(
                    str(song.channel_name or "Apple Musix"),
                    self.regular_font,
                    panel_w - info_x - 35
                )

                draw.text(
                    (info_x, 72),
                    title,
                    fill=(245, 248, 252),
                    font=self.title_font
                )
                draw.text(
                    (info_x, 124),
                    artist,
                    fill=(185, 205, 225),
                    font=self.regular_font
                )

                # Progress line.
                progress_x = info_x
                progress_w = panel_w - info_x - 38
                progress_y = 188
                draw.rounded_rectangle(
                    (progress_x, progress_y, progress_x + progress_w, progress_y + 6),
                    radius=5,
                    fill=(100, 115, 130)
                )
                draw.rounded_rectangle(
                    (progress_x, progress_y, progress_x + int(progress_w * 0.22), progress_y + 6),
                    radius=5,
                    fill=(245, 248, 252)
                )
                draw.ellipse(
                    (
                        progress_x + int(progress_w * 0.22) - 6,
                        progress_y - 3,
                        progress_x + int(progress_w * 0.22) + 6,
                        progress_y + 9
                    ),
                    fill=(245, 248, 252)
                )

                draw.text(
                    (progress_x, 204),
                    "0:00",
                    fill=(205, 215, 225),
                    font=self.regular_font
                )

                duration = str(getattr(song, "duration", "") or "")
                duration_text = f"-{duration}" if duration else "-:--"
                duration_bbox = draw.textbbox((0, 0), duration_text, font=self.regular_font)
                draw.text(
                    (progress_x + progress_w - (duration_bbox[2] - duration_bbox[0]), 204),
                    duration_text,
                    fill=(205, 215, 225),
                    font=self.regular_font
                )

                # Previous / pause / next controls.
                controls_y = 286
                center_x = info_x + progress_w // 2

                draw.text(
                    (center_x - 112, controls_y),
                    "◀◀",
                    fill=(248, 250, 252),
                    font=self.signature_font
                )
                draw.text(
                    (center_x - 20, controls_y - 4),
                    "Ⅱ",
                    fill=(248, 250, 252),
                    font=self.title_font
                )
                draw.text(
                    (center_x + 70, controls_y),
                    "▶▶",
                    fill=(248, 250, 252),
                    font=self.signature_font
                )

                # Volume line.
                volume_y = 360
                draw.text(
                    (info_x, volume_y - 8),
                    "⌕",
                    fill=(220, 230, 240),
                    font=self.signature_font
                )
                draw.rounded_rectangle(
                    (info_x + 35, volume_y, info_x + progress_w, volume_y + 6),
                    radius=5,
                    fill=(105, 120, 135)
                )
                draw.rounded_rectangle(
                    (info_x + 35, volume_y, info_x + 35 + int((progress_w - 35) * 0.68), volume_y + 6),
                    radius=5,
                    fill=(245, 248, 252)
                )

                # Small Telegram/player-style utility icons.
                draw.text(
                    (center_x - 55, 412),
                    "▢",
                    fill=(205, 215, 225),
                    font=self.regular_font
                )
                draw.text(
                    (center_x + 10, 412),
                    "☷",
                    fill=(205, 215, 225),
                    font=self.regular_font
                )

                # Apple Musix signature.
                draw.text(
                    (28, panel_h - 38),
                    "Apple Musix <<3",
                    fill=(90, 190, 245),
                    font=self.signature_font
                )

                # Rounded outer edge, matching the reference card.
                mask = Image.new("L", player.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, panel_w - 1, panel_h - 1),
                    radius=30,
                    fill=255
                )

                final = Image.new("RGBA", player.size, (8, 15, 24, 255))
                final.paste(player, (0, 0), mask)

                final.save(output)

            try:
                os.remove(temp)
            except OSError:
                pass

            return output


        except Exception:
            return config.DEFAULT_THUMB
