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

import re
import asyncio
from functools import wraps

from pyrogram import filters, types
from pyrogram.errors import FloodWait, QueryIdInvalid

from Elevenyts import tune, app, config, db, lang, logger, queue, tg, yt
from Elevenyts.helpers import admin_check, buttons, can_manage_vc


def safe_callback(func):
    """Decorator to handle exceptions in callback handlers."""

    @wraps(func)
    async def wrapper(client, query: types.CallbackQuery):
        try:
            return await func(client, query)

        except QueryIdInvalid:
            return

        except Exception as e:
            logger.error(
                f"Error in callback {func.__name__}: {e}",
                exc_info=True
            )

            try:
                await query.answer(
                    "❌ An error occurred. Please try again.",
                    show_alert=True
                )
            except Exception:
                pass

    return wrapper


async def get_direct_stream(media):
    """
    Get a fresh direct streaming URL.

    IMPORTANT:
    Direct YouTube URLs expire, therefore URL ko
    playback ke time fresh generate kiya jata hai.
    """

    try:
        media.file_path = None

        stream_url = await yt.get_stream_url(
            media.id,
            is_live=getattr(media, "is_live", False),
            video=getattr(media, "video", False),
        )

        if stream_url:
            media.file_path = stream_url
            return stream_url

        return None

    except Exception as e:
        logger.error(
            f"Failed to get direct stream for "
            f"{getattr(media, 'id', 'unknown')}: {e}",
            exc_info=True
        )
        return None


@app.on_callback_query(filters.regex("^start$") & ~app.bl_users)
@lang.language()
@safe_callback
async def _start_callback(_, query: types.CallbackQuery):
    """Handle start button callback - return to start message."""

    await query.answer()

    _text = query.lang["start"].format(query.from_user.mention)

    key = buttons.start_key(
        query.lang,
        True
    )

    try:
        await query.edit_message_caption(
            caption=_text,
            reply_markup=key,
        )

    except Exception:
        try:
            await query.edit_message_text(
                text=_text,
                reply_markup=key,
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex("^language$") & ~app.bl_users)
@lang.language()
@safe_callback
async def _language(_, query: types.CallbackQuery):
    """Show the currently available language."""
    await query.answer("🌐 English is currently enabled.", show_alert=True)


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
@safe_callback
async def cancel_dl(_, query: types.CallbackQuery):

    await query.answer()

    await tg.cancel(query)


