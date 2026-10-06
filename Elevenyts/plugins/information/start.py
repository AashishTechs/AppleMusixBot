# ==========================================================
# Copyright (c) 2026 Apple Music <<3
# All Rights Reserved.
#
# Project      : Apple Music Telegram Music Bot
# Powered By   : Apple Music <<3
# Type         : API Based Telegram Music Bot
#
# Bot          : @AppleMusix_bot
# Support      : https://t.me/deep_emotions_01
# GitHub       : https://github.com/AashishTechs/AppleMusixBot
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================

import asyncio

from pyrogram import enums, errors, filters, types

from Elevenyts import app, config, db, lang
from Elevenyts.helpers import buttons, utils


@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    """Handle /help command in private chats - shows help menu with image."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    try:
        await m.reply_photo(
            photo=config.START_IMG,  # Use same image as start command
            caption=m.lang["help"],
            reply_markup=buttons.help_markup(m.lang),
        )
    except Exception:
        # Fallback to text if photo fails
        await m.reply_text(
            text=m.lang["help"],
            reply_markup=buttons.help_markup(m.lang),
        )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    """
    Handle /start command - welcome message for users.

    - In private chat: Shows welcome message with inline buttons
    - In group chat: Shows short welcome message
    - Adds new users to database
    - Sends log to logger group for new users
    """
    # Keep /start visible while the welcome panel is being prepared.
    # This makes the command feel like a normal working Telegram command
    # instead of disappearing before the response suddenly appears.
    try:
        await app.send_chat_action(
            message.chat.id,
            enums.ChatAction.UPLOAD_PHOTO,
        )
        await asyncio.sleep(0.4)
    except Exception:
        pass
    
    # Skip if message from channel or anonymous admin
    if not message.from_user:
        return

    # Check if user is blacklisted
    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    # If /start help, show help menu
    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    # Determine if chat is private or group
    private = message.chat.type == enums.ChatType.PRIVATE

    # Use the Apple Musix welcome panel for both private and group /start.
    # The locale currently provides the welcome text under the "start" key.
    _text = message.lang["start"].format(message.from_user.mention)

    key = buttons.start_key(message.lang, private)
    try:
        await message.reply_photo(
            photo=config.START_IMG,
            caption=_text,
            reply_markup=key,
        )
    except errors.ChatSendPhotosForbidden:
        # If photos are not allowed, send text only
        await message.reply_text(
            text=_text,
            reply_markup=key,
        )

    # Remove /start only after the welcome panel is already on screen.
    # The user therefore sees a clear command -> response flow.
    try:
        await message.delete()
    except Exception:
        pass

    # Do not delay the welcome panel for database/logging work.
    # These operations are intentionally scheduled in the background.
    if private:
        async def _register_user():
            try:
                if await db.is_user(message.from_user.id):
                    return
                await utils.send_log(message)
                await db.add_user(message.from_user.id)
            except Exception:
                pass

        asyncio.create_task(_register_user())


@app.on_message(filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    """
    Handle /playmode or /settings command - show group settings.

    Displays:
    - Play mode (everyone or admin only)
    - Current language
    - Options to change settings
    """
    # Auto-delete command message
    try:
        await message.delete()
    except Exception:
        pass
    
    admin_only = await db.get_play_mode(message.chat.id)  # Get play mode setting
    _language = "en"
    await utils.safe_text(
        message,
        message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, _language, message.chat.id
        ),
    )


@app.on_message(filters.new_chat_members, group=7)
@lang.language()
async def _new_member(_, message: types.Message):
    """
    Handle new member events - detect when bot is added to groups.

    - Leaves non-supergroup chats
    - Adds new groups to database
    """
    # Only work in supergroups (not basic groups)
    if message.chat.type != enums.ChatType.SUPERGROUP:
        return await message.chat.leave()

    # Check each new member
    for member in message.new_chat_members:
        if member.id == app.id:  # Bot itself was added
            if await db.is_chat(message.chat.id):
                return  # Chat already in database
            # Add chat to database (log is sent from new_chat.py with photo)
            await db.add_chat(message.chat.id)
