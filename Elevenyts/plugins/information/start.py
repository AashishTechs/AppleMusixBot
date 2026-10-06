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

_START_IN_PROGRESS = set()



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
    """Handle /start and send the welcome panel without duplicate requests."""
    chat_id = message.chat.id

    # If the user sends /start again while the first one is still uploading,
    # ignore the duplicate instead of creating a second welcome panel.
    if chat_id in _START_IN_PROGRESS:
        return
    _START_IN_PROGRESS.add(chat_id)

    try:
        if not message.from_user:
            return

        if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
            await message.reply_text(message.lang["bl_user_notify"])
            return

        if len(message.command) > 1 and message.command[1] == "help":
            await _help(_, message)
            return

        private = message.chat.type == enums.ChatType.PRIVATE
        text_value = message.lang["start"].format(message.from_user.mention)
        key = buttons.start_key(message.lang, private)

        try:
            await message.reply_photo(
                photo=config.START_IMG,
                caption=text_value,
                reply_markup=key,
            )
        except errors.ChatSendPhotosForbidden:
            await message.reply_text(
                text=text_value,
                reply_markup=key,
            )

        # Do not wait for Telegram to delete /start.  The welcome panel
        # is already visible, so deletion can happen in the background and
        # does not add another network round-trip to the user's response time.
        asyncio.create_task(message.delete())

        # Keep database/logging work out of the response path.
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
    finally:
        _START_IN_PROGRESS.discard(chat_id)


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
