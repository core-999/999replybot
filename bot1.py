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
        
        # Bot စတင် run တاနဲ့ Database ထဲက Sticker မှတ်ဉာဏ်တွေကို အလိုအလျောက် ဖျက်မည်
        try:
            result = brain_collection.delete_many({"sticker_id": {"$ne": None, "$ne": ""}})
            if result.deleted_count > 0:
                print(f"🧹 Startup Cleanup: MongoDB ထဲမှ Sticker မှတ်ဉာဏ် {result.deleted_count} ခုကို အလိုအလျောက် ဖျက်ထုတ်လိုက်ပါပြီ။")
        except Exception as e:
            print(f"⚠️ Startup Sticker Cleanup Error: {e}")
            
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
def save_to_brain(input_text, reply_text):
    try:
        # အဖြေတူတာ ရှိမရှိ အရင်စစ်မယ်
        query = {
            "input_text": input_text.lower().strip(), 
            "reply_text": reply_text
        }
        
        if not brain_collection.find_one(query):
            brain_collection.insert_one(query)
            print(f"✅ အဖြေအသစ် တိုးမှတ်သားပြီး: {input_text} -> {reply_text}")
    except Exception as e:
        print(f"⚠️ save_to_brain error: {e}")

def get_reply(text):
    if not text:
        return None
        
    user_input = text.lower().strip()
    
    try:
        results = list(brain_collection.find({"input_text": user_input}))
        
        if results:
            chosen = random.choice(results)
            print(f"🎯 Found {len(results)} replies for '{user_input}', chose one randomly.")
            return chosen.get("reply_text")
            
        return None
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return None

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
# UNMUTE CALLBACK
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
    current = data.get("reply_on_chats", {}).get(key, data.get("reply_on", True))
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
        
        if "group_mute_times" not in data:
            data["group_mute_times"] = {}
        
        data["group_mute_times"][str(chat_id)] = seconds
        save_data()
        
        bot.reply_to(message, f"✅ ဒီ Group အတွက် Mute time ကို {args[1]} ({seconds} seconds) အဖြစ် သတ်မှတ်လိုက်ပါပြီ။")
    else:
        bot.reply_to(message, "❌ Invalid format! Use: 30s, 5m, or 1h")
        
@bot.message_handler(commands=["addword"])
def add_word(message):
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

@bot.message_handler(commands=["setword"])
def set_chat_word(message):
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

