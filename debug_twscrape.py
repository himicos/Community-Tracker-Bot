import asyncio
import logging
import os
from twscrape import API
from twscrape.logger import set_log_level

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set twscrape log level to DEBUG to see what's happening
set_log_level("DEBUG")

async def debug_user_lookup():
    """Debug user lookup functionality"""
    api = API("data/accounts.db")
    
    # List of usernames to test
    test_usernames = ["elonmusk", "nicdunz", "163ba6y"]
    
    logger.info("Starting debug session...")
    
    # Check accounts status
    try:
        accounts = await api.pool.accounts()
        logger.info(f"Available accounts: {len(accounts)}")
        for account in accounts:
            logger.info(f"Account: {account.username}, Active: {account.active}, Logged in: {account.logged_in}")
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
    
    # Test user lookups
    for username in test_usernames:
        logger.info(f"\n=== Testing user lookup for: {username} ===")
        
        try:
            # Test user_by_login
            user = await api.user_by_login(username)
            if user:
                logger.info(f"SUCCESS: Found user {username} - ID: {user.id}, Screen name: {user.username}")
            else:
                logger.error(f"FAILED: user_by_login returned None for {username}")
                
        except Exception as e:
            logger.error(f"EXCEPTION during user_by_login for {username}: {type(e).__name__}: {e}")
            
            # Check if it's a specific error type
            if "unauthorized" in str(e).lower() or "401" in str(e):
                logger.error("-> This looks like an authentication issue")
            elif "not found" in str(e).lower() or "404" in str(e):
                logger.error("-> This looks like a user not found error")
            elif "rate limit" in str(e).lower():
                logger.error("-> This looks like a rate limit issue")
            
        # Small delay between requests
        await asyncio.sleep(1)
    
    # Test raw GraphQL request
    logger.info("\n=== Testing raw GraphQL request ===")
    try:
        # Try a direct GraphQL request to UserByScreenName
        variables = {
            "screen_name": "elonmusk",
            "withSafetyModeUserFields": True
        }
        
        result = await api.raw_request("UserByScreenName", variables)
        if result:
            logger.info(f"Raw GraphQL request successful: {result.get('data', {}).get('user', {}).get('rest_id')}")
        else:
            logger.error("Raw GraphQL request returned None")
            
    except Exception as e:
        logger.error(f"Raw GraphQL request failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(debug_user_lookup()) 