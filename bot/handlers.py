import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlmodel import Session, select

from bot.models import Target, SavedCommunity, ProxyAccount, engine, get_target, save_target, get_saved_communities, save_cookie, get_cookie, create_db_and_tables, save_proxy, get_proxy, clear_proxy, save_proxy_list, get_proxy_accounts, clear_all_proxies, parse_residential_proxy, save_communities
from bot.scheduler import CommunityScheduler
from bot.twitter_api import TwitterAPI

# Try to import element detector if available
try:
    from bot.element_community_detector import ElementCommunityDetector
    from bot.cookie_manager import CookieManager
    ELEMENT_DETECTION_AVAILABLE = True
except ImportError:
    ELEMENT_DETECTION_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Initialize bot and dispatcher with FSM storage
TOKEN = os.getenv("BOT_TOKEN", "7847904250:AAEJSJzDL0gh4xKo3ZBeZVsX39WXLLcmxE8")
POLL_INTERVAL_MIN = int(os.getenv("POLL_INTERVAL_MIN", "5"))
TG_CHAT_ID_WHITELIST = os.getenv("TG_CHAT_ID_WHITELIST", "").split(",") if os.getenv("TG_CHAT_ID_WHITELIST") else []

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Function to get TwitterAPI instance with current proxy configuration
def get_twitter_api():
    """Get TwitterAPI instance with current proxy configuration"""
    proxy_accounts = get_proxy_accounts()
    if proxy_accounts:
        # Use database proxy rotation
        return TwitterAPI()
    else:
        # Fallback to legacy proxy
        proxy = get_proxy()
        return TwitterAPI(proxy=proxy)

# Global variables will be initialized after all functions are defined
twitter_api = None
scheduler = None
_globals_initialized = False

def initialize_globals():
    """Initialize global variables"""
    global twitter_api, scheduler, _globals_initialized
    
    # Prevent duplicate initialization
    if _globals_initialized:
        logging.info("Globals already initialized, skipping...")
        return
    
    twitter_api = get_twitter_api()
    scheduler = CommunityScheduler(twitter_api)
    scheduler.set_bot(bot)
    _globals_initialized = True
    
    # Initialize element detection if available
    if ELEMENT_DETECTION_AVAILABLE:
        global cookie_manager, element_detector
        cookie_manager = CookieManager()
        element_detector = ElementCommunityDetector(cookie_manager)

def force_reinitialize_globals():
    """Force reinitialize global variables (used when proxy settings change)"""
    global twitter_api, scheduler, _globals_initialized
    
    logging.info("Force reinitializing globals due to proxy change...")
    
    # Stop existing scheduler if running
    if scheduler and scheduler.is_active():
        scheduler.stop()
    
    # Reset flag and reinitialize
    _globals_initialized = False
    initialize_globals()

# Define FSM states
class BotStates(StatesGroup):
    waiting_for_target = State()
    waiting_for_cookie = State()
    waiting_for_proxy = State()
    waiting_for_proxy_list = State()

# Create main menu keyboard with inline buttons
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📋 Set Target", callback_data="action:set_target"),
        InlineKeyboardButton(text="🍪 Set Cookie", callback_data="action:set_cookie"),
        InlineKeyboardButton(text="🌐 Proxy Settings", callback_data="action:proxy_menu"),
        InlineKeyboardButton(text="▶️ Start Tracking", callback_data="action:start_tracking"),
        InlineKeyboardButton(text="⏹️ Stop Tracking", callback_data="action:stop_tracking"),
        InlineKeyboardButton(text="ℹ️ Status", callback_data="action:status"),
        InlineKeyboardButton(text="📊 Communities", callback_data="action:communities")
    )
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

# Create proxy management keyboard
def get_proxy_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🌐 Set Single Proxy", callback_data="action:set_proxy"),
        InlineKeyboardButton(text="📋 Set Proxy List", callback_data="action:set_proxy_list"),
        InlineKeyboardButton(text="👁️ View Proxies", callback_data="action:view_proxies"),
        InlineKeyboardButton(text="🗑️ Clear All Proxies", callback_data="action:clear_proxies"),
        InlineKeyboardButton(text="🔙 Back", callback_data="action:back")
    )
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

# Create interval keyboard
def get_interval_keyboard():
    builder = InlineKeyboardBuilder()
    for interval in [1, 3, 5, 10, 15, 30]:
        builder.add(InlineKeyboardButton(
            text=f"{interval} min",
            callback_data=f"interval:{interval}"
        ))
    builder.add(InlineKeyboardButton(text="🔙 Back", callback_data="action:back"))
    builder.adjust(3)  # 3 buttons per row
    return builder.as_markup()

# Create target selection keyboard
def get_target_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Custom Target", callback_data="target:custom"),
        InlineKeyboardButton(text="🔙 Back", callback_data="action:back")
    )
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()