# ======================
# LIST BRAIN ENTRIES COMMAND
# ======================
@bot.message_handler(commands=["list"])
def list_brain(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if message.chat.type not in ["private", "group", "supergroup"]:
        return

    args = message.text.split(maxsplit=1)
    mode = args[1].strip().lower() if len(args) > 1 else "words"

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
            input_text = doc.get("input_text")
            reply_text = doc.get("reply_text")
            safe_input = html.escape(input_text[:40]) if input_text else ""
            reply_preview = html.escape(reply_text[:35]) if reply_text else "[Empty]"
            msg += f"<b>{idx}.</b> 💬 <code>{safe_input}</code>\n   ➜ {reply_preview}\n\n"
            
            if len(msg) > 3500:
                try:
                    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_to_message_id=message.message_id)
                except Exception as e:
                    print(f"[DEBUG] Error sending list: {e}")
                msg = ""

        help_msg = "\n<b>🗑️ ဖျက်ချမည့် နည်းလမ်း:</b>\n/d 1  -  /d hello"
        if msg:
            bot.send_message(message.chat.id, msg + help_msg, parse_mode="HTML", reply_to_message_id=message.message_id)
        else:
            bot.send_message(message.chat.id, help_msg, parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    # Default mode: show ban words
    gw = data.get("extra_words", [])
    cw = data.get("chat_words", {}).get(str(message.chat.id), [])

    msg = f"<b>📋 Ban Words</b>\n\n"
    msg += f"<b>Global ({len(gw)}):</b>\n"
    if gw:
        for w in gw:
            msg += f"• <code>{html.escape(w)}</code>\n"
    else:
        msg += "(No global ban words)\n"

    msg += f"\n<b> ესချက်တင် ({len(cw)}):</b>\n"
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
        return bot.reply_to(message, "သုံးပုံ:\n/d နံပါတ် - /d 1\n/d စာလုံး - /d hello")
    target = args[1].strip()
    
    deleted = 0
    
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
    
    target_lower = target.lower()
    try:
        result = brain_collection.delete_many({"input_text": target_lower})
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
    
    current_status = data.get("reply_on_chats", {}).get(str(chat_id), True)
    new_status = not current_status
    
    data.setdefault("reply_on_chats", {})[str(chat_id)] = new_status
    save_data()
    
    kb = InlineKeyboardMarkup()
    btn_text = "🟢 𝐁𝐨𝐭 စာပြန်ခြင်း: ON" if new_status else "🔴 𝐁𝐨𝐭 စာပြန်ခြင်း: OFF"
    kb.add(InlineKeyboardButton(btn_text, callback_data="toggle_reply"))
    
    bot.send_message(chat_id, f"<tg-emoji emoji-id='5251299553239398548'>🤖</tg-emoji> <b>𝐁𝐨𝐭 စာပြန်ခြင်း စနစ်ကို {'ဖွင့်' if new_status else 'ပိတ်'} လိုက်ပါပြီ။</b>\n\n{btn_text}", 
                     reply_markup=kb, parse_mode="HTML")        

@bot.message_handler(commands=["id"])
def show_chat_id(message):
    chat = message.chat
    bot.reply_to(message, f"Chat ID: {chat.id}")

# ======================
# BROADCAST
# ======================
@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ ဒီ Command ကို Bot Owner သာ သုံးနိုင်ပါတယ်။")
    
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Broadcast ပို့ချင်တဲ့ Message ကို <b>Reply</b> ထောက်ပြီးမှ သုံးပေးပါ။", parse_mode="HTML")

    target_msg = message.reply_to_message
    all_targets = list(set(data.get("groups", []) + data.get("users", [])))
    
    if not all_targets:
        return bot.reply_to(message, "⚠️ ပို့စရာ Target မရှိသေးပါဘူး။")

    status_msg = bot.reply_to(message, f"🚀 စုစုပေါင်း {len(all_targets)} နေရာကို ပို့နေပါပြီ...")
    
    success = 0
    fail = 0

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
            print(f"Broadcast failed for {tid}: {e}")
            fail += 1
            continue

    bot.edit_message_text(
        f"✅ <b>Broadcast ပို့ပြီးပါပြီ!</b>\n\n🟢 အောင်မြင်: {success}\n🔴 ကျရှုံး: {fail}",
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

# ======================
# START & WELCOME
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    
    if message.chat.type == "private":
        if message.chat.id not in data["users"]:
            data["users"].append(message.chat.id)
            save_data()

        # ── Bot ကို start လုပ်သူများ ဘယ် group တွေမှာ သုံးနေလဲ Owner ဆီ ပို့ပေးမည့် စနစ် ──
        try:
            user_name = message.from_user.first_name
            user_username = f"@{message.from_user.username}" if message.from_user.username else "No Username"
            
            # Bot ထည့်ထားသော Group စာရင်းများကို ရှာဖွေမည်
            user_active_groups = []
            for g_id in data.get("groups", []):
                try:
                    member = bot.get_chat_member(g_id, user_id)
                    # User သည် ထို Group ထဲတွင် ရှိနေပြီး Admin သို့မဟုတ် Member ဖြစ်နေပါက
                    if member.status in ["creator", "administrator", "member"]:
                        chat_info = bot.get_chat(g_id)
                        user_active_groups.append(f"• {chat_info.title} (<code>{g_id}</code>)")
                except Exception:
                    pass
            
            groups_str = "\n".join(user_active_groups) if user_active_groups else "Group တစ်ခုမှ ရှာမတွေ့ပါ။"
            
            log_text = (
                f"📥 <b>New /start Activity Detected!</b>\n\n"
                f"👤 <b>User:</b> {user_name} ({user_username})\n"
                f"🆔 <b>User ID:</b> <code>{user_id}</code>\n\n"
                f"👥 <b>အသုံးပြုနေသော Group များ:</b>\n{groups_str}"
            )
            
            # Owner အားလုံးဆီသို့ ပို့ပေးမည်
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, log_text, parse_mode="HTML")
                except Exception as e:
                    print(f"Failed to send start log to owner {admin_id}: {e}")
        except Exception as e:
            print(f"Error in start logging: {e}")
        # ────────────────────────────────────────────────────────────

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
    if message.from_user.id in ADMIN_IDS:
        sent_dm = False
        try:
            bot.send_message(message.from_user.id, help_text, parse_mode=None)
            sent_dm = True
        except Exception as e:
            print(f"Failed to DM owner help: {e}")

        try:
            if sent_dm:
                bot.reply_to(message, "✅ Owner help sent privately.")
            else:
                bot.reply_to(message, help_text, parse_mode=None)
        except Exception as e:
            print(f"Failed to reply in chat for /help: {e}")
    else:
        try:
            bot.reply_to(message, "❌ ဒီ Command ကို Bot Owner သာ သုံးနိုင်ပါတယ်။")
        except Exception:
            pass

# ======================
# MESSAGE GUARD & LEARNING
# ======================
BASE_PATTERNS = [
    r"b[\W_]*i[\W_]*o",
    r"j[\W_]*o[\W_]*i[\W_]*n",
    r"t[\W_]*\.?[\W_]*m[\W_]*e",
    r"http",
    r"www",
    r"link",
    r"ဂျိုင်း",
    r"ဂျိုင်း[\s\S]*လင့်|ဂျိုင်း[\s\S]*လင့်|ဂျိုင်း[\s\S]*လင်ခ်",
    r"လင့်ခ်|လင့်|လင့်|လင်ခ်",
    r"ဘိုင်[\W_]*အို",
    r"ဘိုင်ယို"
]

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

def _normalize_text_for_match(s: str) -> str:
    if not s:
        return s
    nk = unicodedata.normalize('NFKC', s).lower()
    nk = ''.join(c for c in unicodedata.normalize('NFKD', nk) if not unicodedata.category(c).startswith('M'))
    return nk

def matches_word_in_text(word: str, text: str) -> bool:
    if not word or not text:
        return False
    pattern = r'\b' + re.escape(word) + r'\b'
    if re.search(pattern, text, flags=re.UNICODE):
        return True
    return False

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
    nkfd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nkfd if not unicodedata.category(c).startswith('M'))

