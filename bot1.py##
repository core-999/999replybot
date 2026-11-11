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
# CONFIG (Environment Variables ကနေ ယူမယ်)
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
# MongoDB နဲ့ ချိတ်ဆက်မယ်
client = pymongo.MongoClient(MONGO_URI)
db = client['bot_database']
brain_collection = db['brain']

def init_db():
    try:
        client.admin.command('ping')
        print("✅ MongoDB Connected Successfully!")
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
    
    # Default values များ သတ်မှတ်ခြင်း
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
    # Duplicate တွေ ဖယ်ထုတ်ခြင်း
    data["groups"] = list(set(data.get("groups", [])))
    data["users"] = list(set(data.get("users", [])))
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ဒေတာတွေကို စတင် load လုပ်မယ်
data = load_data()

# Bot startup time မှတ်မယ်
BOT_START_TIME = int(time.time())

# ======================
# HELPER FUNCTIONS
# ======================
def is_joined(user_id):
    # Owner ဆိုရင် အလိုအလျောက် pass ဖြစ်မယ်
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
# DATABASE (Learning System) - MongoDB Version
# ======================
def init_db():
    # MongoDB collection is created automatically on first insert
    pass

def save_data():
    # ဒီ function က အရင်အတိုင်းပဲ ထားပါ
    pass

def save_to_brain(input_text, reply_text, sticker_id):
    try:
        # အဖြေတူတာ ရှိမရှိ အရင်စစ်မယ် (စာသားရော အဖြေရော တူနေရင် ထပ်မသိမ်းဖို့)
        query = {
            "input_text": input_text.lower().strip(), 
            "reply_text": reply_text, 
            "sticker_id": sticker_id
        }
        
        if not brain_collection.find_one(query):
            brain_collection.insert_one(query)
            print(f"✅ အဖြေအသစ် တိုးမှတ်သားပြီး: {input_text} -> {reply_text if reply_text else 'Sticker'}")
    except Exception as e:
        print(f"⚠️ save_to_brain error: {e}")

def get_reply(text):
    if not text:
        return None, None
        
    user_input = text.lower().strip()
    
    try:
        # ၁။ input_text နဲ့ ကိုက်ညီတဲ့ အဖြေအားလုံးကိုပဲ သီးသန့်ဆွဲထုတ်မယ် (ဒါက ပိုမြန်တယ်)
        results = list(brain_collection.find({"input_text": user_input}))
        
        if results:
            # ၂။ အဖြေတွေ အများကြီးရှိရင် တစ်ခုကို Random (ကျဘန်း) ရွေးမယ်
            # ဒါမှ စာသားတွေ မထပ်တော့မှာပါ
            chosen = random.choice(results)
            print(f"🎯 Found {len(results)} replies for '{user_input}', chose one randomly.")
            return chosen.get("reply_text"), chosen.get("sticker_id")
            
        return None, None
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return None, None
    
    print(f"[DEBUG] Total docs in database: {len(all_docs)}")
    
    user_input = text.lower().strip()
    possible_matches = []
    
    for idx, doc in enumerate(all_docs):
        db_input = doc.get("input_text")
        db_reply = doc.get("reply_text")
        db_sticker = doc.get("sticker_id")
        if db_input:
            db_input_clean = db_input.lower().strip()
            is_sticker_key = len(db_input_clean) > 50
            
            # စတစ်ကာ ID ဆိုရင် အတိအကျတူမှ (ID က ရှည်လို့ပါ)
            if is_sticker_key:
                match = db_input_clean == user_input
                print(f"[DEBUG] Row {idx} STICKER: match={match}, has_reply_text={db_reply is not None}, has_sticker_id={db_sticker is not None}")
                if match:
                    print(f"[DEBUG] ✅✅ STICKER MATCH FOUND! Will return reply_sticker={db_sticker is not None})")
                    possible_matches.append((db_reply, db_sticker))
            # စာသားဆိုရင် အကြောင်းအရင်းတိကျစေဖို့ whole-word match သာ အသုံး
            else:
                try:
                    # For short text, do exact match first, then word-boundary match
                    if db_input_clean == user_input:
                        possible_matches.append((db_reply, db_sticker))
                    else:
                        pattern = r"\b" + re.escape(db_input_clean) + r"\b"
                        if re.search(pattern, user_input):
                            possible_matches.append((db_reply, db_sticker))
                except:
                    if db_input_clean in user_input:
                        possible_matches.append((db_reply, db_sticker))
    
    # အဖြေရှိရင် Random တစ်ခု ရွေးမယ်
    if possible_matches:
        print(f"[DEBUG] Found {len(possible_matches)} match(es), selecting random one...")
        selected = random.choice(possible_matches)
        print(f"[DEBUG] Selected reply: reply_text={selected[0] is not None}, sticker_id={selected[1] is not None}")
        return selected
    
    print(f"[DEBUG] 🔍 No matches found in database")
    return None, None

# ======================
# UTILS & BUTTONS
# ======================
def is_clean_text(text):
    if not text: return False
    
    # စာလုံးရေ ၁ လုံးအောက် သို့မဟုတ် ၁၅၀ ထက်များရင် မမှတ်ဘူး
    if len(text) < 1 or len(text) > 150: 
        return False
        
    # Link တွေ၊ @ ပါရင် မမှတ်ဘူး
    if re.search(r'http[s]?://', text) or '@' in text: 
        return False
        
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
# UNMUTE CALLBACK (Function အသစ်)
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
    # Toggle per-chat setting
    key = str(chat_id)
    current = data.get("reply_on_chats", {}).get(key, data.get("reply_on", True))
    new_status = not current
    data.setdefault("reply_on_chats", {})[key] = new_status
    save_data()

    btn_text = "🟢 𝐁𝐨𝐭 စာပြန်ခြင်း: ON" if new_status else "🔴 𝐁𝐨𝐭 စာပြန်ခြင်း: OFF"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton(btn_text, callback_data="toggle_reply"))

    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=kb)
    except Exception:
        # ignore edit errors (message may be non-editable)
        pass
    bot.answer_callback_query(call.id, f"𝐁𝐨𝐭 စာပြန်ခြင်းကို {'ဖွင့်' if new_status else 'ပိတ်'} လိုက်ပါပြီ။")        

