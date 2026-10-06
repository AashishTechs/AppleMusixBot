# ==========================================================
# Copyright (c) 2026 Apple Music <<3
# All Rights Reserved.
#
# Project      : Apple Music Telegram Music Bot
# Powered By   : Apple Music <<3
# Type         : API Based Telegram Music Bot
#
# Bot          : @AppleMusix_bot
# GitHub       : https://github.com/AashishTechs/AppleMusixBot
# ==========================================================

from pyrogram import filters, types

from Elevenyts import app, config, db, lang, queue
from Elevenyts.helpers import Track, buttons, thumb


@app.on_message(
    filters.command(["queue", "playing", "cqueue", "cplaying"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
async def _queue_func(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    is_channel = m.command[0].lower() in ["cqueue", "cplaying"]
    chat_id = m.chat.id

    if is_channel:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await app.send_message(
                m.chat.id,
                "<blockquote>❌ Channel play is not enabled.</blockquote>",
            )
        chat_id = channel_id

    if not await db.get_call(chat_id):
        return await app.send_message(
            m.chat.id,
            "<blockquote>🎧 <b>Nothing is playing.</b></blockquote>",
        )

    # Work on a copy. The old code popped the current track from the real
    # queue, which could corrupt the active queue.
    items = list(queue.get_queue(chat_id))

    if not items:
        return await app.send_message(
            m.chat.id,
            "<blockquote>🎧 <b>Nothing is queued.</b></blockquote>",
        )

    current = items[0]

    try:
        media = (
            await thumb.generate(current)
            if isinstance(current, Track)
            else config.DEFAULT_THUMB
        )
    except Exception:
        media = config.DEFAULT_THUMB

    playing = await db.playing(chat_id)
    status = "▶ PLAYING" if playing else "Ⅱ PAUSED"

    caption = (
        "<blockquote>🎧 <b>APPLE MUSIX ‹‹𝟹</b></blockquote>\n"
        f"<blockquote>🎵 <b>NOW PLAYING :</b> "
        f"<a href="{current.url}">{current.title}</a></blockquote>\n"
        f"<blockquote>⏱️ <b>LENGTH :</b> {current.duration} MIN</blockquote>\n"
        f"<blockquote>👤 <b>USER :</b> {current.user}</blockquote>"
    )

    upcoming = items[1:16]

    if upcoming:
        caption += (
            f"\n<blockquote>🔵 <b>QUEUED | {len(items) - 1}</b></blockquote>"
        )
        for index, media_item in enumerate(upcoming, start=1):
            caption += (
                f"\n<blockquote><b>{index}.</b> "
                f"{media_item.title} • {media_item.duration}</blockquote>"
            )

    markup = buttons.queue_markup(
        chat_id,
        status,
        playing,
    )

    try:
        await app.send_photo(
            chat_id=m.chat.id,
            photo=media,
            caption=caption,
            reply_markup=markup,
        )
    except Exception:
        # If thumbnail generation/file upload fails, keep the command usable.
        await app.send_message(
            chat_id=m.chat.id,
            text=caption,
            reply_markup=markup,
        )
