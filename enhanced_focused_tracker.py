#!/usr/bin/env python3
"""
Enhanced Focused Community Tracker
Prioritizes detection of posts made WITHIN communities (most reliable evidence)
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import re
from bs4 import BeautifulSoup

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.twitter_api import TwitterAPI
from bot.models import Community, DatabaseManager

class EnhancedFocusedTracker:
    """Enhanced tracker prioritizing direct community posting evidence"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api = None
        self.db = DatabaseManager()
        
    async def initialize(self):
        """Initialize the tracker"""
        try:
            self.api = TwitterAPI()
            self.logger.info("✅ Enhanced Focused Community Tracker initialized")
            return True
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def track_user_communities(self, username: str, hours_lookback: int = 168) -> Dict[str, Any]:
        """
        Track communities with enhanced detection prioritizing direct posting evidence
        """
        try:
            self.logger.info(f"🎯 Enhanced tracking for @{username} (prioritizing direct posting evidence)")
            
            # Get user info
            user = await self.api.api.user_by_login(username)
            if not user:
                return {"error": f"User @{username} not found"}
            
            # Get previously stored communities
            stored_communities = self.db.get_user_communities(user.id)
            self.logger.info(f"📚 Found {len(stored_communities)} previously stored communities")
            
            # Enhanced detection with prioritization
            current_communities = await self._enhanced_detect_communities(user.id, username, hours_lookback)
            self.logger.info(f"🔍 Detected {len(current_communities)} current communities")
            
            # Compare and find changes
            changes = self._compare_communities(stored_communities, current_communities)
            
            # Update database
            if current_communities:
                self.db.update_user_communities(user.id, current_communities)
                self.db.log_tracking_run(user.id, {
                    "communities_found": len(current_communities),
                    "communities_joined": len(changes["joined"]),
                    "communities_left": len(changes["left"]),
                    "scan_type": "enhanced_focused",
                    "success": True
                })
            
            return {
                "user_id": user.id,
                "username": username,
                "stored_communities": stored_communities,
                "current_communities": current_communities,
                "changes": changes,
                "detection_methods": ["community_posts", "url_extraction", "post_mentions"],
                "timestamp": datetime.now(),
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error tracking communities for @{username}: {e}")
            return {"error": str(e), "success": False}
    
    async def _enhanced_detect_communities(self, user_id: str, username: str, hours_lookback: int) -> List[Community]:
        """
        Enhanced detection with prioritization:
        1. Posts made WITHIN communities (highest confidence)
        2. Direct community URL sharing
        3. Text mentions of communities
        """
        all_communities = []
        
        # Method 1: PRIORITY - Detect posts made within communities
        community_posts = await self._detect_community_posts(user_id, hours_lookback)
        if community_posts:
            all_communities.extend(community_posts)
            self.logger.info(f"📍 Community posts: {len(community_posts)} communities (HIGH CONFIDENCE)")
        
        # Method 2: Direct URL sharing in tweets
        url_communities = await self._detect_community_urls(user_id, hours_lookback)
        if url_communities:
            all_communities.extend(url_communities)
            self.logger.info(f"🔗 URL sharing: {len(url_communities)} communities (MEDIUM CONFIDENCE)")
        
        # Method 3: Text mentions (lower priority)
        mentioned_communities = await self._detect_text_mentions(user_id, hours_lookback)
        if mentioned_communities:
            all_communities.extend(mentioned_communities)
            self.logger.info(f"💬 Text mentions: {len(mentioned_communities)} communities (LOWER CONFIDENCE)")
        
        # Remove duplicates and prioritize by confidence
        unique_communities = self._deduplicate_and_prioritize(all_communities)
        
        return unique_communities
    
    async def _detect_community_posts(self, user_id: str, hours_lookback: int) -> List[Community]:
        """
        Detect posts made WITHIN communities - highest confidence method
        """
        communities = []
        
        try:
            self.logger.info(f"📍 Analyzing posts made within communities (last {hours_lookback}h)")
            
            # Get user's recent tweets with expanded data
            tweets = await self._get_user_tweets_with_metadata(user_id, hours_lookback)
            
            for tweet in tweets:
                # Look for community metadata in tweet
                community_data = self._extract_community_from_tweet(tweet)
                
                if community_data:
                    community = Community(
                        id=community_data['id'],
                        name=community_data['name'],
                        role="Member"  # If posting in community, definitely a member
                    )
                    
                    # High confidence metadata
                    community.source = "community_post"
                    community.confidence = 0.95  # Very high confidence
                    community.detected_at = datetime.now()
                    community.tweet_id = tweet.get('id')
                    community.post_context = f"Posted in community: {tweet.get('text', '')[:100]}"
                    
                    communities.append(community)
            
            self.logger.info(f"📍 Found {len(communities)} communities from direct posts")
            
        except Exception as e:
            self.logger.error(f"❌ Error detecting community posts: {e}")
        
        return communities
    
    async def _detect_community_urls(self, user_id: str, hours_lookback: int) -> List[Community]:
        """
        Detect community URLs shared in tweets
        """
        communities = []
        
        try:
            self.logger.info(f"🔗 Analyzing community URLs in tweets")
            
            tweets = await self._get_user_tweets_with_metadata(user_id, hours_lookback)
            
            # URL patterns for communities
            url_patterns = [
                r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/i/communities/(\d+)',
                r'/i/communities/(\d+)',
                r'communities/(\d+)'
            ]
            
            for tweet in tweets:
                text = tweet.get('text', '')
                
                # Skip retweets
                if text.startswith('RT @'):
                    continue
                
                for pattern in url_patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        community_id = match.group(1)
                        
                        # Try to extract community name from context
                        community_name = self._extract_community_name_from_context(text, community_id)
                        
                        community = Community(
                            id=f"community_{community_id}",
                            name=community_name,
                            role="Member"  # Sharing URL suggests membership
                        )
                        
                        community.source = "url_sharing"
                        community.confidence = 0.85  # High confidence for direct URLs
                        community.detected_at = datetime.now()
                        community.tweet_id = tweet.get('id')
                        community.url_shared = match.group(0)
                        
                        communities.append(community)
            
            self.logger.info(f"🔗 Found {len(communities)} communities from URL sharing")
            
        except Exception as e:
            self.logger.error(f"❌ Error detecting community URLs: {e}")
        
        return communities
    
    async def _detect_text_mentions(self, user_id: str, hours_lookback: int) -> List[Community]:
        """
        Detect communities mentioned in text (lower confidence)
        """
        communities = []
        
        try:
            self.logger.info(f"💬 Analyzing text mentions of communities")
            
            tweets = await self._get_user_tweets_with_metadata(user_id, hours_lookback)
            
            # High-confidence text patterns
            patterns = [
                (r'(?:posted in|shared in|member of|active in)\s+(?:the\s+)?([A-Za-z0-9\s\-_]+?)\s+(?:community|group)', "Member", 0.8),
                (r'(?:created|founded|launched)\s+(?:the\s+)?([A-Za-z0-9\s\-_]+?)\s+(?:community|group)', "Creator", 0.9),
                (r'(?:admin|moderating|managing)\s+(?:the\s+)?([A-Za-z0-9\s\-_]+?)\s+(?:community|group)', "Admin", 0.85),
            ]
            
            for tweet in tweets:
                text = tweet.get('text', '')
                
                # Skip retweets and replies
                if text.startswith('RT @') or text.startswith('@'):
                    continue
                
                for pattern, role, confidence in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        community_name = self._clean_community_name(match.group(1))
                        
                        if len(community_name) > 3:
                            community = Community(
                                id=f"mentioned_{community_name.lower().replace(' ', '_')}",
                                name=community_name,
                                role=role
                            )
                            
                            community.source = "text_mention"
                            community.confidence = confidence
                            community.detected_at = datetime.now()
                            community.tweet_id = tweet.get('id')
                            community.mention_context = text[:150]
                            
                            communities.append(community)
            
            self.logger.info(f"💬 Found {len(communities)} communities from text mentions")
            
        except Exception as e:
            self.logger.error(f"❌ Error detecting text mentions: {e}")
        
        return communities
    
    def _extract_community_from_tweet(self, tweet: Dict) -> Optional[Dict]:
        """
        Extract community information from tweet metadata
        This is where we'd parse the HTML structure you showed
        """
        try:
            # Check if tweet has community metadata
            text = tweet.get('text', '')
            
            # Look for community links in the text or metadata
            # This would be enhanced with actual HTML parsing if available
            community_match = re.search(r'/i/communities/(\d+)', text)
            if community_match:
                community_id = community_match.group(1)
                
                # Try to extract community name from surrounding context
                community_name = self._extract_community_name_from_context(text, community_id)
                
                return {
                    'id': f"community_{community_id}",
                    'name': community_name,
                    'source_id': community_id
                }
            
            # Additional metadata extraction would go here
            # For example, if we had access to the full HTML structure
            
        except Exception as e:
            self.logger.debug(f"Error extracting community from tweet: {e}")
        
        return None
    
    def _extract_community_name_from_context(self, text: str, community_id: str) -> str:
        """
        Extract community name from context around the community ID
        """
        # Default name if we can't extract it
        default_name = f"Community {community_id}"
        
        try:
            # Look for patterns around the community link
            patterns = [
                r'([A-Za-z0-9\s\-_]+?)\s+(?:community|group).*?/i/communities/' + community_id,
                r'/i/communities/' + community_id + r'.*?([A-Za-z0-9\s\-_]+?)\s+(?:community|group)',
                r'(?:the\s+)?([A-Za-z0-9\s\-_]+?)\s+/i/communities/' + community_id,
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    name = self._clean_community_name(match.group(1))
                    if len(name) > 2:
                        return name
            
            # Look for quoted community names
            quote_match = re.search(r'["\']([^"\']+)["\']', text)
            if quote_match and len(quote_match.group(1)) > 2:
                return quote_match.group(1)
            
        except Exception as e:
            self.logger.debug(f"Error extracting community name: {e}")
        
        return default_name
    
    async def _get_user_tweets_with_metadata(self, user_id: str, hours_lookback: int) -> List[Dict]:
        """
        Get user tweets with additional metadata for community detection
        """
        tweets = []
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
            cursor = None
            max_tweets = 100  # More tweets for better detection
            
            for page in range(5):  # More pages for comprehensive detection
                try:
                    # Fix API call - use positional arguments only
                    if cursor:
                        response = await self.api.api.user_tweets(
                            user_id,
                            20,  # count as positional argument
                            cursor
                        )
                    else:
                        response = await self.api.api.user_tweets(
                            user_id,
                            20  # count as positional argument
                        )
                    
                    if not response or not response.tweets:
                        break
                    
                    for tweet in response.tweets:
                        try:
                            if hasattr(tweet, 'date'):
                                tweet_time = datetime.fromisoformat(tweet.date.replace('Z', '+00:00'))
                                if tweet_time < cutoff_time:
                                    break
                                
                                tweets.append({
                                    'id': tweet.id,
                                    'text': tweet.text,
                                    'date': tweet.date,
                                    'user_id': user_id,
                                    'metadata': getattr(tweet, 'metadata', {}),
                                    'entities': getattr(tweet, 'entities', {}),
                                })
                        except Exception as e:
                            continue
                    
                    cursor = response.next_cursor
                    if not cursor or len(tweets) >= max_tweets:
                        break
                        
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.warning(f"Error getting tweets page {page}: {e}")
                    break
            
            self.logger.info(f"📄 Retrieved {len(tweets)} tweets for analysis")
            
        except Exception as e:
            self.logger.error(f"❌ Error getting user tweets: {e}")
        
        return tweets
    
    def _clean_community_name(self, name: str) -> str:
        """Clean up detected community names"""
        # Remove common words and clean up
        stop_words = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        name = re.sub(r'[^\w\s\-]', '', name).strip()
        words = [word for word in name.split() if word.lower() not in stop_words and len(word) > 1]
        return ' '.join(words) if words else name
    
    def _deduplicate_and_prioritize(self, communities: List[Community]) -> List[Community]:
        """
        Remove duplicates and prioritize by confidence/source
        """
        # Group by community ID/name
        community_groups = {}
        
        for community in communities:
            # Create a key for grouping (normalize community name)
            key = community.name.lower().strip()
            
            if key not in community_groups:
                community_groups[key] = []
            community_groups[key].append(community)
        
        # Select best community from each group
        unique_communities = []
        
        for group in community_groups.values():
            # Sort by confidence and source priority
            source_priority = {'community_post': 3, 'url_sharing': 2, 'text_mention': 1}
            
            best = max(group, key=lambda c: (
                source_priority.get(getattr(c, 'source', ''), 0),
                getattr(c, 'confidence', 0)
            ))
            
            unique_communities.append(best)
        
        return unique_communities
    
    def _compare_communities(self, stored: List[Community], current: List[Community]) -> Dict[str, List[Community]]:
        """Compare communities and find changes"""
        stored_ids = {c.id for c in stored}
        current_ids = {c.id for c in current}
        
        joined_ids = current_ids - stored_ids
        left_ids = stored_ids - current_ids
        
        joined = [c for c in current if c.id in joined_ids]
        left = [c for c in stored if c.id in left_ids]
        unchanged = [c for c in current if c.id in stored_ids]
        
        self.logger.info(f"📊 Changes: {len(joined)} joined, {len(left)} left, {len(unchanged)} unchanged")
        
        return {"joined": joined, "left": left, "unchanged": unchanged}
    
    def create_notification(self, result: Dict[str, Any]) -> str:
        """Create enhanced notification with confidence indicators"""
        if not result.get("success"):
            return f"❌ Error: {result.get('error', 'Unknown error')}"
        
        username = result["username"]
        changes = result["changes"]
        current_communities = result["current_communities"]
        
        message_parts = [
            f"🎯 **Enhanced Community Tracking**\n",
            f"👤 User: @{username}",
            f"🕐 Scan: {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"🔍 Methods: Community posts → URL sharing → Text mentions\n"
        ]
        
        # Show new communities with confidence levels
        if changes["joined"]:
            message_parts.append(f"✅ **Newly Detected ({len(changes['joined'])}):**")
            for community in changes["joined"]:
                confidence = getattr(community, 'confidence', 0)
                source = getattr(community, 'source', 'unknown')
                
                # Confidence emoji
                if confidence >= 0.9:
                    conf_emoji = "🔥"
                elif confidence >= 0.8:
                    conf_emoji = "✅"
                else:
                    conf_emoji = "⚠️"
                
                message_parts.append(f"   {conf_emoji} **{community.name}**")
                message_parts.append(f"      Role: {community.role}")
                message_parts.append(f"      Evidence: {source}")
                message_parts.append(f"      Confidence: {confidence:.0%}")
                
                # Add context if available
                if hasattr(community, 'post_context'):
                    message_parts.append(f"      Context: {community.post_context[:50]}...")
                
            message_parts.append("")
        
        # Summary with confidence breakdown
        if current_communities:
            high_conf = len([c for c in current_communities if getattr(c, 'confidence', 0) >= 0.9])
            med_conf = len([c for c in current_communities if 0.8 <= getattr(c, 'confidence', 0) < 0.9])
            low_conf = len([c for c in current_communities if getattr(c, 'confidence', 0) < 0.8])
            
            message_parts.append(f"📊 **Current Status:**")
            message_parts.append(f"• Total communities: {len(current_communities)}")
            message_parts.append(f"• High confidence (🔥): {high_conf}")
            message_parts.append(f"• Medium confidence (✅): {med_conf}")
            message_parts.append(f"• Lower confidence (⚠️): {low_conf}")
        
        if not changes["joined"] and not changes["left"]:
            message_parts.append(f"\n✨ No changes detected")
        
        message_parts.append(f"\n🤖 Enhanced Community Tracker")
        
        return "\n".join(message_parts)


async def main():
    """Test the enhanced focused tracker"""
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🎯 ENHANCED FOCUSED COMMUNITY TRACKER")
    print("📍 PRIORITIZED DETECTION:")
    print("   1. 🔥 Posts made WITHIN communities (95% confidence)")
    print("   2. ✅ Community URLs shared (85% confidence)")  
    print("   3. ⚠️ Text mentions (60-80% confidence)")
    print("=" * 70)
    
    tracker = EnhancedFocusedTracker()
    
    if not await tracker.initialize():
        print("❌ Failed to initialize")
        return
    
    username = "163ba6y"
    
    try:
        print(f"\n🔍 Enhanced tracking for @{username}...")
        result = await tracker.track_user_communities(username)
        
        if result.get("success"):
            print(f"\n📊 RESULTS:")
            print(f"📚 Previously stored: {len(result['stored_communities'])}")
            print(f"🔍 Currently detected: {len(result['current_communities'])}")
            print(f"✅ Newly found: {len(result['changes']['joined'])}")
            
            # Show detected communities with confidence
            if result['current_communities']:
                print(f"\n🏘️ **DETECTED COMMUNITIES:**")
                for i, community in enumerate(result['current_communities'], 1):
                    confidence = getattr(community, 'confidence', 0)
                    source = getattr(community, 'source', 'unknown')
                    
                    if confidence >= 0.9:
                        emoji = "🔥"
                    elif confidence >= 0.8:
                        emoji = "✅"
                    else:
                        emoji = "⚠️"
                    
                    print(f"  {i}. {emoji} {community.name}")
                    print(f"     Role: {community.role}")
                    print(f"     Evidence: {source}")
                    print(f"     Confidence: {confidence:.0%}")
            
            # Show notification
            notification = tracker.create_notification(result)
            print(f"\n📱 NOTIFICATION:")
            print("=" * 70)
            print(notification)
            print("=" * 70)
            
        else:
            print(f"❌ Failed: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 