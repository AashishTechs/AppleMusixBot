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
import logging
from pyrogram import filters, types
from pyrogram.errors import ChatSendPlainForbidden, ChatWriteForbidden

from Elevenyts import tune, app, db, lang
from Elevenyts.helpers import can_manage_vc

logger = logging.getLogger(__name__)


@app.on_message(
    filters.command(["skip", "next", "cskip", "cnext"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@can_manage_vc
async def _skip(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    # Check for channel play mode.
    command_name = m.command[0].lower().split("@", 1)[0]\n    is_channel = command_name in ["cskip", "cnext"]
    chat_id = m.chat.id

    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)

        if channel_id is None:
            try:
                return await m.reply_text(
                    "Channel play is not enabled. Use /channelplay to enable."
                )
            except (ChatSendPlainForbidden, ChatWriteForbidden):
                return

        chat_id = channel_id

    if not await db.get_call(chat_id):
        try:
            return await m.reply_text("Nothing is playing.")
        except (ChatSendPlainForbidden, ChatWriteForbidden):
            return

    # Run the switch synchronously. If another play_next() is already
    # transitioning the queue, wait briefly and verify that the current
    # track actually changed instead of silently treating the skip as done.
    current = None
    try:
        from Elevenyts import queue
        current = queue.get_current(chat_id)
    except Exception:
        pass

    current_id = getattr(current, "id", None)

    try:
        await tune.play_next(chat_id, force_skip=True)

        # play_next() can return immediately when its per-chat lock is busy.
        # In that case, give the active transition a moment to finish and
        # retry once if the current track is still unchanged.
        await asyncio.sleep(0.5)

        try:
            current_after = queue.get_current(chat_id)
        except Exception:
            current_after = None

        after_id = getattr(current_after, "id", None)

        if current_id and after_id == current_id:
            await asyncio.sleep(1.0)

            try:
                current_after = queue.get_current(chat_id)
            except Exception:
                current_after = None

            after_id = getattr(current_after, "id", None)

            if after_id == current_id:
                logger.info(
                    "Retrying play_next for %s because /skip did not "
                    "advance the current track",
                    chat_id,
                )
                await tune.play_next(chat_id)

    except Exception as e:
        logger.error(
            "Skip/play_next failed for %s: %s",
            chat_id,
            e,
            exc_info=True,
        )
        try:
            return await m.reply_text(
                "❌ <b>Could not skip the current track.</b> Please try again."
            )
        except (ChatSendPlainForbidden, ChatWriteForbidden):
            return

    try:
        sent_msg = await m.reply_text(
            f"⏭️ Skipped by {m.from_user.mention}"
        )
    except (ChatSendPlainForbidden, ChatWriteForbidden):
        logger.warning("Cannot send plain text in media-only chat")
        return

    # Keep the confirmation short-lived.
    await asyncio.sleep(3)

    try:
        await sent_msg.delete()
    except Exception:
        pass