def detect_reason(text):
    if not text:
        return "spam"
    try:
        t = unicodedata.normalize("NFKC", text).lower()
        t = strip_accents(t)
        for idx, pattern in enumerate(BASE_PATTERNS):
            if re.search(pattern, t):
                return PATTERN_NAMES.get(idx, "spam")
        for word in data.get("extra_words", []):
            if matches_word_in_text(word.lower(), t):
                return word
    except:
        pass
    return "spam"

@bot.message_handler(content_types=["new_chat_members"])
def welcome_group(message):
    try:
        if message.new_chat_members:
            for user in message.new_chat_members:
                try:
                    bot_id = bot.get_me().id
                    if user.id == bot_id:
                        msg = "<tg-emoji emoji-id='5251299553239398548'>🤖</tg-emoji> <b> 𝐀𝐮𝐭𝐨 𝐑𝐞𝐩𝐥𝐲 & 𝐒𝐩𝐚𝐦 𝐥𝐢𝐧𝐤 𝐆𝐫𝐨𝐮𝐩 𝐇𝐞𝐥𝐩 𝐁𝐨𝐭 Active!</b>\n\n<tg-emoji emoji-id='5215613971352004352'>❤️</tg-emoji> ကျွန်​ေတာ်ကို 𝐀𝐝𝐦𝐢𝐧 ပေးထားဖို့ မမေ့ပါနဲ့ဗျာ။ <tg-emoji emoji-id='5215361191051798408'>🤍</tg-emoji>\n\n𝐒𝐩𝐚𝐦 𝐥𝐢𝐧𝐤တွေနဲ့ 𝐛𝐢𝐨 တွေကို အလိုအလျောက် ဖျက်ပေးပါမယ်။"
                        bot.send_message(message.chat.id, msg, reply_markup=main_buttons())
                except Exception as e:
                    print(f"❌ Failed to send welcome message: {e}")
    except Exception as e:
        print(f"❌ Error in welcome_group: {e}")

