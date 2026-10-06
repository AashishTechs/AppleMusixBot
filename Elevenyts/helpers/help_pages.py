# ==========================================================
# Copyright (c) 2026 Apple Music <<3
# Apple Musix help-page image renderer
# ==========================================================

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


WIDTH = 960
PAD = 32

BG = "#0f1b28"
PANEL = "#1b2a39"
HEADER = "#27384b"
ROW_A = "#172637"
ROW_B = "#223244"
BORDER = "#3b4d62"
TEXT = "#f5f7fb"
MUTED = "#dce4ee"
COMMAND = "#58a9e8"


def _font(size, bold=False):
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/opentype/inter/InterDisplay-Regular.otf",
        ]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


TITLE = _font(38, True)
DESC = _font(24)
SECTION = _font(31, True)
HEADER_FONT = _font(23, True)
BODY = _font(21)
BODY_BOLD = _font(21, True)
SMALL = _font(19)


PAGES = {
    "admins": {
        "title": "Admin Commands",
        "desc": "Commands available only to administrators.",
        "sections": [
            {
                "title": "Play Mode",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/playmode", "Open Play Mode settings and choose whether playback is available to everyone or administrators only."],
                        ["/settings", "Open the group settings panel and manage the current Play Mode."],
                    ],
                ),
            },
            {
                "title": "Play Commands",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/play <query>", "Play a song or YouTube search result in the voice chat."],
                        ["/playforce <query>", "Force-play the requested track immediately."],
                        ["/vplay <query>", "Play a video in the video chat."],
                        ["/vplayforce <query>", "Force-play the requested video immediately."],
                        ["/cplay <query>", "Play music using the linked channel."],
                        ["/cplayforce <query>", "Force-play music using the linked channel."],
                        ["/cvplay <query>", "Play a video using the linked channel."],
                        ["/cvplayforce <query>", "Force-play a video using the linked channel."],
                        ["/channelplay [linked|id|disable]", "Enable, configure, or disable channel play for the group."],
                    ],
                ),
            },
            {
                "title": "Playback",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/pause /cpause", "Pause the current playing stream."],
                        ["/resume /cresume", "Resume the paused stream."],
                        ["/skip /next /cskip /cnext", "Skip the current stream and play the next track in queue."],
                        ["/end /stop /cend /cstop", "Stop playback and clear the queue."],
                        ["/queue /playing /cqueue /cplaying", "Show the current queue."],
                        ["/shuffle /cshuffle", "Shuffle the queued tracks."],
                        ["/loop [mode] /cloop [mode]", "Cycle or set the loop mode for the current playback."],
                        ["/seek [seconds] /cseek [seconds]", "Seek forward to the requested number of seconds."],
                        ["/seekback [seconds] /cseekback [seconds]", "Seek backward to the requested number of seconds."],
                    ],
                ),
            },
        ],
        "notes": [
            "Prefix commands with c to use them in linked channels.",
            "Example: /cpause, /cskip, /cqueue",
        ],
    },
    "auth": {
        "title": "Auth Module",
        "desc": "Manage authorized users who can control the bot without being Telegram admins.",
        "sections": [
            {
                "title": "Commands",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/auth [username]", "Add a user to the bot's authorized users list."],
                        ["/unauth [username]", "Remove a user from the authorized users list."],
                        ["/authusers", "Show the list of authorized users in the current group."],
                    ],
                ),
            }
        ],
        "notes": [
            "Authorized users can use admin commands without having admin rights in the chat.",
            "This feature is available only for group administrators.",
        ],
    },
    "blchat": {
        "title": "Blacklist Module",
        "desc": "Manage blacklisted chats and blocked users.",
        "sections": [
            {
                "title": "Blacklist Chats",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/blacklistchat [chat_id]", "Blacklist a chat from using the bot."],
                        ["/whitelistchat [chat_id]", "Remove a chat from the blacklist."],
                        ["/blacklistedchat", "Show all blacklisted chats."],
                    ],
                ),
            },
            {
                "title": "Block Users",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/block [username/reply]", "Block a user from using the bot."],
                        ["/unblock [username/reply]", "Unblock a previously blocked user."],
                        ["/blockedusers", "Show the list of blocked users."],
                    ],
                ),
            },
        ],
    },
    "broadcast": {
        "title": "Broadcast Module",
        "desc": "Broadcast messages to chats and users. (Sudo users only)",
        "sections": [
            {
                "title": "Commands",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/broadcast [message/reply]", "Broadcast a message to served chats."],
                    ],
                ),
            },
            {
                "title": "Broadcast Modes",
                "table": (
                    ["Mode", "Description"],
                    [
                        ["--pin", "Pin the broadcasted message in chats."],
                        ["--pinloud", "Pin the message and notify chat members."],
                        ["--user", "Broadcast only to users who have started the bot."],
                        ["--nobot", "Skip broadcasting to bots."],
                    ],
                ),
            },
        ],
        "example": "/broadcast --user --pin Testing Broadcast",
    },
    "ping": {
        "title": "Ping Module",
        "desc": "Check the bot's performance and statistics.",
        "sections": [
            {
                "title": "Commands",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/ping", "Show the bot's ping and system statistics."],
                        ["/stats", "Display global statistics, top tracks, top users, top chats, and more."],
                    ],
                ),
            }
        ],
    },
    "play": {
        "title": "Play Module",
        "desc": "Commands for playing music and videos.",
        "bullets": [
            "c stands for Channel Play.",
            "v stands for Video Play.",
            "force stands for Force Play.",
        ],
        "sections": [
            {
                "title": "Play Commands",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/play /vplay /cplay", "Start streaming the requested track in the voice/video chat."],
                        ["/playforce /vplayforce /cplayforce", "Stop the current stream and immediately play the requested track."],
                        ["/channelplay [chat username/id]", "Connect a channel to a group for channel play."],
                        ["/channelplay disable", "Disable channel play for the group."],
                        ["/pause /cpause", "Pause the current stream."],
                        ["/resume /cresume", "Resume the paused stream."],
                        ["/skip /next /cskip", "Skip the current stream and play the next track in queue."],
                        ["/end /stop /cend", "Stop playback and clear the queue."],
                        ["/queue /cqueue", "Show the current queue."],
                        ["/shuffle /cshuffle", "Shuffle the queued tracks."],
                        ["/loop [1-10]", "Repeat the current track for the specified number of times."],
                        ["/seek [time]", "Seek to the given timestamp."],
                        ["/seekback [time]", "Seek backward to the given timestamp."],
                    ],
                ),
            }
        ],
        "notes": [
            "Prefix commands with c to use them in linked channels.",
            "Example: /cpause, /cskip, /cqueue",
        ],
    },
    "sudo": {
        "title": "Sudo Module",
        "desc": "Commands available only to sudo users.",
        "sections": [
            {
                "title": "Sudo Users",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/addsudo [username/reply]", "Add a sudo user."],
                        ["/delsudo [username/reply]", "Remove a sudo user."],
                        ["/listsudo", "Show sudo users."],
                    ],
                ),
            },
            {
                "title": "Global Ban",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/gban [username/reply]", "Globally ban a user from all served chats."],
                        ["/ungban [username/reply]", "Remove a global ban."],
                        ["/gbannedusers", "Show globally banned users."],
                    ],
                ),
            },
            {
                "title": "Blacklist Chats",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/blacklistchat [chat_id]", "Blacklist a chat from using the bot."],
                        ["/whitelistchat [chat_id]", "Remove a chat from the blacklist."],
                        ["/blacklistedchat", "Show all blacklisted chats."],
                    ],
                ),
            },
            {
                "title": "Block Users",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/block [username/reply]", "Block a user from using the bot."],
                        ["/unblock [username/reply]", "Unblock a previously blocked user."],
                        ["/blockedusers", "Show the list of blocked users."],
                    ],
                ),
            },
        ],
    },
    "maintenance": {
        "title": "Active Video Chats Module",
        "desc": "Manage active voice and video chats.",
        "sections": [
            {
                "title": "Commands",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/activevoice", "Show all active voice chats."],
                        ["/activevideo", "Show all active video chats."],
                        ["/vclogger [enable/disable]", "Enable or disable video chat logs."],
                        ["/autoend [enable/disable]", "Automatically end streams when nobody is listening."],
                    ],
                ),
            }
        ],
    },
    "start": {
        "title": "Start Module",
        "desc": "Basic bot commands.",
        "sections": [
            {
                "title": "Commands",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/start", "Start the music bot."],
                        ["/help", "Open the help menu."],
                        ["/privacy", "View the privacy policy."],
                        ["/reboot", "Reboot the bot for your chat."],
                        ["/settings", "Open the interactive group settings menu."],
                        ["/sudolist", "Show the list of bot sudo users."],
                    ],
                ),
            }
        ],
    },
    "autoplay": {
        "title": "Auto Play",
        "desc": "Auto Play automatically plays related songs when the queue becomes empty.",
        "sections": [
            {
                "title": "Command",
                "table": (
                    ["Command", "Description"],
                    [
                        ["/autoplay", "Open Auto Play settings."],
                    ],
                ),
            }
        ],
        "subsections": [
            (
                "Enable / Disable",
                [
                    "Use /autoplay and tap the Auto Play button.",
                    "You can also toggle Auto Play directly from the Stream Controls.",
                    "The button shows whether Auto Play is Enabled or Disabled.",
                ],
            ),
            (
                "How It Works",
                [
                    "Queued songs are played first.",
                    "When the queue ends, related songs are picked from YouTube Mix.",
                    "Auto Play continues until disabled or the stream is stopped.",
                ],
            ),
        ],
    },
}