# Create communities keyboard
def get_communities_keyboard(communities):
    builder = InlineKeyboardBuilder()
    
    if communities:
        for i, community in enumerate(communities):
            builder.add(InlineKeyboardButton(
                text=f"{community.name}",
                callback_data=f"community:{community.community_id}"
            ))
    else:
        builder.add(InlineKeyboardButton(
            text="No communities found",
            callback_data="community:none"
        ))
    
    builder.add(InlineKeyboardButton(text="🔄 Refresh", callback_data="action:refresh_communities"))
    builder.add(InlineKeyboardButton(text="🔙 Back", callback_data="action:back"))
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handler for /start command - the only command needed to start using the bot"""
    # Check if user is in whitelist if whitelist is enabled
    if TG_CHAT_ID_WHITELIST and str(message.chat.id) not in TG_CHAT_ID_WHITELIST:
        await message.answer("You are not authorized to use this bot.")
        return
        
    await message.answer(
        "Welcome to Twitter Community Tracker Console!\n\n"
        "Use the buttons below to control the bot:",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("action:"))
async def process_action_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Process main menu button clicks"""
    # Check if user is in whitelist if whitelist is enabled
    if TG_CHAT_ID_WHITELIST and str(callback_query.message.chat.id) not in TG_CHAT_ID_WHITELIST:
        await callback_query.answer("You are not authorized to use this bot.")
        return
        
    await callback_query.answer()
    action = callback_query.data.split(":")[1]
    
    if action == "set_target":
        await callback_query.message.edit_text(
            "Select a Twitter handle to track or choose 'Custom Target' to enter manually:",
            reply_markup=get_target_keyboard()
        )
    
    elif action == "set_cookie":
        # Show cookie upload method selection
        instructions = twitter_api.get_cookie_upload_methods()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Manual Method", callback_data="cookie_method:manual")],
            [InlineKeyboardButton(text="🚀 Auto-Enriched (Recommended)", callback_data="cookie_method:auto")],
            [InlineKeyboardButton(text="📥 Browser Export", callback_data="cookie_method:export")],
            [InlineKeyboardButton(text="📋 View Saved Cookies", callback_data="cookie_method:list")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="action:back")]
        ])
        
        await callback_query.message.edit_text(
            "🍪 **Cookie Upload Methods**\n\n"
            "Choose your preferred method for uploading Twitter cookies:\n\n"
            "🔧 **Manual**: Copy auth\\_token + ct0 only\n"
            "🚀 **Auto-Enriched**: Bot generates missing cookies automatically\n"
            "📥 **Browser Export**: Upload JSON export from browser\n"
            "📋 **View Saved**: Manage previously saved cookies",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    elif action == "proxy_menu":
        proxy_accounts = get_proxy_accounts()
        proxy_count = len(proxy_accounts)
        await callback_query.message.edit_text(
            f"Proxy Management\n\n"
            f"Active proxies: {proxy_count}\n"
            f"Residential proxy format supported\n\n"
            f"Choose an option:",
            reply_markup=get_proxy_keyboard()
        )
    
    elif action == "set_proxy_list":
        await state.set_state(BotStates.waiting_for_proxy_list)
        await callback_query.message.edit_text(
            "Please send your proxy list (one proxy per line).\n\n"
            "Supported formats:\n"
            "• Residential: `host:port:username:password`\n"
            "• HTTP with auth: `http://user:pass@host:port`\n"
            "• SOCKS5: `socks5://user:pass@host:port`\n"
            "• Simple: `host:port`\n\n"
            "Example residential proxy:\n"
            "`quality.proxywing.com:8888:pkg-private2-country-us-session-Do8WkypR:mfu9i9s0zyj6tibs`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="action:proxy_menu")]
            ])
        )
    
    elif action == "view_proxies":
        proxy_accounts = get_proxy_accounts()
        if not proxy_accounts:
            await callback_query.message.edit_text(
                "No proxies configured.\n\nAdd some proxies first.",
                reply_markup=get_proxy_keyboard()
            )
            return
        
        proxy_text = "🌐 **Active Proxies:**\n\n"
        for i, proxy in enumerate(proxy_accounts[:10]):  # Show first 10
            last_used = proxy.last_used_at.strftime('%H:%M') if proxy.last_used_at else 'Never'
            proxy_preview = proxy.proxy_string[:40] + "..." if len(proxy.proxy_string) > 40 else proxy.proxy_string
            proxy_text += f"{i+1}. `{proxy_preview}`\n   Last used: {last_used}\n\n"
        
        if len(proxy_accounts) > 10:
            proxy_text += f"... and {len(proxy_accounts) - 10} more proxies"
        
        await callback_query.message.edit_text(
            proxy_text,
            reply_markup=get_proxy_keyboard()
        )
    
    elif action == "clear_proxies":
        clear_all_proxies()
        # Also clear legacy proxy file
        try:
            os.remove("data/proxy.txt")
        except FileNotFoundError:
            pass
        
        # Reinitialize TwitterAPI without proxy
        force_reinitialize_globals()
        
        await callback_query.message.edit_text(
            "All proxies cleared! ✅\n\n"
            "Proxy accounts have been removed from the database.\n"
            "TwitterAPI reinitialized without proxy.",
            reply_markup=get_proxy_keyboard()
        )
    
    elif action == "set_proxy":
        await state.set_state(BotStates.waiting_for_proxy)
        await callback_query.message.edit_text(
            "Please enter your proxy URL (single proxy mode).\n\n"
            "Supported formats:\n"
            "• HTTP: `http://user:pass@proxy:port`\n"
            "• SOCKS5: `socks5://user:pass@proxy:port`\n"
            "• Residential: `host:port:username:password`\n"
            "• Without auth: `http://proxy:port`\n\n"
            "Send 'clear' to remove current proxy.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="action:proxy_menu")]
            ])
        )
    
    elif action == "start_tracking":
        with Session(engine) as session:
            target = get_target(session)
            
        if not target:
            await callback_query.message.edit_text(
                "No target set. Please set a target first.",
                reply_markup=get_main_keyboard()
            )
            return
            
        cookie = get_cookie()
        if not cookie:
            await callback_query.message.edit_text(
                "No cookie set. Please set a cookie first.",
                reply_markup=get_main_keyboard()
            )
            return
            
        await callback_query.message.edit_text(
            "Select polling interval:",
            reply_markup=get_interval_keyboard()
        )
    
    elif action == "stop_tracking":
        scheduler.stop()
        
        await callback_query.message.edit_text(
            "Tracking stopped.",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "status":
        with Session(engine) as session:
            target = get_target(session)
            communities = get_saved_communities(session)
        
        proxy_accounts = get_proxy_accounts()
        legacy_proxy = get_proxy()
        
        if not target:
            status_text = "No target set. Please set a target first."
        else:
            cookie_status = "✅ Set" if get_cookie() else "❌ Not set"
            if proxy_accounts:
                proxy_status = f"✅ {len(proxy_accounts)} proxies in rotation"
            elif legacy_proxy:
                proxy_status = "✅ Single proxy set"
            else:
                proxy_status = "❌ Not set"
            
            status_text = (
                f"Target: @{target.screen_name}\n"
                f"Cookie: {cookie_status}\n"
                f"Proxies: {proxy_status}\n"
                f"Tracking: {'Active' if scheduler.is_active() else 'Inactive'}\n"
                f"Interval: {scheduler.interval_minutes or 'Not set'} min\n"
                f"Last run: {scheduler.last_run.strftime('%Y-%m-%d %H:%M:%SZ') if scheduler.last_run else 'Never'}\n"
                f"Communities: {len(communities)}"
            )
        
        await callback_query.message.edit_text(
            status_text,
            reply_markup=get_main_keyboard()
        )
    
    elif action == "communities":
        with Session(engine) as session:
            target = get_target(session)
            communities = get_saved_communities(session)
        
        if not target:
            await callback_query.message.edit_text(
                "No target set. Please set a target first.",
                reply_markup=get_main_keyboard()
            )
            return
            
        await callback_query.message.edit_text(
            f"Communities for @{target.screen_name}:",
            reply_markup=get_communities_keyboard(communities)
        )
    
    elif action == "refresh_communities":
        with Session(engine) as session:
            target = get_target(session)
            
        if not target:
            await callback_query.message.edit_text(
                "No target set. Please set a target first.",
                reply_markup=get_main_keyboard()
            )
            return
            
        cookie = get_cookie()
        if not cookie:
            await callback_query.message.edit_text(
                "No cookie set. Please set a cookie first.",
                reply_markup=get_main_keyboard()
            )
            return
            
        # Show loading message
        await callback_query.message.edit_text(
            "Refreshing communities...",
            reply_markup=None
        )
        
        try:
            # Try element detection first if available
            if ELEMENT_DETECTION_AVAILABLE:
                try:
                    communities = await element_detector.detect_communities(target.screen_name)
                    if communities:
                        result_message = element_detector.format_detection_results(communities, target.screen_name)
                        await callback_query.message.edit_text(
                            result_message,
                            reply_markup=get_main_keyboard()
                        )
                        return
                except Exception as e:
                    logging.error(f"Element detection failed: {e}")
            
            # Fallback to original method
            await scheduler.check_communities(target.screen_name)
            
            # Get updated communities
            with Session(engine) as session:
                communities = get_saved_communities(session)
                
            await callback_query.message.edit_text(
                f"Communities for @{target.screen_name}:",
                reply_markup=get_communities_keyboard(communities)
            )
        except Exception as e:
            await callback_query.message.edit_text(
                f"Error refreshing communities: {str(e)}",
                reply_markup=get_main_keyboard()
            )
    
    elif action == "back":
        # Clear any waiting states
        await state.clear()
        
        await callback_query.message.edit_text(
            "Twitter Community Tracker Console\n\n"
            "Use the buttons below to control the bot:",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "main_menu":
        # Clear any waiting states
        await state.clear()
        
        await callback_query.message.edit_text(
            "🏠 **Twitter Community Tracker Console**\n\n"
            "Welcome back! Use the buttons below to control the bot:",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith("target:"))
async def process_target_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Process target selection"""
    await callback_query.answer()
    target = callback_query.data.split(":")[1]
    
    if target == "custom":
        await state.set_state(BotStates.waiting_for_target)
        await callback_query.message.edit_text(
            "Please enter a Twitter handle or user ID to track:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="action:back")]
            ])
        )
    else:
        # For predefined targets (not used in this version but kept for extensibility)
        with Session(engine) as session:
            target_obj = Target(
                user_id=target,
                screen_name=target,
                name=target
            )
            save_target(session, target_obj)
        
        await callback_query.message.edit_text(
            f"Target set: @{target}",
            reply_markup=get_main_keyboard()
        )

@dp.message(BotStates.waiting_for_target)
async def process_target_input(message: types.Message, state: FSMContext):
    """Process custom target input"""
    # Clear the waiting state
    await state.clear()
    
    target_handle = message.text.lstrip('@')
    
    # Show loading message
    loading_msg = await message.answer("Validating target...")
    
    try:
        # Validate target with Twitter API
        cookie = get_cookie()
        if not cookie:
            await loading_msg.delete()
            await message.answer(
                "No cookie set. Please set a cookie first.",
                reply_markup=get_main_keyboard()
            )
            return
            
        # Add account from cookie if not already added
        await twitter_api.add_account_from_cookie(cookie)
        
        # Fast validation - just check if user exists and auth works (no community scanning)
        user_data = await twitter_api.validate_user_and_auth(target_handle)
        
        if not user_data:
            await loading_msg.delete()
            await message.answer(
                f"Could not find user: {target_handle}",
                reply_markup=get_main_keyboard()
            )
            return
            
        # Save target to database
        with Session(engine) as session:
            target_obj = Target(
                user_id=user_data['user_id'],
                screen_name=user_data['screen_name'],
                name=user_data['name']
            )
            save_target(session, target_obj)
        
        await loading_msg.delete()
        
        # Show successful validation with scan options
        scan_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Scan Communities Now", callback_data=f"scan_now:{target_handle}")],
            [InlineKeyboardButton(text="⏰ Start Auto Monitoring", callback_data=f"start_monitoring:{target_handle}")],
            [InlineKeyboardButton(text="⚙️ Configure Interval", callback_data="configure_interval")],
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="action:main_menu")]
        ])
        
        await message.answer(
            f"✅ **Target Validated Successfully**\n\n"
            f"**User:** @{user_data['screen_name']}\n"
            f"**Name:** {user_data['name']}\n"
            f"**ID:** {user_data['user_id']}\n"
            f"**Followers:** {user_data.get('followers_count', 'N/A')}\n"
            f"**Verified:** {'✅' if user_data.get('verified') else '❌'}\n\n"
            f"🎯 **What would you like to do next?**",
            reply_markup=scan_keyboard,
            parse_mode="Markdown"
        )
    except ValueError as e:
        await loading_msg.delete()
        await message.answer(
            f"Error: {str(e)}",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        await loading_msg.delete()
        await message.answer(
            f"Error validating target: {str(e)}",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith("cookie_method:"))
async def process_cookie_method_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Process cookie method selection"""
    await callback_query.answer()
    method = callback_query.data.split(":")[1]
    
    if method == "manual":
        await state.set_state(BotStates.waiting_for_cookie)
        await state.update_data(cookie_method="manual")
        
        instructions = twitter_api.get_cookie_upload_methods()
        
        await callback_query.message.edit_text(
            f"🔧 **Manual Cookie Method**\n\n"
            f"1. Open Twitter/X in your browser and login\n"
            f"2. Press F12 (Developer Tools)\n"
            f"3. Go to Application/Storage tab\n"
            f"4. Find Cookies → x.com\n"
            f"5. Copy these cookies:\n"
            f"   • auth\\_token (long hex string)\n"
            f"   • ct0 (CSRF token, 32+ chars)\n\n"
            f"Please paste your cookies in the format:\n"
            f"`auth_token=abc123...; ct0=def456...;`\n\n"
            f"⚠️ **Your message will be deleted immediately for security**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="action:set_cookie")]
            ]),
            parse_mode="Markdown"
        )
    
    elif method == "auto":
        await state.set_state(BotStates.waiting_for_cookie)
        await state.update_data(cookie_method="auto")
        
        instructions = twitter_api.get_cookie_upload_methods()
        
        await callback_query.message.edit_text(
            f"🚀 **Auto-Enriched Method (Recommended)**\n\n"
            f"1. Follow manual method to get auth\\_token and ct0\n"
            f"2. Send just: auth\\_token=abc123...; ct0=def456...;\n"
            f"3. Bot automatically generates:\n"
            f"   • guest\\_id\n"
            f"   • personalization\\_id\n"
            f"   • guest\\_id\\_ads\n"
            f"   • guest\\_id\\_marketing\n\n"
            f"Just paste the essential cookies:\n"
            f"`auth_token=abc123...; ct0=def456...;`\n\n"
            f"✨ Bot will automatically generate:\n"
            f"• guest\\_id\n"
            f"• personalization\\_id\n"
            f"• guest\\_id\\_ads\n"
            f"• guest\\_id\\_marketing\n\n"
            f"⚠️ **Your message will be deleted immediately for security**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="action:set_cookie")]
            ]),
            parse_mode="Markdown"
        )
    
    elif method == "export":
        await state.set_state(BotStates.waiting_for_cookie)
        await state.update_data(cookie_method="export")
        
        instructions = twitter_api.get_cookie_upload_methods()
        
        await callback_query.message.edit_text(
            f"📥 **Browser Export Method**\n\n"
            f"Export all cookies as JSON from browser extensions.\n"
            f"Send the JSON array and bot will extract Twitter cookies automatically.\n\n"
            f"⚠️ **Your message will be deleted immediately for security**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="action:set_cookie")]
            ]),
            parse_mode="Markdown"
        )
    
    elif method == "list":
        # Show saved cookies
        saved_cookies = twitter_api.list_saved_cookies()
        
        if not saved_cookies:
            await callback_query.message.edit_text(
                "📋 **No Saved Cookies**\n\n"
                "You haven't saved any cookie sets yet.\n"
                "Upload cookies first to save them for later use.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Back", callback_data="action:set_cookie")]
                ])
            )
            return
        
        # Create keyboard with saved cookies
        keyboard = []
        for cookie_info in saved_cookies[:10]:  # Limit to 10 most recent
            name = cookie_info['name']
            preview = cookie_info['auth_token_preview']
            keyboard.append([InlineKeyboardButton(
                text=f"🍪 {name} ({preview})", 
                callback_data=f"load_cookie:{name}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="action:set_cookie")])
        
        cookie_list = "\n".join([
            f"• **{info['name']}** ({info['auth_token_preview']})\n"
            f"  Created: {info['created_at'][:10]}\n"
            f"  Last used: {info['last_used'][:10]}"
            for info in saved_cookies[:5]
        ])
        
        await callback_query.message.edit_text(
            f"📋 **Saved Cookie Sets**\n\n"
            f"{cookie_list}\n\n"
            f"Click on a cookie set to load it:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

@dp.callback_query(lambda c: c.data.startswith("load_cookie:"))
async def process_load_cookie_callback(callback_query: types.CallbackQuery):
    """Process loading saved cookies"""
    await callback_query.answer()
    cookie_name = callback_query.data.split(":", 1)[1]
    
    loading_msg = await callback_query.message.edit_text(
        f"Loading cookie set: {cookie_name}..."
    )
    
    try:
        success = await twitter_api.load_saved_cookies(cookie_name)
        
        if success:
            await loading_msg.edit_text(
                f"✅ **Cookie Set Loaded Successfully**\n\n"
                f"Loaded: **{cookie_name}**\n"
                f"Status: Active and ready for tracking\n\n"
                f"You can now start tracking Twitter users!",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await loading_msg.edit_text(
                f"❌ **Failed to Load Cookie Set**\n\n"
                f"Cookie set '{cookie_name}' could not be loaded.\n"
                f"It may be corrupted or expired.\n\n"
                f"Please upload fresh cookies.",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await loading_msg.edit_text(
            f"❌ **Error Loading Cookies**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again or upload fresh cookies.",
            reply_markup=get_main_keyboard()
        )

@dp.message(BotStates.waiting_for_cookie)
async def process_cookie_input(message: types.Message, state: FSMContext):
    """Process enhanced cookie input with multiple methods"""
    # Get method from state
    data = await state.get_data()
    method = data.get('cookie_method', 'auto')  # Default to auto
    
    # Clear the waiting state
    await state.clear()
    
    # Store the cookie input
    cookie_input = message.text
    
    # Delete the message containing the cookie for security
    await message.delete()
    
    # Show loading message
    loading_msg = await message.answer("🔄 Processing cookies...")
    
    try:
        # Use enhanced cookie processing
        result = await twitter_api.add_account_from_cookie_enhanced(
            cookie_input=cookie_input,
            method=method,
            account_name=f"telegram_user_{message.from_user.id}"
        )
        
        await loading_msg.delete()
        
        if result['success']:
            # Success message with details
            method_desc = {
                'manual': 'Manual Extraction',
                'auto': 'Auto-Enriched',
                'export': 'Browser Export'
            }.get(method, 'Auto-Enriched')
            
            enrichment_note = " with auto-generated tokens" if result.get('enriched') else ""
            
            await message.answer(
                f"✅ **Cookies Set Successfully!**\n\n"
                f"Method: {method_desc}{enrichment_note}\n"
                f"Saved as: {result.get('saved_as', 'N/A')}\n\n"
                f"🔐 Your authentication is now active and ready for tracking!\n"
                f"🚀 You can now start monitoring Twitter communities.",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Error message with specific details
            await message.answer(
                f"❌ **Cookie Processing Failed**\n\n"
                f"Method: {method}\n"
                f"Error: {result['message']}\n\n"
                f"💡 **Troubleshooting:**\n"
                f"• Ensure you copied both auth_token AND ct0\n"
                f"• Get fresh cookies from your browser\n"
                f"• Try the Auto-Enriched method\n"
                f"• Check that cookies aren't expired",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await loading_msg.delete()
        await message.answer(
            f"❌ **Unexpected Error**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again with fresh cookies.",
            reply_markup=get_main_keyboard()
        )

@dp.message(BotStates.waiting_for_proxy)
async def process_proxy_input(message: types.Message, state: FSMContext):
    """Process proxy input"""
    # Clear the waiting state
    await state.clear()
    
    # Store the proxy
    proxy_str = message.text
    
    # Delete the message containing the proxy for security
    await message.delete()
    
    # Show loading message
    loading_msg = await message.answer("Validating proxy...")
    
    try:
        # Validate proxy
        if proxy_str.lower() == "clear":
            clear_proxy()
            clear_all_proxies()  # Also clear proxy rotation
            # Reinitialize TwitterAPI without proxy
            force_reinitialize_globals()
            await loading_msg.delete()
            await message.answer(
                "All proxies removed successfully! ✅\n\n"
                "TwitterAPI reinitialized without proxy.",
                reply_markup=get_proxy_keyboard()
            )
        else:
            # Parse residential proxy format if needed
            parsed_proxy = parse_residential_proxy(proxy_str)
            
            # Basic proxy format validation
            if not (parsed_proxy.startswith('http://') or parsed_proxy.startswith('https://') or parsed_proxy.startswith('socks5://')):
                raise ValueError("Invalid proxy format. Must be residential format (host:port:user:pass) or start with http://, https://, or socks5://")
            
            # Save proxy to both filesystem and database
            save_proxy(parsed_proxy)
            
            # Reinitialize TwitterAPI with the new proxy
            force_reinitialize_globals()
            
            await loading_msg.delete()
            proxy_preview = parsed_proxy[:50] + "..." if len(parsed_proxy) > 50 else parsed_proxy
            await message.answer(
                "Single proxy set successfully! ✅\n\n"
                f"Active proxy: `{proxy_preview}`\n\n"
                "Proxy has been saved to database and will persist across restarts.",
                reply_markup=get_proxy_keyboard()
            )
    except Exception as e:
        await loading_msg.delete()
        await message.answer(
            f"Error validating proxy: {str(e)}",
            reply_markup=get_proxy_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith("interval:"))
async def process_interval_callback(callback_query: types.CallbackQuery):
    """Process interval selection callback"""
    await callback_query.answer()
    
    # Extract interval from callback data
    interval = int(callback_query.data.split(":")[1])
    
    with Session(engine) as session:
        target = get_target(session)
        
    if not target:
        await callback_query.message.edit_text(
            "No target set. Please set a target first.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Start tracking job
    scheduler.set_notification_chat(callback_query.message.chat.id)
    scheduler.interval_minutes = interval
    await scheduler.start(target.screen_name)
    
    await callback_query.message.edit_text(
        f"Polling every {interval} min...\n"
        f"Target: @{target.screen_name}\n\n"
        f"Tracking is now active. You will receive notifications when the target joins, creates, or leaves communities.",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("community:"))
async def process_community_callback(callback_query: types.CallbackQuery):
    """Process community selection"""
    await callback_query.answer()
    
    community_id = callback_query.data.split(":")[1]
    
    if community_id == "none":
        await callback_query.message.edit_text(
            "No communities available.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Get community details
    with Session(engine) as session:
        statement = select(SavedCommunity).where(SavedCommunity.community_id == community_id)
        community = session.exec(statement).first()
        
        if not community:
            await callback_query.message.edit_text(
                "Community not found.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Create community details keyboard
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="🔙 Back to Communities", callback_data="action:communities")
        )
        
        await callback_query.message.edit_text(
            f"Community: {community.label}\n"
            f"ID: {community.community_id}\n"
            f"Role: {community.role}\n"
            f"First seen: {community.first_seen_at.strftime('%Y-%m-%d %H:%M:%SZ')}\n"
            f"Last seen: {community.last_seen_at.strftime('%Y-%m-%d %H:%M:%SZ')}",
            reply_markup=builder.as_markup()
        )

@dp.message(BotStates.waiting_for_proxy_list)
async def process_proxy_list_input(message: types.Message, state: FSMContext):
    """Process proxy list input"""
    # Clear the waiting state
    await state.clear()
    
    # Store the proxy list
    proxy_list_text = message.text
    
    # Delete the message containing the proxy list for security
    await message.delete()
    
    # Show loading message
    loading_msg = await message.answer("Processing proxy list...")
    
    try:
        # Validate and save proxy list
        if not proxy_list_text.strip():
            raise ValueError("Empty proxy list provided")
        
        proxy_lines = [line.strip() for line in proxy_list_text.strip().split('\n') if line.strip()]
        
        if not proxy_lines:
            raise ValueError("No valid proxy lines found")
        
        # Basic validation for each proxy
        for i, proxy_line in enumerate(proxy_lines):
            parsed = parse_residential_proxy(proxy_line)
            if not parsed:
                raise ValueError(f"Invalid proxy format on line {i+1}: {proxy_line}")
        
        # Save proxy list to database
        save_proxy_list(proxy_list_text)
        
        # Reinitialize TwitterAPI with proxy rotation support
        force_reinitialize_globals()
        
        await loading_msg.delete()
        await message.answer(
            f"Proxy list set successfully! ✅\n\n"
            f"Added {len(proxy_lines)} proxies to rotation.\n"
            f"TwitterAPI will now use proxy rotation.\n"
            f"All proxies are saved to database and will persist across restarts.",
            reply_markup=get_proxy_keyboard()
        )
    except Exception as e:
        await loading_msg.delete()
        await message.answer(
            f"Error processing proxy list: {str(e)}",
            reply_markup=get_proxy_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith("scan_now:"))
async def process_scan_now_callback(callback_query: types.CallbackQuery):
    """Process immediate community scan request"""
    await callback_query.answer()
    username = callback_query.data.split(":", 1)[1]
    
    loading_msg = await callback_query.message.edit_text(
        f"🌐 **Fast Community Scan for @{username}**\n\n"
        f"Using browser automation + post analysis...\n"
        f"(No social graph analysis for speed)"
    )
    
    try:
        # Perform lightweight community scan with timeout
        scan_timeout = 30  # 30 seconds timeout (much faster now)
        result = await asyncio.wait_for(
            twitter_api.get_user_communities_comprehensive(username, deep_scan=False),
            timeout=scan_timeout
        )
        
        if not result:
            await loading_msg.edit_text(
                f"❌ **Scan Failed**\n\n"
                f"Could not retrieve community data for @{username}.\n"
                f"Please check authentication and try again.",
                reply_markup=get_main_keyboard()
            )
            return
        
        communities = result.communities
        
        if not communities:
            await loading_msg.edit_text(
                f"📊 **Scan Complete - No Communities Found**\n\n"
                f"**User:** @{username}\n"
                f"**Result:** No community memberships detected\n\n"
                f"This could mean:\n"
                f"• User is not in any communities\n"
                f"• Communities are private\n"
                f"• Detection method limitations\n\n"
                f"Try auto-monitoring to detect future activity!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏰ Start Monitoring", callback_data=f"start_monitoring:{username}")],
                    [InlineKeyboardButton(text="🔙 Main Menu", callback_data="action:main_menu")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Format communities for display
        community_text = []
        admin_count = 0
        member_count = 0
        
        for i, community in enumerate(communities[:10], 1):  # Limit display to 10
            role_emoji = "👑" if community.role == "Admin" else "👤"
            community_text.append(f"{i}. {role_emoji} **{community.name}**")
            community_text.append(f"   Role: {community.role}")
            
            if community.role == "Admin":
                admin_count += 1
            else:
                member_count += 1
        
        if len(communities) > 10:
            community_text.append(f"\n... and {len(communities) - 10} more communities")
        
        communities_display = "\n".join(community_text)
        
        # Save communities to database to prevent false "new" alerts later
        try:
            with Session(engine) as session:
                save_communities(session, username, communities)
                
            scheduler.db_manager.update_user_communities(username, communities)
            
        except Exception as save_error:
            # Log but don't fail the scan if database save fails
            logging.error(f"Failed to save communities to database: {save_error}")
        
        await loading_msg.edit_text(
            f"✅ **Community Scan Complete**\n\n"
            f"**User:** @{username}\n"
            f"**Total Communities:** {len(communities)}\n"
            f"**Admin/Creator:** {admin_count}\n"
            f"**Member:** {member_count}\n\n"
            f"**Communities Found:**\n{communities_display}\n\n"
            f"🎯 **Next Steps:**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏰ Start Monitoring", callback_data=f"start_monitoring:{username}")],
                [InlineKeyboardButton(text="🔄 Rescan", callback_data=f"scan_now:{username}")],
                [InlineKeyboardButton(text="🔙 Main Menu", callback_data="action:main_menu")]
            ]),
            parse_mode="Markdown"
        )
        
    except asyncio.TimeoutError:
        await loading_msg.edit_text(
            f"⏰ **Scan Timeout**\n\n"
            f"Community scan for @{username} took longer than {scan_timeout} seconds.\n\n"
            f"This can happen with:\n"
            f"• Heavy community activity\n"
            f"• Browser automation delays\n"
            f"• Network issues\n\n"
            f"Try again or use monitoring instead.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Try Again", callback_data=f"scan_now:{username}")],
                [InlineKeyboardButton(text="⏰ Start Monitoring", callback_data=f"start_monitoring:{username}")],
                [InlineKeyboardButton(text="🔙 Main Menu", callback_data="action:main_menu")]
            ]),
            parse_mode="Markdown"
        )
        return
    except Exception as e:
        await loading_msg.edit_text(
            f"❌ **Scan Error**\n\n"
            f"Error scanning @{username}: {str(e)}\n\n"
            f"Please try again or contact support.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith("start_monitoring:"))
async def process_start_monitoring_callback(callback_query: types.CallbackQuery):
    """Process start monitoring request"""
    await callback_query.answer()
    username = callback_query.data.split(":", 1)[1]
    
    # Check if monitoring is already active
    if scheduler.is_active() and scheduler.target_user == username:
        await callback_query.message.edit_text(
            f"⚠️ **Already Monitoring**\n\n"
            f"@{username} is already being monitored.\n"
            f"Interval: {scheduler.interval_minutes} minutes\n\n"
            f"Check logs for activity updates.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛑 Stop Monitoring", callback_data=f"stop_monitoring:{username}")],
                [InlineKeyboardButton(text="⚙️ Change Interval", callback_data="configure_interval")],
                [InlineKeyboardButton(text="🔙 Main Menu", callback_data="action:main_menu")]
            ]),
            parse_mode="Markdown"
        )
        return
    
    # Start monitoring
    try:
        # Set notification chat
        scheduler.set_notification_chat(callback_query.from_user.id)
        
        # Start monitoring
        success = await scheduler.start(username)
        
        if success:
            await callback_query.message.edit_text(
                f"🎯 **Enhanced Community Monitoring Started**\n\n"
                f"**Target:** @{username}\n"
                f"**Interval:** {scheduler.interval_minutes} minutes\n"
                f"**Features:** Deep scanning, comprehensive detection\n\n"
                f"📡 Monitoring all community activities...\n\n"
                f"You'll receive notifications when:\n"
                f"• User joins new communities\n"
                f"• User leaves communities\n"
                f"• User creates communities\n"
                f"• User's role changes\n\n"
                f"⏰ Next check in {scheduler.interval_minutes} minutes",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛑 Stop Monitoring", callback_data=f"stop_monitoring:{username}")],
                    [InlineKeyboardButton(text="⚙️ Change Interval", callback_data="configure_interval")],
                    [InlineKeyboardButton(text="📊 Check Status", callback_data="monitoring_status")],
                    [InlineKeyboardButton(text="🔙 Main Menu", callback_data="action:main_menu")]
                ]),
                parse_mode="Markdown"
            )
        else:
            await callback_query.message.edit_text(
                f"❌ **Failed to Start Monitoring**\n\n"
                f"Could not start monitoring for @{username}.\n"
                f"Please check authentication and try again.",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ **Monitoring Error**\n\n"
            f"Error starting monitoring: {str(e)}",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith("stop_monitoring:"))
