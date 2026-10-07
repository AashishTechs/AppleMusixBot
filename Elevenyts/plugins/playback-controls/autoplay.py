# ==========================================================
# Copyright (c) 2026 Apple Music <<3
# All Rights Reserved.
#
# Project      : Apple Music Telegram Music Bot
# Bot          : @AppleMusix_bot
# GitHub       : https://github.com/AashishTechs/AppleMusixBot
# ==========================================================

from pyrogram import filters, types

from Elevenyts import app, db, lang
from Elevenyts.helpers import can_manage_vc, buttons


@app.on_message(
    filters.command(["autoplay"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@can_manage_vc
async def _autoplay(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    enabled = await db.get_autoplay(m.chat.id)

    text = (
        "<blockquote>🎵 <b>APPLE MUSIX • AUTO PLAY</b></blockquote>\n\n"
        "Auto Play automatically plays related songs when the queue becomes empty.\n\n"
        f"<b>Status:</b> {'✅ Enabled' if enabled else '❌ Disabled'}\n\n"
        "• Queued songs are played first.\n"
        "• When the queue ends, related songs are picked from YouTube Mix.\n"
        "• Auto Play continues until disabled or the stream is stopped."
    )

    await app.send_message(
        chat_id=m.chat.id,
        text=text,
        reply_markup=buttons.autoplay_markup(
            m.chat.id,
            enabled,
        ),
    )
