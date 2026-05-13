import json
import os
import sys
import signal
import subprocess
import hashlib
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

CONTROLLER_TOKEN = "8999526361:AAHiHkjpP5QNxHwX6hm6vd6LmGMyhnyUNmg"
OWNER_ID         = "8600328303"
MAIN_BOT_SCRIPT  = "main.py"

FEATURES_FILE = "bot/features.json"
LOG_FILE      = "bot/shuvo.log"
PID_FILE      = "bot/.main_pid"
PAUSE_FILE    = "bot/.paused"

_PASS_HASH = hashlib.sha256("asraful123".encode()).hexdigest()

_authenticated: set = set()

FEATURES = {
    "ai_chat":     "🤖 AI Chat",
    "daily_claim": "🎁 Daily Claim",
    "redeem":      "🎫 Redeem Code",
    "voice":       "🎙️ Voice TTS",
    "imagegen":    "🌈 Image Gen",
    "music":       "🎧 Music Gen",
    "videogen":    "🎞️ Video Gen",
    "sprite":      "👾 Sprite Gen",
    "model3d":     "🧊 3D Model",
    "editimage":   "🖌️ Edit Image",
    "tgid":        "📞 TG ID→Num",
    "tguser":      "🔍 User→Num",
    "indinfo":     "☎️ IND Info",
    "instainfo":   "📸 Instagram",
    "viddown":     "🎬 Vid Download",
    "pincode":     "📮 Pincode",
    "ifsc":        "🏦 IFSC",
    "ipinfo":      "🌐 IP Info",
    "ffstats":     "🎯 FF Stats",
    "emailrep":    "📧 Email Check",
    "vehicle":     "🚗 Vehicle",
    "weather":     "⛅ Weather",
    "nasa":        "🚀 NASA",
    "aadhar":      "🪪 Aadhar",
    "gst":         "💼 GST",
    "pan":         "🪪 PAN",
    "paknum":      "🇵🇰 Pak Num",
    "vehicle_rc":  "🚗 Vehicle RC",
    "upi":         "💳 UPI Info",
}


def is_owner(uid):
    return str(uid) == str(OWNER_ID)

def is_authed(uid):
    return str(uid) in _authenticated

def check_pass(text: str) -> bool:
    return hashlib.sha256(text.strip().encode()).hexdigest() == _PASS_HASH


def load_features():
    os.makedirs("bot", exist_ok=True)
    try:
        with open(FEATURES_FILE) as f:
            data = json.load(f)
    except Exception:
        data = {}
    for k in FEATURES:
        if k not in data:
            data[k] = True
    return data

def save_features(data):
    os.makedirs("bot", exist_ok=True)
    with open(FEATURES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_main_pid():
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return None

def process_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def bot_status_line():
    pid    = get_main_pid()
    paused = os.path.exists(PAUSE_FILE)
    if pid and process_alive(pid):
        state = f"🟢 Running  (PID {pid})"
    elif pid:
        state = f"🔴 Dead     (stale PID {pid})"
    else:
        state = "⚪ Unknown  (no PID file)"
    mode = "⏸️ PAUSED" if paused else "▶️ Active"
    return state, mode

def panel_text():
    feats       = load_features()
    on          = sum(1 for v in feats.values() if v)
    tot         = len(feats)
    state, mode = bot_status_line()
    now         = datetime.now().strftime("%d %b %Y  %H:%M:%S")
    return (
        f"🎛️ <b>SHUVO BOT — Controller</b>\n\n"
        f"🤖 Status  : {state}\n"
        f"🕹️ Mode    : {mode}\n"
        f"🔧 Features: <b>{on}/{tot}</b> enabled\n"
        f"🕐 Time    : {now}"
    )

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔧 Features",      callback_data="c_feat_0"),
         InlineKeyboardButton("📋 Live Logs",     callback_data="c_logs")],
        [InlineKeyboardButton("📊 Stats",         callback_data="c_stats"),
         InlineKeyboardButton("🔁 Refresh",       callback_data="c_home")],
        [InlineKeyboardButton("⏸️ Pause Bot",     callback_data="c_pause"),
         InlineKeyboardButton("▶️ Resume Bot",    callback_data="c_resume")],
        [InlineKeyboardButton("🔄 Restart Bot",   callback_data="c_restart"),
         InlineKeyboardButton("🛑 Kill Process",  callback_data="c_kill")],
        [InlineKeyboardButton("🟢 Spawn Process", callback_data="c_spawn"),
         InlineKeyboardButton("🗑 Clear Logs",    callback_data="c_clearlogs")],
        [InlineKeyboardButton("🔒 Logout",        callback_data="c_logout")],
    ])

