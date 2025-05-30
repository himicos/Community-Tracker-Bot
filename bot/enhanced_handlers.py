#!/usr/bin/env python3
"""
Enhanced Telegram Bot Handlers with Element-Based Community Detection
Integrates HTML element detection with existing bot structure
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing models and utilities
from models import (
    Target, SavedCommunity, ProxyAccount, engine, create_db_and_tables, Session
)
from cookie_manager import CookieManager
from element_community_detector import ElementCommunityDetector
from keyboard_utils import get_main_keyboard

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv("BOT_TOKEN", "7847904250:AAEJSJzDL0gh4xKo3ZBeZVsX39WXLLcmxE8")
TG_CHAT_ID_WHITELIST = os.getenv("TG_CHAT_ID_WHITELIST", "").split(",") if os.getenv("TG_CHAT_ID_WHITELIST") else []

# Initialize bot and dispatcher with FSM storage
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Initialize managers
cookie_manager = CookieManager()
element_detector = ElementCommunityDetector(cookie_manager)

# Database helper functions
def get_target_wrapper():
    """Wrapper function to get target with session handling"""
    try:
        with Session(engine) as session:
            from sqlmodel import select
            statement = select(Target).limit(1)
            result = session.exec(statement).first()
            return result
    except Exception:
        return None

def save_target_wrapper(username: str):
    """Wrapper function to save target with session handling"""
    try:
        with Session(engine) as session:
            # Remove existing targets
            from sqlmodel import select
            statement = select(Target)
            existing_targets = session.exec(statement).all()
            for target in existing_targets:
                session.delete(target)
            
            # Create new target
            new_target = Target(
                user_id=f"user_{username}",
                screen_name=username,
                name=username
            )
            session.add(new_target)
            session.commit()
            return new_target
    except Exception as e:
        logging.error(f"Error saving target: {e}")
        return None

class BotStates(StatesGroup):
    """FSM states for bot interactions"""
    waiting_for_target = State()
    waiting_for_cookie = State()

def check_authorization(chat_id: int) -> bool:
    """Check if user is authorized to use the bot"""
    if TG_CHAT_ID_WHITELIST and str(chat_id) not in TG_CHAT_ID_WHITELIST:
        return False
    return True

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handler for /start command"""
    if not check_authorization(message.chat.id):
        await message.answer("You are not authorized to use this bot.")
        return
        
    await message.answer(
        "Twitter Community Tracker Console\n\nUse the buttons below to control the bot:",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "action:set_target")
