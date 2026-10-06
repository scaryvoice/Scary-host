#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║       🎭  TEAM MYSTERIOUS - File Hosting Bot  🎭        ║
║       Force Join + Menu + File Hosting                  ║
║       Owner: SCARY 👻  |  Developer: LILXGOD ⚡         ║
╚══════════════════════════════════════════════════════════╝
"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path

# ═══════════════════════════════════════════════════════════
#  🎯  SETUP ZONE — SIRF YAHAN VALUES BHARO
# ═══════════════════════════════════════════════════════════
#
#  1️⃣  BOT_TOKEN      →  @BotFather se lo
#  2️⃣  OWNER_ID       →  @userinfobot se lo (apni Telegram ID)
#  3️⃣  CHANNEL_USERNAME →  apna channel @username (force join)
#  4️⃣  ADMIN_IDS      →  extra admins ki IDs (comma se separate)
#  5️⃣  PORT           →  HTTP server port (default 8080)
#  6️⃣  BASE_URL       →  public URL (blank = localhost)
#
# ───────────────────────────────────────────────────────────

BOT_TOKEN        = "8861785824:AAFZQcApJEgxCQ4PJOXzWC-op5I_D5YcdXk"                           # 🔑 yahan bot token daalo
OWNER_ID         = 8484989041                            # 👑 yahan apni Telegram ID
CHANNEL_USERNAME = "@teamxmysterious"               # 📢 force join channel
ADMIN_IDS        = []                           # 🛡️ e.g. [123, 456, 789]
PORT             = int(os.getenv("PORT", "8080"))                        # 🌐 HTTP port
BASE_URL         = ""                           # 🔗 blank = localhost

# ───────────────────────────────────────────────────────────
#  ⚙️  CONSTANTS (iske niche kuch na badlo)
# ───────────────────────────────────────────────────────────

BOT_NAME    = "TEAM MYSTERIOUS"
OWNER_NAME  = "SCARY"
DEV_NAME    = "LILXGOD"
MAX_FILE_MB = 20

# ═══════════════════════════════════════════════════════════
#  🚀  AUTO INSTALL + SETUP
# ═══════════════════════════════════════════════════════════
REQUIRED = {
    "telegram": "python-telegram-bot==20.7",
    "dotenv": "python-dotenv==1.0.0",
    "httpx": "httpx==0.27.0",
}


def ensure_deps():
    missing = []
    for mod, pkg in REQUIRED.items():
        if importlib.util.find_spec(mod) is None:
            missing.append(pkg)
    if missing:
        print(f"📦 Installing: {', '.join(missing)}")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--upgrade", *missing]
            )
            print("✅ Dependencies ready!\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Auto-install failed: {e}")
            print("Run: pip install " + " ".join(missing))
            sys.exit(1)


ensure_deps()

import logging
import asyncio
import re
import json
from urllib.parse import quote
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from threading import Thread

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import TelegramError, BadRequest, Forbidden, RetryAfter
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────────
#  PATHS & ENV PERSISTENCE
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
ENV_FILE = BASE_DIR / ".env"
HOST_DIR = BASE_DIR / "hosted_files"
HOST_DIR.mkdir(exist_ok=True)


def load_saved_config():
    """Agar .env file maujood hai to usme se values uthao (only if empty)."""
    global BOT_TOKEN, OWNER_ID, CHANNEL_USERNAME, ADMIN_IDS, PORT, BASE_URL

    if not ENV_FILE.exists():
        return

    data = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()

    if not BOT_TOKEN:
        BOT_TOKEN = data.get("BOT_TOKEN", BOT_TOKEN)
    if not OWNER_ID:
        try:
            OWNER_ID = int(data.get("OWNER_ID", OWNER_ID) or 0)
        except ValueError:
            pass
    if CHANNEL_USERNAME == "@YourChannel":
        CHANNEL_USERNAME = data.get("CHANNEL_USERNAME", CHANNEL_USERNAME)
    if not ADMIN_IDS:
        raw = data.get("ADMIN_IDS", "")
        ADMIN_IDS = [int(x) for x in raw.split(",") if x.strip().isdigit()]
    if PORT == 8080:
        try:
            PORT = int(data.get("PORT", PORT) or PORT)
        except ValueError:
            pass
    if not BASE_URL:
        BASE_URL = data.get("BASE_URL", BASE_URL)