@bot.message_handler(content_types=["group_chat_created", "supergroup_chat_created", "channel_chat_created"])
def handle_chat_creation(message):
    try:
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

    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type in ["group", "supergroup"]:
        if chat_id not in data.get("groups", []):
            if "groups" not in data: data["groups"] = []
            data["groups"].append(chat_id)
            if "reply_on_chats" not in data: data["reply_on_chats"] = {}
            data["reply_on_chats"][str(chat_id)] = False 
            save_data() 
            print(f"🤖 [AUTO-ADD] Group {chat_id} registered and replies set to False.")

    try:
        if message.content_type == 'text' and message.text and message.text.startswith('/'):
            return
    except Exception:
        pass

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

    is_story = (message.content_type == 'story')
    is_forwarded = (message.forward_from is not None) or (message.forward_from_chat is not None) or (message.forward_sender_name is not None)

    if is_story or is_forwarded:
        if not is_admin(chat_id, user_id):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception as e:
                return

            warn_text = "⚠️ <b>သတိပေးချက်</b>\n\n"
            if is_story:
                warn_text += "<tg-emoji emoji-id='4918087434840834979'>ℹ️</tg-emoji> 𝐒𝐭𝐨𝐫𝐲 ပို့ခြင်းများကို ခွင့်မပြုပါ။\n"
            else:
                warn_text += "<tg-emoji emoji-id='4918087434840834979'>ℹ️</tg-emoji> 𝐟𝐨𝐫𝐰𝐚𝐫𝐝𝐞𝐝 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 များကို ခွင့်မပြုပါ။\n"
                
            if message.from_user:
                warn_text += f"<tg-emoji emoji-id='4913497231492908158'>👤</tg-emoji> 𝐔𝐬𝐞𝐫: {mention(message.from_user)}"
                
            bot.send_message(chat_id, warn_text, parse_mode="HTML")
            return

    check_text = message.text if message.text else message.caption
    
    if check_text:
        norm_text = strip_accents(unicodedata.normalize('NFKC', check_text).lower())
    else:
        norm_text = check_text

    is_bot_sender = False
    if hasattr(message.from_user, 'is_bot') and message.from_user.is_bot:
        is_bot_sender = True
    elif message.from_user.username and message.from_user.username.lower().endswith('bot'):
        is_bot_sender = True
    has_link = check_text and ('http' in check_text.lower() or 't.me/' in check_text.lower() or 'www' in check_text.lower())
    is_long_text = check_text and len(check_text) > 50
    
    if is_bot_sender and (has_link or is_long_text):
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception as e:
            pass
        
        bot.send_message(
            chat_id,
            f"<tg-emoji emoji-id='6271786398404055377'>⚠️</tg-emoji> အက်မင်တစ်ခုမဟုတ်တဲ့ ဘော့ကနေ မှားတဲ့ လင့်/စာများ ပိုခြင်းကို ခွင့်မပြုပါ။\n\n👤 𝐁𝐨𝐭: {mention(message.from_user)}",
            parse_mode=None
        )
        return
    
    found = False
    matched_chat_word = None
    if check_text:
        t = norm_text
        if any(re.search(p, t) for p in BASE_PATTERNS):
            found = True
        if not found:
            for w in data.get("extra_words", []):
                if matches_word_in_text(w, t):
                    found = True
                    break
        if not found:
            cw = data.get("chat_words", {}).get(str(chat_id), [])
            for w in cw:
                if matches_word_in_text(w, t):
                    found = True
                    matched_chat_word = w
                    break
    
    if found or is_forwarded:
        if not is_admin(chat_id, user_id):
            if matched_chat_word:
                warn_msg = f"⚠️ သင့်စာထဲတွင် Group မှပိတ်ပင်ထားသော စကားပါနေသည်။ ({matched_chat_word})"
            else:
                warn_msg = data.get("warning_text") or "⚠️ သတိပေးချက်: သင့်စာသားတွင် ဂျိုင်း/ဘိုင်အို/လင့် တစ်ခုခုပါသည်။"
            bot.send_message(chat_id, warn_msg)
            
            try:
                reason = "forward" if is_forwarded else detect_reason(check_text)
            except:
                reason = "spam"
            
            key = strike_key(chat_id, user_id)
            strikes = data["strikes"].get(key, 0) + 1
            data["strikes"][key] = strikes
            save_data()
            
            if strikes >= 3:
                group_mute_times = data.get("group_mute_times", {})
                current_mute_duration = group_mute_times.get(str(chat_id), data.get("mute_time", 60))
        
                until_date = int(time.time()) + current_mute_duration
                try:
                    bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(), until_date=until_date)
                except Exception as e: 
                    pass
                
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton("🔓 Unmute", callback_data=f"unmute:{user_id}"))
                user_label    = "<b>User:</b>"
                reason_label  = "<b>အကြောင်းပြချက်:</b>"
                time_label    = "<b>ကြာချိန်:</b>"

                bot.send_message(
                    chat_id,
                    f"<tg-emoji emoji-id='6174589325695521740'>❌</tg-emoji> <b>𝐀𝐮𝐭𝐨 𝐦𝐮𝐭𝐞</b> <tg-emoji emoji-id='6257780484281997093'>❌</tg-emoji>\n\n"
                    f"<blockquote>"
                    f"<tg-emoji emoji-id='4913497231492908158'>👤</tg-emoji> <code> </code>{user_label} {mention(message.from_user)} <tg-emoji emoji-id='6177007478182516158'>✨</tg-emoji>\n\n"
                    f"<tg-emoji emoji-id='4918087434840834979'>ℹ️</tg-emoji> <code> </code>{reason_label} (ဘိုင်အို/ဂျိုင်း/လင့်) ၃ ကြိမ်ပို့ခြင်း\n"
                    f"<tg-emoji emoji-id='4904882772637648609'>⏱️</tg-emoji> <code> </code>{time_label} {current_mute_duration} စက္ကန့်\n\n"
                    f"<tg-emoji emoji-id='5123230779593196220'>⏳</tg-emoji> <code> </code>သတ်မှတ်ချိန်ပြည့်ပါက အလိုအလျောက် Unmute ဖြစ်ပါမည်။"
                    f"</blockquote>",
                    reply_markup=kb,
                    parse_mode="HTML"
              )
                data["strikes"][key] = 0
                save_data()
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
            
            try: 
                bot.delete_message(chat_id, message.message_id)
            except Exception as e: 
                pass
            return
        else:
            return

    # Text-to-Text သင်ယူခြင်းအပိုင်းသာ ကျန်တော့မည် (Sticker သင်ယူမှု လုံးဝဖြုတ်ထားပါပြီ)
    if message.reply_to_message:
        if message.reply_to_message.content_type == 'text':
            parent = message.reply_to_message.text.strip().lower() if message.reply_to_message.text else None
            if parent:
                if message.content_type == 'text':
                    current_reply = message.html_text 
                    if is_clean_text(current_reply):
                        save_to_brain(parent, current_reply)
                        return 

    if not message.text or not message.text.startswith("/"):
        user_input = message.text.lower() if message.text else None

        chat_key = str(chat_id)
        chat_reply_on = data.get("reply_on_chats", {}).get(chat_key, True)

        if user_input and chat_reply_on and message.content_type == 'text':
            reply_text = get_reply(user_input)
            try:
                if reply_text:
                    bot.reply_to(message, reply_text, parse_mode=None)
            except Exception as e:
                print(f"⚠️ Error sending reply: {e}")

# ======================
# RUN 
# ======================
if __name__ == '__main__':
    init_db()
    print("🤖 Dating Bot is starting...")
    while True:
        try:
            print("🚀 Bot is now online and will only reply to new messages.")
            bot.infinity_polling(timeout=90, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            print(f"⚠️ Connection Error: {e}")
            print("🔄 5 seconds နေရင် ပြန်စပါမယ်...")
            time.sleep(5)