# ======================
# ADMIN CONFIG COMMANDS
# ======================
@bot.message_handler(commands=["setmute"])
def set_mute_time(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # ၁။ Private Chat မှာဆိုရင် Bot Admin ပဲ ရရမယ်
    if message.chat.type == "private":
        if user_id not in ADMIN_IDS: return
    else:
        # ၂။ Group မှာဆိုရင် Group Admin ဖြစ်ရမယ် (သို့မဟုတ်) Bot Owner ဖြစ်ရမယ်
        try:
            member = bot.get_chat_member(chat_id, user_id)
            is_group_admin = member.status in ["administrator", "creator"]
            if not is_group_admin and user_id not in ADMIN_IDS:
                return bot.reply_to(message, "❌ ဒီ command ကို Group Admin များသာ သုံးနိုင်ပါတယ်။")
        except Exception as e:
            print(f"Error checking admin status: {e}")
            return

    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Usage: /setmute 30s (or 5m, 1d)")
    
    seconds = parse_time(args[1])
    if seconds is not None:
        if seconds < 30:
            return bot.reply_to(message, "⚠️ Telegram စည်းကမ်းအရ Mute time ကို အနည်းဆုံး 30s ထားပေးရပါမယ်။")
        
        # ၃။ Group ID အလိုက် Mute Time ကို သိမ်းဆည်းမယ်
        if "group_mute_times" not in data:
            data["group_mute_times"] = {}
        
        data["group_mute_times"][str(chat_id)] = seconds
        save_data()
        
        bot.reply_to(message, f"✅ ဒီ Group အတွက် Mute time ကို {args[1]} ({seconds} seconds) အဖြစ် သတ်မှတ်လိုက်ပါပြီ။")
    else:
        bot.reply_to(message, "❌ Invalid format! Use: 30s, 5m, or 1h")
        
@bot.message_handler(commands=["addword"])
def add_word(message):
    # owner-only global word addition (only in private chat)
    if message.chat.type != "private" or message.from_user.id not in ADMIN_IDS:
        return
    raw = message.text.replace("/addword", "").strip()
    if not raw:
        return bot.reply_to(message, "Usage: /addword &lt;word&gt;")
    norm = _normalize_text_for_match(raw)
    if not norm or len(norm) < 1:
        return bot.reply_to(message, "⚠️ စကားလုံး အနည်းဆုံး 2 လုံး ရှိရပါမည်။")
    if norm and norm not in data.get("extra_words", []):
        data.setdefault("extra_words", []).append(norm)
        save_data()
        bot.reply_to(message, f"✅ Added to global ban list: {raw}")
    else:
        bot.reply_to(message, f"ℹ️ '{raw}' already in global ban list.")

# ======================
# CUSTOM WARNING MESSAGE
# ======================
@bot.message_handler(commands=["setwarn"])
def set_warning_text(message):
    """Owner/admins can change the short guard warning text shown when a violation is detected."""
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Admins only.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return bot.reply_to(message, "Usage: /setwarn <warning message>")
    data["warning_text"] = parts[1].strip()
    save_data()
    bot.reply_to(message, f"✅ Warning text updated.")

@bot.message_handler(commands=["setword"])
def set_chat_word(message):
    # add a word to the current chat's whitelist/ban list
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Admins only")
    raw = message.text.replace("/setword", "").strip()
    if not raw:
        return bot.reply_to(message, "Usage: /setword &lt;word&gt;")
    norm = _normalize_text_for_match(raw)
    if not norm or len(norm) < 2:
        return bot.reply_to(message, "⚠️ စကားလုံး အနည်းဆုံး 2 လုံး ရှိရပါမည်။")
    lst = data.setdefault("chat_words", {}).setdefault(str(message.chat.id), [])
    if norm not in lst:
        lst.append(norm)
        save_data()
        bot.reply_to(message, f"✅ Added '{raw}' to this chat's ban list.")
    else:
        bot.reply_to(message, f"ℹ️ '{raw}' already in this chat's ban list.")


@bot.message_handler(commands=["getwarn"])
def get_warning_text(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    warn = data.get("warning_text") or "(default message)"
    bot.reply_to(message, f"Current warning text:\n{warn}")

@bot.message_handler(commands=["delword"])
def del_word(message):
    # remove from global or chat-specific list
    chat_id = message.chat.id
    if message.chat.type == "private":
        if message.from_user.id not in ADMIN_IDS:
            return
        target = data.setdefault("extra_words", [])
    else:
        if not is_admin(chat_id, message.from_user.id):
            return
        target = data.setdefault("chat_words", {}).setdefault(str(chat_id), [])

    raw = message.text.replace("/delword", "").strip()
    if not raw:
        return bot.reply_to(message, "Usage: /delword &lt;word&gt;")
    norm = _normalize_text_for_match(raw)
    if norm in target:
        target.remove(norm)
        save_data()
        bot.reply_to(message, f"✅ Removed from ban list: {raw}")
    else:
        bot.reply_to(message, "❌ Word not found in list.")

# ...existing code...

# ======================
# LIST BRAIN ENTRIES COMMAND (with Sticker ID display)
# ======================
@bot.message_handler(commands=["list"])
def list_brain(message):
    """Two-mode /list command:
    - `/list` (default) shows ban words (/addword global + chat-specific)
    - `/list brain` shows saved brain replies (legacy behaviour)
    - If replying to a sticker: shows brain entries for that sticker
    """
    # only owner can use
    if message.from_user.id not in ADMIN_IDS:
        return
    print(f"[DEBUG] /list command called: text={message.text}")
    if message.chat.type not in ["private", "group", "supergroup"]:
        return

    args = message.text.split(maxsplit=1)
    mode = args[1].strip().lower() if len(args) > 1 else "words"

    # If user replied to a sticker always show brain entries for that sticker
    if message.reply_to_message and message.reply_to_message.sticker:
        sticker_id = message.reply_to_message.sticker.file_id
        try:
            results = list(brain_collection.find({"sticker_id": sticker_id}, {"_id": 1, "input_text": 1}))
        except Exception as e:
            print(f"Error fetching sticker entries: {e}")
            results = []

        if results:
            safe_sticker = html.escape(sticker_id)
            msg = f"<b>🎯 Sticker ID:</b>\n<code>{safe_sticker}</code>\n\n<b>ဒီ sticker မှတ်ထားတွေ:</b>\n"
            for doc in results:
                rowid = str(doc["_id"])
                input_text = doc.get("input_text")
                safe_input = html.escape(input_text[:50]) if input_text else ""
                msg += f"• <code>{safe_input}</code>\n"
            msg += f"\n✂️ ဖျက်ချိုင်း: /d {safe_sticker}"
            bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_to_message_id=message.message_id)
            return
        else:
            bot.send_message(message.chat.id, "ဒီ sticker မှတ်ထားတွေ မရှိပါ။", reply_to_message_id=message.message_id)
            return

    # Mode: brain -> list DB replies
    if mode == "brain":
        try:
            all_entries = list(brain_collection.find({}))
        except Exception as e:
            print(f"Error fetching brain entries: {e}")
            all_entries = []

        if not all_entries:
            bot.send_message(message.chat.id, "❌ မှတ်ဉာဏ်မှာ ဘာမျှ မရှိသေးပါ။", reply_to_message_id=message.message_id)
            return

        msg = f"<b>📚 မှတ်ဉာဏ်ရှိတဲ့ Entries ({len(all_entries)})</b>\n\n"
        for idx, doc in enumerate(all_entries, 1):
            rowid = str(doc["_id"])
            input_text = doc.get("input_text")
            reply_text = doc.get("reply_text")
            sticker_id = doc.get("sticker_id")
            safe_input = html.escape(input_text[:40]) if input_text else ""
            if sticker_id:
                msg += f"<b>{idx}.</b> 📌 <code>{safe_input}</code>\n   ➜ 🎭 Sticker\n\n"
            else:
                reply_preview = html.escape(reply_text[:35]) if reply_text else "[Empty]"
                msg += f"<b>{idx}.</b> 💬 <code>{safe_input}</code>\n   ➜ {reply_preview}\n\n"
            if len(msg) > 3500:
                try:
                    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_to_message_id=message.message_id)
                except Exception as e:
                    print(f"[DEBUG] Error sending list: {e}")
                msg = ""

        help_msg = "\n<b>🗑️ ဖျတ်ချချန် နည်းလမ်း:</b>\n/d 1  -  /d hello  -  Sticker ➜ reply then /list"
        if msg:
            bot.send_message(message.chat.id, msg + help_msg, parse_mode="HTML", reply_to_message_id=message.message_id)
        else:
            bot.send_message(message.chat.id, help_msg, parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    # Default mode: show ban words (global + chat-specific)
    gw = data.get("extra_words", [])
    cw = data.get("chat_words", {}).get(str(message.chat.id), [])

    msg = f"<b>📋 Ban Words</b>\n\n"
    msg += f"<b>Global ({len(gw)}):</b>\n"
    if gw:
        for w in gw:
            msg += f"• <code>{html.escape(w)}</code>\n"
    else:
        msg += "(No global ban words)\n"

    msg += f"\n<b>This chat ({len(cw)}):</b>\n"
    if cw:
        for w in cw:
            msg += f"• <code>{html.escape(w)}</code>\n"
    else:
        msg += "(No chat-specific ban words)\n"

    msg += "\n<b>Use:</b> /addword &lt;word&gt; (owner private), /setword &lt;word&gt; (group admin), /delword &lt;word&gt;\n"
    msg += "To view saved replies: /list brain"

    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_to_message_id=message.message_id)

