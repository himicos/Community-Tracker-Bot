#!/usr/bin/env python3
"""
Test script to verify CSRF fixes for Twitter API integration
"""
import asyncio
import logging
import os
import sys

# Add the current directory to the path so we can import bot modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.twitter_api import TwitterAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_twitter_api():
    """Test the improved Twitter API with CSRF fixes"""
    logger = logging.getLogger(__name__)
    
    print("🔍 Testing Twitter API with CSRF fixes...")
    print("=" * 50)
    
    # Initialize Twitter API
    api = TwitterAPI()
    
    # Test user lookup without authentication first (this should still fail)
    test_users = ["elonmusk", "nicdunz", "163ba6y"]
    
    for user in test_users:
        print(f"\n📋 Testing user lookup for: {user}")
        try:
            result = await api.get_user_communities(user)
            if result:
                print(f"✅ SUCCESS: Found user {result.name} (@{result.screen_name})")
                print(f"   User ID: {result.user_id}")
                print(f"   Verified: {result.verified}")
                print(f"   Blue Verified: {result.is_blue_verified}")
                print(f"   Communities: {len(result.communities)}")
            else:
                print(f"❌ FAILED: Could not lookup user {user}")
        except Exception as e:
            error_msg = str(e)
            if "csrf" in error_msg.lower() or "403" in error_msg:
                print(f"🔐 CSRF Error (Expected): {error_msg}")
                print("   This indicates you need to add authentication cookies.")
            else:
                print(f"❌ Other Error: {error_msg}")
    
    print("\n" + "=" * 50)
    print("📋 Cookie Requirements:")
    print("=" * 50)
    print("To fix the CSRF errors, you need to add Twitter authentication cookies.")
    print("\n🍪 Required Cookie Format:")
    print("auth_token=YOUR_LONG_TOKEN; ct0=YOUR_CSRF_TOKEN; guest_id=v1%3A...; personalization_id=\"v1_...=\";")
    print("\n📱 How to get cookies:")
    print("1. Login to Twitter/X in your browser")
    print("2. Open Developer Tools (F12)")
    print("3. Go to Application/Storage → Cookies → x.com")
    print("4. Copy the values for:")
    print("   - auth_token (long hex string)")
    print("   - ct0 (32+ character CSRF token)")
    print("   - guest_id (visitor ID)")
    print("   - personalization_id (preferences)")
    print("\n🔧 Testing with cookies:")
    print("Once you have cookies, use the bot's /add_cookie command to add them.")
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_twitter_api()) 