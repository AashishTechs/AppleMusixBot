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

import asyncio
import importlib
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from pyrogram import idle, types

# Telegram command menu. Keep this list complete so users can discover every
# registered command from Telegram's "/" suggestion menu. Permission filters
# remain in the individual plugins, so showing a command does not grant access.
BOT_COMMANDS = [
    types.BotCommand("start", "Start the bot"),
    types.BotCommand("help", "Open the help menu"),
    types.BotCommand("privacy", "View privacy policy"),
    types.BotCommand("play", "Play a song"),
    types.BotCommand("vplay", "Play a video"),
    types.BotCommand("cplay", "Play music in a linked channel"),
    types.BotCommand("playforce", "Force play a song"),
    types.BotCommand("vplayforce", "Force play a video"),
    types.BotCommand("cplayforce", "Force play in a linked channel"),
    types.BotCommand("pause", "Pause playback"),
    types.BotCommand("cpause", "Pause linked-channel playback"),
    types.BotCommand("resume", "Resume playback"),
    types.BotCommand("cresume", "Resume linked-channel playback"),
    types.BotCommand("skip", "Skip the current track"),
    types.BotCommand("next", "Play the next track"),
    types.BotCommand("cskip", "Skip in a linked channel"),
    types.BotCommand("stop", "Stop playback and clear queue"),
    types.BotCommand("end", "Stop playback and clear queue"),
    types.BotCommand("cend", "Stop linked-channel playback"),
    types.BotCommand("queue", "Show the current queue"),
    types.BotCommand("cqueue", "Show the linked-channel queue"),
    types.BotCommand("shuffle", "Shuffle the queue"),
    types.BotCommand("cshuffle", "Shuffle linked-channel queue"),
    types.BotCommand("loop", "Loop the current track"),
    types.BotCommand("seek", "Seek to a timestamp"),
    types.BotCommand("seekback", "Seek backward"),
    types.BotCommand("channelplay", "Configure channel play"),
    types.BotCommand("settings", "Open group settings"),
    types.BotCommand("autoplay", "Configure Auto Play"),
    types.BotCommand("ping", "Check bot ping and status"),
    types.BotCommand("stats", "Show bot statistics"),
    types.BotCommand("id", "Show Telegram ID"),
    types.BotCommand("activevoice", "Show active voice chats"),
    types.BotCommand("activevideo", "Show active video chats"),
    types.BotCommand("vclogger", "Configure voice-chat logging"),
    types.BotCommand("autoend", "Configure automatic stream ending"),
    types.BotCommand("auth", "Authorize a user"),
    types.BotCommand("unauth", "Remove user authorization"),
    types.BotCommand("authusers", "Show authorized users"),
    types.BotCommand("adminmention", "Mention group administrators"),
    types.BotCommand("bots", "Show bot information"),
    types.BotCommand("groupdata", "Show group information"),
    types.BotCommand("blacklistchat", "Blacklist a chat"),
    types.BotCommand("whitelistchat", "Remove chat from blacklist"),
    types.BotCommand("blacklistedchat", "Show blacklisted chats"),
    types.BotCommand("blchats", "Show blacklisted chats"),
    types.BotCommand("block", "Block a user"),
    types.BotCommand("unblock", "Unblock a user"),
    types.BotCommand("blockedusers", "Show blocked users"),
    types.BotCommand("blusers", "Show blocked users"),
    types.BotCommand("broadcast", "Broadcast a message"),
    types.BotCommand("stop_gcast", "Stop an active broadcast"),
    types.BotCommand("stop_broadcast", "Stop an active broadcast"),
    types.BotCommand("addsudo", "Add a sudo user"),
    types.BotCommand("delsudo", "Remove a sudo user"),
    types.BotCommand("rmsudo", "Remove a sudo user"),
    types.BotCommand("listsudo", "Show sudo users"),
    types.BotCommand("sudolist", "Show sudo users"),
    types.BotCommand("gban", "Globally ban a user"),
    types.BotCommand("ungban", "Remove a global ban"),
    types.BotCommand("unglobalban", "Remove a global ban"),
    types.BotCommand("gbanlist", "Show global bans"),
    types.BotCommand("gbannedusers", "Show global bans"),
    types.BotCommand("leave", "Make the bot leave a chat"),
    types.BotCommand("autoleave", "Configure automatic leaving"),
    types.BotCommand("maintenance", "Configure maintenance mode"),
    types.BotCommand("reboot", "Reboot the bot"),
    types.BotCommand("restart", "Restart the bot"),
    types.BotCommand("eval", "Run owner maintenance code"),
]