async def handle_set_target(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle set target button"""
    if not check_authorization(callback_query.message.chat.id):
        await callback_query.answer("You are not authorized to use this bot.")
        return
    
    await callback_query.answer()
    await callback_query.message.answer("Enter the Twitter username you want to track:")
    await state.set_state(BotStates.waiting_for_target)

@dp.callback_query(lambda c: c.data == "action:set_cookie")
async def handle_set_cookie(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle set cookie button"""
    if not check_authorization(callback_query.message.chat.id):
        await callback_query.answer("You are not authorized to use this bot.")
        return
    
    await callback_query.answer()
    await callback_query.message.answer(
        "Upload Twitter Cookies\n\n"
        "Required: auth_token and ct0\n\n"
        "Format: auth_token=abc123; ct0=def456;\n\n"
        "How to get cookies:\n"
        "1. Open x.com in browser\n"
        "2. Open Developer Tools (F12)\n"
        "3. Go to Application > Cookies\n"
        "4. Copy auth_token and ct0 values"
    )
    await state.set_state(BotStates.waiting_for_cookie)

@dp.callback_query(lambda c: c.data == "action:start_tracking")
async def handle_track_communities(callback_query: types.CallbackQuery):
    """Handle track communities button - NEW ENHANCED VERSION"""
    if not check_authorization(callback_query.message.chat.id):
        await callback_query.answer("You are not authorized to use this bot.")
        return
    
    await callback_query.answer()
    
    # Get current target
    target = get_target_wrapper()
    if not target:
        await callback_query.message.answer(
            "❌ No target set. Please set a target user first.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Check if cookies are available
    saved_cookies = cookie_manager.list_cookie_sets()
    if not saved_cookies:
        await callback_query.message.answer(
            "⚠️ No authentication cookies found.\n\n"
            "Please upload cookies first for enhanced community detection.\n"
            "Use 'Set Cookie' button to add authentication.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Start tracking
    loading_msg = await callback_query.message.answer(
        f"🔍 Starting enhanced community tracking for @{target.screen_name}...\n\n"
        f"Using browser-based detection with authentication 🌐\n"
        f"Analyzing last 10 posts for community activity..."
    )
    
    try:
        # Import our main tracking function
        from community_tracker_main import start_community_tracking
        
        # Run community tracking
        result = await start_community_tracking(
            username=target.screen_name,
            user_id=callback_query.from_user.id
        )
        
        if result['success']:
            # Format the results message
            communities = result['communities']
            total = result['total_communities']
            
            # Create detailed response
            response_text = f"🎯 Community Tracking Results for @{target.screen_name}\n"
            response_text += f"👤 {result['display_name']}\n"
            response_text += "=" * 50 + "\n\n"
            
            # Joined communities
            if communities['joined']:
                response_text += f"🎉 Communities Joined ({len(communities['joined'])}):\n"
                for community in communities['joined'][:5]:  # Limit to 5
                    response_text += f"  • {community['name']} (Role: {community['role']})\n"
                if len(communities['joined']) > 5:
                    response_text += f"  ... and {len(communities['joined']) - 5} more\n"
                response_text += "\n"
            
            # Created communities  
            if communities['created']:
                response_text += f"🚀 Communities Created ({len(communities['created'])}):\n"
                for community in communities['created'][:5]:
                    response_text += f"  • {community['name']} (Role: {community['role']})\n"
                if len(communities['created']) > 5:
                    response_text += f"  ... and {len(communities['created']) - 5} more\n"
                response_text += "\n"
            
            # Tweeted about communities
            if communities['tweeted']:
                response_text += f"💬 Communities Mentioned ({len(communities['tweeted'])}):\n"
                for community in communities['tweeted'][:5]:
                    response_text += f"  • {community['name']}\n"
                if len(communities['tweeted']) > 5:
                    response_text += f"  ... and {len(communities['tweeted']) - 5} more\n"
                response_text += "\n"
            
            # Summary
            if total == 0:
                response_text += "📭 No new community activity detected in recent posts.\n"
            else:
                response_text += f"📊 Total: {total} communities detected from recent activity\n"
            
            response_text += "\n🔔 This analysis covers the last 10 posts for maximum relevance."
            
            await loading_msg.edit_text(response_text)
            
        else:
            # Handle errors
            error_messages = {
                'no_cookies': "❌ No authentication cookies found. Please upload cookies first.",
                'user_not_found': f"❌ User @{target.screen_name} not found or profile is private.",
                'tracking_failed': f"❌ Community tracking failed: {result.get('message', 'Unknown error')}"
            }
            
            error_msg = error_messages.get(result.get('error'), f"❌ Error: {result.get('message', 'Unknown error')}")
            
            await loading_msg.edit_text(error_msg)
        
    except Exception as e:
        logging.error(f"Community tracking error: {e}")
        await loading_msg.edit_text(
            f"❌ Community tracking failed: {str(e)}\n\n"
            f"Please check your cookies and target settings."
        )

@dp.callback_query(lambda c: c.data == "action:status")
async def handle_status(callback_query: types.CallbackQuery):
    """Handle status button"""
    if not check_authorization(callback_query.message.chat.id):
        await callback_query.answer("You are not authorized to use this bot.")
        return
    
    await callback_query.answer()
    
    # Get current target
    target = get_target_wrapper()
    target_status = f"@{target.screen_name}" if target else "Not set"
    
    # Get cookie status
    saved_cookies = cookie_manager.list_cookie_sets()
    cookie_status = f"{len(saved_cookies)} saved" if saved_cookies else "None"
    
    status_message = (
        f"Community Tracker Status\n\n"
        f"Target: {target_status}\n"
        f"Cookies: {cookie_status}\n"
        f"Detection: {'Element-based' if saved_cookies else 'Regex patterns'}\n\n"
        f"Ready for tracking."
    )
    
    await callback_query.message.answer(status_message)

@dp.callback_query(lambda c: c.data == "action:communities")
async def handle_communities(callback_query: types.CallbackQuery):
    """Handle communities button"""
    if not check_authorization(callback_query.message.chat.id):
        await callback_query.answer("You are not authorized to use this bot.")
        return
    
    await callback_query.answer()
    await callback_query.message.answer("Communities feature - shows detected communities")

@dp.callback_query(lambda c: c.data == "action:proxy_menu")
async def handle_proxy_menu(callback_query: types.CallbackQuery):
    """Handle proxy menu button"""
    if not check_authorization(callback_query.message.chat.id):
        await callback_query.answer("You are not authorized to use this bot.")
        return
    
    await callback_query.answer()
    await callback_query.message.answer("Proxy settings - configure proxy options")

@dp.callback_query(lambda c: c.data == "action:stop_tracking")
async def handle_stop_tracking(callback_query: types.CallbackQuery):
    """Handle stop tracking button"""
    if not check_authorization(callback_query.message.chat.id):
        await callback_query.answer("You are not authorized to use this bot.")
        return
    
    await callback_query.answer()
    await callback_query.message.answer("Tracking stopped")

@dp.message(BotStates.waiting_for_target)
async def process_target_input(message: types.Message, state: FSMContext):
    """Process target username input"""
    if not check_authorization(message.chat.id):
        await message.answer("You are not authorized to use this bot.")
        return
    
    target_username = message.text.strip()
    
    # Remove @ if present
    if target_username.startswith('@'):
        target_username = target_username[1:]
    
    if not target_username:
        await message.answer("Please enter a valid Twitter username.")
        await state.clear()
        return
    
    # Save target
    save_target_wrapper(target_username)
    
    await message.answer(f"Target set to @{target_username}")
    await state.clear()

@dp.message(BotStates.waiting_for_cookie)
async def process_cookie_input(message: types.Message, state: FSMContext):
    """Process cookie input"""
    if not check_authorization(message.chat.id):
        await message.answer("You are not authorized to use this bot.")
        return
    
    cookie_text = message.text.strip()
    
    # Delete the message containing cookies for security
    await message.delete()
    
    if not cookie_text:
        await message.answer("Please provide valid cookie data.")
        await state.clear()
        return
    
    try:
        # Parse cookies using cookie manager
        cookie_set = cookie_manager.parse_manual_cookies(cookie_text)
        
        if not cookie_set:
            await message.answer("Invalid cookie format. Please provide auth_token and ct0.")
            await state.clear()
            return
        
        # Auto-enrich cookies
        enriched_cookies = cookie_manager.auto_enrich_cookies(cookie_set)
        
        # Save cookies
        success = cookie_manager.save_cookies(enriched_cookies, "default")
        
        if success:
            await message.answer("Cookies saved successfully!")
        else:
            await message.answer("Failed to save cookies.")
        
    except Exception as e:
        logging.error(f"Cookie processing error: {e}")
        await message.answer(f"Cookie processing error: {str(e)}")
    
    await state.clear()

async def on_startup():
    """Initialize bot on startup"""
    logging.info("Enhanced Community Tracker Bot starting up...")
    
    # Create database tables
    create_db_and_tables()
    
    logging.info("✅ Enhanced Community Tracker Bot ready!")

async def on_shutdown():
    """Cleanup on shutdown"""
    logging.info("Enhanced Community Tracker Bot shutting down...")
    await bot.session.close()

async def main():
    """Main bot function"""
    await on_startup()
    
    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 