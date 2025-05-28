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
from sqlmodel import Session

from bot.models import Target, SavedCommunity, engine, get_target, save_target, get_saved_communities, save_cookie, get_cookie, create_db_and_tables
from bot.scheduler import TwitterTracker
from bot.twitter_api import TwitterAPI

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

# Initialize Twitter API
twitter_api = TwitterAPI()

# Initialize tracker
tracker = TwitterTracker(bot=bot, twitter_api=twitter_api)

# Define FSM states
class BotStates(StatesGroup):
    waiting_for_target = State()
    waiting_for_cookie = State()

# Create main menu keyboard with inline buttons
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📋 Set Target", callback_data="action:set_target"),
        InlineKeyboardButton(text="🍪 Set Cookie", callback_data="action:set_cookie"),
        InlineKeyboardButton(text="▶️ Start Tracking", callback_data="action:start_tracking"),
        InlineKeyboardButton(text="⏹️ Stop Tracking", callback_data="action:stop_tracking"),
        InlineKeyboardButton(text="ℹ️ Status", callback_data="action:status"),
        InlineKeyboardButton(text="📊 Communities", callback_data="action:communities")
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
        await state.set_state(BotStates.waiting_for_cookie)
        await callback_query.message.edit_text(
            "Please enter your Twitter authentication cookie string.\n\n"
            "Format: `auth_token=...; ct0=...;`\n\n"
            "This will be used to authenticate with Twitter's API.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="action:back")]
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
        tracker.stop()
        
        await callback_query.message.edit_text(
            "Tracking stopped.",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "status":
        with Session(engine) as session:
            target = get_target(session)
            communities = get_saved_communities(session)
        
        if not target:
            status_text = "No target set. Please set a target first."
        else:
            cookie_status = "✅ Set" if get_cookie() else "❌ Not set"
            status_text = (
                f"Target: @{target.screen_name}\n"
                f"Cookie: {cookie_status}\n"
                f"Tracking: {'Active' if tracker.job else 'Inactive'}\n"
                f"Interval: {tracker.interval or 'Not set'} min\n"
                f"Last run: {tracker.last_run.strftime('%Y-%m-%d %H:%M:%SZ') if tracker.last_run else 'Never'}\n"
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
            # Manually check communities once
            await tracker.check_communities(target.user_id)
            
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
        
        # Get user info to validate
        user_data = await twitter_api.get_user_communities(target_handle)
        
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
                user_id=user_data.user_id,
                screen_name=user_data.screen_name,
                name=user_data.name or user_data.screen_name
            )
            save_target(session, target_obj)
        
        await loading_msg.delete()
        await message.answer(
            f"Target set: @{user_data.screen_name} (ID: {user_data.user_id})",
            reply_markup=get_main_keyboard()
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

@dp.message(BotStates.waiting_for_cookie)
async def process_cookie_input(message: types.Message, state: FSMContext):
    """Process cookie input"""
    # Clear the waiting state
    await state.clear()
    
    # Store the cookie
    cookie_str = message.text
    
    # Delete the message containing the cookie for security
    await message.delete()
    
    # Show loading message
    loading_msg = await message.answer("Validating cookie...")
    
    try:
        # Validate cookie by adding account to twscrape
        success = await twitter_api.add_account_from_cookie(cookie_str)
        
        if success:
            # Save cookie
            save_cookie(cookie_str)
            
            await loading_msg.delete()
            await message.answer(
                "Cookie set successfully! ✅\n\n"
                "Your authentication cookie has been stored securely.",
                reply_markup=get_main_keyboard()
            )
        else:
            await loading_msg.delete()
            await message.answer(
                "Invalid cookie format. Please ensure it contains auth_token and ct0.",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        await loading_msg.delete()
        await message.answer(
            f"Error validating cookie: {str(e)}",
            reply_markup=get_main_keyboard()
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
    tracker.start(target.user_id, interval, callback_query.message.chat.id)
    
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

async def on_startup():
    """Startup actions"""
    # Create database tables
    create_db_and_tables()
    logging.info("Bot started")

async def on_shutdown():
    """Shutdown actions"""
    # Stop tracking job
    tracker.stop()
    logging.info("Bot stopped")

# Register startup and shutdown handlers
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)

# Main entry point
async def main():
    # Start the bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