# ======================
# DELETE BRAIN ENTRY COMMAND
# ======================
@bot.message_handler(commands=["d"])
def delete_brain_entry(message):
    if message.chat.type not in ["private", "group", "supergroup"]:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "သုံးပုံ:\n/d နံပါတ် - /d 1\n/d စာလုံး - /d hello\n/d sticker_id - /d CAACAgIA...")
    target = args[1].strip()
    
    deleted = 0
    
    # Try as index/number
    try:
        all_docs = list(brain_collection.find({}))
        index = int(target)
        if 1 <= index <= len(all_docs):
            doc = all_docs[index - 1]
            result = brain_collection.delete_one({"_id": doc["_id"]})
            deleted = result.deleted_count
        if deleted:
            bot.reply_to(message, f"✅ Entry #{index} ကို ဖျက်ပြီးပါပြီ။")
        else:
            bot.reply_to(message, f"❌ Entry #{index} မတွေ့ပါ။")
        return
    except ValueError:
        pass
    
    # Try as text input_text or sticker_id
    target_lower = target.lower()
    try:
        result = brain_collection.delete_many({"$or": [{"input_text": target_lower}, {"sticker_id": target}]})
        deleted = result.deleted_count
    except Exception as e:
        print(f"Error deleting: {e}")
        deleted = 0
    
    if deleted:
        bot.reply_to(message, f"✅ မှတ်ဉာဏ်ထဲက '{target}' ကို ဖျက်ပြီးပါပြီ။ ({deleted} entry)")
    else:
        bot.reply_to(message, f"❌ '{target}' ဆိုတာ မတွေ့ပါ။")

@bot.message_handler(commands=["rp"])
def reply_toggle(message):
    chat_id = message.chat.id
    if not is_admin(chat_id, message.from_user.id):
        return bot.reply_to(message, "❌ Admin များသာ ဤ Setting ကို ပြောင်းလဲနိုင်ပါသည်။")
    
    # လက်ရှိ Status ကို စစ်မယ် (Default: ON)
    current_status = data.get("reply_on_chats", {}).get(str(chat_id), True)
    new_status = not current_status
    
    # Update and save immediately
    data.setdefault("reply_on_chats", {})[str(chat_id)] = new_status
    save_data()
    
    print(f"[DEBUG] /rp toggled in {chat_id}: {current_status} -> {new_status}")
    
    kb = InlineKeyboardMarkup()
    btn_text = "🟢 𝐁𝐨𝐭 စာပြန်ခြင်း: ON" if new_status else "🔴 𝐁𝐨𝐭 စာပြန်ခြင်း: OFF"
    kb.add(InlineKeyboardButton(btn_text, callback_data="toggle_reply"))
    
    bot.send_message(chat_id, f"<tg-emoji emoji-id='5251299553239398548'>🤖</tg-emoji> <b>𝐁𝐨𝐭 စာပြန်ခြင်း စနစ်ကို {'ဖွင့်' if new_status else 'ပိတ်'} လိုက်ပါပြီ།</b>\n\n{btn_text}", 
                     reply_markup=kb, parse_mode="HTML")        

@bot.message_handler(commands=["id"])
def show_chat_id(message):
    # replies with the current chat's ID
    chat = message.chat
    bot.reply_to(message, f"Chat ID: {chat.id}")


@bot.message_handler(commands=["astk"])  # delete all sticker memories
def delete_all_sticker_memory(message):
    # only bot owner(s) can run this
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ ဒီ command ကို Bot Owner သာ အသုံးပြုနိုင်ပါသည်။")

    try:
        count = brain_collection.count_documents({"sticker_id": {"$ne": None, "$ne": ""}})
        result = brain_collection.delete_many({"sticker_id": {"$ne": None, "$ne": ""}})
        deleted_count = result.deleted_count
        bot.reply_to(message, f"✅ Sticker memory များကို ဖျက်ပြီးပါပြီ — {deleted_count} entries ဖျက်ပြီးပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ ဖျက်ပေးစရာအမှားတက်ပါသည်: {e}")

