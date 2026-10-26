"""Safe Shruti direct-audio integration.

This module wraps the existing YouTube stream extractor instead of replacing it.
For normal YouTube audio tracks, Shruti is tried first. If the API is disabled,
not configured, unavailable, or returns a non-media response, the original
yt-dlp extraction path is used unchanged.
"""

from __future__ import annotations

from urllib.parse import urlencode

import aiohttp

from Elevenyts import config, logger


async def _probe(url: str) -> bool:
    """Lightly validate the Shruti endpoint without downloading the song."""
    timeout = aiohttp.ClientTimeout(total=max(2, config.SHRUTI_TIMEOUT))
    headers = {"Range": "bytes=0-1"}

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                headers=headers,
                allow_redirects=False,
            ) as response:
                content_type = (
                    response.headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )

                # Redirects are enough to prove that the API accepted the
                # request; PyTgCalls can follow the final media URL itself.
                if response.status in {301, 302, 303, 307, 308}:
                    return bool(response.headers.get("Location"))

                if response.status not in {200, 206}:
                    return False

                if content_type in {
                    "application/json",
                    "text/html",
                    "text/plain",
                }:
                    return False

                return True

    except Exception as exc:
        logger.debug(f"Shruti probe failed: {exc}")
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
    """Install Shruti as a safe first-choice audio source on the existing YouTube object."""
    original_get_stream_info = youtube.get_stream_info

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
                logger.info(
                    f"⚡ Shruti direct audio source ready: {video_id}"
                )
                return {
                    "url": stream_url,
                    "headers": {},
                    "source": "shruti",
                }

            logger.warning(
                f"⚠️ Shruti unavailable for {video_id}; "
                "falling back to existing yt-dlp extractor."
            )

        return await original_get_stream_info(
            video_id,
            is_live=is_live,
            video=video,
        )

    youtube.get_stream_info = get_stream_info_with_shruti
    logger.info(
        "🎵 Shruti direct audio integration installed "
        "with yt-dlp fallback."
    )
