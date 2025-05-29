#!/usr/bin/env python3
"""
Keyboard Utilities Module

Utilities for creating Telegram inline keyboards:
- Main menu keyboards
- Action-specific keyboards
- Dynamic keyboards based on data
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Any


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Create main menu keyboard with inline buttons"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📋 Set Target", callback_data="action:set_target"),
        InlineKeyboardButton(text="🍪 Set Cookie", callback_data="action:set_cookie"),
        InlineKeyboardButton(text="🌐 Proxy Settings", callback_data="action:proxy_menu"),
        InlineKeyboardButton(text="▶️ Start Tracking", callback_data="action:start_tracking"),
        InlineKeyboardButton(text="⏹️ Stop Tracking", callback_data="action:stop_tracking"),
        InlineKeyboardButton(text="ℹ️ Status", callback_data="action:status"),
        InlineKeyboardButton(text="📊 Communities", callback_data="action:communities")
    )
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()


def get_proxy_keyboard() -> InlineKeyboardMarkup:
    """Create proxy management keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🌐 Set Single Proxy", callback_data="action:set_proxy"),
        InlineKeyboardButton(text="📋 Set Proxy List", callback_data="action:set_proxy_list"),
        InlineKeyboardButton(text="👁️ View Proxies", callback_data="action:view_proxies"),
        InlineKeyboardButton(text="🗑️ Clear All Proxies", callback_data="action:clear_proxies"),
        InlineKeyboardButton(text="🔙 Back", callback_data="action:back")
    )
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()


def get_interval_keyboard() -> InlineKeyboardMarkup:
    """Create interval selection keyboard"""
    builder = InlineKeyboardBuilder()
    for interval in [1, 3, 5, 10, 15, 30]:
        builder.add(InlineKeyboardButton(
            text=f"{interval} min",
            callback_data=f"interval:{interval}"
        ))
    builder.add(InlineKeyboardButton(text="🔙 Back", callback_data="action:back"))
    builder.adjust(3)  # 3 buttons per row
    return builder.as_markup()


def get_target_keyboard() -> InlineKeyboardMarkup:
    """Create target selection keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Custom Target", callback_data="target:custom"),
        InlineKeyboardButton(text="🔙 Back", callback_data="action:back")
    )
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()


def get_communities_keyboard(communities: List[Any]) -> InlineKeyboardMarkup:
    """Create communities keyboard"""
    builder = InlineKeyboardBuilder()
    
    if communities:
        for i, community in enumerate(communities):
            builder.add(InlineKeyboardButton(
                text=f"{community.name}",
                callback_data=f"community:{community.community_id}"
            ))
    else:
        builder.add(InlineKeyboardButton(
            text="No communities found",
            callback_data="community:none"
        ))
    
    builder.add(InlineKeyboardButton(text="🔄 Refresh", callback_data="action:refresh_communities"))
    builder.add(InlineKeyboardButton(text="🔙 Back", callback_data="action:back"))
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()


def get_cookie_method_keyboard() -> InlineKeyboardMarkup:
    """Create cookie method selection keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Manual Method", callback_data="cookie_method:manual")],
        [InlineKeyboardButton(text="🚀 Auto-Enriched (Recommended)", callback_data="cookie_method:auto")],
        [InlineKeyboardButton(text="📥 Browser Export", callback_data="cookie_method:export")],
        [InlineKeyboardButton(text="📋 View Saved Cookies", callback_data="cookie_method:list")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="action:back")]
    ])


