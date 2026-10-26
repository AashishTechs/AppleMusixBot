"""Shruti audio integration with validated downloads and safe yt-dlp fallback.

The Shruti endpoint returns the audio body, not a short-lived media URL.
Download and validate the response before passing a local file to FFmpeg.
If the API fails, fall back to the existing YouTube extractor.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import aiohttp

from Elevenyts import config, logger


_DOWNLOAD_DIR = Path("downloads") / "shruti"
_MIN_AUDIO_BYTES = 16 * 1024
_AUDIO_CONTENT_TYPES = ("audio/", "application/octet-stream", "binary/octet-stream")


async def _download_audio(video_id: str) -> str | None:
    """Download one Shruti audio response to a validated local cache file."""
    if not video_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in video_id):
        return None

    _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = _DOWNLOAD_DIR / f"{video_id}.mp3"
    partial = _DOWNLOAD_DIR / f"{video_id}.mp3.part"

    try:
        if target.is_file() and target.stat().st_size >= _MIN_AUDIO_BYTES:
            return str(target.resolve())
    except OSError:
        pass

    timeout = aiohttp.ClientTimeout(
        total=300,
        sock_connect=max(5, min(config.SHRUTI_TIMEOUT, 30)),
    )
    params = {
        "url": video_id,
        "type": "audio",
        "api_key": config.SHRUTI_API_KEY,
    }
    endpoint = f"{config.SHRUTI_API_URL.rstrip('/')}/download"

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(endpoint, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        "Shruti API returned HTTP %s for track %s; using YouTube fallback.",
                        response.status,
                        video_id,
                    )
                    return None

                content_type = response.headers.get("Content-Type", "").lower()
                if content_type and not any(
                    content_type.startswith(kind) for kind in _AUDIO_CONTENT_TYPES
                ):
                    logger.warning(
                        "Shruti returned non-audio content type for track %s; using YouTube fallback.",
                        video_id,
                    )
                    return None

                written = 0
                with partial.open("wb") as output:
                    async for chunk in response.content.iter_chunked(128 * 1024):
                        if not chunk:
                            continue
                        output.write(chunk)
                        written += len(chunk)

                if written < _MIN_AUDIO_BYTES:
                    logger.warning(
                        "Shruti returned an empty/too-small response for track %s; using YouTube fallback.",
                        video_id,
                    )
                    return None

        partial.replace(target)
        logger.info("Shruti audio downloaded and validated for track %s (%s bytes).", video_id, written)
        return str(target.resolve())

    except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
        logger.warning(
            "Shruti request failed for track %s (%s); using YouTube fallback.",
            video_id,
            type(exc).__name__,
        )
        return None
    except Exception:
        logger.exception("Unexpected Shruti error for track %s; using YouTube fallback.", video_id)
        return None
    finally:
        try:
            if partial.exists():
                partial.unlink()
        except OSError:
            pass


def install(youtube) -> None:
    """Install Shruti as an optional audio source, with yt-dlp fallback."""
    original_get_stream_info = youtube.get_stream_info
    youtube._shruti_original_get_stream_info = original_get_stream_info

    async def get_stream_info_with_shruti(
        video_id: str,
        is_live: bool = False,
        video: bool = False,
    ):
        use_shruti = (
            config.ENABLE_SHRUTI_API
            and bool(config.SHRUTI_API_KEY)
            and bool(config.SHRUTI_API_URL)
            and bool(video_id)
            and not video
            and not is_live
        )

        if use_shruti:
            logger.info("Trying Shruti audio source for track %s", video_id)
            audio_path = await _download_audio(video_id)
            if audio_path:
                return {
                    "url": audio_path,
                    "headers": {},
                    "source": "shruti",
                }
            logger.info("Shruti unavailable for track %s; falling back to YouTube.", video_id)

        return await original_get_stream_info(
            video_id,
            is_live=is_live,
            video=video,
        )

    youtube.get_stream_info = get_stream_info_with_shruti
    logger.info(
        "Shruti audio source hook installed (enabled=%s).",
        config.ENABLE_SHRUTI_API,
    )