def prompt_missing_config():
    """Agar SETUP ZONE khali hai to interactively poochho."""
    global BOT_TOKEN, OWNER_ID, CHANNEL_USERNAME, ADMIN_IDS, PORT, BASE_URL

    needs_setup = (
        not BOT_TOKEN
        or OWNER_ID == 0
        or CHANNEL_USERNAME == "@YourChannel"
    )

    if not needs_setup:
        return

    print("\n" + "═" * 60)
    print(f"   🎭  {BOT_NAME} — Setup Wizard")
    print("═" * 60)

    if not BOT_TOKEN:
        BOT_TOKEN = input("🔑 BOT_TOKEN (from @BotFather): ").strip()
        if not BOT_TOKEN:
            print("❌ Token required!")
            sys.exit(1)

    if OWNER_ID == 0:
        while True:
            raw = input("👑 OWNER_ID (from @userinfobot): ").strip()
            if raw.isdigit():
                OWNER_ID = int(raw)
                break
            print("⚠️  Sirf numbers daalo (e.g. 123456789)")

    if CHANNEL_USERNAME == "@YourChannel":
        ch = input("📢 Channel username (e.g. @TeamMysterious): ").strip()
        if not ch:
            print("❌ Channel required for force-join!")
            sys.exit(1)
        CHANNEL_USERNAME = ch if ch.startswith("@") else "@" + ch

    if not ADMIN_IDS:
        raw = input(
            f"🛡️  Extra ADMIN_IDS (comma-separated, blank = none) "
            f"[owner {OWNER_ID} auto-added]: "
        ).strip()
        if raw:
            ADMIN_IDS = [
                int(x) for x in re.split(r"[,\s]+", raw) if x.isdigit()
            ]

    if BASE_URL == "":
        raw = input(f"🔗 Public BASE_URL (blank = http://localhost:{PORT}): ").strip()
        BASE_URL = raw or f"http://localhost:{PORT}"

    # Save to .env so next time no prompt
    ENV_FILE.write_text(
        f"# TEAM MYSTERIOUS — Auto-generated config\n"
        f"BOT_TOKEN={BOT_TOKEN}\n"
        f"OWNER_ID={OWNER_ID}\n"
        f"CHANNEL_USERNAME={CHANNEL_USERNAME}\n"
        f"ADMIN_IDS={','.join(map(str, ADMIN_IDS))}\n"
        f"BASE_URL={BASE_URL}\n"
        f"PORT={PORT}\n"
    )
    print(f"\n✅ Config saved → {ENV_FILE}\n")


# Load saved first, then prompt if needed
load_saved_config()
prompt_missing_config()

# Owner auto-included in admins
if OWNER_ID and OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(OWNER_ID)

ALLOWED_EXT = {".js", ".py", ".mjs", ".cjs", ".json", ".txt", ".zip", ".ts"}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s │ %(levelname)s │ %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("mysterious")


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
_MD_SPECIAL = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def esc(text) -> str:
    if text is None:
        return ""
    return _MD_SPECIAL.sub(r"\\\1", str(text))


# ─────────────────────────────────────────────
#  HTTP FILE SERVER (threaded)
# ─────────────────────────────────────────────
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HOST_DIR), **kwargs)

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            pass


def start_http_server():
    while True:
        try:
            server = ThreadingHTTPServer(("0.0.0.0", PORT), QuietHandler)
            logger.info(f"🌐 HTTP server live on port {PORT}")
            server.serve_forever()
        except OSError as e:
            logger.error(f"❌ HTTP failed: {e}")
            logger.error(f"Port {PORT} busy? Change PORT and restart.")
            return
        except Exception as e:
            logger.exception(f"HTTP crashed: {e}")
            import time
            time.sleep(5)


# ─────────────────────────────────────────────
#  FORCE JOIN
# ─────────────────────────────────────────────
async def is_joined(user_id: int, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    if is_owner(user_id) or is_admin(user_id):
        return True  # admins always bypass
    try:
        member = await ctx.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME, user_id=user_id
        )
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
            ChatMemberStatus.RESTRICTED,
        )
    except BadRequest as e:
        logger.warning(f"Join check BadRequest ({CHANNEL_USERNAME}): {e}")
        logger.warning("⚠️  Bot ko channel ka ADMIN banao!")
        return False
    except (Forbidden, TelegramError) as e:
        logger.warning(f"Join check failed: {e}")
        return False


def force_join_keyboard():
    link = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=link)],
        [InlineKeyboardButton("✅ I've Joined — Verify",
                              callback_data="verify_join")],
    ])


