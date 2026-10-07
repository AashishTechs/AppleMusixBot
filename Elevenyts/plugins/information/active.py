# ==========================================================
# Copyright (c) 2026 Apple Music <<3
# All Rights Reserved.
#
# Project      : Apple Music Telegram Music Bot
# Powered By   : Apple Music <<3
# Bot          : @AppleMusix_bot
# ==========================================================

from pyrogram import filters, types

from Elevenyts import app, db, queue


def _command_name(message: types.Message) -> str:
    return message.command[0].lower().split("@", 1)[0]


async def _chat_label(chat_id: int) -> str:
    try:
        chat = await app.get_chat(chat_id)
        title = chat.title or getattr(chat, "first_name", None) or str(chat_id)
        return f"<b>{title}</b> <code>{chat_id}</code>"
    except Exception:
        return f"<code>{chat_id}</code>"


async def _active_voice_text() -> str:
    lines = []
    for chat_id in list(db.active_calls):
        media = queue.get_current(chat_id)
        if not media:
            continue

        title = (getattr(media, "title", None) or "Unknown track").strip()
        label = await _chat_label(chat_id)
        lines.append(
            f"<b>{len(lines) + 1}.</b> {label}\n"
            f"   🎵 <b>Playing:</b> {title[:70]}"
        )

    if not lines:
        return "🎙 <b>ACTIVE VOICE CHATS</b>\n\nNo active voice music sessions."

    return (
        "🎙 <b>APPLE MUSIX • ACTIVE VOICE CHATS</b>\n\n"
        f"✦ <b>Active:</b> {len(lines)}\n\n"
        + "\n\n".join(lines)
    )


@app.on_message(
    filters.command(["ac", "activevc", "activevoice"])
    & app.sudo_filter
)
async def _activevoice(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    if _command_name(m) == "ac":
        return await m.reply_text(
            f"🎙 <b>ACTIVE VOICE CHATS</b>\n\n"
            f"✦ <b>Active:</b> {len(db.active_calls)}"
        )

    return await m.reply_text(await _active_voice_text())


@app.on_message(
    filters.command(["activevideo"])
    & app.sudo_filter
)
async def _activevideo(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    video_chats = await db.get_video_chats()

    if not video_chats:
        return await m.reply_text(
            "🎥 <b>APPLE MUSIX • ACTIVE VIDEO CHATS</b>\n\n"
            "No active Telegram video chats."
        )

    lines = []
    for chat_id in video_chats:
        lines.append(
            f"<b>{len(lines) + 1}.</b> "
            f"{await _chat_label(chat_id)}\n"
            "   🎥 <b>Video Chat:</b> Active"
        )

    return await m.reply_text(
        "🎥 <b>APPLE MUSIX • ACTIVE VIDEO CHATS</b>\n\n"
        f"✦ <b>Active:</b> {len(lines)}\n\n"
        + "\n\n".join(lines)
    )


@app.on_message(
    filters.command(["vclogger"])
    & app.sudo_filter
)
async def _vclogger(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    if len(m.command) < 2:
        enabled = await db.get_vc_logger()
        return await m.reply_text(
            "📋 <b>VC LOGGER</b>\n\n"
            f"✦ <b>Status:</b> {'Enabled' if enabled else 'Disabled'}\n\n"
            "<code>/vclogger enable</code>\n"
            "<code>/vclogger disable</code>"
        )

    action = m.command[1].lower()
    if action not in {"enable", "disable"}:
        return await m.reply_text(
            "⚠️ <b>INVALID OPTION</b>\n\n"
            "Use <code>/vclogger enable</code> or "
            "<code>/vclogger disable</code>."
        )

    enabled = action == "enable"
    await db.set_vc_logger(enabled)

    return await m.reply_text(
        "📋 <b>VC LOGGER</b>\n\n"
        f"✅ VC event logging <b>{'enabled' if enabled else 'disabled'}</b>."
    )


@app.on_message(
    filters.command(["autoend"])
    & app.sudo_filter
)
async def _autoend(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    if len(m.command) < 2:
        enabled = await db.get_autoleave(m.chat.id)
        return await m.reply_text(
            "⏹ <b>AUTO-END</b>\n\n"
            f"✦ <b>Status:</b> {'Enabled' if enabled else 'Disabled'}\n"
            "✦ Timeout: <b>5 minutes</b> without listeners\n\n"
            "<code>/autoend enable</code>\n"
            "<code>/autoend disable</code>"
        )

    action = m.command[1].lower()
    if action not in {"enable", "disable"}:
        return await m.reply_text(
            "⚠️ <b>INVALID OPTION</b>\n\n"
            "Use <code>/autoend enable</code> or "
            "<code>/autoend disable</code>."
        )

    enabled = action == "enable"
    await db.set_autoleave(m.chat.id, enabled)

    return await m.reply_text(
        "⏹ <b>AUTO-END</b>\n\n"
        f"✅ Automatic listener-based ending "
        f"<b>{'enabled' if enabled else 'disabled'}</b>."
    )