def features_keyboard(page=0):
    feats      = load_features()
    items      = list(FEATURES.items())
    per        = 8
    start      = page * per
    chunk      = items[start:start + per]
    rows       = []
    for i in range(0, len(chunk), 2):
        row = []
        for key, label in chunk[i:i+2]:
            icon = "✅" if feats.get(key, True) else "❌"
            row.append(InlineKeyboardButton(f"{icon} {label}", callback_data=f"cf_{key}"))
        rows.append(row)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"c_feat_{page-1}"))
    total_pages = (len(items) + per - 1) // per
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"c_feat_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton("🔛 All ON",  callback_data="c_allon"),
        InlineKeyboardButton("🔕 All OFF", callback_data="c_alloff"),
    ])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="c_home")])
    return InlineKeyboardMarkup(rows)

def feat_panel_text():
    feats = load_features()
    on    = sum(1 for v in feats.values() if v)
    tot   = len(feats)
    return f"🔧 <b>Feature Toggle</b>\n✅ Enabled: <b>{on}/{tot}</b>\n\nTap any feature to toggle it:"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if not is_owner(uid):
        await update.message.reply_text("🚫 Unauthorized.")
        return
    if is_authed(uid):
        await update.message.reply_text(panel_text(), reply_markup=main_keyboard(), parse_mode="HTML")
        return
    context.user_data["awaiting_pass"] = True
    await update.message.reply_text(
        "🔐 <b>Controller Bot</b>\n\n"
        "🔑 Enter your password to access the panel:",
        parse_mode="HTML"
    )