FORCE_JOIN_TEXT = (
    f"👻 *SCARY ACCESS LOCK* 👻\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    f"🎭 *{esc(BOT_NAME)}* me ghusne se pehle\n"
    f"hamara channel join karna padega\\.\\.\\.\n\n"
    f"📢 {esc(CHANNEL_USERNAME)}\n\n"
    "👇 *Join karo, phir Verify dabao*"
)

VERIFY_FAIL = (
    "💀 Bhai pehle channel join kar!\n\n"
    f"📢 {CHANNEL_USERNAME} join karo,\n"
    "phir Verify button dabao."
)


# ─────────────────────────────────────────────
#  MENUS
# ─────────────────────────────────────────────
def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Upload File", callback_data="menu:upload"),
         InlineKeyboardButton("📂 My Files", callback_data="menu:list")],
        [InlineKeyboardButton("📊 Stats", callback_data="menu:stats"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu:about")],
        [InlineKeyboardButton("📖 Help", callback_data="menu:help"),
         InlineKeyboardButton("🎭 Team Info", callback_data="menu:team")],
    ])


def get_reply_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📤 Upload"), KeyboardButton("📂 My Files")],
            [KeyboardButton("📊 Stats"), KeyboardButton("ℹ️ About")],
            [KeyboardButton("📖 Help"), KeyboardButton("🎭 Team")],
        ],
        resize_keyboard=True, is_persistent=True,
        input_field_placeholder="Choose from menu or send a file…",
    )


def get_back_button(target="menu:main"):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Back to Menu", callback_data=target)]]
    )


# ─────────────────────────────────────────────
#  TEXT TEMPLATES
# ─────────────────────────────────────────────
WELCOME = (
    f"🎭 *Welcome to {esc(BOT_NAME)}* 🎭\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "✅ *Verified\\!* Channel join confirmed\\.\n"
    "👻 _Welcome to the darkness\\.\\.\\._\n\n"
    "Mujhe `.js` / `.py` / `.json` / `.zip` file bhejo — "
    "main host karke *direct download link* dunga\\.\n\n"
    "⚡ *Fast • Free • No Ads*\n\n"
    "👇 *Menu se choose karo:*"
)

HELP_TEXT = (
    f"📖 *{esc(BOT_NAME)} — Help*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "1️⃣ Koi bhi supported file bhejo\n"
    "2️⃣ Bot save karega aur link dega\n"
    "3️⃣ Link browser me open karke download karo\n\n"
    f"*Allowed:* `{esc(', '.join(sorted(ALLOWED_EXT)))}`\n\n"
    "*Commands:*\n"
    "• /start — Main menu\n"
    "• /menu — Menu dikhao\n"
    "• /list — Hosted files\n"
    "• /stats — Server stats\n"
    "• /about — About us\n"
    "• /myid — Apni Telegram ID dekho"
)

ABOUT_TEXT = (
    f"🎭 *About {esc(BOT_NAME)}* 🎭\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "We host your code files with instant direct links\\.\n\n"
    "🚀 *Features:*\n"
    "• Lightning\\-fast uploads\n"
    "• Direct download links\n"
    "• Support for `.js`, `.py`, `.json` & more\n"
    "• No ads, no limits\n\n"
    f"👑 *Owner:* {esc(OWNER_NAME)}\n"
    f"💻 *Developer:* {esc(DEV_NAME)}\n\n"
    "💀 *Mystery is our identity\\.*"
)

TEAM_TEXT = (
    f"🎭 *{esc(BOT_NAME)} — The Crew* 🎭\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    f"👑 *Owner* — {esc(OWNER_NAME)} 👻\n"
    f"💻 *Developer* — {esc(DEV_NAME)} ⚡\n"
    "🎨 *Designer* — Phantom\n"
    "⚡ *Support* — Ghost\n\n"
    f"📢 Join: {esc(CHANNEL_USERNAME)}\n"
    "💀 _We move in silence\\.\\.\\. if you hear us, it's too late\\._"
)

UPLOAD_HINT = (
    "📤 *Upload Mode*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Ab koi bhi file bhejo — main host kar dunga\\!\n\n"
    f"*Allowed:* `{esc(', '.join(sorted(ALLOWED_EXT)))}`\n"
    f"*Max size:* {MAX_FILE_MB} MB\n\n"
    "_File select karke send dabao\\._"
)


# ─────────────────────────────────────────────
#  SAFE REPLY HELPERS
# ─────────────────────────────────────────────
async def safe_reply(message, text, **kwargs):
    try:
        return await message.reply_text(text, **kwargs)
    except BadRequest as e:
        logger.warning(f"reply failed: {e}")
        kwargs.pop("parse_mode", None)
        return await message.reply_text(text, **kwargs)


