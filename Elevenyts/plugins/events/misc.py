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

import asyncio
import time

import pyrogram
from pyrogram import enums, filters, types

from Elevenyts import (
    tune,
    app,
    config,
    db,
    lang,
    logger,
    queue,
    tasks,
    userbot,
    yt,
)

from Elevenyts.helpers import buttons


@app.on_message(
    filters.regex(r"^/")
    & ~filters.service,
    group=-1
)
async def _maintenance_mode_check(
    _,
    m: types.Message
):
    """
    Global maintenance mode check.

    Runs before other handlers and blocks non-sudo
    users when maintenance mode is enabled.
    """

    # Skip sudo users
    if not m.from_user or m.from_user.id in app.sudoers:
        return

    maintenance = await db.get_maintenance()

    if maintenance:

        try:

            await m.reply_text(
                "<blockquote><b>🔧 Bot Under Maintenance</b>\n\n"
                "The bot is currently undergoing maintenance.\n"
                "Please try again later.</blockquote>"
            )

        except Exception:
            pass

        raise pyrogram.StopPropagation


@app.on_message(
    filters.video_chat_started,
    group=19
)
@app.on_message(
    filters.video_chat_ended,
    group=20
)
async def _watcher_vc(
    _,
    m: types.Message
):
    await tune.stop(
        m.chat.id
    )


async def auto_leave():
    """
    Auto-leave inactive groups.

    Runs in background with error recovery.
    """

    while True:

        try:

            await asyncio.sleep(1800)

            for ub in userbot.clients:

                left = 0

                try:

                    for dialog in await ub.get_dialogs():

                        chat_id = dialog.chat.id

                        if left >= 20:
                            break

                        # Skip logger and excluded chats
                        excluded = [
                            app.logger,
                            *config.EXCLUDED_CHATS
                        ]

                        if chat_id in excluded:
                            continue

                        if dialog.chat.type in [
                            enums.ChatType.GROUP,
                            enums.ChatType.SUPERGROUP,
                        ]:

                            if chat_id in db.active_calls:
                                continue

                            await ub.leave_chat(
                                chat_id
                            )

                            left += 1

                        await asyncio.sleep(5)

                except Exception as e:

                    username = (
                        ub.me.username
                        if hasattr(ub, "me")
                        and ub.me
                        else "Unknown"
                    )

                    logger.error(
                        f"Auto-leave error for assistant "
                        f"{username}: {e}"
                    )

                    continue

        except Exception as e:

            logger.error(
                f"Critical error in auto_leave task: {e}"
            )

            await asyncio.sleep(60)

            continue


async def track_time():
    """
    Track playback time.

    Runs every second for active calls.
    """

    while True:

        try:

            await asyncio.sleep(1)

            for chat_id in list(
                db.active_calls
            ):

                try:

                    if not await db.playing(
                        chat_id
                    ):
                        continue

                    media = queue.get_current(
                        chat_id
                    )

                    if not media:
                        continue

                    if not hasattr(
                        media,
                        "time"
                    ) or media.time is None:

                        media.time = 0

                    media.time += 1

                except Exception as e:

                    logger.debug(
                        f"track_time error for "
                        f"chat {chat_id}: {e}"
                    )

                    continue

        except Exception as e:

            logger.error(
                f"Critical error in track_time task: {e}"
            )

            await asyncio.sleep(1)

            continue


