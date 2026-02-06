from models import User, Issue, init_db

import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

import telebot
from telebot import apihelper, types

load_dotenv()  # Take environment variables from .env.

bot_token = os.getenv('BOT_TOKEN')
BOT_TOKEN = bot_token

# CRITICAL STEP: Override the server URL to point to Baleh
apihelper.API_URL = "https://tapi.bale.ai/bot{0}/{1}"

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

database_url = os.getenv('DATABASE_URL')
DATABASE_URL = database_url

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Get admin ID from environment
try:
    ADMIN_ID = int(os.getenv('ADMIN_ID'))
except (ValueError, TypeError):
    print("Warning: ADMIN_ID not set or invalid. Broadcast functionality will be disabled.")
    ADMIN_ID = None


# --- DATABASE FUNCTIONS ---

def add_user(user_id: int, first_name: str = None, username: str = None):
    """
    Registers a user in Postgres if they don't exist.
    Returns True if a new user was created, False if they already existed.
    """
    with SessionLocal() as session:
        with session.begin():
            user = session.get(User, user_id)

            if not user:
                new_user = User(
                    user_id=user_id,
                    first_name=first_name,
                    username=username,
                    role="employee",
                    status="pending_approval"
                )
                session.add(new_user)
                return True

            return False


def get_all_users():
    """Returns a list of all user IDs."""
    with SessionLocal() as session:
        users = session.query(User.user_id).all()
        return [user.user_id for user in users]


def is_admin(user_id: int):
    """Check if user is an admin."""
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user:
            return user.role in ['admin', 'super_admin']
        return False


def create_issue(title: str, message: str, created_by: int):
    """Create a new issue in the database."""
    with SessionLocal() as session:
        with session.begin():
            new_issue = Issue(
                title=title,
                message=message,
                created_by=created_by,
                status="open"
            )
            session.add(new_issue)
            session.flush()  # Get the ID before committing
            issue_id = new_issue.id
            return issue_id


def get_open_issues():
    """Get all open issues."""
    with SessionLocal() as session:
        issues = session.query(Issue).filter(Issue.status == 'open').order_by(Issue.created_at.desc()).all()
        # Convert to dict to avoid detached instance issues
        return [{
            'id': issue.id,
            'title': issue.title,
            'message': issue.message,
            'created_at': issue.created_at,
            'created_by': issue.created_by
        } for issue in issues]


def close_issue(issue_id: int, resolution: str, closed_by: int):
    """Close an issue with resolution."""
    with SessionLocal() as session:
        with session.begin():
            issue = session.get(Issue, issue_id)
            if issue:
                issue.status = 'closed'
                issue.resolution = resolution
                issue.closed_by = closed_by
                issue.closed_at = func.now()
                session.flush()
                return {
                    'id': issue.id,
                    'title': issue.title,
                    'message': issue.message,
                    'resolution': resolution
                }
    return None


def update_last_seen(user_id: int):
    """Update user's last_seen timestamp."""
    with SessionLocal() as session:
        with session.begin():
            user = session.get(User, user_id)
            if user:
                user.last_seen = func.now()


# --- KEYBOARD HELPERS ---

def get_user_keyboard():
    """Create keyboard for regular users."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("📋 Help"),
    )
    return keyboard


def get_admin_keyboard():
    """Create keyboard for admin users."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    keyboard.add(
        types.KeyboardButton("📢 Broadcast Issue"),
        types.KeyboardButton("📋 View Open Issues"),
        types.KeyboardButton("📝 My Issues")
    )
    keyboard.add(
        types.KeyboardButton("❌ Cancel"),
        types.KeyboardButton("❓ Help")
    )
    return keyboard


# --- BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username

    # Save user to database
    is_new = add_user(user_id, first_name, username)
    update_last_seen(user_id)

    # Get appropriate keyboard
    keyboard = get_admin_keyboard() if is_admin(user_id) else get_user_keyboard()

    if is_new:
        bot.reply_to(message,
                     f"Hello {first_name}! 👋\n\n"
                     f"You have been registered in the system.\n"
                     f"Your account is pending approval.\n\n"
                     f"Use the buttons below or type /help for commands.",
                     reply_markup=keyboard
                     )
        print(f"New User: {user_id} - {first_name} (@{username})")
    else:
        bot.reply_to(message,
                     f"Welcome back, {first_name}!\n\n"
                     f"Use the buttons below or type /help for commands.",
                     reply_markup=keyboard
                     )