# ======================
# BROADCAST
# ======================
@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    # ၁။ Admin ဟုတ်မဟုတ် အရင်စစ်မယ်
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ ဒီ Command ကို Bot Owner သာ သုံးနိုင်ပါတယ်။")
    
    # ၂။ ပို့မယ့် Message ကို ယူမယ် (Reply ထောက်ထားတဲ့ message ကို copy ကူးမှာပါ)
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Broadcast ပို့ချင်တဲ့ Message (ပုံ/ဗီဒီယို/စာသား) ကို <b>Reply</b> ထောက်ပြီးမှ ဒီ command ကို သုံးပေးပါ။", parse_mode="HTML")

    target_msg = message.reply_to_message
    
    # ၃။ ပို့ရမယ့် Target IDs
    all_targets = list(set(data.get("groups", []) + data.get("users", [])))
    
    if not all_targets:
        return bot.reply_to(message, "⚠️ ပို့စရာ Target မရှိသေးပါဘူး။")

    status_msg = bot.reply_to(message, f"🚀 စုစုပေါင်း {len(all_targets)} နေရာကို ပို့နေပါပြီ...")
    
    success = 0
    fail = 0

    for tid in all_targets:
        try:
            # copy_message သည် Original Message ၏ ပုံစံ၊ Caption နှင့် Premium Emoji အားလုံးကို 
            # မူရင်းအတိုင်း ကူးယူပေးပို့သည်။ (Photo, Video, Sticker, Text, Audio အကုန်ရသည်)
            bot.forward_message(
                chat_id=tid, 
                from_chat_id=message.chat.id, 
                message_id=target_msg.message_id
            )
            success += 1
            time.sleep(0.1) # မြန်နှုန်းမြှင့်ထားသော်လည်း Flood မဖြစ်အောင် အနည်းငယ်ခြားထားသည်
        except Exception as e:
            print(f"Broadcast failed for {tid}: {e}")
            fail += 1
            continue

    bot.edit_message_text(
        f"✅ <b>Broadcast ပို့ပြီးပါပြီ!</b>\n\n🟢 အောင်မြင်: {success}\n🔴 ကျရှုံး: {fail}",
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        parse_mode="HTML"
    )

# ======================
# ADMIN GROUP MANAGEMENT COMMANDS
# ======================


@bot.message_handler(commands=["delgp"])
def del_group(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ Only the bot owner can remove groups.")

    parts = message.text.split()
    
    # ၁။ Command ရိုက်တဲ့ Group ကိုပဲ ဖျက်ချင်ရင် (/delgp)
    if len(parts) == 1:
        gid = message.chat.id
    # ၂။ တခြား Group ID ကို ပေးပြီး ဖျက်ချင်ရင် (/delgp -100xxxx)
    elif len(parts) == 2:
        try:
            gid = int(parts[1])
        except ValueError:
            return bot.reply_to(message, "⚠️ Chat ID က ကိန်းဂဏန်း ဖြစ်ရပါမယ်။")
    else:
        return bot.reply_to(message, "Usage: /delgp သို့မဟုတ် /delgp <chat_id>")

    if gid not in data.get("groups", []):
        return bot.reply_to(message, "ℹ️ ဒီ Group က စာရင်းထဲမှာ မရှိပါဘူး။")

    # စာရင်းထဲကနေ ဖျက်ထုတ်မယ်
    data["groups"].remove(gid)
    # reply_on_chats ထဲမှာ ရှိနေရင်လည်း ဖယ်ထုတ်မယ်
    if str(gid) in data.get("reply_on_chats", {}):
        del data["reply_on_chats"][str(gid)]
    
    save_data()
    bot.reply_to(message, f"✅ Group {gid} ကို စာရင်းထဲကနေ ဖယ်ထုတ်လိုက်ပါပြီ။")
# ======================
# START & WELCOME
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    
    if message.chat.type == "private":
        # ၁။ အရင်ဆုံး User ကို စာရင်းထဲမှာ မှတ်သားလိုက်ပါ (Join ထားသည်ဖြစ်စေ၊ မထားသည်ဖြစ်စေ)
        if message.chat.id not in data["users"]:
            data["users"].append(message.chat.id)
            save_data()

        # ၂။ ပြီးမှ Force Join စစ်ဆေးပါ
        if not is_joined(user_id):
            join_kb = InlineKeyboardMarkup()
            clean_channel = FORCE_JOIN_CHANNEL.replace('@', '')
            join_kb.add(InlineKeyboardButton("𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐣𝐨𝐢𝐧", url=f"https://t.me/{clean_channel}"))
            join_kb.add(InlineKeyboardButton("𝐣𝐨𝐢𝐧(စစ်ဆေးမည်)", url=f"https://t.me/{BOT_USERNAME}?start=start"))
            
            return bot.send_message(
                message.chat.id, 
                "<tg-emoji emoji-id='6269316311172518259'>❌</tg-emoji> <b>အသုံးပြုခွင့်မရှိသေးပါ!</b> <tg-emoji emoji-id='6257780484281997093'>❌</tg-emoji>\n\nဒီ 𝐁𝐨𝐭 ကို သုံးဖို့အတွက် 𝐆𝐫𝐨𝐮𝐩 ကို အရင် 𝐉𝐨𝐢𝐧 ပေးရပါမယ်။",
                reply_markup=join_kb
            )

    # ၃။ Join ထားပြီးသူများအတွက် ပြသမည့် စာသား
    bot.send_message(
        message.chat.id, 
        "<tg-emoji emoji-id='5251299553239398548'>🤖</tg-emoji> <b>𝐀𝐮𝐭𝐨 𝐑𝐞𝐩𝐥𝐲 & 𝐒𝐩𝐚𝐦 𝐥𝐢𝐧𝐤 𝐆𝐫𝐨𝐮𝐩 𝐇𝐞𝐥𝐩 𝐁𝐨𝐭 Online!</b>\n\n"
        "<tg-emoji emoji-id='5240241223632954241'>🚫</tg-emoji> 𝐁𝐢𝐨 / 𝐉𝐨𝐢𝐧 / 𝐋𝐢𝐧𝐤 𝐬𝐩𝐚𝐦 𝐚𝐮𝐭𝐨 𝐝𝐞𝐥𝐞𝐭𝐞\n"
        "<tg-emoji emoji-id='6271786398404055377'>⚠️</tg-emoji> 𝟑 𝐖𝐚𝐫𝐧𝐢𝐧𝐠𝐬 = 𝐀𝐮𝐭𝐨 𝐌𝐮𝐭𝐞\n\n"
        "<tg-emoji emoji-id='5226945370684140473'>➕</tg-emoji> 𝐁𝐨𝐭 ကို 𝐆𝐫𝐨𝐮𝐩 ထဲထည့်ပြီး 𝐀𝐝𝐦𝐢𝐧 ပေးထားပါ။<tg-emoji emoji-id='5226945370684140473'>➕</tg-emoji> ",
        reply_markup=main_buttons()
    )
            


@bot.message_handler(commands=["help"]) 
def help_command(message):
    help_text = (
        "👋 Owner အတွက် အသုံးပြုနိုင်သော Command များ-\n"
        "/setmute\n /addword (global)\n /delword (global)\n /broadcast\n /list\n"
        "/setwarn [message]\n /getwarn\n"
        "Group admins: /setword [word]\n /delword [word]\n"
    )
    # Always log the incoming help request for debugging
    try:
        print(f"/help requested by {message.from_user.id} in chat {message.chat.id} (type={message.chat.type})")
    except Exception:
        pass

    if message.from_user.id in ADMIN_IDS:
        # Try to DM the owner with full help, and always reply in-chat with a short confirmation
        sent_dm = False
        try:
            bot.send_message(message.from_user.id, help_text, parse_mode=None)
            sent_dm = True
        except Exception as e:
            print(f"Failed to DM owner help: {e}")

        # Reply in the invoking chat with a short confirmation or fallback to full text
        try:
            if sent_dm:
                bot.reply_to(message, "✅ Owner help sent privately.")
            else:
                bot.reply_to(message, help_text, parse_mode=None)
        except Exception as e:
            print(f"Failed to reply in chat for /help: {e}")
    else:
        # Non-owner callers get a short info message
        try:
            bot.reply_to(message, "❌ ဒီ Command ကို Bot Owner သာ သုံးနိုင်ပါတယ်။")
        except Exception:
            pass

# ======================
# MESSAGE GUARD & LEARNING
# ======================
# Patterns include English variants plus common Myanmar (Burmese) transliterations
BASE_PATTERNS = [
    r"b[\W_]*i[\W_]*o",        # bio (english, with possible separators)
    r"j[\W_]*o[\W_]*i[\W_]*n",# join (english)
    r"t[\W_]*\.?[\W_]*m[\W_]*e", # t.me / telegram links
    r"http",
    r"www",
    r"link",
    # Burmese transliterations / common forms
    r"ဂျိုင်း",                   # "ဂျိုင်း" (join)
    r"ဂျိုင်း[\s\S]*လင့်|ဂျိုင်း[\s\S]*လင့်|ဂျိုင်း[\s\S]*လင်ခ်", # join + link combos
    r"လင့်ခ်|လင့်|လင့်|လင်ခ်",   # various spellings of "link" in Burmese
    r"ဘိုင်[\W_]*အို",           # "ဘိုင်အို" (bio)
    r"ဘိုင်ယို"                  # alternative spelling
]

last_message_dict = {}

# Human readable names for detected pattern indices (used for logging/debug)
PATTERN_NAMES = {
    0: "bio_en",
    1: "join_en",
    2: "telegram",
    3: "http",
    4: "www",
    5: "link_en",
    6: "join_mm",
    7: "join_mm_link_combo",
    8: "link_mm",
    9: "bio_mm",
    10: "bio_mm_alt"
}

# Normalize persisted `extra_words` to the same form used for matching
def _normalize_text_for_match(s: str) -> str:
    if not s:
        return s
    nk = unicodedata.normalize('NFKC', s).lower()
    nk = ''.join(c for c in unicodedata.normalize('NFKD', nk) if not unicodedata.category(c).startswith('M'))
    return nk

# Safe word matching: check if word appears anywhere in text
def matches_word_in_text(word: str, text: str) -> bool:
    # 'word' ဆိုတာ ပိတ်ပင်ထားတဲ့စာ (ဥပမာ: "လီး")
    # 'text' ဆိုတာ User ပို့တဲ့စာ (ဥပမာ: "လီးလား")
    # word_boundary ကို စစ်ဖို့ regex အသုံးပြုထားပြီး အစ/အဆုံးကို \b သတ်မှတ်ပါတယ်။
    if not word or not text:
        return False
    pattern = r'\b' + re.escape(word) + r'\b'
    if re.search(pattern, text, flags=re.UNICODE):
        return True
    return False


def check_banned_words(user_text: str, banned_list: list) -> bool:
    # user_text ထဲမှာ banned_list ထဲက စကားလုံး တစ်ခုခု ပါကြောင်း စစ်ပါတယ်
    # မှန်ကန်အောင်အဓိကလာတာက
    # banned_list ထဲမှာ "လ" လို single-character ကို မထည့်ရ၊
    # မလိုလားအပ်တဲ့ false positive တွေရှောင်ရန်ပါ။
    for word in banned_list:
        if matches_word_in_text(word, user_text):
            return True
    return False

# Apply normalization to any existing extra_words saved in data
if isinstance(data.get("extra_words", None), list):
    normalized = []
    for w in data.get("extra_words", []):
        if not w: continue
        n = _normalize_text_for_match(w)
        if n and n not in normalized:
            normalized.append(n)
    data["extra_words"] = normalized
    save_data()

def strip_accents(s: str) -> str:
    """Return string with diacritical marks removed."""
    nkfd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nkfd if not unicodedata.category(c).startswith('M'))


