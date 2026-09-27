import asyncio
import logging
import re
import wave
from io import BytesIO

import numpy as np
from pytgcalls import filters as call_filters
from pytgcalls.types import Device, Direction, StreamFrames

logger = logging.getLogger(__name__)

# ==========================================================
# Voice Command Settings
# ==========================================================

SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2

SILENCE_SECONDS = 1.2
SILENCE_RMS = 0.008
MAX_BUFFER_SECONDS = 12

# Whisper model
MODEL_NAME = "base"


# ==========================================================
# Audio Buffer
# ==========================================================

class AudioBuffer:

    def __init__(self):
        self.data = bytearray()
        self.silent_seconds = 0.0
        self.has_speech = False
        self.processing = False

    def add(self, audio: bytes):

        if not audio:
            return

        self.data.extend(audio)

        samples = np.frombuffer(
            audio,
            dtype=np.int16,
        )

        if len(samples) == 0:
            return

        samples_float = (
            samples.astype(np.float32) / 32768.0
        )

        rms = float(
            np.sqrt(
                np.mean(
                    samples_float ** 2
                )
            )
        )

        duration = len(samples) / (
            SAMPLE_RATE * CHANNELS
        )

        if rms >= SILENCE_RMS:
            self.has_speech = True
            self.silent_seconds = 0.0
        else:
            self.silent_seconds += duration

    def clear(self):

        self.data.clear()
        self.silent_seconds = 0.0
        self.has_speech = False
        self.processing = False

    def too_large(self):

        max_bytes = (
            SAMPLE_RATE
            * CHANNELS
            * SAMPLE_WIDTH
            * MAX_BUFFER_SECONDS
        )

        return len(self.data) >= max_bytes


# ==========================================================
# Voice Command Manager
# ==========================================================