@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@safe_callback
async def _controls(_, query: types.CallbackQuery):

    args = query.data.split()

    action = args[1]
    chat_id = int(args[2])

    qaction = len(args) == 4
    user = query.from_user.mention

    # ------------------------------------------------------
    # CLOSE
    # ------------------------------------------------------

    if action == "close":

        await query.answer()

        try:
            await query.message.delete()
        except Exception:
            pass

        return

    # ------------------------------------------------------
    # PERMISSION CHECK
    # ------------------------------------------------------

    user_id = query.from_user.id

    has_permission = False

    if user_id in app.sudoers:
        has_permission = True

    elif await db.is_auth(chat_id, user_id):
        has_permission = True

    else:
        admins = await db.get_admins(chat_id)

        if user_id in admins:
            has_permission = True

    if not has_permission:
        return await query.answer(
            "⚠️ You don't have permission to use this.",
            show_alert=True
        )

    # ------------------------------------------------------
    # CALL CHECK
    # ------------------------------------------------------

    if not await db.get_call(chat_id):
        return await query.answer(
            query.lang["not_playing"],
            show_alert=True
        )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    if action == "status":
        return await query.answer()

    # ------------------------------------------------------
    # SEEK
    # ------------------------------------------------------

    if action.startswith("seek_"):

        return await handle_seek(
            query,
            chat_id,
            action,
            user
        )

    # ------------------------------------------------------
    # LOOP
    # ------------------------------------------------------

    if action == "loop":

        return await handle_loop(
            query,
            chat_id,
            user
        )

    # ------------------------------------------------------
    # SHUFFLE
    # ------------------------------------------------------

    if action == "shuffle":

        return await handle_shuffle(
            query,
            chat_id,
            user
        )

    await query.answer(
        query.lang["processing"],
        show_alert=True
    )

    # ------------------------------------------------------
    # PAUSE
    # ------------------------------------------------------

    if action == "pause":

        if not await db.playing(chat_id):

            return await query.answer(
                query.lang["play_already_paused"],
                show_alert=True
            )

        if not await tune.pause(chat_id):

            return await query.answer(
                query.lang["not_playing"],
                show_alert=True
            )

        if qaction:

            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(
                    chat_id,
                    query.lang["paused"],
                    False
                )
            )

        status = query.lang["paused"]

        reply = query.lang["play_paused"].format(user)

    # ------------------------------------------------------
    # RESUME
    # ------------------------------------------------------

    elif action == "resume":

        status = query.lang["playing"]

        if await db.playing(chat_id):

            return await query.answer(
                query.lang["play_not_paused"],
                show_alert=True
            )

        if not await tune.resume(chat_id):

            return await query.answer(
                query.lang["not_playing"],
                show_alert=True
            )

        if qaction:

            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(
                    chat_id,
                    query.lang["playing"],
                    True
                )
            )

        reply = query.lang["play_resumed"].format(user)

    # ------------------------------------------------------
    # SKIP
    # ------------------------------------------------------

    elif action == "skip":

        await tune.play_next(chat_id)

        status = query.lang["skipped"]

        reply = query.lang["play_skipped"].format(user)

    # ------------------------------------------------------
    # FORCE PLAY
    # ------------------------------------------------------

    elif action == "force":

        pos, media = queue.check_item(
            chat_id,
            args[3]
        )

        if not media or pos == -1:

            return await query.edit_message_text(
                query.lang["play_expired"]
            )

        current = queue.get_current(chat_id)

        m_id = (
            current.message_id
            if current
            else None
        )

        queue.force_add(
            chat_id,
            media,
            remove=pos
        )

        try:

            await app.delete_messages(
                chat_id=chat_id,
                message_ids=[
                    m_id,
                    media.message_id
                ],
                revoke=True
            )

            media.message_id = None

        except Exception:
            pass

        msg = await app.send_message(
            chat_id=chat_id,
            text=query.lang["play_next"]
        )

        # --------------------------------------------------
        # DIRECT STREAM
        # --------------------------------------------------
        # OLD:
        # media.file_path = await yt.download(...)
        #
        # NEW:
        # Fresh direct stream URL.
        # --------------------------------------------------

        stream_url = await get_direct_stream(media)

        if not stream_url:

            try:
                await msg.edit_text(
                    "❌ Unable to get direct stream for this track."
                )
            except Exception:
                pass

            return

        media.message_id = msg.id

        return await tune.play_media(
            chat_id,
            msg,
            media
        )

    # ------------------------------------------------------
    # REPLAY
    # ------------------------------------------------------

    elif action == "replay":

        media = queue.get_current(chat_id)

        media.user = user

        await tune.replay(chat_id)

        status = query.lang["replayed"]

        reply = query.lang["play_replayed"].format(user)

    # ------------------------------------------------------
    # STOP
    # ------------------------------------------------------

    elif action == "stop":

        await tune.stop(chat_id)

        status = query.lang["stopped"]

        reply = query.lang["play_stopped"].format(user)

    # ------------------------------------------------------
    # MESSAGE UPDATE
    # ------------------------------------------------------

    try:

        if action in ["skip", "replay", "stop"]:

            sent_msg = None

            try:

                sent_msg = await query.message.reply_text(
                    reply,
                    quote=False
                )

            except FloodWait as e:

                await asyncio.sleep(e.value)

                try:

                    sent_msg = await query.message.reply_text(
                        reply,
                        quote=False
                    )

                except Exception:
                    pass

            except Exception:
                pass

            try:
                await query.message.delete()
            except Exception:
                pass

            # Auto-delete reply after 5 seconds
            if sent_msg:

                await asyncio.sleep(5)

                try:
                    await sent_msg.delete()
                except Exception:
                    pass

            return

        mtext = re.sub(
            r"\n\n<blockquote>.*?</blockquote>",
            "",
            query.message.caption.html
            or query.message.text.html,
            flags=re.DOTALL,
        )

        keyboard = buttons.controls(
            chat_id,
            status=status if action != "resume" else None
        )

        await query.edit_message_text(
            f"{mtext}\n\n<blockquote>{reply}</blockquote>",
            reply_markup=keyboard
        )

    except FloodWait as e:

        await asyncio.sleep(e.value)

        try:

            await query.edit_message_text(
                f"{mtext}\n\n<blockquote>{reply}</blockquote>",
                reply_markup=keyboard
            )

        except Exception:
            pass

    except Exception:
        pass


