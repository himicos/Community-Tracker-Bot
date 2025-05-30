#!/usr/bin/env python3
"""
Browser-Based Community Detector

This module uses browser automation to capture real DOM community metadata
that's client-side rendered in the DOM but not available via API.
"""

import asyncio
import logging
import json
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from bot.models import Community
from bot.cookie_manager import CookieManager


class BrowserCommunityDetector:
    """
    Browser-based community detection using real DOM data
    """
    
    def __init__(self, cookie_manager: CookieManager):
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
        self.driver = None
        self.previous_communities = {}  # Cache for comparison
        
    async def detect_real_communities(self, username: str, max_tweets: int = 10) -> List[Community]:
        """
        Detect real communities using browser automation with DOM parsing
        Limited to recent posts for faster detection
        """
        try:
            self.logger.info(f"🌐 Starting browser-based community detection for @{username}")
            
            # Initialize browser
            await self._init_browser()
            
            # Navigate to user's profile
            user_url = f"https://x.com/{username}"
            self.driver.get(user_url)
            
            # Wait for page to load
            await self._wait_for_page_load()
            
            # Collect tweets with community data (limited to recent 10)
            community_tweets = await self._collect_community_tweets(max_tweets)
            
            # Parse communities from DOM data
            all_communities = await self._parse_dom_communities(community_tweets)
            
            # Filter to only NEW communities
            new_communities = await self._filter_new_communities(username, all_communities)
            
            self.logger.info(f"📊 Collected {len(community_tweets)} tweets with community data")
            self.logger.info(f"✅ Browser detection found {len(new_communities)} NEW communities")
            
            return new_communities
            
        except Exception as e:
            self.logger.error(f"Error in browser community detection: {e}")
            return []
        
        finally:
            await self._cleanup_browser()
    
    async def _init_browser(self):
        """Initialize Chrome browser with inherited cookies"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            
            # Navigate to Twitter first
            self.driver.get("https://x.com")
            time.sleep(2)
            
            # Get cookies from cookie manager and add them to browser
            cookies = await self._get_cookies_from_manager()
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    self.logger.debug(f"Failed to add cookie: {e}")
            
            self.logger.info("✅ Browser initialized with authentication cookies")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {e}")
            raise
    
    async def _get_cookies_from_manager(self) -> List[Dict]:
        """Get cookies from the existing cookie manager"""
        try:
            # Get available cookie sets
            cookie_sets = self.cookie_manager.list_cookie_sets()
            
            if not cookie_sets:
                self.logger.warning("No cookies available from cookie manager")
                return []
            
            # Find the most recently used cookie set (first in list should be most recent)
            cookie_set = None
            for available_set in cookie_sets:
                try:
                    cookie_set = self.cookie_manager.load_cookies(available_set['name'])
                    if cookie_set and cookie_set.auth_token:
                        self.logger.info(f"Using cookie set: {available_set['name']}")
                        break
                except Exception as e:
                    self.logger.debug(f"Failed to load cookie set {available_set['name']}: {e}")
                    continue
            
            if not cookie_set:
                self.logger.warning("No valid cookies found")
                return []
            
            # Convert cookie set to Selenium format
            cookies = []
            
            # Auth token cookie
            if cookie_set.auth_token:
                cookies.append({
                    'name': 'auth_token',
                    'value': cookie_set.auth_token,
                    'domain': '.x.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': True
                })
            
            # CSRF token cookie
            if cookie_set.ct0:
                cookies.append({
                    'name': 'ct0',
                    'value': cookie_set.ct0,
                    'domain': '.x.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': False
                })
            
            # Optional cookies
            if cookie_set.guest_id:
                cookies.append({
                    'name': 'guest_id',
                    'value': cookie_set.guest_id,
                    'domain': '.x.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': False
                })
            
            if cookie_set.personalization_id:
                cookies.append({
                    'name': 'personalization_id',
                    'value': cookie_set.personalization_id,
                    'domain': '.x.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': False
                })
            
            if cookie_set.guest_id_ads:
                cookies.append({
                    'name': 'guest_id_ads',
                    'value': cookie_set.guest_id_ads,
                    'domain': '.x.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': False
                })
            
            if cookie_set.guest_id_marketing:
                cookies.append({
                    'name': 'guest_id_marketing',
                    'value': cookie_set.guest_id_marketing,
                    'domain': '.x.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': False
                })
            
            self.logger.info(f"Retrieved {len(cookies)} cookies from cookie manager")
            return cookies
            
        except Exception as e:
            self.logger.error(f"Error getting cookies: {e}")
            return []
    
    async def _wait_for_page_load(self):
        """Wait for Twitter page to fully load"""
        try:
            # Wait for main content to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']"))
            )
            
            # Additional wait for dynamic content
            time.sleep(3)
            
        except TimeoutException:
            self.logger.warning("Page load timeout - proceeding anyway")
    
    async def _collect_community_tweets(self, max_tweets: int) -> List[Dict]:
        """Collect tweets with community data from the browser DOM - FAST VERSION"""
        community_tweets = []
        
        try:
            # Wait for initial tweets to load
            await asyncio.sleep(2)  # Reduced wait time
            
            # Get tweet elements quickly
            tweet_selectors = [
                "[data-testid='tweet']",
                "article[data-testid='tweet']"
            ]
            
            all_tweet_elements = []
            for selector in tweet_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    all_tweet_elements.extend(elements)
                    self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                except:
                    continue
            
            if not all_tweet_elements:
                self.logger.warning("No tweet elements found")
                return community_tweets
            
            # Process only the number we need
            tweets_to_process = min(len(all_tweet_elements), max_tweets)
            self.logger.info(f"🔍 Processing {tweets_to_process} tweet elements for community data")
            
            for i, tweet_element in enumerate(all_tweet_elements[:tweets_to_process]):
                try:
                    # Extract community data (ONLY real communities)
                    community_data = await self._extract_tweet_community_data(tweet_element)
                    
                    if community_data:
                        community_tweets.append({
                            'tweet_index': i,
                            'community_data': community_data
                        })
                        # Stop after finding max communities (speed up)
                        if len(community_tweets) >= 5:  # Max 5 communities per scan
                            break
                
                except Exception as e:
                    self.logger.debug(f"Error processing tweet {i}: {e}")
                    continue
            
            self.logger.info(f"✅ Found {len(community_tweets)} tweets with REAL community data")
            
        except Exception as e:
            self.logger.error(f"Error collecting community tweets: {e}")
        
        return community_tweets
    
    async def _extract_tweet_community_data(self, tweet_element) -> Optional[Dict]:
        """Extract REAL community metadata from tweet DOM element - FAST & ACCURATE"""
        try:
            # Method 1: Look for socialContext element (PRIMARY - REAL communities only)
            try:
                social_context = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='socialContext']")
                community_name = social_context.text.strip()
                
                if community_name and len(community_name) < 50 and community_name != "Member":  # Real community names are short, not role text
                    # Try to find community URL for ID (look in parent link)
                    community_id = None
                    try:
                        # Look for parent link with community URL
                        parent_link = social_context.find_element(By.XPATH, ".//ancestor::a[contains(@href, '/i/communities/')]")
                        href = parent_link.get_attribute('href')
                        if '/i/communities/' in href:
                            community_id = href.split('/i/communities/')[-1].split('?')[0].split('/')[0]
                    except:
                        # Try to find any community link in the same tweet
                        try:
                            community_link = tweet_element.find_element(By.CSS_SELECTOR, "a[href*='/i/communities/']")
                            href = community_link.get_attribute('href')
                            if '/i/communities/' in href:
                                community_id = href.split('/i/communities/')[-1].split('?')[0].split('/')[0]
                        except:
                            community_id = f"social_{abs(hash(community_name.lower())) % 1000000}"
                    
                    # Try to find role (Member, Admin, etc.)
                    role = "Member"  # Default
                    try:
                        # Look for role text in the tweet element
                        role_elements = tweet_element.find_elements(By.XPATH, ".//span[text()='Admin' or text()='Member' or text()='Moderator']")
                        if role_elements:
                            role = role_elements[0].text.strip()
                    except:
                        pass
                    
                    self.logger.info(f"✅ Found community data: {community_name} (source: socialContext, ID: {community_id})")
                    return {
                        'name': community_name,
                        'id': community_id,
                        'role': role,
                        'source': 'socialContext'  # REAL community membership
                    }
            except:
                pass
            
            # Method 2: Look for direct community links (SECONDARY - also real)
            try:
                community_link = tweet_element.find_element(By.CSS_SELECTOR, "a[href*='/i/communities/']")
                href = community_link.get_attribute('href')
                community_id = href.split('/i/communities/')[-1].split('?')[0].split('/')[0]
                
                # Get community name from link text or nearby elements
                community_name = community_link.text.strip()
                if not community_name:
                    # Try to get name from nested spans
                    try:
                        name_span = community_link.find_element(By.CSS_SELECTOR, "span")
                        community_name = name_span.text.strip()
                    except:
                        pass
                
                if community_name and len(community_name) < 50 and community_name != "Member":  # Filter out role text
                    self.logger.info(f"✅ Found community data: {community_name} (source: directLink, ID: {community_id})")
                    return {
                        'name': community_name,
                        'id': community_id,
                        'role': 'Member',
                        'source': 'directLink'  # REAL community link
                    }
            except:
                pass
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error extracting community data: {e}")
            return None
    
    async def _get_tweet_text(self, tweet_element) -> str:
        """Get tweet text content"""
        try:
            text_element = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
            return text_element.text.strip()
        except:
            return ""
    
    async def _parse_dom_communities(self, community_tweets: List[Dict]) -> List[Community]:
        """Parse community data from collected tweets - FAST & ACCURATE"""
        communities = []
        seen_communities = {}
        
        for tweet_data in community_tweets:
            try:
                community_info = tweet_data['community_data']
                community_key = community_info['name'].lower()
                
                # Only accept REAL communities (socialContext or directLink)
                if community_info['source'] not in ['socialContext', 'directLink']:
                    continue
                
                # Aggregate data for the same community
                if community_key not in seen_communities:
                    seen_communities[community_key] = {
                        'id': community_info['id'],
                        'name': community_info['name'],
                        'role': community_info['role'],
                        'source': community_info['source'],
                        'tweet_count': 1
                    }
                else:
                    seen_communities[community_key]['tweet_count'] += 1
                    # Upgrade role if we find higher authority
                    current_role = seen_communities[community_key]['role']
                    new_role = community_info['role']
                    if current_role == 'Member' and new_role in ['Admin', 'Moderator']:
                        seen_communities[community_key]['role'] = new_role
                
            except Exception as e:
                self.logger.debug(f"Error parsing community data: {e}")
                continue
        
        # Create Community objects
        for community_data in seen_communities.values():
            try:
                community = Community(
                    id=community_data['id'],
                    name=community_data['name'],
                    description=f"Real community detected via {community_data['source']} (tweets: {community_data['tweet_count']})",
                    member_count=0,
                    role=community_data['role'],
                    is_nsfw=False,
                    created_at=datetime.utcnow().isoformat()
                )
                
                communities.append(community)
                self.logger.info(f"✅ Real community: {community.name} (Role: {community.role}, Source: {community_data['source']})")
                
            except Exception as e:
                self.logger.error(f"Error creating community object: {e}")
                continue
        
        return communities
    
    async def _filter_new_communities(self, username: str, detected_communities: List[Community]) -> List[Community]:
        """Filter to only return NEW communities compared to previous runs"""
        try:
            # Load previous communities for this user
            cache_key = f"browser_communities_{username}"
            previous = self.previous_communities.get(cache_key, set())
            
            new_communities = []
            current_community_names = set()
            
            for community in detected_communities:
                community_signature = f"{community.name.lower()}:{community.role}"
                current_community_names.add(community_signature)
                
                if community_signature not in previous:
                    new_communities.append(community)
                    self.logger.info(f"🆕 NEW community detected: {community.name} (Role: {community.role})")
            
            # Update cache
            self.previous_communities[cache_key] = current_community_names
            
            return new_communities
            
        except Exception as e:
            self.logger.error(f"Error filtering new communities: {e}")
            return detected_communities  # Return all if filtering fails
    
    async def _update_community_cache(self, username: str, communities: List[Community]):
        """Update the community cache for future comparisons"""
        try:
            cache_key = f"browser_communities_{username}"
            community_signatures = {f"{c.name.lower()}:{c.role}" for c in communities}
            self.previous_communities[cache_key] = community_signatures
            
            # Optionally save to file for persistence
            cache_file = f"cache/browser_communities_{username}.json"
            import os
            os.makedirs("cache", exist_ok=True)
            
            with open(cache_file, 'w') as f:
                json.dump(list(community_signatures), f)
            
        except Exception as e:
            self.logger.debug(f"Error updating cache: {e}")
    
    async def _cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.logger.info("🧹 Browser cleanup completed")
        except Exception as e:
            self.logger.debug(f"Error during browser cleanup: {e}")


class CommunityNotifier:
    """Enhanced notifier for community changes with categorization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def notify_community_changes(self, username: str, communities: List[Community]):
        """Notify about community changes with categorization"""
        if not communities:
            self.logger.info("📭 No new community changes to notify")
            return
        
        # Categorize communities based on detection source
        joined_communities = []
        created_communities = []
        tweeted_communities = []
        
        for community in communities:
            source = getattr(community, 'source', 'unknown')
            role = community.role.lower()
            
            if source == 'socialContext' or source == 'directLink':
                if role in ['admin', 'creator', 'owner']:
                    created_communities.append(community)
                else:
                    joined_communities.append(community)
            elif source == 'communitySpan' or source == 'textMention':
                tweeted_communities.append(community)
            else:
                # Default to tweeted if unclear
                tweeted_communities.append(community)
        
        # Create notification message
        await self._send_categorized_notification(username, joined_communities, created_communities, tweeted_communities)
    
    async def _send_categorized_notification(self, username: str, joined: List[Community], created: List[Community], tweeted: List[Community]):
        """Send categorized notification"""
        
        self.logger.info("=" * 50)
        self.logger.info(f"🔔 Run completed for @{username}")
        self.logger.info("=" * 50)
        
        # New communities joined
        if joined:
            self.logger.info(f"🎉 New communities joined ({len(joined)}):")
            for community in joined:
                self.logger.info(f"  • {community.name} (Role: {community.role})")
        else:
            self.logger.info("🔍 New communities joined: None")
        
        # New communities created
        if created:
            self.logger.info(f"🚀 New communities created ({len(created)}):")
            for community in created:
                self.logger.info(f"  • {community.name} (Role: {community.role})")
        else:
            self.logger.info("🏗️ New communities created: None")
        
        # New communities tweeted about
        if tweeted:
            self.logger.info(f"💬 New communities tweeted about ({len(tweeted)}):")
            for community in tweeted:
                self.logger.info(f"  • {community.name}")
        else:
            self.logger.info("📝 New communities tweeted about: None")
        
        self.logger.info("=" * 50)
        
        # Also send to Telegram if configured
        if joined or created or tweeted:
            await self._send_telegram_notification(username, joined, created, tweeted)
    
    async def _send_telegram_notification(self, username: str, joined: List[Community], created: List[Community], tweeted: List[Community]):
        """Send enhanced Telegram notification"""
        try:
            # This would integrate with your existing Telegram bot
            message = f"🔔 Community Update for @{username}\n\n"
            
            if joined:
                message += f"🎉 Joined ({len(joined)}):\n"
                for community in joined[:3]:  # Limit to avoid long messages
                    message += f"• {community.name} ({community.role})\n"
                if len(joined) > 3:
                    message += f"... and {len(joined) - 3} more\n"
                message += "\n"
            
            if created:
                message += f"🚀 Created ({len(created)}):\n"
                for community in created[:3]:
                    message += f"• {community.name} ({community.role})\n"
                if len(created) > 3:
                    message += f"... and {len(created) - 3} more\n"
                message += "\n"
            
            if tweeted:
                message += f"💬 Mentioned ({len(tweeted)}):\n"
                for community in tweeted[:3]:
                    message += f"• {community.name}\n"
                if len(tweeted) > 3:
                    message += f"... and {len(tweeted) - 3} more\n"
            
            self.logger.info(f"📱 Telegram notification prepared: {len(message)} chars")
            # Here you would send to actual Telegram bot
            
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {e}") 