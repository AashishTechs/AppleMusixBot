import asyncio
import time
from typing import Dict, Set

from Elevenyts import logger


class PreloadManager:
    """
    Pre-extract direct YouTube stream URLs for upcoming queue items.

    This does NOT download MP3/MP4 files. URLs are kept only briefly because
    YouTube direct stream URLs are temporary.
    """

    CACHE_TTL = 90

    def __init__(self):
        self.tasks: Dict[int, Set[asyncio.Task]] = {}
        self._preloading: Set[str] = set()
        self._cache: Dict[str, tuple[str, dict, float]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _lock_for(self, track_id: str) -> asyncio.Lock:
        lock = self._locks.get(track_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[track_id] = lock
        return lock

    def get_cached_stream(self, track_id: str) -> tuple[str, dict] | None:
        cached = self._cache.get(track_id)
        if not cached:
            return None

        url, headers, expires_at = cached
        if expires_at <= time.monotonic():
            self._cache.pop(track_id, None)
            return None

        return url, headers

    def get_cached_url(self, track_id: str) -> str | None:
        cached = self.get_cached_stream(track_id)
        return cached[0] if cached else None

    def set_cached_url(
        self,
        track_id: str,
        url: str,
        headers: dict | None = None,
    ) -> None:
        self._cache[track_id] = (
            url,
            dict(headers or {}),
            time.monotonic() + self.CACHE_TTL,
        )

    async def start_preload(self, chat_id: int, count: int = 2):
        """Extract stream URLs for the next queued tracks in the background."""
        from Elevenyts import queue, yt

        try:
            upcoming_tracks = queue.peek_next(chat_id, count)

            for track in upcoming_tracks:
                track_id = getattr(track, "id", None)
                if not track_id or self.get_cached_url(track_id):
                    continue

                task = asyncio.create_task(
                    self._preload_track(chat_id, track, yt)
                )
                self.tasks.setdefault(chat_id, set()).add(task)

                def _done(done_task, cid=chat_id):
                    self.tasks.get(cid, set()).discard(done_task)

                task.add_done_callback(_done)

        except Exception as e:
            logger.error(
                f"Preload manager error in chat {chat_id}: {e}"
            )

    async def _preload_track(self, chat_id: int, track, yt=None):
        """Extract and cache a temporary direct stream URL."""
        track_id = getattr(track, "id", None)
        if not track_id or track_id in self._preloading:
            return

        self._preloading.add(track_id)
        lock = self._lock_for(track_id)

        try:
            async with lock:
                if self.get_cached_url(track_id):
                    return

                if yt is None:
                    from Elevenyts import yt

                stream_info = await yt.get_stream_info(
                    track_id,
                    is_live=getattr(track, "is_live", False),
                    video=getattr(track, "video", False),
                )

                if stream_info and stream_info.get("url"):
                    self.set_cached_url(
                        track_id,
                        stream_info["url"],
                        stream_info.get("headers"),
                    )
                    logger.debug(
                        f"Preloaded stream URL for {track_id} in chat {chat_id}"
                    )

        except Exception as e:
            logger.debug(
                f"Preload track failed for {track_id} in chat {chat_id}: {e}"
            )
        finally:
            self._preloading.discard(track_id)

    async def cancel_preload(self, chat_id: int):
        tasks = self.tasks.get(chat_id)

        if tasks:
            for task in list(tasks):
                if not task.done():
                    task.cancel()

            for task in list(tasks):
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.debug(
                        f"Preload cancellation error in chat {chat_id}: {e}"
                    )

            tasks.clear()
            self.tasks.pop(chat_id, None)

    async def cancel_all(self):
        for chat_id in list(self.tasks.keys()):
            await self.cancel_preload(chat_id)

        self._preloading.clear()
        self._cache.clear()
        self._locks.clear()

    def is_preloading(self, track_id: str) -> bool:
        return track_id in self._preloading

    def clear(self):
        self._preloading.clear()
        self.tasks.clear()
        self._cache.clear()
        self._locks.clear()


preload = PreloadManager()
