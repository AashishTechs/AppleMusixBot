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
#
# ==========================================================

from pyrogram import filters, types

from Elevenyts import app


@app.on_message(filters.command(["id", "emojiid", "stickerid"]) & ~app.bl_users)
async def get_id(_, message: types.Message):
    """Return IDs for replied Telegram media/custom emojis."""

    reply = message.reply_to_message

    if not reply:
        await message.reply_text(
            "<b>Reply to a custom emoji, sticker, photo, video, "
            "animation, document or audio with /id.</b>"
        )
        return

    # Custom emoji inside message text/caption.
    entities = list(reply.entities or []) + list(reply.caption_entities or [])
    for entity in entities:
        custom_emoji_id = getattr(entity, "custom_emoji_id", None)
        if custom_emoji_id:
            await message.reply_text(
                f"<b>Custom Emoji ID:</b> <code>{custom_emoji_id}</code>"
            )
            return

    # Sticker.
    if reply.sticker:
        await message.reply_text(
            f"<b>Sticker ID:</b> <code>{reply.sticker.file_id}</code>\n"
            f"<b>Unique ID:</b> <code>{reply.sticker.file_unique_id}</code>"
        )
        return

    # Other common Telegram media.
    if reply.photo:
        await message.reply_text(
            f"<b>Photo ID:</b> <code>{reply.photo.file_id}</code>"
        )
        return

    if reply.animation:
        await message.reply_text(
            f"<b>Animation ID:</b> <code>{reply.animation.file_id}</code>"
        )
        return

    if reply.video:
        await message.reply_text(
            f"<b>Video ID:</b> <code>{reply.video.file_id}</code>"
        )
        return

    if reply.document:
        await message.reply_text(
            f"<b>Document ID:</b> <code>{reply.document.file_id}</code>"
        )
        return

    if reply.audio:
        await message.reply_text(
            f"<b>Audio ID:</b> <code>{reply.audio.file_id}</code>"
        )
        return

    await message.reply_text(
        "<b>No supported Telegram ID found.</b>\n"
        "Reply directly to the custom emoji or media and use /id."
    )