async def safe_edit(query, text, **kwargs):
    try:
        return await query.edit_message_text(text, **kwargs)
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return None
        try:
            return await query.message.reply_text(text, **kwargs)
        except Exception as ee:
            logger.warning(f"edit fallback failed: {ee}")
            return None


# ─────────────────────────────────────────────
#  BOT HANDLERS
# ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    if not await is_joined(update.effective_user.id, ctx):
        await safe_reply(update.message, FORCE_JOIN_TEXT,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=force_join_keyboard())
        return
    await safe_reply(update.message, WELCOME,
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_main_menu())
    await safe_reply(update.message,
                     "💡 _Tip: Neeche wale buttons bhi use kar sakte ho\\._",
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_reply_keyboard())


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_joined(update.effective_user.id, ctx):
        await safe_reply(update.message, FORCE_JOIN_TEXT,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=force_join_keyboard())
        return
    await safe_reply(update.message,
                     f"🎭 *{esc(BOT_NAME)} — Main Menu*",
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_main_menu())


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_joined(update.effective_user.id, ctx):
        await safe_reply(update.message, FORCE_JOIN_TEXT,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=force_join_keyboard())
        return
    await safe_reply(update.message, HELP_TEXT,
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_back_button())


async def cmd_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_joined(update.effective_user.id, ctx):
        await safe_reply(update.message, FORCE_JOIN_TEXT,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=force_join_keyboard())
        return
    await safe_reply(update.message, ABOUT_TEXT,
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_back_button())


async def cmd_myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show user's Telegram ID — useful for admin setup."""
    uid = update.effective_user.id
    tag = (
        "👑 *Owner*" if is_owner(uid)
        else "🛡️ *Admin*" if is_admin(uid)
        else "👤 User"
    )
    await safe_reply(
        update.message,
        f"🆔 *Your Telegram ID*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"`{uid}`\n\n"
        f"Role: {tag}\n\n"
        "_Copy karke OWNER_ID / ADMIN_IDS me daal sakte ho\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_back_button(),
    )


