# ==========================================================
# Copyright (c) 2026 Apple Music <<3
# All Rights Reserved.
#
# Project      : Apple Music Telegram Music Bot
# Bot          : @AppleMusix_bot
# ==========================================================
from pyrogram import filters, types

from Elevenyts import app


@app.on_message(filters.command(["id", "emojiid", "stickerid"]) & ~app.bl_users)
async def _id(_, m: types.Message):
    target = m.reply_to_message

    if not target:
        await m.reply_text(
            "<blockquote><b>🆔 ID TOOL</b></blockquote>\n\n"
            "Reply to a <b>custom emoji</b> or <b>sticker</b> with <code>/id</code>."
        )
        return

    results = []

    # Custom emoji embedded in text/caption.
    for entity in (target.entities or []) + (target.caption_entities or []):
        if entity.type == "custom_emoji" and entity.custom_emoji_id:
            results.append(
                f"<b>Custom Emoji ID:</b> <code>{entity.custom_emoji_id}</code>"
            )

    # Sticker file identifiers.
    if target.sticker:
        results.extend(
            [
                f"<b>Sticker File ID:</b> <code>{target.sticker.file_id}</code>",
                f"<b>Sticker Unique ID:</b> <code>{target.sticker.file_unique_id}</code>",
            ]
        )

    if not results:
        await m.reply_text(
            "<blockquote><b>❌ ID NOT FOUND</b></blockquote>\n\n"
            "The replied message does not contain a custom emoji or sticker."
        )
        return

    await m.reply_text(
        "<blockquote><b>🆔 TELEGRAM ID</b></blockquote>\n\n"
        + "\n".join(results)
    )
