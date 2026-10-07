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
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================

from pyrogram import types
from pyrogram.enums import ButtonStyle

from Elevenyts import app, config, lang


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    # ======================================================
    # DOWNLOAD CANCEL BUTTON
    # ======================================================

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=text,
                        callback_data="cancel_dl",
                        style=ButtonStyle.PRIMARY,
                    )
                ]
            ]
        )

    # ======================================================
    # PREMIUM MUSIC PLAYER
    # ======================================================

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
        autoplay: bool | None = None,
    ) -> types.InlineKeyboardMarkup:

        if remove:
            return self.ikm(
                [
                    [
                        self.ikb(
                            text="✕ CLOSE",
                            callback_data=f"controls close {chat_id}",
                            style=ButtonStyle.DANGER,
                        )
                    ]
                ]
            )

        return self.ikm(
            [
                [
                    self.ikb(
                        text="▷",
                        callback_data=f"controls resume {chat_id}",
                        style=ButtonStyle.SUCCESS,
                    ),
                    self.ikb(
                        text="Ⅱ",
                        callback_data=f"controls pause {chat_id}",
                        style=ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text="↻",
                        callback_data=f"controls loop {chat_id}",
                        style=ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text="▶︎|",
                        callback_data=f"controls skip {chat_id}",
                        style=ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text="□",
                        callback_data=f"controls stop {chat_id}",
                        style=ButtonStyle.DANGER,
                    ),
                ],
                [
                    self.ikb(
                        text=(
                            "AUTO PLAY: ENABLED"
                            if autoplay is True
                            else "AUTO PLAY: DISABLED"
                            if autoplay is False
                            else "AUTO PLAY"
                        ),
                        callback_data=f"controls autoplay {chat_id}",
                        style=ButtonStyle.SUCCESS if autoplay else ButtonStyle.PRIMARY,
                    ),
                ]
            ]
        )

    # ======================================================
    # AUTO PLAY SETTINGS
    # ======================================================

    def autoplay_markup(self, chat_id: int, enabled: bool) -> types.InlineKeyboardMarkup:
        label = "✅ AUTO PLAY: ENABLED" if enabled else "❌ AUTO PLAY: DISABLED"
        return self.ikm([
            [self.ikb(
                text=label,
                callback_data=f"autoplay toggle {chat_id}",
                style=ButtonStyle.SUCCESS if enabled else ButtonStyle.DANGER,
            )],
            [self.ikb(
                text="BACK",
                callback_data=f"autoplay close {chat_id}",
                style=ButtonStyle.PRIMARY,
            )],
        ])

    # ======================================================
    # HELP MENU
    # ======================================================

    def help_markup(
        self,
        _lang: dict,
        back: bool = False,
    ) -> types.InlineKeyboardMarkup:

        # Apple Musix HELP & COMMANDS layout.
        # Button labels intentionally have no arrow icons.
        if back:
            rows = [
                [
                    self.ikb(
                        text="BACK",
                        callback_data="help_main",
                        style=ButtonStyle.DANGER,
                    )
                ]
            ]
        else:
            rows = [
                [
                    self.ikb(text="ADMIN", callback_data="help_admins", style=ButtonStyle.SUCCESS),
                    self.ikb(text="AUTH", callback_data="help_auth", style=ButtonStyle.SUCCESS),
                    self.ikb(text="BLACKLIST", callback_data="help_blchat", style=ButtonStyle.SUCCESS),
                ],
                [
                    self.ikb(text="BROADCAST", callback_data="help_broadcast", style=ButtonStyle.PRIMARY),
                    self.ikb(text="PING", callback_data="help_ping", style=ButtonStyle.PRIMARY),
                    self.ikb(text="PLAY", callback_data="help_play", style=ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text="SUDO", callback_data="help_sudo", style=ButtonStyle.SUCCESS),
                    self.ikb(text="VIDEOCHATS", callback_data="help_maintenance", style=ButtonStyle.SUCCESS),
                    self.ikb(text="START", callback_data="start", style=ButtonStyle.SUCCESS),
                ],
                [
                    self.ikb(text="AUTO PLAY", callback_data="help_autoplay", style=ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text="BACK", callback_data="start", style=ButtonStyle.DANGER),
                ],
            ]

        return self.ikm(rows)

    # ======================================================
    # PING MENU
    # ======================================================

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text="📢 Channel",
                        url=config.SUPPORT_CHANNEL,
                        style=ButtonStyle.SUCCESS,
                    ),
                    self.ikb(
                        text="🆘 Support",
                        url=config.SUPPORT_CHAT,
                        style=ButtonStyle.SUCCESS,
                    ),
                ],
                [
                    self.ikb(
                        text="➕ Add Me to Your Group",
                        url=f"https://t.me/{app.username}?startgroup=true",
                        style=ButtonStyle.PRIMARY,
                    ),
                ],
            ]
        )

    # ======================================================
    # QUEUED MUSIC PLAYER
    # ======================================================

    def play_queued(
        self,
        chat_id: int,
        item_id: str,
        _text: str,
    ) -> types.InlineKeyboardMarkup:

        return self.ikm(
            [
                [
                    self.ikb(
                        text="▷",
                        callback_data=f"controls force {chat_id} {item_id}",
                        style=ButtonStyle.SUCCESS,
                    ),
                    self.ikb(
                        text="Ⅱ",
                        callback_data=f"controls pause {chat_id}",
                        style=ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text="▶︎|",
                        callback_data=f"controls skip {chat_id}",
                        style=ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text="□",
                        callback_data=f"controls stop {chat_id}",
                        style=ButtonStyle.DANGER,
                    ),
                ]
            ]
        )

    # ======================================================
    # QUEUE BUTTON
    # ======================================================

    def queue_markup(
        self,
        chat_id: int,
        _text: str,
        playing: bool,
    ) -> types.InlineKeyboardMarkup:

        _action = "pause" if playing else "resume"

        return self.ikm(
            [
                [
                    self.ikb(
                        text=_text,
                        callback_data=f"controls {_action} {chat_id} q",
                        style=ButtonStyle.SUCCESS,
                    )
                ]
            ]
        )

    # ======================================================
    # SETTINGS
    # ======================================================

    def settings_markup(
        self,
        lang: dict,
        admin_only: bool,
        language: str,
        chat_id: int,
    ) -> types.InlineKeyboardMarkup:

        return self.ikm(
            [
                [
                    self.ikb(
                        text=lang["play_mode"] + " ➜",
                        callback_data=f"controls status {chat_id}",
                        style=ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text=admin_only,
                        callback_data="playmode",
                        style=ButtonStyle.SUCCESS,
                    ),
                ]
            ]
        )

    # ======================================================
    # START MENU
    # ======================================================

    def start_key(
        self,
        lang: dict,
        private: bool = False,
    ) -> types.InlineKeyboardMarkup:

        # Apple Musix welcome panel — match the requested layout.
        # Arrows/icons are intentionally omitted from button labels.
        rows = [
            [
                self.ikb(
                    text="🚀 CREATE YOUR GROUP",
                    url=f"https://t.me/{app.username}?startgroup=true",
                    style=ButtonStyle.DANGER,
                )
            ],
            [
                self.ikb(
                    text="👤 OWNER",
                    url="https://t.me/Aashish_0fficial",
                    style=ButtonStyle.SUCCESS,
                ),
                self.ikb(
                    text="🌐 LANGUAGE",
                    callback_data="language",
                    style=ButtonStyle.SUCCESS,
                ),
            ],
            [
                self.ikb(
                    text="🤝 SUPPORT",
                    url=config.SUPPORT_CHAT,
                    style=ButtonStyle.PRIMARY,
                ),
                self.ikb(
                    text="📢 UPDATES",
                    url=config.SUPPORT_CHANNEL,
                    style=ButtonStyle.PRIMARY,
                ),
            ],
            [
                self.ikb(
                    text="⚙️ HELP AND COMMANDS",
                    callback_data="help",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]

        return self.ikm(rows)

    # ======================================================
    # YOUTUBE LINK MENU
    # ======================================================

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:

        return self.ikm(
            [
                [
                    self.ikb(
                        text="ᴄᴏᴘʏ ʟɪɴᴋ",
                        copy_text=link,
                        style=ButtonStyle.PRIMARY,
                    ),
                    self.ikb(
                        text="ᴏᴘᴇɴ ɪɴ ʏᴏᴜᴛᴜʙᴇ",
                        url=link,
                        style=ButtonStyle.PRIMARY,
                    ),
                ]
            ]
        )