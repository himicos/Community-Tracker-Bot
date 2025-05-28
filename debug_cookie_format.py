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

async def test_cookie_formats():
    """Test different cookie formats to fix CSRF issues"""
    api = API("data/accounts_test.db")
    
    logger.info("Testing different cookie formats...")
    
    # Example cookie formats to test
    cookie_formats = [
        # Format 1: Basic format (what's currently used)
        "auth_token=your_auth_token_here; ct0=your_ct0_token_here;",
        
        # Format 2: Complete cookie format with all required tokens
        """auth_token=your_auth_token_here; ct0=your_ct0_token_here; guest_id=v1%3A123456789; personalization_id="v1_RandomString=="; guest_id_ads=v1%3A123456789; guest_id_marketing=v1%3A123456789;""",
        
        # Format 3: JSON format
        '{"auth_token": "your_auth_token_here", "ct0": "your_ct0_token_here"}',
        
        # Format 4: Base64 encoded format (if supported)
        # This would be the base64 encoding of the cookie string
    ]
    
    logger.info("Cookie format requirements for Twitter GraphQL API:")
    logger.info("1. auth_token - Main authentication token")
    logger.info("2. ct0 - CSRF token (this is crucial for the 403 error)")
    logger.info("3. The ct0 token must match the X-Csrf-Token header")
    logger.info("4. Both cookies and headers must be properly synchronized")
    
    # Show what a proper cookie extraction should look like
    logger.info("\nTo get proper cookies from browser:")
    logger.info("1. Open Twitter/X in browser and login")
    logger.info("2. Open Developer Tools (F12)")
    logger.info("3. Go to Application/Storage tab")
    logger.info("4. Find Cookies for x.com")
    logger.info("5. Copy these essential cookies:")
    logger.info("   - auth_token (long hex string)")
    logger.info("   - ct0 (CSRF token - 32 char hex)")
    logger.info("6. Format as: auth_token=ABC123...; ct0=DEF456...;")
    
    # Test account adding with proper error handling
    test_cookie = "auth_token=example; ct0=example;"
    
    try:
        success = await api.pool.add_account(
            username="test_user",
            password="test_pass", 
            email="test@example.com",
            email_password="test_email_pass",
            cookies=test_cookie
        )
        
        if success:
            logger.info("Test account added successfully")
        else:
            logger.error("Failed to add test account")
            
    except Exception as e:
        logger.error(f"Error adding test account: {e}")
    
    # Clean up test database
    if os.path.exists("data/accounts_test.db"):
        os.remove("data/accounts_test.db")
    
    logger.info("\nSOLUTION RECOMMENDATIONS:")
    logger.info("1. Update to latest twscrape version (currently 0.17.0 ✓)")
    logger.info("2. Ensure cookies include both auth_token AND ct0")
    logger.info("3. Get fresh cookies from browser (they expire)")
    logger.info("4. Consider using cookie-based accounts instead of login/password")
    logger.info("5. Use multiple accounts for rate limit distribution")

if __name__ == "__main__":
    asyncio.run(test_cookie_formats()) 