async def update_timer(
    length=10
):
    """
    Update progress bar every 20 seconds
    for active chats.

    IMPORTANT:
    Direct streaming architecture me
    next song ko MP3/MP4 me download nahi kiya jata.

    Actual direct stream URL playback ke time
    generate hota hai.
    """

    # Individual timer tasks by chat
    chat_tasks = {}

    async def _preload_next(
        chat_id,
        next_media
    ):
        """
        Compatibility preload function.

        OLD:
            yt.download()

        NEW:
            No file download.

        Direct stream URL actual playback ke time
        generate hoga.
        """

        try:

            media_id = getattr(
                next_media,
                "id",
                None
            )

            if not media_id:
                return

            # Never keep an old MP3/MP4 path
            # in direct-stream mode.
            next_media.file_path = None

            logger.debug(
                f"Skipping file preload for chat "
                f"{chat_id}: "
                f"{getattr(next_media, 'title', media_id)}"
            )

        except Exception as e:

            logger.debug(
                f"Preload preparation error "
                f"for chat {chat_id}: {e}"
            )

    async def update_chat_timer(
        chat_id
    ):
        """
        Update timer for a specific chat.
        """

        while True:

            try:

                await asyncio.sleep(20)

                # Check active call and playback
                if (
                    chat_id not in db.active_calls
                    or not await db.playing(chat_id)
                ):
                    break

                media = queue.get_current(
                    chat_id
                )

                if not media:
                    break

                # Ensure media.time exists
                if (
                    not hasattr(media, "time")
                    or media.time is None
                ):
                    media.time = 0

                duration = media.duration_sec
                message_id = media.message_id

                if not duration or not message_id:
                    continue

                played = media.time

                remaining = duration - played

                # --------------------------------------------------
                # Progress bar
                # --------------------------------------------------

                bar_length = 12

                if duration == 0:

                    percentage = 0

                else:

                    percentage = min(
                        (played / duration) * 100,
                        100
                    )

                filled = int(
                    round(
                        bar_length
                        * percentage
                        / 100
                    )
                )

                timer_bar = (
                    "—" * filled
                    + "●"
                    + "—" * (
                        bar_length - filled
                    )
                )

                # --------------------------------------------------
                # Direct-stream preparation
                # --------------------------------------------------
                # Do NOT download next song.
                # Just keep file_path empty so playback
                # can generate a fresh direct URL.
                # --------------------------------------------------

                if remaining <= 30:

                    next_media = queue.get_next(
                        chat_id,
                        check=True
                    )

                    if next_media:

                        if getattr(
                            next_media,
                            "file_path",
                            None
                        ):

                            next_media.file_path = None

                        asyncio.create_task(
                            _preload_next(
                                chat_id,
                                next_media
                            )
                        )

                # --------------------------------------------------
                # Timer text
                # --------------------------------------------------

                if remaining < 10:

                    remove = True

                    timer_text = timer_bar

                else:

                    remove = False

                    if duration >= 3600:

                        played_time = time.strftime(
                            "%H:%M:%S",
                            time.gmtime(
                                played
                            )
                        )

                        total_time = time.strftime(
                            "%H:%M:%S",
                            time.gmtime(
                                duration
                            )
                        )

                    else:

                        played_time = time.strftime(
                            "%M:%S",
                            time.gmtime(
                                played
                            )
                        )

                        total_time = time.strftime(
                            "%M:%S",
                            time.gmtime(
                                duration
                            )
                        )

                    timer_text = (
                        f"{played_time} "
                        f"{timer_bar} "
                        f"{total_time}"
                    )

                # --------------------------------------------------
                # Update Telegram controls
                # --------------------------------------------------

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id,
                        timer=timer_text,
                        remove=remove
                    ),
                )

            except Exception as e:

                error_str = str(e)

                # Expected Telegram errors
                ignored_errors = [
                    "MESSAGE_NOT_MODIFIED",
                    "MESSAGE_ID_INVALID",
                    "MESSAGE_DELETE",
                    "MESSAGE_AUTHOR_REQUIRED",
                    "CHAT_ADMIN_REQUIRED",
                    "CHANNEL_PRIVATE",
                    "haven't joined this channel",
                ]

                if not any(
                    err in error_str
                    for err in ignored_errors
                ):

                    logger.debug(
                        f"update_timer error "
                        f"for chat {chat_id}: {e}"
                    )

                # Stop tracking private/invalid chats
                if "CHANNEL_PRIVATE" in error_str:
                    break

                await asyncio.sleep(1)

    # ----------------------------------------------------------
    # Monitor active chats
    # ----------------------------------------------------------

    while True:

        await asyncio.sleep(2)

        for chat_id in list(
            db.active_calls
        ):

            if chat_id not in chat_tasks:

                task = asyncio.create_task(
                    update_chat_timer(
                        chat_id
                    )
                )

                chat_tasks[chat_id] = task

        # Clean finished tasks
        finished_chats = [
            chat_id
            for chat_id, task
            in chat_tasks.items()
            if (
                task.done()
                or chat_id not in db.active_calls
            )
        ]

        for chat_id in finished_chats:

            chat_tasks.pop(
                chat_id,
                None
            )


