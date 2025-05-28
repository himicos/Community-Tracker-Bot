import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlmodel import Session, select
import json
from typing import List, Optional, Dict, Any

from bot.models import Target, SavedCommunity, engine, get_saved_communities, save_communities, save_run, get_cookie
from bot.twitter_api import TwitterAPI, Community

class TwitterTracker:
    """Class for tracking Twitter communities"""
    
    def __init__(self, bot: Bot, twitter_api: TwitterAPI):
        self.bot = bot
        self.twitter_api = twitter_api
        self.scheduler = AsyncIOScheduler()
        self.job = None
        self.interval = None
        self.last_run = None
        self.chat_id = None
        self.logger = logging.getLogger(__name__)
        self.lock = asyncio.Lock()  # Lock for thread safety
    
    def start(self, user_id: str, interval: int, chat_id: int = None):
        """
        Start tracking job
        
        Args:
            user_id: Twitter user ID or handle
            interval: Polling interval in minutes
            chat_id: Chat ID to send notifications to (optional)
        """
        # Stop existing job if any
        self.stop()
        
        # Set tracking parameters
        self.interval = interval
        self.chat_id = chat_id
        
        # Start new job
        self.job = self.scheduler.add_job(
            self.check_communities,
            'interval',
            minutes=interval,
            args=[user_id],
            next_run_time=datetime.now()  # Run immediately
        )
        
        # Start scheduler if not running
        if not self.scheduler.running:
            self.scheduler.start()
        
        self.logger.info(f"Started tracking {user_id} every {interval} minutes")
    
    def stop(self):
        """Stop tracking job"""
        if self.job:
            self.job.remove()
            self.job = None
            self.interval = None
            self.logger.info("Stopped tracking")
    
    async def check_communities(self, user_id: str):
        """
        Check for community changes
        
        Args:
            user_id: Twitter user ID or handle
        """
        self.logger.info(f"Checking communities for {user_id}")
        self.last_run = datetime.utcnow()
        
        # Get cookie
        cookie = get_cookie()
        if not cookie:
            self.logger.error("No cookie available for authentication")
            if self.chat_id:
                await self.bot.send_message(
                    self.chat_id,
                    "⚠️ Authentication failed: No cookie available.\n\n"
                    "Tracking has been paused. Please set a cookie using the 'Set Cookie' button."
                )
            self.stop()
            return
        
        try:
            # Get communities from Twitter API
            user_data = await self.twitter_api.get_user_communities(user_id)
            
            if not user_data:
                self.logger.error("Failed to get communities")
                return
            
            # Use lock to prevent concurrent database access
            async with self.lock:
                # Get saved communities
                with Session(engine) as session:
                    saved_communities = get_saved_communities(session)
                    
                    # Compare communities
                    joined_ids, left_ids, created_ids = self.twitter_api.diff_communities(
                        saved_communities, user_data.communities
                    )
                    
                    # Save new communities
                    save_communities(session, user_data.communities)
                    
                    # Save run
                    save_run(session, joined_ids, left_ids, created_ids)
            
            # Send notifications
            await self.send_notifications(user_data, joined_ids, left_ids, created_ids)
            
        except ValueError as e:
            # Handle specific errors
            error_message = str(e)
            self.logger.error(f"Error checking communities: {error_message}")
            
            if "private/protected" in error_message:
                if self.chat_id:
                    await self.bot.send_message(
                        self.chat_id,
                        f"⚠️ Target account is private or protected.\n\n"
                        f"Unable to fetch communities for {user_id}."
                    )
            
            elif "cookie" in error_message.lower():
                if self.chat_id:
                    await self.bot.send_message(
                        self.chat_id,
                        "⚠️ Authentication failed: Cookie expired or invalid.\n\n"
                        "Tracking has been paused. Please set a new cookie using the 'Set Cookie' button."
                    )
                self.stop()
            
            else:
                if self.chat_id:
                    await self.bot.send_message(
                        self.chat_id,
                        f"⚠️ Error checking communities: {error_message}"
                    )
        
        except Exception as e:
            # Handle general errors
            self.logger.error(f"Error checking communities: {str(e)}")
            if self.chat_id:
                await self.bot.send_message(
                    self.chat_id,
                    f"⚠️ Error checking communities: {str(e)}"
                )
    
    async def send_notifications(self, user_data, joined_ids: List[str], left_ids: List[str], created_ids: List[str]):
        """
        Send notifications for community changes
        
        Args:
            user_data: TwitterUserCommunityPayload object
            joined_ids: List of joined community IDs
            left_ids: List of left community IDs
            created_ids: List of created community IDs
        """
        if not self.chat_id:
            return
        
        # Map community IDs to Community objects
        community_map = {c.id: c for c in user_data.communities}
        
        # Bundle notifications if there are many
        if len(joined_ids) + len(left_ids) > 5:
            # Send summary message
            summary = []
            
            if joined_ids:
                joined_summary = []
                created_summary = []
                
                for community_id in joined_ids:
                    if community_id in community_map:
                        community = community_map[community_id]
                        if community_id in created_ids:
                            created_summary.append(f"• {community.name} ({community_id})")
                        else:
                            joined_summary.append(f"• {community.name} ({community_id})")
                
                if created_summary:
                    summary.append(f"🔵 CREATED ({len(created_summary)}):\n" + "\n".join(created_summary))
                if joined_summary:
                    summary.append(f"🟢 JOINED ({len(joined_summary)}):\n" + "\n".join(joined_summary))
            
            if left_ids:
                left_summary = [f"• {community_id}" for community_id in left_ids]
                summary.append(f"🔴 LEFT ({len(left_ids)}):\n" + "\n".join(left_summary))
            
            message = (
                f"Community changes for {user_data.name} (@{user_data.screen_name})   "
                f"{'✅ blue_verified' if user_data.is_blue_verified else ''}\n\n"
                + "\n\n".join(summary) + 
                f"\n\nTime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}"
            )
            
            await self.bot.send_message(self.chat_id, message)
            
            # If profile image is available, send it
            if user_data.profile_image_url_https:
                try:
                    await self.bot.send_photo(
                        self.chat_id,
                        user_data.profile_image_url_https,
                        caption=f"Profile photo: @{user_data.screen_name}"
                    )
                except Exception as e:
                    self.logger.error(f"Error sending profile image: {str(e)}")
            
            return
        
        # Send individual notifications
        # Send joined/created notifications
        for community_id in joined_ids:
            if community_id in community_map:
                community = community_map[community_id]
                
                # Check if created
                if community_id in created_ids:
                    emoji = "🔵"
                    action = "CREATED"
                else:
                    emoji = "🟢"
                    action = "JOINED"
                
                message = (
                    f"{emoji} {action}\n\n"
                    f"User: {user_data.name} (@{user_data.screen_name})   "
                    f"{'✅ blue_verified' if user_data.is_blue_verified else ''}\n"
                    f"Community: {community.name} ({community_id})\n"
                    f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}"
                )
                
                await self.bot.send_message(self.chat_id, message)
                
                # If profile image is available, send it
                if user_data.profile_image_url_https:
                    try:
                        await self.bot.send_photo(
                            self.chat_id,
                            user_data.profile_image_url_https,
                            caption=f"Profile photo: @{user_data.screen_name}"
                        )
                    except Exception as e:
                        self.logger.error(f"Error sending profile image: {str(e)}")
        
        # Send left notifications
        for community_id in left_ids:
            message = (
                f"🔴 LEFT\n\n"
                f"User: {user_data.name} (@{user_data.screen_name})   "
                f"{'✅ blue_verified' if user_data.is_blue_verified else ''}\n"
                f"Community: {community_id}\n"
                f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}"
            )
            
            await self.bot.send_message(self.chat_id, message)
