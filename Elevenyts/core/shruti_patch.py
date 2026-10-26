"""Shruti audio integration with validated downloads and safe yt-dlp fallback.

The Shruti endpoint returns the audio body, not a short-lived media URL.
Download and validate the response before passing a local file to FFmpeg.
If the API fails, fall back to the existing YouTube extractor.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import aiohttp

from Elevenyts import config, logger


_DOWNLOAD_DIR = Path("downloads") / "shruti"
_MIN_AUDIO_BYTES = 16 * 1024
_AUDIO_CONTENT_TYPES = ("audio/", "application/octet-stream", "binary/octet-stream")
_AUDIO_EXTENSIONS = {
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/webm": ".webm",
    "audio/flac": ".flac",
}


def _extension_for_content_type(content_type: str) -> str:
    """Choose a filename extension matching the response's audio container."""
    mime_type = content_type.split(";", 1)[0].strip().lower()
    return _AUDIO_EXTENSIONS.get(mime_type, ".audio")


async def _download_audio(video_id: str) -> str | None:
    """Download one Shruti audio response to a validated local cache file."""
    if not video_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in video_id):
        return None

    # Shruti currently responds with audio/mp4. Reuse only the matching
    # .m4a cache; don't mistake old MP4 bytes saved as .mp3 for real MP3.
    cached_m4a = _DOWNLOAD_DIR / f"{video_id}.m4a"
    partial = _DOWNLOAD_DIR / f"{video_id}.{uuid.uuid4().hex}.part"

    try:
        _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        if cached_m4a.is_file() and cached_m4a.stat().st_size >= _MIN_AUDIO_BYTES:
            return str(cached_m4a.resolve())
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
    target: Path | None = None

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

                extension = _extension_for_content_type(content_type)
                target = _DOWNLOAD_DIR / f"{video_id}{extension}"
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
        logger.info(
            "Shruti audio downloaded for track %s (%s bytes, %s).",
            video_id,
            written,
            target.suffix,
        )
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
