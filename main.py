# -*- coding: utf-8 -*-
import telebot
from telebot import types
import time
import random
import string
import json
import os
import threading
import logging

# --- ТАНЗИМОТ ---
# Токени шумо аллакай дар ин ҷо гузошта шудааст
BOT_TOKEN = "8409397084:AAEDpBJHAoc6UtnVt59e7VMD7I13kR3fSi0"
ADMIN_ID = 5873962867
USER_DATA_FILE = "final_boss_users_v1_1.json"
GLOBAL_DATA_FILE = "final_boss_global_v1_1.json"

# Системаи ҷоизаҳо
WINNING_NUMBERS = {
    10: {"prize": 5.0, "usd_equiv": 0.03}, 30: {"prize": 6.33, "usd_equiv": 0.04},
    100: {"prize": 12.0, "usd_equiv": 0.07}, 200: {"prize": 1.0, "usd_equiv": 0.006},
    260: {"prize": 4.0, "usd_equiv": 0.024}, 380: {"prize": 12.0, "usd_equiv": 0.07},
    509: {"prize": 2.0, "usd_equiv": 0.012}
}
MAX_KEYS_DISPLAY = 5
BOOST_SPEED = 0.9

# Танзимоти устуворӣ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = telebot.TeleBot(BOT_TOKEN)
file_lock = threading.Lock()

# --- ИДОРАКУНИИ БЕХАТАРИ МАЪЛУМОТ ---
def load_data(filename, default_data={}):
    with file_lock:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                try: return json.load(f)
                except json.JSONDecodeError: return default_data
        return default_data

def save_data(filename, data):
    with file_lock:
        with open(filename, 'w') as f: json.dump(data, f, indent=4)

def generate_random_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=48))