def _files_list_text():
    files = sorted([f for f in HOST_DIR.iterdir() if f.is_file()])
    if not files:
        return None
    lines = [f"📂 *{esc(BOT_NAME)} — Hosted Files*\n",
             "━━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for i, f in enumerate(files[:30], 1):
        kb = f.stat().st_size / 1024
        lines.append(f"{i}\\. `{esc(f.name)}` — {kb:.1f} KB")
    if len(files) > 30:
        lines.append(f"\n_\\.\\.\\.and {len(files) - 30} more_")
    lines.append(f"\n_Total: {len(files)} file\\(s\\)_")
    return "\n".join(lines)


async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_joined(update.effective_user.id, ctx):
        await safe_reply(update.message, FORCE_JOIN_TEXT,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=force_join_keyboard())
        return
    text = _files_list_text()
    if not text:
        await safe_reply(update.message,
                         f"📂 *{esc(BOT_NAME)}* pe abhi koi file host nahi hui\\.",
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=get_back_button())
        return
    await safe_reply(update.message, text,
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_back_button())


async def cmd_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    # 🔒 Admin only
    if not is_admin(update.effective_user.id):
        await safe_reply(update.message,
                         "🚫 Ye command sirf *admins* use kar sakte hain\\.",
                         parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not ctx.args:
        await safe_reply(update.message, "Usage: `/delete filename\\.js`",
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=get_back_button())
        return
    name = ctx.args[0]
    fp = (HOST_DIR / name)
    try:
        fp = fp.resolve()
        root = HOST_DIR.resolve()
        if root not in fp.parents and fp.parent != root:
            await safe_reply(update.message, "❌ Invalid path.")
            return
    except Exception:
        await safe_reply(update.message, "❌ Invalid filename.")
        return
    if not fp.is_file():
        await safe_reply(update.message, "❌ File nahi mili\\.",
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=get_back_button())
        return
    fp.unlink()
    await safe_reply(update.message, f"🗑️ `{esc(name)}` delete ho gayi\\.",
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_back_button())


def _stats_text():
    files = [f for f in HOST_DIR.iterdir() if f.is_file()]
    total = sum(f.stat().st_size for f in files)
    return (
        f"📊 *{esc(BOT_NAME)} — Server Stats*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📁 Files hosted: `{len(files)}`\n"
        f"💾 Total size: `{total/1024/1024:.2f} MB`\n"
        f"🌐 Base URL: `{esc(BASE_URL)}`\n"
        f"🔌 Port: `{PORT}`\n"
        f"👑 Owner: `{esc(OWNER_NAME)}` \\(ID: `{OWNER_ID}`\\)\n"
        f"💻 Developer: `{esc(DEV_NAME)}`\n"
        f"🛡️ Admins: `{len(ADMIN_IDS)}`\n"
        f"⚡ Status: `🟢 Online`"
    )


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_joined(update.effective_user.id, ctx):
        await safe_reply(update.message, FORCE_JOIN_TEXT,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=force_join_keyboard())
        return
    await safe_reply(update.message, _stats_text(),
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_back_button())


async def handle_doc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        return
    if not await is_joined(update.effective_user.id, ctx):
        await safe_reply(update.message, FORCE_JOIN_TEXT,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=force_join_keyboard())
        return

    doc = update.message.document
    if not doc.file_name:
        await safe_reply(update.message, "❌ File ka naam nahi mila.")
        return

    ext = Path(doc.file_name).suffix.lower()
    if ext not in ALLOWED_EXT:
        await safe_reply(update.message,
                         f"❌ `{esc(ext)}` supported nahi hai\\.\n"
                         f"Allowed: `{esc(', '.join(sorted(ALLOWED_EXT)))}`",
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=get_back_button())
        return

    if doc.file_size and doc.file_size > MAX_FILE_MB * 1024 * 1024:
        await safe_reply(update.message,
                         f"⚠️ File {MAX_FILE_MB}MB se badi hai\\.",
                         reply_markup=get_back_button())
        return

    status = await safe_reply(update.message,
                              f"⏳ *{esc(BOT_NAME)}* downloading file\\.\\.\\.",
                              parse_mode=ParseMode.MARKDOWN_V2)

    safe_filename = re.sub(r"[^\w.\-]", "_", doc.file_name)
    safe_name = f"{doc.file_unique_id}_{safe_filename}"
    filepath = HOST_DIR / safe_name

    try:
        tg_file = await ctx.bot.get_file(doc.file_id)
        await tg_file.download_to_drive(custom_path=str(filepath))
    except RetryAfter as e:
        await safe_edit(status, f"⏳ Rate limited\\. Retry in {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        try:
            tg_file = await ctx.bot.get_file(doc.file_id)
            await tg_file.download_to_drive(custom_path=str(filepath))
        except Exception as ee:
            await safe_edit(status, f"❌ Download fail: {esc(str(ee))}",
                            parse_mode=ParseMode.MARKDOWN_V2)
            return
    except Exception as e:
        logger.exception("Download failed")
        await safe_edit(status, f"❌ Download fail: {esc(str(e))}",
                        parse_mode=ParseMode.MARKDOWN_V2)
        return

    kb = filepath.stat().st_size / 1024
    url = f"{BASE_URL}/{quote(safe_name)}"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ Download", url=url)],
        [InlineKeyboardButton("📋 Copy Link",
                              callback_data=f"copy:{safe_name[:50]}")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")],
    ])

    await safe_edit(
        status,
        f"✅ *File Hosted by {esc(BOT_NAME)}\\!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📄 Name: `{esc(doc.file_name)}`\n"
        f"📦 Size: `{kb:.1f} KB`\n\n"
        f"🔗 Link:\n`{esc(url)}`\n\n"
        f"👑 _Owner: {esc(OWNER_NAME)} 👻_\n"
        f"💻 _Developer: {esc(DEV_NAME)} ⚡_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=markup,
        disable_web_page_preview=True,
    )


async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    try:
        await q.answer()
    except TelegramError:
        pass

    data = q.data or ""
    user_id = q.from_user.id

    if data == "verify_join":
        if await is_joined(user_id, ctx):
            await safe_edit(q, WELCOME,
                            parse_mode=ParseMode.MARKDOWN_V2,
                            reply_markup=get_main_menu())
            try:
                await q.message.reply_text(
                    "💡 _Tip: Neeche wale buttons bhi use kar sakte ho\\._",
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=get_reply_keyboard(),
                )
            except TelegramError:
                pass
        else:
            try:
                await q.answer(VERIFY_FAIL, show_alert=True)
            except TelegramError:
                pass
        return

    if not await is_joined(user_id, ctx):
        try:
            await q.answer("💀 Pehle channel join karo!", show_alert=True)
        except TelegramError:
            pass
        await safe_edit(q, FORCE_JOIN_TEXT,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=force_join_keyboard())
        return

    if data.startswith("copy:"):
        fname = data.split(":", 1)[1]
        matches = [f.name for f in HOST_DIR.iterdir()
                   if f.is_file() and f.name.startswith(fname)]
        if not matches:
            try:
                await q.answer("File nahi mili", show_alert=True)
            except TelegramError:
                pass
            return
        url = f"{BASE_URL}/{quote(matches[0])}"
        try:
            await q.message.reply_text(f"📋 `{esc(url)}`",
                                       parse_mode=ParseMode.MARKDOWN_V2)
        except TelegramError:
            await q.message.reply_text(url)
        return

    routes = {
        "menu:main":   (f"🎭 *{esc(BOT_NAME)} — Main Menu*\n\n👇 Choose an option:",
                        get_main_menu()),
        "menu:upload": (UPLOAD_HINT, get_back_button()),
        "menu:about":  (ABOUT_TEXT, get_back_button()),
        "menu:help":   (HELP_TEXT, get_back_button()),
        "menu:team":   (TEAM_TEXT, get_back_button()),
    }

    if data == "menu:list":
        text = _files_list_text()
        if not text:
            await safe_edit(q,
                            "📂 *Koi file host nahi hui abhi\\.*\n\n"
                            "📤 File bhejo host karne ke liye\\!",
                            parse_mode=ParseMode.MARKDOWN_V2,
                            reply_markup=get_back_button())
            return
        await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=get_back_button())
        return

    if data == "menu:stats":
        await safe_edit(q, _stats_text(), parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=get_back_button())
        return

    if data in routes:
        text, kb = routes[data]
        await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=kb)
        return


