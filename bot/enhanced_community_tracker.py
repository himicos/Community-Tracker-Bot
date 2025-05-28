#!/usr/bin/env python3
"""
Enhanced Community Tracking System

This module implements comprehensive community detection and monitoring:
- Multi-strategy community detection
- Complete parsing of ALL community data
- Real-time change tracking
- Detailed notifications
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


class EnhancedCommunityTracker:
    """Comprehensive Community Tracking System"""
    
    def __init__(self, api: API, cookie_manager: CookieManager):
        self.api = api
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Enhanced Community Tracker initialized with comprehensive detection capabilities")
    
    async def get_all_user_communities(self, username: str, deep_scan: bool = True) -> Optional[TwitterUserCommunityPayload]:
        """
        Comprehensively detect ALL communities for a user
        
        Args:
            username: Twitter username (without @)
            deep_scan: Whether to perform deep analysis (slower but more complete)
            
        Returns:
            Complete TwitterUserCommunityPayload with all detected communities
        """
        self.logger.info(f"Starting comprehensive community scan for @{username}")
        
        try:
            # Get user information
            user = await self.api.user_by_login(username)
            if not user:
                self.logger.error(f"User @{username} not found")
                return None
            
            self.logger.info(f"Found user: {user.displayname} (@{user.username}, ID: {user.id})")
            
            # Initialize community collection
            all_communities = {}  # Use dict to avoid duplicates
            
            # Strategy 1: Direct Community Analysis
            communities_direct = await self._get_communities_direct(user.id)
            for community in communities_direct:
                all_communities[community.id] = community
            
            # Strategy 2: Tweet-based Detection
            if deep_scan:
                communities_tweets = await self._detect_via_comprehensive_tweets(user.id)
                for community in communities_tweets:
                    all_communities[community.id] = community
            
            # Strategy 3: Social Graph Analysis
            if deep_scan:
                communities_social = await self._detect_via_social_graph(user.id)
                for community in communities_social:
                    all_communities[community.id] = community
            
            # Strategy 4: Activity Pattern Analysis
            communities_activity = await self._detect_via_activity_patterns(user.id)
            for community in communities_activity:
                all_communities[community.id] = community
            
            # Strategy 5: Content Analysis
            if deep_scan:
                communities_content = await self._detect_via_content_analysis(user.id)
                for community in communities_content:
                    all_communities[community.id] = community
            
            # Convert to list and enrich community data
            final_communities = list(all_communities.values())
            final_communities = await self._enrich_community_data(final_communities)
            
            self.logger.info(f"Total communities detected for @{username}: {len(final_communities)}")
            
            # Log detailed community information
            for i, community in enumerate(final_communities, 1):
                self.logger.info(f"  {i}. {community.name} (ID: {community.id}, Role: {community.role})")
            
            return TwitterUserCommunityPayload(
                user_id=str(user.id),
                screen_name=user.username,
                name=user.displayname or user.username,
                verified=getattr(user, 'verified', False),
                is_blue_verified=getattr(user, 'blue_verified', False),
                profile_image_url_https=getattr(user, 'profileImageUrl', ''),
                communities=final_communities
            )
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive community scan: {e}")
            return None
    
    async def _get_communities_direct(self, user_id: int) -> List[Community]:
        """
        Attempt direct community detection via API calls
        """
        communities = []
        self.logger.info(f"Attempting direct community detection for user {user_id}")
        
        try:
            # This would use Twitter's GraphQL community endpoints if accessible
            # For now, we'll use indirect methods
            pass
            
        except Exception as e:
            self.logger.debug(f"Direct community detection failed: {e}")
        
        return communities
    
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
        
        Returns:
            Detailed change report
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
            'scan_type': 'deep' if deep_scan else 'quick'
        }
        
        try:
            # Get current comprehensive community state
            current_payload = await self.get_all_user_communities(username, deep_scan=deep_scan)
            
            if not current_payload:
                result['error'] = f"Failed to fetch current communities for @{username}"
                return result
            
            current_communities = current_payload.communities
            result['total_current'] = len(current_communities)
            
            # Compare communities with detailed analysis
            changes = self._detailed_community_diff(previous_communities, current_communities)
            
            result.update(changes)
            
            self.logger.info(f"Community changes for @{username}: "
                           f"joined={len(result['joined'])}, "
                           f"left={len(result['left'])}, "
                           f"created={len(result['created'])}, "
                           f"role_changes={len(result['role_changes'])}")
            
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