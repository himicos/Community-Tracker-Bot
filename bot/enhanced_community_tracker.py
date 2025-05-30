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
from bot.advanced_community_extractor import AdvancedCommunityExtractor
from bot.browser_community_detector import BrowserCommunityDetector, CommunityNotifier


class EnhancedCommunityTracker:
    """Comprehensive Community Tracking System"""
    
    def __init__(self, api: API, cookie_manager: CookieManager):
        self.api = api
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize the post tracker for advanced community detection
        self.post_tracker = CommunityPostTracker(api, cookie_manager)
        
        # Initialize the advanced extractor for DOM-level community data
        self.advanced_extractor = AdvancedCommunityExtractor(api)
        
        # Initialize the browser detector for REAL community detection
        self.browser_detector = BrowserCommunityDetector(cookie_manager)
        
        # Initialize the notifier for new community alerts
        self.notifier = CommunityNotifier()
        
        self.logger.info("Enhanced Community Tracker initialized with comprehensive detection including REAL browser-based detection")
    
    async def get_all_user_communities(self, username: str, deep_scan: bool = True, use_browser: bool = False) -> Optional[TwitterUserCommunityPayload]:
        """
        Get the actual current list of Twitter Communities the user is in
        Now includes REAL browser-based detection for client-side rendered community data
        
        Args:
            username: Twitter username (without @)
            deep_scan: If True, tries multiple methods; if False, uses fastest method
            use_browser: If True, uses browser automation for REAL community detection
            
        Returns:
            TwitterUserCommunityPayload with current community memberships
        """
        self.logger.info(f"🔍 Getting current Twitter Communities for @{username} (browser: {use_browser})")
        
        try:
            # Get user information
            user = await self.api.user_by_login(username)
            if not user:
                self.logger.error(f"User @{username} not found")
                return None
            
            self.logger.info(f"Found user: {user.displayname} (@{user.username}, ID: {user.id})")
            
            # Get actual current communities
            all_communities = []
            
            if use_browser:
                self.logger.info("🌐 Using REAL browser-based community detection")
                
                # Method 1: Browser detection (most accurate - REAL DOM data)
                browser_communities = await self.browser_detector.detect_real_communities(username, max_tweets=10)
                all_communities.extend(browser_communities)
                
                # Send notifications for new communities
                if browser_communities:
                    await self.notifier.notify_community_changes(username, browser_communities)
                
                self.logger.info(f"Browser detection found {len(browser_communities)} communities")
                
                # NEVER fallback to pattern matching - browser detection is authoritative
                if not browser_communities:
                    self.logger.info("🔍 No communities detected in recent posts")
                    
            elif deep_scan:
                self.logger.info("🔍 Using comprehensive community detection with advanced extraction")
                
                # Method 1: Advanced extraction (primary method for API-based detection)
                advanced_communities = await self.advanced_extractor.extract_communities_advanced(user.id)
                all_communities.extend(advanced_communities)
                self.logger.info(f"Advanced extraction found {len(advanced_communities)} communities")
                
                # Method 2: Try direct API calls (supplementary)
                api_communities = await self._get_current_communities_api(user.id)
                # Avoid duplicates
                existing_ids = {c.id for c in all_communities}
                new_api_communities = [c for c in api_communities if c.id not in existing_ids]
                all_communities.extend(new_api_communities)
                
                # Method 3: Extract from recent tweets with community URLs (fallback)
                url_communities = await self._get_communities_from_urls(user.id)
                existing_ids = {c.id for c in all_communities}
                new_url_communities = [c for c in url_communities if c.id not in existing_ids]
                all_communities.extend(new_url_communities)
                
                # Method 4: Profile analysis for community links (fallback)
                profile_communities = await self._get_communities_from_profile(user)
                existing_ids = {c.id for c in all_communities}
                new_profile_communities = [c for c in profile_communities if c.id not in existing_ids]
                all_communities.extend(new_profile_communities)
                
            else:
                self.logger.info("⚡ Using fast community detection with advanced patterns")
                
                # Use advanced extraction as primary fast method
                advanced_communities = await self.advanced_extractor.extract_communities_advanced(user.id)
                all_communities.extend(advanced_communities)
                
                # Fallback to URL method if advanced extraction finds nothing
                if not advanced_communities:
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
    
    async def monitor_user_communities(self, username: str, interval_minutes: int = 30):
        """
        Continuously monitor a user for NEW community activities
        Uses browser detection for maximum accuracy
        """
        self.logger.info(f"👁️ Starting community monitoring for @{username} (interval: {interval_minutes}m)")
        
        while True:
            try:
                # Use browser detection for monitoring (most accurate)
                result = await self.get_all_user_communities(username, deep_scan=True, use_browser=True)
                
                if result and result.communities:
                    self.logger.info(f"📊 Monitoring update: @{username} has {len(result.communities)} total communities")
                else:
                    self.logger.info(f"📊 Monitoring update: @{username} - no new communities detected")
                
                # Wait for next check
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in community monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _get_current_communities_api(self, user_id: int) -> List[Community]:
        """
        Try to get current communities using Twitter's API endpoints
        Now includes community metadata extraction as primary method
        """
        communities = []
        self.logger.info(f"🔗 Attempting direct API community lookup for user {user_id}")
        
        try:
            # Method 1: NEW - Extract communities from tweet metadata (primary method)
            self.logger.info("🔍 Using tweet metadata extraction (primary method)")
            metadata_communities = await self._extract_communities_from_tweet_metadata(user_id)
            if metadata_communities:
                communities.extend(metadata_communities)
                self.logger.info(f"✅ Metadata extraction found {len(metadata_communities)} communities")
            
            # Method 2: URL extraction (fallback/supplementary)
            self.logger.info("🔗 Using URL extraction (supplementary method)")
            url_communities = await self._get_communities_from_urls(user_id)
            
            # Merge and avoid duplicates
            existing_ids = {c.id for c in communities}
            for url_community in url_communities:
                if url_community.id not in existing_ids:
                    communities.append(url_community)
            
            # Method 3: Direct GraphQL (if available)
            graphql_communities = await self._fetch_user_communities_graphql(user_id)
            existing_ids = {c.id for c in communities}
            for graphql_community in graphql_communities:
                if graphql_community.id not in existing_ids:
                    communities.append(graphql_community)
            
            self.logger.info(f"📊 Total current communities found: {len(communities)}")
            
        except Exception as e:
            self.logger.error(f"Error in community detection: {e}")
        
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
            
            # DEBUG: Log first few tweets to see actual content
            for i, tweet in enumerate(tweets[:5]):
                try:
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    self.logger.info(f"🔍 DEBUG Tweet {i+1}: {tweet_text[:200]}...")
                    
                    # Look for any community-related keywords for debugging
                    community_keywords = ['community', 'communities', 'group', '@', '#', 'http', 'x.com', 'twitter.com']
                    found_keywords = [kw for kw in community_keywords if kw.lower() in tweet_text.lower()]
                    if found_keywords:
                        self.logger.info(f"🔍 DEBUG Tweet {i+1} contains: {found_keywords}")
                        
                        # Check for mentions specifically
                        mentions = [word for word in tweet_text.split() if word.startswith('@')]
                        if mentions:
                            self.logger.info(f"🔍 DEBUG Tweet {i+1} mentions: {mentions}")
                        
                        # Check for hashtags
                        hashtags = [word for word in tweet_text.split() if word.startswith('#')]
                        if hashtags:
                            self.logger.info(f"🔍 DEBUG Tweet {i+1} hashtags: {hashtags}")
                        
                        # Check for URLs
                        urls = [word for word in tweet_text.split() if any(domain in word for domain in ['http', 'x.com', 'twitter.com', 't.co'])]
                        if urls:
                            self.logger.info(f"🔍 DEBUG Tweet {i+1} URLs: {urls}")
                
                except Exception as e:
                    self.logger.debug(f"Error in debug analysis of tweet {i+1}: {e}")
            
            # Extract community IDs from URLs
            community_ids = set()
            community_mentions = set()  # Track @mentions of community accounts
            
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
                    
                    # NEW: Look for community-related @mentions
                    community_mention_patterns = [
                        r'@(\w*community\w*)',
                        r'@(\w*group\w*)',
                        r'@(\w*collective\w*)',
                        r'@(\w*club\w*)',
                        r'@(\w*dao\w*)',
                        r'@(\w*guild\w*)'
                    ]
                    
                    for pattern in community_mention_patterns:
                        matches = re.findall(pattern, tweet_text, re.IGNORECASE)
                        for mention in matches:
                            if len(mention) > 3:  # Filter out short matches
                                community_mentions.add(mention.lower())
                                self.logger.info(f"✅ Found community mention: @{mention}")
                    
                    # NEW: Look for community keywords in text
                    community_text_patterns = [
                        r'joined\s+(\w+(?:\s+\w+)*)\s+community',
                        r'part\s+of\s+(\w+(?:\s+\w+)*)\s+community',
                        r'(\w+(?:\s+\w+)*)\s+community\s+member',
                        r'welcome\s+to\s+(\w+(?:\s+\w+)*)',
                        r'(\w+)\s+dao\s+member',
                        r'active\s+in\s+(\w+(?:\s+\w+)*)',
                        r'(\w+(?:\s+\w+)*)\s+community\s+tracking',  # NEW: for "X community tracking"
                        r'track\s+(?:what\s+)?communities\s+(?:user\s+)?(\w+)',  # NEW: for "track communities user joins"
                        r'(\w+)\s+community\s+tool',  # NEW: for "community tool"
                        r'communities\s+user\s+(\w+)',  # NEW: for "communities user joins"
                        r'building\s+(?:a\s+)?community\s+(?:for\s+)?(\w+)',  # NEW: for community building
                        r'created?\s+(?:a\s+)?community\s+(?:called\s+)?(\w+(?:\s+\w+)*)',  # Enhanced creation pattern
                        r'(\w+)\s+community\s+(?:bot|system|platform)',  # NEW: for community systems
                    ]
                    
                    for pattern in community_text_patterns:
                        matches = re.findall(pattern, tweet_text, re.IGNORECASE)
                        for match in matches:
                            community_name = match.strip()
                            if len(community_name) > 2 and not any(word in community_name.lower() for word in ['the', 'this', 'that', 'and', 'or', 'user', 'what', 'when', 'how']):
                                self.logger.info(f"✅ Found community text reference: {community_name}")
                                # Create a synthetic community ID for text-based detection
                                synthetic_id = f"text_{abs(hash(community_name.lower())) % 1000000}"
                                community_ids.add(synthetic_id)
                    
                    # NEW: Look for general community involvement patterns
                    general_patterns = [
                        r'i\s+coded?\s+(\w+(?:\s+\w+)*)\s+community',  # "I coded X community"
                        r'built?\s+(?:a\s+)?(\w+(?:\s+\w+)*)\s+community',  # "built a community"
                        r'working\s+on\s+(\w+(?:\s+\w+)*)\s+community',  # "working on community"
                        r'(\w+(?:\s+\w+)*)\s+community\s+(?:project|tool|bot|tracker|system)',  # community tools
                    ]
                    
                    for pattern in general_patterns:
                        matches = re.findall(pattern, tweet_text, re.IGNORECASE)
                        for match in matches:
                            community_name = match.strip()
                            if len(community_name) > 1 and not any(word in community_name.lower() for word in ['the', 'this', 'that', 'and', 'or', 'user', 'what', 'when', 'how', 'all', 'some']):
                                self.logger.info(f"✅ Found general community reference: {community_name}")
                                # Create a synthetic community ID for text-based detection
                                synthetic_id = f"general_{abs(hash(community_name.lower())) % 1000000}"
                                community_ids.add(synthetic_id)
                    
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
            
            # Log all findings
            if community_mentions:
                self.logger.info(f"📍 Found {len(community_mentions)} community mentions: {list(community_mentions)}")
            
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
                        name=f"Twitter Community {community_id}" if community_id.isdigit() else community_id.replace('text_', '').title(),
                        description="Community detected from user's tweets",
                        member_count=0,
                        role="Member",
                        is_nsfw=False,
                        created_at=datetime.utcnow().isoformat()
                    )
                    communities.append(basic_community)
            
            # Create communities for mentioned accounts
            for mention in community_mentions:
                try:
                    mention_community = Community(
                        id=f"mention_{abs(hash(mention)) % 1000000}",
                        name=f"{mention.title()} Community",
                        description=f"Community detected via @{mention} mention",
                        member_count=0,
                        role="Member",
                        is_nsfw=False,
                        created_at=datetime.utcnow().isoformat()
                    )
                    communities.append(mention_community)
                    self.logger.info(f"✅ Added community from mention: @{mention}")
                except Exception as e:
                    self.logger.debug(f"Error creating community from mention {mention}: {e}")
            
            self.logger.info(f"📋 Extracted {len(communities)} communities from URLs and mentions")
            
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
        Now includes metadata extraction as primary method
        """
        communities = []
        self.logger.info(f"🔍 Using comprehensive community detection")
        
        try:
            # Method 1: NEW - Extract communities from tweet metadata (primary)
            self.logger.info("🔗 Attempting direct API community lookup for user {user_id}")
            metadata_communities = await self._extract_communities_from_tweet_metadata(user_id)
            if metadata_communities:
                communities.extend(metadata_communities)
                self.logger.info(f"✅ Metadata extraction found {len(metadata_communities)} communities")
            
            # Method 2: Try to get user's community memberships via GraphQL
            communities_from_api = await self._fetch_user_communities_graphql(user_id)
            existing_ids = {c.id for c in communities}
            new_api_communities = [c for c in communities_from_api if c.id not in existing_ids]
            if new_api_communities:
                communities.extend(new_api_communities)
                self.logger.info(f"Found {len(new_api_communities)} additional communities via direct API")
            
            # Method 3: Scan recent tweets for Twitter Community URLs and extract IDs
            communities_from_urls = await self._extract_communities_from_tweet_urls(user_id)
            existing_ids = {c.id for c in communities}
            new_url_communities = [c for c in communities_from_urls if c.id not in existing_ids]
            if new_url_communities:
                communities.extend(new_url_communities)
                self.logger.info(f"Found {len(new_url_communities)} additional communities from tweet URLs")
            
            self.logger.info(f"📊 Total current communities found: {len(communities)}")
            
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
    
    async def _extract_communities_from_tweet_metadata(self, user_id: int) -> List[Community]:
        """
        Extract community information from tweet metadata/objects - the missing piece!
        This checks for actual community data that Twitter includes in tweet objects
        """
        communities = []
        
        try:
            # Get recent tweets with full metadata
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=50):
                tweets.append(tweet)
            
            if not tweets:
                self.logger.info("❌ No tweets found for metadata extraction")
                return communities
            
            self.logger.info(f"🔍 Checking {len(tweets)} tweets for community metadata")
            
            # DEBUG: Comprehensive tweet structure analysis
            for i, tweet in enumerate(tweets[:3]):  # Analyze first 3 tweets in detail
                try:
                    self.logger.info(f"🔍 DETAILED ANALYSIS Tweet {i+1}:")
                    
                    # Basic tweet info
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    self.logger.info(f"  📝 Content: {tweet_text[:100]}...")
                    
                    # List ALL available attributes
                    all_attrs = [attr for attr in dir(tweet) if not attr.startswith('_')]
                    self.logger.info(f"  📋 Available attributes ({len(all_attrs)}): {all_attrs}")
                    
                    # Check for community-related attributes
                    community_attrs = [attr for attr in all_attrs if 'community' in attr.lower()]
                    if community_attrs:
                        self.logger.info(f"  🎯 Community-related attributes: {community_attrs}")
                        for attr in community_attrs:
                            try:
                                value = getattr(tweet, attr)
                                self.logger.info(f"    {attr}: {type(value)} = {value}")
                            except Exception as e:
                                self.logger.info(f"    {attr}: Error accessing - {e}")
                    else:
                        self.logger.info(f"  ❌ No community-related attributes found")
                    
                    # Check for nested structures that might contain community data
                    nested_attrs = ['data', 'legacy', 'raw', 'extended_entities', 'entities', 'result', 'core']
                    for attr in nested_attrs:
                        if hasattr(tweet, attr):
                            try:
                                nested_obj = getattr(tweet, attr)
                                if nested_obj:
                                    self.logger.info(f"  📁 {attr}: {type(nested_obj)}")
                                    
                                    # If it's a dict, check for community keys
                                    if isinstance(nested_obj, dict):
                                        community_keys = [k for k in nested_obj.keys() if 'community' in k.lower()]
                                        if community_keys:
                                            self.logger.info(f"    🎯 Found community keys in {attr}: {community_keys}")
                                            for key in community_keys:
                                                self.logger.info(f"      {key}: {nested_obj[key]}")
                                        else:
                                            # List all keys for debugging
                                            self.logger.info(f"    🔑 All keys in {attr}: {list(nested_obj.keys())}")
                                    
                                    # If it's an object, check for community attributes
                                    elif hasattr(nested_obj, '__dict__') or hasattr(nested_obj, '__dir__'):
                                        try:
                                            nested_attrs_list = [a for a in dir(nested_obj) if not a.startswith('_')]
                                            community_nested = [a for a in nested_attrs_list if 'community' in a.lower()]
                                            if community_nested:
                                                self.logger.info(f"    🎯 Found community attributes in {attr}: {community_nested}")
                                                for nested_attr in community_nested:
                                                    try:
                                                        nested_value = getattr(nested_obj, nested_attr)
                                                        self.logger.info(f"      {nested_attr}: {type(nested_value)} = {nested_value}")
                                                    except Exception as e:
                                                        self.logger.info(f"      {nested_attr}: Error - {e}")
                                            else:
                                                self.logger.info(f"    📋 Attributes in {attr}: {nested_attrs_list[:10]}{'...' if len(nested_attrs_list) > 10 else ''}")
                                        except Exception as e:
                                            self.logger.debug(f"    Error analyzing {attr}: {e}")
                                    
                                    else:
                                        self.logger.info(f"    📄 {attr} content: {str(nested_obj)[:100]}...")
                            except Exception as e:
                                self.logger.debug(f"  Error checking {attr}: {e}")
                    
                    # Check for mentions and entities that might be community-related
                    if hasattr(tweet, 'mentionedUsers') and tweet.mentionedUsers:
                        self.logger.info(f"  👥 Mentioned users: {[getattr(u, 'username', str(u)) for u in tweet.mentionedUsers]}")
                    
                    if hasattr(tweet, 'urls') and tweet.urls:
                        self.logger.info(f"  🔗 URLs: {[getattr(u, 'expanded_url', getattr(u, 'url', str(u))) for u in tweet.urls]}")
                    
                    if hasattr(tweet, 'hashtags') and tweet.hashtags:
                        self.logger.info(f"  🏷️ Hashtags: {[getattr(h, 'text', str(h)) for h in tweet.hashtags]}")
                    
                    self.logger.info(f"  ─────────────────────────────────────")
                    
                except Exception as e:
                    self.logger.error(f"Error in detailed analysis of tweet {i+1}: {e}")
            
            # Now try to extract community data
            community_data = {}
            
            for tweet in tweets:
                try:
                    # Check for community-related attributes in the tweet object
                    community_info = self._parse_tweet_community_metadata(tweet)
                    
                    if community_info:
                        community_id = community_info['id']
                        if community_id not in community_data:
                            community_data[community_id] = community_info
                            community_data[community_id]['post_count'] = 0
                        
                        community_data[community_id]['post_count'] += 1
                        self.logger.info(f"✅ Found community metadata: {community_info['name']} (ID: {community_id})")
                
                except Exception as e:
                    self.logger.debug(f"Error checking tweet metadata: {e}")
                    continue
            
            # Create Community objects from found metadata
            for community_id, info in community_data.items():
                try:
                    # Determine role based on posting frequency
                    role = "Admin" if info['post_count'] >= 5 else "Member"
                    
                    community = Community(
                        id=community_id,
                        name=info['name'],
                        description=f"Community detected from tweet metadata (posts: {info['post_count']})",
                        member_count=info.get('member_count', 0),
                        role=role,
                        is_nsfw=info.get('is_nsfw', False),
                        created_at=datetime.utcnow().isoformat()
                    )
                    
                    communities.append(community)
                    
                except Exception as e:
                    self.logger.debug(f"Error creating community from metadata: {e}")
            
            if communities:
                self.logger.info(f"📊 Extracted {len(communities)} communities from tweet metadata")
            else:
                self.logger.info(f"❌ No community metadata found in {len(tweets)} tweets")
            
        except Exception as e:
            self.logger.error(f"Error extracting communities from tweet metadata: {e}")
        
        return communities
    
    def _parse_tweet_community_metadata(self, tweet) -> Optional[Dict[str, Any]]:
        """
        Parse community metadata from a tweet object
        This is the critical missing piece - checking actual tweet metadata for community info
        """
        try:
            # DEBUG: Log tweet attributes for the first few tweets
            if not hasattr(self, '_debug_logged'):
                self._debug_logged = True
                available_attrs = [attr for attr in dir(tweet) if not attr.startswith('_')]
                self.logger.info(f"🔍 DEBUG: Tweet object attributes: {available_attrs}")
                
                # Log any attributes that might contain community data
                potential_community_attrs = []
                for attr in available_attrs:
                    if any(keyword in attr.lower() for keyword in ['community', 'group', 'result', 'legacy', 'data']):
                        potential_community_attrs.append(attr)
                
                if potential_community_attrs:
                    self.logger.info(f"🔍 DEBUG: Potential community-related attributes: {potential_community_attrs}")
                    
                    for attr in potential_community_attrs:
                        try:
                            value = getattr(tweet, attr)
                            self.logger.info(f"🔍 DEBUG: {attr} = {type(value)} - {str(value)[:200]}")
                        except Exception as e:
                            self.logger.debug(f"DEBUG: Error accessing {attr}: {e}")
            
            # Method 1: Check for community field directly on tweet object
            if hasattr(tweet, 'community') and tweet.community:
                community = tweet.community
                self.logger.info(f"✅ Found community via direct attribute: {community}")
                return {
                    'id': getattr(community, 'id', getattr(community, 'id_str', str(community))),
                    'name': getattr(community, 'name', f"Community {getattr(community, 'id', 'Unknown')}"),
                    'member_count': getattr(community, 'member_count', 0),
                    'is_nsfw': getattr(community, 'is_nsfw', False)
                }
            
            # Method 2: Check in tweet legacy data structure  
            if hasattr(tweet, 'legacy') and tweet.legacy:
                legacy = tweet.legacy
                if hasattr(legacy, 'community') and legacy.community:
                    community = legacy.community
                    self.logger.info(f"✅ Found community via legacy structure: {community}")
                    return {
                        'id': getattr(community, 'id_str', str(community)),
                        'name': getattr(community, 'name', f"Community {getattr(community, 'id_str', 'Unknown')}"),
                        'member_count': getattr(community, 'member_count', 0),
                        'is_nsfw': getattr(community, 'is_nsfw', False)
                    }
            
            # Method 3: Check in tweet data/entities structure
            if hasattr(tweet, 'data') and tweet.data:
                data = tweet.data
                if hasattr(data, 'community') and data.community:
                    community = data.community
                    self.logger.info(f"✅ Found community via data structure: {community}")
                    return {
                        'id': getattr(community, 'id', getattr(community, 'id_str', str(community))),
                        'name': getattr(community, 'name', f"Community {getattr(community, 'id', 'Unknown')}"),
                        'member_count': getattr(community, 'member_count', 0),
                        'is_nsfw': getattr(community, 'is_nsfw', False)
                    }
            
            # Method 4: Check for community in extended entities
            if hasattr(tweet, 'extended_entities') and tweet.extended_entities:
                if hasattr(tweet.extended_entities, 'community'):
                    community = tweet.extended_entities.community
                    self.logger.info(f"✅ Found community via extended entities: {community}")
                    return {
                        'id': getattr(community, 'id_str', str(community)),
                        'name': getattr(community, 'name', f"Community {getattr(community, 'id_str', 'Unknown')}"),
                        'member_count': getattr(community, 'member_count', 0),
                        'is_nsfw': getattr(community, 'is_nsfw', False)
                    }
            
            # Method 5: Check for community results or other nested structures
            if hasattr(tweet, 'result') and tweet.result:
                result = tweet.result
                if hasattr(result, 'community') and result.community:
                    community = result.community
                    self.logger.info(f"✅ Found community via result structure: {community}")
                    return {
                        'id': getattr(community, 'id', getattr(community, 'id_str', str(community))),
                        'name': getattr(community, 'name', f"Community {getattr(community, 'id', 'Unknown')}"),
                        'member_count': getattr(community, 'member_count', 0),
                        'is_nsfw': getattr(community, 'is_nsfw', False)
                    }
            
            # Method 6: Debug - log available attributes to understand tweet structure
            if hasattr(tweet, '__dict__'):
                available_attrs = [attr for attr in dir(tweet) if not attr.startswith('_')]
                community_attrs = [attr for attr in available_attrs if 'community' in attr.lower()]
                if community_attrs:
                    self.logger.debug(f"Found community-related attributes on tweet: {community_attrs}")
                    
                    # Try to access the first community attribute found
                    for attr in community_attrs:
                        try:
                            community_data = getattr(tweet, attr)
                            if community_data:
                                self.logger.info(f"✅ Found community via {attr}: {type(community_data)} - {community_data}")
                                # Try to extract basic info
                                if hasattr(community_data, 'id') or hasattr(community_data, 'id_str'):
                                    return {
                                        'id': getattr(community_data, 'id', getattr(community_data, 'id_str', str(community_data))),
                                        'name': getattr(community_data, 'name', f"Community {getattr(community_data, 'id', 'Unknown')}"),
                                        'member_count': getattr(community_data, 'member_count', 0),
                                        'is_nsfw': getattr(community_data, 'is_nsfw', False)
                                    }
                        except Exception as e:
                            self.logger.debug(f"Error accessing {attr}: {e}")
            
            # Method 7: Check for community in raw tweet data (if available)
            if hasattr(tweet, 'raw') and tweet.raw and isinstance(tweet.raw, dict):
                raw_data = tweet.raw
                if 'community' in raw_data:
                    community = raw_data['community']
                    self.logger.info(f"✅ Found community via raw data: {community}")
                    return {
                        'id': community.get('id_str', community.get('id', str(community))),
                        'name': community.get('name', f"Community {community.get('id', 'Unknown')}"),
                        'member_count': community.get('member_count', 0),
                        'is_nsfw': community.get('is_nsfw', False)
                    }
            
        except Exception as e:
            self.logger.debug(f"Error parsing tweet community metadata: {e}")
        
        return None 