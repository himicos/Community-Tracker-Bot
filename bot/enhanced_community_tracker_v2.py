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
            
            self.logger.info(f"Found user: {user.displayname} (@{user.username}, ID: {user.id})")
            
            # Get actual current communities using multiple detection methods
            all_communities = []
            
            if deep_scan:
                self.logger.info("🔍 Using comprehensive community detection")
                
                # Method 1: URL extraction from tweets (most reliable)
                url_communities = await self.detector.get_communities_from_urls(user.id)
                all_communities.extend(url_communities)
                
                # Method 2: Profile analysis for community links
                profile_communities = await self.detector.get_communities_from_profile(user)
                all_communities = self.diff_analyzer.merge_community_lists(all_communities, profile_communities)
                
                # Method 3: Post-based community tracking (creation/joining detection)
                post_communities = await self.post_tracker.detect_community_activities(user.id, hours_lookback=24)
                all_communities = self.diff_analyzer.merge_community_lists(all_communities, post_communities)
                
                # Method 4: Social graph analysis
                social_communities = await self.detector.detect_via_social_graph(user.id)
                all_communities = self.diff_analyzer.merge_community_lists(all_communities, social_communities)
                
                # Method 5: Activity pattern analysis
                activity_communities = await self.analyzer.detect_via_activity_patterns(user.id)
                all_communities = self.diff_analyzer.merge_community_lists(all_communities, activity_communities)
                
                # Method 6: Content analysis
                content_communities = await self.analyzer.detect_via_content_analysis(user.id)
                all_communities = self.diff_analyzer.merge_community_lists(all_communities, content_communities)
                
            else:
                self.logger.info("⚡ Using fast community detection")
                
                # Just use the most reliable methods
                url_communities = await self.detector.get_communities_from_urls(user.id)
                post_communities = await self.post_tracker.detect_community_activities(user.id, hours_lookback=12)
                all_communities = self.diff_analyzer.merge_community_lists(url_communities, post_communities)
            
            self.logger.info(f"📊 Total current communities found: {len(all_communities)}")
            
            # Log each community with details
            for i, community in enumerate(all_communities, 1):
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
                communities=all_communities
            )
            
        except Exception as e:
            self.logger.error(f"Error getting current communities for @{username}: {e}")
            return None
    
    async def track_community_changes(self, username: str, previous_communities: List[Community], deep_scan: bool = True) -> Dict[str, Any]:
        """
        Track community changes for a user using enhanced detection methods
        
        Args:
            username: Twitter username (without @)
            previous_communities: List of previously detected communities
            deep_scan: Whether to use deep scanning methods
            
        Returns:
            Dict containing change detection results
        """
        self.logger.info(f"🔄 Tracking community changes for @{username} (Previous: {len(previous_communities)} communities)")
        
        try:
            # Get current communities
            current_payload = await self.get_all_user_communities(username, deep_scan=deep_scan)
            if not current_payload:
                return {
                    'success': False,
                    'error': 'Failed to get current communities',
                    'changes': {},
                    'summary': 'Error occurred during community detection'
                }
            
            current_communities = current_payload.communities
            
            # Enhanced change detection using multiple methods
            enhanced_changes = await self._detect_enhanced_changes(username, previous_communities, current_communities)
            
            # Detailed difference analysis
            diff = self.diff_analyzer.detailed_community_diff(previous_communities, current_communities)
            
            # Filter high-confidence changes
            filtered_diff = self.diff_analyzer.filter_high_confidence_changes(diff, min_confidence=0.6)
            
            # Calculate confidence score
            confidence_score = self.diff_analyzer.calculate_confidence_score(current_communities)
            
            # Generate summary
            summary = self.diff_analyzer.generate_change_summary(filtered_diff)
            
            # Compile result
            result = {
                'success': True,
                'user': {
                    'username': username,
                    'display_name': current_payload.name,
                    'user_id': current_payload.user_id
                },
                'detection_methods': enhanced_changes.get('methods_used', []),
                'changes': filtered_diff,
                'raw_changes': diff,  # Unfiltered for debugging
                'enhanced_detections': enhanced_changes.get('new_detections', []),
                'confidence_score': confidence_score,
                'summary': summary,
                'scan_type': 'deep' if deep_scan else 'quick',
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
    
    async def _detect_enhanced_changes(self, username: str, previous_communities: List[Community], current_communities: List[Community]) -> Dict[str, Any]:
        """
        Enhanced change detection using multiple analysis methods
        """
        enhanced_result = {
            'methods_used': [],
            'new_detections': []
        }
        
        try:
            # Method 1: Post-based activity analysis
            try:
                post_detections = await self.analyzer.detect_communities_via_enhanced_activity(username, previous_communities)
                if post_detections:
                    enhanced_result['methods_used'].append('post_analysis')
                    enhanced_result['new_detections'].extend(post_detections)
                    self.logger.info(f"📝 Post analysis found {len(post_detections)} additional community indicators")
            except Exception as e:
                self.logger.debug(f"Post analysis failed: {e}")
            
            # Method 2: Temporal pattern analysis (analyze recent activity for community events)
            try:
                user = await self.api.user_by_login(username)
                if user:
                    tweets = []
                    async for tweet in self.api.user_tweets(user.id, limit=50):
                        tweets.append(tweet)
                        if len(tweets) >= 50:
                            break
                    
                    if tweets:
                        temporal_communities = await self.analyzer._analyze_temporal_patterns(tweets)
                        if temporal_communities:
                            enhanced_result['methods_used'].append('temporal_analysis')
                            enhanced_result['new_detections'].extend(temporal_communities)
                            self.logger.info(f"⏰ Temporal analysis found {len(temporal_communities)} community indicators")
            except Exception as e:
                self.logger.debug(f"Temporal analysis failed: {e}")
            
            # Method 3: Post tracker creation/joining detection
            try:
                user = await self.api.user_by_login(username)
                if user:
                    creation_detections = await self.post_tracker.detect_community_creation(user.id, hours_lookback=24)
                    joining_detections = await self.post_tracker.detect_community_joining(user.id, hours_lookback=24)
                    
                    all_post_detections = creation_detections + joining_detections
                    if all_post_detections:
                        enhanced_result['methods_used'].append('creation_joining_detection')
                        enhanced_result['new_detections'].extend(all_post_detections)
                        self.logger.info(f"🆕 Creation/joining analysis found {len(all_post_detections)} community activities")
            except Exception as e:
                self.logger.debug(f"Creation/joining detection failed: {e}")
            
            # Remove duplicates from enhanced detections
            unique_detections = []
            for detection in enhanced_result['new_detections']:
                if not self.diff_analyzer.is_duplicate_community(detection, unique_detections):
                    unique_detections.append(detection)
            
            enhanced_result['new_detections'] = unique_detections
            
            self.logger.info(f"🔍 Enhanced detection methods used: {', '.join(enhanced_result['methods_used'])}")
            self.logger.info(f"🔍 Enhanced detections found: {len(enhanced_result['new_detections'])}")
            
        except Exception as e:
            self.logger.error(f"Error in enhanced change detection: {e}")
        
        return enhanced_result
    
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