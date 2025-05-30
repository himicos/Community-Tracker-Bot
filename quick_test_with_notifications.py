#!/usr/bin/env python3
"""
Quick Community Detection Test with Real Notifications
This script shows how community detection works and what notifications look like.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.twitter_api import TwitterAPI
from bot.enhanced_community_tracker_v2 import EnhancedCommunityTrackerV2

class QuickCommunityTest:
    """Quick test for community detection and notifications"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api = None
        self.tracker = None
    
    async def initialize(self):
        """Initialize API and tracker"""
        try:
            self.logger.info("🚀 Initializing Community Detection System...")
            
            # Initialize Twitter API
            self.api = TwitterAPI()
            
            # Initialize Enhanced Community Tracker V2
            self.tracker = EnhancedCommunityTrackerV2(self.api.api, self.api.cookie_manager)
            
            self.logger.info("✅ System initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def detect_and_notify(self, username: str):
        """Detect communities and show what notification would be sent"""
        try:
            print(f"\n🔍 DETECTING COMMUNITIES FOR @{username}")
            print("=" * 60)
            
            # Detect communities using our enhanced tracker
            result = await self.tracker.get_all_user_communities(username, deep_scan=True)
            
            if result and result.communities:
                communities = result.communities
                print(f"✅ Found {len(communities)} communities!")
                
                # Show detected communities
                print(f"\n📋 DETECTED COMMUNITIES:")
                for i, community in enumerate(communities, 1):
                    role_emoji = "👑" if community.role in ["Admin", "Creator"] else "👤"
                    print(f"  {i}. {role_emoji} {community.name}")
                    print(f"     Role: {community.role}")
                    print(f"     ID: {community.id}")
                    
                    # Show extra attributes if available
                    if hasattr(community, 'source'):
                        print(f"     Source: {community.source}")
                    if hasattr(community, 'confidence'):
                        print(f"     Confidence: {community.confidence:.2f}")
                
                # Generate notification that would be sent to Telegram
                notification = self._create_telegram_notification(username, communities)
                
                print(f"\n📱 TELEGRAM NOTIFICATION THAT WOULD BE SENT:")
                print("=" * 80)
                print(notification)
                print("=" * 80)
                
                return communities
            
            else:
                print(f"⚠️ No communities detected for @{username}")
                print("💡 Try posting about joining communities to test detection!")
                return []
                
        except Exception as e:
            print(f"❌ Error during detection: {e}")
            return []
    
    def _create_telegram_notification(self, username: str, communities: List) -> str:
        """Create a Telegram notification message"""
        message_parts = [
            f"🔔 **Community Detection Alert**\n",
            f"📍 User: @{username}",
            f"📊 Communities Found: {len(communities)}",
            f"🕐 Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        ]
        
        if communities:
            message_parts.append("🏘️ **Your Communities:**")
            
            for i, community in enumerate(communities, 1):
                role_emoji = "👑" if community.role in ["Admin", "Creator"] else "👤"
                message_parts.append(f"  {i}. {role_emoji} **{community.name}**")
                message_parts.append(f"     📝 Role: {community.role}")
                
                # Add extra info if available
                if hasattr(community, 'source'):
                    message_parts.append(f"     🔍 Detected via: {community.source}")
                if hasattr(community, 'confidence'):
                    message_parts.append(f"     📈 Confidence: {community.confidence:.0%}")
                
                message_parts.append("")  # Empty line between communities
        
        # Add summary
        admin_count = len([c for c in communities if c.role in ["Admin", "Creator"]])
        member_count = len([c for c in communities if c.role == "Member"])
        
        message_parts.append(f"📈 **Summary:**")
        message_parts.append(f"• Total Communities: {len(communities)}")
        message_parts.append(f"• Admin/Creator Roles: {admin_count}")
        message_parts.append(f"• Member Roles: {member_count}")
        
        message_parts.append(f"\n🤖 Community Tracker Bot")
        
        return "\n".join(message_parts)


async def main():
    """Main test function"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 QUICK COMMUNITY DETECTION & NOTIFICATION TEST")
    print("📱 This shows what happens when communities are detected")
    print("🔔 You'll see the exact notification that would be sent to Telegram")
    print()
    
    tester = QuickCommunityTest()
    
    if not await tester.initialize():
        print("❌ Failed to initialize system")
        return
    
    # Test with your username
    test_username = "163ba6y"  # Your Twitter username
    
    try:
        communities = await tester.detect_and_notify(test_username)
        
        print(f"\n🎉 TEST COMPLETED!")
        print(f"📊 Result: {len(communities)} communities detected")
        
        if communities:
            print(f"✅ Notification system working - message shown above would be sent to Telegram")
            print(f"🔔 When monitoring is active, you'd receive this notification automatically")
        else:
            print(f"💡 To test detection, try posting:")
            print(f"   'Just joined the AI Developers community!'")
            print(f"   'Created a new community called Test Community'")
            print(f"   'Excited to be part of the Web3 community'")
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 