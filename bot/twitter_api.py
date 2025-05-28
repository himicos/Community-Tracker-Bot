import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import json
import re
import secrets
import base64

from twscrape import API, AccountsPool
from twscrape.logger import set_log_level

from bot.models import Community, TwitterUserCommunityPayload, get_next_available_proxy, update_proxy_last_used, get_proxy_accounts

class TwitterAPI:
    """Improved Twitter API class with better cookie handling and CSRF management"""
    
    def __init__(self, proxy: Optional[str] = None):
        # Initialize API with proxy if provided
        self.proxy = proxy
        self.current_proxy_id = None
        
        # If no proxy provided, try to get one from database
        if not proxy:
            proxy_account = get_next_available_proxy()
            if proxy_account:
                proxy = proxy_account.proxy_url
                self.current_proxy_id = proxy_account.id
                self.logger = logging.getLogger(__name__)
                self.logger.info(f"Auto-selected proxy from database: {proxy_account.account_name}")
        
        self.api = API(proxy=proxy) if proxy else API()
        self.logger = logging.getLogger(__name__)
        # Set twscrape log level to ERROR to reduce noise
        set_log_level("ERROR")
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Initialize accounts pool file
        self.accounts_db = "data/accounts.db"
        
        self.logger.info(f"TwitterAPI initialized with proxy: {proxy if proxy else 'None'}")
    
    def generate_guest_id(self) -> str:
        """Generate a proper guest_id in Twitter's format"""
        # Twitter guest_id format: v1%3A{timestamp}
        timestamp = int(datetime.now().timestamp())
        return f"v1%3A{timestamp}"
    
    def generate_personalization_id(self) -> str:
        """Generate a proper personalization_id in Twitter's format"""
        # Twitter personalization_id format: "v1_{base64_random}=="
        # Generate 16 random bytes and base64 encode
        random_bytes = secrets.token_bytes(12)  # 12 bytes = 16 chars base64
        encoded = base64.b64encode(random_bytes).decode('ascii')
        return f'"v1_{encoded}=="'
    
    def generate_guest_id_ads(self) -> str:
        """Generate guest_id_ads (same format as guest_id)"""
        return self.generate_guest_id()
    
    def generate_guest_id_marketing(self) -> str:
        """Generate guest_id_marketing (same format as guest_id)"""
        return self.generate_guest_id()
    
    def validate_cookie_format(self, cookie_str: str) -> bool:
        """
        Validate cookie format and ensure it contains required tokens
        
        Args:
            cookie_str: Cookie string to validate
            
        Returns:
            bool: True if cookie format is valid
        """
        # Check for required tokens
        has_auth_token = 'auth_token=' in cookie_str
        has_ct0 = 'ct0=' in cookie_str
        
        if not has_auth_token:
            self.logger.error("Cookie missing auth_token")
            return False
            
        if not has_ct0:
            self.logger.error("Cookie missing ct0 (CSRF token)")
            return False
        
        # Extract ct0 token to validate format
        ct0_match = re.search(r'ct0=([^;]+)', cookie_str)
        if ct0_match:
            ct0_token = ct0_match.group(1)
            # ct0 should be a 32+ character hex string
            if len(ct0_token) < 32:
                self.logger.warning(f"ct0 token seems too short: {len(ct0_token)} chars")
        
        return True
    
    def enhance_cookie_string(self, cookie_str: str) -> str:
        """
        Enhance cookie string with additional required cookies for better compatibility
        
        Args:
            cookie_str: Original cookie string
            
        Returns:
            str: Enhanced cookie string
        """
        # Parse existing cookies
        cookies = {}
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        # Generate missing essential cookies if not present
        if 'guest_id' not in cookies:
            cookies['guest_id'] = self.generate_guest_id()
            self.logger.info("Generated guest_id")
        
        if 'personalization_id' not in cookies:
            cookies['personalization_id'] = self.generate_personalization_id()
            self.logger.info("Generated personalization_id")
        
        if 'guest_id_ads' not in cookies:
            cookies['guest_id_ads'] = self.generate_guest_id_ads()
            self.logger.info("Generated guest_id_ads")
        
        if 'guest_id_marketing' not in cookies:
            cookies['guest_id_marketing'] = self.generate_guest_id_marketing()
            self.logger.info("Generated guest_id_marketing")
        
        # Reconstruct cookie string
        enhanced_parts = []
        for key, value in cookies.items():
            enhanced_parts.append(f"{key}={value}")
        
        enhanced_cookie = '; '.join(enhanced_parts) + ';'
        return enhanced_cookie

    def get_rotating_proxy(self) -> Optional[str]:
        """Get next available proxy for rotation"""
        proxy_account = get_next_available_proxy()
        if proxy_account:
            update_proxy_last_used(proxy_account.id)
            self.current_proxy_id = proxy_account.id
            self.logger.info(f"Using rotating proxy: {proxy_account.account_name} ({proxy_account.proxy_url[:30]}...)")
            return proxy_account.proxy_url
        return None
    
    def set_proxy(self, proxy: str):
        """Set proxy for the API instance"""
        self.proxy = proxy
        self.api = API(proxy=proxy)
        
        # Try to find the proxy in database to track usage
        proxy_accounts = get_proxy_accounts()
        for proxy_account in proxy_accounts:
            if proxy_account.proxy_url == proxy:
                self.current_proxy_id = proxy_account.id
                update_proxy_last_used(proxy_account.id)
                break
        
        self.logger.info(f"Proxy set to: {proxy}")

    async def add_account_from_cookie(self, cookie_str: str, proxy: Optional[str] = None, account_name: Optional[str] = None) -> bool:
        """
        Add a Twitter account to the pool using cookie string with improved validation
        
        Args:
            cookie_str: Twitter authentication cookie string (auth_token=...; ct0=...)
            proxy: Optional proxy URL
            account_name: Optional account name for identification
            
        Returns:
            bool: True if account was added successfully, False otherwise
        """
        try:
            # Validate cookie format first
            if not self.validate_cookie_format(cookie_str):
                self.logger.error("Invalid cookie format. Must contain auth_token and ct0.")
                return False
            
            # Enhance cookie string with additional tokens
            enhanced_cookie = self.enhance_cookie_string(cookie_str)
            self.logger.info(f"Enhanced cookie with additional tokens")
            
            # Parse cookie string to extract auth_token and ct0
            auth_token = None
            ct0 = None
            
            for part in enhanced_cookie.split(';'):
                part = part.strip()
                if part.startswith('auth_token='):
                    auth_token = part.split('=', 1)[1]
                elif part.startswith('ct0='):
                    ct0 = part.split('=', 1)[1]
            
            if not auth_token or not ct0:
                self.logger.error("Failed to extract auth_token or ct0 from cookie.")
                return False
            
            # Use provided proxy, instance proxy, or rotating proxy
            use_proxy = proxy or self.proxy
            if not use_proxy:
                use_proxy = self.get_rotating_proxy()
            
            # Create a new accounts pool with proxy support
            pool = AccountsPool(self.accounts_db)
            
            self.logger.info(f"Adding account {account_name or 'twitter_user'} with enhanced cookies")
            
            # Add account using enhanced cookies with proxy
            await pool.add_account(
                username=account_name or "twitter_user",
                password="password_placeholder",
                email="email@placeholder.com",
                email_password="email_pass_placeholder",
                cookies=enhanced_cookie,
                proxy=use_proxy
            )
            
            # Reinitialize API with proxy if needed
            if use_proxy and not self.proxy:
                self.api = API(proxy=use_proxy)
                self.proxy = use_proxy
            
            self.logger.info(f"Account {account_name or 'twitter_user'} added successfully with enhanced cookies")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding account from cookie: {str(e)}")
            return False

    async def get_user_communities(self, user_id_or_handle: str) -> Optional[TwitterUserCommunityPayload]:
        """
        Get communities for a Twitter user with retry logic for CSRF issues
        
        Args:
            user_id_or_handle: Twitter user ID or handle
            
        Returns:
            TwitterUserCommunityPayload object or None if error
        """
        return await self.get_user_communities_with_retries(user_id_or_handle, max_retries=3)

    async def get_user_communities_with_retries(self, user_id_or_handle: str, max_retries: int = 3) -> Optional[TwitterUserCommunityPayload]:
        """
        Get communities for a Twitter user with retry logic for CSRF issues
        
        Args:
            user_id_or_handle: Twitter user ID or handle
            max_retries: Maximum number of retries
            
        Returns:
            TwitterUserCommunityPayload object or None if error
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Attempt {attempt + 1}/{max_retries} for user lookup: {user_id_or_handle}")
                
                # Determine if input is user ID or handle
                is_user_id = user_id_or_handle.isdigit()
                
                # Get user info first
                if is_user_id:
                    user = await self.api.user_by_id(user_id_or_handle)
                else:
                    user_handle = user_id_or_handle.lstrip('@')
                    user = await self.api.user_by_login(user_handle)
                
                if not user:
                    self.logger.error(f"User not found: {user_id_or_handle}")
                    return None
                
                # If we successfully got user info, try to get communities
                # For now, return basic user info since community endpoint might have similar CSRF issues
                return TwitterUserCommunityPayload(
                    user_id=user.id_str,
                    screen_name=user.username,
                    name=user.name,
                    profile_image_url_https=getattr(user, 'profile_image_url_https', ''),
                    is_blue_verified=getattr(user, 'is_blue_verified', False),
                    verified=getattr(user, 'verified', False),
                    communities=[]  # Empty for now due to CSRF issues
                )
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                if "csrf" in error_str or "403" in error_str:
                    self.logger.warning(f"CSRF error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                else:
                    # Non-CSRF error, don't retry
                    break
        
        # All retries failed
        if last_error:
            error_str = str(last_error).lower()
            if "unauthorized" in error_str or "401" in error_str:
                raise ValueError("Target account is private/protected")
            elif "csrf" in error_str or "cookie" in error_str or "auth" in error_str:
                raise ValueError("Authentication cookie expired or invalid - CSRF token mismatch")
            
            raise last_error
        
        return None

    def diff_communities(self, old_communities: List[Community], new_communities: List[Community]) -> Tuple[List[str], List[str], List[str]]:
        """Compare old and new community lists"""
        new_ids = {c.id for c in new_communities}
        old_ids = {c.id for c in old_communities}
        
        joined_ids = new_ids - old_ids
        left_ids = old_ids - new_ids
        created_ids = {c.id for c in new_communities if c.role == "Admin" and c.id in joined_ids}
        
        return list(joined_ids), list(left_ids), list(created_ids)