# --- ФУНКСИЯИ АСОСИИ ЭҶОДИ ИНТЕРФЕЙС ---
def build_scanner_interface(user_id):
    try:
        user_data = load_data(USER_DATA_FILE)
        user_info = user_data.get(str(user_id), {})
        
        personal_scans = user_info.get("personal_scans", 0)
        balance = user_info.get("balance", 0)
        last_keys = user_info.get("last_keys", [])
        is_scanning = user_info.get("scanning", False)
        
        temp = random.randint(10, 90)
        header_text = f"<code>/////{personal_scans}[Skaner]_/------[{temp}°]------\\✓\\\\\\\\</code>"
        
        base_price = 0.00000436
        fluctuation_range = base_price * 0.05 
        fluctuation = random.uniform(-fluctuation_range, fluctuation_range)
        current_price = base_price + fluctuation
        price_change_percent = (fluctuation / base_price) * 100
        price_ticker = f"<code>$PER: {current_price:.8f}{'📈' if price_change_percent >= 0 else '📉'} ({price_change_percent:+.2f}%)</code>"

        keys_text_list = [f"<code>{key}</code>" for key in last_keys]
        keys_text = "\n".join(keys_text_list)
        footer_text = f"<code>Found=[ \"{balance:.2f} $PER\" ]</code>"
        
        full_text = (
            f"{header_text}\n"
            f"{price_ticker}\n"
            "<code>-------------------------------------------------</code>\n"
            f"{keys_text}\n"
            "<code>________________________________________</code>\n"
            f"{footer_text}\n"
            "<code>________________________________________</code>"
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        action_button = types.InlineKeyboardButton("🛑 Stop", callback_data="stop_boost") if is_scanning else types.InlineKeyboardButton("🚀 Boost", callback_data="start_boost")
        markup.add(action_button)
        
        for key_string in last_keys:
            if "✓[Withdraw]✓" in key_string:
                scan_num_str = key_string.split('[')[0]
                markup.add(types.InlineKeyboardButton(f"✓ Withdraw {scan_num_str} ✓", callback_data=f"withdraw_{scan_num_str}"))

        return full_text, markup
    except Exception as e:
        logging.error(f"Error in build_scanner_interface: {e}")
        return "Хатогӣ дар сохтани интерфейс.", types.InlineKeyboardMarkup()

# --- СИКЛИ СКАНЕР ДАР ПАТОКИ АЛОҲИДА ---
def scanner_thread(message_id, chat_id, user_id):
    wipe_line = "█" * 58
    while True:
        try:
            user_data = load_data(USER_DATA_FILE)
            user_info = user_data.get(str(user_id), {})
            if not user_info.get("scanning", False): break

            global_data = load_data(GLOBAL_DATA_FILE, {"scan_count": 0})
            global_data["scan_count"] += 1
            current_global_scan = global_data["scan_count"]
            
            user_info["personal_scans"] = user_info.get("personal_scans", 0) + 1
            new_key = f"{user_info['personal_scans']}[key]:{generate_random_key()}"
            
            win_info = WINNING_NUMBERS.get(current_global_scan)
            if win_info:
                prize = win_info["prize"]
                usd = win_info["usd_equiv"]
                user_info["balance"] = user_info.get("balance", 0) + prize
                new_key += f" PER[{prize:.2f}][{usd:.2f}$] ✓[Withdraw]✓"
            else:
                new_key += f" PER[0]{'_' * random.randint(1, 5)}"

            last_keys = user_info.setdefault("last_keys", [])
            if len(last_keys) >= MAX_KEYS_DISPLAY:
                last_keys.pop(0)
                last_keys.insert(0, wipe_line)
                text, markup = build_scanner_interface(user_id)
                try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
                except telebot.apihelper.ApiTelegramException: pass
                time.sleep(0.4)
                last_keys.pop(0)
            
            last_keys.append(new_key)
            save_data(USER_DATA_FILE, user_data)
            save_data(GLOBAL_DATA_FILE, global_data)
            
            text, markup = build_scanner_interface(user_id)
            try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
            except telebot.apihelper.ApiTelegramException as e:
                if 'message is not modified' not in str(e): logging.warning(e)
            
            time.sleep(BOOST_SPEED)
        except Exception as e:
            logging.error(f"Critical error in scanner_thread for user {user_id}: {e}")
            time.sleep(5)

# --- КОРКАРДКУНАНДАҲОИ БОТ ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    try:
        user_id = str(message.from_user.id)
        user_data = load_data(USER_DATA_FILE)
        
        if user_id not in user_data:
            user_data[user_id] = {"balance": 0, "personal_scans": 0, "last_keys": [], "scanning": False}
            save_data(USER_DATA_FILE, user_data)
            bot.send_message(message.chat.id, "✅ **Табрик!** Шумо бомуваффақият сабти ном шудед.\nИн кафолат медиҳад, ки токенҳои ёфтаи шумо ҳеҷ гоҳ гум намешаванд.", parse_mode="Markdown")
            time.sleep(1)

        text, markup = build_scanner_interface(int(user_id))
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error in start_handler: {e}")
        bot.send_message(message.chat.id, "Хатогӣ рух дод. Лутфан, баъдтар кӯшиш кунед.")

@bot.callback_query_handler(func=lambda call: call.data in ['start_boost', 'stop_boost'])
def boost_control_callback(call):
    try:
        user_id = str(call.from_user.id)
        user_data = load_data(USER_DATA_FILE)
        user_info = user_data.get(user_id, {})

        if call.data == 'start_boost':
            if user_info.get("scanning", False):
                return bot.answer_callback_query(call.id, "❌ Сканер аллакай кор карда истодааст!")
            user_info["scanning"] = True
            save_data(USER_DATA_FILE, user_data)
            thread = threading.Thread(target=scanner_thread, args=(call.message.message_id, call.message.chat.id, call.from_user.id))
            thread.start()
            bot.answer_callback_query(call.id, "🚀 Boost оғоз шуд!")
        elif call.data == 'stop_boost':
            user_info["scanning"] = False
            save_data(USER_DATA_FILE, user_data)
            bot.answer_callback_query(call.id, "🛑 Boost боздошта шуд.")

        text, markup = build_scanner_interface(call.from_user.id)
        try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except telebot.apihelper.ApiTelegramException as e:
            if 'message is not modified' not in str(e): logging.warning(e)
    except Exception as e:
        logging.error(f"Error in boost_control_callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_'))
def withdraw_callback(call):
    try:
        scan_num_str = call.data.split('_')[1]
        user = call.from_user
        admin_message = (
            f"🚨 **Дархости Нав барои Гирифтани Ҷоиза!** 🚨\n\n"
            f"👤 **Корбар:** {user.first_name} (ID: `{user.id}`)\n"
            f"🔢 **Рақами Скан (шахсӣ):** {scan_num_str}\n"
            f"💰 **Ҷоиза:** (Лутфан, аз рӯи рақами скан дар базаи маълумот тафтиш кунед)"
        )
        bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "✅ Дархости шумо ба админ фиристода шуд!", show_alert=True)
    except Exception as e:
        logging.error(f"Error in withdraw_callback: {e}")
        bot.answer_callback_query(call.id, "Хатогӣ дар фиристодани дархост.", show_alert=True)

# --- БА КОР ДАРОВАРДАНИ БОТИ УСТУВОР ---
if __name__ == '__main__':
    logging.info("Token Hunter Pro (Final Boss v1.1) is starting...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as e:
            logging.error(f"Bot polling failed with error: {e}. Restarting in 5 seconds...")
            time.sleep(5)
￼Enter