@bot.message_handler(commands=['help'])
def handle_help(message):
    user_id = message.chat.id
    update_last_seen(user_id)

    help_text = """📋 *Available Commands:*

/start - Register or login
/help - Show this help message
/menu - Show button menu
/hide - Hide button menu
"""

    if is_admin(user_id):
        help_text += """
*Admin Commands:*
/broadcast - Create and broadcast a new issue (multi-step)
/issues - View all open issues
/myissues - View issues you created

💡 _Tip: Use the buttons below for quick access!_
"""
    else:
        help_text += """
💡 _Tip: Use the buttons below for quick access!_
"""

    bot.reply_to(message, help_text, parse_mode='Markdown')


@bot.message_handler(commands=['menu'])
def handle_menu(message):
    """Show the keyboard menu."""
    user_id = message.chat.id
    update_last_seen(user_id)

    keyboard = get_admin_keyboard() if is_admin(user_id) else get_user_keyboard()

    bot.reply_to(message,
                 "🎛 Here's your menu! Use the buttons below:",
                 reply_markup=keyboard
                 )


@bot.message_handler(commands=['hide'])
def handle_hide(message):
    """Hide the keyboard menu."""
    user_id = message.chat.id
    update_last_seen(user_id)

    # Create a remove keyboard markup
    remove_keyboard = types.ReplyKeyboardRemove()

    bot.reply_to(message,
                 "✅ Keyboard hidden. Use /menu to show it again.",
                 reply_markup=remove_keyboard
                 )


@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    user_id = message.chat.id
    update_last_seen(user_id)

    # Check if user is admin
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to broadcast messages.")
        return

    # Start the multistep conversation
    msg = bot.reply_to(message, "📝 Please enter the *title* of the issue:", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_issue_title, user_id)


def process_issue_title(message, admin_id):
    """Process the issue title and ask for description."""
    title = message.text.strip()

    if title == "❌ Cancel":
        bot.reply_to(message, "Cancelling...")
        return

    if len(title) < 3:
        msg = bot.reply_to(message, "❌ Title too short. Please enter a title (minimum 3 characters):")
        bot.register_next_step_handler(msg, process_issue_title, admin_id)
        return

    if len(title) > 255:
        msg = bot.reply_to(message, "❌ Title too long (maximum 255 characters). Please enter a shorter title:")
        bot.register_next_step_handler(msg, process_issue_title, admin_id)
        return

    # Ask for description
    msg = bot.reply_to(message, "✅ Title received!\n\n📝 Now please enter the *description* of the issue:",
                       parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_issue_description, admin_id, title)


def process_issue_description(message, admin_id, title):
    """Process the issue description and create the issue."""
    description = message.text.strip()

    if description == "❌ Cancel":
        bot.reply_to(message, "Cancelling...")
        return

    if len(description) < 10:
        msg = bot.reply_to(message, "❌ Description too short. Please provide more details (minimum 10 characters):")
        bot.register_next_step_handler(msg, process_issue_description, admin_id, title)
        return

    # Create issue in database
    issue_id = create_issue(title, description, admin_id)
    issue_ref = f"ISSUE-{issue_id:03d}"

    # Format the broadcast message
    broadcast_msg = (
        f"🚨 *New Issue: {issue_ref}*\n\n"
        f"*Title:* {title}\n\n"
        f"*Description:*\n{description}\n\n"
        f"_This issue will be tracked and resolved by our team._"
    )

    users = get_all_users()
    bot.reply_to(message, f"📤 Broadcasting to {len(users)} users...")

    success_count = 0
    fail_count = 0

    for uid in users:
        try:
            bot.send_message(uid, broadcast_msg, parse_mode='Markdown')
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Failed to send to {uid}: {e}")

    bot.reply_to(message,
                 f"✅ Broadcast complete!\n\n"
                 f"Issue ID: {issue_ref}\n"
                 f"Title: {title}\n"
                 f"✓ Sent to: {success_count} users\n"
                 f"✗ Failed: {fail_count} users"
                 )