def format_help_page(category):
    """Build a real Telegram HTML help page with a text-based two-column table.

    Telegram messages do not support native bordered tables, so the table is
    rendered with monospace box-drawing characters. This keeps the page as
    real text (not an image) while closely matching the reference layout.
    """
    page = PAGES.get(category, PAGES["start"])

    def esc(value):
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def cell_lines(value, width):
        value = str(value)
        return wrap(
            value,
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
        ) or [""]

    def make_table(headers, rows):
        # Kept narrow enough for Telegram mobile while still looking like
        # the Command | Description tables in the reference screenshots.
        cmd_width = 17
        desc_width = 22

        def border(left, middle, right, fill="─"):
            return (
                left
                + fill * (cmd_width + 2)
                + middle
                + fill * (desc_width + 2)
                + right
            )

        output = [
            border("┌", "┬", "┐"),
        ]

        header_left = cell_lines(headers[0], cmd_width)
        header_right = cell_lines(headers[1], desc_width)
        header_height = max(len(header_left), len(header_right))
        for i in range(header_height):
            left = header_left[i] if i < len(header_left) else ""
            right = header_right[i] if i < len(header_right) else ""
            output.append(
                f"│ {left.ljust(cmd_width)} │ {right.ljust(desc_width)} │"
            )

        output.append(border("├", "┼", "┤"))

        for row_index, row in enumerate(rows):
            left_lines = cell_lines(row[0], cmd_width)
            right_lines = cell_lines(row[1], desc_width)
            row_height = max(len(left_lines), len(right_lines))

            for i in range(row_height):
                left = left_lines[i] if i < len(left_lines) else ""
                right = right_lines[i] if i < len(right_lines) else ""
                output.append(
                    f"│ {left.ljust(cmd_width)} │ {right.ljust(desc_width)} │"
                )

            if row_index != len(rows) - 1:
                output.append(border("├", "┼", "┤"))

        output.append(border("└", "┴", "┘"))
        return "\n".join(output)

    lines = [
        f"<b>{esc(page['title'])}</b>",
        f"<i>{esc(page.get('desc', ''))}</i>",
        "",
    ]

    for item in page.get("bullets", []):
        lines.append(f"• {esc(item)}")
    if page.get("bullets"):
        lines.append("")

    for sec in page.get("sections", []):
        lines.append(f"<b>{esc(sec['title'])}</b>")
        headers, rows = sec["table"]
        lines.append(
            "<pre>"
            + esc(make_table(headers, rows))
            + "</pre>"
        )
        lines.append("")

    for title, bullets in page.get("subsections", []):
        lines.append(f"<b>{esc(title)}</b>")
        for item in bullets:
            lines.append(f"• {esc(item)}")
        lines.append("")

    if page.get("notes"):
        lines.append("<b>Notes</b>")
        for item in page["notes"]:
            lines.append(f"• {esc(item)}")

    if page.get("example"):
        lines.extend(
            ["", "<b>Example</b>", f"<code>{esc(page['example'])}</code>"]
        )

    return "\n".join(lines).strip()