def detect_reason(text):
    """Detect which pattern/word triggered the violation"""
    if not text:
        return "spam"
    try:
        t = unicodedata.normalize("NFKC", text).lower()
        t = strip_accents(t)
        for idx, pattern in enumerate(BASE_PATTERNS):
            if re.search(pattern, t):
                return PATTERN_NAMES.get(idx, "spam")
        for word in data.get("extra_words", []):
            # banned word detection now uses exact word matching
            if matches_word_in_text(word.lower(), t):
                return word
    except:
        pass
    return "spam"


@bot.message_handler(content_types=["new_chat_members"])
def welcome_group(message):
    try:
        print(f"🔔 new_chat_members triggered - Chat: {message.chat.id}")
        print(f"   Chat Type: {message.chat.type}")
        print(f"   Chat Title: {message.chat.title}")
        # (no automatic registration; use /addgp to approve a group)

        if message.new_chat_members:
            print(f"📌 Found {len(message.new_chat_members)} new members")
            for user in message.new_chat_members:
                try:
                    print(f"👤 Processing user: {user.id} - {user.first_name}")
                    bot_id = bot.get_me().id
                    print(f"   Bot ID: {bot_id}, Is Bot: {user.id == bot_id}")
                    # Bot ကိုယ်တိုင် Group ထဲ ရောက်သွားတဲ့အခါ နှုတ်ဆက်ရန်
                    if user.id == bot_id:
                        msg = "<tg-emoji emoji-id='5251299553239398548'>🤖</tg-emoji> <b> 𝐀𝐮𝐭𝐨 𝐑𝐞𝐩𝐥𝐲 & 𝐒𝐩𝐚𝐦 𝐥𝐢𝐧𝐤 𝐆𝐫𝐨𝐮𝐩 𝐇𝐞𝐥𝐩 𝐁𝐨𝐭 Active!</b>\n\n<tg-emoji emoji-id='5215613971352004352'>❤️</tg-emoji> ကျွန်​ေတာ်ကို 𝐀𝐝𝐦𝐢𝐧 ပေးထားဖို့ မမေ့ပါနဲ့ဗျာ။ <tg-emoji emoji-id='5215361191051798408'>🤍</tg-emoji>\n\n𝐒𝐩𝐚𝐦 𝐥𝐢𝐧𝐤တွေနဲ့ 𝐛𝐢𝐨 တွေကို အလိုအလျောက် ဖျက်ပေးပါမယ်။",
                        reply_markup=main_buttons()
                        bot.send_message(message.chat.id, msg, reply_markup=main_buttons())
                        print(f"✅ Bot welcome message sent to group {message.chat.id}")
                    
                except Exception as e:
                    print(f"❌ Failed to send welcome message: {e}")
                    import traceback
                    traceback.print_exc()
        else:
            print("⚠️ message.new_chat_members ကို data မရှိ")
    except Exception as e:
        print(f"❌ Error in welcome_group: {e}")
        import traceback
        traceback.print_exc()

