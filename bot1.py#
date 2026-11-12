import telebot
import re
import unicodedata
import time
import datetime
import json
import os
import pymongo  
import random
import html
from telebot.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv 

load_dotenv()

# ======================
# CONFIG (Environment Variables)
# ======================
TOKEN = os.getenv("TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS").split(",")]
DATA_FILE = os.getenv("DATA_FILE")
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL")
MONGO_URI = os.getenv("MONGO_URI")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ======================
# DATABASE SETUP (MongoDB)
# ======================
client = pymongo.MongoClient(MONGO_URI)
db = client['bot_database']
brain_collection = db['brain']

def init_db():
    try:
        client.admin.command('ping')
        brain_collection.create_index("input_text")
        
        # 📌 DB ထဲက ကျန်နေတဲ့ Sticker မှတ်ဉာဏ်ဟောင်းများအားလုံးကို ရှင်းလင်းဖယ်ရှားခြင်း
        deleted_stk = brain_collection.delete_many({"$or": [{"sticker_id": {"$exists": True, "$ne": None}}, {"sticker_id": {"$ne": None}}]} )
        if deleted_stk.deleted_count > 0:
            print(f"🧹 Cleaned up {deleted_stk.deleted_count} old sticker entries from database.")
            
        print("✅ MongoDB Connected Successfully & Index Created!")
    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")

# ======================
# DATA MANAGEMENT (JSON for Settings)
# ======================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    
    data.setdefault("mute_time", 30)
    data.setdefault("strikes", {})
    data.setdefault("extra_words", [])
    data.setdefault("groups", [])
    data.setdefault("users", [])
    data.setdefault("reply_on", True)
    data.setdefault("reply_on_chats", {})
    data.setdefault("warning_text", None)
    data.setdefault("last_ts", {})
    return data

def save_data():
    data["groups"] = list(set(data.get("groups", [])))
    data["users"] = list(set(data.get("users", [])))
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

data = load_data()
BOT_START_TIME = int(time.time())

# ======================
# HELPER FUNCTIONS
# ======================
def is_joined(user_id):
    if user_id in ADMIN_IDS:
        return True
    try:
        member = bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        if member.status not in ['left', 'kicked']:
            return True
    except Exception as e:
        print(f"[DEBUG] force-join check error for user {user_id}: {e}")
    return False

# ======================
# LEARNING SYSTEM (Text Only)
# ======================
def save_to_brain(input_text, reply_text):
    try:
        query = {
            "input_text": input_text.lower().strip(), 
            "reply_text": reply_text
        }
        
        if not brain_collection.find_one(query):
            brain_collection.insert_one(query)
            print(f"✅ မှတ်သားပြီး: {input_text} -> {reply_text}")
    except Exception as e:
        print(f"⚠️ save_to_brain error (Storage ပြည့်နေနိုင်သည်): {e}")

def get_reply(text):
    if not text:
        return None
        
    user_input = text.lower().strip()
    
    try:
        results = list(brain_collection.find({"input_text": user_input}, {"reply_text": 1}))
        if results:
            chosen = random.choice(results)
            return chosen.get("reply_text")
        return None
    except Exception as e:
        print(f"⚠️ get_reply Error: {e}")
        return None

# ======================
# UTILS & BUTTONS
# ======================
def is_clean_text(text):
    if not text: return False
    if len(text) < 1 or len(text) > 150: return False
    if re.search(r'http[s]?://', text) or '@' in text: return False
    return True

def mention(user):
    return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

def strike_key(chat_id, user_id):
    return f"{chat_id}:{user_id}"

def is_admin(chat_id, user_id):
    try:
        if user_id in ADMIN_IDS: return True
        admins = bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except: return False

def parse_time(text):
    unit = text[-1].lower()
    try:
        if unit == 's': return int(text[:-1])
        if unit == 'm': return int(text[:-1]) * 60
        if unit == 'h': return int(text[:-1]) * 3600
        if unit == 'd': return int(text[:-1]) * 86400
        return int(text)
    except: return None

