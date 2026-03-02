import hashlib, logging, re, os, json, secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from functools import wraps
from datetime import datetime, timedelta

# === Cấu hình ===
BOT_TOKEN = '8315041903:AAEZfE8z8CNfUm44c1S457lv1-7zfq-2hM0'
logging.basicConfig(filename='bot_md5_tai_xiu.log', level=logging.INFO, format='%(asctime)s - %(message)s')

ADMIN_FILE = 'admin_list.json'
KEY_FILE = 'keys.json'
USER_KEYS_FILE = 'user_keys.json'
VERIFY_HISTORY_FILE = 'verify_history.json'

# Các nhóm cần tham gia
GROUPS = {
    "CLB Thang Tùng 🐉": {
        "id": -1002845092108,
        "link": "https://t.me/+D3RxtnBmm_40MjZl"
    },
    "Chat telegram 🐉": {
        "id": -1002573537290,
        "link": "https://t.me/tinnongv5"
    },
    "Share All 🐉": {
        "id": -1002667684704,
        "link": "https://t.me/+JdolGoz6KyQ5M2Vl"
    }
}


# Các game có sẵn
GAMES = {
    "68GAMEBAI": "✨ 68GAMEBAI",
    "HITCLUB": "🔥 HITCLUB",
    "B52": "💣 B52",
    "LUCK8": "🍀 LUCK8",
    "go88": "🔰 go88",
    "iwin": "🔱 iwin"
}

ADMIN_USER_ID = '7071414779'
ADMIN_KEY = 'adminkey120666'

# === Tạo mặc định ===
def init_admin_and_key():
    admins = load_json(ADMIN_FILE)
    admins.setdefault("admins", [])
    if ADMIN_USER_ID not in admins["admins"]:
        admins["admins"].append(ADMIN_USER_ID)
    save_json(ADMIN_FILE, admins)

    keys = load_json(KEY_FILE)
    keys[ADMIN_KEY] = {"used": True}
    save_json(KEY_FILE, keys)

    user_keys = load_json(USER_KEYS_FILE)
    user_keys[ADMIN_USER_ID] = ADMIN_KEY
    save_json(USER_KEYS_FILE, user_keys)

    verify_history = load_json(VERIFY_HISTORY_FILE)
    verify_history.setdefault("verified_users", [])
    save_json(VERIFY_HISTORY_FILE, verify_history)

    cleanup_expired_keys()

# === Biến toàn cục ===
adjustment = 0.0
wrong_streak = 0
history = []
last_prediction = {}

current_game = {}  # Map user_id -> game_name