async def handle_seek(
    query: types.CallbackQuery,
    chat_id: int,
    action: str,
    user: str
):
    """Handle seek forward/backward actions."""

    media = queue.get_current(chat_id)

    if not media or media.is_live:

        return await query.answer(
            "⚠️ Cannot seek in live streams!",
            show_alert=True
        )

    if not media.duration_sec or media.duration_sec == 0:

        return await query.answer(
            "⚠️ Cannot seek in this track!",
            show_alert=True
        )

    # Determine seek amount
    if action == "seek_back_10":

        seconds = -10
        label = "« 10s"

    elif action == "seek_back_30":

        seconds = -30
        label = "« 30s"

    elif action == "seek_forward_10":

        seconds = 10
        label = "10s »"

    elif action == "seek_forward_30":

        seconds = 30
        label = "30s »"

    else:

        return await query.answer(
            "⚠️ Invalid seek action!",
            show_alert=True
        )

    current_time = getattr(
        media,
        "time",
        0
    )

    new_time = max(
        0,
        min(
            current_time + seconds,
            media.duration_sec - 5
        )
    )

    if new_time == 0 and seconds < 0:

        return await query.answer(
            "⏮️ Already at the beginning!",
            show_alert=True
        )

    if (
        new_time >= media.duration_sec - 5
        and seconds > 0
    ):

        return await query.answer(
            "⏭️ Too close to the end!",
            show_alert=True
        )

    success = await tune.seek_stream(
        chat_id,
        int(new_time)
    )

    if success:

        import time as time_module

        if media.duration_sec >= 3600:

            time_str = time_module.strftime(
                "%H:%M:%S",
                time_module.gmtime(new_time)
            )

        else:

            time_str = time_module.strftime(
                "%M:%S",
                time_module.gmtime(new_time)
            )

        await query.answer(
            f"✅ Seeked to {time_str}",
            show_alert=True
        )

        try:

            sent_msg = await query.message.reply_text(
                f"✅ Seeked to {time_str}\n\n"
                f"<blockquote>By {user}</blockquote>",
                quote=False
            )

            await asyncio.sleep(5)

            try:
                await sent_msg.delete()
            except Exception:
                pass

        except FloodWait:
            pass

        except Exception:
            pass


async def handle_loop(
    query: types.CallbackQuery,
    chat_id: int,
    user: str
):
    """Handle loop mode toggling."""

    current_loop = await db.get_loop(chat_id)

    # 0 -> 1 -> 10 -> 0
    if current_loop == 0:

        new_loop = 1

        text = "🔂 Loop: Single Track"

        message = (
            "🔂 Loop mode set to "
            "<b>Single Track</b>"
        )

    elif current_loop == 1:

        new_loop = 10

        text = "🔁 Loop: Queue"

        message = (
            "🔁 Loop mode set to "
            "<b>Queue</b>"
        )

    else:

        new_loop = 0

        text = "➡️ Loop: Off"

        message = (
            "➡️ Loop mode "
            "<b>Disabled</b>"
        )

    await db.set_loop(
        chat_id,
        new_loop
    )

    await query.answer(
        text,
        show_alert=False
    )

    await query.message.reply_text(
        message,
        quote=False
    )


async def handle_shuffle(
    query: types.CallbackQuery,
    chat_id: int,
    user: str
):
    """Handle queue shuffling."""

    import random

    items = queue.get_queue(chat_id)

    if not items or len(items) <= 1:

        return await query.answer(
            "⚠️ Queue is empty or has only one track!",
            show_alert=True
        )

    current = (
        items[0]
        if items
        else None
    )

    remaining = (
        items[1:]
        if len(items) > 1
        else []
    )

    if not remaining:

        return await query.answer(
            "⚠️ No tracks to shuffle!",
            show_alert=True
        )

    random.shuffle(remaining)

    queue.clear(chat_id)

    if current:
        queue.add(
            chat_id,
            current
        )

    for item in remaining:

        queue.add(
            chat_id,
            item
        )

    await query.answer(
        "🔀 Queue shuffled!",
        show_alert=False
    )

    await query.message.reply_text(
        f"🔀 Queue <b>shuffled</b> "
        f"({len(remaining)} tracks)",
        quote=False
    )


