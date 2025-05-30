#!/usr/bin/env python3
"""
Advanced Community Extractor

This module attempts to extract community metadata that appears in the DOM
but is not included in the standard Twitter API responses.
"""

import asyncio
import logging
import re
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from twscrape import API
from bot.models import Community


class AdvancedCommunityExtractor:
    """
    Advanced Community Extraction System
    
    This class attempts to extract community metadata from various sources
    including client-side rendered data that's not in the API responses.
    """
    
    def __init__(self, api: API):
        self.api = api
        self.logger = logging.getLogger(__name__)
        
    async def extract_communities_advanced(self, user_id: int) -> List[Community]:
        """
        Extract communities using advanced techniques that go beyond basic API responses
        """
        communities = []
        
        try:
            self.logger.info(f"🔍 Starting advanced community extraction for user {user_id}")
            
            # Method 1: Try to get tweet HTML content if available
            html_communities = await self._extract_from_tweet_html(user_id)
            communities.extend(html_communities)
            
            # Method 2: Enhanced pattern matching with context
            pattern_communities = await self._extract_with_enhanced_patterns(user_id)
            # Merge avoiding duplicates
            existing_ids = {c.id for c in communities}
            new_pattern_communities = [c for c in pattern_communities if c.id not in existing_ids]
            communities.extend(new_pattern_communities)
            
            # Method 3: Cross-reference with known community indicators
            indicator_communities = await self._extract_from_community_indicators(user_id)
            existing_ids = {c.id for c in communities}
            new_indicator_communities = [c for c in indicator_communities if c.id not in existing_ids]
            communities.extend(new_indicator_communities)
            
            self.logger.info(f"✅ Advanced extraction found {len(communities)} communities")
            
        except Exception as e:
            self.logger.error(f"Error in advanced community extraction: {e}")
        
        return communities
    
    async def _extract_from_tweet_html(self, user_id: int) -> List[Community]:
        """
        Attempt to extract community data from HTML/DOM content if available
        """
        communities = []
        
        try:
            # Get tweets and check if there's any way to access HTML content
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=10):  # Only check last 10 tweets
                tweets.append(tweet)
            
            self.logger.info(f"🔍 Checking {len(tweets)} tweets for HTML community data")
            
            for tweet in tweets:
                try:
                    # Check if tweet has any HTML-like content or raw response data
                    html_content = self._get_tweet_html_content(tweet)
                    
                    if html_content:
                        # Look for the specific HTML patterns you found
                        community_data = self._parse_html_community_data(html_content)
                        
                        for community_info in community_data:
                            community = Community(
                                id=community_info['id'],
                                name=community_info['name'],
                                description=f"Community detected from HTML data - Role: {community_info['role']}",
                                member_count=0,
                                role=community_info['role'],
                                is_nsfw=False,
                                created_at=datetime.utcnow().isoformat()
                            )
                            communities.append(community)
                            
                            self.logger.info(f"✅ Found community via HTML: {community.name} (Role: {community.role})")
                
                except Exception as e:
                    self.logger.debug(f"Error checking tweet HTML: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error extracting from HTML: {e}")
        
        return communities
    
    def _get_tweet_html_content(self, tweet) -> Optional[str]:
        """
        Try to get HTML content from tweet object
        """
        try:
            # Check various attributes that might contain HTML
            html_attrs = ['html', 'raw_html', 'content_html', 'full_html']
            for attr in html_attrs:
                if hasattr(tweet, attr):
                    content = getattr(tweet, attr)
                    if content and isinstance(content, str) and 'data-testid' in content:
                        return content
            
            # Check if any string attributes contain HTML-like content
            all_attrs = [attr for attr in dir(tweet) if not attr.startswith('_')]
            for attr in all_attrs:
                try:
                    value = getattr(tweet, attr)
                    if isinstance(value, str) and ('data-testid="socialContext"' in value or '<span' in value):
                        return value
                except Exception:
                    continue
            
        except Exception as e:
            self.logger.debug(f"Error getting HTML content: {e}")
        
        return None
    
    def _parse_html_community_data(self, html_content: str) -> List[Dict[str, str]]:
        """
        Parse the HTML content for community metadata
        """
        communities = []
        
        try:
            # Pattern 1: Look for socialContext with community names
            social_context_pattern = r'data-testid="socialContext"[^>]*>.*?<span[^>]*>([^<]+)</span>'
            matches = re.findall(social_context_pattern, html_content, re.DOTALL)
            
            for match in matches:
                community_name = match.strip()
                if len(community_name) > 2:  # Valid community name
                    community_id = f"html_{abs(hash(community_name.lower())) % 1000000}"
                    communities.append({
                        'id': community_id,
                        'name': community_name,
                        'role': 'Member'  # Default role
                    })
            
            # Pattern 2: Look for community URLs with IDs
            community_url_pattern = r'href="/i/communities/(\d+)"[^>]*>.*?<span[^>]*>([^<]+)</span>'
            url_matches = re.findall(community_url_pattern, html_content, re.DOTALL)
            
            for community_id, community_name in url_matches:
                if len(community_id) >= 15:  # Valid Twitter ID
                    communities.append({
                        'id': community_id,
                        'name': community_name.strip(),
                        'role': 'Member'
                    })
            
            # Pattern 3: Look for role information
            role_pattern = r'<span[^>]*>(Admin|Member|Moderator)</span>'
            role_matches = re.findall(role_pattern, html_content)
            
            # If we found roles and communities, try to match them
            if role_matches and communities:
                for i, role in enumerate(role_matches):
                    if i < len(communities):
                        communities[i]['role'] = role
            
        except Exception as e:
            self.logger.debug(f"Error parsing HTML community data: {e}")
        
        return communities
    
    async def _extract_with_enhanced_patterns(self, user_id: int) -> List[Community]:
        """
        Use enhanced pattern matching to detect community involvement
        """
        communities = []
        
        try:
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=10):  # Only check last 10 tweets
                tweets.append(tweet)
            
            self.logger.info(f"🔍 Enhanced pattern matching on {len(tweets)} tweets")
            
            # Enhanced patterns based on your real community examples
            enhanced_patterns = [
                # Direct community building/management patterns
                {
                    'pattern': r'(?:built|created|founded|started)\s+(?:the\s+)?(\w+(?:\s+\w+)*)\s+community',
                    'role': 'Admin',
                    'confidence': 'high'
                },
                {
                    'pattern': r'(?:admin|moderator|leader)\s+(?:of\s+)?(?:the\s+)?(\w+(?:\s+\w+)*)\s+community',
                    'role': 'Admin',
                    'confidence': 'high'
                },
                
                # Community tool/tracking patterns (like your examples)
                {
                    'pattern': r'(\w+(?:\s+\w+)*)\s+community\s+(?:tracking|tracker|tool|bot)',
                    'role': 'Developer',
                    'confidence': 'high'
                },
                {
                    'pattern': r'track\s+(?:what\s+)?communities\s+(?:user\s+)?(?:joins|member)',
                    'role': 'Developer',
                    'confidence': 'medium'
                },
                
                # Active participation patterns
                {
                    'pattern': r'(?:joined|part\s+of|member\s+of)\s+(?:the\s+)?(\w+(?:\s+\w+)*)\s+community',
                    'role': 'Member',
                    'confidence': 'medium'
                },
                {
                    'pattern': r'(?:active\s+in|contributing\s+to)\s+(?:the\s+)?(\w+(?:\s+\w+)*)',
                    'role': 'Member',
                    'confidence': 'medium'
                },
                
                # Specific community names (from your examples)
                {
                    'pattern': r'(developers?\s+club|build\s+in\s+public|indie\s+hackers?)',
                    'role': 'Member',
                    'confidence': 'high'
                }
            ]
            
            community_detections = {}
            
            for tweet in tweets:
                try:
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    
                    for pattern_info in enhanced_patterns:
                        pattern = pattern_info['pattern']
                        role = pattern_info['role']
                        confidence = pattern_info['confidence']
                        
                        matches = re.findall(pattern, tweet_text, re.IGNORECASE)
                        
                        for match in matches:
                            if isinstance(match, tuple):
                                community_name = ' '.join(match).strip()
                            else:
                                community_name = match.strip()
                            
                            # Filter out common false positives
                            if self._is_valid_community_name(community_name):
                                community_key = community_name.lower()
                                
                                if community_key not in community_detections:
                                    community_detections[community_key] = {
                                        'name': community_name.title(),
                                        'role': role,
                                        'confidence': confidence,
                                        'occurrences': 0
                                    }
                                
                                community_detections[community_key]['occurrences'] += 1
                                
                                # Upgrade role if we find higher authority evidence
                                if role == 'Admin' and community_detections[community_key]['role'] == 'Member':
                                    community_detections[community_key]['role'] = 'Admin'
                
                except Exception as e:
                    self.logger.debug(f"Error in pattern matching: {e}")
                    continue
            
            # Create Community objects from detections
            for community_data in community_detections.values():
                if community_data['occurrences'] >= 1:  # At least one mention
                    community_id = f"pattern_{abs(hash(community_data['name'].lower())) % 1000000}"
                    
                    community = Community(
                        id=community_id,
                        name=community_data['name'],
                        description=f"Community detected via enhanced patterns (confidence: {community_data['confidence']}, mentions: {community_data['occurrences']})",
                        member_count=0,
                        role=community_data['role'],
                        is_nsfw=False,
                        created_at=datetime.utcnow().isoformat()
                    )
                    
                    communities.append(community)
                    self.logger.info(f"✅ Enhanced pattern detected: {community.name} (Role: {community.role})")
            
        except Exception as e:
            self.logger.error(f"Error in enhanced pattern extraction: {e}")
        
        return communities
    
    def _is_valid_community_name(self, name: str) -> bool:
        """
        Check if the detected name is likely a valid community name
        """
        if not name or len(name) < 2:
            return False
        
        # Filter out common false positives
        false_positives = {
            'the', 'this', 'that', 'and', 'or', 'user', 'what', 'when', 'how', 'where', 'why',
            'all', 'some', 'many', 'few', 'other', 'same', 'new', 'old', 'first', 'last',
            'good', 'bad', 'big', 'small', 'long', 'short', 'high', 'low', 'best', 'worst'
        }
        
        name_lower = name.lower().strip()
        if name_lower in false_positives:
            return False
        
        # Must contain at least one letter
        if not re.search(r'[a-zA-Z]', name):
            return False
        
        return True
    
    async def _extract_from_community_indicators(self, user_id: int) -> List[Community]:
        """
        Extract communities based on known community indicators
        """
        communities = []
        
        try:
            tweets = []
            async for tweet in self.api.user_tweets(user_id, limit=10):  # Only check last 10 tweets
                tweets.append(tweet)
            
            self.logger.info(f"🔍 Checking {len(tweets)} tweets for community indicators")
            
            # Look for mentions that suggest community involvement
            community_mention_patterns = [
                r'@(\w*community\w*)',
                r'@(\w*builders?\w*)',
                r'@(\w*makers?\w*)',
                r'@(\w*indie\w*)',
                r'@(\w*dev\w*)',
                r'@(\w*crypto\w*)',
                r'@(\w*dao\w*)',
                r'@(\w*guild\w*)',
                r'@(\w*club\w*)',
                r'@(\w*collective\w*)'
            ]
            
            mentioned_communities = set()
            
            for tweet in tweets:
                try:
                    tweet_text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                    
                    for pattern in community_mention_patterns:
                        matches = re.findall(pattern, tweet_text, re.IGNORECASE)
                        for mention in matches:
                            if len(mention) > 3:  # Filter short matches
                                mentioned_communities.add(mention.lower())
                
                except Exception as e:
                    continue
            
            # Create communities from mentions
            for mention in mentioned_communities:
                community_id = f"mention_{abs(hash(mention)) % 1000000}"
                
                community = Community(
                    id=community_id,
                    name=f"{mention.title()} Community",
                    description=f"Community detected via @{mention} mentions",
                    member_count=0,
                    role="Member",
                    is_nsfw=False,
                    created_at=datetime.utcnow().isoformat()
                )
                
                communities.append(community)
                self.logger.info(f"✅ Community indicator found: @{mention}")
            
        except Exception as e:
            self.logger.error(f"Error extracting community indicators: {e}")
        
        return communities 