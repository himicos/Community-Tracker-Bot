import os
import logging
import asyncio
from datetime import datetime
from apify_client import ApifyClient
import httpx
from typing import Dict, List, Optional, Tuple, Any

from bot.models import Community, TwitterUserCommunityPayload

class ApifyIntegration:
    """Class for interacting with the Apify API"""
    
    def __init__(self, api_token: str, actor_slug: str = None):
        self.client = ApifyClient(api_token)
        self.actor_slug = actor_slug or os.getenv("APIFY_ACTOR_SLUG", "gbDitRqKnWjNm73ba")
        self.logger = logging.getLogger(__name__)
    
    async def get_user_communities(self, user_id: str, auth_cookie: str, max_retries: int = 3) -> Optional[TwitterUserCommunityPayload]:
        """
        Get communities for a Twitter user using Apify actor
        
        Args:
            user_id: Twitter user ID or handle
            auth_cookie: Twitter authentication cookie
            max_retries: Maximum number of retries on failure
            
        Returns:
            TwitterUserCommunityPayload object or None if error
        """
        retries = 0
        while retries < max_retries:
            try:
                self.logger.info(f"Fetching communities for user {user_id} (attempt {retries + 1}/{max_retries})")
                
                # Prepare the Actor input
                run_input = {
                    "userId": user_id if user_id.isdigit() else None,
                    "screenName": None if user_id.isdigit() else user_id.lstrip('@'),
                    "authCookie": auth_cookie,
                    "proxy": "auto"
                }
                
                # Run the Actor and wait for it to finish
                run = self.client.actor(self.actor_slug).call(run_input=run_input)
                
                # Check if run was successful
                if run["status"] != "SUCCEEDED":
                    self.logger.error(f"Apify run failed with status: {run['status']}")
                    if "401" in str(run.get("errorMessage", "")):
                        raise ValueError("Target account is private/protected")
                    if "cookie" in str(run.get("errorMessage", "")).lower():
                        raise ValueError("Authentication cookie expired or invalid")
                    raise RuntimeError(f"Apify run failed: {run.get('errorMessage', 'Unknown error')}")
                
                # Fetch Actor results from the run's dataset
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                
                if not items:
                    self.logger.warning("No communities found in Apify response")
                    return TwitterUserCommunityPayload(
                        user_id=user_id,
                        screen_name=user_id,
                        communities=[]
                    )
                    
                # Process the first item
                item = items[0]
                
                # Map to our model
                communities = [
                    Community(
                        id=community.get("id", ""),
                        name=community.get("name", "Unknown"),
                        role="Admin" if community.get("role", "").lower() == "admin" else "Member"
                    )
                    for community in item.get("communities", [])
                ]
                
                return TwitterUserCommunityPayload(
                    user_id=item.get("user_id", ""),
                    screen_name=item.get("screen_name", ""),
                    name=item.get("name", ""),
                    profile_image_url_https=item.get("profile_image_url_https", ""),
                    is_blue_verified=item.get("is_blue_verified", False),
                    verified=item.get("verified", False),
                    communities=communities
                )
                
            except ValueError as e:
                # Don't retry for validation errors
                self.logger.error(f"Validation error: {str(e)}")
                raise
                
            except Exception as e:
                self.logger.error(f"Error fetching communities (attempt {retries + 1}/{max_retries}): {str(e)}")
                retries += 1
                if retries < max_retries:
                    # Exponential backoff
                    await asyncio.sleep(2 ** retries)
                else:
                    self.logger.error(f"Max retries reached, giving up")
                    raise
        
        return None
    
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
    
    async def validate_twitter_user(self, user_id_or_handle: str, auth_cookie: str) -> Dict[str, Any]:
        """
        Validate a Twitter user ID or handle
        
        Args:
            user_id_or_handle: Twitter user ID or handle
            auth_cookie: Twitter authentication cookie
            
        Returns:
            Dictionary with user information
        """
        try:
            # For production, this would use Twitter's API to validate the user
            # For this MVP, we'll use the Apify actor to get user info
            
            # Extract auth_token and ct0 from cookie string
            auth_token = None
            ct0 = None
            
            for part in auth_cookie.split(';'):
                part = part.strip()
                if part.startswith('auth_token='):
                    auth_token = part.split('=', 1)[1]
                elif part.startswith('ct0='):
                    ct0 = part.split('=', 1)[1]
            
            if not auth_token or not ct0:
                raise ValueError("Invalid cookie format. Must contain auth_token and ct0.")
            
            # Prepare headers
            headers = {
                'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                'cookie': auth_cookie,
                'x-csrf-token': ct0,
                'x-twitter-active-user': 'yes',
                'x-twitter-auth-type': 'OAuth2Session',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Determine endpoint based on input type
            if user_id_or_handle.isdigit():
                url = f"https://api.twitter.com/1.1/users/show.json?user_id={user_id_or_handle}"
            else:
                screen_name = user_id_or_handle.lstrip('@')
                url = f"https://api.twitter.com/1.1/users/show.json?screen_name={screen_name}"
            
            # Make request
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        'user_id': user_data.get('id_str'),
                        'screen_name': user_data.get('screen_name'),
                        'name': user_data.get('name'),
                        'profile_image_url_https': user_data.get('profile_image_url_https'),
                        'verified': user_data.get('verified', False),
                        'is_blue_verified': user_data.get('verified', False)  # Twitter API doesn't expose blue verification separately
                    }
                elif response.status_code == 401:
                    raise ValueError("Target account is private/protected")
                else:
                    raise RuntimeError(f"Twitter API error: {response.status_code} - {response.text}")
                
        except httpx.RequestError as e:
            self.logger.error(f"Error validating Twitter user: {str(e)}")
            raise RuntimeError(f"Network error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error validating Twitter user: {str(e)}")
            raise