@bot.message_handler(content_types=["group_chat_created", "supergroup_chat_created", "channel_chat_created"])
def handle_chat_creation(message):
    """Handle when chat/group is created"""
    try:
        print(f"🆕 Group/Chat created - Chat ID: {message.chat.id}")
        # do not auto-approve; groups must be added manually with /addgp
        bot.send_message(
            message.chat.id,
            "<tg-emoji emoji-id='5251299553239398548'>🤖</tg-emoji>𝐇𝐞𝐥𝐩 𝐁𝐨𝐭 𝐀𝐜𝐭𝐢𝐯𝐞!\n"
            "𝐁𝐢𝐨/𝐉𝐨𝐢𝐧/𝐋𝐢𝐧𝐤 𝐬𝐩𝐚𝐦 𝐫𝐞𝐦𝐨𝐯𝐞 အတွက် 𝐀𝐝𝐦𝐢𝐧 ပေးထားဖို့ လိုအပ်ပါတယ်။",
            reply_markup=main_buttons()
        )
    except Exception as e:
        print(f"❌ Error handling chat creation: {e}")

@bot.message_handler(content_types=["text", "photo", "sticker", "story", "video", "animation"])
def handle_all(message):
    # --- Time Check Section ---
    if hasattr(message, 'date'):
        msg_ts = message.date
        if isinstance(msg_ts, datetime.datetime):
            msg_ts = int(msg_ts.timestamp())
        try:
            msg_ts = int(msg_ts)
        except:
            msg_ts = None
        if msg_ts is not None:
            if msg_ts < BOT_START_TIME:
                return
            chat_key = str(message.chat.id)
            if "last_ts" not in data: data["last_ts"] = {}
            last = data.get("last_ts", {}).get(chat_key, 0)
            if msg_ts <= last:
                return
            data["last_ts"][chat_key] = msg_ts
            # save_data() ကို အောက်က logic တွေပြီးမှ တစ်ခါတည်းခေါ်တာ ပိုကောင်းပါတယ်

    chat_id = message.chat.id
    user_id = message.from_user.id
    
    print(f"[DEBUG] ===== handle_all called ===== content_type={message.content_type}, chat_type={message.chat.type}, chat_id={chat_id}")

    # --- Auto Register Group Section ---
    if message.chat.type in ["group", "supergroup"]:
        # list ထဲမှာ မရှိသေးရင် အလိုအလျောက် ထည့်မယ်
        if chat_id not in data.get("groups", []):
            if "groups" not in data: data["groups"] = []
            data["groups"].append(chat_id)
            save_data() # ID အသစ်တွေ့တာနဲ့ ချက်ချင်းသိမ်းမယ်
            print(f"🤖 [AUTO-ADD] Group {chat_id} has been registered automatically.")

    # Ignore commands
    try:
        if message.content_type == 'text' and message.text and message.text.startswith('/'):
            return
    except Exception:
        pass