async def process_stop_monitoring_callback(callback_query: types.CallbackQuery):
    """Process stop monitoring request"""
    await callback_query.answer()
    username = callback_query.data.split(":", 1)[1]
    
    try:
        scheduler.stop()
        
        await callback_query.message.edit_text(
            f"🛑 **Monitoring Stopped**\n\n"
            f"Stopped monitoring @{username}.\n"
            f"You can restart monitoring anytime.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Restart Monitoring", callback_data=f"start_monitoring:{username}")],
                [InlineKeyboardButton(text="🔙 Main Menu", callback_data="action:main_menu")]
            ]),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ **Error stopping monitoring:** {str(e)}",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data == "configure_interval")
async def process_configure_interval_callback(callback_query: types.CallbackQuery):
    """Process interval configuration request"""
    await callback_query.answer()
    
    interval_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ 1 minute", callback_data="set_interval:1")],
        [InlineKeyboardButton(text="🔥 5 minutes", callback_data="set_interval:5")],
        [InlineKeyboardButton(text="⏰ 15 minutes", callback_data="set_interval:15")],
        [InlineKeyboardButton(text="📅 30 minutes", callback_data="set_interval:30")],
        [InlineKeyboardButton(text="🕐 1 hour", callback_data="set_interval:60")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="action:main_menu")]
    ])
    
    await callback_query.message.edit_text(
        f"⚙️ **Configure Monitoring Interval**\n\n"
        f"Current interval: **{scheduler.interval_minutes} minutes**\n\n"
        f"Choose how often to check for community changes:\n\n"
        f"⚡ **1 minute** - Very frequent (high Twitter usage)\n"
        f"🔥 **5 minutes** - Frequent monitoring\n"
        f"⏰ **15 minutes** - Balanced (recommended)\n"
        f"📅 **30 minutes** - Less frequent\n"
        f"🕐 **1 hour** - Minimal monitoring\n\n"
        f"⚠️ Shorter intervals may hit rate limits faster.",
        reply_markup=interval_keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("set_interval:"))
