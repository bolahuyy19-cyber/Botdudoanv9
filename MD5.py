# -*- coding: utf-8 -*-
import telebot
from telebot import types
import json
import time
import os
import hashlib

# ================== CONFIG ==================
TOKEN = "8315041903:AAEZfE8z8CNfUm44c1S457lv1-7zfq-2hM0"
ADMIN_ID = "7071414779"
DATA_FILE = "user_data.json"

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# ================== DATA HANDLING ==================
def load_user_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi khi tải dữ liệu người dùng: {e}")
        return {}

def save_user_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi khi lưu dữ liệu người dùng: {e}")

user_data = load_user_data()

def get_balance(chat_id):
    return user_data.get(chat_id, {}).get("balance", 0)

def update_balance(chat_id, amount):
    if chat_id not in user_data:
        user_data[chat_id] = {"balance": 0}
    user_data[chat_id]["balance"] += amount
    save_user_data()

# ================== CUSTOM PREDICTION ==================
def custom_predict(md5):
    try:
        pos = [2, 4, 1, 4, 13, 6, 5, 18]
        values = [int(md5[i], 26) for i in pos]
        total = sum(values)
        result = "Xỉu" if total % 2 == 0 else "Tài"
        return f"🎲 *KẾT QUẢ:* `{result}`"
    except Exception as e:
        print(f"Lỗi phân tích MD5: {e}")
        return "⚠️ *Lỗi:* Mã MD5 không hợp lệ!"

# ================== GAME MENU ==================
games = {
    "68GAMEBAI": "✨ Bạn đã chọn *68GAMEBAI* - Gửi mã MD5 để phân tích!",
    "HITCLUB": "🔥 Bạn đã chọn *HITCLUB*! Nhập mã MD5:",
    "B52": "💣 Bạn đã chọn *B52*! Gửi mã MD5:",
    "LUCK8": "🍀 Bạn đã chọn *LUCK8*! Nhập mã MD5 để bắt đầu:",
    "go88": "🔰 Bạn đã chọn *go88* - Gửi mã MD5 để phân tích!",
    "iwin": "🔱 Bạn đã chọn *iwin* - Gửi mã MD5 để phân tích!"
}

@bot.message_handler(commands=['start'])
def handle_start(msg):
    cid = str(msg.chat.id)
    if cid not in user_data:
        user_data[cid] = {"balance": 0}
        save_user_data()
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton(text=game) for game in games]
    buttons += [types.KeyboardButton("Bảng Giá Xu"), types.KeyboardButton("Liên Hệ Admin")]
    kb.add(*buttons)
    message = (
        "🔹 *CHÀO MỪNG BẠN ĐẾN VỚI BOT DỰ ĐOÁN MD5 NHÓM LẤY KEY (https://t.me/+D3RxtnBmm_40MjZl)*\n\n"
        "🏡 Chọn game để bắt đầu\n"
        "🚀 Mỗi lần dự đoán tốn 1 xu\n"
        "🎉 Dự đoán nhanh chóng, chính xác cao"
    )
    bot.send_message(cid, message, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in games)
def handle_game_choice(msg):
    bot.send_message(msg.chat.id, games[msg.text])

@bot.message_handler(commands=['balance'])
def handle_balance(msg):
    balance = get_balance(str(msg.chat.id))
    bot.send_message(msg.chat.id, f"💰 *Số dư hiện tại:* `{balance}` xu")

@bot.message_handler(commands=["cap"])
def handle_addcoins(msg):
    if str(msg.from_user.id) != ADMIN_ID:
        return bot.send_message(msg.chat.id, "🚫 Bạn không có quyền.")
    try:
        _, uid, amount = msg.text.split()
        update_balance(uid, int(amount))
        bot.send_message(msg.chat.id, f"✅ Đã cộng `{amount}` xu cho `{uid}`")
        bot.send_message(uid, f"🏰 Bạn nhận được `{amount}` xu!")
    except Exception as e:
        print(f"Lỗi lệnh /cap: {e}")
        bot.send_message(msg.chat.id, "⚠️ Cú pháp sai. /cap user_id số_xu")

@bot.message_handler(func=lambda m: len(m.text) == 32 and all(c in "0123456789abcdef" for c in m.text))
def handle_md5(msg):
    cid = str(msg.chat.id)
    if get_balance(cid) <= 0:
        return bot.send_message(cid, "🚫 *Không đủ xu! Liên hệ admin để nạp.*")

    update_balance(cid, -1)
    bot.send_message(cid, "⏳ *Đang phân tích...*")
    result = custom_predict(msg.text)
    now = time.strftime("%H:%M:%S", time.localtime())

    res = (f"🔍 *Mã MD5:* `{msg.text}`\n" +
           result + f"\n🕒 *Thời gian:* `{now}`\n💰 *Số xu còn lại:* `{get_balance(cid)}`")
    bot.send_message(cid, res)

@bot.message_handler(func=lambda m: m.text == "Bảng Giá Xu")
def handle_price(msg):
    bot.send_message(msg.chat.id,
        "💸 *BẢNG GIÁ XU*\n\n"
        "🌟 50k = 50 xu\n"
        "🌟 80K = 100 xu (KM 10 xu)\n"
        "🌟 150K = 200 xu (KM 23 xu)\n"
        "🌟 300K = 2222 xu (KM 50 xu)\n\n"
        "📢 Liên hệ admin để mua xu!"
    )

@bot.message_handler(func=lambda m: m.text == "Liên Hệ Admin")
def handle_contact(msg):
    bot.send_message(msg.chat.id, "📞 *Liên hệ:* t.me/@thanhtungs20")

# ================== CHẠY BOT ==================
while True:
    try:
        print("Bot đang chạy🥰...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        time.sleep(2)