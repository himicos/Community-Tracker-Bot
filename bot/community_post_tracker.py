#!/usr/bin/env python3
"""
Community Post Tracker Module

This module implements tracking of community creation and membership changes
by monitoring posts made to communities and analyzing activity patterns.

Since direct GraphQL endpoints for communities are limited, this approach
tracks community activity through:
1. Posts made to community hashtags/mentions
2. Community URLs shared in tweets
3. Reply patterns to community accounts
4. Timeline analysis for community content
5. Activity pattern changes indicating new memberships

This provides a reliable fallback method when direct API access is limited.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
import json
from collections import defaultdict

from twscrape import API
from bot.models import Community, TwitterUserCommunityPayload
from bot.cookie_manager import CookieManager


class CommunityPostTracker:
    """Advanced community tracking through post and activity analysis"""
    
    def __init__(self, api: API, cookie_manager: CookieManager):
        self.api = api
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
        
        # Community detection patterns
        self.community_indicators = {
            'creation': [
                r'(?:created|launched|founded|started)\s+(?:a\s+)?(?:new\s+)?community',
                r'(?:proud to announce|excited to share|introducing)\s+.*community',
                r'(?:welcome to|join us at|check out)\s+.*community',
                r'community.*(?:is live|now open|officially launched)',
                r'founding\s+(?:members|team).*community'
            ],
            'joining': [
                r'(?:joined|became part of|now member of)\s+.*community',
                r'(?:happy|excited|thrilled)\s+to join.*community',
                r'welcome.*new members.*community',
                r'(?:onboarding|welcoming).*community',
                r'community.*(?:accepted|invited|approved)'
            ],
            'community_urls': [
                r'(?:twitter\.com|x\.com)/i/communities/(\d+)',
                r'communities/(\d+)',
                r't\.co/\w+'  # Shortened URLs that might lead to communities
            ],
            'community_hashtags': [
                r'#\w*community\w*',
                r'#\w*group\w*',
                r'#\w*collective\w*',
                r'#\w*guild\w*',
                r'#\w*dao\w*',
                r'#\w*club\w*'
            ]
        }
        
        # Activity patterns that suggest community participation
        self.activity_patterns = {
            'high_engagement': 3,  # Replies per hour threshold
            'community_mentions': 2,  # Community account mentions
            'hashtag_usage': 5,  # Community hashtags per day
            'url_sharing': 1  # Community URLs shared
        }
        
        self.logger.info("CommunityPostTracker initialized with advanced pattern detection")
    
    async def track_community_changes_via_posts(self, username: str, previous_communities: List[Community], 
                                               hours_lookback: int = 24) -> Dict[str, Any]:
        """
        Track community changes by analyzing posts and activity patterns
        
        Args:
            username: Target Twitter username
            previous_communities: Previously known communities
            hours_lookback: How many hours back to analyze
            
        Returns:
            Dictionary with detected changes
        """
        self.logger.info(f"🔍 Tracking community changes via post analysis for @{username}")
        
        result = {
            'joined': [],
            'left': [],
            'created': [],
            'activity_changes': [],
            'confidence_scores': {},
            'method': 'post_analysis',
            'hours_analyzed': hours_lookback,
            'error': None
        }
        
        try:
            # Get user data
            user = await self.api.user_by_login(username)
            if not user:
                result['error'] = f"User @{username} not found"
                return result
            
            # Analyze recent posts for community activity
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
            
            # Get recent tweets
            recent_tweets = await self._get_recent_tweets(user.id, cutoff_time)
            self.logger.info(f"📊 Analyzing {len(recent_tweets)} recent tweets from @{username}")
            
            # Analyze tweets for community indicators
            creation_indicators = await self._detect_community_creation(recent_tweets, user.id)
            joining_indicators = await self._detect_community_joining(recent_tweets, user.id)
            activity_changes = await self._detect_activity_changes(recent_tweets, previous_communities)
            
            # Process creation indicators
            for indicator in creation_indicators:
                community = await self._create_community_from_indicator(indicator, "Created")
                if community:
                    result['created'].append(community)
                    result['confidence_scores'][community.id] = indicator.get('confidence', 0.5)
            
            # Process joining indicators
            for indicator in joining_indicators:
                community = await self._create_community_from_indicator(indicator, "Member")
                if community:
                    # Check if this is actually a new community or existing
                    if not self._is_known_community(community, previous_communities):
                        result['joined'].append(community)
                        result['confidence_scores'][community.id] = indicator.get('confidence', 0.5)
            
            # Detect communities that user may have left (reduced activity)
            left_communities = await self._detect_left_communities(
                previous_communities, recent_tweets, hours_lookback
            )
            result['left'].extend(left_communities)
            
            # Add activity changes
            result['activity_changes'] = activity_changes
            
            self.logger.info(f"📈 Post analysis results for @{username}: "
                           f"created={len(result['created'])}, "
                           f"joined={len(result['joined'])}, "
                           f"left={len(result['left'])}")
            
        except Exception as e:
            self.logger.error(f"Error in post-based tracking for @{username}: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _get_recent_tweets(self, user_id: int, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Get recent tweets since cutoff time"""
        tweets = []
        count = 0
        
        try:
            async for tweet in self.api.user_tweets(user_id, limit=200):
                count += 1
                
                # Convert tweet to dictionary for easier processing
                tweet_data = {
                    'id': tweet.id,
                    'content': tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet),
                    'created_at': tweet.date if hasattr(tweet, 'date') else datetime.now(),
                    'replies': getattr(tweet, 'replyCount', 0),
                    'retweets': getattr(tweet, 'retweetCount', 0),
                    'likes': getattr(tweet, 'likeCount', 0),
                    'urls': getattr(tweet, 'urls', []),
                    'hashtags': getattr(tweet, 'hashtags', []),
                    'mentions': getattr(tweet, 'mentions', [])
                }
                
                # Check if tweet is within our time window
                if tweet_data['created_at'] >= cutoff_time:
                    tweets.append(tweet_data)
                else:
                    # Stop if we've gone beyond our time window
                    break
                
                # Safety limit
                if count >= 200:
                    break
        
        except Exception as e:
            self.logger.error(f"Error getting recent tweets: {e}")
        
        return tweets
    
    async def _detect_community_creation(self, tweets: List[Dict[str, Any]], user_id: int) -> List[Dict[str, Any]]:
        """Detect community creation indicators in tweets"""
        creation_indicators = []
        
        for tweet in tweets:
            content = tweet['content'].lower()
            
            # Check for creation patterns
            for pattern in self.community_indicators['creation']:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Extract community name context
                    community_context = self._extract_community_context(content, match.group())
                    
                    if community_context:
                        confidence = self._calculate_creation_confidence(tweet, match.group())
                        
                        indicator = {
                            'type': 'creation',
                            'pattern': pattern,
                            'content': community_context,
                            'tweet_id': tweet['id'],
                            'confidence': confidence,
                            'engagement': tweet['replies'] + tweet['retweets'] + tweet['likes'],
                            'timestamp': tweet['created_at']
                        }
                        creation_indicators.append(indicator)
                        
                        self.logger.info(f"🆕 Detected community creation: {community_context} "
                                       f"(confidence: {confidence:.2f})")
        
        return creation_indicators
    
    async def _detect_community_joining(self, tweets: List[Dict[str, Any]], user_id: int) -> List[Dict[str, Any]]:
        """Detect community joining indicators in tweets"""
        joining_indicators = []
        
        for tweet in tweets:
            content = tweet['content'].lower()
            
            # Check for joining patterns
            for pattern in self.community_indicators['joining']:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    community_context = self._extract_community_context(content, match.group())
                    
                    if community_context:
                        confidence = self._calculate_joining_confidence(tweet, match.group())
                        
                        indicator = {
                            'type': 'joining',
                            'pattern': pattern,
                            'content': community_context,
                            'tweet_id': tweet['id'],
                            'confidence': confidence,
                            'engagement': tweet['replies'] + tweet['retweets'] + tweet['likes'],
                            'timestamp': tweet['created_at']
                        }
                        joining_indicators.append(indicator)
                        
                        self.logger.info(f"✅ Detected community joining: {community_context} "
                                       f"(confidence: {confidence:.2f})")
            
            # Check for community URLs
            for url_pattern in self.community_indicators['community_urls']:
                url_matches = re.finditer(url_pattern, content)
                for url_match in url_matches:
                    if url_pattern == r't\.co/\w+':
                        # For t.co URLs, we'd need to expand them
                        community_id = f"tco_{url_match.group()}"
                        community_name = f"Community via {url_match.group()}"
                    else:
                        # Direct community URL
                        community_id = url_match.group(1) if len(url_match.groups()) > 0 else url_match.group()
                        community_name = f"Twitter Community {community_id}"
                    
                    confidence = 0.8  # High confidence for direct URLs
                    
                    indicator = {
                        'type': 'url_sharing',
                        'pattern': url_pattern,
                        'content': community_name,
                        'community_id': community_id,
                        'tweet_id': tweet['id'],
                        'confidence': confidence,
                        'engagement': tweet['replies'] + tweet['retweets'] + tweet['likes'],
                        'timestamp': tweet['created_at']
                    }
                    joining_indicators.append(indicator)
                    
                    self.logger.info(f"🔗 Detected community URL: {community_name} "
                                   f"(confidence: {confidence:.2f})")
        
        return joining_indicators
    
    async def _detect_activity_changes(self, tweets: List[Dict[str, Any]], 
                                     previous_communities: List[Community]) -> List[Dict[str, Any]]:
        """Detect activity pattern changes that might indicate community changes"""
        activity_changes = []
        
        # Analyze hashtag usage patterns
        hashtag_analysis = self._analyze_hashtag_patterns(tweets)
        
        # Analyze mention patterns
        mention_analysis = self._analyze_mention_patterns(tweets)
        
        # Analyze engagement patterns
        engagement_analysis = self._analyze_engagement_patterns(tweets)
        
        # Compare with known communities
        for community in previous_communities:
            community_activity = self._get_community_activity_score(
                tweets, community, hashtag_analysis, mention_analysis
            )
            
            if community_activity['score'] < 0.3:  # Low activity threshold
                activity_changes.append({
                    'type': 'reduced_activity',
                    'community': community.name,
                    'score': community_activity['score'],
                    'indicators': community_activity['indicators']
                })
        
        return activity_changes
    
    async def _detect_left_communities(self, previous_communities: List[Community], 
                                     recent_tweets: List[Dict[str, Any]], 
                                     hours_lookback: int) -> List[Community]:
        """Detect communities the user may have left based on reduced activity"""
        left_communities = []
        
        for community in previous_communities:
            # Calculate activity score for this community
            activity_score = self._calculate_community_activity_score(recent_tweets, community)
            
            # If activity is very low, user might have left
            if activity_score < 0.2:  # Threshold for "left"
                # Additional checks
                mentions_community = any(
                    community.name.lower() in tweet['content'].lower() 
                    for tweet in recent_tweets
                )
                
                # If no mentions and low activity, likely left
                if not mentions_community:
                    self.logger.info(f"❌ Detected potential departure: {community.name} "
                                   f"(activity score: {activity_score:.2f})")
                    left_communities.append(community)
        
        return left_communities
    
    def _extract_community_context(self, content: str, match_text: str) -> Optional[str]:
        """Extract community name/context from surrounding text"""
        # Find the position of the match
        match_pos = content.find(match_text.lower())
        if match_pos == -1:
            return None
        
        # Extract surrounding context
        start = max(0, match_pos - 50)
        end = min(len(content), match_pos + len(match_text) + 50)
        context = content[start:end]
        
        # Look for potential community names
        # Pattern 1: "community called/named X"
        named_pattern = r'(?:community\s+(?:called|named|known as)\s+)(["\']?)([^"\'\s,\.!?]+)\1'
        named_match = re.search(named_pattern, context, re.IGNORECASE)
        if named_match:
            return named_match.group(2).strip()
        
        # Pattern 2: "X community"
        before_pattern = r'([A-Za-z][A-Za-z0-9\s]{2,20})\s+community'
        before_match = re.search(before_pattern, context, re.IGNORECASE)
        if before_match:
            return before_match.group(1).strip()
        
        # Pattern 3: Look for hashtags near the match
        hashtag_pattern = r'#([A-Za-z][A-Za-z0-9_]{2,30})'
        hashtags = re.findall(hashtag_pattern, context)
        if hashtags:
            return hashtags[0]  # Return first relevant hashtag
        
        # Pattern 4: Look for quoted text
        quote_pattern = r'["\']([^"\']{3,30})["\']'
        quote_match = re.search(quote_pattern, context)
        if quote_match:
            return quote_match.group(1)
        
        # Pattern 5: Capitalized words near community
        cap_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        cap_matches = re.findall(cap_pattern, context)
        for cap_match in cap_matches:
            if cap_match.lower() not in ['community', 'the', 'a', 'an', 'new', 'this']:
                return cap_match
        
        return None
    
    def _calculate_creation_confidence(self, tweet: Dict[str, Any], match_text: str) -> float:
        """Calculate confidence score for community creation detection"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for certain keywords
        high_confidence_words = ['created', 'launched', 'founded', 'started', 'announcing']
        if any(word in match_text.lower() for word in high_confidence_words):
            confidence += 0.2
        
        # Higher confidence for higher engagement
        total_engagement = tweet['replies'] + tweet['retweets'] + tweet['likes']
        if total_engagement > 10:
            confidence += 0.1
        if total_engagement > 50:
            confidence += 0.1
        
        # Higher confidence for recent tweets
        if tweet['created_at'] > datetime.now() - timedelta(hours=6):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_joining_confidence(self, tweet: Dict[str, Any], match_text: str) -> float:
        """Calculate confidence score for community joining detection"""
        confidence = 0.4  # Base confidence (slightly lower than creation)
        
        # Higher confidence for certain keywords
        high_confidence_words = ['joined', 'member', 'accepted', 'approved']
        if any(word in match_text.lower() for word in high_confidence_words):
            confidence += 0.2
        
        # Higher confidence for engagement
        total_engagement = tweet['replies'] + tweet['retweets'] + tweet['likes']
        if total_engagement > 5:
            confidence += 0.1
        if total_engagement > 25:
            confidence += 0.1
        
        # Higher confidence for recent activity
        if tweet['created_at'] > datetime.now() - timedelta(hours=12):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _analyze_hashtag_patterns(self, tweets: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze hashtag usage patterns"""
        hashtag_counts = defaultdict(int)
        
        for tweet in tweets:
            content = tweet['content'].lower()
            hashtags = re.findall(r'#(\w+)', content)
            
            for hashtag in hashtags:
                # Filter for community-related hashtags
                if any(keyword in hashtag for keyword in ['community', 'group', 'dao', 'club', 'collective']):
                    hashtag_counts[hashtag] += 1
        
        return dict(hashtag_counts)
    
    def _analyze_mention_patterns(self, tweets: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze mention patterns for community accounts"""
        mention_counts = defaultdict(int)
        
        for tweet in tweets:
            content = tweet['content']
            mentions = re.findall(r'@(\w+)', content)
            
            for mention in mentions:
                # Check if mention looks like a community account
                mention_lower = mention.lower()
                if any(keyword in mention_lower for keyword in ['community', 'dao', 'collective', 'group']):
                    mention_counts[mention] += 1
        
        return dict(mention_counts)
    
    def _analyze_engagement_patterns(self, tweets: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze engagement patterns"""
        if not tweets:
            return {}
        
        total_tweets = len(tweets)
        total_engagement = sum(t['replies'] + t['retweets'] + t['likes'] for t in tweets)
        avg_engagement = total_engagement / total_tweets if total_tweets > 0 else 0
        
        # Calculate engagement over time
        recent_tweets = [t for t in tweets if t['created_at'] > datetime.now() - timedelta(hours=12)]
        recent_engagement = sum(t['replies'] + t['retweets'] + t['likes'] for t in recent_tweets)
        recent_avg = recent_engagement / len(recent_tweets) if recent_tweets else 0
        
        return {
            'average_engagement': avg_engagement,
            'recent_engagement': recent_avg,
            'engagement_trend': recent_avg / avg_engagement if avg_engagement > 0 else 1.0,
            'tweet_frequency': len(recent_tweets) / 12  # Tweets per hour in last 12 hours
        }
    
    def _get_community_activity_score(self, tweets: List[Dict[str, Any]], community: Community,
                                    hashtag_analysis: Dict[str, int], 
                                    mention_analysis: Dict[str, int]) -> Dict[str, Any]:
        """Calculate activity score for a specific community"""
        score = 0.0
        indicators = []
        
        community_name_lower = community.name.lower()
        
        # Check for direct mentions of community name
        name_mentions = sum(1 for tweet in tweets if community_name_lower in tweet['content'].lower())
        if name_mentions > 0:
            score += 0.4
            indicators.append(f"Direct mentions: {name_mentions}")
        
        # Check for related hashtags
        related_hashtags = [ht for ht in hashtag_analysis if community_name_lower in ht.lower()]
        if related_hashtags:
            score += 0.3
            indicators.append(f"Related hashtags: {len(related_hashtags)}")
        
        # Check for community account mentions
        community_handle = f"@{community_name_lower.replace(' ', '').replace('-', '')}"
        handle_mentions = mention_analysis.get(community_handle.replace('@', ''), 0)
        if handle_mentions > 0:
            score += 0.3
            indicators.append(f"Handle mentions: {handle_mentions}")
        
        return {
            'score': min(score, 1.0),
            'indicators': indicators
        }
    
    def _calculate_community_activity_score(self, tweets: List[Dict[str, Any]], 
                                          community: Community) -> float:
        """Calculate activity score for community to detect if user left"""
        score = 0.0
        community_name_lower = community.name.lower()
        
        # Count mentions and references
        mentions = 0
        for tweet in tweets:
            content_lower = tweet['content'].lower()
            if community_name_lower in content_lower:
                mentions += 1
        
        # Normalize by number of tweets
        if tweets:
            score = mentions / len(tweets)
        
        return score
    
    async def _create_community_from_indicator(self, indicator: Dict[str, Any], default_role: str) -> Optional[Community]:
        """Create a Community object from a detected indicator"""
        try:
            community_name = indicator.get('content', 'Unknown Community')
            
            # Generate a deterministic ID based on the community name
            community_id = f"post_{abs(hash(community_name.lower())) % 1000000}"
            
            # Use community_id from indicator if available (for URL-based detection)
            if 'community_id' in indicator:
                community_id = f"twitter_{indicator['community_id']}"
            
            community = Community(
                id=community_id,
                name=community_name,
                role=default_role,
                member_count=None,
                description=f"Detected via {indicator['type']} pattern",
                created_at=indicator.get('timestamp', datetime.now()),
                is_private=None
            )
            
            return community
            
        except Exception as e:
            self.logger.error(f"Error creating community from indicator: {e}")
            return None
    
    def _is_known_community(self, community: Community, known_communities: List[Community]) -> bool:
        """Check if a community is already in the known list"""
        for known in known_communities:
            # Match by ID
            if community.id == known.id:
                return True
            
            # Match by name (case-insensitive)
            if community.name.lower() == known.name.lower():
                return True
        
        return False
    
    async def monitor_community_posts_continuous(self, username: str, callback_func, 
                                               check_interval_minutes: int = 15) -> None:
        """
        Continuously monitor for community changes via post analysis
        
        Args:
            username: Target username to monitor
            callback_func: Function to call when changes are detected
            check_interval_minutes: How often to check for changes
        """
        self.logger.info(f"🔄 Starting continuous community post monitoring for @{username}")
        
        previous_communities = []
        
        while True:
            try:
                # Check for changes
                changes = await self.track_community_changes_via_posts(
                    username, previous_communities, hours_lookback=check_interval_minutes/60*2
                )
                
                # If we found changes, call the callback
                if (changes['joined'] or changes['left'] or changes['created']) and not changes['error']:
                    await callback_func(username, changes)
                    
                    # Update our tracking list
                    # Add new communities
                    previous_communities.extend(changes['joined'])
                    previous_communities.extend(changes['created'])
                    
                    # Remove left communities
                    left_ids = {c.id for c in changes['left']}
                    previous_communities = [c for c in previous_communities if c.id not in left_ids]
                
                # Wait for next check
                await asyncio.sleep(check_interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def detect_community_activities(self, user_id: int, hours_lookback: int = 24) -> List[Community]:
        """
        Detect community activities for a user (both creation and joining)
        This is the main method called by EnhancedCommunityTrackerV2
        
        Args:
            user_id: Twitter user ID
            hours_lookback: Hours to look back for activities
            
        Returns:
            List of detected communities with their activities
        """
        communities = []
        
        try:
            self.logger.info(f"🔍 Detecting community activities for user {user_id} (last {hours_lookback}h)")
            
            # Get user object for username lookup
            try:
                # We need to find a way to get the username from user_id
                # For now, we'll work with the user_id directly
                cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
                recent_tweets = await self._get_recent_tweets(user_id, cutoff_time)
                
                if not recent_tweets:
                    self.logger.info(f"No recent tweets found for user {user_id}")
                    return communities
                
                # Detect creation activities
                creation_indicators = await self._detect_community_creation(recent_tweets, user_id)
                for indicator in creation_indicators:
                    community = await self._create_community_from_indicator(indicator, "Creator")
                    if community:
                        communities.append(community)
                
                # Detect joining activities
                joining_indicators = await self._detect_community_joining(recent_tweets, user_id)
                for indicator in joining_indicators:
                    community = await self._create_community_from_indicator(indicator, "Member")
                    if community:
                        # Avoid duplicates
                        if not any(c.id == community.id for c in communities):
                            communities.append(community)
                
                self.logger.info(f"📊 Detected {len(communities)} community activities for user {user_id}")
                
            except Exception as e:
                self.logger.error(f"Error in activity detection for user {user_id}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error in detect_community_activities: {e}")
        
        return communities

    async def detect_community_creation(self, user_id: int, hours_lookback: int = 24) -> List[Community]:
        """
        Detect communities created by the user
        
        Args:
            user_id: Twitter user ID
            hours_lookback: Hours to look back
            
        Returns:
            List of communities the user created
        """
        communities = []
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
            recent_tweets = await self._get_recent_tweets(user_id, cutoff_time)
            
            creation_indicators = await self._detect_community_creation(recent_tweets, user_id)
            for indicator in creation_indicators:
                community = await self._create_community_from_indicator(indicator, "Creator")
                if community:
                    communities.append(community)
            
            self.logger.info(f"📊 Detected {len(communities)} community creations for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error detecting community creation: {e}")
        
        return communities

    async def detect_community_joining(self, user_id: int, hours_lookback: int = 24) -> List[Community]:
        """
        Detect communities joined by the user
        
        Args:
            user_id: Twitter user ID
            hours_lookback: Hours to look back
            
        Returns:
            List of communities the user joined
        """
        communities = []
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
            recent_tweets = await self._get_recent_tweets(user_id, cutoff_time)
            
            joining_indicators = await self._detect_community_joining(recent_tweets, user_id)
            for indicator in joining_indicators:
                community = await self._create_community_from_indicator(indicator, "Member")
                if community:
                    communities.append(community)
            
            self.logger.info(f"📊 Detected {len(communities)} community joins for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error detecting community joining: {e}")
        
        return communities 