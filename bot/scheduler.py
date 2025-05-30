import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlmodel import Session, select
import json
from typing import List, Optional, Dict, Any

from bot.models import Target, SavedCommunity, engine, get_saved_communities, save_communities, save_run, get_cookie, db_manager, DatabaseManager
from bot.twitter_api import TwitterAPI, Community

class CommunityScheduler:
    """Enhanced Community tracking scheduler with comprehensive monitoring"""
    
    def __init__(self, twitter_api: TwitterAPI, interval_minutes: int = 15):
        self.twitter_api = twitter_api
        self.interval_minutes = interval_minutes
        self.bot: Optional[Bot] = None
        self.chat_id: Optional[int] = None
        self.target_user: Optional[str] = None
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.logger = logging.getLogger(__name__)
        
        # Use global database manager
        self.db_manager = db_manager
        
        self.logger.info(f"Enhanced Community Scheduler initialized with {interval_minutes} minute intervals")
    
    def set_bot(self, bot: Bot):
        """Set the bot instance for notifications"""
        self.bot = bot
        self.logger.info("Bot instance set for scheduler")
    
    def set_notification_chat(self, chat_id: int):
        """Set the chat ID for sending notifications"""
        self.chat_id = chat_id
        self.logger.info(f"Notification chat set to: {chat_id}")
    
    def set_target_user(self, user_id: str):
        """Set the target user to monitor"""
        self.target_user = user_id
        self.logger.info(f"Target user set to: {user_id}")
    
    async def start(self, target_user: str):
        """Start monitoring communities for a user"""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return False
        
        self.target_user = target_user
        self.is_running = True
        
        self.logger.info(f"🚀 Starting enhanced community monitoring for @{target_user}")
        
        # Start the monitoring task
        self.task = asyncio.create_task(self._monitoring_loop())
        
        # Send startup notification
        if self.chat_id and self.bot:
            await self.bot.send_message(
                self.chat_id,
                f"🎯 **Enhanced Community Monitoring Started**\n\n"
                f"Target: @{target_user}\n"
                f"Interval: {self.interval_minutes} minutes\n"
                f"Features: Deep scanning, comprehensive detection\n\n"
                f"📡 Monitoring all community activities...",
                parse_mode="Markdown"
            )
        
        return True
    
    def stop(self):
        """Stop the community monitoring"""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return
        
        self.is_running = False
        
        if self.task:
            self.task.cancel()
            self.logger.info("Monitoring task cancelled")
        
        self.logger.info(f"🛑 Enhanced community monitoring stopped for @{self.target_user}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop with enhanced community tracking"""
        self.logger.info("Enhanced monitoring loop started")
        
        try:
            while self.is_running:
                if self.target_user:
                    await self.check_communities(self.target_user)
                
                # Wait for the next interval
                await asyncio.sleep(self.interval_minutes * 60)
                
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
            
            # Send error notification
            if self.chat_id and self.bot:
                await self.bot.send_message(
                    self.chat_id,
                    f"❌ **Monitoring Error**\n\n"
                    f"Error in monitoring loop: {str(e)}\n"
                    f"Monitoring will restart automatically.",
                    parse_mode="Markdown"
                )
            
            # Restart monitoring after a delay
            await asyncio.sleep(60)  # Wait 1 minute before restart
            if self.is_running:
                self.task = asyncio.create_task(self._monitoring_loop())
    
    def is_active(self) -> bool:
        """Check if the scheduler is currently active"""
        return self.is_running and self.task is not None and not self.task.done()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            'is_running': self.is_running,
            'target_user': self.target_user,
            'interval_minutes': self.interval_minutes,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'has_bot': self.bot is not None,
            'has_chat_id': self.chat_id is not None,
            'task_active': self.task is not None and not self.task.done() if self.task else False
        }

    async def check_communities(self, user_id: str):
        """
        Enhanced community change detection with comprehensive monitoring
        
        Uses multiple detection methods:
        1. Traditional community detection (URLs, profiles, etc.)  
        2. Post-based analysis for creation/joining indicators
        3. Activity pattern analysis
        
        Args:
            user_id: Twitter user ID or handle
        """
        self.logger.info(f"🚀 ====== NEW MONITORING RUN STARTED ======")
        self.logger.info(f"🎯 Target User: @{user_id}")
        self.logger.info(f"🕐 Run Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        self.logger.info(f"⏰ Interval: {self.interval_minutes} minutes")
        self.logger.info(f"📊 Previous Run: {self.last_run.strftime('%Y-%m-%d %H:%M:%S') if self.last_run else 'Never'} UTC")
        self.logger.info(f"🔍 Starting enhanced community check for {user_id}")
        
        self.last_run = datetime.utcnow()
        
        # Get saved cookies for authentication
        cookie_manager = self.twitter_api.cookie_manager
        saved_cookies = cookie_manager.list_cookie_sets()
        
        if not saved_cookies:
            self.logger.error("No authentication cookies available")
            if self.chat_id:
                await self.bot.send_message(
                    self.chat_id,
                    "⚠️ **Authentication Required**\n\n"
                    "No cookies are available for Twitter authentication.\n"
                    "Please upload cookies using the 'Set Cookie' button.\n\n"
                    "🔧 **Methods Available:**\n"
                    "• Manual extraction\n"
                    "• Auto-enriched (recommended)\n"
                    "• Browser export",
                    parse_mode="Markdown"
                )
            return
        
        # Load the most recent cookie set
        latest_cookie = saved_cookies[0]['name']  # Most recent
        success = await self.twitter_api.load_saved_cookies(latest_cookie)
        
        if not success:
            self.logger.error(f"Failed to load cookie set: {latest_cookie}")
            if self.chat_id:
                await self.bot.send_message(
                    self.chat_id,
                    "❌ **Authentication Failed**\n\n"
                    f"Could not load cookie set: {latest_cookie}\n"
                    "Cookies may be expired or corrupted.\n\n"
                    "Please upload fresh cookies.",
                    parse_mode="Markdown"
                )
            return
        
        self.logger.info(f"✅ Authenticated with cookie set: {latest_cookie}")
        
        try:
            # Get previous community state from database
            previous_communities = self.db_manager.get_user_communities(user_id)
            
            # Use ENHANCED tracking with post-based detection
            self.logger.info(f"🎯 Starting enhanced community tracking for @{user_id}")
            
            # Initialize enhanced tracker if not available
            # Force reinitialize to ensure we use V2 tracker
            if hasattr(self.twitter_api, 'enhanced_tracker'):
                delattr(self.twitter_api, 'enhanced_tracker')
            
            from bot.enhanced_community_tracker_v2 import EnhancedCommunityTrackerV2
            self.twitter_api.enhanced_tracker = EnhancedCommunityTrackerV2(
                self.twitter_api.api, self.twitter_api.cookie_manager
            )
            
            # Use enhanced tracking with multiple detection methods
            changes = await self.twitter_api.enhanced_tracker.track_community_changes(
                username=user_id,
                previous_communities=previous_communities,
                deep_scan=False  # Use lightweight monitoring for auto tracking
            )
            
            if changes.get('error'):
                self.logger.error(f"❌ Enhanced tracking failed for @{user_id}: {changes['error']}")
                if self.chat_id:
                    await self.bot.send_message(
                        self.chat_id,
                        f"❌ **Tracking Error**\n\n"
                        f"Could not fetch community data for @{user_id}\n\n"
                        f"Error: {changes['error']}\n\n"
                        f"Possible causes:\n"
                        f"• User doesn't exist or is suspended\n"
                        f"• Authentication expired\n"
                        f"• Twitter rate limits exceeded\n\n"
                        f"Will retry in next cycle.",
                        parse_mode="Markdown"
                    )
                return
            
            # Calculate current communities - FIX THE STRUCTURE
            raw_changes = changes.get('changes', {})  # Get the actual changes structure
            current_communities = []
            
            # Get joined communities from the correct structure  
            joined_communities = raw_changes.get('joined', [])
            for change in joined_communities:
                if hasattr(change, 'get') and 'community' in change:
                    current_communities.append(change['community'])
                else:
                    current_communities.append(change)
            
            # Get created communities
            created_communities = raw_changes.get('created', [])
            for change in created_communities:
                if hasattr(change, 'get') and 'community' in change:
                    current_communities.append(change['community'])
                else:
                    current_communities.append(change)
            
            # Add previous communities that weren't left
            left_communities = raw_changes.get('left', [])
            left_ids = set()
            for change in left_communities:
                if hasattr(change, 'get') and 'community' in change:
                    left_ids.add(change['community'].id)
                else:
                    left_ids.add(change.id)
            
            remaining_previous = [c for c in previous_communities if c.id not in left_ids]
            current_communities.extend(remaining_previous)
            
            self.logger.info(f"📊 Enhanced tracking results for @{user_id}:")
            self.logger.info(f"   • Detection methods used: {changes.get('detection_methods', [])}")
            self.logger.info(f"   • Previous communities: {len(previous_communities)}")
            self.logger.info(f"   • Current communities: {len(current_communities)}")
            self.logger.info(f"   • Changes detected: {len(joined_communities) + len(left_communities) + len(created_communities)}")
            
            # DEBUG: Log actual joined communities
            if joined_communities:
                self.logger.info(f"🔍 DEBUG: Joined communities list:")
                for i, change in enumerate(joined_communities):
                    if hasattr(change, 'get') and 'community' in change:
                        community = change['community']
                        self.logger.info(f"   {i+1}. {community.name} (ID: {community.id})")
                    else:
                        self.logger.info(f"   {i+1}. {change} (raw object)")
            else:
                self.logger.info(f"🔍 DEBUG: No joined communities found in raw_changes")
            
            # Log detected communities with confidence scores
            if current_communities:
                self.logger.info(f"🔍 All detected communities:")
                for i, community in enumerate(current_communities, 1):
                    confidence = changes.get('confidence_scores', {}).get(community.id, 'N/A')
                    self.logger.info(f"   {i}. {community.name} (Role: {community.role}, Confidence: {confidence})")
            
            # Process and notify about changes
            await self._process_enhanced_changes(user_id, changes, current_communities)
            
            # Update database with new community state
            self.db_manager.update_user_communities(user_id, current_communities)
            
            self.logger.info(f"✅ Enhanced community check completed for @{user_id}")
            
        except Exception as e:
            self.logger.error(f"Error in enhanced community checking for {user_id}: {e}")
            if self.chat_id:
                await self.bot.send_message(
                    self.chat_id,
                    f"❌ **Monitoring Error**\n\n"
                    f"Error monitoring @{user_id}: {str(e)}\n\n"
                    f"This may indicate:\n"
                    f"• Twitter API changes\n"
                    f"• Authentication issues\n"
                    f"• Network connectivity problems\n\n"
                    f"Monitoring will continue automatically.",
                    parse_mode="Markdown"
                )
    
    async def _process_enhanced_changes(self, user_id: str, changes: Dict[str, Any], all_communities: List):
        """
        Process and notify about enhanced community changes
        
        Args:
            user_id: Twitter username
            changes: Dictionary with detected changes
            all_communities: Complete list of current communities
        """
        if changes.get('error'):
            self.logger.error(f"Error in change detection: {changes['error']}")
            return
        
        # Extract change data - FIX THE STRUCTURE
        raw_changes = changes.get('changes', {})
        joined = raw_changes.get('joined', [])
        left = raw_changes.get('left', [])
        created = raw_changes.get('created', [])
        role_changes = raw_changes.get('role_changed', [])  # Note: role_changed not role_changes
        
        total_changes = len(joined) + len(left) + len(created) + len(role_changes)
        
        # ALWAYS send a scan completion notification
        if total_changes == 0:
            self.logger.info(f"✅ No community changes detected for @{user_id}")
            
            if self.chat_id:
                # Send simple scan completion notification
                message = f"🔍 **Scan Completed**\n\n"
                message += f"Target: @{user_id}\n"
                message += f"Communities found: {len(all_communities)}\n"
                
                if len(all_communities) > 0:
                    message += f"\n📋 **Current Communities:**\n"
                    for i, community in enumerate(all_communities[:5], 1):
                        message += f"   {i}. {community.name}\n"
                    if len(all_communities) > 5:
                        message += f"   ... and {len(all_communities) - 5} more\n"
                else:
                    message += f"\nNo communities detected.\n"
                
                message += f"\n⏰ Next scan in {self.interval_minutes} minutes"
                
                try:
                    await self.bot.send_message(self.chat_id, message, parse_mode="Markdown")
                    self.logger.info(f"📤 Scan completion notification sent for @{user_id}")
                except Exception as e:
                    self.logger.error(f"Error sending scan notification: {e}")
            
            return
        
        self.logger.info(f"🚨 Community changes detected for @{user_id}: {total_changes} changes")
        
        if not self.chat_id:
            self.logger.warning("No chat_id set - cannot send notifications")
            return
        
        # Build enhanced notification message
        message_parts = [f"🔔 **Community Activity Detected**\n"]
        message_parts.append(f"User: @{user_id}")
        message_parts.append(f"Scan type: {changes.get('scan_type', 'Enhanced Tracking')}")
        message_parts.append(f"Total changes: {total_changes}\n")
        
        # Joined communities
        if joined:
            message_parts.append(f"✅ **Joined Communities ({len(joined)}):**")
            for change in joined[:5]:  # Limit to prevent message overflow
                community = change['community']  # Extract Community object from dict
                role_emoji = "👑" if community.role == "Admin" else "👤"
                # Escape markdown characters in community name
                safe_name = community.name.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace(']', r'\]')
                community_url = f"https://x.com/i/communities/{community.id}"
                message_parts.append(f"   {role_emoji} **{safe_name}**")
                message_parts.append(f"      Link: {community_url}")
                message_parts.append(f"      Role: {community.role}")
            
            if len(joined) > 5:
                message_parts.append(f"   ... and {len(joined) - 5} more")
            message_parts.append("")
        
        # Created communities
        if created:
            message_parts.append(f"🆕 **Created Communities ({len(created)}):**")
            for change in created[:3]:  # Fewer for created since they're more important
                community = change['community']  # Extract Community object from dict
                # Escape markdown characters in community name
                safe_name = community.name.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace(']', r'\]')
                community_url = f"https://x.com/i/communities/{community.id}"
                message_parts.append(f"   👑 **{safe_name}**")
                message_parts.append(f"      Link: {community_url}")
                message_parts.append(f"      Role: {community.role}")
            
            if len(created) > 3:
                message_parts.append(f"   ... and {len(created) - 3} more")
            message_parts.append("")
        
        # Left communities
        if left:
            message_parts.append(f"❌ **Left Communities ({len(left)}):**")
            for change in left[:5]:
                community = change['community']  # Extract Community object from dict
                # Escape markdown characters in community name
                safe_name = community.name.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace(']', r'\]')
                community_url = f"https://x.com/i/communities/{community.id}"
                message_parts.append(f"   🚪 **{safe_name}**")
                message_parts.append(f"      Link: {community_url}")
                message_parts.append(f"      Previous role: {community.role}")
            
            if len(left) > 5:
                message_parts.append(f"   ... and {len(left) - 5} more")
            message_parts.append("")
        
        # Role changes
        if role_changes:
            message_parts.append(f"🔄 **Role Changes ({len(role_changes)}):**")
            for change in role_changes[:3]:
                community = change['community']
                old_role = change['old_role']
                new_role = change['new_role']
                
                role_emoji = "📈" if new_role == "Admin" else "📉"
                message_parts.append(f"   {role_emoji} {community.name}")
                message_parts.append(f"      {old_role} → {new_role}")
            
            if len(role_changes) > 3:
                message_parts.append(f"   ... and {len(role_changes) - 3} more")
            message_parts.append("")
        
        # Add summary
        message_parts.append(f"📊 **Current Status:**")
        message_parts.append(f"Total communities: {len(all_communities)}")
        message_parts.append(f"Admin roles: {len([c for c in all_communities if c.role == 'Admin'])}")
        message_parts.append(f"Member roles: {len([c for c in all_communities if c.role == 'Member'])}")
        
        message_parts.append(f"\n⏰ Detected at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # Send notification
        full_message = "\n".join(message_parts)
        
        try:
            await self.bot.send_message(
                self.chat_id,
                full_message,
                parse_mode="Markdown"
            )
            
            self.logger.info(f"📤 Enhanced notification sent for @{user_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending enhanced notification: {e}")
            
            # Try sending without markdown if formatting fails
            try:
                simple_message = f"🔔 **Community Changes Detected for @{user_id}**\n\n"
                
                if joined:
                    simple_message += f"✅ **Joined {len(joined)} Communities:**\n"
                    for change in joined[:5]:
                        community = change['community']
                        community_url = f"https://x.com/i/communities/{community.id}"
                        simple_message += f"• {community.name}\n"
                        simple_message += f"  Link: {community_url}\n"
                        simple_message += f"  Role: {community.role}\n\n"
                
                if created:
                    simple_message += f"🆕 **Created {len(created)} Communities:**\n"
                    for change in created[:3]:
                        community = change['community']
                        community_url = f"https://x.com/i/communities/{community.id}"
                        simple_message += f"• {community.name}\n"
                        simple_message += f"  Link: {community_url}\n"
                        simple_message += f"  Role: {community.role}\n\n"
                
                if left:
                    simple_message += f"❌ **Left {len(left)} Communities:**\n"
                    for change in left[:5]:
                        community = change['community']
                        community_url = f"https://x.com/i/communities/{community.id}"
                        simple_message += f"• {community.name}\n"
                        simple_message += f"  Link: {community_url}\n\n"
                
                simple_message += f"📊 **Summary:** Joined: {len(joined)}, Left: {len(left)}, Created: {len(created)}, Role changes: {len(role_changes)}\n"
                simple_message += f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                
                await self.bot.send_message(self.chat_id, simple_message, parse_mode="Markdown")
                self.logger.info(f"📤 Fallback notification sent for @{user_id}")
                
            except Exception as e2:
                self.logger.error(f"Error sending fallback notification: {e2}")
                
                # Final fallback - plain text
                try:
                    plain_message = f"Community changes detected for @{user_id}:\n"
                    plain_message += f"Joined: {len(joined)}, Left: {len(left)}, Created: {len(created)}, Role changes: {len(role_changes)}\n\n"
                    
                    if joined:
                        plain_message += "Joined Communities:\n"
                        for change in joined[:3]:
                            community = change['community']
                            plain_message += f"- {community.name} (Role: {community.role})\n"
                            plain_message += f"  https://x.com/i/communities/{community.id}\n"
                    
                    await self.bot.send_message(self.chat_id, plain_message)
                    self.logger.info(f"📤 Plain text notification sent for @{user_id}")
                    
                except Exception as e3:
                    self.logger.error(f"All notification methods failed: {e3}")
    
    async def _send_periodic_summary(self, user_id: str, communities: List):
        """Send periodic summary of current community state"""
        try:
            message_parts = [f"📋 **Community Summary for @{user_id}**\n"]
            
            # Categorize communities by role
            admin_communities = [c for c in communities if c.role == "Admin"]
            member_communities = [c for c in communities if c.role == "Member"]
            other_communities = [c for c in communities if c.role not in ["Admin", "Member"]]
            
            message_parts.append(f"Total communities: {len(communities)}")
            
            if admin_communities:
                message_parts.append(f"\n👑 **Admin/Creator ({len(admin_communities)}):**")
                for community in admin_communities[:3]:
                    message_parts.append(f"   • {community.name}")
                if len(admin_communities) > 3:
                    message_parts.append(f"   ... and {len(admin_communities) - 3} more")
            
            if member_communities:
                message_parts.append(f"\n👤 **Member ({len(member_communities)}):**")
                for community in member_communities[:5]:
                    message_parts.append(f"   • {community.name}")
                if len(member_communities) > 5:
                    message_parts.append(f"   ... and {len(member_communities) - 5} more")
            
            if other_communities:
                message_parts.append(f"\n🔧 **Other roles ({len(other_communities)}):**")
                for community in other_communities[:3]:
                    message_parts.append(f"   • {community.name} ({community.role})")
            
            message_parts.append(f"\n📡 Monitoring actively...")
            message_parts.append(f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            await self.bot.send_message(
                self.chat_id,
                "\n".join(message_parts),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            self.logger.error(f"Error sending periodic summary: {e}")
