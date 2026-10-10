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
            output = f"cache/{song.id}_full_v6.png"

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


    async def fetch_synced_lyrics(self, song: Track) -> list[tuple[int, str]]:
        """Fetch timestamped lyrics from LRCLIB; return [] when unavailable."""
        title = str(getattr(song, "title", "") or "").strip()
        artist = str(getattr(song, "channel_name", "") or "").strip()
        if not title:
            return []
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "https://lrclib.net/api/search",
                    params={"track_name": title, "artist_name": artist},
                    headers={"User-Agent": "AppleMusixBot/1.0"},
                ) as response:
                    if response.status != 200:
                        return []
                    data = await response.json(content_type=None)
            candidates = sorted(
                data if isinstance(data, list) else [],
                key=lambda item: bool(item.get("syncedLyrics")),
                reverse=True,
            )
            synced = next(
                (item.get("syncedLyrics") for item in candidates if item.get("syncedLyrics")),
                None,
            )
            if not synced:
                return []
            lines = []
            for raw in synced.splitlines():
                match = re.match(r"\s*\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]\s*(.*)", raw)
                if not match:
                    continue
                minutes, seconds, fraction, text = match.groups()
                millis = int((fraction or "0").ljust(3, "0")[:3])
                timestamp = int(minutes) * 60 + int(seconds) + millis / 1000
                if text.strip():
                    lines.append((timestamp, text.strip()))
            return sorted(lines)
        except Exception:
            return []

    async def generate_live_frame(
        self,
        song: Track,
        position: int,
        lyrics: list[tuple[int, str]],
    ) -> str:
        """Render a playback-synced frame without changing the base artwork."""
        base = await self.generate(song)
        try:
            frame = Image.open(base).convert("RGBA")
            draw = ImageDraw.Draw(frame)
            # Hide the static duration/play pill while preserving the card layout.
            draw.rounded_rectangle((465, 255, 910, 425), radius=18, fill=(14, 20, 43, 255))
            pink = (255, 82, 157, 255)
            white = (245, 247, 255, 255)
            muted = (151, 161, 190, 255)
            try:
                lyric_font = ImageFont.truetype("Elevenyts/helpers/Inter-Light.ttf", 21)
                small_font = ImageFont.truetype("Elevenyts/helpers/Inter-Light.ttf", 17)
            except OSError:
                lyric_font = ImageFont.load_default()
                small_font = ImageFont.load_default()

            active = -1
            for i, (stamp, _) in enumerate(lyrics):
                if stamp <= position:
                    active = i
                else:
                    break
            visible = []
            if active >= 0:
                visible.extend([(i, lyrics[i][1]) for i in range(max(0, active - 2), min(len(lyrics), active + 3))])
            elif lyrics:
                visible.extend([(i, lyrics[i][1]) for i in range(min(5, len(lyrics)))])
            if not visible:
                visible = [(-1, "♪  Lyrics unavailable for this track  ♪")]

            y = 266 + max(0, (5 - len(visible)) * 12)
            for index, line in visible[:5]:
                color = pink if index == active else (white if index >= 0 else muted)
                text = trim_to_width(line, lyric_font, 410)
                draw.text((480, y), text, fill=color, font=lyric_font)
                y += 31

            duration = max(0, int(getattr(song, "duration_sec", 0) or 0))
            x1, x2, bar_y = 480, 885, 454
            draw.rounded_rectangle((x1, bar_y, x2, bar_y + 5), radius=3, fill=(64, 71, 99, 255))
            progress = min(1.0, position / duration) if duration else 0.0
            fill_x = x1 + int((x2 - x1) * progress)
            draw.rounded_rectangle((x1, bar_y, max(x1 + 1, fill_x), bar_y + 5), radius=3, fill=pink)
            def stamp(seconds):
                seconds = max(0, int(seconds))
                return f"{seconds // 60:02d}:{seconds % 60:02d}"
            draw.text((480, 468), stamp(position), fill=white, font=small_font)
            draw.text((825, 468), stamp(duration), fill=muted, font=small_font)

            output = f"cache/{song.id}_live_{int(position // 8)}.png"
            frame.save(output)
            return output
        except Exception:
            return base

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
                bg_color = (14, 20, 43, 255)
                card = Image.new("RGBA", (player_w, player_h), bg_color)
                draw = ImageDraw.Draw(card)

                # Soft inner highlight, while keeping the background color fixed.
                # Clean card: no visible outer border.


                # Artwork: TRUE SQUARE cover.
                # The player always shows a 1:1 cover area.  The source is
                # proportionally resized and softly extended to the square
                # so the cover never becomes a visible 16:9 rectangle.
                art_size = 390
                art_x, art_y = 36, 66

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
                rx = 480
                rw = player_w - rx - 42

                now_font = ImageFont.truetype(
                    "Elevenyts/helpers/Raleway-Bold.ttf", 24
                )
                title_font = ImageFont.truetype(
                    "Elevenyts/helpers/Raleway-Bold.ttf", 44
                )
                artist_font = ImageFont.truetype(
                    "Elevenyts/helpers/Inter-Light.ttf", 31
                )
                small_font = ImageFont.truetype(
                    "Elevenyts/helpers/Inter-Light.ttf", 24
                )

                accent = (255, 82, 157, 255)
                artist_color = (255, 164, 204, 255)
                muted = (164, 173, 202, 255)
                white = (250, 252, 251, 255)
                dark = (14, 20, 43, 255)

                draw.text(
                    (rx, 102),
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
                    (rx, 151),
                    title,
                    fill=white,
                    font=title_font
                )

                draw.text(
                    (rx, 218),
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
                    (rx, 273),
                    duration_label,
                    fill=muted,
                    font=small_font
                )

                # Compact reference-style Play pill.
                pill_x, pill_y = rx, 331
                pill_w, pill_h = 230, 58

                draw.rounded_rectangle(
                    (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
                    radius=29,
                    fill=accent
                )

                py = pill_y + pill_h // 2
                draw.polygon(
                    [
                        (pill_x + 48, py - 15),
                        (pill_x + 48, py + 15),
                        (pill_x + 75, py)
                    ],
                    fill=dark
                )

                draw.text(
                    (pill_x + 103, pill_y + 8),
                    "Play",
                    fill=dark,
                    font=ImageFont.truetype(
                        "Elevenyts/helpers/Raleway-Bold.ttf", 28
                    )
                )

                # Reference music icon in the upper-right corner.
                mx, my = player_w - 88, 52
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
