#!/usr/bin/env python3
"""
Selenium-based Community Detector
Real browser automation to detect community elements in rendered HTML
"""

import asyncio
import logging
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from bot.cookie_manager import CookieManager, CookieSet
from bot.models import Community

@dataclass
class CommunityDetection:
    """Represents a detected community with high confidence"""
    community_id: str
    name: str
    url: str
    detection_type: str
    confidence: float
    evidence: str
    detected_at: datetime
    html_source: str

class SeleniumCommunityDetector:
    """Selenium-based community detector with scrolling"""
    
    def __init__(self, cookie_manager: CookieManager):
        self.cookie_manager = cookie_manager
        self.logger = logging.getLogger(__name__)
        self.driver = None
        
    async def detect_communities(self, username: str, cookie_name: str = "default") -> List[CommunityDetection]:
        """
        Main detection method using Selenium browser automation
        
        Args:
            username: Twitter username to analyze
            cookie_name: Name of saved cookie set to use
            
        Returns:
            List of detected communities
        """
        communities = []
        
        try:
            # Initialize browser
            if not await self._initialize_browser(cookie_name):
                self.logger.error("Failed to initialize browser")
                return communities
            
            # Navigate to user's profile
            profile_url = f"https://x.com/{username}"
            self.logger.info(f"🌐 Navigating to {profile_url}")
            self.driver.get(profile_url)
            
            # Wait for page to load LONGER
            self.logger.info(f"⏳ Waiting for page content to load...")
            await asyncio.sleep(5)  # Increased from 3 to 5 seconds
            
            # Wait for timeline content specifically
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: len(driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')) > 0
                )
                self.logger.info(f"✅ Timeline content loaded")
            except TimeoutException:
                self.logger.warning(f"⚠️ Timeline content may not have loaded completely")
                
                # DEBUG: Check what's actually on the page
                page_title = self.driver.title
                current_url = self.driver.current_url
                self.logger.info(f"🔍 DEBUG - Page title: '{page_title}'")
                self.logger.info(f"🔍 DEBUG - Current URL: {current_url}")
                
                # Check if we're on login page
                if "login" in current_url.lower() or "signin" in current_url.lower():
                    self.logger.error(f"❌ Redirected to login page - authentication failed")
                    return communities
                
                # Check if user exists  
                if "User not found" in self.driver.page_source or "doesn't exist" in self.driver.page_source:
                    self.logger.error(f"❌ User @{username} not found or suspended")
                    return communities
                    
                # Check for any tweets at all
                tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
                cellInnerDiv_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="cellInnerDiv"]')
                
                self.logger.info(f"🔍 DEBUG - Found {len(tweet_elements)} tweet elements")
                self.logger.info(f"🔍 DEBUG - Found {len(cellInnerDiv_elements)} cellInnerDiv elements")
                
                # Try saving a screenshot for debugging
                try:
                    screenshot_path = f"debug_screenshot_{username}.png"
                    self.driver.save_screenshot(screenshot_path)
                    self.logger.info(f"📸 Screenshot saved: {screenshot_path}")
                except Exception as e:
                    self.logger.debug(f"Could not save screenshot: {e}")
            
            # Scroll and detect communities
            communities = await self._scroll_and_detect(username)
            
            self.logger.info(f"🔍 Selenium detection found {len(communities)} communities for @{username}")
            return communities
            
        except Exception as e:
            self.logger.error(f"❌ Selenium detection failed for @{username}: {e}")
            return communities
        
        finally:
            await self._close_browser()
    
    async def _initialize_browser(self, cookie_name: str) -> bool:
        """Initialize Selenium browser with cookies"""
        try:
            # Load cookies from cookie manager
            cookie_set = self.cookie_manager.load_cookies(cookie_name)
            if not cookie_set:
                self.logger.error(f"No cookies found with name: {cookie_name}")
                return False
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
            
            # Initialize driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Navigate to Twitter to set cookies
            self.driver.get("https://x.com")
            await asyncio.sleep(2)
            
            # Add cookies
            cookies_to_add = {
                'auth_token': cookie_set.auth_token,
                'ct0': cookie_set.ct0,
            }
            
            if cookie_set.guest_id:
                cookies_to_add['guest_id'] = cookie_set.guest_id
            if cookie_set.personalization_id:
                cookies_to_add['personalization_id'] = cookie_set.personalization_id
            
            for name, value in cookies_to_add.items():
                if value:
                    self.driver.add_cookie({
                        'name': name,
                        'value': value,
                        'domain': '.x.com',
                        'path': '/'
                    })
            
            # Refresh to apply cookies
            self.driver.refresh()
            await asyncio.sleep(3)
            
            # Test if authenticated
            if "login" in self.driver.current_url.lower():
                self.logger.warning("⚠️ Authentication test failed - still on login page")
                return False
            
            self.logger.info("✅ Browser authenticated successfully")
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Browser initialization failed: {e}")
            return False
    
    async def _scroll_and_detect(self, username: str) -> List[CommunityDetection]:
        """Scroll through timeline and detect community elements"""
        communities = []
        detected_ids = set()
        
        try:
            self.logger.info(f"🔍 Scrolling through @{username}'s timeline to detect communities")
            
            # Scroll and collect community elements
            scroll_count = 0
            max_scrolls = 10  # Limit scrolling
            last_height = 0
            
            while scroll_count < max_scrolls:
                # Detect communities in current view
                current_communities = await self._detect_communities_in_view()
                
                # Add new communities
                for community in current_communities:
                    if community.community_id not in detected_ids:
                        communities.append(community)
                        detected_ids.add(community.community_id)
                        self.logger.info(f"🎯 Found new community: {community.name} (ID: {community.community_id})")
                
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(2)  # Wait for content to load
                
                # Check if we've reached the bottom
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break  # No new content loaded
                
                last_height = new_height
                scroll_count += 1
                
                self.logger.info(f"📄 Scroll {scroll_count}/{max_scrolls} - Found {len(communities)} communities so far")
            
            self.logger.info(f"📊 Scrolling complete - Found {len(communities)} total communities")
            return communities
            
        except Exception as e:
            self.logger.error(f"Error during scrolling and detection: {e}")
            return communities
    
    async def _detect_communities_in_view(self) -> List[CommunityDetection]:
        """Detect community elements in current viewport"""
        communities = []
        
        try:
            # Look for community elements in current page - MORE PRECISE
            # First priority: socialContext elements
            social_context_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="socialContext"]')
            
            # Second priority: direct community links  
            community_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/i/communities/"]')
            
            # Third priority: spans within community links only
            community_span_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/i/communities/"] span.css-1jxf684')
            
            total_elements = len(social_context_elements) + len(community_links) + len(community_span_elements)
            self.logger.info(f"🔍 Found {len(social_context_elements)} socialContext + {len(community_links)} community links + {len(community_span_elements)} community spans = {total_elements} total")
            
            # Debug: Log socialContext elements specifically
            if social_context_elements:
                self.logger.info(f"🎯 SocialContext elements found:")
                for i, element in enumerate(social_context_elements[:3]):
                    try:
                        text = element.text
                        self.logger.info(f"   SocialContext {i+1}: '{text}'")
                    except Exception as e:
                        self.logger.debug(f"   SocialContext {i+1}: Error - {e}")
            else:
                self.logger.info(f"❌ No socialContext elements found")
            
            # Debug: Log community links specifically  
            if community_links:
                self.logger.info(f"🔗 Community links found:")
                for i, element in enumerate(community_links[:3]):
                    try:
                        href = element.get_attribute('href')
                        text = element.text
                        self.logger.info(f"   Link {i+1}: '{text}' -> {href}")
                    except Exception as e:
                        self.logger.debug(f"   Link {i+1}: Error - {e}")
            else:
                self.logger.info(f"❌ No community links found")
            
            # Method 1: Look for socialContext elements (highest priority)
            social_context_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="socialContext"]')
            
            for element in social_context_elements:
                try:
                    # Get community name from the element text
                    community_name = element.text.strip()
                    if not community_name or len(community_name) < 3:
                        continue
                    
                    # Look for associated community link
                    parent_link = element.find_element(By.XPATH, ".//ancestor::a[contains(@href, '/i/communities/')]")
                    if parent_link:
                        href = parent_link.get_attribute('href')
                        community_id_match = href.split('/i/communities/')[-1]
                        if community_id_match and community_id_match.isdigit():
                            community = CommunityDetection(
                                community_id=community_id_match,
                                name=community_name,
                                url=href,
                                detection_type='socialContext_selenium',
                                confidence=0.98,  # Very high confidence
                                evidence=f"SocialContext element: {community_name}",
                                detected_at=datetime.now(),
                                html_source=element.get_attribute('outerHTML')
                            )
                            communities.append(community)
                
                except Exception as e:
                    self.logger.debug(f"Error processing socialContext element: {e}")
            
            # Method 2: Look for community spans with specific CSS classes
            community_spans = self.driver.find_elements(By.CSS_SELECTOR, 'span.css-1jxf684.r-bcqeeo.r-1ttztb7.r-qvutc0.r-poiln3')
            
            for span in community_spans:
                try:
                    text = span.text.strip()
                    if not text or len(text) < 3:
                        continue
                    
                    # Skip common non-community text
                    skip_words = ['reply', 'retweet', 'like', 'share', 'follow', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'by', 'for', 'with', 'from', 'to']
                    if text.lower() in skip_words or text.isdigit():
                        continue
                    
                    # Look for associated community link in parent elements
                    try:
                        parent_link = span.find_element(By.XPATH, ".//ancestor::a[contains(@href, '/i/communities/')]")
                        href = parent_link.get_attribute('href')
                        community_id_match = href.split('/i/communities/')[-1]
                        if community_id_match and community_id_match.isdigit():
                            community = CommunityDetection(
                                community_id=community_id_match,
                                name=text,
                                url=href,
                                detection_type='css_span_selenium',
                                confidence=0.95,  # High confidence
                                evidence=f"CSS span detection: {text}",
                                detected_at=datetime.now(),
                                html_source=span.get_attribute('outerHTML')
                            )
                            communities.append(community)
                    except NoSuchElementException:
                        continue
                        
                except Exception as e:
                    self.logger.debug(f"Error processing CSS span: {e}")
            
            # Method 3: Direct community links
            community_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/i/communities/"]')
            
            for link in community_links:
                try:
                    href = link.get_attribute('href')
                    community_id_match = href.split('/i/communities/')[-1]
                    if not community_id_match or not community_id_match.isdigit():
                        continue
                    
                    # Get community name from link text or nested elements
                    community_name = link.text.strip()
                    if not community_name:
                        # Look for nested spans
                        nested_spans = link.find_elements(By.CSS_SELECTOR, 'span.css-1jxf684')
                        for span in nested_spans:
                            text = span.text.strip()
                            if text and len(text) > 2:
                                community_name = text
                                break
                    
                    if not community_name or len(community_name) < 3:
                        community_name = f"Community {community_id_match[:8]}..."
                    
                    community = CommunityDetection(
                        community_id=community_id_match,
                        name=community_name,
                        url=href,
                        detection_type='direct_link_selenium',
                        confidence=0.90,
                        evidence=f"Direct community link: {community_name}",
                        detected_at=datetime.now(),
                        html_source=link.get_attribute('outerHTML')
                    )
                    communities.append(community)
                    
                except Exception as e:
                    self.logger.debug(f"Error processing community link: {e}")
            
            return communities
            
        except Exception as e:
            self.logger.error(f"Error detecting communities in view: {e}")
            return communities
    
    async def _close_browser(self):
        """Close Selenium browser"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.logger.info("🔒 Browser closed")
            except Exception as e:
                self.logger.debug(f"Error closing browser: {e}")
    
    def format_detection_results(self, communities: List[CommunityDetection], username: str) -> str:
        """Format detection results for Telegram message"""
        
        if not communities:
            return f"Selenium Community Detection Results\n\nUser: @{username}\nResult: No communities detected"
        
        message_parts = [
            f"Selenium Community Detection Results\n",
            f"User: @{username}",
            f"Communities Found: {len(communities)}\n"
        ]
        
        for i, community in enumerate(communities, 1):
            confidence_emoji = "🔥" if community.confidence >= 0.95 else "✅" if community.confidence >= 0.9 else "⚠️"
            
            message_parts.append(f"{i}. {confidence_emoji} {community.name}")
            message_parts.append(f"   ID: {community.community_id}")
            message_parts.append(f"   Source: {community.detection_type}")
            message_parts.append(f"   Confidence: {community.confidence:.0%}")
            message_parts.append(f"   {community.evidence}\n")
        
        return "\n".join(message_parts) 