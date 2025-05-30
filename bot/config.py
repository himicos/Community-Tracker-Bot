#!/usr/bin/env python3
"""
Configuration Settings for Community Tracker Bot
Optimized for safe testing and production use
"""

import os
from typing import Dict, Any

class BotConfig:
    """Centralized configuration for safe API usage"""
    
    # ========================================
    # RATE LIMITING SETTINGS (SAFE FOR TESTING)
    # ========================================
    
    # Tweet scanning limits (reduced for testing)
    TWEET_SCAN_LIMIT_FAST = 20       # Fast scan: check last 20 tweets
    TWEET_SCAN_LIMIT_NORMAL = 50     # Normal scan: check last 50 tweets  
    TWEET_SCAN_LIMIT_DEEP = 100      # Deep scan: check last 100 tweets
    
    # API call delays (prevent rate limiting)
    API_DELAY_SHORT = 0.5           # 0.5 seconds between quick calls
    API_DELAY_NORMAL = 1.0          # 1 second between normal calls
    API_DELAY_LONG = 2.0            # 2 seconds between heavy calls
    
    # Social graph limits (very conservative)
    FOLLOWING_SCAN_LIMIT = 100      # Max following to check
    FOLLOWERS_SCAN_LIMIT = 50       # Max followers to check
    
    # ========================================
    # COMMUNITY DETECTION SETTINGS
    # ========================================
    
    # Detection method priorities
    DETECTION_METHODS = {
        "url_extraction": True,      # Extract from community URLs in tweets
        "post_analysis": True,       # Analyze posts for creation/joining
        "activity_patterns": True,   # Check activity patterns
        "social_graph": False,       # Disabled for testing (rate intensive)
        "graphql_direct": True,      # Direct GraphQL queries
    }
    
    # Confidence thresholds
    MIN_CONFIDENCE_CREATION = 0.7    # Minimum confidence for community creation
    MIN_CONFIDENCE_JOINING = 0.6     # Minimum confidence for joining
    MIN_CONFIDENCE_GENERAL = 0.5     # General minimum confidence
    
    # ========================================
    # MONITORING SETTINGS
    # ========================================
    
    # Scan intervals (minutes)
    MONITORING_INTERVAL_FAST = 15    # Every 15 minutes
    MONITORING_INTERVAL_NORMAL = 30  # Every 30 minutes
    MONITORING_INTERVAL_SLOW = 60    # Every hour
    
    # Change detection settings
    TRACK_COMMUNITY_CREATION = True  # Monitor community creation
    TRACK_COMMUNITY_JOINING = True   # Monitor joining communities
    TRACK_ROLE_CHANGES = True        # Monitor role changes
    
    # ========================================
    # TESTING SETTINGS
    # ========================================
    
    @classmethod
    def get_test_config(cls) -> Dict[str, Any]:
        """Get configuration optimized for testing"""
        return {
            "tweet_limit": cls.TWEET_SCAN_LIMIT_FAST,
            "api_delay": cls.API_DELAY_NORMAL,
            "following_limit": 20,  # Very low for testing
            "followers_limit": 10,  # Very low for testing
            "enable_social_graph": False,  # Disable for testing
            "confidence_threshold": cls.MIN_CONFIDENCE_GENERAL,
            "methods": {
                "url_extraction": True,
                "post_analysis": True,
                "activity_patterns": False,  # Disable for basic testing
                "graphql_direct": True,
            }
        }
    
    @classmethod
    def get_production_config(cls) -> Dict[str, Any]:
        """Get configuration for production use"""
        return {
            "tweet_limit": cls.TWEET_SCAN_LIMIT_NORMAL,
            "api_delay": cls.API_DELAY_LONG,
            "following_limit": cls.FOLLOWING_SCAN_LIMIT,
            "followers_limit": cls.FOLLOWERS_SCAN_LIMIT,
            "enable_social_graph": True,
            "confidence_threshold": cls.MIN_CONFIDENCE_GENERAL,
            "methods": cls.DETECTION_METHODS
        }
    
    @classmethod
    def get_monitoring_config(cls) -> Dict[str, Any]:
        """Get configuration for continuous monitoring"""
        return {
            "interval_minutes": cls.MONITORING_INTERVAL_NORMAL,
            "track_creation": cls.TRACK_COMMUNITY_CREATION,
            "track_joining": cls.TRACK_COMMUNITY_JOINING,
            "track_roles": cls.TRACK_ROLE_CHANGES,
            "deep_scan": False,  # Use fast scans for monitoring
        }

# Global configuration instance
config = BotConfig()

# ========================================
# ENVIRONMENT-BASED SETTINGS
# ========================================

def get_current_config() -> Dict[str, Any]:
    """Get configuration based on environment"""
    env_mode = os.getenv("BOT_MODE", "testing").lower()
    
    if env_mode == "production":
        return config.get_production_config()
    elif env_mode == "monitoring":
        return config.get_monitoring_config()
    else:  # Default to testing
        return config.get_test_config()

def is_testing_mode() -> bool:
    """Check if we're in testing mode"""
    return os.getenv("BOT_MODE", "testing").lower() == "testing"

def get_rate_limit_delay(operation_type: str = "normal") -> float:
    """Get appropriate delay for operation type"""
    delays = {
        "fast": BotConfig.API_DELAY_SHORT,
        "normal": BotConfig.API_DELAY_NORMAL,
        "heavy": BotConfig.API_DELAY_LONG,
    }
    return delays.get(operation_type, BotConfig.API_DELAY_NORMAL) 