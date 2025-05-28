#!/usr/bin/env python3
"""
Advanced Cookie Management System for Twitter Community Tracker Bot

This module provides two methods of cookie handling:
1. Manual Extraction: Users provide essential cookies manually
2. Auto-Enrichment: System automatically generates missing cookies
"""

import os
import logging
import json
import re
import secrets
import base64
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class CookieSet:
    """Represents a complete set of Twitter cookies"""
    auth_token: str
    ct0: str  # CSRF token
    guest_id: Optional[str] = None
    personalization_id: Optional[str] = None
    guest_id_ads: Optional[str] = None
    guest_id_marketing: Optional[str] = None
    
    def to_string(self) -> str:
        """Convert to cookie string format"""
        parts = [f"auth_token={self.auth_token}", f"ct0={self.ct0}"]
        
        if self.guest_id:
            parts.append(f"guest_id={self.guest_id}")
        if self.personalization_id:
            parts.append(f"personalization_id={self.personalization_id}")
        if self.guest_id_ads:
            parts.append(f"guest_id_ads={self.guest_id_ads}")
        if self.guest_id_marketing:
            parts.append(f"guest_id_marketing={self.guest_id_marketing}")
        
        return "; ".join(parts) + ";"


class CookieManager:
    """Advanced Cookie Management System"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_dir = "data"
        self.cookie_file = os.path.join(self.data_dir, "cookies.json")
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    # ========================================
    # METHOD 1: MANUAL EXTRACTION
    # ========================================
    
    def parse_manual_cookies(self, cookie_string: str) -> Optional[CookieSet]:
        """
        Parse manually extracted cookies from browser
        
        Supports multiple formats:
        - Cookie string: "auth_token=abc; ct0=def;"
        - JSON format: {"auth_token": "abc", "ct0": "def"}
        - Browser export format
        
        Args:
            cookie_string: Raw cookie input from user
            
        Returns:
            CookieSet object or None if invalid
        """
        try:
            self.logger.info("Parsing manual cookie extraction")
            
            # Try JSON format first
            if cookie_string.strip().startswith('{'):
                return self._parse_json_cookies(cookie_string)
            
            # Try browser export format (array of cookie objects)
            elif cookie_string.strip().startswith('['):
                return self._parse_browser_export(cookie_string)
            
            # Default to cookie string format
            else:
                return self._parse_cookie_string(cookie_string)
                
        except Exception as e:
            self.logger.error(f"Error parsing manual cookies: {e}")
            return None
    
    def _parse_cookie_string(self, cookie_string: str) -> Optional[CookieSet]:
        """Parse standard cookie string format"""
        cookies = {}
        
        # Clean and split cookie string
        for part in cookie_string.split(';'):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        # Extract required cookies
        auth_token = cookies.get('auth_token')
        ct0 = cookies.get('ct0')
        
        if not auth_token or not ct0:
            self.logger.error("Missing required cookies: auth_token and ct0")
            return None
        
        return CookieSet(
            auth_token=auth_token,
            ct0=ct0,
            guest_id=cookies.get('guest_id'),
            personalization_id=cookies.get('personalization_id'),
            guest_id_ads=cookies.get('guest_id_ads'),
            guest_id_marketing=cookies.get('guest_id_marketing')
        )
    
    def _parse_json_cookies(self, json_string: str) -> Optional[CookieSet]:
        """Parse JSON format cookies"""
        try:
            data = json.loads(json_string)
            
            auth_token = data.get('auth_token')
            ct0 = data.get('ct0')
            
            if not auth_token or not ct0:
                self.logger.error("JSON missing required fields: auth_token and ct0")
                return None
            
            return CookieSet(
                auth_token=auth_token,
                ct0=ct0,
                guest_id=data.get('guest_id'),
                personalization_id=data.get('personalization_id'),
                guest_id_ads=data.get('guest_id_ads'),
                guest_id_marketing=data.get('guest_id_marketing')
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format: {e}")
            return None
    
    def _parse_browser_export(self, export_string: str) -> Optional[CookieSet]:
        """Parse browser exported cookie array format"""
        try:
            data = json.loads(export_string)
            
            if not isinstance(data, list):
                self.logger.error("Browser export should be an array")
                return None
            
            cookies = {}
            for cookie in data:
                if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                    if cookie.get('domain', '').endswith('twitter.com') or cookie.get('domain', '').endswith('x.com'):
                        cookies[cookie['name']] = cookie['value']
            
            auth_token = cookies.get('auth_token')
            ct0 = cookies.get('ct0')
            
            if not auth_token or not ct0:
                self.logger.error("Browser export missing required cookies")
                return None
            
            return CookieSet(
                auth_token=auth_token,
                ct0=ct0,
                guest_id=cookies.get('guest_id'),
                personalization_id=cookies.get('personalization_id'),
                guest_id_ads=cookies.get('guest_id_ads'),
                guest_id_marketing=cookies.get('guest_id_marketing')
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid browser export format: {e}")
            return None
    
    # ========================================
    # METHOD 2: AUTO-ENRICHMENT
    # ========================================
    
    def auto_enrich_cookies(self, cookie_set: CookieSet) -> CookieSet:
        """
        Automatically enrich minimal cookie set with generated values
        
        Args:
            cookie_set: Minimal cookie set (requires auth_token and ct0)
            
        Returns:
            Enriched cookie set with all required fields
        """
        self.logger.info("Auto-enriching cookies with generated values")
        
        # Generate missing cookies
        if not cookie_set.guest_id:
            cookie_set.guest_id = self._generate_guest_id()
            self.logger.debug("Generated guest_id")
        
        if not cookie_set.personalization_id:
            cookie_set.personalization_id = self._generate_personalization_id()
            self.logger.debug("Generated personalization_id")
        
        if not cookie_set.guest_id_ads:
            cookie_set.guest_id_ads = self._generate_guest_id()
            self.logger.debug("Generated guest_id_ads")
        
        if not cookie_set.guest_id_marketing:
            cookie_set.guest_id_marketing = self._generate_guest_id()
            self.logger.debug("Generated guest_id_marketing")
        
        return cookie_set
    
    def _generate_guest_id(self) -> str:
        """Generate Twitter-compatible guest_id"""
        timestamp = int(datetime.now().timestamp())
        return f"v1%3A{timestamp}"
    
    def _generate_personalization_id(self) -> str:
        """Generate Twitter-compatible personalization_id"""
        random_bytes = secrets.token_bytes(12)
        encoded = base64.b64encode(random_bytes).decode('ascii')
        return f'"v1_{encoded}=="'
    
    # ========================================
    # AUTHENTICATION & VALIDATION
    # ========================================
    
    def validate_cookie_set(self, cookie_set: CookieSet) -> Tuple[bool, List[str]]:
        """
        Validate cookie set for completeness and format
        
        Args:
            cookie_set: Cookie set to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        if not cookie_set.auth_token:
            issues.append("Missing auth_token")
        elif len(cookie_set.auth_token) < 20:
            issues.append("auth_token seems too short")
        
        if not cookie_set.ct0:
            issues.append("Missing ct0 (CSRF token)")
        elif len(cookie_set.ct0) < 32:
            issues.append("ct0 token seems too short")
        
        # Validate format patterns
        if cookie_set.guest_id and not re.match(r'^v1%3A\d+$', cookie_set.guest_id):
            issues.append("guest_id format invalid")
        
        if cookie_set.personalization_id and not re.match(r'^"v1_[A-Za-z0-9+/]+=*"$', cookie_set.personalization_id):
            issues.append("personalization_id format invalid")
        
        return len(issues) == 0, issues
    
    def authenticate_with_cookies(self, cookie_set: CookieSet) -> Dict[str, str]:
        """
        Generate authentication headers from cookie set
        
        Args:
            cookie_set: Complete cookie set
            
        Returns:
            Dictionary of headers for Twitter API authentication
        """
        headers = {
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'cookie': cookie_set.to_string(),
            'x-csrf-token': cookie_set.ct0,
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        return headers
    
    # ========================================
    # STORAGE & MANAGEMENT
    # ========================================
    
    def save_cookies(self, cookie_set: CookieSet, name: str = "default") -> bool:
        """
        Save cookie set to secure storage
        
        Args:
            cookie_set: Cookie set to save
            name: Name/identifier for this cookie set
            
        Returns:
            True if saved successfully
        """
        try:
            # Load existing cookies
            cookies_data = {}
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, 'r') as f:
                    cookies_data = json.load(f)
            
            # Add new cookie set
            cookies_data[name] = {
                'auth_token': cookie_set.auth_token,
                'ct0': cookie_set.ct0,
                'guest_id': cookie_set.guest_id,
                'personalization_id': cookie_set.personalization_id,
                'guest_id_ads': cookie_set.guest_id_ads,
                'guest_id_marketing': cookie_set.guest_id_marketing,
                'created_at': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.cookie_file, 'w') as f:
                json.dump(cookies_data, f, indent=2)
            
            self.logger.info(f"Cookies saved successfully as '{name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving cookies: {e}")
            return False
    
    def load_cookies(self, name: str = "default") -> Optional[CookieSet]:
        """
        Load cookie set from storage
        
        Args:
            name: Name/identifier of cookie set to load
            
        Returns:
            CookieSet object or None if not found
        """
        try:
            if not os.path.exists(self.cookie_file):
                return None
            
            with open(self.cookie_file, 'r') as f:
                cookies_data = json.load(f)
            
            if name not in cookies_data:
                return None
            
            data = cookies_data[name]
            
            # Update last_used timestamp
            data['last_used'] = datetime.now().isoformat()
            with open(self.cookie_file, 'w') as f:
                json.dump(cookies_data, f, indent=2)
            
            return CookieSet(
                auth_token=data['auth_token'],
                ct0=data['ct0'],
                guest_id=data.get('guest_id'),
                personalization_id=data.get('personalization_id'),
                guest_id_ads=data.get('guest_id_ads'),
                guest_id_marketing=data.get('guest_id_marketing')
            )
            
        except Exception as e:
            self.logger.error(f"Error loading cookies: {e}")
            return None
    
    def list_cookie_sets(self) -> List[Dict[str, str]]:
        """
        List all saved cookie sets
        
        Returns:
            List of cookie set metadata
        """
        try:
            if not os.path.exists(self.cookie_file):
                return []
            
            with open(self.cookie_file, 'r') as f:
                cookies_data = json.load(f)
            
            result = []
            for name, data in cookies_data.items():
                result.append({
                    'name': name,
                    'created_at': data.get('created_at', 'Unknown'),
                    'last_used': data.get('last_used', 'Never'),
                    'auth_token_preview': data['auth_token'][:10] + '...' if data.get('auth_token') else 'None'
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing cookies: {e}")
            return []
    
    def delete_cookies(self, name: str) -> bool:
        """
        Delete a cookie set
        
        Args:
            name: Name of cookie set to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            if not os.path.exists(self.cookie_file):
                return False
            
            with open(self.cookie_file, 'r') as f:
                cookies_data = json.load(f)
            
            if name in cookies_data:
                del cookies_data[name]
                
                with open(self.cookie_file, 'w') as f:
                    json.dump(cookies_data, f, indent=2)
                
                self.logger.info(f"Deleted cookie set '{name}'")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting cookies: {e}")
            return False
    
    # ========================================
    # UTILITY METHODS
    # ========================================
    
    def get_upload_instructions(self) -> Dict[str, str]:
        """
        Get detailed instructions for both upload methods
        
        Returns:
            Dictionary with instructions for each method
        """
        return {
            'method1_manual': '''🔧 METHOD 1: Manual Extraction

1. Open Twitter/X in your browser and login
2. Press F12 (Developer Tools)
3. Go to Application/Storage tab
4. Find Cookies → x.com
5. Copy these cookies:
   • auth_token (long hex string)
   • ct0 (CSRF token, 32+ chars)

Format: auth_token=abc123...; ct0=def456...;''',

            'method2_enriched': '''🚀 METHOD 2: Auto-Enriched (Recommended)

1. Follow Method 1 to get auth_token and ct0
2. Send just: auth_token=abc123...; ct0=def456...;
3. Bot automatically generates:
   • guest_id
   • personalization_id  
   • guest_id_ads
   • guest_id_marketing

This method is easier and more reliable!''',

            'browser_export': '''📥 BONUS: Browser Export

Export all cookies as JSON from browser extensions
Send the JSON array and bot will extract Twitter cookies
automatically.'''
        }


# Global instance
cookie_manager = CookieManager() 