@bot.message_handler(commands=['issues'])
def handle_issues(message):
    user_id = message.chat.id
    update_last_seen(user_id)

    # Check if user is admin
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to view issues.")
        return

    issues = get_open_issues()

    if not issues:
        bot.reply_to(message, "✅ No open issues at the moment!")
        return

    # Create inline keyboard with issue buttons
    markup = types.InlineKeyboardMarkup(row_width=1)

    for issue in issues:
        issue_id = issue['id']
        # Use title for button display
        title = issue['title']
        button_text = f"ISSUE-{issue_id:03d}: {title}"

        # Create callback data
        callback_data = f"view_issue_{issue_id}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))

    bot.send_message(
        message.chat.id,
        f"📋 *Open Issues ({len(issues)})*\n\nClick on an issue to view details and close it:",
        reply_markup=markup,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['myissues'])
def handle_my_issues(message):
    user_id = message.chat.id
    update_last_seen(user_id)

    # Check if user is admin
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to view issues.")
        return

    with SessionLocal() as session:
        issues = session.query(Issue).filter(
            Issue.created_by == user_id,
            Issue.status == 'open'
        ).order_by(Issue.created_at.desc()).all()

        issues_data = [{
            'id': issue.id,
            'title': issue.title,
            'message': issue.message,
            'created_at': issue.created_at
        } for issue in issues]

    if not issues_data:
        bot.reply_to(message, "✅ You have no open issues!")
        return

    # Create inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=1)

    for issue in issues_data:
        issue_id = issue['id']
        title = issue['title']
        button_text = f"ISSUE-{issue_id:03d}: {title}"
        callback_data = f"view_issue_{issue_id}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))

    bot.send_message(
        message.chat.id,
        f"📋 *Your Open Issues ({len(issues_data)})*\n\nClick on an issue to view details:",
        reply_markup=markup,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['cancel'])
def handle_cancel(message):
    user_id = message.chat.id
    update_last_seen(user_id)


# --- CALLBACK QUERY HANDLERS (for inline buttons) ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_issue_'))
def callback_view_issue(call):
    """Handle viewing issue details."""
    user_id = call.from_user.id
    update_last_seen(user_id)

    # Extract issue ID from callback data
    issue_id = int(call.data.split('_')[2])

    with SessionLocal() as session:
        issue = session.get(Issue, issue_id)

        if not issue:
            bot.answer_callback_query(call.id, "❌ Issue not found!")
            return

        if issue.status == 'closed':
            bot.answer_callback_query(call.id, "This issue has already been closed!")
            return

        issue_data = {
            'id': issue.id,
            'title': issue.title,
            'message': issue.message,
            'created_at': issue.created_at
        }

    # Format issue details
    issue_text = (
        f"🔍 *Issue Details*\n\n"
        f"*ID:* ISSUE-{issue_data['id']:03d}\n"
        f"*Status:* Open\n"
        f"*Created:* {issue_data['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        f"*Title:*\n{issue_data['title']}\n\n"
        f"*Description:*\n{issue_data['message']}"
    )

    # Create buttons for closing the issue
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✅ Close This Issue", callback_data=f"close_issue_{issue_id}"),
        types.InlineKeyboardButton("« Back to Issues List", callback_data="back_to_issues")
    )

    # Edit the message to show issue details
    bot.edit_message_text(
        issue_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('close_issue_'))
def callback_close_issue(call):
    """Handle closing an issue - ask for resolution."""
    user_id = call.from_user.id
    update_last_seen(user_id)

    issue_id = int(call.data.split('_')[2])

    # Store the issue_id in a temporary way (we'll use a simple approach)
    # In production, you'd want to use a proper state management
    bot.send_message(
        call.message.chat.id,
        f"📝 Please provide the resolution for ISSUE-{issue_id:03d}:\n\n"
        f"Reply to this message with how the issue was resolved.",
        reply_markup=types.ForceReply(selective=True)
    )

    # Store issue_id for the next message
    # We'll use message_id as a simple key
    bot.answer_callback_query(call.id, "Please send the resolution details...")

    # Register next step handler
    bot.register_next_step_handler(call.message, process_issue_resolution, issue_id, user_id)


