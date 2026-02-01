
from models import User

import os
from dotenv import load_dotenv

from sqlalchemy import update, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

import telebot
from telebot import apihelper
import json
import os

load_dotenv()  # Take environment variables from .env.

bot_token = os.getenv('BOT_TOKEN')

# 1. SETUP: Put your BALE bot token here
BOT_TOKEN = bot_token

# 2. CRITICAL STEP: Override the server URL to point to Baleh
# This is what makes a "Telegram" library work with Baleh.
apihelper.API_URL = "https://tapi.bale.ai/bot{0}/{1}"

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

database_url = os.getenv('DATABASE_URL')
DATABASE_URL = database_url

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# --- DATABASE FUNCTIONS ---
def add_user(user_id: int, first_name: str = None, username: str = None):
    """
    Registers a user in Postgres if they don't exist.
    Returns True if a new user was created, False if they already existed.
    """
    with SessionLocal() as session:
        with session.begin():
            # 1. Check if user exists using primary key
            user = session.get(User, user_id)

            if not user:
                # 2. Create new user instance
                new_user = User(
                    user_id=user_id,
                    first_name=first_name,
                    username=username,
                    role="employee",  # Default role
                    status="pending_approval"  # Default status
                )
                session.add(new_user)
                return True

            return False  # User already exists


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
    try:
        ADMIN_ID = int(os.getenv('ADMIN_ID'))
    except ValueError as e:
        print(f"Error: {e}")

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


async def update_activity(session: AsyncSession, user_id: int):
    """
    Updates the last_seen column.
    We use 'update' specifically for performance instead of loading the whole object.
    """
    try:
        stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(last_seen=func.now())
        )
        await session.execute(stmt)
        await session.commit()
    except Exception as e:
        await session.rollback()
        print(f"Error updating activity for {user_id}: {e}")

# --- MAIN LOOP ---
print("Bale Bot Started...")
try:
    bot.infinity_polling()
except Exception as e:
    print(f"Error: {e}")