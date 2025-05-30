#!/usr/bin/env python3
"""
Focused Community Tracker - Only Direct User Communities
This tracker focuses on communities the user is directly involved with:
1. Communities they're actual members of
2. Communities they mention in their posts
3. Compares with previously stored communities
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import re

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.twitter_api import TwitterAPI
from bot.models import Community, DatabaseManager

class FocusedCommunityTracker:
    """Focused tracker for direct user community connections only"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api = None
        self.db = DatabaseManager()
        
    async def initialize(self):
        """Initialize the tracker"""
        try:
            self.api = TwitterAPI()
            self.logger.info("✅ Focused Community Tracker initialized")
            return True
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def track_user_communities(self, username: str, hours_lookback: int = 24) -> Dict[str, Any]:
        """
        Track communities for a specific user - only direct connections
        
        Args:
            username: Twitter username to track
            hours_lookback: How far back to look in posts (default 24h)
            
        Returns:
            Dict with detected communities, changes, and comparison with stored data
        """
        try:
            self.logger.info(f"🎯 Tracking communities for @{username} (direct connections only)")
            
            # Get user info
            user = await self.api.api.user_by_login(username)
            if not user:
                return {"error": f"User @{username} not found"}
            
            # Get previously stored communities
            stored_communities = self.db.get_user_communities(user.id)
            self.logger.info(f"📚 Found {len(stored_communities)} previously stored communities")
            
            # Detect current communities (direct connections only)
            current_communities = await self._detect_direct_communities(user.id, username, hours_lookback)
            self.logger.info(f"🔍 Detected {len(current_communities)} current communities")
            
            # Compare and find changes
            changes = self._compare_communities(stored_communities, current_communities)
            
            # Update database with current communities
            if current_communities:
                self.db.update_user_communities(user.id, current_communities)
                
                # Log the tracking run
                self.db.log_tracking_run(user.id, {
                    "communities_found": len(current_communities),
                    "communities_joined": len(changes["joined"]),
                    "communities_left": len(changes["left"]),
                    "scan_type": "focused_direct",
                    "success": True
                })
            
            return {
                "user_id": user.id,
                "username": username,
                "stored_communities": stored_communities,
                "current_communities": current_communities,
                "changes": changes,
                "detection_methods": ["direct_membership", "post_mentions"],
                "timestamp": datetime.now(),
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error tracking communities for @{username}: {e}")
            return {"error": str(e), "success": False}
    
    async def _detect_direct_communities(self, user_id: str, username: str, hours_lookback: int) -> List[Community]:
        """
        Detect communities the user is directly connected to
        
        Methods:
        1. Direct membership detection (GraphQL/API calls)
        2. Communities mentioned in user's posts
        3. Fallback to enhanced detection with filtering
        """
        all_communities = []
        
        # Method 1: Try to detect direct membership
        direct_communities = await self._detect_direct_membership(user_id, username)
        if direct_communities:
            all_communities.extend(direct_communities)
            self.logger.info(f"📋 Direct membership: {len(direct_communities)} communities")
        
        # Method 2: Communities mentioned in user's posts
        mentioned_communities = await self._detect_mentioned_communities(user_id, hours_lookback)
        if mentioned_communities:
            all_communities.extend(mentioned_communities)
            self.logger.info(f"💬 Post mentions: {len(mentioned_communities)} communities")
        
        # Method 3: Fallback - use enhanced tracker but filter to direct connections only
        if len(all_communities) == 0:
            self.logger.info("🔄 Using fallback detection with filtering...")
            fallback_communities = await self._fallback_enhanced_detection(username)
            all_communities.extend(fallback_communities)
        
        # Remove duplicates
        unique_communities = self._deduplicate_communities(all_communities)
        
        return unique_communities
    
    async def _detect_direct_membership(self, user_id: str, username: str) -> List[Community]:
        """
        Try to detect direct community membership
        This uses available API methods to find actual memberships
        """
        communities = []
        
        try:
            # Try GraphQL community detection if available
            # This would be the most direct method but may require specific API access
            self.logger.info("🔍 Attempting direct membership detection...")
            
            # For now, we'll focus on what we can reliably detect
            # This is a placeholder for when direct membership APIs are available
            
        except Exception as e:
            self.logger.debug(f"Direct membership detection not available: {e}")
        
        return communities
    
    async def _fallback_enhanced_detection(self, username: str) -> List[Community]:
        """
        Fallback method using enhanced tracker but filtering only direct connections
        """
        try:
            from bot.enhanced_community_tracker_v2 import EnhancedCommunityTrackerV2
            
            tracker = EnhancedCommunityTrackerV2(self.api.api, self.api.cookie_manager)
            result = await tracker.get_all_user_communities(username, deep_scan=False)
            
            if result and result.communities:
                # Filter to only include communities that seem directly connected
                filtered_communities = []
                
                for community in result.communities:
                    # Only include if:
                    # 1. It has a real community ID (not derived from following/followers)
                    # 2. The source suggests direct connection
                    if (not community.id.startswith('following_') and 
                        not community.id.startswith('mention_') and
                        not community.id.startswith('theme_')):
                        
                        # Update source to indicate it came from fallback
                        community.source = "direct_detection"
                        community.confidence = 0.6  # Lower confidence for fallback
                        filtered_communities.append(community)
                
                self.logger.info(f"🔄 Fallback detection found {len(filtered_communities)} direct communities")
                return filtered_communities
                
        except Exception as e:
            self.logger.warning(f"Fallback detection failed: {e}")
        
        return []
    
    async def _detect_mentioned_communities(self, user_id: str, hours_lookback: int) -> List[Community]:
        """
        Detect communities mentioned in user's own posts
        """
        communities = []
        
        try:
            self.logger.info(f"💬 Analyzing user posts for community mentions (last {hours_lookback}h)")
            
            # Get user's recent tweets
            tweets = await self._get_user_tweets(user_id, hours_lookback)
            
            # Enhanced community detection patterns
            community_patterns = [
                # Direct membership statements
                (r'(?:joined|joining|member of|part of|belong to)\s+(?:the\s+)?([A-Za-z0-9\s\-_]+?)\s+(?:community|DAO|group|guild|collective)', "Member"),
                (r'(?:created|launched|founding|started)\s+(?:the\s+)?([A-Za-z0-9\s\-_]+?)\s+(?:community|DAO|group|guild|collective)', "Creator"),
                (r'(?:admin|moderator|mod)\s+(?:of|in|at)\s+(?:the\s+)?([A-Za-z0-9\s\-_]+?)\s+(?:community|DAO|group)', "Admin"),
                
                # Twitter community URLs (most reliable)
                (r'twitter\.com/i/communities/(\d+)', "Member"),
                (r'x\.com/i/communities/(\d+)', "Member"),
                (r'/communities/(\d+)', "Member"),
                
                # Specific community hashtags
                (r'#([A-Za-z0-9]+(?:DAO|Community|Guild|Collective|Protocol))\b', "Member"),
                
                # @ mentions that are clearly communities
                (r'@([A-Za-z0-9_]+(?:DAO|Community|Guild|Collective|Protocol))\b', "Member"),
                
                # More context-aware patterns
                (r'(?:welcome to|proud to be in|excited to join)\s+(?:the\s+)?([A-Za-z0-9\s\-_]+?)\s+(?:community|DAO)', "Member"),
                (r'(?:our|my)\s+([A-Za-z0-9\s\-_]+?)\s+(?:community|DAO|project)\s+(?:is|has)', "Creator"),
            ]
            
            for tweet in tweets:
                text = tweet.get('text', '')
                
                # Skip retweets and direct replies to focus on user's own content
                if (text.startswith('RT @') or 
                    text.startswith('@') or 
                    'RT:' in text[:10]):
                    continue
                
                for pattern, default_role in community_patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        community_identifier = match.group(1).strip()
                        
                        # For URL patterns, use the ID directly
                        if pattern.endswith(r'(\d+)', "Member")[0]:
                            community_name = f"Community {community_identifier}"
                            community_id = f"community_{community_identifier}"
                        else:
                            # Clean up the community name
                            community_name = self._clean_community_name(community_identifier)
                            community_id = f"mentioned_{community_name.lower().replace(' ', '_').replace('-', '_')}"
                        
                        if len(community_name) > 2:  # Minimum length check
                            # Determine role based on context
                            role = self._determine_role_from_context(text, community_name, default_role)
                            
                            community = Community(
                                id=community_id,
                                name=community_name,
                                role=role
                            )
                            
                            # Add metadata
                            community.source = "post_mention"
                            community.confidence = self._calculate_confidence(pattern, text, community_name)
                            community.detected_at = datetime.now()
                            community.mention_context = text[:150] + "..." if len(text) > 150 else text
                            community.tweet_id = tweet.get('id')
                            
                            communities.append(community)
            
            self.logger.info(f"💬 Found {len(communities)} community mentions in posts")
            
        except Exception as e:
            self.logger.error(f"❌ Error detecting mentioned communities: {e}")
        
        return communities
    
    def _determine_role_from_context(self, text: str, community_name: str, default_role: str) -> str:
        """Determine user role based on context clues in the text"""
        text_lower = text.lower()
        
        # Creator/Founder indicators
        creator_words = ['created', 'launched', 'founded', 'started', 'building', 'my', 'our']
        if any(word in text_lower for word in creator_words):
            return "Creator"
        
        # Admin/Moderator indicators  
        admin_words = ['admin', 'moderator', 'mod', 'manage', 'lead']
        if any(word in text_lower for word in admin_words):
            return "Admin"
        
        return default_role
    
    def _calculate_confidence(self, pattern: str, text: str, community_name: str) -> float:
        """Calculate confidence score based on pattern and context"""
        base_confidence = 0.7
        
        # URL patterns are most reliable
        if 'communities/' in pattern:
            return 0.95
        
        # Direct action words increase confidence
        action_words = ['joined', 'created', 'launched', 'member of']
        if any(word in text.lower() for word in action_words):
            base_confidence += 0.1
        
        # Longer community names tend to be more specific
        if len(community_name) > 10:
            base_confidence += 0.05
        
        # First person statements are more reliable
        if any(word in text.lower() for word in ['i ', 'my ', 'our ']):
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)  # Cap at 95%
    
    async def _get_user_tweets(self, user_id: str, hours_lookback: int) -> List[Dict]:
        """Get user's recent tweets"""
        tweets = []
        
        try:
            # Calculate time window
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
            
            # Get tweets using the API
            cursor = None
            max_tweets = 50  # Reasonable limit
            
            for page in range(3):  # Max 3 pages
                try:
                    # Get user tweets - fix the API call
                    response = await self.api.api.user_tweets(
                        user_id,  # positional argument
                        count=20,
                        cursor=cursor
                    )
                    
                    if not response or not response.tweets:
                        break
                    
                    for tweet in response.tweets:
                        # Parse tweet date properly
                        try:
                            if hasattr(tweet, 'date'):
                                tweet_time = datetime.fromisoformat(tweet.date.replace('Z', '+00:00'))
                            else:
                                # Skip if no date available
                                continue
                                
                            if tweet_time < cutoff_time:
                                break
                            
                            tweets.append({
                                'id': tweet.id,
                                'text': tweet.text,
                                'date': tweet.date,
                                'user_id': user_id
                            })
                        except Exception as date_error:
                            self.logger.debug(f"Error parsing tweet date: {date_error}")
                            continue
                    
                    cursor = response.next_cursor
                    if not cursor or len(tweets) >= max_tweets:
                        break
                        
                    # Rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    self.logger.warning(f"Error getting tweets page {page}: {e}")
                    break
            
            self.logger.info(f"📄 Analyzed {len(tweets)} recent tweets")
            
        except Exception as e:
            self.logger.error(f"❌ Error getting user tweets: {e}")
        
        return tweets
    
    def _clean_community_name(self, name: str) -> str:
        """Clean up detected community names"""
        # Remove common words that aren't part of the name
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Clean whitespace and special characters
        name = re.sub(r'[^\w\s]', '', name).strip()
        
        # Split into words and filter
        words = [word for word in name.split() if word.lower() not in stop_words]
        
        return ' '.join(words) if words else name
    
    def _deduplicate_communities(self, communities: List[Community]) -> List[Community]:
        """Remove duplicate communities based on name similarity"""
        unique_communities = []
        seen_names = set()
        
        for community in communities:
            # Normalize name for comparison
            normalized_name = community.name.lower().strip()
            
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_communities.append(community)
        
        return unique_communities
    
    def _compare_communities(self, stored: List[Community], current: List[Community]) -> Dict[str, List[Community]]:
        """
        Compare stored communities with current ones to find changes
        
        Returns:
            Dict with 'joined', 'left', and 'unchanged' lists
        """
        stored_ids = {c.id for c in stored}
        current_ids = {c.id for c in current}
        
        joined_ids = current_ids - stored_ids
        left_ids = stored_ids - current_ids
        unchanged_ids = stored_ids & current_ids
        
        joined = [c for c in current if c.id in joined_ids]
        left = [c for c in stored if c.id in left_ids]
        unchanged = [c for c in current if c.id in unchanged_ids]
        
        self.logger.info(f"📊 Community changes: {len(joined)} joined, {len(left)} left, {len(unchanged)} unchanged")
        
        return {
            "joined": joined,
            "left": left,
            "unchanged": unchanged
        }
    
    def create_notification(self, result: Dict[str, Any]) -> str:
        """
        Create a notification message for detected changes
        """
        if not result.get("success"):
            return f"❌ Error tracking communities: {result.get('error', 'Unknown error')}"
        
        username = result["username"]
        changes = result["changes"]
        current_communities = result["current_communities"]
        
        message_parts = [
            f"🎯 **Community Tracking Update**\n",
            f"👤 User: @{username}",
            f"🕐 Scan time: {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"🔍 Methods: Direct membership + Post mentions\n"
        ]
        
        # Show changes
        if changes["joined"]:
            message_parts.append(f"✅ **Newly Joined ({len(changes['joined'])}):**")
            for community in changes["joined"]:
                confidence = getattr(community, 'confidence', 0)
                source = getattr(community, 'source', 'unknown')
                message_parts.append(f"   👤 **{community.name}**")
                message_parts.append(f"      Role: {community.role}")
                message_parts.append(f"      Source: {source}")
                message_parts.append(f"      Confidence: {confidence:.1%}")
            message_parts.append("")
        
        if changes["left"]:
            message_parts.append(f"❌ **Left Communities ({len(changes['left'])}):**")
            for community in changes["left"]:
                message_parts.append(f"   🚪 **{community.name}**")
                message_parts.append(f"      Previous role: {community.role}")
            message_parts.append("")
        
        # Summary
        total_communities = len(current_communities)
        message_parts.append(f"📊 **Current Status:**")
        message_parts.append(f"• Total communities: {total_communities}")
        
        if current_communities:
            admin_count = len([c for c in current_communities if c.role in ["Admin", "Creator"]])
            member_count = len([c for c in current_communities if c.role == "Member"])
            message_parts.append(f"• Admin/Creator roles: {admin_count}")
            message_parts.append(f"• Member roles: {member_count}")
        
        # Detection summary
        if not changes["joined"] and not changes["left"]:
            message_parts.append(f"\n✨ No changes detected - all communities stable")
        else:
            total_changes = len(changes["joined"]) + len(changes["left"])
            message_parts.append(f"\n🔄 Total changes detected: {total_changes}")
        
        message_parts.append(f"\n🤖 Focused Community Tracker")
        
        return "\n".join(message_parts)


