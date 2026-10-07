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
    is_channel = m.command[0].lower() in ["cskip", "cnext"]
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

    # Run the switch synchronously so playback errors are not hidden
    # inside a fire-and-forget task. play_next() already has its own
    # per-chat lock, so duplicate skip requests remain protected.
    try:
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
