import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import json

from twscrape import API, AccountsPool
from twscrape.logger import set_log_level

from bot.models import Community, TwitterUserCommunityPayload

class TwitterAPI:
    """Class for interacting with Twitter API using twscrape"""
    
    def __init__(self):
        self.api = API()
        self.logger = logging.getLogger(__name__)
        # Set twscrape log level to ERROR to reduce noise
        set_log_level("ERROR")
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Initialize accounts pool file
        self.accounts_db = "data/accounts.db"
    
    async def add_account_from_cookie(self, cookie_str: str) -> bool:
        """
        Add a Twitter account to the pool using cookie string
        
        Args:
            cookie_str: Twitter authentication cookie string (auth_token=...; ct0=...)
            
        Returns:
            bool: True if account was added successfully, False otherwise
        """
        try:
            # Parse cookie string to extract auth_token and ct0
            auth_token = None
            ct0 = None
            
            for part in cookie_str.split(';'):
                part = part.strip()
                if part.startswith('auth_token='):
                    auth_token = part.split('=', 1)[1]
                elif part.startswith('ct0='):
                    ct0 = part.split('=', 1)[1]
            
            if not auth_token or not ct0:
                self.logger.error("Invalid cookie format. Must contain auth_token and ct0.")
                return False
            
            # Create a new accounts pool
            pool = AccountsPool(self.accounts_db)
            
            # Add account using cookies
            await pool.add_account_from_cookies(
                username="twitter_user",  # Placeholder, will be updated after login
                auth_token=auth_token,
                ct0=ct0
            )
            
            # Load accounts into API
            await self.api.pool.load_from_db(self.accounts_db)
            
            self.logger.info("Account added successfully from cookies")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding account from cookie: {str(e)}")
            return False
    
    async def get_user_communities(self, user_id_or_handle: str) -> Optional[TwitterUserCommunityPayload]:
        """
        Get communities for a Twitter user using twscrape
        
        Args:
            user_id_or_handle: Twitter user ID or handle
            
        Returns:
            TwitterUserCommunityPayload object or None if error
        """
        try:
            # Check if we have any accounts in the pool
            if not await self.api.pool.get_accounts():
                self.logger.error("No Twitter accounts available. Please add an account using cookies.")
                return None
            
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
            
            # Get user communities using GraphQL
            # This is a direct GraphQL query to the UserCommunities endpoint
            variables = {
                "userId": user.id_str,
                "count": 100,  # Fetch up to 100 communities
                "includePromotedContent": False
            }
            
            # Execute GraphQL query for UserCommunities
            result = await self.api.raw_request(
                "UserCommunities",
                variables
            )
            
            if not result or "data" not in result:
                self.logger.error(f"Failed to get communities for user {user_id_or_handle}")
                return None
            
            # Parse communities from response
            communities_data = result.get("data", {}).get("user", {}).get("communities", {}).get("edges", [])
            
            communities = []
            for edge in communities_data:
                node = edge.get("node", {})
                community_id = node.get("rest_id")
                community_name = node.get("name", "Unknown")
                
                # Determine role (Admin or Member)
                role = "Member"
                if node.get("role") == "Admin" or node.get("is_admin", False):
                    role = "Admin"
                
                communities.append(Community(
                    id=community_id,
                    name=community_name,
                    role=role
                ))
            
            # Create payload
            return TwitterUserCommunityPayload(
                user_id=user.id_str,
                screen_name=user.screen_name,
                name=user.name,
                profile_image_url_https=user.profile_image_url_https,
                is_blue_verified=user.is_blue_verified,
                verified=user.verified,
                communities=communities
            )
            
        except Exception as e:
            self.logger.error(f"Error getting communities for user {user_id_or_handle}: {str(e)}")
            
            # Check for specific error types
            error_str = str(e).lower()
            if "unauthorized" in error_str or "401" in error_str:
                raise ValueError("Target account is private/protected")
            elif "cookie" in error_str or "auth" in error_str:
                raise ValueError("Authentication cookie expired or invalid")
            
            raise
    
    def diff_communities(self, old_communities: List[Community], new_communities: List[Community]) -> Tuple[List[str], List[str], List[str]]:
        """
        Compare old and new community lists to find joined, left, and created communities
        
        Args:
            old_communities: List of previously saved communities
            new_communities: List of newly fetched communities
            
        Returns:
            Tuple of (joined_ids, left_ids, created_ids)
        """
        new_ids = {c.id for c in new_communities}
        old_ids = {c.id for c in old_communities}
        
        joined_ids = new_ids - old_ids
        left_ids = old_ids - new_ids
        created_ids = {c.id for c in new_communities if c.role == "Admin" and c.id in joined_ids}
        
        return list(joined_ids), list(left_ids), list(created_ids)
