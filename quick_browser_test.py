#!/usr/bin/env python3
"""
Quick Browser Community Detection Test

This demonstrates the new REAL browser-based community detection
that captures actual DOM community metadata.
"""

import asyncio
import logging
import sys
import os

# Add the bot directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from twscrape import API
from bot.enhanced_community_tracker import EnhancedCommunityTracker
from bot.cookie_manager import CookieManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def quick_browser_test():
    """Quick test of browser-based community detection"""
    
    try:
        logger.info("🚀 Testing REAL browser-based community detection")
        
        # Initialize components
        api = API()
        cookie_manager = CookieManager()
        tracker = EnhancedCommunityTracker(api, cookie_manager)
        
        # Test with the user who has community content
        test_username = "163ba6y"
        
        logger.info(f"🌐 Testing REAL browser detection for @{test_username}")
        
        # Test browser-based detection (REAL community data)
        result = await tracker.get_all_user_communities(
            test_username, 
            deep_scan=True, 
            use_browser=True  # This is the key - REAL DOM parsing
        )
        
        if result:
            logger.info(f"✅ SUCCESS! Browser detection found {len(result.communities)} communities for @{result.screen_name}")
            
            if result.communities:
                logger.info(f"🎯 REAL Community Data Detected:")
                for i, community in enumerate(result.communities, 1):
                    logger.info(f"  🆕 {i}. {community.name}")
                    logger.info(f"      ID: {community.id}")
                    logger.info(f"      Role: {community.role}")
                    logger.info(f"      ─────────────────────────────")
                
                # Show the new notification format
                logger.info("")
                logger.info("🔔 New Notification Format:")
                logger.info("=" * 50)
                logger.info(f"🔔 Run completed for @{test_username}")
                logger.info("=" * 50)
                
                # Categorize for demo
                joined = [c for c in result.communities if getattr(c, 'source', 'unknown') in ['socialContext', 'directLink'] and c.role.lower() not in ['admin', 'creator']]
                created = [c for c in result.communities if getattr(c, 'source', 'unknown') in ['socialContext', 'directLink'] and c.role.lower() in ['admin', 'creator']]
                tweeted = [c for c in result.communities if getattr(c, 'source', 'unknown') in ['communitySpan', 'textMention']]
                
                if not (joined or created or tweeted):
                    # Default categorization if no source info
                    tweeted = result.communities
                
                logger.info(f"🎉 New communities joined: {len(joined)}")
                for community in joined:
                    logger.info(f"  • {community.name} (Role: {community.role})")
                
                logger.info(f"🚀 New communities created: {len(created)}")  
                for community in created:
                    logger.info(f"  • {community.name} (Role: {community.role})")
                
                logger.info(f"💬 New communities tweeted about: {len(tweeted)}")
                for community in tweeted:
                    logger.info(f"  • {community.name}")
                
                logger.info("=" * 50)
                
                logger.info(f"🔔 These represent community activity from the last 10 posts!")
            else:
                logger.info(f"📭 No NEW communities detected (may already be in cache)")
                
        else:
            logger.error("❌ Browser detection failed")
        
        logger.info("✅ Browser detection test completed")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.info("💡 Make sure you have Chrome installed and selenium package")
        logger.info("💡 Install: pip install selenium")

async def start_monitoring():
    """Start continuous monitoring (demo)"""
    
    try:
        logger.info("👁️ Starting continuous community monitoring demo")
        
        # Initialize components
        api = API()
        cookie_manager = CookieManager()
        tracker = EnhancedCommunityTracker(api, cookie_manager)
        
        test_username = "163ba6y"
        
        # Start monitoring (checks every 30 minutes)
        await tracker.monitor_user_communities(test_username, interval_minutes=30)
        
    except Exception as e:
        logger.error(f"❌ Monitoring failed: {e}")

async def main():
    """Main function"""
    logger.info("Choose test mode:")
    logger.info("1. Quick browser test")
    logger.info("2. Start monitoring")
    
    # For demo, just run quick test
    await quick_browser_test()

if __name__ == "__main__":
    asyncio.run(main())