# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================

from pyrogram import filters, types

from Elevenyts import tune, app, db, lang, queue
from Elevenyts.helpers import can_manage_vc
import logging


@app.on_message(filters.command(["seek", "seekback", "cseek", "cseekback"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _seek(_, m: types.Message):
    logging.getLogger(__name__).info("🎛️ /seek handler triggered in chat=%s user=%s command=%s", m.chat.id, m.from_user.id if m.from_user else None, m.command)
    try:
        await m.delete()
    except Exception:
        pass
    
    command_name = m.command[0].lower().split("@", 1)[0]

    if len(m.command) < 2:
        return await m.reply_text(f"Usage: {command_name} <seconds>")

    raw_time = m.command[1].strip().lower()

    # Accept seconds as well as MM:SS / HH:MM:SS.
    try:
        if ":" in raw_time:
            parts = [int(part) for part in raw_time.split(":")]
            if len(parts) == 2:
                to_seek = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                to_seek = parts[0] * 3600 + parts[1] * 60 + parts[2]
            else:
                raise ValueError
        else:
            to_seek = int(raw_time)
    except ValueError:
        return await m.reply_text(
            f"Usage: {command_name} <seconds|MM:SS>"
        )

    if to_seek < 10:
        return await m.reply_text("Minimum seek is 10 seconds")

    # Check for channel play mode
    is_channel = command_name in {"cseek", "cseekback"}
    chat_id = m.chat.id
    
    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await m.reply_text("Channel play is not enabled. Use /channelplay to enable.")
        chat_id = channel_id

    if not await db.get_call(chat_id):
        return await m.reply_text("Nothing is playing.")

    if not await db.playing(chat_id):
        return await m.reply_text("Playback is paused. Resume first.")

    media = queue.get_current(chat_id)
    if not media.duration_sec:
        return await m.reply_text("Cannot seek in live streams.")

    sent = await m.reply_text("Seeking...")
    
    current_time = await tune.current_time(chat_id)
    command_name = m.command[0].lower().split("@", 1)[0]

    if command_name in {"seekback", "cseekback"}:
        stype = "backward"
        start_from = max(1, current_time - to_seek)
    else:
        stype = "forward"
        start_from = min(current_time + to_seek, max(1, media.duration_sec - 5))

    logging.getLogger(__name__).info(
        "🎯 Seek request chat=%s command=%s current=%s offset=%s target=%s",
        chat_id, command_name, current_time, to_seek, start_from,
    )

    success = await tune.seek_stream(chat_id, int(start_from))
    
    if success:
        await sent.edit_text(f"Seeked {stype} to {start_from} seconds by {m.from_user.mention}")
    else:
        await sent.edit_text("Failed to seek!")