async def install_bot_commands():
    """Publish private and group command menus with the correct Telegram scopes."""
    try:
        # Default/private menu: keep the complete command list.
        await app.set_bot_commands(BOT_COMMANDS)

        # Group menu: hide owner-only maintenance/admin commands, while keeping
        # normal group commands such as /auth visible. Handler permissions still
        # decide who can actually execute each command.
        hidden_from_groups = {
            "broadcast", "stop_gcast", "stop_broadcast",
            "addsudo", "delsudo", "rmsudo", "listsudo", "sudolist",
            "gban", "ungban", "unglobalban", "gbanlist", "gbannedusers",
            "blacklistchat", "whitelistchat", "blacklistedchat", "blchats",
            "block", "unblock", "blockedusers", "blusers",
            "leave", "autoleave", "maintenance", "reboot", "restart", "eval",
        }
        group_commands = [
            command for command in BOT_COMMANDS
            if command.command not in hidden_from_groups
        ]
        await app.set_bot_commands(
            group_commands,
            scope=types.BotCommandScopeAllGroupChats(),
        )

        logger.info(
            "⌨️ Telegram command menus installed: %d private, %d group commands.",
            len(BOT_COMMANDS),
            len(group_commands),
        )
    except Exception as e:
        logger.error("Failed to install Telegram command menu: %s", e, exc_info=True)


# Raise the file descriptor limit on Linux to avoid "[Errno 24] Too many open files"
# when serving many groups concurrently (each audio stream + ffmpeg probe opens FDs).
if sys.platform != "win32":
    try:
        import resource
        _soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        _target = min(65536, _hard)
        if _soft < _target:
            resource.setrlimit(resource.RLIMIT_NOFILE, (_target, _hard))
    except Exception:
        pass

from Elevenyts import (tune, app, config, db,
                   logger, stop, userbot, yt)
from Elevenyts.plugins import all_modules


# HTTP Server for Render health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for Render health checks"""
    
    def do_GET(self):
        """Handle GET requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')
    
    def log_message(self, format, *args):
        """Suppress log messages to keep console clean"""
        pass


def run_http_server():
    """Run a simple HTTP server for Render health checks"""
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"🌐 HTTP health check server started on port {port}")
    server.serve_forever()


async def main():
    try:
        # Step 1: Validate required environment variables
        try:
            config.check()
        except SystemExit as e:
            logger.error(str(e))
            return

        # Step 2: Start HTTP server in a separate thread (for Render)
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        logger.info("🌐 HTTP server thread started for Render health checks")

        # Step 3: Connect to MongoDB database
        await db.connect()
        
        # Step 4: Start the main bot client
        await app.boot()
        
        # Step 5: Start assistant/userbot clients (for joining voice chats)
        await userbot.boot()
        
        # Step 6: Initialize voice call handler
        await tune.boot()

        # Step 7: Load all plugin modules (commands like /play, /pause, etc.)
        for module in all_modules:
            try:
                importlib.import_module(f"Elevenyts.plugins.{module}")
            except Exception as e:
                logger.error(f"Failed to load plugin {module}: {e}", exc_info=True)
        logger.info(f"🔌 Loaded {len(all_modules)} plugin modules.")

        # Publish commands after every plugin has been loaded. The menu is
        # visible to everyone; owner/admin restrictions are still enforced
        # by the command handlers themselves.
        await install_bot_commands()

        # Step 8: Load sudo users and blacklisted users from database
        sudoers = await db.get_sudoers()
        app.sudoers.update(sudoers)  # Add sudo users to set
        app.sudo_filter.update(sudoers)  # Add sudo users to filter
        app.bl_users.update(await db.get_blacklisted())  # Add blacklisted users to filter
        logger.info(f"👑 Loaded {len(app.sudoers)} sudo users.")
        logger.info("\n🎉 Bot started successfully! Ready to play music! 🎵\n")

        # Step 9: Keep the bot running (press Ctrl+C to stop)
        try:
            await idle()
        except KeyboardInterrupt:
            logger.info("Received stop signal...")
        except Exception as e:
            logger.error(f"Error during idle: {e}", exc_info=True)
        
        # Step 10: Cleanup and shutdown when bot is stopped
        await stop()
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except SystemExit as e:
        logger.error(f"Bot exited with system error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error caused bot to stop: {e}", exc_info=True)
        # Don't raise - allow clean shutdown
    finally:
        # Ensure cleanup happens
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.stop()
        except:
            pass
