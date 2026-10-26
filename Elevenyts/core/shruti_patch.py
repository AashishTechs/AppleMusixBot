"""Safe Shruti direct-audio integration.

Shruti is used only for ordinary YouTube audio tracks. The API response is
followed and checked for a successful media response before it is handed to
PyTgCalls. Any configuration, network, redirect, or content-validation failure
falls back to the existing yt-dlp extractor.
"""

from __future__ import annotations

from urllib.parse import urlencode

import aiohttp

from Elevenyts import config, logger


_MEDIA_TYPES = ("audio/", "application/octet-stream", "binary/octet-stream")


async def _probe(url: str) -> bool:
    """Validate that the Shruti endpoint resolves to a readable media response.

    Only one byte is requested/read, so the probe does not intentionally
    download the track. Redirects are followed so a redirect to an error page
    or an invalid destination is not mistaken for a valid media stream.
    """
    timeout = aiohttp.ClientTimeout(total=max(2, config.SHRUTI_TIMEOUT))
    headers = {"Range": "bytes=0-0"}

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                headers=headers,
                allow_redirects=True,
                max_redirects=5,
            ) as response:
                if response.status not in {200, 206}:
                    return False

                content_type = (
                    response.headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )

                if not any(content_type.startswith(kind) for kind in _MEDIA_TYPES):
                    return False

                # Require a non-empty response. The Range header asks for a
                # single byte; if the server ignores Range, close after one byte.
                first_byte = await response.content.read(1)
                if not first_byte:
                    return False

                return True

    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        logger.debug("Shruti probe failed: %s", type(exc).__name__)
        return False
    except Exception as exc:
        logger.debug("Shruti probe failed: %s", type(exc).__name__)
        return False


def _build_url(video_id: str) -> str:
    query = urlencode(
        {
            "url": video_id,
            "type": "audio",
            "api_key": config.SHRUTI_API_KEY,
        }
    )
    return f"{config.SHRUTI_API_URL}/download?{query}"


def install(youtube) -> None:
    """Install Shruti as a first-choice source, preserving the original extractor."""
    original_get_stream_info = youtube.get_stream_info

    # Keep a reference so playback code can explicitly fall back if needed.
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
            stream_url = _build_url(video_id)

            if await _probe(stream_url):
                logger.info("Shruti media response validated for track %s", video_id)
                return {
                    "url": stream_url,
                    "headers": {},
                    "source": "shruti",
                }

            logger.warning(
                "Shruti validation failed for track %s; using yt-dlp fallback.",
                video_id,
            )

        return await original_get_stream_info(
            video_id,
            is_live=is_live,
            video=video,
        )

    youtube.get_stream_info = get_stream_info_with_shruti
    logger.info("Shruti audio source installed with yt-dlp extraction fallback.")
