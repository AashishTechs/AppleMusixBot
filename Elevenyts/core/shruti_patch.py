"""Shruti direct-audio integration.

Shruti's documented /download endpoint returns the audio response itself rather
than a short-lived media URL. The endpoint has not passed a live health test,
so keep it disabled by default until it reliably returns audio. The URL is
handed directly to FFmpeg; HTTP errors after that point cannot be handled
reliably by the URL-extraction fallback.
"""

from __future__ import annotations

from urllib.parse import urlencode

from Elevenyts import config, logger


def _build_url(video_id: str) -> str:
    query = urlencode(
        {
            "url": video_id,
            "type": "audio",
            "api_key": config.SHRUTI_API_KEY,
        }
    )
    return f"{config.SHRUTI_API_URL.rstrip('/')}/download?{query}"


def install(youtube) -> None:
    """Install optional Shruti source.

yt-dlp is used when Shruti is disabled. This hook does not provide runtime
fallback after FFmpeg opens a Shruti URL, so keep the feature disabled until
the endpoint has been verified.
"""
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
            logger.info(
                "Using Shruti direct-audio endpoint for track %s",
                video_id,
            )
            return {
                "url": _build_url(video_id),
                "headers": {},
                "source": "shruti",
            }

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