# --- Auto Register Group Section ---
    if message.chat.type in ["group", "supergroup"]:
        # list ထဲမှာ မရှိသေးရင် အလိုအလျောက် ထည့်မယ်
        if chat_id not in data.get("groups", []):
            if "groups" not in data: data["groups"] = []
            data["groups"].append(chat_id)
            
            # အသစ်တိုးတဲ့ Group ကို reply ပိတ်ထားမယ် (Admin က /rp နဲ့ ဖွင့်ရအောင်)
            if "reply_on_chats" not in data: data["reply_on_chats"] = {}
            data["reply_on_chats"][str(chat_id)] = False 
            
            save_data() 
            print(f"🤖 [AUTO-ADD] Group {chat_id} registered and replies set to False.")


    if message.chat.type == "private" and user_id not in ADMIN_IDS:
        if not is_joined(user_id):
            join_kb = InlineKeyboardMarkup()
            clean_channel = FORCE_JOIN_CHANNEL.replace('@', '')
            join_kb.add(InlineKeyboardButton("𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐣𝐨𝐢𝐧", url=f"https://t.me/{clean_channel}"))
            join_kb.add(InlineKeyboardButton(" 𝐣𝐨𝐢𝐧 (စစ်ဆေးမည်)", url=f"https://t.me/{BOT_USERNAME}?start=start"))
            return bot.send_message(
                message.chat.id,
                "<tg-emoji emoji-id='6257780484281997093'>❌</tg-emoji> <b>အသုံးပြုခွင့်မရှိသေးပါ!</b>\n\nဒီ 𝐁𝐨𝐭 ကို သုံးဖို့အတွက် 𝐒𝐔𝐏𝐏𝐎𝐑𝐓 ကို အရင် Join ပေးရပါမယ်။",
                reply_markup=join_kb
            )

    # ၁။ Guard စနစ် (Story/Forward Detection)
    # content_types ထဲမှာ 'story' ကို ထည့်ထားဖို့ မမေ့ပါနဲ့
    is_story = (message.content_type == 'story')
    is_forwarded = (message.forward_from is not None) or (message.forward_from_chat is not None) or (message.forward_sender_name is not None)

    if is_story or is_forwarded:
        # allow admins
        if not is_admin(chat_id, user_id):
            try:
                # အရင်ဆုံး Message ကို ဖျက်မယ်
                bot.delete_message(chat_id, message.message_id)
                print(f"🗑️ Deleted { 'Story' if is_story else 'Forward' } in {chat_id}")
            except Exception as e:
                print(f"❌ Failed to delete message: {e}")
                return

            # သတိပေးစာ ပို့မယ်
            warn_text = "⚠️ <b>သတိပေးချက်</b>\n\n"
        if is_story:
            warn_text += "<tg-emoji emoji-id='4918087434840834979'>ℹ️</tg-emoji> 𝐒𝐭𝐨𝐫𝐲 ပို့ခြင်းများကို ခွင့်မပြုပါ။\n"
        else:
            warn_text += "<tg-emoji emoji-id='4918087434840834979'>ℹ️</tg-emoji> 𝐟𝐨𝐫𝐰𝐚𝐫𝐝𝐞𝐝 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 များကို ခွင့်မပြုပါ။\n"
            
        if message.from_user:
            warn_text += f"<tg-emoji emoji-id='4913497231492908158'>👤</tg-emoji> 𝐔𝐬𝐞𝐫: {mention(message.from_user)}"
            
        bot.send_message(chat_id, warn_text, parse_mode="HTML")
        return
    # ဒီမှာတင် ရပ်လိုက်မယ် (နောက်ထပ် check တွေ မလုပ်တော့ဘူး)

    check_text = message.text if message.text else message.caption
    is_forwarded = message.forward_from or message.forward_from_chat or message.forward_sender_name
    
    # strip accents for pattern matching
    if check_text:
        norm_text = strip_accents(unicodedata.normalize('NFKC', check_text).lower())
    else:
        norm_text = check_text

    # Check if message is from a non-admin bot with links or long text
    is_bot_sender = False
    if hasattr(message.from_user, 'is_bot') and message.from_user.is_bot:
        is_bot_sender = True
    elif message.from_user.username and message.from_user.username.lower().endswith('bot'):
        is_bot_sender = True
    has_link = check_text and ('http' in check_text.lower() or 't.me/' in check_text.lower() or 'www' in check_text.lower())
    is_long_text = check_text and len(check_text) > 50
    
    if is_bot_sender and (has_link or is_long_text):            # Delete non-admin bot spam
        try:
            bot.delete_message(chat_id, message.message_id)
            print(f"🤖 Non-admin bot spam deleted - User: {user_id}, Chat: {chat_id}")
        except Exception as e:
            print(f"⚠️ Failed to delete bot message: {e}")
        
        # Send warning
        bot.send_message(
            chat_id,
            f"<tg-emoji emoji-id='6271786398404055377'>⚠️</tg-emoji> အက်မင်တစ်ခုမဟုတ်တဲ့ ဘော့ကနေ မှားတဲ့ လင့်/စာများ ပိုခြင်းကို ခွင့်မပြုပါ။\n\n👤 𝐁𝐨𝐭: {mention(message.from_user)}",
            parse_mode=None
        )
        return
    
    found = False
    matched_chat_word = None
    if check_text:
        t = norm_text  # already NFKC-normalized and accents stripped
        # start with base patterns
        if any(re.search(p, t) for p in BASE_PATTERNS):
            found = True
        # global extra words
        if not found:
            for w in data.get("extra_words", []):
                if matches_word_in_text(w, t):
                    found = True
                    break
        # chat-specific words
        if not found:
            cw = data.get("chat_words", {}).get(str(chat_id), [])
            for w in cw:
                if matches_word_in_text(w, t):
                    found = True
                    matched_chat_word = w
                    break
    
    if found or is_forwarded:
        if not is_admin(chat_id, user_id):
            # send warning only to non-admins; special message for chat-specific words
            if matched_chat_word:
                warn_msg = f"⚠️ သင့်စာထဲတွင် Group မှပိတ်ပင်ထားသော စကားပါနေသည်။ ({matched_chat_word})"
            else:
                warn_msg = data.get("warning_text") or "⚠️ သတိပေးချက်: သင့်စာသားတွင် ဂျိုင်း/ဘိုင်အို/လင့် တစ်ခုခုပါသည်။"
            bot.send_message(chat_id, warn_msg)
            # Detect reason
            try:
                reason = "forward" if is_forwarded else detect_reason(check_text)
            except:
                reason = "spam"
            
            # Warning/mute logic with inline unmute button
            key = strike_key(chat_id, user_id)
            strikes = data["strikes"].get(key, 0) + 1
            data["strikes"][key] = strikes
            save_data()
            print(f"💥 Violation detected - Reason: {reason}, Strikes: {strikes}/3, User: {user_id}, Chat: {chat_id}")
            
            if strikes >= 3:
                # ၁၀၆၈ ဝန်းကျင်မှာ အောက်ကအတိုင်း ပြင်ပါ
                group_mute_times = data.get("group_mute_times", {})
                current_mute_duration = group_mute_times.get(str(chat_id), data.get("mute_time", 60))
        
                until_date = int(time.time()) + current_mute_duration
                print(f"🔇 Muting user {user_id} for {current_mute_duration} seconds...")
                try:
                    bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(), until_date=until_date)
                    print(f"✅ User {user_id} muted successfully until {until_date}")
                except Exception as e: 
                    print(f"❌ Failed to mute user {user_id}: {e}")
                
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton("🔓 Unmute", callback_data=f"unmute:{user_id}"))
                # Monospace space (固定 width) ကို သုံးပြီး စာသားတွေကို ညီအောင် ညှိထားပါတယ်
                user_label    = "<b>User:</b>"
                reason_label  = "<b>အကြောင်းပြချက်:</b>"
                time_label    = "<b>ကြာချိန်:</b>"

                bot.send_message(
                    chat_id,
                    f"<tg-emoji emoji-id='6174589325695521740'>❌</tg-emoji> <b>𝐀𝐮𝐭𝐨 𝐦𝐮𝐭𝐞</b> <tg-emoji emoji-id='6257780484281997093'>❌</tg-emoji>\n\n"
                    f"<blockquote>"
                    f"<tg-emoji emoji-id='4913497231492908158'>👤</tg-emoji> <code> </code>{user_label} {mention(message.from_user)} <tg-emoji emoji-id='6177007478182516158'>✨</tg-emoji>\n\n"
                    f"<tg-emoji emoji-id='4918087434840834979'>ℹ️</tg-emoji> <code> </code>{reason_label} (ဘိုင်အို/ဂျိုင်း/လင့်) ၃ ကြိမ်ပို့ခြင်း\n"
                    f"<tg-emoji emoji-id='4904882772637648609'>⏱️</tg-emoji> <code> </code>{time_label} {mute_time} စက္ကန့်\n\n"
                    f"<tg-emoji emoji-id='5123230779593196220'>⏳</tg-emoji> <code> </code>သတ်မှတ်ချိန်ပြည့်ပါက အလိုအလျောက် Unmute ဖြစ်ပါမည်။"
                    f"</blockquote>",
                    reply_markup=kb,
                    parse_mode="HTML"
              )
                data["strikes"][key] = 0
                save_data()
                print(f"📊 Reset strikes for user {user_id}")
            else:
                bot.send_message(
                    chat_id,
                    f"<blockquote><tg-emoji emoji-id='5395695537687123235'>❌</tg-emoji> <b>သတိပေးချက် ({strikes}/3)</b> <tg-emoji emoji-id='5424818078833715060'>❌</tg-emoji></blockquote>\n"
                    f"<blockquote>"
                    f"<tg-emoji emoji-id='5424972470023104089'>👤</tg-emoji> 𝐔𝐬𝐞𝐫: {mention(message.from_user)} <tg-emoji emoji-id='6177007478182516158'>✨</tg-emoji>\n"
                    f"<tg-emoji emoji-id='5411225014148014586'>🚫</tg-emoji> (ဘိုင်အို / ဂျိုင်း / လင့်) ဆိုင်ရာ စာသားများ ပို့ခြင်းကို ခွင့်မပြုပါ။\n"
                    f"<tg-emoji emoji-id='5215613971352004352'>⚠️</tg-emoji> ၃ ကြိမ် ပြုလုပ်ပါက 𝐀𝐮𝐭𝐨 𝐦𝐮𝐭𝐞 ဖြစ်ပါမည်။<tg-emoji emoji-id='5215361191051798408'>❤️</tg-emoji>"
                    f"</blockquote>",
                    parse_mode="HTML"
               )
                print(f"⚠️ Warning #{strikes} sent to user {user_id}")
            
            try: 
                bot.delete_message(chat_id, message.message_id)
                print(f"🗑️ Message deleted")
            except Exception as e: 
                print(f"⚠️ Failed to delete message: {e}")
            return
        else:
            # Admin posted a message with bio/join/link — allow it, do not delete
            print(f"⏭️ Admin message allowed (bio/join/link detected but admin bypass) - User: {user_id}, Chat: {chat_id}")
            return


    # ၂။ သင်ယူခြင်းအပိုင်း (Reply ထောက်ထားရင် အရင်ဆုံး မှတ်မယ်)
    if message.reply_to_message:
        print(f"[DEBUG] Reply detected - replied_to_type: {message.reply_to_message.content_type}")
        if message.reply_to_message.content_type == 'sticker':
            parent = message.reply_to_message.sticker.file_id
            print(f"[DEBUG] Parent is STICKER: {parent[:20]}...")
        else:
            parent = message.reply_to_message.text.strip().lower() if message.reply_to_message.text else None
            print(f"[DEBUG] Parent is TEXT: {parent[:30] if parent else 'None'}...")

        if parent:
            if message.content_type == 'sticker':
                reply_sticker_id = message.sticker.file_id
                print(f"[DEBUG] 🎯 Saving STICKER-TO-STICKER: parent_sticker={parent[:20]}... → reply_sticker={reply_sticker_id[:20]}...")
                try:
                    brain_collection.insert_one({
                        "input_text": parent, 
                        "reply_text": None, 
                        "sticker_id": reply_sticker_id # ဒီမှာလည်း ပြင်မယ်
                    })
                    print(f"✅ မှတ်သားပြီး (Sticker-to-Sticker)")
                except Exception as e:
                    print(f"⚠️ Error saving sticker-to-sticker: {e}")
                return

            elif message.content_type == 'text':
                current_reply = message.html_text 
                if is_clean_text(current_reply):
                    save_to_brain(parent, current_reply, None)
                    print(f"✅ မှတ်သားပြီး (Text-to-Text): {parent[:30]}...")
                    return # သင်ယူပြီးရင် ဒီမှာတင် ရပ်လိုက်ပါ

    # ၃။ စကားပြောပြန်ဖြေခြင်း (Reply မဟုတ်တဲ့ ပုံမှန်စာတွေအတွက်)
    print(f"[DEBUG] === REPLY SECTION === message.content_type={message.content_type}, message.text={message.text is not None}")
    if not message.text or not message.text.startswith("/"):
        print(f"[DEBUG] Entered reply section (not command or no text)")
        if message.content_type == 'sticker':
            user_input = message.sticker.file_id
            print(f"[DEBUG] 📌 STICKER DETECTED - file_id: {user_input[:30]}...")
        else:
            user_input = message.text.lower() if message.text else None
            print(f"[DEBUG] Text message: {user_input[:30] if user_input else 'None'}...")

        # per-chat reply_on check:
        # - private chats: default to True (always reply unless explicitly disabled)
        # - groups: default to True (reply unless explicitly disabled via /rp)
        chat_key = str(chat_id)
        if message.chat.type == "private":
            chat_reply_on = data.get("reply_on_chats", {}).get(chat_key, True)
        else:
            chat_reply_on = data.get("reply_on_chats", {}).get(chat_key, True)
        print(f"[DEBUG] chat_reply_on for {chat_key} = {chat_reply_on}")

        if user_input and chat_reply_on:
            print(f"[DEBUG] user_input={user_input is not None}, chat_reply_on={chat_reply_on}")
            if message.content_type == 'sticker':
                print(f"[DEBUG] 📨 Sticker input received, searching database for match...")
                print(f"[DEBUG] Sticker file_id: {user_input[:50] if len(user_input) > 50 else user_input}")
            reply_text, sticker_id = get_reply(user_input)
            import time as _time
            t0 = _time.time()
            print(f"[DEBUG] get_reply returned: reply_text={reply_text is not None}, sticker_id={sticker_id is not None}")
            if sticker_id:
                print(f"[DEBUG] 🎯🎯 SENDING STICKER REPLY: sticker={sticker_id[:30]}...")
            try:
                if sticker_id:
                    print(f"[DEBUG] About to call bot.send_sticker(chat_id={chat_id}, sticker_id={sticker_id[:30]}...)")
                    bot.send_sticker(chat_id, sticker_id, reply_to_message_id=message.message_id)
                    print(f"[DEBUG] ✅ Sticker reply sent in {(_time.time()-t0):.2f}s")
                elif reply_text:
                    bot.reply_to(message, reply_text, parse_mode=None)
                    print(f"[DEBUG] ✅ Text reply sent in {(_time.time()-t0):.2f}s")
                else:
                    print(f"[DEBUG] ❌❌ No reply found for input")
            except Exception as e:
                print(f"⚠️ သုံးဆောင်း အချက်အမှားတက်ပါသည် (Chat ID: {chat_id}) - အကြောင်းရင်း: {e}")
        else:
            print(f"[DEBUG] Conditions not met: user_input={user_input is not None}, chat_reply_on={chat_reply_on}")
            
    

# RUN (Error တက်လျှင် အလိုအလျောက် ပြန်ပတ်ပေးမည့် စနစ်)
# ======================
if __name__ == '__main__':
    init_db()
    print("🤖 Dating Bot is starting...")
    # No need to flush old updates, just rely on BOT_START_TIME
    while True:
        try:
            print("🚀 Bot is now online and will only reply to new messages.")
            bot.infinity_polling(timeout=90, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            print(f"⚠️ Connection Error: {e}")
            print("🔄 5 seconds နေရင် ပြန်စပါမယ်...")
            time.sleep(5)