async def cmd_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    _authenticated.discard(uid)
    context.user_data["awaiting_pass"] = False
    await update.message.reply_text("🔒 Logged out. Send /start to log in again.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if not is_owner(uid):
        return
    if not context.user_data.get("awaiting_pass"):
        return

    text = update.message.text or ""
    try:
        await update.message.delete()
    except Exception:
        pass

    if check_pass(text):
        _authenticated.add(uid)
        context.user_data["awaiting_pass"] = False
        await update.message.reply_text(
            "✅ <b>Access Granted!</b>\n\n" + panel_text(),
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
    else:
        context.user_data["awaiting_pass"] = True
        await update.message.reply_text(
            "❌ <b>Wrong password!</b>\n\nTry again:",
            parse_mode="HTML"
        )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid   = str(query.from_user.id)

    if not is_owner(uid):
        await query.answer("🚫 Unauthorized.", show_alert=True)
        return

    if not is_authed(uid):
        await query.answer("🔒 Session expired. Send /start to log in.", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data in ("c_home", "c_refresh"):
        await query.edit_message_text(panel_text(), reply_markup=main_keyboard(), parse_mode="HTML")

    elif data == "c_logout":
        _authenticated.discard(uid)
        context.user_data["awaiting_pass"] = False
        await query.edit_message_text(
            "🔒 <b>Logged out.</b>\n\nSend /start to log in again.",
            parse_mode="HTML"
        )

    elif data.startswith("c_feat_"):
        page = int(data.split("_")[-1])
        await query.edit_message_text(feat_panel_text(), reply_markup=features_keyboard(page), parse_mode="HTML")

    elif data.startswith("cf_"):
        key   = data[3:]
        feats = load_features()
        feats[key] = not feats.get(key, True)
        save_features(feats)
        await query.edit_message_text(feat_panel_text(), reply_markup=features_keyboard(0), parse_mode="HTML")

    elif data == "c_allon":
        save_features({k: True for k in FEATURES})
        await query.edit_message_text(feat_panel_text(), reply_markup=features_keyboard(0), parse_mode="HTML")

    elif data == "c_alloff":
        save_features({k: False for k in FEATURES})
        await query.edit_message_text(feat_panel_text(), reply_markup=features_keyboard(0), parse_mode="HTML")

    elif data == "c_logs":
        try:
            with open(LOG_FILE, encoding="utf-8") as f:
                lines = f.readlines()[-50:]
            log_text = "".join(lines).strip() or "No logs yet."
        except FileNotFoundError:
            log_text = "📭 No log file found yet."
        if len(log_text) > 3500:
            log_text = "…" + log_text[-3500:]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Refresh", callback_data="c_logs"),
             InlineKeyboardButton("🗑 Clear",   callback_data="c_clearlogs")],
            [InlineKeyboardButton("🏠 Home",    callback_data="c_home")],
        ])
        await query.edit_message_text(
            f"📋 <b>Live Logs</b> (last 50 lines)\n\n<pre>{log_text}</pre>",
            reply_markup=kb, parse_mode="HTML"
        )

    elif data == "c_clearlogs":
        try:
            open(LOG_FILE, "w").close()
            msg = "🗑 Log file cleared."
        except Exception as e:
            msg = f"❌ Could not clear: {e}"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Home", callback_data="c_home")]
        ]))

    elif data == "c_pause":
        os.makedirs("bot", exist_ok=True)
        with open(PAUSE_FILE, "w") as f:
            f.write(datetime.now().isoformat())
        await query.edit_message_text(
            "⏸️ <b>Bot Paused</b>\n\nAll user commands are blocked.\nUsers will see a maintenance message.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Resume", callback_data="c_resume"),
                 InlineKeyboardButton("🏠 Home",   callback_data="c_home")],
            ]), parse_mode="HTML"
        )

    elif data == "c_resume":
        try:
            os.remove(PAUSE_FILE)
        except FileNotFoundError:
            pass
        await query.edit_message_text(
            "▶️ <b>Bot Resumed</b>\n\nAll commands are active again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Home", callback_data="c_home")]
            ]), parse_mode="HTML"
        )

    elif data == "c_restart":
        pid = get_main_pid()
        if pid and process_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                result = f"🔄 SIGTERM sent to PID {pid}\nWorkflow will auto-restart the bot."
            except Exception as e:
                result = f"❌ Failed: {e}"
        else:
            result = "⚠️ Process not found. Use Spawn to start it manually."
        await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Home", callback_data="c_home")]
        ]))

    elif data == "c_kill":
        pid = get_main_pid()
        if pid and process_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
                result = f"🛑 SIGKILL sent to PID {pid}\nProcess forcefully terminated."
            except Exception as e:
                result = f"❌ Failed: {e}"
        else:
            result = "⚠️ No running process found."
        await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Home", callback_data="c_home")]
        ]))

    elif data == "c_spawn":
        try:
            proc = subprocess.Popen(
                [sys.executable, MAIN_BOT_SCRIPT],
                stdout=open(LOG_FILE, "a"),
                stderr=subprocess.STDOUT
            )
            result = f"🟢 Spawned new bot process\nPID: <b>{proc.pid}</b>"
        except Exception as e:
            result = f"❌ Failed to spawn: {e}"
        await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Home", callback_data="c_home")]
        ]), parse_mode="HTML")

    elif data == "c_stats":
        try:
            with open("bot/user.json") as f:
                users = json.load(f)
            total  = len(users)
            active = sum(1 for u in users.values() if not u.get("banned"))
            banned = total - active
            admins = sum(1 for u in users.values() if u.get("is_admin"))
            tot_cr = sum(u.get("credits", 0) for u in users.values())
        except Exception:
            total = active = banned = admins = tot_cr = 0
        try:
            with open("bot/codes.json") as f:
                codes = json.load(f)
            n_codes = len(codes)
        except Exception:
            n_codes = 0
        state, mode = bot_status_line()
        feats  = load_features()
        on_cnt = sum(1 for v in feats.values() if v)
        await query.edit_message_text(
            f"📊 <b>SHUVO BOT Stats</b>\n\n"
            f"👥 Total Users   : <b>{total}</b>\n"
            f"✅ Active        : <b>{active}</b>\n"
            f"🚫 Banned        : <b>{banned}</b>\n"
            f"🛡 Admins        : <b>{admins}</b>\n"
            f"💰 Total Credits : <b>{tot_cr}</b>\n"
            f"🎫 Codes         : <b>{n_codes}</b>\n"
            f"🔧 Features ON   : <b>{on_cnt}/{len(feats)}</b>\n\n"
            f"🤖 {state}\n"
            f"🕹️ {mode}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Refresh", callback_data="c_stats"),
                 InlineKeyboardButton("🏠 Home",    callback_data="c_home")],
            ]), parse_mode="HTML"
        )


def main():
    print("Controller bot starting...")
    app = Application.builder().token(CONTROLLER_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("logout", cmd_logout))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Controller bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
