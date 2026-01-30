import telebot
from telebot import apihelper
import json
import os

# 1. SETUP: Put your BALE bot token here
BOT_TOKEN = 'YOUR_BALE_BOT_TOKEN'

# 2. CRITICAL STEP: Override the server URL to point to Baleh
# This is what makes a "Telegram" library work with Baleh.
apihelper.API_URL = "https://tapi.bale.ai/bot{0}/{1}"

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

# File to store user IDs (simple database)
DB_FILE = "bale_users.json"


# --- DATABASE FUNCTIONS ---
def add_user(user_id):
    """Saves the user ID to a file if not already present."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump([], f)

    with open(DB_FILE, 'r') as f:
        users = json.load(f)

    if user_id not in users:
        users.append(user_id)
        with open(DB_FILE, 'w') as f:
            json.dump(users, f)
        return True
    return False


def get_all_users():
    """Returns a list of all user IDs."""
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r') as f:
        return json.load(f)


# --- BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name

    # Save user to database
    is_new = add_user(user_id)

    if is_new:
        bot.reply_to(message, f"Hello {first_name}! You have been added to the broadcast list.")
        print(f"New User: {user_id} - {first_name}")
    else:
        bot.reply_to(message, "You are already on the list.")


@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    # SECURITY: Replace '12345678' with your own numeric ID to prevent others from using this
    # You can see your ID printed in the console when you use /start
    ADMIN_ID = 12345678

    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "You are not authorized to broadcast.")
        return

    # Get the message text (remove '/broadcast ' from the start)
    msg = message.text.replace('/broadcast ', '')

    if len(msg) < 2:
        bot.reply_to(message, "Please provide a message. Example: /broadcast Hello All")
        return

    users = get_all_users()
    bot.reply_to(message, f"Broadcasting to {len(users)} users...")

    count = 0
    for uid in users:
        try:
            bot.send_message(uid, msg)
            count += 1
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")

    bot.reply_to(message, f"Broadcast complete. Sent to {count} users.")


# --- MAIN LOOP ---
print("Bale Bot Started...")
try:
    bot.infinity_polling()
except Exception as e:
    print(f"Error: {e}")