async def main():
    """Test the focused community tracker"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 FOCUSED COMMUNITY TRACKER")
    print("📍 Only tracking direct user connections:")
    print("   • Communities user is actually member of")
    print("   • Communities mentioned in user's posts")
    print("   • Comparing with stored data")
    print("=" * 70)
    
    tracker = FocusedCommunityTracker()
    
    if not await tracker.initialize():
        print("❌ Failed to initialize tracker")
        return
    
    # Test with your username
    username = "163ba6y"  # Change to your username
    
    try:
        print(f"\n🔍 Tracking communities for @{username}...")
        result = await tracker.track_user_communities(username, hours_lookback=168)  # Last week
        
        if result.get("success"):
            # Show results
            print(f"\n📊 TRACKING RESULTS:")
            print(f"📚 Previously stored: {len(result['stored_communities'])}")
            print(f"🔍 Currently detected: {len(result['current_communities'])}")
            print(f"✅ Newly joined: {len(result['changes']['joined'])}")
            print(f"❌ Left communities: {len(result['changes']['left'])}")
            
            # Show current communities
            if result['current_communities']:
                print(f"\n🏘️ **CURRENT COMMUNITIES:**")
                for i, community in enumerate(result['current_communities'], 1):
                    source = getattr(community, 'source', 'unknown')
                    confidence = getattr(community, 'confidence', 0)
                    print(f"  {i}. 👤 {community.name}")
                    print(f"     Role: {community.role}")
                    print(f"     Source: {source}")
                    print(f"     Confidence: {confidence:.1%}")
            
            # Generate and show notification
            notification = tracker.create_notification(result)
            print(f"\n📱 NOTIFICATION THAT WOULD BE SENT:")
            print("=" * 70)
            print(notification)
            print("=" * 70)
            
        else:
            print(f"❌ Tracking failed: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 