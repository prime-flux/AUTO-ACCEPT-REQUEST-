import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes
import json
import os
from datetime import datetime

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - Replace these with your values
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = YOUR_ADMIN_TELEGRAM_ID  # Your Telegram user ID (number)

# Your Private Channels - Just add bot as admin, no manual setup needed!
# Leave this list empty - bot will auto-detect channels!
APPROVED_CHANNELS = {}  # Auto-populated

PROMOTION_MESSAGE = "🌟 All join requests are auto-approved! Just click the channel links below."

# Data storage
join_requests_db = []
content_requests_db = []
users_db = set()
channels_db = {}

# Load data from file
def load_data():
    global join_requests_db, content_requests_db, users_db, channels_db
    try:
        if os.path.exists('bot_data.json'):
            with open('bot_data.json', 'r') as f:
                data = json.load(f)
                join_requests_db.extend(data.get('join_requests', []))
                content_requests_db.extend(data.get('content_requests', []))
                users_db.update(data.get('users', []))
                channels_db.update(data.get('channels', {}))
    except Exception as e:
        logger.error(f"Error loading data: {e}")

# Save data to file
def save_data():
    try:
        with open('bot_data.json', 'w') as f:
            json.dump({
                'join_requests': join_requests_db,
                'content_requests': content_requests_db,
                'users': list(users_db),
                'channels': channels_db
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

# Handle chat join requests - AUTO APPROVE
async def handle_chat_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically approve all join requests"""
    try:
        chat = update.chat_join_request.chat
        user = update.chat_join_request.from_user
        
        # Save channel info
        if str(chat.id) not in channels_db:
            channels_db[str(chat.id)] = {
                'title': chat.title,
                'username': chat.username or 'Private',
                'id': chat.id,
                'type': chat.type,
                'join_requests': 0
            }
        
        channels_db[str(chat.id)]['join_requests'] = channels_db[str(chat.id)].get('join_requests', 0) + 1
        
        # Log join request
        join_data = {
            'user_id': user.id,
            'username': user.username or 'No username',
            'first_name': user.first_name,
            'channel_id': chat.id,
            'channel_name': chat.title,
            'timestamp': datetime.now().isoformat(),
            'status': 'approved'
        }
        join_requests_db.append(join_data)
        save_data()
        
        # AUTO APPROVE the join request
        await context.bot.approve_chat_join_request(
            chat_id=chat.id,
            user_id=user.id
        )
        
        logger.info(f"✅ Auto-approved: {user.first_name} (@{user.username}) in {chat.title}")
        
        # Send welcome message to user
        welcome_text = f"""
✅ Welcome! You've been approved!

🎉 Channel: {chat.title}
👤 Welcome {user.first_name}!

Your join request was automatically approved by our bot. Enjoy the content! 🚀

{PROMOTION_MESSAGE}
"""
        
        try:
            # Create button to open channel
            keyboard = [[InlineKeyboardButton("📢 Open Channel", url=f"https://t.me/{chat.username if chat.username else 'c/' + str(chat.id)[4:]}")]]
            if chat.username:
                keyboard[0][0] = InlineKeyboardButton("📢 Open Channel", url=f"https://t.me/{chat.username}")
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=user.id,
                text=welcome_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Could not send welcome message to user: {e}")
        
        # Notify admin
        admin_notification = f"""
✅ Auto-Approved Join Request

👤 User: {user.first_name} (@{user.username})
🆔 User ID: {user.id}
📢 Channel: {chat.title}
⏰ Time: {datetime.now().strftime('%d-%m-%Y %H:%M')}

Total approvals in this channel: {channels_db[str(chat.id)]['join_requests']}
"""
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_notification
            )
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
            
    except Exception as e:
        logger.error(f"Error handling join request: {e}")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "No username"
    
    users_db.add(user_id)
    save_data()
    
    keyboard = [
        [InlineKeyboardButton("📥 Request Content", callback_data='request')],
        [InlineKeyboardButton("ℹ️ How it Works", callback_data='help')]
    ]
    
    # Add channel buttons if we have any
    if channels_db:
        keyboard.insert(1, [InlineKeyboardButton("📢 Our Channels", callback_data='channels')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🤖 Welcome to Auto-Approve Bot!

Hi @{username}! 👋

✨ Features:
• ✅ AUTO-APPROVE join requests instantly
• 📥 Request content from channels
• 📊 Track all members
• 📢 Broadcast to users

🔐 How it works:
1. Join any of our private channels
2. Your request is APPROVED automatically
3. Enjoy instant access! 

{PROMOTION_MESSAGE}

Click below to get started! 👇
"""
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 How to Use:

🔐 JOIN CHANNELS:
1️⃣ Click on any channel link
2️⃣ Request to join
3️⃣ Get approved INSTANTLY by bot
4️⃣ No waiting needed!

📥 REQUEST CONTENT:
1️⃣ Click "Request Content"
2️⃣ Send your request
3️⃣ Posted to channels automatically

✅ All join requests are approved automatically!
⚡ Instant access to all channels!

💡 Note: Make sure you've started the bot to receive notifications.
"""
    
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text)
    else:
        await update.message.reply_text(help_text)

# Show channels list
async def show_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    if not channels_db:
        text = "📢 No channels connected yet!\n\nAdd the bot as admin in your channels."
    else:
        text = f"📢 OUR CHANNELS ({len(channels_db)}):\n\n"
        text += "Click to join any channel - Auto-approved! ✅\n\n"
        
        buttons = []
        for channel_id, info in channels_db.items():
            text += f"🔹 {info['title']}\n"
            text += f"   Members approved: {info.get('join_requests', 0)}\n\n"
            
            # Create button for channel
            if info['username'] and info['username'] != 'Private':
                buttons.append([InlineKeyboardButton(
                    f"📢 {info['title']}", 
                    url=f"https://t.me/{info['username']}"
                )])
        
        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
        
        if query:
            await query.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

# Handle button callbacks
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'request':
        await query.message.reply_text(
            "📝 Send Your Content Request:\n\n"
            "Type what you want:\n"
            "• Movie name\n"
            "• Series name\n"
            "• Any content\n\n"
            "Your request will be posted to channels!"
        )
        context.user_data['waiting_for_request'] = True
        
    elif query.data == 'help':
        await help_command(update, context)
        
    elif query.data == 'channels':
        await show_channels(update, context)

# Handle content requests
async def handle_content_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_request'):
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "Anonymous"
    first_name = update.effective_user.first_name or "User"
    request_text = update.message.text
    
    # Save request
    request_data = {
        'id': len(content_requests_db) + 1,
        'user_id': user_id,
        'username': username,
        'first_name': first_name,
        'request': request_text,
        'timestamp': datetime.now().isoformat()
    }
    content_requests_db.append(request_data)
    save_data()
    
    await update.message.reply_text(
        f"✅ Request Submitted!\n\n"
        f"🆔 Request ID: #{request_data['id']}\n"
        f"📝 Request: {request_text}\n\n"
        f"Admin will process your request soon!"
    )
    
    # Notify admin
    admin_msg = f"""
📥 New Content Request

🆔 ID: #{request_data['id']}
👤 User: {first_name} (@{username})
💬 User ID: {user_id}
📝 Request: {request_text}
⏰ {datetime.now().strftime('%d-%m-%Y %H:%M')}
"""
    
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")
    
    context.user_data['waiting_for_request'] = False

# Admin: Broadcast to users
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 Broadcast to All Users\n\n"
            "Usage: /broadcast <message>\n\n"
            "Example:\n"
            "/broadcast Welcome to our channel!"
        )
        return
    
    message = ' '.join(context.args)
    success = 0
    failed = 0
    
    await update.message.reply_text("📤 Broadcasting...")
    
    for user_id in users_db:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success += 1
        except Exception as e:
            failed += 1
    
    await update.message.reply_text(
        f"📊 Broadcast Complete!\n\n"
        f"✅ Sent: {success}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {len(users_db)}"
    )

# Admin: Stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return
    
    total_approvals = len(join_requests_db)
    total_content_requests = len(content_requests_db)
    total_users = len(users_db)
    total_channels = len(channels_db)
    
    # Channel breakdown
    channel_stats = ""
    for channel_id, info in channels_db.items():
        channel_stats += f"📢 {info['title']}\n"
        channel_stats += f"   Approvals: {info.get('join_requests', 0)}\n\n"
    
    stats_text = f"""
📊 BOT STATISTICS

👥 USERS:
   Bot Users: {total_users}

✅ JOIN REQUESTS:
   Total Auto-Approved: {total_approvals}

📥 CONTENT REQUESTS:
   Total Requests: {total_content_requests}

📢 CHANNELS ({total_channels}):
{channel_stats if channel_stats else "   No channels yet"}

⏰ Updated: {datetime.now().strftime('%d-%m-%Y %H:%M')}

🤖 Status: Active ✅
Auto-Approve: Enabled ✅
"""
    
    await update.message.reply_text(stats_text)

# Admin: Recent approvals
async def recent_approvals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return
    
    if not join_requests_db:
        await update.message.reply_text("📭 No approvals yet!")
        return
    
    recent = join_requests_db[-20:] if len(join_requests_db) >= 20 else join_requests_db
    
    text = "✅ RECENT AUTO-APPROVALS (Last 20):\n\n"
    for req in reversed(recent):
        text += f"👤 {req['first_name']} (@{req['username']})\n"
        text += f"📢 {req['channel_name']}\n"
        text += f"⏰ {req['timestamp'][:16]}\n\n"
    
    await update.message.reply_text(text)

# Admin: Content requests
async def content_requests_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return
    
    if not content_requests_db:
        await update.message.reply_text("📭 No content requests!")
        return
    
    recent = content_requests_db[-20:] if len(content_requests_db) >= 20 else content_requests_db
    
    text = "📥 CONTENT REQUESTS (Last 20):\n\n"
    for req in reversed(recent):
        text += f"🆔 #{req['id']} | @{req['username']}\n"
        text += f"📝 {req['request']}\n"
        text += f"⏰ {req['timestamp'][:16]}\n\n"
    
    await update.message.reply_text(text)

# Admin: Channels list
async def channels_list_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return
    
    if not channels_db:
        await update.message.reply_text(
            "📢 No channels connected!\n\n"
            "Add the bot as admin in your private channels.\n"
            "Bot will auto-detect channels when it receives join requests."
        )
        return
    
    text = f"📢 CONNECTED CHANNELS ({len(channels_db)}):\n\n"
    
    for channel_id, info in channels_db.items():
        text += f"🔹 {info['title']}\n"
        text += f"   Type: {info['type']}\n"
        text += f"   Username: @{info['username'] if info['username'] != 'Private' else 'Private'}\n"
        text += f"   ID: {channel_id}\n"
        text += f"   Approvals: {info.get('join_requests', 0)}\n\n"
    
    await update.message.reply_text(text)

# Admin panel
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return
    
    admin_text = f"""
🔐 ADMIN PANEL

📊 STATISTICS:
/stats - Bot statistics
/approvals - Recent approvals
/requests - Content requests
/channels - Connected channels
/users - User list

📢 ACTIONS:
/broadcast <msg> - Message all users

ℹ️ /admin - This panel

🤖 Bot Info:
✅ Auto-Approve: Active
📢 Channels: {len(channels_db)}
👥 Users: {len(users_db)}
✅ Approvals: {len(join_requests_db)}
"""
    
    await update.message.reply_text(admin_text)

# Users list
async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return
    
    text = f"👥 Total Users: {len(users_db)}\n\n"
    
    for i, uid in enumerate(list(users_db)[:50], 1):
        text += f"{i}. {uid}\n"
    
    if len(users_db) > 50:
        text += f"\n... and {len(users_db) - 50} more"
    
    await update.message.reply_text(text)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# Main function
def main():
    load_data()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # CRITICAL: Chat join request handler for auto-approval
    application.add_handler(ChatMemberHandler(handle_chat_join_request, ChatMemberHandler.CHAT_MEMBER))
    
    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Admin commands
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("approvals", recent_approvals))
    application.add_handler(CommandHandler("requests", content_requests_list))
    application.add_handler(CommandHandler("channels", channels_list_admin))
    application.add_handler(CommandHandler("users", users_list))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_content_request))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("🤖 Auto-Approve Bot Started!")
    logger.info(f"👤 Admin ID: {ADMIN_ID}")
    logger.info("✅ Auto-approval enabled for all channels!")
    logger.info("📢 Add bot as admin in your channels to enable auto-approval")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()