def main_buttons():
    kb = InlineKeyboardMarkup()
    kb.add(
         InlineKeyboardButton(
            "𝐀𝐝𝐝 𝐓𝐨 𝐘𝐨𝐮𝐫 𝐆𝐫𝐨𝐮𝐩",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=s&delete_message+manage_video_chats_message+invite_users")
          )
    kb.row(    
         InlineKeyboardButton("𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url="https://t.me/myanmarbot_music"),
         InlineKeyboardButton(" 𝐒𝐔𝐏𝐏𝐎𝐑𝐓 ", url="https://t.me/myanmar_music_Bot2027")
          )
    kb.row(  
        InlineKeyboardButton("𝟗𝟗𝟗", url="tg://resolve?domain=cores_999&text=𝐑𝐞𝐩𝐥𝐚𝐲_𝐁𝐨𝐭"),
        InlineKeyboardButton("𝐀𝐥𝐥 𝐁𝐎𝐓", url="https://t.me/myanmarbot_music/53")
          )
    return kb

# ======================
# CALLBACK QUERIES
# ======================
@bot.callback_query_handler(func=lambda call: call.data.startswith("unmute:"))
def handle_unmute(call):
    chat_id = call.message.chat.id
    if not is_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Admin များသာ Unmute လုပ်နိုင်ပါသည်။", show_alert=True)
        return
    
    target_id = int(call.data.split(":")[1])
    try:
        bot.restrict_chat_member(chat_id, target_id, 
            permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        bot.edit_message_text(f"✅ {mention(call.from_user)} မှ User ကို Unmute လုပ်ပေးလိုက်ပါပြီ။", chat_id, call.message.message_id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "toggle_reply")
def toggle_reply_callback(call):
    chat_id = call.message.chat.id
    if not is_admin(chat_id, call.from_user.id):
        return bot.answer_callback_query(call.id, "❌ Admin များသာ လုပ်ဆောင်နိုင်ပါသည်။", show_alert=True)
    
    key = str(chat_id)
    current = data.get("reply_on_chats", {}).get(key, True)
    new_status = not current
    data.setdefault("reply_on_chats", {})[key] = new_status
    save_data()

    btn_text = "🟢 𝐁𝐨𝐭 စာပြန်ခြင်း: ON" if new_status else "🔴 𝐁𝐨𝐭 စာပြန်ခြင်း: OFF"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton(btn_text, callback_data="toggle_reply"))

    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id, f"𝐁𝐨𝐭 စာပြန်ခြင်းကို {'ဖွင့်' if new_status else 'ပိတ်'} လိုက်ပါပြီ။")        

# ======================
# ADMIN CONFIG COMMANDS
# ======================
@bot.message_handler(commands=["setmute"])
def set_mute_time(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if message.chat.type == "private":
        if user_id not in ADMIN_IDS: return
    else:
        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status not in ["administrator", "creator"] and user_id not in ADMIN_IDS:
                return bot.reply_to(message, "❌ ဒီ command ကို Group Admin များသာ သုံးနိုင်ပါတယ်။")
        except:
            return

    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Usage: /setmute 30s (or 5m, 1d)")
    
    seconds = parse_time(args[1])
    if seconds is not None:
        if seconds < 30:
            return bot.reply_to(message, "⚠️ Telegram စည်းကမ်းအရ Mute time ကို အနည်းဆုံး 30s ထားပေးရပါမယ်။")
        
        data.setdefault("group_mute_times", {})[str(chat_id)] = seconds
        save_data()
        bot.reply_to(message, f"✅ ဒီ Group အတွက် Mute time ကို {args[1]} အဖြစ် သတ်မှတ်လိုက်ပါပြီ။")
    else:
        bot.reply_to(message, "❌ Invalid format! Use: 30s, 5m, or 1h")

@bot.message_handler(commands=["addword"])
def add_word(message):
    if message.chat.type != "private" or message.from_user.id not in ADMIN_IDS:
        return
    raw = message.text.replace("/addword", "").strip()
    if not raw:
        return bot.reply_to(message, "Usage: /addword <word>")
    norm = unicodedata.normalize('NFKC', raw).lower()
    if norm not in data.get("extra_words", []):
        data.setdefault("extra_words", []).append(norm)
        save_data()
        bot.reply_to(message, f"✅ Added to global ban list: {raw}")
    else:
        bot.reply_to(message, f"ℹ️ '{raw}' already in global ban list.")

@bot.message_handler(commands=["setwarn"])
def set_warning_text(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Admins only.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return bot.reply_to(message, "Usage: /setwarn <warning message>")
    data["warning_text"] = parts[1].strip()
    save_data()
    bot.reply_to(message, f"✅ Warning text updated.")

@bot.message_handler(commands=["getwarn"])
def get_warning_text(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    warn = data.get("warning_text") or "(default message)"
    bot.reply_to(message, f"Current warning text:\n{warn}")

@bot.message_handler(commands=["delword"])
def del_word(message):
    chat_id = message.chat.id
    if message.chat.type == "private":
        if message.from_user.id not in ADMIN_IDS: return
        target = data.setdefault("extra_words", [])
    else:
        if not is_admin(chat_id, message.from_user.id): return
        target = data.setdefault("chat_words", {}).setdefault(str(chat_id), [])

    raw = message.text.replace("/delword", "").strip()
    if not raw:
        return bot.reply_to(message, "Usage: /delword <word>")
    norm = unicodedata.normalize('NFKC', raw).lower()
    if norm in target:
        target.remove(norm)
        save_data()
        bot.reply_to(message, f"✅ Removed from ban list: {raw}")
    else:
        bot.reply_to(message, "❌ Word not found in list.")

@bot.message_handler(commands=["list"])
def list_brain(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split(maxsplit=1)
    mode = args[1].strip().lower() if len(args) > 1 else "words"

    if mode == "brain":
        try:
            all_entries = list(brain_collection.find({}))
        except:
            all_entries = []

        if not all_entries:
            return bot.reply_to(message, "❌ မှတ်ဉာဏ်မှာ ဘာမျှ မရှိသေးပါ။")

        msg = f"<b>📚 မှတ်ဉာဏ်ရှိတဲ့ Entries ({len(all_entries)})</b>\n\n"
        for idx, doc in enumerate(all_entries, 1):
            safe_input = html.escape(doc.get("input_text", "")[:40])
            safe_reply = html.escape(doc.get("reply_text", "")[:35])
            msg += f"<b>{idx}.</b> 💬 <code>{safe_input}</code>\n   ➜ {safe_reply}\n\n"
            if len(msg) > 3500:
                bot.send_message(message.chat.id, msg, parse_mode="HTML")
                msg = ""
        if msg:
            bot.send_message(message.chat.id, msg, parse_mode="HTML")
        return

    gw = data.get("extra_words", [])
    cw = data.get("chat_words", {}).get(str(message.chat.id), [])
    msg = f"<b>📋 Ban Words</b>\nGlobal: {len(gw)} | Chat: {len(cw)}\nTo view brain: /list brain"
    bot.reply_to(message, msg, parse_mode="HTML")

@bot.message_handler(commands=["d"])
def delete_brain_entry(message):
    if message.chat.type not in ["private", "group", "supergroup"]:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "သုံးပုံ: /d 1 (သို့) /d keyword")
    target = args[1].strip()
    
    try:
        all_docs = list(brain_collection.find({}))
        index = int(target)
        if 1 <= index <= len(all_docs):
            brain_collection.delete_one({"_id": all_docs[index - 1]["_id"]})
            return bot.reply_to(message, f"✅ Entry #{index} ကို ဖျက်ပြီးပါပြီ။")
    except ValueError:
        pass
    
    result = brain_collection.delete_many({"input_text": target.lower()})
    if result.deleted_count:
        bot.reply_to(message, f"✅ မှတ်ဉာဏ်ထဲက '{target}' ကို ဖျက်ပြီးပါပြီ။")
    else:
        bot.reply_to(message, f"❌ မတွေ့ပါ။")

@bot.message_handler(commands=["rp"])
def reply_toggle(message):
    chat_id = message.chat.id
    if not is_admin(chat_id, message.from_user.id):
        return bot.reply_to(message, "❌ Admin များသာ လုပ်ဆောင်နိုင်ပါသည်။")
    
    current_status = data.get("reply_on_chats", {}).get(str(chat_id), True)
    new_status = not current_status
    data.setdefault("reply_on_chats", {})[str(chat_id)] = new_status
    save_data()
    
    kb = InlineKeyboardMarkup()
    btn_text = "🟢 𝐁𝐨𝐭 စာပြန်ခြင်း: ON" if new_status else "🔴 𝐁𝐨𝐭 စာပြန်ခြင်း: OFF"
    kb.add(InlineKeyboardButton(btn_text, callback_data="toggle_reply"))
    
    bot.send_message(chat_id, f"<b>𝐁𝐨𝐭 စာပြန်ခြင်း စနစ်ကို {'ဖွင့်' if new_status else 'ပိတ်'} လိုက်ပါပြီ။</b>", 
                     reply_markup=kb, parse_mode="HTML")

# ======================
# BROADCAST SYSTEM (Auto-Cleanup for Blocked/Kicked chats)
# ======================
@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ ဒီ Command ကို Bot Owner သာ သုံးနိုင်ပါတယ်။")
    
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Broadcast ပို့ချင်တဲ့ Message (ပုံ/ဗီဒီယို/စာသား) ကို <b>Reply</b> ထောက်ပြီးမှ ဒီ command ကို သုံးပေးပါ။", parse_mode="HTML")

    target_msg = message.reply_to_message
    all_targets = list(set(data.get("groups", []) + data.get("users", [])))
    
    if not all_targets:
        return bot.reply_to(message, "⚠️ ပို့စရာ Target မရှိသေးပါဘူး။")

    status_msg = bot.reply_to(message, f"🚀 စုစုပေါင်း {len(all_targets)} နေရာကို ပို့နေပါပြီ...")
    
    success = 0
    fail = 0
    removed_chats = []

    for tid in all_targets:
        try:
            bot.forward_message(
                chat_id=tid, 
                from_chat_id=message.chat.id, 
                message_id=target_msg.message_id
            )
            success += 1
            time.sleep(0.1)
        except Exception as e:
            err_str = str(e)
            # 📌 Bot ကို Block လုပ်ထားတာ (သို့) Group ကနေ ထုတ်ထားတာ (Kicked/Forbidden) ဆိုရင် ဖယ်ရှားရန် စာရင်းသွင်းမည်
            if "Forbidden" in err_str or "kicked" in err_str or "chat not found" in err_str or "blocked" in err_str:
                removed_chats.append(tid)
            fail += 1
            continue

    # 🧹 Block လုပ်ထားသော User များနှင့် Kicked ဖြစ်သော Group များကို Database မှ အလိုအလျောက် ဖယ်ရှားခြင်း
    if removed_chats:
        for r_id in removed_chats:
            if r_id in data.get("groups", []):
                data["groups"].remove(r_id)
            if r_id in data.get("users", []):
                data["users"].remove(r_id)
            if str(r_id) in data.get("reply_on_chats", {}):
                del data["reply_on_chats"][str(r_id)]
        save_data()
        print(f"🧹 Cleaned up {len(removed_chats)} blocked/kicked chats from database.")

    bot.edit_message_text(
        f"✅ <b>Broadcast ပို့ပြီးပါပြီ!</b>\n\n🟢 အောင်မြင်: {success}\n🔴 ကျရှုံး: {fail}\n🗑️ ပယ်ဖျက်လိုက်သော ID ဟောင်းများ: {len(removed_chats)} ခု",
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        parse_mode="HTML"
    )

@bot.message_handler(commands=["delgp"])
def del_group(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ Only the bot owner can remove groups.")

    parts = message.text.split()
    if len(parts) == 1:
        gid = message.chat.id
    elif len(parts) == 2:
        try:
            gid = int(parts[1])
        except ValueError:
            return bot.reply_to(message, "⚠️ Chat ID က ကိန်းဂဏန်း ဖြစ်ရပါမယ်။")
    else:
        return bot.reply_to(message, "Usage: /delgp သို့မဟုတ် /delgp <chat_id>")

    if gid not in data.get("groups", []):
        return bot.reply_to(message, "ℹ️ ဒီ Group က စာရင်းထဲမှာ မရှိပါဘူး။")

    data["groups"].remove(gid)
    if str(gid) in data.get("reply_on_chats", {}):
        del data["reply_on_chats"][str(gid)]
    
    save_data()
    bot.reply_to(message, f"✅ Group {gid} ကို စာရင်းထဲကနေ ဖယ်ထုတ်လိုက်ပါပြီ။")

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    if message.chat.type == "private":
        if message.chat.id not in data["users"]:
            data["users"].append(message.chat.id)
            save_data()

        if not is_joined(user_id):
            join_kb = InlineKeyboardMarkup()
            clean_channel = FORCE_JOIN_CHANNEL.replace('@', '')
            join_kb.add(InlineKeyboardButton("𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐣𝐨𝐢𝐧", url=f"https://t.me/{clean_channel}"))
            join_kb.add(InlineKeyboardButton("𝐣𝐨𝐢𝐧(စစ်ဆေးမည်)", url=f"https://t.me/{BOT_USERNAME}?start=start"))
            return bot.send_message(message.chat.id, "❌ ဒီ Bot ကိုသုံးဖို့ Channel ကို အရင် Join ပေးပါ။", reply_markup=join_kb)

    bot.send_message(
        message.chat.id, 
        "<tg-emoji emoji-id='5251299553239398548'>🤖</tg-emoji> <b>𝐀𝐮𝐭𝐨 𝐑𝐞𝐩𝐥𝐲 & 𝐒𝐩𝐚𝐦 𝐥𝐢𝐧𝐤 𝐆𝐫𝐨𝐮𝐩 𝐇𝐞𝐥𝐩 𝐁𝐨𝐭 Online!</b>\n\n"
        "<tg-emoji emoji-id='5240241223632954241'>🚫</tg-emoji> 𝐁𝐢𝐨 / 𝐉𝐨𝐢𝐧 / 𝐋𝐢𝐧𝐤 𝐬𝐩𝐚𝐦 𝐚𝐮𝐭𝐨 𝐝𝐞𝐥𝐞𝐭𝐞\n"
        "<tg-emoji emoji-id='6271786398404055377'>⚠️</tg-emoji> 𝟑 𝐖𝐚𝐫𝐧𝐢𝐧𝐠𝐬 = 𝐀𝐮𝐭𝐨 𝐌𝐮𝐭𝐞\n\n"
        "<tg-emoji emoji-id='5226945370684140473'>➕</tg-emoji> 𝐁𝐨𝐭 ကို 𝐆𝐫𝐨𝐮𝐩 ထဲထည့်ပြီး 𝐀𝐝𝐦𝐢𝐧 ပေးထားပါ။",
        reply_markup=main_buttons()
    )

# ======================
# MESSAGE HANDLER (GUARD & LEARNING & REPLY)
# ======================
BASE_PATTERNS = [
    r"b[\W_]*i[\W_]*o", r"j[\W_]*o[\W_]*i[\W_]*n", r"t[\W_]*\.?[\W_]*m[\W_]*e", 
    r"http", r"www", r"link", r"ဂျိုင်း", r"လင့်ခ်|လင့်|လင့်|လင်ခ်", r"ဘိုင်[\W_]*အို"
]

def strip_accents(s: str) -> str:
    nkfd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nkfd if not unicodedata.category(c).startswith('M'))

def matches_word_in_text(word: str, text: str) -> bool:
    if not word or not text: return False
    pattern = r'\b' + re.escape(word) + r'\b'
    return bool(re.search(pattern, text, flags=re.UNICODE))

@bot.message_handler(content_types=["text", "photo", "sticker", "story", "video", "animation"])
def handle_all(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type in ["group", "supergroup"]:
        if chat_id not in data.get("groups", []):
            data.setdefault("groups", []).append(chat_id)
            data.setdefault("reply_on_chats", {}).get(str(chat_id), True)
            save_data()

    if message.content_type == 'text' and message.text and message.text.startswith('/'):
        return

    if message.chat.type == "private" and user_id not in ADMIN_IDS:
        if not is_joined(user_id):
            return

    # --- 1. SPAM / GUARD CHECK ---
    is_story = (message.content_type == 'story')
    is_forwarded = (message.forward_from is not None) or (message.forward_from_chat is not None)

    check_text = message.text if message.text else message.caption
    norm_text = strip_accents(unicodedata.normalize('NFKC', check_text).lower()) if check_text else ""

    found = False
    if check_text:
        if any(re.search(p, norm_text) for p in BASE_PATTERNS):
            found = True
        else:
            for w in data.get("extra_words", []):
                if matches_word_in_text(w, norm_text):
                    found = True
                    break

    if found or is_story or is_forwarded:
        if not is_admin(chat_id, user_id):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception as e:
                err_str = str(e)
                # 📌 Group ထဲမှာ Bot ကို Kicked လုပ်ထားရင် စာရင်းထဲက ချက်ချင်း ဖြုတ်ထုတ်မည်
                if "Forbidden" in err_str or "kicked" in err_str:
                    if chat_id in data.get("groups", []):
                        data["groups"].remove(chat_id)
                        save_data()
                pass
            
            key = strike_key(chat_id, user_id)
            strikes = data["strikes"].get(key, 0) + 1
            data["strikes"][key] = strikes
            save_data()
            
            if strikes >= 3:
                mute_time = data.get("group_mute_times", {}).get(str(chat_id), data.get("mute_time", 60))
                until_date = int(time.time()) + mute_time
                try:
                    bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(), until_date=until_date)
                except:
                    pass
                kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔓 Unmute", callback_data=f"unmute:{user_id}"))
                bot.send_message(chat_id, f"❌ <b>{mention(message.from_user)}</b> ယာယီ Mute လုပ်လိုက်ပါပြီ။", reply_markup=kb, parse_mode="HTML")
                data["strikes"][key] = 0
                save_data()
            else:
                warn_msg = data.get("warning_text") or f"⚠️ သတိပေးချက် ({strikes}/3): လင့်/ဘိုင်အို/ဂျိုင်း များ ပို့ခွင့်မပြုပါ။"
                bot.send_message(chat_id, warn_msg, parse_mode="HTML")
            return

    # --- 2. LEARNING SYSTEM (Text Reply Only) ---
    if message.reply_to_message and message.reply_to_message.text and message.content_type == 'text':
        parent = message.reply_to_message.text.strip().lower()
        current_reply = message.html_text
        if is_clean_text(current_reply):
            save_to_brain(parent, current_reply)
            return

    # --- 3. REPLY SYSTEM (Exact Match Only) ---
    chat_key = str(chat_id)
    chat_reply_on = data.get("reply_on_chats", {}).get(chat_key, True)

    if message.content_type == 'text' and message.text and chat_reply_on:
        user_input = message.text.lower().strip()
        
        reply_text = get_reply(user_input)
        
        if reply_text:
            try:
                bot.reply_to(message, reply_text, parse_mode=None)
            except Exception as e:
                err_str = str(e)
                # 📌 အကယ်၍ Bot ကို Group ကနေ ထုတ်ထားရင် (Forbidden) စာရင်းထဲက အလိုအလျောက် ဖြုတ်ထုတ်မည်
                if "Forbidden" in err_str or "kicked" in err_str or "chat not found" in err_str:
                    if chat_id in data.get("groups", []):
                        data["groups"].remove(chat_id)
                        if str(chat_id) in data.get("reply_on_chats", {}):
                            del data["reply_on_chats"][str(chat_id)]
                        save_data()
                        print(f"🧹 Auto-removed kicked group {chat_id} from database.")
                print(f"⚠️ Reply error: {e}")

# ======================
# RUN BOT
# ======================
if __name__ == '__main__':
    init_db()
    print("🤖 Clean Reply Bot is starting...")
    while True:
        try:
            bot.infinity_polling(timeout=90, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            print(f"⚠️ Connection Error: {e}")
            time.sleep(5)
