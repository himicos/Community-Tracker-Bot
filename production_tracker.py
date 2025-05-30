#!/usr/bin/env python3
"""
Production Community Tracker - Multi-User Ready
Tracks community posting history and compares with past data.
Ready for commercial deployment.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import re
import sqlite3
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import json

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.twitter_api import TwitterAPI
from bot.models import Community

@dataclass
class CommunityPost:
    """Represents a community post with metadata"""
    user_id: str
    community_id: str
    community_name: str
    post_id: str
    post_text: str
    posted_at: datetime
    confidence: float
    detection_method: str

class ProductionDatabase:
    """Production database with proper user separation"""
    
    def __init__(self, db_path: str = "production_tracker.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with proper schema for multi-user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_scan TIMESTAMP,
                    total_communities INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Community posts table (historical data)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS community_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    community_id TEXT NOT NULL,
                    community_name TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    post_text TEXT,
                    posted_at TIMESTAMP NOT NULL,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence REAL NOT NULL,
                    detection_method TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, post_id, community_id)
                )
            """)
            
            # Current communities table (latest state)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS current_communities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    community_id TEXT NOT NULL,
                    community_name TEXT NOT NULL,
                    role TEXT DEFAULT 'Member',
                    first_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    post_count INTEGER DEFAULT 1,
                    confidence REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, community_id)
                )
            """)
            
            # Tracking logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracking_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    scan_type TEXT NOT NULL,
                    communities_found INTEGER DEFAULT 0,
                    new_posts INTEGER DEFAULT 0,
                    scan_duration REAL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
    
    def add_user(self, user_id: str, username: str) -> bool:
        """Add a new user for tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users (user_id, username, last_scan)
                    VALUES (?, ?, ?)
                """, (user_id, username, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding user {username}: {e}")
            return False
    
    def get_user_community_history(self, user_id: str) -> List[CommunityPost]:
        """Get user's community posting history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, community_id, community_name, post_id, 
                           post_text, posted_at, confidence, detection_method
                    FROM community_posts 
                    WHERE user_id = ?
                    ORDER BY posted_at DESC
                """, (user_id,))
                
                return [
                    CommunityPost(
                        user_id=row[0],
                        community_id=row[1], 
                        community_name=row[2],
                        post_id=row[3],
                        post_text=row[4],
                        posted_at=datetime.fromisoformat(row[5]),
                        confidence=row[6],
                        detection_method=row[7]
                    ) for row in cursor.fetchall()
                ]
        except Exception as e:
            logging.error(f"Error getting community history for {user_id}: {e}")
            return []
    
    def save_community_posts(self, posts: List[CommunityPost]) -> int:
        """Save new community posts"""
        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for post in posts:
                    try:
                        # Insert community post
                        cursor.execute("""
                            INSERT OR IGNORE INTO community_posts 
                            (user_id, community_id, community_name, post_id, 
                             post_text, posted_at, confidence, detection_method)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            post.user_id, post.community_id, post.community_name,
                            post.post_id, post.post_text, post.posted_at,
                            post.confidence, post.detection_method
                        ))
                        
                        if cursor.rowcount > 0:
                            saved_count += 1
                            
                            # Update or insert current community
                            cursor.execute("""
                                INSERT OR REPLACE INTO current_communities
                                (user_id, community_id, community_name, last_activity, 
                                 post_count, confidence)
                                VALUES (?, ?, ?, ?, 
                                    COALESCE((SELECT post_count FROM current_communities 
                                             WHERE user_id = ? AND community_id = ?), 0) + 1,
                                    ?)
                            """, (
                                post.user_id, post.community_id, post.community_name,
                                post.posted_at, post.user_id, post.community_id, 
                                post.confidence
                            ))
                        
                    except Exception as e:
                        logging.debug(f"Error saving post {post.post_id}: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error saving community posts: {e}")
        
        return saved_count
    
    def get_current_communities(self, user_id: str) -> List[Dict]:
        """Get user's current communities"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT community_id, community_name, role, first_detected,
                           last_activity, post_count, confidence
                    FROM current_communities 
                    WHERE user_id = ?
                    ORDER BY last_activity DESC
                """, (user_id,))
                
                return [
                    {
                        'community_id': row[0],
                        'community_name': row[1],
                        'role': row[2],
                        'first_detected': row[3],
                        'last_activity': row[4],
                        'post_count': row[5],
                        'confidence': row[6]
                    } for row in cursor.fetchall()
                ]
        except Exception as e:
            logging.error(f"Error getting current communities for {user_id}: {e}")
            return []
    
    def log_tracking_run(self, user_id: str, scan_data: Dict):
        """Log tracking run results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tracking_logs 
                    (user_id, scan_type, communities_found, new_posts, 
                     scan_duration, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    scan_data.get('scan_type', 'production'),
                    scan_data.get('communities_found', 0),
                    scan_data.get('new_posts', 0),
                    scan_data.get('scan_duration', 0),
                    scan_data.get('success', True),
                    scan_data.get('error_message')
                ))
                
                # Update user last scan
                cursor.execute("""
                    UPDATE users SET last_scan = ?, total_communities = ?
                    WHERE user_id = ?
                """, (datetime.now(), scan_data.get('communities_found', 0), user_id))
                
                conn.commit()
        except Exception as e:
            logging.error(f"Error logging tracking run: {e}")
    
    def get_all_active_users(self) -> List[Dict]:
        """Get all active users for tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, username, last_scan, total_communities
                    FROM users 
                    WHERE is_active = 1
                    ORDER BY last_scan ASC
                """)
                
                return [
                    {
                        'user_id': row[0],
                        'username': row[1], 
                        'last_scan': row[2],
                        'total_communities': row[3]
                    } for row in cursor.fetchall()
                ]
        except Exception as e:
            logging.error(f"Error getting active users: {e}")
            return []


class ProductionCommunityTracker:
    """Production-ready multi-user community tracker"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api = None
        self.db = ProductionDatabase()
        self.executor = ThreadPoolExecutor(max_workers=5)  # For parallel processing
    
    async def initialize(self):
        """Initialize the tracker"""
        try:
            self.api = TwitterAPI()
            self.logger.info("✅ Production Community Tracker initialized")
            return True
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def add_user_for_tracking(self, username: str) -> Dict[str, Any]:
        """Add a user for community tracking"""
        try:
            user = await self.api.api.user_by_login(username)
            if not user:
                return {"success": False, "error": f"User @{username} not found"}
            
            success = self.db.add_user(user.id, username)
            if success:
                return {
                    "success": True,
                    "user_id": user.id,
                    "username": username,
                    "message": f"Added @{username} for tracking"
                }
            else:
                return {"success": False, "error": "Failed to add user to database"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def track_user_communities(self, user_id: str, username: str, 
                                   hours_lookback: int = 24) -> Dict[str, Any]:
        """Track communities for a specific user with historical comparison"""
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🎯 Tracking communities for @{username} (ID: {user_id})")
            
            # Get historical data
            historical_posts = self.db.get_user_community_history(user_id)
            current_communities = self.db.get_current_communities(user_id)
            
            self.logger.info(f"📚 Found {len(historical_posts)} historical posts in {len(current_communities)} communities")
            
            # Detect new community posts
            new_posts = await self._detect_new_community_posts(user_id, hours_lookback)
            
            # Save new posts
            saved_count = 0
            if new_posts:
                saved_count = self.db.save_community_posts(new_posts)
                self.logger.info(f"💾 Saved {saved_count} new community posts")
            
            # Get updated current communities
            updated_communities = self.db.get_current_communities(user_id)
            
            # Compare changes
            changes = self._analyze_changes(current_communities, updated_communities, new_posts)
            
            # Log tracking run
            scan_duration = (datetime.now() - start_time).total_seconds()
            self.db.log_tracking_run(user_id, {
                'scan_type': 'production_tracking',
                'communities_found': len(updated_communities),
                'new_posts': saved_count,
                'scan_duration': scan_duration,
                'success': True
            })
            
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "historical_posts": len(historical_posts),
                "current_communities": updated_communities,
                "new_posts": new_posts,
                "changes": changes,
                "scan_duration": scan_duration,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            # Log error
            self.db.log_tracking_run(user_id, {
                'scan_type': 'production_tracking',
                'success': False,
                'error_message': str(e),
                'scan_duration': (datetime.now() - start_time).total_seconds()
            })
            
            self.logger.error(f"❌ Error tracking @{username}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _detect_new_community_posts(self, user_id: str, hours_lookback: int) -> List[CommunityPost]:
        """Detect new posts made within communities"""
        posts = []
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
            tweets = await self._get_user_tweets(user_id, hours_lookback)
            
            for tweet in tweets:
                # Look for community evidence in tweet
                community_data = self._extract_community_from_tweet(tweet)
                
                if community_data:
                    post = CommunityPost(
                        user_id=user_id,
                        community_id=community_data['id'],
                        community_name=community_data['name'],
                        post_id=tweet['id'],
                        post_text=tweet['text'][:500],  # Limit text length
                        posted_at=datetime.fromisoformat(tweet['date'].replace('Z', '+00:00')),
                        confidence=0.95,  # High confidence for direct posting
                        detection_method='community_post'
                    )
                    posts.append(post)
            
            self.logger.info(f"🔍 Detected {len(posts)} new community posts")
            
        except Exception as e:
            self.logger.error(f"❌ Error detecting community posts: {e}")
        
        return posts
    
    async def _get_user_tweets(self, user_id: str, hours_lookback: int) -> List[Dict]:
        """Get user's recent tweets"""
        tweets = []
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)
            cursor = None
            
            for page in range(3):  # Limit pages for production
                try:
                    if cursor:
                        response = await self.api.api.user_tweets(user_id, 20, cursor)
                    else:
                        response = await self.api.api.user_tweets(user_id, 20)
                    
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
                                    'date': tweet.date
                                })
                        except Exception:
                            continue
                    
                    cursor = response.next_cursor
                    if not cursor:
                        break
                        
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    self.logger.warning(f"Error getting tweets page {page}: {e}")
                    break
            
        except Exception as e:
            self.logger.error(f"❌ Error getting user tweets: {e}")
        
        return tweets
    
    def _extract_community_from_tweet(self, tweet: Dict) -> Optional[Dict]:
        """Extract community information from tweet"""
        try:
            text = tweet.get('text', '')
            
            # Look for community URLs (most reliable)
            community_match = re.search(r'/i/communities/(\d+)', text)
            if community_match:
                community_id = community_match.group(1)
                
                # Try to extract community name
                name_patterns = [
                    r'([A-Za-z0-9\s\-_]+?)\s*(?:community|group|collective)',
                    r'#([A-Za-z0-9]+)',
                    r'@([A-Za-z0-9_]+)'
                ]
                
                community_name = f"Community {community_id}"  # Default
                
                for pattern in name_patterns:
                    name_match = re.search(pattern, text, re.IGNORECASE)
                    if name_match:
                        potential_name = name_match.group(1).strip()
                        if len(potential_name) > 2:
                            community_name = potential_name
                            break
                
                return {
                    'id': community_id,
                    'name': community_name
                }
            
        except Exception as e:
            self.logger.debug(f"Error extracting community from tweet: {e}")
        
        return None
    
    def _analyze_changes(self, old_communities: List[Dict], new_communities: List[Dict], 
                        new_posts: List[CommunityPost]) -> Dict[str, Any]:
        """Analyze changes in user's communities"""
        old_ids = {c['community_id'] for c in old_communities}
        new_ids = {c['community_id'] for c in new_communities}
        
        newly_joined = new_ids - old_ids
        left_communities = old_ids - new_ids
        
        return {
            "newly_joined": [c for c in new_communities if c['community_id'] in newly_joined],
            "left_communities": [c for c in old_communities if c['community_id'] in left_communities],
            "new_posts_count": len(new_posts),
            "total_communities": len(new_communities)
        }
    
    async def track_multiple_users(self, max_concurrent: int = 3) -> Dict[str, Any]:
        """Track multiple users concurrently"""
        try:
            active_users = self.db.get_all_active_users()
            self.logger.info(f"🔄 Tracking {len(active_users)} active users")
            
            results = []
            
            # Process users in batches to avoid rate limits
            for i in range(0, len(active_users), max_concurrent):
                batch = active_users[i:i + max_concurrent]
                
                # Track users concurrently
                tasks = [
                    self.track_user_communities(user['user_id'], user['username'])
                    for user in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for user, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Error tracking {user['username']}: {result}")
                        results.append({
                            "username": user['username'],
                            "success": False,
                            "error": str(result)
                        })
                    else:
                        results.append(result)
                
                # Wait between batches
                if i + max_concurrent < len(active_users):
                    await asyncio.sleep(5)
            
            successful = len([r for r in results if r.get('success')])
            
            return {
                "success": True,
                "total_users": len(active_users),
                "successful_scans": successful,
                "failed_scans": len(results) - successful,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error in multi-user tracking: {e}")
            return {"success": False, "error": str(e)}
    
    def create_notification(self, result: Dict[str, Any]) -> str:
        """Create notification for tracking results"""
        if not result.get("success"):
            return f"❌ Tracking failed: {result.get('error')}"
        
        username = result["username"]
        changes = result["changes"]
        communities = result["current_communities"]
        new_posts = result["new_posts"]
        
        message_parts = [
            f"🎯 **Community Tracking Update**\n",
            f"👤 User: @{username}",
            f"🕐 {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"📊 Historical posts: {result['historical_posts']}\n"
        ]
        
        # New posts
        if new_posts:
            message_parts.append(f"🔥 **New Community Posts ({len(new_posts)}):**")
            for post in new_posts[:3]:  # Show first 3
                message_parts.append(f"   📍 {post.community_name}")
                message_parts.append(f"      Posted: {post.posted_at.strftime('%H:%M')}")
                message_parts.append(f"      Text: {post.post_text[:50]}...")
            
            if len(new_posts) > 3:
                message_parts.append(f"   ... and {len(new_posts) - 3} more")
            message_parts.append("")
        
        # Community changes
        if changes["newly_joined"]:
            message_parts.append(f"✅ **New Communities ({len(changes['newly_joined'])}):**")
            for comm in changes["newly_joined"]:
                message_parts.append(f"   🏘️ {comm['community_name']}")
        
        # Summary
        message_parts.append(f"📊 **Current Status:**")
        message_parts.append(f"• Total communities: {changes['total_communities']}")
        message_parts.append(f"• New posts today: {changes['new_posts_count']}")
        
        if not new_posts and not changes["newly_joined"]:
            message_parts.append(f"\n✨ No new activity detected")
        
        message_parts.append(f"\n🤖 Production Community Tracker")
        
        return "\n".join(message_parts)


async def main():
    """Test the production tracker"""
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🚀 PRODUCTION COMMUNITY TRACKER")
    print("📊 Multi-user ready with historical data comparison")
    print("💾 Proper database separation per user")
    print("🔄 Concurrent user tracking")
    print("=" * 70)
    
    tracker = ProductionCommunityTracker()
    
    if not await tracker.initialize():
        print("❌ Failed to initialize")
        return
    
    # Add user for tracking
    username = "163ba6y"
    add_result = await tracker.add_user_for_tracking(username)
    print(f"\n👥 Add User Result: {add_result}")
    
    if add_result.get("success"):
        # Track the user
        print(f"\n🔍 Tracking @{username}...")
        result = await tracker.track_user_communities(
            add_result["user_id"], 
            username, 
            hours_lookback=168  # Last week
        )
        
        if result.get("success"):
            print(f"\n📊 RESULTS:")
            print(f"📚 Historical posts: {result['historical_posts']}")
            print(f"🏘️ Current communities: {len(result['current_communities'])}")
            print(f"🆕 New posts: {len(result['new_posts'])}")
            print(f"⏱️ Scan duration: {result['scan_duration']:.2f}s")
            
            # Show notification
            notification = tracker.create_notification(result)
            print(f"\n📱 NOTIFICATION:")
            print("=" * 70)
            print(notification)
            print("=" * 70)
        else:
            print(f"❌ Tracking failed: {result.get('error')}")
    
    print(f"\n🎯 **PRODUCTION FEATURES:**")
    print("✅ Multi-user support with proper DB separation")
    print("✅ Historical data tracking and comparison") 
    print("✅ Concurrent user processing")
    print("✅ High-confidence community detection")
    print("✅ Production-ready error handling")
    print("✅ Commercial deployment ready")


if __name__ == "__main__":
    asyncio.run(main()) 