async def process_set_interval_callback(callback_query: types.CallbackQuery):
    """Process interval setting"""
    await callback_query.answer()
    new_interval = int(callback_query.data.split(":", 1)[1])
    
    # Update scheduler interval
    scheduler.interval_minutes = new_interval
    
    # If monitoring is active, restart with new interval
    was_running = scheduler.is_active()
    current_target = scheduler.target_user
    
    if was_running:
        scheduler.stop()
        await asyncio.sleep(1)  # Brief pause
        await scheduler.start(current_target)
    
    await callback_query.message.edit_text(
        f"✅ **Interval Updated**\n\n"
        f"New monitoring interval: **{new_interval} minutes**\n\n"
        f"{'📡 Monitoring restarted with new interval.' if was_running else '⏸️ Apply when monitoring starts.'}\n\n"
        f"⏰ Next check: {new_interval} minutes from now",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "monitoring_status")
async def process_monitoring_status_callback(callback_query: types.CallbackQuery):
    """Show monitoring status"""
    await callback_query.answer()
    
    status = scheduler.get_status()
    
    if status['is_running']:
        status_text = f"🟢 **Active**\n"
        status_text += f"**Target:** @{status['target_user']}\n"
        status_text += f"**Interval:** {status['interval_minutes']} minutes\n"
        if status['last_run']:
            status_text += f"**Last check:** {status['last_run'][:19]} UTC\n"
        status_text += f"**Bot connected:** {'✅' if status['has_bot'] else '❌'}\n"
        status_text += f"**Notifications:** {'✅' if status['has_chat_id'] else '❌'}\n"
        status_text += f"**Task active:** {'✅' if status['task_active'] else '❌'}"
    else:
        status_text = "🔴 **Inactive**\nNo monitoring currently running."
    
    await callback_query.message.edit_text(
        f"📊 **Monitoring Status**\n\n{status_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="monitoring_status")],
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="action:main_menu")]
        ]),
        parse_mode="Markdown"
    )

async def on_startup():
    """Startup actions"""
    # Create database tables
    create_db_and_tables()
    
    # Log proxy status
    proxy_accounts = get_proxy_accounts()
    if proxy_accounts:
        logging.info(f"Bot started with {len(proxy_accounts)} proxies in rotation")
    else:
        legacy_proxy = get_proxy()
        if legacy_proxy:
            logging.info(f"Bot started with legacy proxy: {legacy_proxy[:30]}...")
        else:
            logging.info("Bot started without proxy")
    
    logging.info("Bot started")

async def on_shutdown():
    """Shutdown actions"""
    # Stop tracking job
    if scheduler:
        scheduler.stop()
    logging.info("Bot stopped")

# Register startup and shutdown handlers
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)

# Main entry point
async def main():
    # Initialize global variables first
    initialize_globals()
    
    # Start the bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
