#!/usr/bin/env python3
"""
Community Detection Module

Core methods for detecting Twitter community memberships through various strategies:
- URL extraction from tweets
- Profile analysis
- Direct API calls
- Social graph analysis
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Set
from twscrape import API
from bot.models import Community
from bot.cookie_manager import CookieManager


class CommunityDetector:
    """Core community detection functionality"""
    
    def __init__(self, api: API, cookie_manager: CookieManager):
        self.api = api
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
    
    async def get_communities_from_urls(self, user_id: int, max_tweets: int = 10) -> List[Community]:
        """
        Get communities by extracting Community URLs from user's recent tweets
        This is currently the most reliable method
        
        Args:
            user_id: Twitter user ID
            max_tweets: Maximum number of recent tweets to scan (default: 10)
        """
        communities = []
        
        try:
            # Get recent tweets to scan for community URLs (limited to 10 for efficiency)
            tweets = []
            tweet_count = 0
            async for tweet in self.api.user_tweets(user_id, limit=max_tweets):
                tweets.append(tweet)
                tweet_count += 1
                if tweet_count >= max_tweets:
                    break
            
            if not tweets:
                self.logger.info("No tweets found to scan for community URLs")
                return communities
            
            self.logger.info(f"🔍 Scanning {len(tweets)} recent tweets for Twitter Community URLs")
            
            # Extract community IDs from URLs
            community_ids = set()
            for tweet in tweets:
                try:
                    # Get tweet content
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    
                    # Look for Twitter Community URLs
                    url_patterns = [
                        r'(?:twitter\.com|x\.com)/i/communities/(\d+)',
                        r'/communities/(\d+)',
                        r'communities/(\d+)'
                    ]
                    
                    for pattern in url_patterns:
                        matches = re.findall(pattern, tweet_text)
                        for community_id in matches:
                            if community_id.isdigit() and len(community_id) >= 15:
                                community_ids.add(community_id)
                                self.logger.info(f"✅ Found community ID: {community_id}")
                    
                    # Also check URLs in tweet entities
                    if hasattr(tweet, 'urls') and tweet.urls:
                        for url_entity in tweet.urls:
                            expanded_url = getattr(url_entity, 'expanded_url', '') or getattr(url_entity, 'url', '')
                            
                            if expanded_url:
                                self.logger.debug(f"Checking URL: {expanded_url}")
                            
                            for pattern in url_patterns:
                                matches = re.findall(pattern, expanded_url)
                                for community_id in matches:
                                    if community_id.isdigit() and len(community_id) >= 15:
                                        community_ids.add(community_id)
                                        self.logger.info(f"✅ Found community ID in URL entity: {community_id}")
                    
                    # Also check for any t.co URLs and try to expand them manually
                    tco_pattern = r'https?://t\.co/\w+'
                    tco_matches = re.findall(tco_pattern, tweet_text)
                    for tco_url in tco_matches:
                        try:
                            self.logger.debug(f"Found t.co URL: {tco_url} (expansion not implemented)")
                        except Exception as e:
                            self.logger.debug(f"Error processing t.co URL: {e}")
                
                except Exception as e:
                    self.logger.debug(f"Error processing tweet for community URLs: {e}")
                    continue
            
            # Now fetch details for each found community ID
            if community_ids:
                self.logger.info(f"📋 Processing {len(community_ids)} unique community IDs")
                
                for community_id in community_ids:
                    try:
                        community = await self.create_community_from_id(community_id, user_id)
                        if community:
                            communities.append(community)
                            self.logger.info(f"✅ Added community: {community.name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to create community from ID {community_id}: {e}")
            else:
                self.logger.info("No valid community URLs found in recent tweets")
        
        except Exception as e:
            self.logger.error(f"Error extracting communities from URLs: {e}")
        
        return communities
    
    async def get_communities_from_profile(self, user) -> List[Community]:
        """
        Extract community information from user's profile
        Looks for community links in bio, pinned tweets, etc.
        """
        communities = []
        
        try:
            # Check user description/bio
            description = getattr(user, 'description', '') or ''
            if description:
                community_ids = self.extract_community_ids_from_text(description)
                for community_id in community_ids:
                    try:
                        community = await self.create_community_from_id(community_id, user.id)
                        if community:
                            communities.append(community)
                    except Exception as e:
                        self.logger.debug(f"Error creating community from profile ID {community_id}: {e}")
            
            # TODO: Check pinned tweets, profile links, etc.
            
        except Exception as e:
            self.logger.debug(f"Error extracting communities from profile: {e}")
        
        return communities
    
    def extract_community_ids_from_text(self, text: str) -> List[str]:
        """Extract community IDs from any text content"""
        community_ids = []
        
        # Patterns for Twitter Community URLs
        patterns = [
            r'(?:twitter\.com|x\.com)/i/communities/(\d+)',
            r'/communities/(\d+)',
            r'communities/(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match.isdigit() and len(match) >= 15:
                    community_ids.append(match)
        
        return community_ids
    
    async def create_community_from_id(self, community_id: str, user_id: int) -> Optional[Community]:
        """
        Create a Community object from a community ID with intelligent name resolution
        """
        try:
            # Known community mappings for better names
            known_communities = {
                '1493446837214187523': 'Build in Public',
                # Add more as we discover them
            }
            
            # Get community name
            if community_id in known_communities:
                community_name = known_communities[community_id]
            else:
                # Try to fetch community name from Twitter (placeholder for future implementation)
                community_name = await self.fetch_community_name_from_twitter(community_id)
                if not community_name:
                    community_name = f"Community {community_id[:8]}..."
            
            # Determine user's role in the community
            role = await self.determine_user_role_in_community(community_id, user_id)
            
            community = Community(
                id=community_id,
                name=community_name,
                description="",
                member_count=0,
                is_nsfw=False,
                theme="",
                created_at=None,
                admin_id="",
                role=role,
                joined_at=None
            )
            
            return community
            
        except Exception as e:
            self.logger.error(f"Error creating community from ID {community_id}: {e}")
            return None
    
    async def fetch_community_name_from_twitter(self, community_id: str) -> Optional[str]:
        """
        Try to fetch actual community name from Twitter API (future implementation)
        """
        try:
            # This would make a GraphQL request to get community details
            # For now, return None to use placeholder names
            self.logger.debug(f"Community name lookup not implemented for ID: {community_id}")
            return None
            
        except Exception as e:
            self.logger.debug(f"Error fetching community name for {community_id}: {e}")
            return None
    
    async def determine_user_role_in_community(self, community_id: str, user_id: int) -> str:
        """
        Determine user's role in a community
        """
        try:
            # This would require additional API calls to determine the actual role
            # For now, we'll default to "Member"
            # 
            # Future implementation could:
            # 1. Check if user is community admin/moderator
            # 2. Check creation date vs join date
            # 3. Analyze posting patterns in community
            
            return "Member"
            
        except Exception as e:
            self.logger.debug(f"Error determining role for community {community_id}: {e}")
            return "Member"
    
    async def get_communities_direct_api(self, user_id: int) -> List[Community]:
        """
        Try to get current communities using Twitter's API endpoints
        This is a placeholder for future direct API implementation
        """
        communities = []
        self.logger.info(f"🔗 Attempting direct API community lookup for user {user_id}")
        
        try:
            # This would be the ideal method using Twitter's GraphQL
            # For now, we'll implement it as a fallback to URL extraction
            self.logger.debug("Direct API method not yet implemented, using URL extraction")
            
        except Exception as e:
            self.logger.debug(f"Direct API method failed: {e}")
        
        return communities
    
    async def detect_via_social_graph(self, user_id: int) -> List[Community]:
        """
        Detect communities by analyzing user's social connections
        """
        communities = []
        
        try:
            self.logger.info(f"🔍 Analyzing social graph for community indicators for user {user_id}")
            
            # Analyze following list for community accounts
            following_communities = await self.analyze_following_for_communities(user_id, limit=500)
            communities.extend(following_communities)
            
            # Analyze followers for community indicators  
            follower_communities = await self.analyze_followers_for_communities(user_id, limit=200)
            # Remove duplicates
            existing_ids = {c.id for c in communities}
            new_communities = [c for c in follower_communities if c.id not in existing_ids]
            communities.extend(new_communities)
            
            self.logger.info(f"📊 Social graph analysis found {len(communities)} community indicators")
            
        except Exception as e:
            self.logger.error(f"Error in social graph analysis: {e}")
        
        return communities
    
    async def analyze_following_for_communities(self, user_id: int, limit: int = 500) -> List[Community]:
        """
        Analyze who the user follows to identify community accounts
        """
        communities = []
        
        try:
            following_count = 0
            community_accounts = []
            
            async for user in self.api.following(user_id, limit=limit):
                following_count += 1
                
                # Check if this is a community account
                if self.is_community_account(user):
                    community_accounts.append(user)
                
                if following_count >= limit:
                    break
            
            self.logger.info(f"📋 Analyzed {following_count} following accounts, found {len(community_accounts)} community accounts")
            
            # Create community objects from community accounts
            for account in community_accounts:
                try:
                    community = Community(
                        id=f"following_{account.id}",
                        name=account.displayname or account.username,
                        description=getattr(account, 'description', '') or '',
                        member_count=getattr(account, 'followersCount', 0),
                        is_nsfw=False,
                        theme="following_based",
                        created_at=None,
                        admin_id=str(account.id),
                        role="Member",
                        joined_at=None
                    )
                    communities.append(community)
                    
                except Exception as e:
                    self.logger.debug(f"Error creating community from following account: {e}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing following for communities: {e}")
        
        return communities
    
    async def analyze_followers_for_communities(self, user_id: int, limit: int = 200) -> List[Community]:
        """
        Analyze user's followers to identify community connections
        """
        communities = []
        
        try:
            follower_count = 0
            community_indicators = []
            
            async for follower in self.api.followers(user_id, limit=limit):
                follower_count += 1
                
                # Check for community indicators in follower profiles
                if self.has_community_indicators(follower):
                    community_indicators.append(follower)
                
                if follower_count >= limit:
                    break
            
            self.logger.info(f"📋 Analyzed {follower_count} followers, found {len(community_indicators)} with community indicators")
            
            # Extract community information from indicators
            for indicator in community_indicators:
                try:
                    # Extract community info from bio, username, etc.
                    extracted_communities = self.extract_communities_from_user(indicator)
                    communities.extend(extracted_communities)
                    
                except Exception as e:
                    self.logger.debug(f"Error extracting communities from follower: {e}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing followers for communities: {e}")
        
        return communities
    
    def is_community_account(self, user) -> bool:
        """
        Determine if a user account represents a community
        """
        try:
            username = user.username.lower()
            display_name = (user.displayname or '').lower()
            description = getattr(user, 'description', '') or ''
            
            # Community account indicators
            community_keywords = [
                'community', 'dao', 'collective', 'group', 'club', 'society',
                'organization', 'network', 'alliance', 'guild', 'team'
            ]
            
            # Check username and display name
            for keyword in community_keywords:
                if keyword in username or keyword in display_name:
                    return True
            
            # Check description for community indicators
            if any(keyword in description.lower() for keyword in community_keywords):
                return True
            
            # Check for community-style account patterns
            if user.username.endswith('dao') or user.username.endswith('community'):
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error checking if account is community: {e}")
            return False
    
    def has_community_indicators(self, user) -> bool:
        """
        Check if a user has indicators of community involvement
        """
        try:
            description = getattr(user, 'description', '') or ''
            
            # Look for community-related keywords in bio
            community_indicators = [
                'member of', 'part of', 'community', 'dao member',
                'contributor', 'builder', 'founder', 'moderator'
            ]
            
            return any(indicator in description.lower() for indicator in community_indicators)
            
        except Exception as e:
            self.logger.debug(f"Error checking community indicators: {e}")
            return False
    
    def extract_communities_from_user(self, user) -> List[Community]:
        """
        Extract community information from a user's profile
        """
        communities = []
        
        try:
            description = getattr(user, 'description', '') or ''
            
            # Extract community IDs from description
            community_ids = self.extract_community_ids_from_text(description)
            
            # Create basic community objects
            for community_id in community_ids:
                community = Community(
                    id=community_id,
                    name=f"Community {community_id[:8]}...",
                    description="",
                    member_count=0,
                    is_nsfw=False,
                    theme="follower_based",
                    created_at=None,
                    admin_id="",
                    role="Member",
                    joined_at=None
                )
                communities.append(community)
        
        except Exception as e:
            self.logger.debug(f"Error extracting communities from user: {e}")
        
        return communities
    
    async def get_communities_from_tweet_objects(self, user_id: int, max_tweets: int = 10) -> List[Community]:
        """
        Extract community information directly from tweet objects (most reliable method)
        
        Each tweet object contains community metadata if posted to a community:
        - tweet.community.id
        - tweet.community.name  
        - tweet.community.description
        - etc.
        
        Args:
            user_id: Twitter user ID
            max_tweets: Maximum number of tweets to analyze
            
        Returns:
            List of Community objects
        """
        communities = []
        
        try:
            self.logger.info(f"🔍 Analyzing tweet objects for direct community metadata")
            
            tweet_count = 0
            async for tweet in self.api.user_tweets(user_id, limit=max_tweets):
                tweet_count += 1
                
                # DEBUG: Log tweet structure to understand what's available
                self.logger.info(f"📊 Tweet {tweet_count} analysis:")
                self.logger.info(f"   Tweet ID: {getattr(tweet, 'id', 'N/A')}")
                self.logger.info(f"   Tweet content: {getattr(tweet, 'rawContent', 'N/A')[:100]}...")
                
                # Debug: Log all available attributes
                available_attrs = [attr for attr in dir(tweet) if not attr.startswith('_')]
                self.logger.info(f"   Available attributes: {available_attrs}")
                
                # Check for various community-related fields
                community_fields = ['community', 'communities', 'communityResults', 'socialContext']
                for field in community_fields:
                    if hasattr(tweet, field):
                        field_value = getattr(tweet, field)
                        self.logger.info(f"   Found field '{field}': {field_value}")
                
                # Check if tweet has community metadata
                if hasattr(tweet, 'community') and tweet.community:
                    try:
                        self.logger.info(f"🎯 Found community metadata: {tweet.community}")
                        community = Community(
                            id=str(tweet.community.id),
                            name=tweet.community.name,
                            description=getattr(tweet.community, 'description', ''),
                            member_count=getattr(tweet.community, 'member_count', 0),
                            is_nsfw=getattr(tweet.community, 'is_nsfw', False),
                            theme=getattr(tweet.community, 'theme', 'unknown'),
                            created_at=getattr(tweet.community, 'created_at', None),
                            admin_id=getattr(tweet.community, 'admin_id', ''),
                            role="Member",  # Default role
                            joined_at=None
                        )
                        
                        # Avoid duplicates
                        if not any(c.id == community.id for c in communities):
                            communities.append(community)
                            self.logger.info(f"🎯 Found community from tweet metadata: {community.name} (ID: {community.id})")
                    
                    except Exception as e:
                        self.logger.error(f"Error processing community metadata: {e}")
                
                # Also check tweet text for community links as backup
                if hasattr(tweet, 'rawContent') and tweet.rawContent:
                    community_urls = re.findall(r'https://(?:twitter\.com|x\.com)/i/communities/(\d+)', tweet.rawContent)
                    for community_id in community_urls:
                        # Create community object from URL
                        if not any(c.id == community_id for c in communities):
                            community = Community(
                                id=community_id,
                                name=f"Community {community_id[:8]}...",
                                description="",
                                member_count=0,
                                is_nsfw=False,
                                theme="url_detected",
                                created_at=None,
                                admin_id="",
                                role="Member",
                                joined_at=None
                            )
                            communities.append(community)
                            self.logger.info(f"🔗 Found community from URL: {community.name} (ID: {community.id})")
                
                # DEBUG: Let's also check if there's any mention of "Build in Public" or similar
                content = getattr(tweet, 'rawContent', '') or ''
                if any(keyword in content.lower() for keyword in ['build in public', 'community', '1493446837214187523']):
                    self.logger.info(f"🔍 Found potential community reference in tweet: {content[:200]}...")
                
                if tweet_count >= max_tweets:
                    break
            
            self.logger.info(f"📊 Direct API community detection found {len(communities)} communities from {tweet_count} tweets")
            return communities
            
        except Exception as e:
            self.logger.error(f"Error in direct community detection: {e}")
            return [] 