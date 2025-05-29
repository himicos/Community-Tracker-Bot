import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import json
import re
import secrets
import base64

from twscrape import API, AccountsPool
from twscrape.logger import set_log_level

from bot.models import Community, TwitterUserCommunityPayload, get_next_available_proxy, update_proxy_last_used, get_proxy_accounts
from bot.cookie_manager import CookieManager, CookieSet
from bot.enhanced_community_tracker import EnhancedCommunityTracker
from bot.twitter_graphql import TwitterGraphQLCommunities

class TwitterAPI:
    """Enhanced Twitter API class with comprehensive cookie management, community tracking, and GraphQL integration"""
    
    def __init__(self, proxy: Optional[str] = None):
        # Initialize API with proxy if provided
        self.proxy = proxy
        self.current_proxy_id = None
        
        # If no proxy provided, try to get one from database
        if not proxy:
            proxy_account = get_next_available_proxy()
            if proxy_account:
                proxy = proxy_account.proxy_url
                self.current_proxy_id = proxy_account.id
                self.logger = logging.getLogger(__name__)
                self.logger.info(f"Auto-selected proxy from database: {proxy_account.account_name}")
        
        self.api = API(proxy=proxy) if proxy else API()
        self.logger = logging.getLogger(__name__)
        # Set twscrape log level to ERROR to reduce noise
        set_log_level("ERROR")
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Initialize accounts pool file
        self.accounts_db = "data/accounts.db"
        
        # Initialize cookie manager, enhanced tracker, and GraphQL integration
        self.cookie_manager = CookieManager()
        self.enhanced_tracker = EnhancedCommunityTracker(self.api, self.cookie_manager)
        self.graphql = TwitterGraphQLCommunities(self.cookie_manager)
        
        self.logger.info(f"TwitterAPI initialized with GraphQL support and proxy: {proxy if proxy else 'None'}")
    
    # ========================================
    # ENHANCED COOKIE MANAGEMENT
    # ========================================
    
    async def add_account_from_cookie_enhanced(self, cookie_input: str, method: str = "auto", account_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Enhanced cookie handling with two methods
        
        Args:
            cookie_input: Cookie string or JSON input from user
            method: "manual" or "auto" (auto-enrichment)
            account_name: Optional account name
            
        Returns:
            Dictionary with success status and details
        """
        result = {
            'success': False,
            'method_used': method,
            'message': '',
            'cookie_set': None,
            'enriched': False
        }
        
        try:
            self.logger.info(f"Processing cookies using {method} method")
            
            # Step 1: Parse input cookies
            cookie_set = self.cookie_manager.parse_manual_cookies(cookie_input)
            if not cookie_set:
                result['message'] = "Failed to parse cookie input. Check format."
                return result
            
            # Step 2: Validate basic requirements
            is_valid, issues = self.cookie_manager.validate_cookie_set(cookie_set)
            if not is_valid:
                result['message'] = f"Cookie validation failed: {', '.join(issues)}"
                return result
            
            # Step 3: Auto-enrich if method is auto or if incomplete
            if method == "auto" or not all([cookie_set.guest_id, cookie_set.personalization_id]):
                original_complete = all([cookie_set.guest_id, cookie_set.personalization_id, 
                                       cookie_set.guest_id_ads, cookie_set.guest_id_marketing])
                
                cookie_set = self.cookie_manager.auto_enrich_cookies(cookie_set)
                result['enriched'] = not original_complete
                
                if result['enriched']:
                    self.logger.info("Cookies auto-enriched with generated tokens")
            
            # Step 4: Final validation
            is_valid, issues = self.cookie_manager.validate_cookie_set(cookie_set)
            if not is_valid:
                result['message'] = f"Enriched cookie validation failed: {', '.join(issues)}"
                return result
            
            # Step 5: Add account to twscrape
            success = await self._add_to_twscrape(cookie_set, account_name)
            if not success:
                result['message'] = "Failed to add account to Twitter API"
                return result
            
            # Step 6: Save cookies
            save_name = account_name or f"account_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            saved = self.cookie_manager.save_cookies(cookie_set, save_name)
            
            result.update({
                'success': True,
                'message': f"Account added successfully using {method} method" + 
                          (" with auto-enrichment" if result['enriched'] else ""),
                'cookie_set': cookie_set,
                'saved_as': save_name if saved else None
            })
            
            self.logger.info(f"Successfully added account with {method} method")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in enhanced cookie handling: {e}")
            result['message'] = f"Error: {str(e)}"
            return result
    
    async def _add_to_twscrape(self, cookie_set: CookieSet, account_name: Optional[str] = None) -> bool:
        """Add cookie set to twscrape accounts pool"""
        try:
            # Use provided proxy, instance proxy, or rotating proxy
            use_proxy = self.proxy
            if not use_proxy:
                use_proxy = self.get_rotating_proxy()
            
            # Create a new accounts pool with proxy support
            pool = AccountsPool(self.accounts_db)
            
            self.logger.info(f"Adding account {account_name or 'twitter_user'} to twscrape")
            
            # Add account using complete cookie set
            await pool.add_account(
                username=account_name or "twitter_user",
                password="password_placeholder",
                email="email@placeholder.com",
                email_password="email_pass_placeholder",
                cookies=cookie_set.to_string(),
                proxy=use_proxy
            )
            
            # Reinitialize API with proxy if needed
            if use_proxy and not self.proxy:
                self.api = API(proxy=use_proxy)
                self.proxy = use_proxy
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding to twscrape: {e}")
            return False
    
    def get_cookie_upload_methods(self) -> Dict[str, str]:
        """Get instructions for both cookie upload methods"""
        return self.cookie_manager.get_upload_instructions()
    
    def list_saved_cookies(self) -> List[Dict[str, str]]:
        """List all saved cookie sets"""
        return self.cookie_manager.list_cookie_sets()
    
    async def load_saved_cookies(self, name: str = "default") -> bool:
        """Load and activate saved cookies"""
        try:
            cookie_set = self.cookie_manager.load_cookies(name)
            if not cookie_set:
                self.logger.error(f"No saved cookies found with name: {name}")
                return False
            
            success = await self._add_to_twscrape(cookie_set, f"loaded_{name}")
            if success:
                self.logger.info(f"Successfully loaded and activated cookies: {name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error loading saved cookies: {e}")
            return False
    
    # ========================================
    # COMPREHENSIVE COMMUNITY TRACKING
    # ========================================
    
    async def get_user_communities_comprehensive(self, username: str, deep_scan: bool = True) -> Optional[TwitterUserCommunityPayload]:
        """
        Get comprehensive community information using enhanced tracking
        
        Args:
            username: Twitter username (without @)
            deep_scan: Whether to perform deep analysis (slower but finds ALL communities)
            
        Returns:
            Complete TwitterUserCommunityPayload with all detected communities
        """
        self.logger.info(f"Starting comprehensive community tracking for @{username}")
        
        try:
            # Use enhanced community tracker for comprehensive detection
            result = await self.enhanced_tracker.get_all_user_communities(username, deep_scan=deep_scan)
            
            if result:
                self.logger.info(f"Comprehensive scan complete for @{username}: {len(result.communities)} communities found")
                
                # Log detailed results
                for i, community in enumerate(result.communities, 1):
                    self.logger.info(f"  {i}. {community.name} (Role: {community.role}, ID: {community.id})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive community tracking: {e}")
            return None
    
    async def track_community_changes_comprehensive(self, username: str, previous_communities: List[Community], deep_scan: bool = True) -> Dict[str, Any]:
        """
        Track comprehensive changes in user's community participation
        
        Returns:
            Detailed change report with all detected changes
        """
        return await self.enhanced_tracker.track_community_changes(username, previous_communities, deep_scan=deep_scan)
    
    # ========================================
    # GRAPHQL DIRECT COMMUNITY DETECTION
    # ========================================
    
    async def get_user_communities_direct(self, username: str) -> Optional[TwitterUserCommunityPayload]:
        """
        Get user's actual community memberships using GraphQL API (DIRECT METHOD)
        
        This method attempts to get real community membership data rather than inferring
        from tweets or other indirect methods.
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            TwitterUserCommunityPayload with actual community memberships
        """
        self.logger.info(f"🔍 Getting DIRECT community memberships for @{username} via GraphQL")
        
        try:
            result = await self.graphql.get_user_communities_direct(username)
            
            if result:
                self.logger.info(f"✅ Direct GraphQL scan complete for @{username}: {len(result.communities)} actual memberships found")
                
                # Log detailed results
                for i, community in enumerate(result.communities, 1):
                    self.logger.info(f"  {i}. {community.name} (Role: {community.role}, ID: {community.id})")
            else:
                self.logger.warning(f"⚠️ No direct community data found for @{username}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in direct GraphQL community detection: {e}")
            return None
    
    async def track_community_changes_direct(self, username: str, previous_communities: List[Community]) -> Dict[str, Any]:
        """
        Track changes using direct GraphQL community detection
        
        This is the most accurate method for detecting:
        - User joined a new community
        - User left a community  
        - User created a new community
        
        Args:
            username: Twitter username (without @)
            previous_communities: List of previously stored communities
            
        Returns:
            Detailed change report with actual membership changes
        """
        self.logger.info(f"🔍 Tracking DIRECT community changes for @{username}")
        
        try:
            result = await self.graphql.detect_community_changes_graphql(username, previous_communities)
            
            if result.get("has_changes"):
                self.logger.info(f"✅ DIRECT changes detected for @{username}:")
                if result.get("joined"):
                    self.logger.info(f"  📈 Joined: {len(result['joined'])} communities")
                if result.get("left"):
                    self.logger.info(f"  📉 Left: {len(result['left'])} communities")
                if result.get("created"):
                    self.logger.info(f"  🆕 Created: {len(result['created'])} communities")
            else:
                self.logger.info(f"ℹ️ No direct community changes detected for @{username}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error tracking direct community changes: {e}")
            return {"error": str(e)}
    
    async def get_user_communities_hybrid(self, username: str, prefer_direct: bool = True) -> Optional[TwitterUserCommunityPayload]:
        """
        Hybrid approach: Try direct GraphQL first, fallback to comprehensive detection
        
        Args:
            username: Twitter username (without @)
            prefer_direct: If True, try GraphQL first; if False, try comprehensive first
            
        Returns:
            Best available community data
        """
        self.logger.info(f"🔄 Using HYBRID community detection for @{username}")
        
        if prefer_direct:
            # Try GraphQL first
            self.logger.info("  🎯 Attempting direct GraphQL detection...")
            result = await self.get_user_communities_direct(username)
            
            if result and len(result.communities) > 0:
                self.logger.info(f"  ✅ Direct method succeeded: {len(result.communities)} communities")
                return result
            
            # Fallback to comprehensive
            self.logger.info("  🔄 Falling back to comprehensive detection...")
            result = await self.get_user_communities_comprehensive(username, deep_scan=False)
            
            if result:
                self.logger.info(f"  ✅ Comprehensive fallback succeeded: {len(result.communities)} communities")
            
            return result
        else:
            # Try comprehensive first
            self.logger.info("  📊 Attempting comprehensive detection...")
            result = await self.get_user_communities_comprehensive(username, deep_scan=True)
            
            if result and len(result.communities) > 0:
                self.logger.info(f"  ✅ Comprehensive method succeeded: {len(result.communities)} communities")
                return result
            
            # Fallback to direct
            self.logger.info("  🔄 Falling back to direct GraphQL...")
            result = await self.get_user_communities_direct(username)
            
            if result:
                self.logger.info(f"  ✅ Direct fallback succeeded: {len(result.communities)} communities")
            
            return result
    
    # ========================================
    # LEGACY COMPATIBILITY METHODS
    # ========================================
    
    async def add_account_from_cookie(self, cookie_str: str, proxy: Optional[str] = None, account_name: Optional[str] = None) -> bool:
        """
        Legacy method for backward compatibility
        Uses auto-enrichment method by default
        """
        result = await self.add_account_from_cookie_enhanced(
            cookie_input=cookie_str,
            method="auto",
            account_name=account_name
        )
        return result['success']
    
    async def get_user_communities(self, username: str) -> Optional[TwitterUserCommunityPayload]:
        """
        Legacy method for backward compatibility
        Uses comprehensive tracking with quick scan
        """
        return await self.get_user_communities_comprehensive(username, deep_scan=False)
    
    # ========================================
    # UTILITY METHODS (PRESERVED)
    # ========================================
    
    def get_rotating_proxy(self) -> Optional[str]:
        """Get next available proxy for rotation"""
        proxy_account = get_next_available_proxy()
        if proxy_account:
            update_proxy_last_used(proxy_account.id)
            self.current_proxy_id = proxy_account.id
            self.logger.info(f"Using rotating proxy: {proxy_account.account_name} ({proxy_account.proxy_url[:30]}...)")
            return proxy_account.proxy_url
        return None
    
    def set_proxy(self, proxy: str):
        """Set proxy for the API instance"""
        self.proxy = proxy
        self.api = API(proxy=proxy)
        
        # Try to find the proxy in database to track usage
        proxy_accounts = get_proxy_accounts()
        for proxy_account in proxy_accounts:
            if proxy_account.proxy_url == proxy:
                self.current_proxy_id = proxy_account.id
                update_proxy_last_used(proxy_account.id)
                break
        
        self.logger.info(f"Proxy set to: {proxy}")
    
    # Legacy methods for diff_communities - preserved for compatibility
    def diff_communities(self, old_communities: List[Community], new_communities: List[Community]) -> Tuple[List[str], List[str], List[str]]:
        """Compare old and new community lists (legacy method)"""
        new_ids = {c.id for c in new_communities}
        old_ids = {c.id for c in old_communities}
        
        joined_ids = new_ids - old_ids
        left_ids = old_ids - new_ids
        created_ids = {c.id for c in new_communities if c.role == "Admin" and c.id in joined_ids}
        
        return list(joined_ids), list(left_ids), list(created_ids)
