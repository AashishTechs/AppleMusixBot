import asyncio
from typing import Dict, Set

from Elevenyts import logger


class PreloadManager:
    """
    Direct-stream based preload manager.

    Important:
    - Songs ko MP3/MP4 me download nahi karta.
    - YouTube stream URLs ko advance me extract nahi karta,
      kyunki direct URLs expire ho sakte hain.
    - Actual playback ke time stream URL generate hoga.
    """

    def __init__(self):
        self.tasks: Dict[int, Set[asyncio.Task]] = {}
        self._preloading: Set[str] = set()

    async def start_preload(self, chat_id: int, count: int = 2):
        """
        Queue me upcoming tracks ko prepare karta hai.

        Direct streaming architecture me actual URL ko preload
        nahi karte, sirf manager ko active rakhte hain.
        """
        from Elevenyts import queue
        try:
            upcoming_tracks = queue.peek_next(chat_id, count)

            if not upcoming_tracks:
                return

            logger.debug(
                f"Direct streaming: {len(upcoming_tracks)} upcoming "
                f"track(s) ready for on-demand stream extraction "
                f"in chat {chat_id}"
            )

        except Exception as e:
            logger.error(
                f"Preload manager error in chat {chat_id}: {e}"
            )

    async def _preload_track(self, chat_id: int, track):
        """
        Compatibility method.

        Old system me ye function MP3/MP4 download karta tha.
        Ab intentionally kuch download nahi karta.
        """

        try:
            track_id = getattr(track, "id", None)

            if not track_id:
                return

            logger.debug(
                f"Skipping file preload for track {track_id}; "
                f"direct streaming will extract URL when playback starts."
            )

        except Exception as e:
            logger.error(
                f"Preload track error in chat {chat_id}: {e}"
            )

    async def cancel_preload(self, chat_id: int):
        """
        Existing preload tasks cancel karta hai.
        """

        tasks = self.tasks.get(chat_id)

        if not tasks:
            return

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
        """
        Sabhi chats ke preload tasks cancel karta hai.
        """

        chat_ids = list(self.tasks.keys())

        for chat_id in chat_ids:
            await self.cancel_preload(chat_id)

        self._preloading.clear()

    def is_preloading(self, track_id: str) -> bool:
        """
        Check karta hai ki track preload state me hai ya nahi.
        """

        return track_id in self._preloading

    def clear(self):
        """
        Internal state clear karta hai.
        """

        self._preloading.clear()
        self.tasks.clear()


preload = PreloadManager()