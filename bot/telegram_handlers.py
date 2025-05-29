#!/usr/bin/env python3
"""
Telegram Bot Handlers Module

Core handlers for Telegram bot commands and interactions:
- Command handlers
- Message handlers
- State management
"""

import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from bot.models import (
    Target, SavedCommunity, ProxyAccount, engine, get_target, save_target,
    get_saved_communities, save_cookie, get_cookie, create_db_and_tables,
    save_proxy, get_proxy, clear_proxy, save_proxy_list, get_proxy_accounts,
    clear_all_proxies, parse_residential_proxy
)
from bot.scheduler import CommunityScheduler
from bot.twitter_api import TwitterAPI
from bot.keyboard_utils import (
    get_main_keyboard, get_proxy_keyboard, get_interval_keyboard,
    get_target_keyboard, get_communities_keyboard
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv("BOT_TOKEN", "7847904250:AAEJSJzDL0gh4xKo3ZBeZVsX39WXLLcmxE8")
POLL_INTERVAL_MIN = int(os.getenv("POLL_INTERVAL_MIN", "5"))
TG_CHAT_ID_WHITELIST = os.getenv("TG_CHAT_ID_WHITELIST", "").split(",") if os.getenv("TG_CHAT_ID_WHITELIST") else []

# Initialize bot and dispatcher with FSM storage
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Global variables
twitter_api = None
tracker = None


class BotStates(StatesGroup):
    """FSM states for bot interactions"""
    waiting_for_target = State()
    waiting_for_cookie = State()
    waiting_for_proxy = State()
    waiting_for_proxy_list = State()


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


def initialize_globals():
    """Initialize global variables"""
    global twitter_api, tracker
    twitter_api = get_twitter_api()
    tracker = CommunityScheduler(twitter_api)
    tracker.set_bot(bot)


def check_authorization(chat_id: int) -> bool:
    """Check if user is authorized to use the bot"""
    if TG_CHAT_ID_WHITELIST and str(chat_id) not in TG_CHAT_ID_WHITELIST:
        return False
    return True


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handler for /start command - the only command needed to start using the bot"""
    if not check_authorization(message.chat.id):
        await message.answer("You are not authorized to use this bot.")
        return
        
    await message.answer(
        "Welcome to Twitter Community Tracker Console!\n\n"
        "Use the buttons below to control the bot:",
        reply_markup=get_main_keyboard()
    )


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
        await message.answer("Please enter a valid Twitter username.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    try:
        # Test if user exists
        twitter_api = get_twitter_api()
        result = await twitter_api.test_user_exists(target_username)
        
        if result and result.get('exists'):
            # Save target
            save_target(target_username)
            await message.answer(
                f"✅ Target set to @{target_username}\n"
                f"User found: {result.get('display_name', target_username)}\n"
                f"Followers: {result.get('followers_count', 'N/A')}\n\n"
                f"You can now start tracking!",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                f"❌ User @{target_username} not found or account is private.\n"
                f"Please check the username and try again.",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logging.error(f"Error testing user existence: {e}")
        # Still save the target even if test fails
        save_target(target_username)
        await message.answer(
            f"⚠️ Target set to @{target_username}\n"
            f"Note: Could not verify user existence. The tracking will attempt to work anyway.\n"
            f"Error: {str(e)}",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()


@dp.message(BotStates.waiting_for_cookie)
async def process_cookie_input(message: types.Message, state: FSMContext):
    """Process cookie input"""
    if not check_authorization(message.chat.id):
        await message.answer("You are not authorized to use this bot.")
        return
    
    cookie_text = message.text.strip()
    
    if not cookie_text:
        await message.answer("Please provide valid cookie data.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    try:
        # Get the selected method from state data
        state_data = await state.get_data()
        method = state_data.get('cookie_method', 'manual')
        
        twitter_api = get_twitter_api()
        
        if method == 'auto':
            # Auto-enriched method
            result = await twitter_api.save_auto_enriched_cookies(cookie_text)
            if result['success']:
                await message.answer(
                    f"✅ Cookies saved successfully using auto-enriched method!\n"
                    f"Enriched {result['enriched_count']} cookies automatically.\n"
                    f"Session validated and ready for use.",
                    reply_markup=get_main_keyboard()
                )
            else:
                await message.answer(
                    f"❌ Failed to save cookies: {result['error']}\n"
                    f"Please check your cookie format and try again.",
                    reply_markup=get_main_keyboard()
                )
        
        elif method == 'export':
            # Browser export method
            result = await twitter_api.import_browser_cookies(cookie_text)
            if result['success']:
                await message.answer(
                    f"✅ Browser cookies imported successfully!\n"
                    f"Imported {result['imported_count']} cookies from browser export.\n"
                    f"Session validated and ready for use.",
                    reply_markup=get_main_keyboard()
                )
            else:
                await message.answer(
                    f"❌ Failed to import browser cookies: {result['error']}\n"
                    f"Please check your JSON format and try again.",
                    reply_markup=get_main_keyboard()
                )
        
        else:
            # Manual method (default)
            result = await twitter_api.save_manual_cookies(cookie_text)
            if result['success']:
                await message.answer(
                    f"✅ Cookies saved successfully using manual method!\n"
                    f"Session validated and ready for use.",
                    reply_markup=get_main_keyboard()
                )
            else:
                await message.answer(
                    f"❌ Failed to save cookies: {result['error']}\n"
                    f"Please check your cookie format and try again.",
                    reply_markup=get_main_keyboard()
                )
    
    except Exception as e:
        logging.error(f"Error processing cookies: {e}")
        await message.answer(
            f"❌ Error processing cookies: {str(e)}\n"
            f"Please try again with valid cookie data.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()


@dp.message(BotStates.waiting_for_proxy)
async def process_proxy_input(message: types.Message, state: FSMContext):
    """Process proxy input"""
    if not check_authorization(message.chat.id):
        await message.answer("You are not authorized to use this bot.")
        return
    
    proxy_text = message.text.strip()
    
    if not proxy_text:
        await message.answer("Please provide valid proxy data.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    try:
        # Parse residential proxy format
        proxy_data = parse_residential_proxy(proxy_text)
        
        if proxy_data:
            # Save to database as proxy account
            save_proxy(proxy_data)
            await message.answer(
                f"✅ Residential proxy added successfully!\n"
                f"Host: {proxy_data['host']}:{proxy_data['port']}\n"
                f"Type: {proxy_data.get('type', 'http')}\n"
                f"Auth: {'Yes' if proxy_data.get('username') else 'No'}",
                reply_markup=get_main_keyboard()
            )
        else:
            # Try legacy format
            save_proxy({'proxy_url': proxy_text})
            await message.answer(
                f"✅ Proxy saved successfully!\n"
                f"Proxy: {proxy_text[:50]}{'...' if len(proxy_text) > 50 else ''}",
                reply_markup=get_main_keyboard()
            )
    
    except Exception as e:
        logging.error(f"Error saving proxy: {e}")
        await message.answer(
            f"❌ Error saving proxy: {str(e)}\n"
            f"Please check your proxy format and try again.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()


@dp.message(BotStates.waiting_for_proxy_list)
async def process_proxy_list_input(message: types.Message, state: FSMContext):
    """Process proxy list input"""
    if not check_authorization(message.chat.id):
        await message.answer("You are not authorized to use this bot.")
        return
    
    proxy_text = message.text.strip()
    
    if not proxy_text:
        await message.answer("Please provide valid proxy data.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    try:
        # Parse multiple proxies
        proxy_lines = [line.strip() for line in proxy_text.split('\n') if line.strip()]
        
        if not proxy_lines:
            await message.answer("No valid proxy lines found.", reply_markup=get_main_keyboard())
            await state.clear()
            return
        
        # Process each proxy
        success_count = 0
        proxies = []
        
        for line in proxy_lines:
            try:
                proxy_data = parse_residential_proxy(line)
                if proxy_data:
                    proxies.append(proxy_data)
                    success_count += 1
                else:
                    # Try legacy format
                    proxies.append({'proxy_url': line})
                    success_count += 1
            except Exception as e:
                logging.warning(f"Failed to parse proxy line '{line}': {e}")
        
        if proxies:
            # Save all proxies
            save_proxy_list(proxies)
            await message.answer(
                f"✅ Proxy list processed successfully!\n"
                f"Added {success_count} out of {len(proxy_lines)} proxies.\n"
                f"Proxies are now available for rotation.",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                f"❌ No valid proxies found in the list.\n"
                f"Please check your proxy format and try again.",
                reply_markup=get_main_keyboard()
            )
    
    except Exception as e:
        logging.error(f"Error processing proxy list: {e}")
        await message.answer(
            f"❌ Error processing proxy list: {str(e)}\n"
            f"Please check your proxy format and try again.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()


async def on_startup():
    """Bot startup handler"""
    try:
        # Create database tables
        create_db_and_tables()
        logging.info("Database initialized")
        
        # Initialize global variables
        initialize_globals()
        logging.info("Global variables initialized")
        
        # Start the bot
        logging.info("Community Tracker Bot started successfully")
    except Exception as e:
        logging.error(f"Error during startup: {e}")


async def on_shutdown():
    """Bot shutdown handler"""
    try:
        global tracker
        if tracker:
            await tracker.stop()
            logging.info("Tracker stopped")
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")


async def main():
    """Main bot runner"""
    # Initialize global variables first
    initialize_globals()
    
    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    await dp.start_polling(bot) 