def get_cookie_list_keyboard(cookies: List[Any]) -> InlineKeyboardMarkup:
    """Create keyboard for saved cookies list"""
    builder = InlineKeyboardBuilder()
    
    if cookies:
        for i, cookie in enumerate(cookies):
            # Truncate name if too long
            name = cookie.name[:20] + "..." if len(cookie.name) > 20 else cookie.name
            builder.add(InlineKeyboardButton(
                text=f"🍪 {name}",
                callback_data=f"load_cookie:{cookie.id}"
            ))
    else:
        builder.add(InlineKeyboardButton(
            text="No saved cookies",
            callback_data="cookie_method:none"
        ))
    
    builder.add(InlineKeyboardButton(text="🔙 Back", callback_data="action:set_cookie"))
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Create confirmation keyboard for destructive actions"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes", callback_data=f"confirm:{action}"),
            InlineKeyboardButton(text="❌ No", callback_data="action:back")
        ]
    ])


def get_tracking_control_keyboard(is_running: bool) -> InlineKeyboardMarkup:
    """Create tracking control keyboard based on current state"""
    builder = InlineKeyboardBuilder()
    
    if is_running:
        builder.add(
            InlineKeyboardButton(text="⏹️ Stop Tracking", callback_data="action:stop_tracking"),
            InlineKeyboardButton(text="🔄 Restart", callback_data="action:restart_tracking"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="action:tracking_settings")
        )
    else:
        builder.add(
            InlineKeyboardButton(text="▶️ Start Tracking", callback_data="action:start_tracking"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="action:tracking_settings")
        )
    
    builder.add(InlineKeyboardButton(text="🔙 Back", callback_data="action:back"))
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()


def get_tracking_settings_keyboard() -> InlineKeyboardMarkup:
    """Create tracking settings keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="⏱️ Set Interval", callback_data="action:set_interval"),
        InlineKeyboardButton(text="🎯 Change Target", callback_data="action:set_target"),
        InlineKeyboardButton(text="🔍 Scan Mode", callback_data="action:scan_mode"),
        InlineKeyboardButton(text="📊 Notifications", callback_data="action:notification_settings"),
        InlineKeyboardButton(text="🔙 Back", callback_data="action:status")
    )
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()


def get_scan_mode_keyboard() -> InlineKeyboardMarkup:
    """Create scan mode selection keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Deep Scan (Comprehensive)", callback_data="scan_mode:deep")],
        [InlineKeyboardButton(text="⚡ Quick Scan (Fast)", callback_data="scan_mode:quick")],
        [InlineKeyboardButton(text="🧠 Smart Scan (Adaptive)", callback_data="scan_mode:smart")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="action:tracking_settings")]
    ])


def get_notification_settings_keyboard() -> InlineKeyboardMarkup:
    """Create notification settings keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔔 All Changes", callback_data="notify:all")],
        [InlineKeyboardButton(text="📈 New Joins Only", callback_data="notify:joins")],
        [InlineKeyboardButton(text="📉 Leaves Only", callback_data="notify:leaves")],
        [InlineKeyboardButton(text="🔄 Role Changes", callback_data="notify:roles")],
        [InlineKeyboardButton(text="🔕 Minimal", callback_data="notify:minimal")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="action:tracking_settings")]
    ])


def get_proxy_details_keyboard(proxy_count: int) -> InlineKeyboardMarkup:
    """Create proxy details keyboard with current proxy count"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Add Proxy", callback_data="action:set_proxy"),
        InlineKeyboardButton(text="📋 Add List", callback_data="action:set_proxy_list"),
        InlineKeyboardButton(text="🔄 Test Proxies", callback_data="action:test_proxies"),
        InlineKeyboardButton(text="🗑️ Clear All", callback_data="action:clear_proxies"),
        InlineKeyboardButton(text="🔙 Back", callback_data="action:proxy_menu")
    )
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()


def get_community_details_keyboard(community_id: str) -> InlineKeyboardMarkup:
    """Create keyboard for community details view"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh Details", callback_data=f"refresh_community:{community_id}")],
        [InlineKeyboardButton(text="📊 View Members", callback_data=f"community_members:{community_id}")],
        [InlineKeyboardButton(text="💬 Recent Posts", callback_data=f"community_posts:{community_id}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="action:communities")]
    ]) 