def _wrap(draw, text, font, width):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _rounded(draw, xy, fill, outline=BORDER, radius=14, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def render_help_page(category, out_dir="/tmp"):
    page = PAGES.get(category, PAGES["start"])
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"applemusix_help_{category}.jpg"

    dummy = Image.new("RGB", (WIDTH, 100), BG)
    d = ImageDraw.Draw(dummy)

    height = PAD + 58
    title_lines = _wrap(d, page["title"], TITLE, WIDTH - PAD * 2)
    height += len(title_lines) * 46 + 12
    desc_lines = _wrap(d, page.get("desc", ""), DESC, WIDTH - PAD * 2)
    height += len(desc_lines) * 31 + 20

    if page.get("bullets"):
        height += 10
        for item in page["bullets"]:
            height += len(_wrap(d, "• " + item, BODY, WIDTH - PAD * 2 - 20)) * 29 + 7

    for sec in page.get("sections", []):
        height += 54
        headers, rows = sec["table"]
        col1 = 310
        col2 = WIDTH - PAD * 2 - col1
        for row in [headers] + rows:
            left = _wrap(d, row[0], HEADER_FONT if row is headers else BODY, col1 - 26)
            right = _wrap(d, row[1], HEADER_FONT if row is headers else BODY_BOLD, col2 - 26)
            height += max(len(left), len(right)) * 28 + 22

    for title, bullets in page.get("subsections", []):
        height += 54
        for item in bullets:
            height += len(_wrap(d, "• " + item, BODY, WIDTH - PAD * 2 - 20)) * 29 + 7

    if page.get("notes"):
        height += 54
        for item in page["notes"]:
            height += len(_wrap(d, "• " + item, BODY, WIDTH - PAD * 2 - 20)) * 29 + 7

    if page.get("example"):
        height += 58 + 34

    height += PAD + 10
    img = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)

    _rounded(draw, (18, 14, WIDTH - 18, height - 14), PANEL, outline=PANEL, radius=24, width=1)

    x = PAD
    y = 34

    for line in title_lines:
        draw.text((x, y), line, font=TITLE, fill=TEXT)
        y += 46
    y += 2

    for line in desc_lines:
        draw.text((x, y), line, font=DESC, fill=TEXT)
        y += 31
    y += 14

    if page.get("bullets"):
        for item in page["bullets"]:
            for line in _wrap(draw, "• " + item, BODY, WIDTH - PAD * 2 - 20):
                draw.text((x + 4, y), line, font=BODY, fill=TEXT)
                y += 29
            y += 5
        y += 4

    for sec in page.get("sections", []):
        draw.text((x, y), sec["title"], font=SECTION, fill=TEXT)
        y += 48

        headers, rows = sec["table"]
        col1 = 310
        col2 = WIDTH - PAD * 2 - col1
        table_x = x
        table_w = WIDTH - PAD * 2
        table_top = y
        row_heights = []

        for row in [headers] + rows:
            f_left = HEADER_FONT if row is headers else BODY
            f_right = HEADER_FONT if row is headers else BODY
            left_lines = _wrap(draw, row[0], f_left, col1 - 26)
            right_lines = _wrap(draw, row[1], f_right, col2 - 26)
            row_heights.append(max(len(left_lines), len(right_lines)) * 28 + 22)

        total_h = sum(row_heights)
        draw.rounded_rectangle(
            (table_x, table_top, table_x + table_w, table_top + total_h),
            radius=14,
            fill=ROW_A,
            outline=BORDER,
            width=2,
        )

        cy = table_top
        for idx, row in enumerate([headers] + rows):
            rh = row_heights[idx]
            fill = HEADER if idx == 0 else (ROW_A if idx % 2 else ROW_B)
            draw.rectangle((table_x, cy, table_x + table_w, cy + rh), fill=fill)
            if idx == 0:
                draw.line((table_x, cy + rh, table_x + table_w, cy + rh), fill=BORDER, width=2)
            elif idx > 0:
                draw.line((table_x, cy, table_x + table_w, cy), fill=BORDER, width=1)
            draw.line((table_x + col1, cy, table_x + col1, cy + rh), fill=BORDER, width=1)

            f_left = HEADER_FONT if idx == 0 else BODY
            f_right = HEADER_FONT if idx == 0 else BODY
            left_lines = _wrap(draw, row[0], f_left, col1 - 26)
            right_lines = _wrap(draw, row[1], f_right, col2 - 26)

            ly = cy + (rh - len(left_lines) * 28) / 2
            ry = cy + (rh - len(right_lines) * 28) / 2
            for line in left_lines:
                draw.text((table_x + 13, ly), line, font=f_left, fill=TEXT)
                ly += 28
            for line in right_lines:
                draw.text((table_x + col1 + 13, ry), line, font=f_right, fill=TEXT)
                ry += 28
            cy += rh

        y = table_top + total_h + 24

    for title, bullets in page.get("subsections", []):
        draw.text((x, y), title, font=SECTION, fill=TEXT)
        y += 48
        for item in bullets:
            for line in _wrap(draw, "• " + item, BODY, WIDTH - PAD * 2 - 20):
                draw.text((x + 4, y), line, font=BODY, fill=TEXT)
                y += 29
            y += 5
        y += 4

    if page.get("notes"):
        draw.text((x, y), "Notes", font=SECTION, fill=TEXT)
        y += 48
        for item in page["notes"]:
            for line in _wrap(draw, "• " + item, BODY, WIDTH - PAD * 2 - 20):
                draw.text((x + 4, y), line, font=BODY, fill=TEXT)
                y += 29
            y += 5

    if page.get("example"):
        draw.text((x, y), "Example", font=SECTION, fill=TEXT)
        y += 44
        draw.text((x, y), page["example"], font=BODY, fill=COMMAND)

    img.save(out, "JPEG", quality=94, optimize=True)
    return str(out)