class VoiceCommandManager:

    def __init__(self):

        self.buffers = {}

        self.whisper_model = None
        self.model_loading = False

    # ------------------------------------------------------
    # Whisper model
    # ------------------------------------------------------

    def _load_model(self):

        if self.whisper_model is not None:
            return self.whisper_model

        if self.model_loading:
            return None

        self.model_loading = True

        try:

            from faster_whisper import WhisperModel

            logger.info(
                "🎤 Loading Faster-Whisper model: %s",
                MODEL_NAME,
            )

            self.whisper_model = WhisperModel(
                MODEL_NAME,
                device="cpu",
                compute_type="int8",
            )

            logger.info(
                "🎤 Faster-Whisper model loaded."
            )

            return self.whisper_model

        except Exception:

            logger.exception(
                "❌ Failed to load Faster-Whisper model"
            )

            return None

        finally:

            self.model_loading = False

    # ------------------------------------------------------
    # WAV creation
    # ------------------------------------------------------

    @staticmethod
    def _make_wav(audio: bytes) -> bytes:

        output = BytesIO()

        with wave.open(output, "wb") as wav:

            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(audio)

        return output.getvalue()

    # ------------------------------------------------------
    # Speech → Text
    # ------------------------------------------------------

    async def transcribe(
        self,
        audio: bytes,
    ):

        if not audio:
            return None

        model = self._load_model()

        if model is None:
            return None

        wav_data = self._make_wav(audio)

        def run_whisper():

            try:

                segments, info = model.transcribe(
                    wav_data,
                    beam_size=5,
                    vad_filter=True,
                    language=None,
                )

                text = " ".join(
                    segment.text.strip()
                    for segment in segments
                    if segment.text
                )

                return text.strip()

            except Exception:

                logger.exception(
                    "❌ Whisper transcription failed"
                )

                return None

        return await asyncio.to_thread(
            run_whisper
        )

    # ------------------------------------------------------
    # Detect "Play <song>"
    # ------------------------------------------------------

    @staticmethod
    def extract_song(text: str):

        if not text:
            return None

        text = text.strip()

        pattern = (
            r"^\s*"
            r"(?:play|प्ले)"
            r"(?:\s+|[,:;.!?\-]+)"
            r"(.+?)"
            r"\s*$"
        )

        match = re.match(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        song = match.group(1).strip()

        if not song:
            return None

        return song

    # ------------------------------------------------------
    # Get direct stream URL
    # ------------------------------------------------------

    async def get_direct_stream(
        self,
        yt,
        media,
    ):

        try:

            stream_url = await yt.get_stream_url(
                media.id,
                is_live=getattr(
                    media,
                    "is_live",
                    False,
                ),
                video=getattr(
                    media,
                    "video",
                    False,
                ),
            )

            if stream_url:

                media.file_path = stream_url

                logger.info(
                    "🔗 Direct stream URL obtained for: %s",
                    media.title,
                )

                return stream_url

            logger.error(
                "❌ Direct stream URL is empty for: %s",
                media.title,
            )

            return None

        except Exception as e:

            logger.error(
                "❌ Direct stream extraction failed for %s: %s",
                media.title,
                e,
                exc_info=True,
            )

            return None

    # ------------------------------------------------------
    # Process command
    # ------------------------------------------------------

    async def process_command(
        self,
        chat_id: int,
        text: str,
    ):

        song = self.extract_song(text)

        # Normal conversation ignore
        if not song:
            return

        logger.info(
            "🎤 Voice command detected in %s: Play %s",
            chat_id,
            song,
        )

        try:

            # Import only when command is detected.
            from Elevenyts import (
                app,
                config,
                db,
                queue,
                tune,
                yt,
            )

            # ------------------------------------------------
            # Queue limit
            # ------------------------------------------------

            try:

                queue_count = queue.count(
                    chat_id
                )

                if queue_count >= config.QUEUE_LIMIT:

                    await app.send_message(
                        chat_id,
                        "❌ <b>Queue limit reached.</b>",
                    )

                    return

            except Exception:

                pass

            # ------------------------------------------------
            # Search YouTube
            # ------------------------------------------------

            try:

                media = await yt.search(
                    song,
                    0,
                )

            except Exception as e:

                logger.error(
                    "❌ Voice YouTube search failed: %s",
                    e,
                )

                return

            if not media:

                await app.send_message(
                    chat_id,
                    f"❌ <b>Song not found:</b> {song}",
                )

                return

            # ------------------------------------------------
            # Duration check
            # ------------------------------------------------

            try:

                if (
                    not media.is_live
                    and media.duration_sec
                    and media.duration_sec
                    > config.DURATION_LIMIT * 60
                ):

                    await app.send_message(
                        chat_id,
                        "❌ <b>Song duration is too long.</b>",
                    )

                    return

            except Exception:

                pass

            media.user = "🎤 Voice Command"

            # ------------------------------------------------
            # Music already playing
            # ------------------------------------------------

            if await db.get_call(chat_id):

                # Do NOT download the song here.
                # The direct stream URL will be extracted
                # when this track actually starts playing.

                media.file_path = None

                queue.add(
                    chat_id,
                    media,
                )

                await app.send_message(
                    chat_id,
                    (
                        "🎤 <b>Voice Command</b>\n\n"
                        f"🎵 <b>Added to queue:</b>\n"
                        f"{media.title}"
                    ),
                )

                return

            # ------------------------------------------------
            # Direct streaming
            # ------------------------------------------------

            media.file_path = None

            stream_url = await self.get_direct_stream(
                yt,
                media,
            )

            if not stream_url:

                await app.send_message(
                    chat_id,
                    (
                        "❌ <b>Unable to get direct stream.</b>\n"
                        "Please try the song again."
                    ),
                )

                return

            # ------------------------------------------------
            # Add to queue
            # ------------------------------------------------

            queue.add(
                chat_id,
                media,
            )

            # ------------------------------------------------
            # Start playback
            # ------------------------------------------------

            await tune.play_media(
                chat_id=chat_id,
                message=None,
                media=media,
            )

            logger.info(
                "▶️ Voice direct streaming started: %s",
                media.title,
            )

        except Exception:

            logger.exception(
                "❌ Error processing voice command in %s",
                chat_id,
            )

    # ------------------------------------------------------
    # Process completed speech
    # ------------------------------------------------------

    async def process_audio(
        self,
        chat_id: int,
        buffer: AudioBuffer,
    ):

        if buffer.processing:
            return

        if not buffer.has_speech:

            buffer.clear()

            return

        buffer.processing = True

        audio = bytes(
            buffer.data
        )

        # Clear immediately so next speech can record.
        buffer.clear()

        try:

            text = await self.transcribe(
                audio
            )

            if not text:
                return

            logger.info(
                "🎤 Voice transcript [%s]: %s",
                chat_id,
                text,
            )

            await self.process_command(
                chat_id,
                text,
            )

        except Exception:

            logger.exception(
                "❌ Voice audio processing error"
            )

    # ------------------------------------------------------
    # Incoming audio frames
    # ------------------------------------------------------

    async def handle_frames(
        self,
        update: StreamFrames,
    ):

        chat_id = update.chat_id

        if not chat_id:
            return

        for frame in update.frames:

            audio = getattr(
                frame,
                "frame",
                None,
            )

            if audio is None:

                audio = getattr(
                    frame,
                    "data",
                    None,
                )

            if not audio:
                continue

            ssrc = getattr(
                frame,
                "ssrc",
                0,
            )

            key = (
                chat_id,
                ssrc,
            )

            if key not in self.buffers:

                self.buffers[key] = AudioBuffer()

            buffer = self.buffers[key]

            buffer.add(audio)

            # ------------------------------------------------
            # Speech finished
            # ------------------------------------------------

            if (
                buffer.has_speech
                and buffer.silent_seconds
                >= SILENCE_SECONDS
            ):

                if not buffer.processing:

                    asyncio.create_task(
                        self.process_audio(
                            chat_id,
                            buffer,
                        )
                    )

            # ------------------------------------------------
            # Safety limit
            # ------------------------------------------------

            if buffer.too_large():

                if (
                    buffer.has_speech
                    and not buffer.processing
                ):

                    asyncio.create_task(
                        self.process_audio(
                            chat_id,
                            buffer,
                        )
                    )

                else:

                    buffer.clear()

    # ------------------------------------------------------
    # Register listener
    # ------------------------------------------------------

    def register(
        self,
        client,
    ):

        @client.on_update(
            call_filters.stream_frame(
                Direction.INCOMING,
                Device.MICROPHONE
                | Device.SPEAKER,
            )
        )
        async def voice_frames(
            _,
            update: StreamFrames,
        ):

            try:

                await self.handle_frames(
                    update
                )

            except Exception:

                logger.exception(
                    "❌ Voice frame handler error"
                )


# ==========================================================
# Global Manager
# ==========================================================

voice_commands = VoiceCommandManager()


def register_voice_listener(client):

    voice_commands.register(
        client
    )

    logger.info(
        "🎤 Voice command listener registered."
    )