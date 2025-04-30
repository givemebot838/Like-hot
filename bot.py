import asyncio
import requests
import json
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Bot config
BOT_TOKEN = os.getenv('8035963417:AAHUyA7CRuf2lX3MHm5-kfouetyODFlj8z8')
API_URL = "https://gmg-id-like.vercel.app/like"
USAGE_FILE = "like_usage.json"
GROUP_STATUS_FILE = "group_status.json"
FOOTER_FILE = "footer_config.json"
USER_DAILY_LIMIT = 2
DEFAULT_DAILY_LIMIT = 50
UNLIMITED_USER_ID = '7943593819'

# --- Helper Functions ---

def load_usage():
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r") as f:
                data = json.load(f)
                if data.get("date") == today:
                    return data
        except json.JSONDecodeError:
            pass
    return {"date": today, "total_count": 0, "users": {}}

def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_group_status():
    if os.path.exists(GROUP_STATUS_FILE):
        try:
            with open(GROUP_STATUS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def save_group_status(data):
    with open(GROUP_STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_group_active(chat_id):
    status = load_group_status()
    group = status.get(str(chat_id))
    if not group or not group.get("active"):
        return False
    expiry = group.get("expires")
    if expiry:
        return datetime.now() <= datetime.strptime(expiry, "%Y-%m-%d")
    return True

def get_group_limit(chat_id):
    status = load_group_status()
    return status.get(str(chat_id), {}).get("limit", DEFAULT_DAILY_LIMIT)

def load_footer_config():
    if os.path.exists(FOOTER_FILE):
        try:
            with open(FOOTER_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def save_footer_config(data):
    with open(FOOTER_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_footer(chat_id):
    config = load_footer_config()
    return config.get(str(chat_id), "*BOT BY GRANDMIXTURE GAMER*")

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_group_active(chat_id):
        return
    await update.message.reply_text(
        f"👋 Welcome! Use /like <uid> to send likes. (Each user: {USER_DAILY_LIMIT}/day, Group Limit Varies)"
    )

async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_group_active(chat_id):
        return

    usage = load_usage()
    user_id = str(update.message.from_user.id)
    group_limit = get_group_limit(chat_id)

    if usage["total_count"] >= group_limit:
        await update.message.reply_text("❌ Daily group limit reached. Try again tomorrow!")
        return

    if user_id != UNLIMITED_USER_ID:
        user_count = usage["users"].get(user_id, 0)
        if user_count >= USER_DAILY_LIMIT:
            await update.message.reply_text(f"❌ You used your {USER_DAILY_LIMIT} likes for today.")
            return

    if len(context.args) != 1:
        await update.message.reply_text("❗ Usage: /like <uid>")
        return

    uid = context.args[0]
    server = "ind"
    temp_msg = await update.message.reply_text(f"⏳ Sending likes to UID: {uid}...")
    await asyncio.sleep(10)

    try:
        response = requests.get(API_URL, params={"uid": uid, "server_name": server})
        if response.status_code == 200:
            data = response.json()
            nickname = data.get("PlayerNickname", "Unknown Player")
            before_likes = data.get("LikesbeforeCommand", data.get("Likes", "0"))
            after_likes = data.get("LikesafterCommand", data.get("Likes", "0"))

            try:
                likes_given = int(after_likes) - int(before_likes)
            except ValueError:
                likes_given = 0

            if likes_given == 0:
                await temp_msg.edit_text("⚠️This UID has already received the today maximum likes in Please wait till Reset.Try again tomorrow.")
                return

            usage["total_count"] += 1
            if user_id != UNLIMITED_USER_ID:
                usage["users"][user_id] = usage["users"].get(user_id, 0) + 1
            save_usage(usage)

            remaining_group = group_limit - usage["total_count"]
            user_remaining = (
                "GMG" if user_id == UNLIMITED_USER_ID else USER_DAILY_LIMIT - usage["users"].get(user_id, 0)
            )

            await temp_msg.edit_text(
                f"""*✅ Like Sent Successfully\\!*
*├─ Player Name:* `{nickname}`
*├─ Before Likes:* `{before_likes}`
*├─ After Likes:* `{after_likes}`
*├─ Likes Given:* `{likes_given}`
*├─ Your Remaining:* `{user_remaining}`
*└─ Remaining Group Likes Today:* `{remaining_group}`

{get_footer(chat_id)}""",
                parse_mode="MarkdownV2"
            )
        else:
            await temp_msg.edit_text("❌ Failed to send likes. Server error.")
    except Exception as e:
        print(f"[ERROR] like command failed: {e}")
        await temp_msg.edit_text("❌ An error occurred while sending likes.")
        
# Main bot run
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("like", like))
    print("Bot is running...")
    app.run_polling()
        
