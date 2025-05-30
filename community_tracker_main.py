#!/usr/bin/env python3
"""
Community Tracker Main Integration

This module provides the main function that gets called from the Telegram bot
when users click "Start Tracking". It uses real browser-based community detection
with proper authentication.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, List, Optional, Tuple

# Add the bot directory to Python path
sys.path.append(os.path.dirname(__file__))

from twscrape import API
from bot.enhanced_community_tracker import EnhancedCommunityTracker
from bot.cookie_manager import CookieManager
from bot.models import Community

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def start_community_tracking(username: str, user_id: int = None) -> Dict:
    """
    Main function called from Telegram bot when "Start Tracking" is clicked
    
    Args:
        username: Twitter username to track (without @)
        user_id: Telegram user ID (optional, for logging)
        
    Returns:
        Dictionary with tracking results and categorized communities
    """
    try:
        logger.info(f"🚀 Starting community tracking for @{username} (Telegram user: {user_id})")
        
        # Initialize components
        api = API()
        cookie_manager = CookieManager()
        tracker = EnhancedCommunityTracker(api, cookie_manager)
        
        # Check if we have cookies for authentication
        cookie_sets = cookie_manager.list_cookie_sets()
        if not cookie_sets:
            return {
                'success': False,
                'error': 'no_cookies',
                'message': 'No authentication cookies found. Please upload cookies first.',
                'communities': {
                    'joined': [],
                    'created': [],
                    'tweeted': []
                }
            }
        
        # Perform community detection with browser automation
        result = await tracker.get_all_user_communities(
            username, 
            deep_scan=True, 
            use_browser=True  # This enables REAL DOM detection
        )
        
        if not result:
            return {
                'success': False,
                'error': 'user_not_found',
                'message': f'User @{username} not found or profile is private.',
                'communities': {
                    'joined': [],
                    'created': [],
                    'tweeted': []
                }
            }
        
        # Categorize communities
        categorized = categorize_communities(result.communities)
        
        # Prepare response
        response = {
            'success': True,
            'username': username,
            'display_name': result.name,
            'user_id': result.user_id,
            'total_communities': len(result.communities),
            'communities': categorized,
            'message': f'Successfully tracked {len(result.communities)} communities for @{username}'
        }
        
        logger.info(f"✅ Community tracking completed for @{username}")
        logger.info(f"📊 Found: {len(categorized['joined'])} joined, {len(categorized['created'])} created, {len(categorized['tweeted'])} tweeted")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error in community tracking: {e}")
        return {
            'success': False,
            'error': 'tracking_failed',
            'message': f'Community tracking failed: {str(e)}',
            'communities': {
                'joined': [],
                'created': [],
                'tweeted': []
            }
        }


def categorize_communities(communities: List[Community]) -> Dict[str, List[Dict]]:
    """
    Categorize communities into joined, created, and tweeted about
    
    Args:
        communities: List of Community objects
        
    Returns:
        Dictionary with categorized community lists
    """
    joined = []
    created = []
    tweeted = []
    
    for community in communities:
        # Get source information
        source = getattr(community, 'source', 'unknown')
        role = community.role.lower()
        
        community_dict = {
            'id': community.id,
            'name': community.name,
            'role': community.role,
            'source': source
        }
        
        # Categorize based on source and role
        if source in ['socialContext', 'directLink']:
            # These are real community memberships
            if role in ['admin', 'creator', 'owner', 'moderator']:
                created.append(community_dict)
            else:
                joined.append(community_dict)
        elif source in ['communitySpan', 'textMention']:
            # These are communities mentioned in tweets
            tweeted.append(community_dict)
        else:
            # Default categorization for unknown sources
            if role in ['admin', 'creator', 'owner', 'moderator']:
                created.append(community_dict)
            else:
                tweeted.append(community_dict)
    
    return {
        'joined': joined,
        'created': created,
        'tweeted': tweeted
    }


async def quick_community_check(username: str) -> Dict:
    """
    Quick community check without browser (faster, API-based only)
    
    Args:
        username: Twitter username to check
        
    Returns:
        Dictionary with quick results
    """
    try:
        logger.info(f"⚡ Quick community check for @{username}")
        
        # Initialize components
        api = API()
        cookie_manager = CookieManager()
        tracker = EnhancedCommunityTracker(api, cookie_manager)
        
        # Perform fast community detection (no browser)
        result = await tracker.get_all_user_communities(
            username, 
            deep_scan=False,  # Fast mode
            use_browser=False  # API-based only
        )
        
        if not result:
            return {
                'success': False,
                'error': 'user_not_found',
                'communities': []
            }
        
        # Prepare response
        communities_list = []
        for community in result.communities:
            communities_list.append({
                'id': community.id,
                'name': community.name,
                'role': community.role
            })
        
        return {
            'success': True,
            'username': username,
            'communities': communities_list,
            'total': len(communities_list)
        }
        
    except Exception as e:
        logger.error(f"❌ Error in quick check: {e}")
        return {
            'success': False,
            'error': 'check_failed',
            'communities': []
        }


async def monitor_user_communities(username: str, interval_minutes: int = 30) -> None:
    """
    Start continuous monitoring for a user (background task)
    
    Args:
        username: Twitter username to monitor
        interval_minutes: Check interval in minutes
    """
    try:
        logger.info(f"👁️ Starting continuous monitoring for @{username}")
        
        # Initialize components
        api = API()
        cookie_manager = CookieManager()
        tracker = EnhancedCommunityTracker(api, cookie_manager)
        
        # Start monitoring (this runs indefinitely)
        await tracker.monitor_user_communities(username, interval_minutes)
        
    except Exception as e:
        logger.error(f"❌ Error in monitoring: {e}")


def run_tracking_async(username: str, user_id: int = None) -> Dict:
    """
    Synchronous wrapper for async tracking function
    Call this from the Telegram bot
    
    Args:
        username: Twitter username to track
        user_id: Telegram user ID
        
    Returns:
        Dictionary with tracking results
    """
    try:
        # Run the async function
        result = asyncio.run(start_community_tracking(username, user_id))
        return result
    except Exception as e:
        logger.error(f"❌ Error in sync wrapper: {e}")
        return {
            'success': False,
            'error': 'wrapper_failed',
            'message': f'Tracking wrapper failed: {str(e)}',
            'communities': {
                'joined': [],
                'created': [],
                'tweeted': []
            }
        }


if __name__ == "__main__":
    # Test the tracking system
    test_username = "163ba6y"
    result = run_tracking_async(test_username)
    print(f"Tracking result: {result}") 