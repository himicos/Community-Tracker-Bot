#!/usr/bin/env python3
"""
Enhanced Community Tracking System - Refactored Version

This module implements comprehensive community detection and monitoring using
a modular architecture with separated concerns:
- Core detection (community_detection.py)
- Activity analysis (community_analysis.py)
- Difference analysis (community_diff.py)
- Post tracking (community_post_tracker.py)
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import json

from twscrape import API
from bot.models import Community, TwitterUserCommunityPayload
from bot.cookie_manager import CookieManager, CookieSet
from bot.community_post_tracker import CommunityPostTracker
from bot.community_detection import CommunityDetector
from bot.community_analysis import CommunityAnalyzer
from bot.community_diff import CommunityDifferenceAnalyzer


class EnhancedCommunityTrackerV2:
    """
    Refactored Enhanced Community Tracking System
    
    Uses modular components for different aspects of community detection
    and analysis, making the codebase more maintainable and testable.
    """
    
    def __init__(self, api: API, cookie_manager: CookieManager):
        self.api = api
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize modular components
        self.post_tracker = CommunityPostTracker(api, cookie_manager)
        self.detector = CommunityDetector(api, cookie_manager)
        self.analyzer = CommunityAnalyzer(api, cookie_manager)
        self.diff_analyzer = CommunityDifferenceAnalyzer()
        
        self.logger.info("Enhanced Community Tracker V2 initialized with modular architecture")
    
    async def get_all_user_communities(self, username: str, deep_scan: bool = True) -> Optional[TwitterUserCommunityPayload]:
        """
        Get the actual current list of Twitter Communities the user is in
        
        Args:
            username: Twitter username (without @)
            deep_scan: If True, tries multiple methods; if False, uses fastest method
            
        Returns:
            TwitterUserCommunityPayload with current community memberships
        """
        self.logger.info(f"🔍 Getting current Twitter Communities for @{username} (Deep scan: {deep_scan})")
        
        try:
            # Get user information
            user = await self.api.user_by_login(username)
            if not user:
                self.logger.error(f"User @{username} not found")
                return None
            
            display_name = getattr(user, 'display_name', getattr(user, 'name', username))
            self.logger.info(f"Found user: {display_name} (@{user.username}, ID: {user.id})")
            
            # Method 0: Direct API Community Detection (MOST RELIABLE)
            try:
                api_communities = await self.detector.get_communities_from_tweet_objects(user.id, max_tweets=20)
                communities.extend(api_communities)
                self.logger.info(f"🎯 Direct API detection found {len(api_communities)} communities")
            except Exception as e:
                self.logger.debug(f"Direct API detection failed: {e}")
            
            # Get actual current communities using multiple detection methods
            communities = []
            
            if deep_scan:
                self.logger.info("🔍 Using comprehensive community detection")
                
                # Method 1: Browser automation - Direct community detection (MOST IMPORTANT)
                self.logger.info(f"🌐 Using browser automation for direct community detection")
                try:
                    # Method 1A: Selenium-based HTML Element Detection (for socialContext, CSS elements)
                    try:
                        from bot.selenium_community_detector import SeleniumCommunityDetector
                        selenium_detector = SeleniumCommunityDetector(self.cookie_manager)
                        
                        # Use the same cookie selection logic as scheduler
                        saved_cookies = self.cookie_manager.list_cookie_sets()
                        if saved_cookies:
                            cookie_name = saved_cookies[0]['name']  # Most recent cookie set
                        else:
                            cookie_name = "default"
                        
                        self.logger.info(f"🌐 Using Selenium detector with cookie: {cookie_name}")
                        html_detections = await selenium_detector.detect_communities(username, cookie_name)
                        
                        # Convert SeleniumCommunityDetector results to Community objects
                        for detection in html_detections:
                            community = Community(
                                id=detection.community_id,
                                name=detection.name,
                                description="",
                                member_count=0,
                                is_nsfw=False,
                                theme="selenium_detected",
                                created_at=None,
                                admin_id="",
                                role="Member",  # Default role
                                joined_at=None
                            )
                            communities.append(community)
                        
                        self.logger.info(f"🎯 Selenium HTML Detection found {len(html_detections)} communities (socialContext, CSS elements)")
                        
                    except Exception as e:
                        self.logger.error(f"Selenium detection failed: {e}")
                        import traceback
                        self.logger.error(f"Selenium detection traceback: {traceback.format_exc()}")
                    
                    # Method 1B: Text-based URL detection (backup)
                    url_communities = await self.detector.get_communities_from_urls(user.id, max_tweets=10)
                    communities.extend(url_communities)
                    self.logger.info(f"🌐 Text URL scanning found {len(url_communities)} communities")
                    
                    # Method 1C: Profile-based communities from browser detection
                    profile_communities = await self.detector.get_communities_from_profile(user)
                    communities = self.diff_analyzer.merge_community_lists(communities, profile_communities)
                    self.logger.info(f"🌐 Profile analysis found {len(profile_communities)} communities")
                    
                except Exception as e:
                    self.logger.debug(f"Browser automation failed: {e}")
                
                # Method 2: Profile analysis for community links
                self.logger.info(f"👤 Analyzing profile for community indicators")
                try:
                    if user.description:
                        profile_communities = self.analyzer._extract_communities_from_text(user.description, confidence=0.8)
                        communities.extend(profile_communities)
                        self.logger.info(f"👤 Profile analysis found {len(profile_communities)} communities")
                except Exception as e:
                    self.logger.debug(f"Profile analysis failed: {e}")
                
                # Method 3: Post-based community tracking (creation/joining detection)
                post_communities = await self.post_tracker.detect_community_activities(user.id, hours_lookback=24)
                communities = self.diff_analyzer.merge_community_lists(communities, post_communities)
                self.logger.info(f"📝 Post analysis found {len(post_communities)} communities")
                
                # Method 4: Social graph analysis
                social_communities = await self.detector.detect_via_social_graph(user.id)
                communities = self.diff_analyzer.merge_community_lists(communities, social_communities)
                self.logger.info(f"👥 Social graph analysis found {len(social_communities)} communities")
                
                # Method 5: Activity pattern analysis
                activity_communities = await self.analyzer.detect_via_activity_patterns(user.id)
                communities = self.diff_analyzer.merge_community_lists(communities, activity_communities)
                self.logger.info(f"📊 Activity pattern analysis found {len(activity_communities)} communities")
                
                # Method 6: Content analysis
                content_communities = await self.analyzer.detect_via_content_analysis(user.id)
                communities = self.diff_analyzer.merge_community_lists(communities, content_communities)
                self.logger.info(f"📊 Content analysis found {len(content_communities)} communities")
                
            else:
                self.logger.info("⚡ Using fast community detection")
                
                # Just use the most reliable methods
                url_communities = await self.detector.get_communities_from_urls(user.id)
                post_communities = await self.post_tracker.detect_community_activities(user.id, hours_lookback=12)
                communities = self.diff_analyzer.merge_community_lists(url_communities, post_communities)
            
            self.logger.info(f"📊 Total current communities found: {len(communities)}")
            
            # Log each community with details
            for i, community in enumerate(communities, 1):
                confidence = getattr(community, 'confidence', 'N/A')
                theme = getattr(community, 'theme', 'unknown')
                self.logger.info(f"  {i}. {community.name} (ID: {community.id}, Role: {community.role}, Theme: {theme}, Confidence: {confidence})")
            
            return TwitterUserCommunityPayload(
                user_id=str(user.id),
                screen_name=user.username,
                name=user.displayname or user.username,
                verified=getattr(user, 'verified', False),
                is_blue_verified=getattr(user, 'blue_verified', False),
                profile_image_url_https=getattr(user, 'profileImageUrl', ''),
                communities=communities
            )
            
        except Exception as e:
            self.logger.error(f"Error getting current communities for @{username}: {e}")
            return None
    
    async def track_community_changes(self, username: str, previous_communities: List[Community], deep_scan: bool = True) -> Dict[str, Any]:
        """
        Track community changes with enhanced detection methods
        
        Args:
            username: Twitter username
            previous_communities: Previously detected communities
            deep_scan: If True, uses comprehensive detection. If False, uses lightweight monitoring
        """
        self.logger.info(f"🔄 Tracking community changes for @{username} (Previous: {len(previous_communities)} communities)")
        
        try:
            # For monitoring (not deep_scan), use lightweight detection
            if not deep_scan:
                self.logger.info(f"⚡ Using lightweight monitoring mode for @{username}")
                current_communities = await self._get_communities_lightweight_monitoring(username)
            else:
                self.logger.info(f"🔍 Getting current Twitter Communities for @{username} (Deep scan: {deep_scan})")
                current_communities = await self.get_current_communities_comprehensive(username)
            
            if not current_communities:
                self.logger.warning(f"No current communities found for @{username}")
                return {
                    'success': True,
                    'changes': {'joined': [], 'left': [], 'created': [], 'role_changes': []},
                    'summary': 'No communities detected'
                }
            
            # Calculate differences
            diff = self.diff_analyzer.calculate_differences(previous_communities, current_communities)
            
            # Enhanced change detection for additional insights
            enhanced_changes = await self._detect_enhanced_changes(username, previous_communities, current_communities)
            
            # Filter and validate changes
            if deep_scan:
                # Only apply confidence filtering for deep scans
                filtered_diff = self.diff_analyzer.filter_and_validate_changes(diff)
            else:
                # For lightweight monitoring (Selenium), trust all detections
                filtered_diff = diff
                self.logger.info(f"🎯 Bypassing confidence filter for lightweight monitoring")
            
            # Calculate confidence score
            if deep_scan:
                confidence_score = self.diff_analyzer.calculate_change_confidence(filtered_diff, enhanced_changes)
            else:
                # For lightweight monitoring, use high confidence since we trust Selenium
                confidence_score = 0.95 if any(len(changes) > 0 for changes in filtered_diff.values()) else 0.0
            
            # Generate summary
            total_changes = sum(len(changes) for changes in filtered_diff.values())
            summary = f"Found {len(current_communities)} communities, {total_changes} changes detected"
            
            result = {
                'success': True,
                'user': {
                    'username': username,
                    'display_name': current_payload.name if 'current_payload' in locals() else username,
                    'user_id': getattr(current_payload, 'user_id', None) if 'current_payload' in locals() else None
                },
                'detection_methods': enhanced_changes.get('methods_used', []),
                'changes': filtered_diff,
                'raw_changes': diff,  # Unfiltered for debugging
                'enhanced_detections': enhanced_changes.get('new_detections', []),
                'confidence_score': confidence_score,
                'summary': summary,
                'scan_type': 'deep' if deep_scan else 'lightweight_monitoring',
                'timestamp': datetime.now().isoformat(),
                'total_current_communities': len(current_communities),
                'total_previous_communities': len(previous_communities)
            }
            
            # Log results
            total_changes = sum(len(changes) for changes in filtered_diff.values())
            self.logger.info(f"📊 Change detection complete: {total_changes} filtered changes found")
            self.logger.info(f"📊 Confidence score: {confidence_score:.2f}")
            self.logger.info(f"📊 Methods used: {', '.join(enhanced_changes.get('methods_used', []))}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error tracking community changes for @{username}: {e}")
            return {
                'success': False,
                'error': str(e),
                'changes': {},
                'summary': f'Error tracking changes: {str(e)}'
            }
    
    async def _get_communities_lightweight_monitoring(self, username: str) -> List[Community]:
        """
        Lightweight community detection for monitoring - SELENIUM ONLY
        
        Simple approach:
        1. Selenium detection (finds the actual HTML elements)
        2. Report findings
        3. Schedule next check
        4. Done - no excessive scanning
        """
        self.logger.info(f"⚡ Lightweight Selenium-only monitoring for @{username}")
        communities = []
        
        try:
            # Get user info
            user = await self.api.user_by_login(username)
            if not user:
                self.logger.error(f"User @{username} not found")
                return []

            display_name = getattr(user, 'display_name', getattr(user, 'name', username))
            self.logger.info(f"Found user: {display_name} (@{user.username}, ID: {user.id})")
            
            # ONLY Method: Selenium-based HTML Element Detection
            try:
                from bot.selenium_community_detector import SeleniumCommunityDetector
                selenium_detector = SeleniumCommunityDetector(self.cookie_manager)
                
                # Use the same cookie selection logic as scheduler
                saved_cookies = self.cookie_manager.list_cookie_sets()
                if saved_cookies:
                    cookie_name = saved_cookies[0]['name']  # Most recent cookie set
                else:
                    cookie_name = "default"
                
                self.logger.info(f"🌐 Using Selenium detector with cookie: {cookie_name}")
                html_detections = await selenium_detector.detect_communities(username, cookie_name)
                
                # Convert SeleniumCommunityDetector results to Community objects
                for detection in html_detections:
                    community = Community(
                        id=detection.community_id,
                        name=detection.name,
                        description="",
                        member_count=0,
                        is_nsfw=False,
                        theme="selenium_detected",
                        created_at=None,
                        admin_id="",
                        role="Member",  # Default role
                        joined_at=None
                    )
                    communities.append(community)
                
                self.logger.info(f"🎯 Selenium detection found {len(html_detections)} communities")
                
            except Exception as e:
                self.logger.error(f"Selenium detection failed: {e}")
            
            # Remove duplicates (simple)
            unique_communities = []
            for community in communities:
                if not any(c.id == community.id for c in unique_communities):
                    unique_communities.append(community)
            
            self.logger.info(f"⚡ Lightweight monitoring complete: {len(unique_communities)} unique communities")
            return unique_communities
            
        except Exception as e:
            self.logger.error(f"Error in lightweight monitoring for @{username}: {e}")
            return []
    
    async def _detect_enhanced_changes(self, username: str, previous_communities: List[Community], current_communities: List[Community]) -> Dict[str, Any]:
        """
        SIMPLIFIED - No enhanced detection, just return empty results
        """
        return {
            'methods_used': ['selenium_only'],
            'new_detections': []
        }
    
    async def get_community_creation_activities(self, username: str, hours_lookback: int = 24) -> List[Community]:
        """
        Get communities that the user has created recently
        """
        try:
            user = await self.api.user_by_login(username)
            if not user:
                return []
            
            return await self.post_tracker.detect_community_creation(user.id, hours_lookback=hours_lookback)
        
        except Exception as e:
            self.logger.error(f"Error getting community creation activities: {e}")
            return []
    
    async def get_community_joining_activities(self, username: str, hours_lookback: int = 24) -> List[Community]:
        """
        Get communities that the user has joined recently
        """
        try:
            user = await self.api.user_by_login(username)
            if not user:
                return []
            
            return await self.post_tracker.detect_community_joining(user.id, hours_lookback=hours_lookback)
        
        except Exception as e:
            self.logger.error(f"Error getting community joining activities: {e}")
            return []
    
    async def analyze_community_engagement(self, username: str, community_id: str) -> Dict[str, Any]:
        """
        Analyze user's engagement with a specific community
        """
        try:
            user = await self.api.user_by_login(username)
            if not user:
                return {'error': 'User not found'}
            
            # Get recent tweets
            tweets = []
            async for tweet in self.api.user_tweets(user.id, limit=100):
                tweets.append(tweet)
                if len(tweets) >= 100:
                    break
            
            if not tweets:
                return {'engagement_level': 'none', 'activities': []}
            
            # Analyze engagement patterns
            engagement_data = await self.analyzer.analyze_engagement_patterns_for_communities(tweets, user.id)
            
            # Filter for specific community
            community_engagement = [c for c in engagement_data if c.id == community_id]
            
            return {
                'engagement_level': 'high' if community_engagement else 'low',
                'activities': community_engagement,
                'total_analyzed_tweets': len(tweets)
            }
        
        except Exception as e:
            self.logger.error(f"Error analyzing community engagement: {e}")
            return {'error': str(e)}
    
    def get_detection_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the detection methods and their performance
        """
        return {
            'available_methods': {
                'url_extraction': 'Extract community IDs from shared Twitter Community URLs',
                'profile_analysis': 'Analyze user profile for community links',
                'post_tracking': 'Detect creation and joining announcements in posts',
                'social_graph': 'Analyze following/followers for community accounts',
                'activity_patterns': 'Detect community involvement through hashtags and mentions',
                'content_analysis': 'Identify communities through content themes',
                'temporal_analysis': 'Detect community events through activity bursts',
                'engagement_analysis': 'Identify communities through interaction patterns'
            },
            'confidence_levels': {
                'url_based': 0.9,
                'post_creation': 0.85,
                'post_joining': 0.75,
                'hashtag_patterns': 0.7,
                'mention_patterns': 0.7,
                'content_themes': 0.6,
                'social_graph': 0.5,
                'temporal_patterns': 0.4
            },
            'scan_modes': {
                'deep': 'Uses all available detection methods for maximum accuracy',
                'quick': 'Uses only the most reliable methods for faster results'
            }
        } 