def process_issue_resolution(message, issue_id, admin_id):
    """Process the resolution text and close the issue."""
    resolution = message.text.strip()

    if len(resolution) < 10:
        bot.reply_to(message, "❌ Resolution too short. Please provide more details.")
        return

    # Close the issue
    issue_data = close_issue(issue_id, resolution, admin_id)

    if not issue_data:
        bot.reply_to(message, "❌ Failed to close issue. It may have already been closed.")
        return

    # Notify the admin
    bot.reply_to(message,
                 f"✅ *Issue Closed Successfully!*\n\n"
                 f"*ID:* ISSUE-{issue_id:03d}\n"
                 f"*Title:* {issue_data['title']}\n"
                 f"*Resolution:* {resolution}\n\n"
                 f"Broadcasting resolution to all users...",
                 parse_mode='Markdown'
                 )

    # Broadcast the resolution to all users
    resolution_msg = (
        f"✅ *Issue Resolved: ISSUE-{issue_id:03d}*\n\n"
        f"*Title:*\n{issue_data['title']}\n\n"
        f"*Original Issue:*\n{issue_data['message']}\n\n"
        f"*Resolution:*\n{resolution}\n\n"
        f"_This issue has been marked as closed._"
    )

    users = get_all_users()
    success_count = 0

    for uid in users:
        try:
            bot.send_message(uid, resolution_msg, parse_mode='Markdown')
            success_count += 1
        except Exception as e:
            print(f"Failed to send resolution to {uid}: {e}")

    bot.send_message(
        message.chat.id,
        f"📤 Resolution broadcast complete!\n"
        f"✓ Sent to {success_count} users"
    )


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_issues')
def callback_back_to_issues(call):
    """Go back to issues list."""
    user_id = call.from_user.id
    update_last_seen(user_id)

    issues = get_open_issues()

    if not issues:
        bot.edit_message_text(
            "✅ No open issues at the moment!",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return

    # Recreate the issues list
    markup = types.InlineKeyboardMarkup(row_width=1)

    for issue in issues:
        issue_id = issue['id']
        title = issue['title']
        button_text = f"ISSUE-{issue_id:03d}: {title}"
        callback_data = f"view_issue_{issue_id}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))

    bot.edit_message_text(
        f"📋 *Open Issues ({len(issues)})*\n\nClick on an issue to view details and close it:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

    bot.answer_callback_query(call.id)


# --- KEYBOARD BUTTON HANDLERS ---

@bot.message_handler(func=lambda message: message.text == "📋 Help" or message.text == "❓ Help")
def button_help(message):
    handle_help(message)

@bot.message_handler(func=lambda message: message.text == "❌ Cancel")
def button_cancel(message):
    handle_cancel(message)

@bot.message_handler(func=lambda message: message.text == "📢 Broadcast Issue")
def button_broadcast(message):
    handle_broadcast(message)


@bot.message_handler(func=lambda message: message.text == "📋 View Open Issues")
def button_issues(message):
    handle_issues(message)


@bot.message_handler(func=lambda message: message.text == "📝 My Issues")
def button_my_issues(message):
    handle_my_issues(message)


# Track all messages to update last_seen
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Catch-all handler for updating activity."""
    user_id = message.chat.id
    update_last_seen(user_id)

    bot.reply_to(message,
                 "I don't understand that command. Use /help to see available commands."
                 )


# --- MAIN LOOP ---
if __name__ == "__main__":
    print("🤖 Bale Bot Started...")
    print(f"Admin ID: {ADMIN_ID}")

    # Initialize database tables if they don't exist
    try:
        init_db()
    except Exception as e:
        print(f"Database initialization note: {e}")

    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Error: {e}")