async def vc_watcher(
    sleep=15
):
    """
    Leave voice chat after 5 minutes
    if no users are listening.
    """

    alone_times = {}

    LEAVE_TIMEOUT = 300

    while True:

        await asyncio.sleep(
            sleep
        )

        current_time = time.time()

        for chat_id in list(
            db.active_calls
        ):

            try:

                # Check auto-leave setting
                if not await db.get_autoleave(
                    chat_id
                ):

                    alone_times.pop(
                        chat_id,
                        None
                    )

                    continue

                client = await db.get_assistant(
                    chat_id
                )

                # Check assistant participation
                try:

                    participants = (
                        await client.get_participants(
                            chat_id
                        )
                    )

                except Exception:

                    alone_times.pop(
                        chat_id,
                        None
                    )

                    continue

                # Only assistant is in VC
                if len(participants) < 2:

                    if chat_id not in alone_times:

                        alone_times[chat_id] = (
                            current_time
                        )

                    else:

                        alone_duration = (
                            current_time
                            - alone_times[chat_id]
                        )

                        if (
                            alone_duration
                            >= LEAVE_TIMEOUT
                        ):

                            _lang = await lang.get_lang(
                                chat_id
                            )

                            try:

                                current_media = (
                                    queue.get_current(
                                        chat_id
                                    )
                                )

                                if (
                                    current_media
                                    and current_media.message_id
                                ):

                                    sent = (
                                        await app.edit_message_reply_markup(
                                            chat_id=chat_id,
                                            message_id=current_media.message_id,
                                            reply_markup=buttons.controls(
                                                chat_id=chat_id,
                                                status=_lang["stopped"],
                                                remove=True
                                            ),
                                        )
                                    )

                                    await sent.reply_text(
                                        _lang["auto_left"]
                                    )

                            except Exception:
                                pass

                            # Stop playback
                            await tune.stop(
                                chat_id
                            )

                            # Leave voice chat
                            try:

                                await client.leave_call(
                                    chat_id,
                                    close=False
                                )

                            except Exception as e:

                                error_msg = str(
                                    e
                                ).lower()

                                ignored = [
                                    "not in a call",
                                    "not in the group call",
                                    "no active group call",
                                    "call was already stopped",
                                    "call already disconnected",
                                ]

                                if not any(
                                    item in error_msg
                                    for item in ignored
                                ):

                                    logger.debug(
                                        f"Error leaving call "
                                        f"for {chat_id}: {e}"
                                    )

                            alone_times.pop(
                                chat_id,
                                None
                            )

                else:

                    # Users joined
                    alone_times.pop(
                        chat_id,
                        None
                    )

            except Exception as e:

                logger.debug(
                    f"vc_watcher error "
                    f"for chat {chat_id}: {e}"
                )

                alone_times.pop(
                    chat_id,
                    None
                )

                continue


# ==========================================================
# Background tasks
# ==========================================================

tasks.append(
    asyncio.create_task(
        vc_watcher()
    )
)

if config.AUTO_LEAVE:

    tasks.append(
        asyncio.create_task(
            auto_leave()
        )
    )

tasks.append(
    asyncio.create_task(
        track_time()
    )
)

tasks.append(
    asyncio.create_task(
        update_timer()
    )
)