#!/usr/bin/env python3
"""
Community Activity Analysis Module

Advanced analysis methods for detecting community involvement through:
- Activity pattern analysis
- Content theme analysis
- Engagement pattern monitoring
- Behavioral change detection
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, Counter
from twscrape import API
from bot.models import Community
from bot.cookie_manager import CookieManager


class CommunityAnalyzer:
    """Advanced community activity and pattern analysis"""
    
    def __init__(self, api: API, cookie_manager: CookieManager):
        self.api = api
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
    
    async def detect_via_activity_patterns(self, user_id: int) -> List[Community]:
        """
        Detect community involvement through activity pattern analysis
        """
        communities = []
        
        try:
            self.logger.info(f"🧠 Analyzing activity patterns for community detection for user {user_id}")
            
            # Get recent tweets for analysis
            tweets = []
            tweet_count = 0
            async for tweet in self.api.user_tweets(user_id, limit=200):
                tweets.append(tweet)
                tweet_count += 1
                if tweet_count >= 200:
                    break
            
            if not tweets:
                self.logger.info("No tweets available for activity pattern analysis")
                return communities
            
            # Analyze patterns in tweets
            patterns = self._analyze_activity_patterns(tweets)
            
            # Convert patterns to community objects
            for pattern_type, pattern_data in patterns.items():
                if pattern_type == "hashtag_communities":
                    for hashtag, frequency in pattern_data.items():
                        if frequency >= 3:  # Threshold for community involvement
                            community = Community(
                                id=f"hashtag_{hashtag}",
                                name=f"#{hashtag} Community",
                                description=f"Community identified through hashtag usage (frequency: {frequency})",
                                member_count=0,
                                is_nsfw=False,
                                theme="hashtag_based",
                                created_at=None,
                                admin_id="",
                                role="Member",
                                joined_at=None
                            )
                            communities.append(community)
                
                elif pattern_type == "mention_communities":
                    for mention, frequency in pattern_data.items():
                        if frequency >= 2:  # Lower threshold for mentions
                            community = Community(
                                id=f"mention_{mention}",
                                name=f"@{mention} Community",
                                description=f"Community identified through frequent mentions (frequency: {frequency})",
                                member_count=0,
                                is_nsfw=False,
                                theme="mention_based",
                                created_at=None,
                                admin_id="",
                                role="Member",
                                joined_at=None
                            )
                            communities.append(community)
            
            self.logger.info(f"📊 Activity pattern analysis identified {len(communities)} potential communities")
            
        except Exception as e:
            self.logger.error(f"Error in activity pattern analysis: {e}")
        
        return communities
    
    def _analyze_activity_patterns(self, tweets) -> Dict[str, Dict[str, int]]:
        """
        Analyze tweets for activity patterns that indicate community involvement
        """
        patterns = {
            "hashtag_communities": defaultdict(int),
            "mention_communities": defaultdict(int),
            "reply_patterns": defaultdict(int),
            "quote_patterns": defaultdict(int)
        }
        
        try:
            community_hashtags = [
                'dao', 'defi', 'nft', 'web3', 'crypto', 'blockchain',
                'community', 'builders', 'devs', 'creators', 'collective'
            ]
            
            for tweet in tweets:
                try:
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    
                    # Analyze hashtags
                    hashtags = re.findall(r'#(\w+)', tweet_text.lower())
                    for hashtag in hashtags:
                        if any(keyword in hashtag for keyword in community_hashtags):
                            patterns["hashtag_communities"][hashtag] += 1
                    
                    # Analyze mentions
                    mentions = re.findall(r'@(\w+)', tweet_text.lower())
                    for mention in mentions:
                        # Filter for potential community accounts
                        if any(keyword in mention for keyword in community_hashtags):
                            patterns["mention_communities"][mention] += 1
                    
                    # Analyze reply patterns
                    if hasattr(tweet, 'inReplyToUser') and tweet.inReplyToUser:
                        reply_user = tweet.inReplyToUser.username.lower()
                        patterns["reply_patterns"][reply_user] += 1
                    
                    # Analyze quote tweet patterns
                    if hasattr(tweet, 'quotedTweet') and tweet.quotedTweet:
                        quoted_user = getattr(tweet.quotedTweet.user, 'username', '').lower()
                        if quoted_user:
                            patterns["quote_patterns"][quoted_user] += 1
                
                except Exception as e:
                    self.logger.debug(f"Error analyzing tweet for patterns: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error in pattern analysis: {e}")
        
        return patterns
    
    async def detect_via_content_analysis(self, user_id: int) -> List[Community]:
        """
        Detect community involvement through content theme analysis
        """
        communities = []
        
        try:
            self.logger.info(f"📝 Analyzing content themes for community detection for user {user_id}")
            
            # Get recent tweets for content analysis
            tweets = []
            tweet_count = 0
            async for tweet in self.api.user_tweets(user_id, limit=100):
                tweets.append(tweet)
                tweet_count += 1
                if tweet_count >= 100:
                    break
            
            if not tweets:
                return communities
            
            # Analyze content themes
            themes = self._analyze_content_themes(tweets)
            
            # Convert themes to community indicators
            for theme, keywords in themes.items():
                if len(keywords) >= 5:  # Threshold for theme consistency
                    community = Community(
                        id=f"theme_{theme}",
                        name=f"{theme.title()} Community",
                        description=f"Community identified through content themes: {', '.join(keywords[:3])}...",
                        member_count=0,
                        is_nsfw=False,
                        theme="content_based",
                        created_at=None,
                        admin_id="",
                        role="Member",
                        joined_at=None
                    )
                    communities.append(community)
            
            self.logger.info(f"📊 Content analysis identified {len(communities)} thematic communities")
            
        except Exception as e:
            self.logger.error(f"Error in content analysis: {e}")
        
        return communities
    
    def _analyze_content_themes(self, tweets) -> Dict[str, List[str]]:
        """
        Analyze tweet content to identify consistent themes that suggest community involvement
        """
        themes = defaultdict(list)
        
        try:
            # Define theme keywords
            theme_keywords = {
                'crypto': ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'defi', 'yield', 'staking'],
                'nft': ['nft', 'opensea', 'pfp', 'collection', 'mint', 'whitelist', 'drop'],
                'web3': ['web3', 'dapp', 'protocol', 'smart contract', 'metamask', 'wallet'],
                'dao': ['dao', 'governance', 'proposal', 'voting', 'treasury', 'collective'],
                'gaming': ['gaming', 'play2earn', 'p2e', 'guild', 'metaverse', 'gamefi'],
                'ai': ['ai', 'artificial intelligence', 'machine learning', 'gpt', 'llm'],
                'startup': ['startup', 'founder', 'entrepreneurship', 'vc', 'funding', 'pitch']
            }
            
            for tweet in tweets:
                try:
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    tweet_text_lower = tweet_text.lower()
                    
                    # Check each theme
                    for theme, keywords in theme_keywords.items():
                        for keyword in keywords:
                            if keyword in tweet_text_lower:
                                themes[theme].append(keyword)
                
                except Exception as e:
                    self.logger.debug(f"Error analyzing tweet content: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error in theme analysis: {e}")
        
        return themes
    
    async def analyze_for_new_community_patterns(self, tweets, previous_communities: List[Community]) -> List[Community]:
        """
        Analyze recent tweets for patterns indicating new community involvement
        """
        new_communities = []
        
        try:
            # Get existing community names for comparison
            existing_names = {c.name.lower() for c in previous_communities}
            
            # Analyze tweets for community-related activities
            for tweet in tweets:
                try:
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    tweet_date = getattr(tweet, 'date', datetime.now())
                    
                    # Look for joining patterns
                    joining_patterns = [
                        r'joined\s+(?:the\s+)?(\w+(?:\s+\w+)*)\s+community',
                        r'excited\s+to\s+join\s+(\w+(?:\s+\w+)*)',
                        r'new\s+member\s+of\s+(\w+(?:\s+\w+)*)',
                        r'welcome\s+to\s+(\w+(?:\s+\w+)*)\s+community'
                    ]
                    
                    for pattern in joining_patterns:
                        matches = re.findall(pattern, tweet_text.lower())
                        for match in matches:
                            community_name = match.strip()
                            if community_name and community_name not in existing_names:
                                community = Community(
                                    id=f"new_join_{hash(community_name)}",
                                    name=community_name.title(),
                                    description=f"Recently joined community detected from tweet",
                                    member_count=0,
                                    is_nsfw=False,
                                    theme="recent_join",
                                    created_at=None,
                                    admin_id="",
                                    role="Member",
                                    joined_at=tweet_date
                                )
                                new_communities.append(community)
                
                except Exception as e:
                    self.logger.debug(f"Error analyzing tweet for new patterns: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error analyzing for new community patterns: {e}")
        
        return new_communities
    
    async def analyze_engagement_patterns_for_communities(self, tweets, user_id: int) -> List[Community]:
        """
        Analyze engagement patterns to identify community involvement
        """
        communities = []
        
        try:
            engagement_data = defaultdict(lambda: {
                'replies': 0,
                'quotes': 0,
                'mentions': 0,
                'hashtags': set()
            })
            
            for tweet in tweets:
                try:
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    
                    # Track replies to specific users
                    if hasattr(tweet, 'inReplyToUser') and tweet.inReplyToUser:
                        target_user = tweet.inReplyToUser.username.lower()
                        engagement_data[target_user]['replies'] += 1
                    
                    # Track mentions
                    mentions = re.findall(r'@(\w+)', tweet_text.lower())
                    for mention in mentions:
                        engagement_data[mention]['mentions'] += 1
                    
                    # Track hashtags
                    hashtags = re.findall(r'#(\w+)', tweet_text.lower())
                    for hashtag in hashtags:
                        for user_key in engagement_data.keys():
                            engagement_data[user_key]['hashtags'].add(hashtag)
                
                except Exception as e:
                    self.logger.debug(f"Error analyzing engagement patterns: {e}")
                    continue
            
            # Convert high-engagement accounts to community indicators
            for account, data in engagement_data.items():
                total_engagement = data['replies'] + data['quotes'] + data['mentions']
                if total_engagement >= 3:  # Threshold for significant engagement
                    community = Community(
                        id=f"engagement_{account}",
                        name=f"{account.title()} Community",
                        description=f"High engagement community (replies: {data['replies']}, mentions: {data['mentions']})",
                        member_count=0,
                        is_nsfw=False,
                        theme="engagement_based",
                        created_at=None,
                        admin_id="",
                        role="Member",
                        joined_at=None
                    )
                    communities.append(community)
        
        except Exception as e:
            self.logger.error(f"Error analyzing engagement patterns: {e}")
        
        return communities
    
    async def detect_communities_via_enhanced_activity(self, username: str, previous_communities: List[Community]) -> List[Community]:
        """
        Enhanced activity-based community detection using multiple signals
        """
        communities = []
        
        try:
            # Get user data
            user = await self.api.user_by_login(username)
            if not user:
                return communities
            
            self.logger.info(f"🔍 Enhanced activity analysis for @{username}")
            
            # Get recent tweets for comprehensive analysis
            tweets = []
            tweet_count = 0
            async for tweet in self.api.user_tweets(user.id, limit=200):
                tweets.append(tweet)
                tweet_count += 1
                if tweet_count >= 200:
                    break
            
            if not tweets:
                return communities
            
            # Multiple analysis methods
            analysis_methods = [
                self.analyze_for_new_community_patterns(tweets, previous_communities),
                self.analyze_engagement_patterns_for_communities(tweets, user.id),
                self._analyze_temporal_patterns(tweets),
                self._analyze_conversation_threads(tweets)
            ]
            
            # Run all analyses
            results = await asyncio.gather(*analysis_methods, return_exceptions=True)
            
            # Collect all results
            for result in results:
                if isinstance(result, list):
                    communities.extend(result)
                elif isinstance(result, Exception):
                    self.logger.debug(f"Analysis method failed: {result}")
            
            # Remove duplicates
            unique_communities = []
            seen_ids = set()
            for community in communities:
                if community.id not in seen_ids:
                    unique_communities.append(community)
                    seen_ids.add(community.id)
            
            self.logger.info(f"📊 Enhanced activity analysis found {len(unique_communities)} communities")
            
            return unique_communities
        
        except Exception as e:
            self.logger.error(f"Error in enhanced activity analysis: {e}")
            return communities
    
    async def _analyze_temporal_patterns(self, tweets) -> List[Community]:
        """
        Analyze temporal patterns in posting to identify community events
        """
        communities = []
        
        try:
            # Group tweets by day and analyze for event patterns
            daily_activity = defaultdict(list)
            
            for tweet in tweets:
                try:
                    tweet_date = getattr(tweet, 'date', datetime.now())
                    day_key = tweet_date.strftime('%Y-%m-%d')
                    daily_activity[day_key].append(tweet)
                except Exception as e:
                    self.logger.debug(f"Error processing tweet date: {e}")
            
            # Look for burst activity days (potential community events)
            avg_daily_tweets = sum(len(tweets) for tweets in daily_activity.values()) / len(daily_activity) if daily_activity else 0
            
            for day, day_tweets in daily_activity.items():
                if len(day_tweets) > avg_daily_tweets * 2:  # Burst activity
                    # Analyze what caused the burst
                    burst_themes = self._analyze_content_themes(day_tweets)
                    
                    for theme, keywords in burst_themes.items():
                        if len(keywords) >= 3:
                            community = Community(
                                id=f"burst_{theme}_{day}",
                                name=f"{theme.title()} Event Community",
                                description=f"Community activity burst on {day}",
                                member_count=0,
                                is_nsfw=False,
                                theme="temporal_burst",
                                created_at=datetime.strptime(day, '%Y-%m-%d'),
                                admin_id="",
                                role="Member",
                                joined_at=None
                            )
                            communities.append(community)
        
        except Exception as e:
            self.logger.debug(f"Error in temporal analysis: {e}")
        
        return communities
    
    async def _analyze_conversation_threads(self, tweets) -> List[Community]:
        """
        Analyze conversation threads to identify community discussions
        """
        communities = []
        
        try:
            # Group tweets by conversation/reply chains
            conversations = defaultdict(list)
            
            for tweet in tweets:
                try:
                    if hasattr(tweet, 'conversationId') and tweet.conversationId:
                        conversations[tweet.conversationId].append(tweet)
                    elif hasattr(tweet, 'inReplyToUser') and tweet.inReplyToUser:
                        # Group by reply target if no conversation ID
                        reply_key = f"reply_{tweet.inReplyToUser.username}"
                        conversations[reply_key].append(tweet)
                except Exception as e:
                    self.logger.debug(f"Error grouping conversation: {e}")
            
            # Analyze conversations for community indicators
            for conv_id, conv_tweets in conversations.items():
                if len(conv_tweets) >= 3:  # Meaningful conversation
                    # Analyze themes in the conversation
                    conv_themes = self._analyze_content_themes(conv_tweets)
                    
                    for theme, keywords in conv_themes.items():
                        if len(keywords) >= 2:
                            community = Community(
                                id=f"conversation_{theme}_{hash(conv_id)}",
                                name=f"{theme.title()} Discussion Community",
                                description=f"Community identified through conversation analysis",
                                member_count=0,
                                is_nsfw=False,
                                theme="conversation_based",
                                created_at=None,
                                admin_id="",
                                role="Member",
                                joined_at=None
                            )
                            communities.append(community)
        
        except Exception as e:
            self.logger.debug(f"Error in conversation analysis: {e}")
        
        return communities 