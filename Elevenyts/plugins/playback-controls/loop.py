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

from pyrogram import filters, types

from Elevenyts import app, db, lang
from Elevenyts.helpers import can_manage_vc


@app.on_message(filters.command(["loop", "cloop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _loop(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    is_channel = m.command[0].lower() == "cloop"
    chat_id = m.chat.id

    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await m.reply_text(
                "Channel play is not enabled. Use /channelplay to enable."
            )
        chat_id = channel_id

    if not await db.get_call(chat_id):
        return await m.reply_text("Nothing is playing.")

    # /loop [1-10]
    # The number means how many additional times the current track
    # should be replayed. /loop 0 disables looping.
    if len(m.command) > 1:
        try:
            repeats = int(m.command[1])
        except ValueError:
            return await m.reply_text(
                "Usage: /loop [1-10]\n"
                "Use /loop 0 to disable looping."
            )

        if repeats < 0 or repeats > 10:
            return await m.reply_text(
                "Loop count must be between 0 and 10."
            )
    else:
        repeats = 1

    await db.set_loop(chat_id, repeats)

    if repeats == 0:
        text = "🔁 Loop disabled."
    elif repeats == 1:
        text = "🔁 Current track will repeat 1 more time."
    else:
        text = f"🔁 Current track will repeat {repeats} more times."

    await m.reply_text(text)