async def reply_button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not await is_joined(update.effective_user.id, ctx):
        await safe_reply(update.message, FORCE_JOIN_TEXT,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=force_join_keyboard())
        return

    t = update.message.text
    mapping = {
        "📤 Upload":   (UPLOAD_HINT, None),
        "📊 Stats":    (_stats_text(), get_back_button()),
        "ℹ️ About":    (ABOUT_TEXT, get_main_menu()),
        "📖 Help":     (HELP_TEXT, get_main_menu()),
        "🎭 Team":     (TEAM_TEXT, get_main_menu()),
    }

    if t == "📂 My Files":
        text = _files_list_text()
        if not text:
            await safe_reply(update.message,
                             f"📂 *{esc(BOT_NAME)}* pe abhi koi file host nahi hui\\.",
                             parse_mode=ParseMode.MARKDOWN_V2,
                             reply_markup=get_back_button())
            return
        await safe_reply(update.message, text,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=get_back_button())
        return

    if t in mapping:
        text, kb = mapping[t]
        await safe_reply(update.message, text,
                         parse_mode=ParseMode.MARKDOWN_V2,
                         reply_markup=kb)
        return

    await safe_reply(update.message,
                     "🤔 Samajh nahi aaya\\.\n\n/menu se menu kholo\\.",
                     parse_mode=ParseMode.MARKDOWN_V2,
                     reply_markup=get_main_menu())


async def err_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {ctx.error}", exc_info=ctx.error)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing!")
        sys.exit(1)
    if not CHANNEL_USERNAME:
        print("❌ CHANNEL_USERNAME missing!")
        sys.exit(1)
    if not OWNER_ID:
        print("⚠️  OWNER_ID not set — admin commands restricted!")

    Thread(target=start_http_server, daemon=True).start()

    print("\n" + "═" * 60)
    print(f"   🎭  {BOT_NAME} — File Hosting Bot  🎭")
    print(f"   👑  Owner: {OWNER_NAME} (ID: {OWNER_ID}) 👻")
    print(f"   💻  Developer: {DEV_NAME} ⚡")
    print("═" * 60)
    print(f"   📢 Force Join  : {CHANNEL_USERNAME}")
    print(f"   🛡️  Admins      : {len(ADMIN_IDS)} ({', '.join(map(str, ADMIN_IDS))})")
    print(f"   🌐 Base URL    : {BASE_URL}")
    print(f"   🔌 Port        : {PORT}")
    print(f"   📁 Files dir   : {HOST_DIR}")
    print("═" * 60)
    print("   ✅ Bot is running — Ctrl+C to stop\n")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(30).write_timeout(30)
        .connect_timeout(30).pool_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("stats", cmd_stats))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, reply_button_handler)
    )

    app.add_error_handler(err_handler)

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n👋 {BOT_NAME} bot stopped. Goodbye!")