@app.on_callback_query(
    filters.regex(r"^help")
    & ~app.bl_users
)
@lang.language()
async def _help(_, query: types.CallbackQuery):

    await query.answer()

    # Main help menu
    if query.data == "help":

        try:

            await query.edit_message_caption(
                caption=query.lang["help"],
                reply_markup=buttons.help_markup(
                    query.lang
                )
            )

        except Exception:

            try:

                await query.edit_message_text(
                    text=query.lang["help"],
                    reply_markup=buttons.help_markup(
                        query.lang
                    )
                )

            except Exception:
                pass

        return

    category = query.data.replace(
        "help_",
        ""
    )

    if category == "main":
        category = "main"

    if category == "main":

        try:

            await query.edit_message_caption(
                caption=query.lang["help"],
                reply_markup=buttons.help_markup(
                    query.lang
                )
            )

        except Exception:

            try:

                await query.edit_message_text(
                    text=query.lang["help"],
                    reply_markup=buttons.help_markup(
                        query.lang
                    )
                )

            except Exception:
                pass

        return

    help_texts = {
        "admins": (
            "<b>Admin Commands</b>\\n"
            "Commands available only to administrators.\\n\\n"
            "<b>Playback</b>\\n\\n"
            "<pre>"
            "Command                 Description\\n"
            "────────────────────────────────────────\\n"
            "/pause                  Pause the current playing stream.\\n"
            "/resume                 Resume the paused stream.\\n"
            "/skip                   Skip the current stream and play the\\n"
            "                        next track in queue.\\n"
            "/end or /stop           Stop playback and clear the queue.\\n"
            "/queue                  Show the current queue.\\n"
            "/shuffle                Shuffle the queued tracks.\\n"
            "/loop [1-10]            Repeat the current track for the\\n"
            "                        specified number of times.\\n"
            "/seek [time]            Seek to the given timestamp.\\n"
            "/seekback [time]        Seek backward to the given\\n"
            "                        timestamp.\\n"
            "</pre>\\n\\n"
            "<b>Notes</b>\\n"
            "• Prefix commands with c to use them in linked channels.\\n"
            "• Example: /cpause, /cskip, /cqueue"
        ),
        "auth": (
            "<b>Auth Module</b>\\n"
            "Manage authorized users who can control the bot without\\n"
            "being Telegram admins.\\n\\n"
            "<b>Commands</b>\\n\\n"
            "<pre>"
            "Command                 Description\\n"
            "────────────────────────────────────────\\n"
            "/auth [username]        Add a user to the bot's authorized\\n"
            "                        users list.\\n"
            "/unauth [username]      Remove a user from the authorized\\n"
            "                        users list.\\n"
            "/authusers              Show the list of authorized users in\\n"
            "                        the current group.\\n"
            "</pre>\\n\\n"
            "<b>Notes</b>\\n"
            "• Authorized users can use admin commands without\\n"
            "  having admin rights in the chat.\\n"
            "• This feature is available only for group administrators."
        ),
        "blchat": (
            "<b>Blacklist Module</b>\\n"
            "Manage blacklisted chats and blocked users.\\n\\n"
            "<b>Blacklist Chats</b>\\n\\n"
            "<pre>"
            "Command                  Description\\n"
            "────────────────────────────────────────\\n"
            "/blacklistchat [chat_id]  Blacklist a chat from using the\\n"
            "                         bot.\\n"
            "/whitelistchat [chat_id]  Remove a chat from the\\n"
            "                         blacklist.\\n"
            "/blacklistedchat          Show all blacklisted chats.\\n"
            "</pre>\\n\\n"
            "<b>Block Users</b>\\n\\n"
            "<pre>"
            "Command                  Description\\n"
            "────────────────────────────────────────\\n"
            "/block [username/reply]   Block a user from using the\\n"
            "                         bot.\\n"
            "/unblock [username/reply] Unblock a previously\\n"
            "                         blocked user.\\n"
            "/blockedusers             Show the list of blocked\\n"
            "                         users.\\n"
            "</pre>"
        ),
        "broadcast": (
            "<b>Broadcast Module</b>\\n"
            "Broadcast messages to chats and users. (Sudo users only)\\n\\n"
            "<b>Commands</b>\\n\\n"
            "<pre>"
            "Command                  Description\\n"
            "────────────────────────────────────────\\n"
            "/broadcast [message/reply]  Broadcast a message to\\n"
            "                           served chats.\\n"
            "</pre>\\n\\n"
            "<b>Broadcast Modes</b>\\n\\n"
            "<pre>"
            "Mode       Description\\n"
            "────────────────────────────────────────\\n"
            "--pin      Pin the broadcasted message in chats.\\n"
            "--pinloud  Pin the message and notify chat members.\\n"
            "--user     Broadcast only to users who have started the\\n"
            "           bot.\\n"
            "--nobot    Skip broadcasting to bots.\\n"
            "</pre>\\n\\n"
            "<b>Example</b>\\n"
            "<code>/broadcast --user --pin Testing Broadcast</code>"
        ),
        "ping": (
            "<b>Ping Module</b>\\n"
            "Check the bot's performance and statistics.\\n\\n"
            "<b>Commands</b>\\n\\n"
            "<pre>"
            "Command       Description\\n"
            "────────────────────────────────────────\\n"
            "/ping         Show the bot's ping and system statistics.\\n"
            "/stats        Display global statistics, top tracks, top users,\\n"
            "              top chats, and more."
            "</pre>"
        ),
        "play": (
            "<b>Play Module</b>\\n\\n"
            "Commands for playing music and videos.\\n\\n"
            "<b>Play Commands</b>\\n\\n"
            "• c stands for <b>Channel Play</b>.\\n"
            "• v stands for <b>Video Play</b>.\\n"
            "• force stands for <b>Force Play</b>.\\n\\n"
            "<pre>"
            "Command                 Description\\n"
            "────────────────────────────────────────\\n"
            "/play /vplay /cplay     Start streaming the requested\\n"
            "                        track in the voice/video chat.\\n"
            "/playforce /vplayforce  Stop the current stream and\\n"
            "/cplayforce             immediately play the requested\\n"
            "                        track.\\n"
            "/channelplay [chat      Connect a channel to a group for\\n"
            "username/id]            channel play.\\n"
            "/channelplay disable    Disable channel play for the group.\\n"
            "/pause /cpause          Pause the current stream.\\n"
            "/resume /cresume        Resume the paused stream.\\n"
            "/skip /next /cskip      Skip the current stream and play\\n"
            "                        the next track in queue.\\n"
            "/end /stop /cend        Stop playback and clear the queue.\\n"
            "/queue /cqueue          Show the current queue.\\n"
            "/shuffle /cshuffle      Shuffle the queued tracks.\\n"
            "/loop [1-10]            Repeat the current track for the\\n"
            "                        specified number of times.\\n"
            "/seek [time]            Seek to the given timestamp.\\n"
            "/seekback [time]        Seek backward to the given timestamp.\\n"
            "</pre>\\n\\n"
            "<b>Notes</b>\\n\\n"
            "• Prefix commands with <b>c</b> to use them in linked channels.\\n\\n"
            "• Example: /cpause, /cskip, /cqueue"
        ),
        "sudo": (
            "<b>Sudo Module</b>\\n"
            "Commands available only to sudo users.\\n\\n"
            "<b>Sudo Users</b>\\n\\n"
            "<pre>"
            "Command                  Description\\n"
            "────────────────────────────────────────\\n"
            "/addsudo [username/reply] Add a sudo user.\\n"
            "/delsudo [username/reply] Remove a sudo user.\\n"
            "/listsudo                 Show sudo users.\\n"
            "</pre>\\n\\n"
            "<b>Global Ban</b>\\n\\n"
            "<pre>"
            "Command                  Description\\n"
            "────────────────────────────────────────\\n"
            "/gban [username/reply]   Globally ban a user from all\\n"
            "                         served chats.\\n"
            "/ungban [username/reply] Remove a global ban.\\n"
            "/gbannedusers             Show globally banned users."
            "</pre>\\n\\n"
            "<b>Blacklist Chats</b>\\n\\n"
            "<pre>"
            "Command                  Description\\n"
            "────────────────────────────────────────\\n"
            "/blacklistchat [chat_id] Blacklist a chat from using the\\n"
            "                         bot.\\n"
            "/whitelistchat [chat_id] Remove a chat from the\\n"
            "                         blacklist.\\n"
            "/blacklistedchat         Show all blacklisted chats.\\n"
            "</pre>\\n\\n"
            "<b>Block Users</b>\\n\\n"
            "<pre>"
            "Command                  Description\\n"
            "────────────────────────────────────────\\n"
            "/block [username/reply]  Block a user from using the\\n"
            "                         bot.\\n"
            "/unblock [username/reply] Unblock a previously\\n"
            "                         blocked user.\\n"
            "/blockedusers            Show the list of blocked\\n"
            "                         users."
            "</pre>"
        ),
        "maintenance": (
            "<b>Active Video Chats Module</b>\\n"
            "Manage active voice and video chats.\\n\\n"
            "<b>Commands</b>\\n\\n"
            "<pre>"
            "Command                    Description\\n"
            "────────────────────────────────────────\\n"
            "/activevoice               Show all active voice chats.\\n"
            "/activevideo               Show all active video chats.\\n"
            "/vclogger [enable/disable] Enable or disable video\\n"
            "                           chat logs.\\n"
            "/autoend [enable/disable]  Automatically end streams\\n"
            "                           when nobody is listening."
            "</pre>"
        ),
        "queue": (
            "<b>AUTO PLAY MODULE</b>\\n\\n"
            "Playback, queue and automatic next-track controls.\\n\\n"
            "<pre>"
            "COMMAND                  DESCRIPTION\\n"
            "────────────────────────────────────────\\n"
            "/pause / /cpause          Pause the current stream.\\n"
            "/resume / /cresume        Resume the paused stream.\\n"
            "/skip / /next             Skip to the next track.\\n"
            "/end / /stop              Stop playback and clear queue.\\n"
            "/queue                    Show the current queue.\\n"
            "/shuffle                  Shuffle queued tracks.\\n"
            "/loop [1-10]              Repeat the current track.\\n"
            "/seek [time]              Seek to a timestamp.\\n"
            "/seekback [time]          Seek backward.\\n"
            "</pre>"
        ),
        "start": (
            "<b>Start Module</b>\\n"
            "Basic bot commands.\\n\\n"
            "<b>Commands</b>\\n\\n"
            "<pre>"
            "Command       Description\\n"
            "────────────────────────────────────────\\n"
            "/start        Start the music bot.\\n"
            "/help         Open the help menu.\\n"
            "/privacy      View the privacy policy.\\n"
            "/reboot       Reboot the bot for your chat.\\n"
            "/settings     Open the interactive group settings menu.\\n"
            "/sudolist     Show the list of bot sudo users."
            "</pre>"
        ),
        "autoplay": (
            "<b>Auto Play</b>\\n"
            "Auto Play automatically plays related songs when the\\n"
            "queue becomes empty.\\n\\n"
            "<b>Command</b>\\n\\n"
            "<pre>"
            "Command       Description\\n"
            "────────────────────────────────────────\\n"
            "/autoplay     Open Auto Play settings."
            "</pre>\\n\\n"
            "<b>Enable / Disable</b>\\n"
            "• Use <code>/autoplay</code> and tap the Auto Play button.\\n"
            "• You can also toggle Auto Play directly from the\\n"
            "  <b>Stream Controls</b>.\\n"
            "• The button shows whether Auto Play is <b>Enabled</b> or\\n"
            "  <b>Disabled</b>.\\n\\n"
            "<b>How It Works</b>\\n"
            "• Queued songs are played first.\\n"
            "• When the queue ends, related songs are picked from\\n"
            "  YouTube Mix.\\n"
            "• Auto Play continues until disabled or the stream is\\n"
            "  stopped."
        ),
        "main": query.lang["help"],
    }

    help_text = help_texts.get(
        category,
        "<b>APPLE MUSIX HELP</b>\\n\\nChoose a category above to view its commands."
    )

    try:

        await query.edit_message_caption(
            caption=help_text,
            reply_markup=buttons.help_markup(
                query.lang,
                True
            )
        )

    except Exception:

        try:

            await query.edit_message_text(
                text=help_text,
                reply_markup=buttons.help_markup(
                    query.lang,
                    True
                )
            )

        except Exception:
            pass


@app.on_callback_query(
    filters.regex("playmode")
    & ~app.bl_users
)
@lang.language()
@admin_check
async def _playmode(_, query: types.CallbackQuery):

    await query.answer(
        query.lang["processing"],
        show_alert=True
    )

    chat_id = query.message.chat.id

    admin_only = await db.get_play_mode(
        chat_id
    )

    _language = "en"

    await db.set_play_mode(
        chat_id,
        admin_only
    )

    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            not admin_only,
            _language,
            chat_id,
        )
    )