# === Tiện ích ===
def load_json(filename):
    return json.load(open(filename, 'r', encoding='utf-8')) if os.path.exists(filename) else {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_admin(user_id):
    admins = load_json(ADMIN_FILE)
    return str(user_id) in admins.get("admins", [])

def is_verified_user(user_id):
    verify_history = load_json(VERIFY_HISTORY_FILE)
    return str(user_id) in verify_history.get("verified_users", [])

def add_verified_user(user_id):
    verify_history = load_json(VERIFY_HISTORY_FILE)
    if str(user_id) not in verify_history.get("verified_users", []):
        verify_history.setdefault("verified_users", []).append(str(user_id))
        save_json(VERIFY_HISTORY_FILE, verify_history)

def cleanup_expired_keys():
    keys = load_json(KEY_FILE)
    now = datetime.now()
    updated = {k: v for k, v in keys.items() if 'expire_time' not in v or datetime.strptime(v['expire_time'], '%Y-%m-%d %H:%M:%S') > now}
    if len(updated) != len(keys):
        save_json(KEY_FILE, updated)

# === Phân tích MD5 ===
def is_valid_md5(md5):
    return bool(re.match(r'^[a-f0-9]{32}$', md5.lower()))

def analyze_md5(md5, adj):
    value = sum(ord(c) * (i + 1) for i, c in enumerate(md5)) % 1000
    base_ratio = value / 1000
    if len(history) >= 3 and history[-1] == history[-2] == history[-3]:
        if history[-1] == 'tài':
            base_ratio += 0.08
        elif history[-1] == 'xỉu':
            base_ratio -= 0.08
    tai_ratio = min(1, max(0, base_ratio + adj))
    return round(tai_ratio * 100, 2), round((1 - tai_ratio) * 100, 2)

def detect_trend(history, max_len=10):
    if len(history) < 3:
        return "Chưa đủ dữ liệu"

    recent = history[-max_len:]
    patterns = {
        ('tài', 'tài', 'xỉu'): "Mẫu: Tài Tài Xỉu",
        ('xỉu', 'tài', 'xỉu'): "Mẫu: Xỉu Tài Xỉu",
        ('xỉu', 'xỉu', 'tài'): "Mẫu: Xỉu Xỉu Tài",
        ('tài', 'xỉu', 'xỉu'): "Mẫu: Tài Xỉu Xỉu",
        ('tài', 'tài', 'xỉu'): "Mẫu: Tài Tài Xỉu",
        ('tài', 'tài', 'tài'): "Mẫu: Tài Tài Tài",
        ('xỉu', 'xỉu', 'xỉu'): "Mẫu: Xỉu Xỉu Xỉu",
        ('xỉu', 'tài', 'xỉu', 'tài'): "Mẫu: Xỉu Tài Xỉu Tài",
        ('tài', 'tài', 'tài', 'xỉu'): "Mẫu: 3 Tài ra Xỉu",
        ('xỉu', 'xỉu', 'xỉu', 'tài'): "Mẫu: 3 Xỉu ra Tài",
        ('tài', 'xỉu', 'tài'): "Mẫu: Tài Xỉu Tài",
        ('xỉu', 'tài', 'tài', 'xỉu'): "Mẫu: Xỉu Tài Tài Xỉu",
    }
    for length in range(4, 2, -1):
        seq = tuple(recent[-length:])
        if seq in patterns:
            return patterns[seq]

    for i in range(5, 2, -1):
        if len(recent) >= i and all(x == recent[-1] for x in recent[-i:]):
            return f"Cầu bệt ({recent[-1].capitalize()} x {i})"

    if len(recent) >= 4 and all(recent[i] != recent[i+1] for i in range(len(recent)-1)):
        return "Cầu đảo (Tài/Xỉu xen kẽ)"

    count_tai = recent.count("tài")
    count_xiu = recent.count("xỉu")
    if count_tai > count_xiu and recent[-1] == "tài":
        return "Xu hướng Tài tăng"
    elif count_xiu > count_tai and recent[-1] == "xỉu":
        return "Xu hướng Xỉu tăng"

    return "Xu hướng không rõ ràng"

# === Lệnh người dùng ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Nếu user đã xác minh - hiển thị game menu
    if is_verified_user(user_id) or is_admin(update.effective_user.id):
        keyboard = []
        for game_name in GAMES.keys():
            keyboard.append([InlineKeyboardButton(GAMES[game_name], callback_data=f"game_{game_name}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "🎮 **Chọn game để dự đoán:**"
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Nếu chưa xác minh - hiển thị nút join nhóm
        keyboard = [
            [InlineKeyboardButton("🐉 CLB Thang Tùng 🐉", url=GROUPS["CLB Thang Tùng 🐉"]["link"])],
            [InlineKeyboardButton("🐉 Chat telegram 🐉", url=GROUPS["Chat telegram 🐉"]["link"])],
            [InlineKeyboardButton("🐉 Share All 🐉", url=GROUPS["Share All 🐉"]["link"])],
            [InlineKeyboardButton("✅ Xác Minh", callback_data="verify_member")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "🎲 **Chào mừng!**\n\n📌 Vui lòng tham gia đầy đủ 3 nhóm sau để sử dụng bot:\n\n✨ Tài Xỉu MD5\n📊 Gửi MD5 để dự đoán\n\n💡 Sau khi tham gia đủ 3 nhóm, click **Xác Minh**"
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def verify_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Kiểm tra tất cả 3 nhóm
    verified_groups = []
    failed_groups = []
    error_groups = []
    
    for group_name, group_info in GROUPS.items():
        try:
            member = await context.bot.get_chat_member(group_info["id"], user_id)
            if member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                verified_groups.append(group_name)
            else:
                failed_groups.append(group_name)
        except Exception as e:
            # Bot không thể access nhóm (có thể do quyền hoặc nhóm riêng tư)
            error_groups.append(group_name)
    
    # Nếu user tham gia đủ 3 nhóm hoặc bot không thể kiểm tra hết (trust user)
    if len(verified_groups) == 3 or (len(verified_groups) > 0 and len(error_groups) > 0):
        add_verified_user(user_id)
        await query.answer("✅ Xác minh thành công!", show_alert=True)
        await query.edit_message_text("✅ **Xác minh thành công!**\n\n🎲 Giờ bạn có thể dùng bot bình thường.\n\n💡 Gửi MD5 để dự đoán!", parse_mode='Markdown')
    elif len(verified_groups) > 0:
        # Hiển thị nhóm chưa tham gia
        msg = f"❌ Bạn mới tham gia {len(verified_groups)}/3 nhóm:\n\n"
        msg += "✅ Đã tham gia:\n"
        for g in verified_groups:
            msg += f"  • {g}\n"
        if failed_groups:
            msg += "\n⚠️ Chưa tham gia:\n"
            for g in failed_groups:
                msg += f"  • {g}\n"
        await query.answer(msg, show_alert=True)
    else:
        # Không thể kiểm tra hoặc chưa tham gia bất kỳ nhóm nào
        msg = "⚠️ Bot không thể kiểm tra membership. Vui lòng đảm bảo bạn đã tham gia cả 3 nhóm:\n\n"
        for group_name in GROUPS.keys():
            msg += f"  • {group_name}\n"
        msg += "\nSau đó click Xác Minh lại!"
        await query.answer(msg, show_alert=True)


async def handle_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    game_name = query.data.replace("game_", "")
    
    if game_name in GAMES:
        current_game[user_id] = game_name
        await query.answer(f"✅ Bạn chọn {GAMES[game_name]}", show_alert=False)
        await query.edit_message_text(f"🎮 **{GAMES[game_name]}**\n\n💬 Gửi mã MD5 để dự đoán:", parse_mode='Markdown')
    else:
        await query.answer("❌ Game không hợp lệ", show_alert=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global adjustment, history, last_prediction
    user_id = str(update.effective_user.id)
    
    # Kiểm tra xem user đã xác minh chưa
    if not is_verified_user(user_id) and not is_admin(int(user_id)):
        await update.message.reply_text("🔐 Bạn cần xác minh trước. Dùng /start để xác minh!")
        return
    
    md5 = update.message.text.strip().lower()
    if not is_valid_md5(md5):
        await update.message.reply_text("❌ MD5 không hợp lệ.")
        return
    tai, xiu = analyze_md5(md5, adjustment)
    prediction = "Tài" if tai > xiu else "Xỉu"
    last_prediction[user_id] = prediction.lower()
    history.append(prediction.lower())
    trend = detect_trend(history)
    game = current_game.get(user_id, "Unknown")
    msg = f"🎮 **{game}**\n\n🔍 MD5: {md5}\n🎯 Tỷ lệ: Tài {tai}%, Xỉu {xiu}%\n👉 Dự đoán: {prediction}\n\n📊 {trend}\n📥 Nhập kết quả thật: /ketqua tài hoặc /ketqua xỉu"
    await update.message.reply_text(msg)

async def handle_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global adjustment, wrong_streak, last_prediction
    user_id = str(update.effective_user.id)
    
    # Kiểm tra xem user đã xác minh chưa
    if not is_verified_user(user_id) and not is_admin(int(user_id)):
        await update.message.reply_text("🔐 Bạn cần xác minh trước. Dùng /start để xác minh!")
        return
    
    if user_id not in last_prediction:
        await update.message.reply_text("❗ Chưa có dự đoán nào.")
        return
    try:
        actual = context.args[0].lower()
        if actual not in ["tài", "xỉu"]:
            raise ValueError
        if actual == last_prediction[user_id]:
            msg = "✅ Đoán đúng!"
            wrong_streak = 0
            adjustment *= 0.9
        else:
            msg = f"❌ Đoán sai! Bot đoán {last_prediction[user_id].upper()}, kết quả là {actual.upper()}."
            wrong_streak += 1
            adjustment += 0.02
        del last_prediction[user_id]
        await update.message.reply_text(f"{msg}\n📈 Điều chỉnh hiện tại: {round(adjustment, 4)}")
    except:
        await update.message.reply_text("❌ Dùng đúng cú pháp: /ketqua tài hoặc /ketqua xỉu")

# === Admin ===
async def create_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền admin.")
        return
    try:
        days = int(context.args[0]) if context.args else 1
    except:
        await update.message.reply_text("⚠️ Dùng: /newkey <số ngày>")
        return
    new_key = secrets.token_hex(4)
    expire = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    keys = load_json(KEY_FILE)
    keys[new_key] = {"used": False, "expire_time": expire}
    save_json(KEY_FILE, keys)
    await update.message.reply_text(f"🔑 Key mới: `{new_key}`\n⏳ Hạn dùng: {expire}", parse_mode='Markdown')

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền admin.")
        return
    verify_history = load_json(VERIFY_HISTORY_FILE)
    users = verify_history.get("verified_users", [])
    if not users:
        await update.message.reply_text("📭 Chưa có người dùng nào xác minh.")
        return
    msg = "📋 Danh sách user đã xác minh:\n\n"
    for uid in users:
        msg += f"👤 User ID: `{uid}`\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

# === Main ===
def main():
    init_admin_and_key()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ketqua", handle_result))
    app.add_handler(CommandHandler("newkey", create_key))
    app.add_handler(CommandHandler("listusers", list_users))
    app.add_handler(CallbackQueryHandler(verify_member, pattern="^verify_member$"))
    app.add_handler(CallbackQueryHandler(handle_game_selection, pattern="^game_"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
