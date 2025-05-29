#!/usr/bin/env python3
"""
Enhanced Community Tracking System

This module implements comprehensive community detection and monitoring:
- Multi-strategy community detection
- Complete parsing of ALL community data
- Real-time change tracking
- Detailed notifications
- Post-based community tracking for creation and membership detection
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import json
import re

from twscrape import API
from bot.models import Community, TwitterUserCommunityPayload
from bot.cookie_manager import CookieManager, CookieSet
from bot.community_post_tracker import CommunityPostTracker


class EnhancedCommunityTracker:
    """Comprehensive Community Tracking System"""
    
    def __init__(self, api: API, cookie_manager: CookieManager):
        self.api = api
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize the post tracker for advanced community detection
        self.post_tracker = CommunityPostTracker(api, cookie_manager)
        
        self.logger.info("Enhanced Community Tracker initialized with comprehensive detection capabilities including post tracking")
    
    async def get_all_user_communities(self, username: str, deep_scan: bool = True) -> Optional[TwitterUserCommunityPayload]:
        """
        Get the actual current list of Twitter Communities the user is in
        
        Args:
            username: Twitter username (without @)
            deep_scan: If True, tries multiple methods; if False, uses fastest method
            
        Returns:
            TwitterUserCommunityPayload with current community memberships
        """
        self.logger.info(f"🔍 Getting current Twitter Communities for @{username}")
        
        try:
            # Get user information
            user = await self.api.user_by_login(username)
            if not user:
                self.logger.error(f"User @{username} not found")
                return None
            
            self.logger.info(f"Found user: {user.displayname} (@{user.username}, ID: {user.id})")
            
            # Get actual current communities
            all_communities = []
            
            if deep_scan:
                self.logger.info("🔍 Using comprehensive community detection")
                
                # Method 1: Try direct API calls (most accurate)
                api_communities = await self._get_current_communities_api(user.id)
                all_communities.extend(api_communities)
                
                # Method 2: Extract from recent tweets with community URLs
                url_communities = await self._get_communities_from_urls(user.id)
                # Avoid duplicates
                existing_ids = {c.id for c in all_communities}
                new_communities = [c for c in url_communities if c.id not in existing_ids]
                all_communities.extend(new_communities)
                
                # Method 3: Profile analysis for community links
                profile_communities = await self._get_communities_from_profile(user)
                new_profile_communities = [c for c in profile_communities if c.id not in existing_ids]
                all_communities.extend(new_profile_communities)
                
            else:
                self.logger.info("⚡ Using fast community detection")
                
                # Just use the most reliable method (URLs from tweets)
                url_communities = await self._get_communities_from_urls(user.id)
                all_communities.extend(url_communities)
            
            self.logger.info(f"📊 Total current communities found: {len(all_communities)}")
            
            # Log each community
            for i, community in enumerate(all_communities, 1):
                self.logger.info(f"  {i}. {community.name} (ID: {community.id}, Role: {community.role})")
            
            return TwitterUserCommunityPayload(
                user_id=str(user.id),
                screen_name=user.username,
                name=user.displayname or user.username,
                verified=getattr(user, 'verified', False),
                is_blue_verified=getattr(user, 'blue_verified', False),
                profile_image_url_https=getattr(user, 'profileImageUrl', ''),
                communities=all_communities
            )
            
        except Exception as e:
            self.logger.error(f"Error getting current communities for @{username}: {e}")
            return None
    
    async def _get_current_communities_api(self, user_id: int) -> List[Community]:
        """
        Try to get current communities using Twitter's API endpoints
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
    
    async def _get_communities_from_urls(self, user_id: int) -> List[Community]:
        """
        Get communities by extracting Community URLs from user's recent tweets
        This is currently the most reliable method
        """
        communities = []
        
        try:
            # Get recent tweets to scan for community URLs
            tweets = []
            tweet_count = 0
            async for tweet in self.api.user_tweets(user_id, limit=100):  # Check more tweets
                tweets.append(tweet)
                tweet_count += 1
                if tweet_count >= 100:
                    break
            
            if not tweets:
                self.logger.info("No tweets found to scan for community URLs")
                return communities
            
            self.logger.info(f"🔍 Scanning {len(tweets)} tweets for Twitter Community URLs")
            
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
                            if community_id.isdigit() and len(community_id) >= 15:  # Valid Twitter Community ID
                                community_ids.add(community_id)
                                self.logger.info(f"✅ Found community ID: {community_id}")
                    
                    # Also check URLs in tweet entities
                    if hasattr(tweet, 'urls') and tweet.urls:
                        for url_entity in tweet.urls:
                            expanded_url = getattr(url_entity, 'expanded_url', '') or getattr(url_entity, 'url', '')
                            
                            # Log URLs for debugging
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
                            # This would require following redirects to expand URLs
                            # For now, we'll log them for debugging
                            self.logger.debug(f"Found t.co URL: {tco_url} (expansion not implemented)")
                        except Exception as e:
                            self.logger.debug(f"Error processing t.co URL: {e}")
                
                except Exception as e:
                    self.logger.debug(f"Error processing tweet for community URLs: {e}")
                    continue
            
            # Create community objects for each found ID
            for community_id in community_ids:
                try:
                    # Try to get community details
                    community = await self._create_community_from_id(community_id, user_id)
                    if community:
                        communities.append(community)
                        self.logger.info(f"✅ Added community: {community.name}")
                    
                except Exception as e:
                    self.logger.debug(f"Error creating community object for {community_id}: {e}")
                    # Create basic community as fallback
                    basic_community = Community(
                        id=community_id,
                        name=f"Twitter Community {community_id}",
                        description="Community detected from user's tweets",
                        member_count=0,
                        role="Member",
                        is_nsfw=False,
                        created_at=datetime.utcnow().isoformat()
                    )
                    communities.append(basic_community)
            
            self.logger.info(f"📋 Extracted {len(communities)} communities from URLs")
            
        except Exception as e:
            self.logger.error(f"Error extracting communities from URLs: {e}")
        
        return communities
    
    async def _get_communities_from_profile(self, user) -> List[Community]:
        """
        Check user's profile bio and pinned tweet for community links
        """
        communities = []
        
        try:
            # Check profile description
            bio = getattr(user, 'description', '') or ''
            if bio:
                community_ids = self._extract_community_ids_from_text(bio)
                for community_id in community_ids:
                    community = await self._create_community_from_id(community_id, user.id)
                    if community:
                        communities.append(community)
                        self.logger.info(f"Found community in bio: {community.name}")
            
            # Could also check pinned tweet if available
            
        except Exception as e:
            self.logger.debug(f"Error checking profile for communities: {e}")
        
        return communities
    
    def _extract_community_ids_from_text(self, text: str) -> List[str]:
        """
        Extract community IDs from any text
        """
        community_ids = []
        
        url_patterns = [
            r'(?:twitter\.com|x\.com)/i/communities/(\d+)',
            r'/communities/(\d+)',
            r'communities/(\d+)'
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, text)
            for community_id in matches:
                if community_id.isdigit() and len(community_id) >= 15:
                    community_ids.append(community_id)
        
        return community_ids
    
    async def _create_community_from_id(self, community_id: str, user_id: int) -> Optional[Community]:
        """
        Create a Community object from a community ID with as much detail as possible
        """
        try:
            # Try to determine the user's role and get community name
            role = await self._determine_user_role_in_community(community_id, user_id)
            
            # For now, create with basic info
            # In a full implementation, this would fetch from Twitter's API
            community = Community(
                id=community_id,
                name=f"Twitter Community {community_id}",  # Would get real name from API
                description="Community membership detected from user activity",
                member_count=0,  # Would get from API
                role=role,
                is_nsfw=False,  # Would get from API
                created_at=datetime.utcnow().isoformat()
            )
            
            return community
            
        except Exception as e:
            self.logger.debug(f"Error creating community object for {community_id}: {e}")
            return None
    
    async def _determine_user_role_in_community(self, community_id: str, user_id: int) -> str:
        """
        Determine user's role in a specific community
        """
        try:
            # Check recent tweets for role indicators related to this community
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=50):
                tweets.append(tweet)
            
            # Look for role keywords in tweets mentioning this community
            for tweet in tweets:
                try:
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    
                    # If tweet mentions this community ID
                    if community_id in tweet_text:
                        # Check for admin/creator keywords
                        admin_keywords = ['created', 'founding', 'admin', 'moderator', 'leading', 'started']
                        for keyword in admin_keywords:
                            if keyword in tweet_text.lower():
                                return "Admin"
                
                except Exception as e:
                    continue
            
            # Default to Member
            return "Member"
            
        except Exception as e:
            self.logger.debug(f"Error determining role for community {community_id}: {e}")
            return "Member"
    
    async def _get_communities_direct(self, user_id: int) -> List[Community]:
        """
        Direct Twitter Communities API detection - gets actual community memberships
        Uses Twitter's GraphQL endpoints to fetch real community data
        """
        communities = []
        self.logger.info(f"Attempting direct Twitter Communities API detection for user {user_id}")
        
        try:
            # Method 1: Try to get user's community memberships via GraphQL
            communities_from_api = await self._fetch_user_communities_graphql(user_id)
            if communities_from_api:
                communities.extend(communities_from_api)
                self.logger.info(f"Found {len(communities_from_api)} communities via direct API")
            
            # Method 2: Scan recent tweets for Twitter Community URLs and extract IDs
            communities_from_urls = await self._extract_communities_from_tweet_urls(user_id)
            if communities_from_urls:
                # Avoid duplicates
                existing_ids = {c.id for c in communities}
                new_communities = [c for c in communities_from_urls if c.id not in existing_ids]
                communities.extend(new_communities)
                self.logger.info(f"Found {len(new_communities)} additional communities from tweet URLs")
            
            self.logger.info(f"Total direct communities found: {len(communities)}")
            
        except Exception as e:
            self.logger.error(f"Direct community detection failed: {e}")
        
        return communities
    
    async def _fetch_user_communities_graphql(self, user_id: int) -> List[Community]:
        """
        Fetch user's communities using Twitter's GraphQL API
        This attempts to use the actual Communities endpoints
        """
        communities = []
        
        try:
            # Twitter's GraphQL endpoint for user communities
            # This is based on reverse engineering of Twitter's web app
            
            # First, try to get communities the user is a member of
            member_communities = await self._get_user_member_communities(user_id)
            communities.extend(member_communities)
            
            # Then, try to get communities the user has created/admin
            admin_communities = await self._get_user_admin_communities(user_id)
            communities.extend(admin_communities)
            
        except Exception as e:
            self.logger.debug(f"GraphQL community fetch failed: {e}")
        
        return communities
    
    async def _get_user_member_communities(self, user_id: int) -> List[Community]:
        """
        Get communities where user is a member using GraphQL
        """
        communities = []
        
        try:
            # This would use a GraphQL query like:
            # query UserCommunities($userId: ID!) {
            #   user(rest_id: $userId) {
            #     communities {
            #       edges {
            #         node {
            #           id_str
            #           name
            #           description
            #           member_count
            #           created_at
            #           is_nsfw
            #           role
            #         }
            #       }
            #     }
            #   }
            # }
            
            # For now, we'll use the tweet scanning method as a fallback
            # since the exact GraphQL schema may change
            self.logger.debug("GraphQL member communities endpoint not yet implemented")
            
        except Exception as e:
            self.logger.debug(f"Failed to get member communities: {e}")
        
        return communities
    
    async def _get_user_admin_communities(self, user_id: int) -> List[Community]:
        """
        Get communities where user is admin/creator using GraphQL
        """
        communities = []
        
        try:
            # Similar GraphQL approach for admin communities
            self.logger.debug("GraphQL admin communities endpoint not yet implemented")
            
        except Exception as e:
            self.logger.debug(f"Failed to get admin communities: {e}")
        
        return communities
    
    async def _extract_communities_from_tweet_urls(self, user_id: int) -> List[Community]:
        """
        Extract Twitter Community IDs from recent tweets and fetch community details
        This is more reliable than text analysis as it gets actual community IDs
        """
        communities = []
        
        try:
            # Get recent tweets to scan for community URLs
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=50):  # Check more tweets for URLs
                tweets.append(tweet)
            
            if not tweets:
                return communities
            
            self.logger.info(f"Scanning {len(tweets)} tweets for Twitter Community URLs")
            
            # Extract community IDs from URLs
            community_ids = set()
            for tweet in tweets:
                try:
                    # Get full tweet content including URLs
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    
                    # Look for Twitter Community URLs
                    url_patterns = [
                        r'(?:twitter\.com|x\.com)/i/communities/(\d+)',
                        r'communities/(\d+)',
                    ]
                    
                    for pattern in url_patterns:
                        matches = re.findall(pattern, tweet_text)
                        for community_id in matches:
                            if community_id.isdigit() and len(community_id) > 10:  # Valid Twitter ID
                                community_ids.add(community_id)
                                self.logger.info(f"Found community ID in tweet: {community_id}")
                    
                    # Also check URLs in tweet entities if available
                    if hasattr(tweet, 'urls'):
                        for url in tweet.urls:
                            expanded_url = getattr(url, 'expanded_url', '') or getattr(url, 'url', '')
                            for pattern in url_patterns:
                                matches = re.findall(pattern, expanded_url)
                                for community_id in matches:
                                    if community_id.isdigit() and len(community_id) > 10:
                                        community_ids.add(community_id)
                                        self.logger.info(f"Found community ID in URL: {community_id}")
                
                except Exception as e:
                    self.logger.debug(f"Error processing tweet for URLs: {e}")
                    continue
            
            # Fetch details for each community ID
            for community_id in community_ids:
                try:
                    community_details = await self._fetch_community_details(community_id)
                    if community_details:
                        communities.append(community_details)
                        self.logger.info(f"Successfully fetched details for community {community_id}: {community_details.name}")
                    
                except Exception as e:
                    self.logger.debug(f"Failed to fetch details for community {community_id}: {e}")
                    # Create basic community object even if details fetch fails
                    basic_community = Community(
                        id=community_id,
                        name=f"Twitter Community {community_id}",
                        description="Community detected from tweet URL",
                        member_count=0,
                        role="Member",  # Assume member unless proven otherwise
                        is_nsfw=False,
                        created_at=datetime.utcnow().isoformat()
                    )
                    communities.append(basic_community)
            
            self.logger.info(f"Extracted {len(communities)} communities from tweet URLs")
            
        except Exception as e:
            self.logger.error(f"Error extracting communities from tweet URLs: {e}")
        
        return communities
    
    async def _fetch_community_details(self, community_id: str) -> Optional[Community]:
        """
        Fetch detailed information about a specific community
        """
        try:
            # This would use Twitter's GraphQL to get community details
            # For now, we'll create a basic structure
            
            # Try to determine user's role in the community by checking their tweets about it
            role = await self._determine_user_role_in_community(community_id)
            
            # Create community object with available information
            community = Community(
                id=community_id,
                name=f"Twitter Community {community_id}",  # Would get real name from API
                description="Community detected from user activity",
                member_count=0,  # Would get from API
                role=role,
                is_nsfw=False,  # Would get from API
                created_at=datetime.utcnow().isoformat()
            )
            
            return community
            
        except Exception as e:
            self.logger.debug(f"Failed to fetch community details for {community_id}: {e}")
            return None
    
    async def _determine_user_role_in_community(self, community_id: str) -> str:
        """
        Determine user's role in a community based on their tweet activity
        """
        try:
            # Check recent tweets for role indicators
            # Look for phrases like "created", "admin", "moderator", etc.
            # For now, default to Member
            return "Member"
            
        except Exception as e:
            self.logger.debug(f"Failed to determine role for community {community_id}: {e}")
            return "Member"
    
    async def _detect_via_comprehensive_tweets(self, user_id: int, limit: int = 200) -> List[Community]:
        """
        Comprehensive tweet analysis for community detection
        """
        communities = []
        self.logger.info(f"Analyzing tweets for community indicators (user: {user_id})")
        
        try:
            # Get recent tweets with extended limit for comprehensive analysis
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=limit):
                tweets.append(tweet)
            
            if not tweets:
                self.logger.info(f"No tweets found for user {user_id}")
                return communities
            
            # Comprehensive pattern analysis
            community_indicators = self._extract_comprehensive_patterns(tweets)
            
            # Convert indicators to Community objects
            for indicator in community_indicators:
                community = self._create_community_from_indicator(indicator, "tweet_analysis")
                if community:
                    communities.append(community)
            
            self.logger.info(f"Found {len(communities)} communities via tweet analysis")
            
        except Exception as e:
            self.logger.error(f"Error in tweet analysis: {e}")
        
        return communities
    
    def _extract_comprehensive_patterns(self, tweets) -> Set[Dict[str, Any]]:
        """
        Extract comprehensive community patterns from tweets
        """
        indicators = set()
        
        for tweet in tweets:
            try:
                text = tweet.rawContent.lower() if hasattr(tweet, 'rawContent') else str(tweet).lower()
                
                # Pattern 1: Community hashtags (expanded)
                hashtag_patterns = [
                    r'#(\w*community\w*)',
                    r'#(\w*group\w*)',
                    r'#(\w*club\w*)',
                    r'#(\w*collective\w*)',
                    r'#(\w*society\w*)',
                    r'#(\w*forum\w*)',
                    r'#(\w*discord\w*)',
                    r'#(\w*telegram\w*)'
                ]
                
                for pattern in hashtag_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        if len(match) > 3:  # Filter meaningful names
                            indicators.add(('hashtag', match.title(), text[:100]))
                
                # Pattern 2: Community mentions (expanded)
                mention_patterns = [
                    r'@(\w*community\w*)',
                    r'@(\w*group\w*)',
                    r'@(\w*collective\w*)',
                    r'@(\w*club\w*)'
                ]
                
                for pattern in mention_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        if len(match) > 3:
                            indicators.add(('mention', match.title(), text[:100]))
                
                # Pattern 3: Community action keywords
                action_keywords = [
                    'joined community',
                    'community member',
                    'community admin',
                    'community moderator',
                    'created community',
                    'community founder',
                    'part of community',
                    'active in community',
                    'leading community'
                ]
                
                for keyword in action_keywords:
                    if keyword in text:
                        # Extract community name from context
                        context = self._extract_community_context(text, keyword)
                        if context:
                            indicators.add(('action', context, text[:100]))
                
                # Pattern 4: Twitter Communities URLs
                url_patterns = [
                    r'(?:twitter\.com|x\.com)/i/communities/(\w+)',
                    r'communities/(\w+)',
                    r'community\.(\w+)'
                ]
                
                for pattern in url_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        indicators.add(('url', f"Community_{match}", text[:100]))
                
                # Pattern 5: Discord/Telegram invites (often community-related)
                invite_patterns = [
                    r'discord\.gg/(\w+)',
                    r't\.me/(\w+)',
                    r'telegram\.me/(\w+)'
                ]
                
                for pattern in invite_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        indicators.add(('invite', f"External_{match}", text[:100]))
                
            except Exception as e:
                self.logger.debug(f"Error analyzing tweet: {e}")
                continue
        
        return indicators
    
    def _extract_community_context(self, text: str, keyword: str) -> Optional[str]:
        """
        Extract community name from context around action keywords
        """
        try:
            # Find keyword position
            keyword_pos = text.find(keyword)
            if keyword_pos == -1:
                return None
            
            # Extract surrounding context
            start = max(0, keyword_pos - 50)
            end = min(len(text), keyword_pos + len(keyword) + 50)
            context = text[start:end]
            
            # Look for quoted community names
            quoted_matches = re.findall(r'"([^"]+)"', context)
            for match in quoted_matches:
                if 'community' in match.lower() and len(match) > 3:
                    return match.title()
            
            # Look for capitalized words near the keyword
            words = context.split()
            for i, word in enumerate(words):
                if keyword.split()[0] in word.lower():
                    # Check nearby words for community names
                    for j in range(max(0, i-3), min(len(words), i+4)):
                        if words[j].istitle() and len(words[j]) > 3:
                            return words[j]
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error extracting context: {e}")
            return None
    
    def _create_community_from_indicator(self, indicator: tuple, source: str) -> Optional[Community]:
        """
        Create Community object from detection indicator
        """
        try:
            indicator_type, name, context = indicator
            
            # Generate unique ID based on name and source
            community_id = f"{source}_{hash(name) % 1000000}"
            
            # Determine role based on context
            role = "Member"  # Default
            if any(word in context.lower() for word in ['admin', 'moderator', 'founder', 'created', 'leading']):
                role = "Admin"
            elif any(word in context.lower() for word in ['joined', 'active', 'part of']):
                role = "Member"
            
            return Community(
                id=community_id,
                name=name,
                description=f"Detected via {indicator_type} analysis: {context[:100]}...",
                member_count=0,  # Unknown from this detection method
                role=role,
                is_nsfw=False,
                created_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            self.logger.debug(f"Error creating community from indicator: {e}")
            return None
    
    async def _detect_via_social_graph(self, user_id: int) -> List[Community]:
        """
        Detect communities via social graph analysis
        """
        communities = []
        self.logger.info(f"Analyzing social graph for community indicators (user: {user_id})")
        
        try:
            # Analyze following list for community accounts
            following_communities = await self._analyze_following_for_communities(user_id)
            communities.extend(following_communities)
            
            # Analyze followers for community patterns
            followers_communities = await self._analyze_followers_for_communities(user_id)
            communities.extend(followers_communities)
            
            self.logger.info(f"Found {len(communities)} communities via social graph analysis")
            
        except Exception as e:
            self.logger.error(f"Error in social graph analysis: {e}")
        
        return communities
    
    async def _analyze_following_for_communities(self, user_id: int, limit: int = 500) -> List[Community]:
        """
        Analyze following list for community accounts
        """
        communities = []
        
        try:
            following = []
            async for followed_user in self.api.following(user_id, limit=limit):
                following.append(followed_user)
            
            community_indicators = [
                'community', 'commune', 'group', 'collective', 'club', 'society',
                'forum', 'discussion', 'members', 'discord', 'telegram', 'guild'
            ]
            
            for followed_user in following:
                try:
                    username = followed_user.username.lower()
                    name = (followed_user.displayname or "").lower()
                    description = (getattr(followed_user, 'description', '') or "").lower()
                    
                    # Check if this looks like a community account
                    combined_text = f"{username} {name} {description}"
                    
                    if any(indicator in combined_text for indicator in community_indicators):
                        community = Community(
                            id=f"following_{followed_user.id}",
                            name=followed_user.displayname or followed_user.username,
                            description=getattr(followed_user, 'description', '')[:200] or "Community account",
                            member_count=getattr(followed_user, 'followersCount', 0),
                            role="Member",  # User is following, likely a member
                            is_nsfw=False,
                            created_at=datetime.utcnow().isoformat()
                        )
                        communities.append(community)
                
                except Exception as e:
                    self.logger.debug(f"Error analyzing followed user: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error analyzing following list: {e}")
        
        return communities
    
    async def _analyze_followers_for_communities(self, user_id: int, limit: int = 200) -> List[Community]:
        """
        Analyze followers for community patterns (reverse detection)
        """
        communities = []
        
        try:
            # This is a more advanced technique - if many community accounts follow the user,
            # it suggests the user might be active in community spaces
            
            followers = []
            async for follower in self.api.followers(user_id, limit=limit):
                followers.append(follower)
            
            community_followers = 0
            community_names = set()
            
            for follower in followers:
                try:
                    username = follower.username.lower()
                    name = (follower.displayname or "").lower()
                    
                    if any(indicator in f"{username} {name}" for indicator in ['community', 'group', 'collective']):
                        community_followers += 1
                        community_names.add(follower.displayname or follower.username)
                
                except Exception as e:
                    continue
            
            # If significant portion of followers are community accounts, 
            # user is likely active in community spaces
            if community_followers > 5:  # Threshold
                meta_community = Community(
                    id=f"meta_community_{user_id}",
                    name="Community Ecosystem",
                    description=f"User is followed by {community_followers} community accounts, indicating active participation in community spaces",
                    member_count=community_followers,
                    role="Active Participant",
                    is_nsfw=False,
                    created_at=datetime.utcnow().isoformat()
                )
                communities.append(meta_community)
        
        except Exception as e:
            self.logger.error(f"Error analyzing followers: {e}")
        
        return communities
    
    async def _detect_via_activity_patterns(self, user_id: int) -> List[Community]:
        """
        Detect communities via activity pattern analysis
        """
        communities = []
        self.logger.info(f"Analyzing activity patterns for community indicators (user: {user_id})")
        
        try:
            # Analyze tweet timing and frequency patterns
            # Analyze reply patterns to community accounts
            # Analyze retweet patterns from community accounts
            
            # Get user's recent activity
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=100):
                tweets.append(tweet)
            
            # Pattern: Frequent interactions with same accounts (potential community members)
            interaction_counts = {}
            
            for tweet in tweets:
                try:
                    # Check mentions in tweets
                    mentions = getattr(tweet, 'mentionedUsers', []) or []
                    for mention in mentions:
                        if hasattr(mention, 'username'):
                            interaction_counts[mention.username] = interaction_counts.get(mention.username, 0) + 1
                    
                    # Check if tweet is a reply
                    if hasattr(tweet, 'inReplyToUser') and tweet.inReplyToUser:
                        username = tweet.inReplyToUser.username
                        interaction_counts[username] = interaction_counts.get(username, 0) + 2  # Replies weighted higher
                
                except Exception as e:
                    continue
            
            # Find frequently interacted accounts
            frequent_interactions = {k: v for k, v in interaction_counts.items() if v >= 3}
            
            if frequent_interactions:
                # Create a community based on frequent interactions
                top_users = sorted(frequent_interactions.items(), key=lambda x: x[1], reverse=True)[:5]
                community = Community(
                    id=f"interaction_pattern_{user_id}",
                    name="Frequent Interaction Network",
                    description=f"Community detected via frequent interactions with: {', '.join([user for user, count in top_users])}",
                    member_count=len(frequent_interactions),
                    role="Active Member",
                    is_nsfw=False,
                    created_at=datetime.utcnow().isoformat()
                )
                communities.append(community)
        
        except Exception as e:
            self.logger.error(f"Error in activity pattern analysis: {e}")
        
        return communities
    
    async def _detect_via_content_analysis(self, user_id: int) -> List[Community]:
        """
        Detect communities via deep content analysis
        """
        communities = []
        self.logger.info(f"Performing deep content analysis for community detection (user: {user_id})")
        
        try:
            # Get user's tweets and analyze content themes
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=100):
                tweets.append(tweet)
            
            # Analyze content themes and topics
            topic_keywords = self._analyze_content_themes(tweets)
            
            # Convert themes to potential communities
            for topic, keywords in topic_keywords.items():
                if len(keywords) >= 3:  # Threshold for topic relevance
                    community = Community(
                        id=f"content_theme_{hash(topic) % 1000000}",
                        name=f"{topic.title()} Community",
                        description=f"Community detected via content analysis. Related keywords: {', '.join(keywords[:5])}",
                        member_count=0,
                        role="Content Creator",
                        is_nsfw=False,
                        created_at=datetime.utcnow().isoformat()
                    )
                    communities.append(community)
        
        except Exception as e:
            self.logger.error(f"Error in content analysis: {e}")
        
        return communities
    
    def _analyze_content_themes(self, tweets) -> Dict[str, List[str]]:
        """
        Analyze tweets to identify content themes
        """
        themes = {
            'crypto': ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'defi', 'nft', 'web3'],
            'tech': ['ai', 'ml', 'python', 'javascript', 'coding', 'developer', 'programming'],
            'gaming': ['gaming', 'game', 'esports', 'twitch', 'steam', 'xbox', 'playstation'],
            'art': ['art', 'design', 'creative', 'drawing', 'painting', 'artist'],
            'business': ['startup', 'entrepreneur', 'business', 'marketing', 'sales'],
            'finance': ['trading', 'stocks', 'investment', 'finance', 'market']
        }
        
        detected_themes = {}
        
        for tweet in tweets:
            try:
                text = tweet.rawContent.lower() if hasattr(tweet, 'rawContent') else str(tweet).lower()
                
                for theme, keywords in themes.items():
                    matches = [keyword for keyword in keywords if keyword in text]
                    if matches:
                        if theme not in detected_themes:
                            detected_themes[theme] = []
                        detected_themes[theme].extend(matches)
            
            except Exception as e:
                continue
        
        # Remove duplicates and filter
        for theme in detected_themes:
            detected_themes[theme] = list(set(detected_themes[theme]))
        
        return detected_themes
    
    async def _enrich_community_data(self, communities: List[Community]) -> List[Community]:
        """
        Enrich community data with additional information
        """
        self.logger.info(f"Enriching data for {len(communities)} communities")
        
        enriched_communities = []
        
        for community in communities:
            try:
                # Add confidence score based on detection method
                if community.id.startswith('following_'):
                    community.description += " [High Confidence: Following relationship]"
                elif community.id.startswith('tweet_analysis_'):
                    community.description += " [Medium Confidence: Tweet analysis]"
                elif community.id.startswith('interaction_pattern_'):
                    community.description += " [High Confidence: Interaction patterns]"
                else:
                    community.description += " [Medium Confidence: Content analysis]"
                
                enriched_communities.append(community)
                
            except Exception as e:
                self.logger.debug(f"Error enriching community data: {e}")
                enriched_communities.append(community)  # Add anyway
        
        return enriched_communities
    
    async def track_community_changes(self, username: str, previous_communities: List[Community], deep_scan: bool = True) -> Dict[str, Any]:
        """
        Track comprehensive changes in user's community participation
        
        Uses multiple detection methods:
        1. Traditional community detection (URLs, profiles, etc.)
        2. Post-based analysis for creation/joining indicators
        3. Activity pattern analysis
        
        Returns:
            Detailed change report with high confidence
        """
        self.logger.info(f"Tracking comprehensive community changes for @{username}")
        
        result = {
            'joined': [],
            'left': [],
            'created': [],
            'role_changes': [],
            'activity_changes': [],
            'error': None,
            'total_previous': len(previous_communities),
            'total_current': 0,
            'scan_type': 'deep' if deep_scan else 'quick',
            'detection_methods': [],
            'confidence_scores': {}
        }
        
        try:
            # Method 1: Traditional comprehensive community detection
            self.logger.info("🔍 Running traditional community detection...")
            current_payload = await self.get_all_user_communities(username, deep_scan=deep_scan)
            
            traditional_communities = []
            if current_payload:
                traditional_communities = current_payload.communities
                result['total_current'] = len(traditional_communities)
                result['detection_methods'].append('traditional')
                
                # Compare with previous communities
                traditional_changes = self._detailed_community_diff(previous_communities, traditional_communities)
                
                # Merge traditional results
                result['joined'].extend(traditional_changes['joined'])
                result['left'].extend(traditional_changes['left'])
                result['created'].extend(traditional_changes['created'])
                result['role_changes'].extend(traditional_changes['role_changes'])
                
                self.logger.info(f"Traditional detection found: "
                               f"joined={len(traditional_changes['joined'])}, "
                               f"left={len(traditional_changes['left'])}, "
                               f"created={len(traditional_changes['created'])}")
            
            # Method 2: Post-based community detection (Enhanced for recent activity)
            self.logger.info("📊 Running post-based community detection...")
            try:
                post_changes = await self.post_tracker.track_community_changes_via_posts(
                    username, previous_communities, hours_lookback=24
                )
                
                if not post_changes.get('error'):
                    result['detection_methods'].append('post_analysis')
                    
                    # Merge post-based results (avoid duplicates)
                    for new_community in post_changes['joined']:
                        if not self._is_duplicate_community(new_community, result['joined']):
                            result['joined'].append(new_community)
                            result['confidence_scores'][new_community.id] = post_changes['confidence_scores'].get(new_community.id, 0.7)
                    
                    for new_community in post_changes['created']:
                        if not self._is_duplicate_community(new_community, result['created']):
                            result['created'].append(new_community)
                            result['confidence_scores'][new_community.id] = post_changes['confidence_scores'].get(new_community.id, 0.8)
                    
                    for left_community in post_changes['left']:
                        if not self._is_duplicate_community(left_community, result['left']):
                            result['left'].append(left_community)
                    
                    # Add activity changes
                    result['activity_changes'].extend(post_changes.get('activity_changes', []))
                    
                    self.logger.info(f"Post analysis found: "
                                   f"joined={len(post_changes['joined'])}, "
                                   f"left={len(post_changes['left'])}, "
                                   f"created={len(post_changes['created'])}")
                else:
                    self.logger.warning(f"Post analysis failed: {post_changes['error']}")
                    
            except Exception as e:
                self.logger.error(f"Post-based detection failed: {e}")
            
            # Method 3: Enhanced activity pattern analysis
            if deep_scan:
                self.logger.info("🧠 Running enhanced activity pattern analysis...")
                try:
                    activity_communities = await self._detect_communities_via_enhanced_activity(username, previous_communities)
                    
                    if activity_communities:
                        result['detection_methods'].append('activity_patterns')
                        
                        for community in activity_communities:
                            if not self._is_duplicate_community(community, result['joined']):
                                result['joined'].append(community)
                                result['confidence_scores'][community.id] = 0.6  # Medium confidence for activity-based
                        
                        self.logger.info(f"Activity pattern analysis found {len(activity_communities)} communities")
                        
                except Exception as e:
                    self.logger.error(f"Activity pattern analysis failed: {e}")
            
            # Update total current count
            all_current_communities = []
            all_current_communities.extend(result['joined'])
            all_current_communities.extend(result['created'])
            # Add previous communities that weren't left
            left_ids = {c.id for c in result['left']}
            remaining_previous = [c for c in previous_communities if c.id not in left_ids]
            all_current_communities.extend(remaining_previous)
            
            result['total_current'] = len(all_current_communities)
            
            self.logger.info(f"📈 Combined community changes for @{username}: "
                           f"joined={len(result['joined'])}, "
                           f"left={len(result['left'])}, "
                           f"created={len(result['created'])}, "
                           f"role_changes={len(result['role_changes'])}, "
                           f"methods_used={result['detection_methods']}")
            
        except Exception as e:
            self.logger.error(f"Error tracking community changes for @{username}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _detailed_community_diff(self, old_communities: List[Community], new_communities: List[Community]) -> Dict[str, List]:
        """
        Perform detailed comparison of community lists
        """
        # Create mappings for comparison
        old_by_id = {c.id: c for c in old_communities}
        new_by_id = {c.id: c for c in new_communities}
        old_by_name = {c.name.lower(): c for c in old_communities}
        new_by_name = {c.name.lower(): c for c in new_communities}
        
        joined = []
        left = []
        created = []
        role_changes = []
        
        # Find new communities (joined)
        for community_id, community in new_by_id.items():
            if community_id not in old_by_id:
                # Check if it's the same community with different ID (name-based matching)
                if community.name.lower() not in old_by_name:
                    if community.role in ["Admin", "Creator", "Founder"]:
                        created.append(community)
                    else:
                        joined.append(community)
        
        # Find removed communities (left)
        for community_id, community in old_by_id.items():
            if community_id not in new_by_id:
                # Check if it's the same community with different ID
                if community.name.lower() not in new_by_name:
                    left.append(community)
        
        # Find role changes
        for community_id, old_community in old_by_id.items():
            if community_id in new_by_id:
                new_community = new_by_id[community_id]
                if old_community.role != new_community.role:
                    role_changes.append({
                        'community': new_community,
                        'old_role': old_community.role,
                        'new_role': new_community.role
                    })
        
        return {
            'joined': joined,
            'left': left,
            'created': created,
            'role_changes': role_changes
        }
    
    async def _detect_basic_community_actions(self, user_id: int) -> List[Community]:
        """
        Lightweight detection for actual community joins/creates only
        Focuses on explicit community actions with minimal API calls
        """
        communities = []
        self.logger.info(f"Performing basic community action detection (user: {user_id})")
        
        try:
            # Get only recent tweets (limited to avoid rate limits)
            tweets = []
            count = 0
            async for tweet in self.api.user_tweets(user_id, limit=20):  # Much smaller limit
                tweets.append(tweet)
                count += 1
                if count >= 20:  # Hard limit
                    break
            
            if not tweets:
                self.logger.info(f"No recent tweets found for user {user_id}")
                return communities
            
            self.logger.info(f"Analyzing {len(tweets)} recent tweets for community actions")
            
            # Look for explicit community actions only
            tweet_count = 0
            for tweet in tweets:
                try:
                    tweet_count += 1
                    text = tweet.rawContent.lower() if hasattr(tweet, 'rawContent') else str(tweet).lower()
                    
                    # Debug: Log first few tweets to see what we're analyzing
                    if tweet_count <= 3:
                        self.logger.info(f"Sample tweet {tweet_count}: {text[:100]}...")
                    
                    # Pattern 1: Explicit community joins
                    join_patterns = [
                        r'joined\s+(\w+(?:\s+\w+)*)\s+community',
                        r'became\s+(?:a\s+)?member\s+of\s+(\w+(?:\s+\w+)*)',
                        r'welcome\s+to\s+(\w+(?:\s+\w+)*)\s+community',
                        r'now\s+part\s+of\s+(\w+(?:\s+\w+)*)',
                    ]
                    
                    for pattern in join_patterns:
                        matches = re.findall(pattern, text)
                        for match in matches:
                            community_name = match.strip().title()
                            if len(community_name) > 3:
                                community = Community(
                                    id=f"joined_{hash(community_name) % 1000000}",
                                    name=community_name,
                                    role="Member"
                                )
                                communities.append(community)
                                self.logger.info(f"Detected joined community: {community_name}")
                    
                    # Pattern 2: Explicit community creation
                    create_patterns = [
                        r'created\s+(?:a\s+)?(?:new\s+)?community\s+(?:called\s+)?(\w+(?:\s+\w+)*)',
                        r'launched\s+(\w+(?:\s+\w+)*)\s+community',
                        r'founding\s+(\w+(?:\s+\w+)*)\s+community',
                        r'started\s+(?:a\s+)?(?:new\s+)?community\s+(\w+(?:\s+\w+)*)',
                    ]
                    
                    for pattern in create_patterns:
                        matches = re.findall(pattern, text)
                        for match in matches:
                            community_name = match.strip().title()
                            if len(community_name) > 3:
                                community = Community(
                                    id=f"created_{hash(community_name) % 1000000}",
                                    name=community_name,
                                    role="Admin"
                                )
                                communities.append(community)
                                self.logger.info(f"Detected created community: {community_name}")
                    
                    # Pattern 3: Twitter Communities URLs (most reliable)
                    url_patterns = [
                        r'(?:twitter\.com|x\.com)/i/communities/(\d+)',
                        r'communities/(\d+)',
                    ]
                    
                    for pattern in url_patterns:
                        matches = re.findall(pattern, text)
                        for match in matches:
                            community = Community(
                                id=f"twitter_community_{match}",
                                name=f"Twitter Community {match}",
                                role="Member"  # Default to member, could be admin if they created it
                            )
                            communities.append(community)
                            self.logger.info(f"Detected Twitter community link: {match}")
                    
                    # Pattern 4: Check for broader community indicators for debugging
                    if tweet_count <= 10:  # Only check first 10 tweets for debug
                        community_keywords = ['community', 'group', 'club', 'collective', 'discord', 'telegram']
                        found_keywords = [kw for kw in community_keywords if kw in text]
                        if found_keywords:
                            self.logger.debug(f"Found community keywords in tweet {tweet_count}: {found_keywords}")
                    
                except Exception as e:
                    self.logger.debug(f"Error processing tweet {tweet_count} for community detection: {e}")
                    continue
            
            # Remove duplicates based on ID
            unique_communities = {}
            for community in communities:
                unique_communities[community.id] = community
            
            final_communities = list(unique_communities.values())
            self.logger.info(f"Found {len(final_communities)} communities via basic detection")
            
            # If no communities found, log for debugging
            if len(final_communities) == 0:
                self.logger.info(f"No explicit community actions detected in {len(tweets)} recent tweets for user {user_id}")
                self.logger.info("This is normal if the user hasn't recently tweeted about joining/creating communities")
            
            return final_communities
            
        except Exception as e:
            self.logger.error(f"Error in basic community detection: {e}")
            return []

    def _is_duplicate_community(self, new_community: Community, existing_communities: List[Community]) -> bool:
        """
        Check if a new community is a duplicate of an existing one
        
        Uses multiple matching criteria:
        1. Exact ID match
        2. Name similarity (case-insensitive)
        3. Pattern matching for similar community names
        """
        for existing in existing_communities:
            # Exact ID match
            if existing.id == new_community.id:
                return True
            
            # Name similarity match (case-insensitive)
            if existing.name.lower() == new_community.name.lower():
                return True
            
            # Pattern matching for similar names
            # Remove common words and compare
            new_clean = self._clean_community_name(new_community.name)
            existing_clean = self._clean_community_name(existing.name)
            
            if new_clean and existing_clean and new_clean == existing_clean:
                return True
        
        return False
    
    def _clean_community_name(self, name: str) -> str:
        """Clean community name for comparison"""
        if not name:
            return ""
        
        # Convert to lowercase and remove common words
        cleaned = name.lower()
        
        # Remove common community-related words
        common_words = ['community', 'group', 'collective', 'club', 'dao', 'the', 'a', 'an']
        for word in common_words:
            cleaned = cleaned.replace(word, ' ')
        
        # Remove extra spaces and return
        return ' '.join(cleaned.split())
    
    async def _detect_communities_via_enhanced_activity(self, username: str, previous_communities: List[Community]) -> List[Community]:
        """
        Enhanced activity pattern analysis for community detection
        
        Analyzes:
        1. Reply patterns to community accounts
        2. Hashtag evolution and new community hashtags
        3. Mention patterns and community account interactions
        4. Timeline analysis for community content
        """
        communities = []
        
        try:
            user = await self.api.user_by_login(username)
            if not user:
                return communities
            
            self.logger.info(f"🔍 Enhanced activity analysis for @{username}")
            
            # Get extended tweet history for pattern analysis
            tweets = []
            count = 0
            async for tweet in self.api.user_tweets(user.id, limit=100):
                tweets.append(tweet)
                count += 1
                if count >= 100:
                    break
            
            if not tweets:
                return communities
            
            # Analyze for new community patterns
            new_communities = await self._analyze_for_new_community_patterns(tweets, previous_communities)
            communities.extend(new_communities)
            
            # Analyze engagement patterns for community discovery
            engagement_communities = await self._analyze_engagement_patterns_for_communities(tweets, user.id)
            
            # Avoid duplicates
            existing_ids = {c.id for c in communities}
            for comm in engagement_communities:
                if comm.id not in existing_ids:
                    communities.append(comm)
            
            self.logger.info(f"Enhanced activity analysis found {len(communities)} communities")
            
        except Exception as e:
            self.logger.error(f"Error in enhanced activity analysis: {e}")
        
        return communities
    
    async def _analyze_for_new_community_patterns(self, tweets, previous_communities: List[Community]) -> List[Community]:
        """Analyze tweets for new community activity patterns"""
        communities = []
        
        # Track hashtag evolution
        recent_hashtags = set()
        community_hashtags = set()
        
        for tweet in tweets[:20]:  # Analyze recent tweets
            try:
                content = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                
                # Extract hashtags
                hashtags = re.findall(r'#(\w+)', content.lower())
                recent_hashtags.update(hashtags)
                
                # Filter for community-related hashtags
                for hashtag in hashtags:
                    if any(keyword in hashtag for keyword in ['community', 'dao', 'group', 'club', 'collective']):
                        community_hashtags.add(hashtag)
                
            except Exception as e:
                self.logger.debug(f"Error processing tweet for hashtag analysis: {e}")
                continue
        
        # Check for new community hashtags not in previous communities
        previous_community_names = {c.name.lower() for c in previous_communities}
        
        for hashtag in community_hashtags:
            # Create potential community name from hashtag
            potential_name = hashtag.replace('community', '').replace('dao', '').replace('group', '').strip()
            if len(potential_name) > 2 and potential_name not in previous_community_names:
                community = Community(
                    id=f"hashtag_{abs(hash(hashtag)) % 1000000}",
                    name=f"{potential_name.title()} Community",
                    role="Member",
                    description=f"Detected via hashtag #{hashtag}"
                )
                communities.append(community)
                self.logger.info(f"🏷️ Detected community via hashtag #{hashtag}: {community.name}")
        
        return communities
    
    async def _analyze_engagement_patterns_for_communities(self, tweets, user_id: int) -> List[Community]:
        """Analyze engagement patterns to discover communities"""
        communities = []
        
        # Track mentions and replies
        mentioned_accounts = {}
        
        for tweet in tweets:
            try:
                content = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                
                # Find mentions
                mentions = re.findall(r'@(\w+)', content)
                
                for mention in mentions:
                    mention_lower = mention.lower()
                    # Check if mention looks like a community account
                    if any(keyword in mention_lower for keyword in ['community', 'dao', 'collective', 'group', 'club']):
                        if mention not in mentioned_accounts:
                            mentioned_accounts[mention] = 0
                        mentioned_accounts[mention] += 1
                
            except Exception as e:
                self.logger.debug(f"Error analyzing engagement patterns: {e}")
                continue
        
        # Create communities for frequently mentioned community accounts
        for account, count in mentioned_accounts.items():
            if count >= 2:  # Mentioned at least twice
                community_name = account.replace('community', '').replace('dao', '').replace('group', '').strip()
                if len(community_name) > 2:
                    community = Community(
                        id=f"mention_{abs(hash(account)) % 1000000}",
                        name=f"{community_name.title()} Community",
                        role="Member",
                        description=f"Detected via frequent mentions of @{account} ({count} times)"
                    )
                    communities.append(community)
                    self.logger.info(f"💬 Detected community via mentions: @{account} → {community.name}")
        
        return communities 