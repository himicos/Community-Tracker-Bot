#!/usr/bin/env python3
"""
Community Detection Notification Demo
This script demonstrates how notifications are generated when communities are detected.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.models import Community

class CommunityExt:
    """Extended community for demo purposes"""
    def __init__(self, id: str, name: str, role: str, 
                 description: str = "", member_count: int = 0, 
                 source: str = "unknown", confidence: float = 0.8):
        self.id = id
        self.name = name
        self.role = role
        self.description = description
        self.member_count = member_count
        self.source = source
        self.confidence = confidence

class NotificationDemo:
    """Demonstrate the notification system for community detection"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def demo_notification_system(self):
        """Demonstrate different types of notifications"""
        print("📱 COMMUNITY TRACKING NOTIFICATION SYSTEM DEMO")
        print("=" * 80)
        print("This demonstrates what notifications look like when communities are detected\n")
        
        # Sample detected communities (using extended class for demo)
        detected_communities = [
            CommunityExt(
                id="1234567890123456789",
                name="Crypto Builders",
                role="Member",
                description="A community for crypto developers",
                member_count=1250,
                source="url_extraction",
                confidence=0.85
            ),
            CommunityExt(
                id="9876543210987654321",
                name="AI Enthusiasts",
                role="Member",
                description="Discussing AI and machine learning",
                member_count=890,
                source="post_analysis",
                confidence=0.78
            ),
            CommunityExt(
                id="5555555555555555555",
                name="Web3 Developers",
                role="Admin",
                description="Building the decentralized web",
                member_count=2100,
                source="post_analysis",
                confidence=0.92
            ),
            CommunityExt(
                id="7777777777777777777",
                name="NFT Artists Collective",
                role="Member",
                description="Artists creating NFT art",
                member_count=650,
                source="url_extraction", 
                confidence=0.80
            )
        ]
        
        # Demo 1: Initial Community Detection
        self._demo_initial_detection("163ba6y", detected_communities)
        
        # Demo 2: Community Changes (Joined)
        new_communities = [
            CommunityExt(
                id="1111111111111111111",
                name="DeFi Protocol Discussion",
                role="Member",
                description="Discussing DeFi protocols and strategies",
                member_count=540,
                source="post_analysis",
                confidence=0.88
            )
        ]
        self._demo_joined_notification("163ba6y", new_communities)
        
        # Demo 3: Community Creation
        created_communities = [
            CommunityExt(
                id="9999999999999999999",
                name="My Blockchain Project",
                role="Creator",
                description="Community for my new blockchain project",
                member_count=1,
                source="post_analysis",
                confidence=0.95
            )
        ]
        self._demo_creation_notification("163ba6y", created_communities)
        
        # Demo 4: Complete Activity Report
        self._demo_activity_report("163ba6y", detected_communities, new_communities, created_communities)
        
        # Demo 5: Real-time Monitoring Alert
        self._demo_monitoring_alert("163ba6y")
        
        print("\n🎯 NOTIFICATION SUMMARY")
        print("=" * 80)
        print("✅ 5 different notification types demonstrated")
        print("✅ Shows community names, roles, and confidence scores")
        print("✅ Includes detection methods and timestamps")
        print("✅ Ready for Telegram bot integration")
        print("📱 These notifications would be sent to your Telegram chat")
        print("=" * 80)
    
    def _demo_initial_detection(self, username: str, communities: List[CommunityExt]):
        """Demo initial community detection notification"""
        print("🔔 NOTIFICATION TYPE 1: Initial Community Detection")
        print("-" * 60)
        
        message = self._create_detection_notification(username, communities, "Enhanced V2 Detection")
        self._display_notification(message)
    
    def _demo_joined_notification(self, username: str, communities: List[CommunityExt]):
        """Demo community joining notification"""
        print("🔔 NOTIFICATION TYPE 2: New Community Joined")
        print("-" * 60)
        
        changes = {
            "joined": communities,
            "left": [],
            "created": [],
            "detection_methods": ["post_analysis"],
            "scan_type": "Real-time Monitoring"
        }
        
        message = self._create_change_notification(username, changes)
        self._display_notification(message)
    
    def _demo_creation_notification(self, username: str, communities: List[CommunityExt]):
        """Demo community creation notification"""
        print("🔔 NOTIFICATION TYPE 3: Community Created")
        print("-" * 60)
        
        changes = {
            "joined": [],
            "left": [],
            "created": communities,
            "detection_methods": ["post_analysis"],
            "scan_type": "Creation Detection"
        }
        
        message = self._create_change_notification(username, changes)
        self._display_notification(message)
    
    def _demo_activity_report(self, username: str, existing: List[CommunityExt], 
                            joined: List[CommunityExt], created: List[CommunityExt]):
        """Demo comprehensive activity report"""
        print("🔔 NOTIFICATION TYPE 4: Comprehensive Activity Report")
        print("-" * 60)
        
        all_communities = existing + joined + created
        
        changes = {
            "joined": joined,
            "left": [],
            "created": created,
            "current_communities": all_communities,
            "detection_methods": ["enhanced_v2", "post_analysis", "url_extraction"],
            "scan_type": "Comprehensive Scan"
        }
        
        message = self._create_activity_report(username, changes)
        self._display_notification(message)
    
    def _demo_monitoring_alert(self, username: str):
        """Demo monitoring system status alert"""
        print("🔔 NOTIFICATION TYPE 5: Monitoring System Alert")
        print("-" * 60)
        
        message = f"""🚀 **Community Monitoring Started**

User: @{username}
Interval: 15 minutes
Features: Deep scanning, real-time detection

📡 **Active Detection Methods:**
✅ Enhanced V2 Tracker
✅ Post Analysis (creation/joining)
✅ URL Extraction
✅ Activity Pattern Analysis
✅ GraphQL Community Detection

🎯 **Monitoring For:**
• New community memberships
• Community creation activities
• Role changes (Member ↔ Admin)
• Community departures
• Activity pattern changes

⚙️ **Configuration:**
• Safe rate limiting enabled
• Confidence threshold: 0.7
• Scan depth: Comprehensive
• Error recovery: Automatic

📱 You'll receive notifications for any community changes detected.

⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"""
        
        self._display_notification(message)
    
    def _create_detection_notification(self, username: str, communities: List[CommunityExt], 
                                     detection_method: str) -> str:
        """Create initial detection notification"""
        message_parts = [
            f"🔔 **Community Detection Results**\n",
            f"User: @{username}",
            f"Detection Method: {detection_method}",
            f"Communities Found: {len(communities)}\n"
        ]
        
        if communities:
            message_parts.append("📋 **Detected Communities:**")
            for i, community in enumerate(communities, 1):
                role_emoji = "👑" if community.role in ["Admin", "Creator"] else "👤"
                message_parts.append(f"  {i}. {role_emoji} **{community.name}**")
                message_parts.append(f"     Role: {community.role}")
                message_parts.append(f"     Members: {community.member_count:,}")
                message_parts.append(f"     Source: {community.source}")
                message_parts.append(f"     Confidence: {community.confidence:.2f}")
                message_parts.append("")
        
        message_parts.append(f"⏰ Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(message_parts)
    
    def _create_change_notification(self, username: str, changes: Dict[str, Any]) -> str:
        """Create change notification"""
        message_parts = [
            f"🔔 **Community Activity Detected**\n",
            f"User: @{username}",
            f"Scan type: {changes.get('scan_type', 'Real-time Monitoring')}",
            f"Detection methods: {changes.get('detection_methods', [])}"
        ]
        
        total_changes = (len(changes.get('joined', [])) + 
                        len(changes.get('created', [])) + 
                        len(changes.get('left', [])))
        
        message_parts.append(f"Total changes: {total_changes}\n")
        
        # Joined communities
        if changes.get('joined'):
            message_parts.append(f"✅ **Joined Communities ({len(changes['joined'])}):**")
            for community in changes['joined']:
                message_parts.append(f"   👤 **{community.name}**")
                message_parts.append(f"      Role: {community.role}")
                message_parts.append(f"      Members: {community.member_count:,}")
                message_parts.append(f"      Confidence: {community.confidence:.2f}")
                message_parts.append(f"      Info: Detected via {community.source}")
            message_parts.append("")
        
        # Created communities
        if changes.get('created'):
            message_parts.append(f"🆕 **Created Communities ({len(changes['created'])}):**")
            for community in changes['created']:
                message_parts.append(f"   👑 **{community.name}**")
                message_parts.append(f"      Role: {community.role}")
                message_parts.append(f"      Members: {community.member_count:,}")
                message_parts.append(f"      Confidence: {community.confidence:.2f}")
                message_parts.append(f"      Info: Detected via {community.source}")
            message_parts.append("")
        
        # Left communities
        if changes.get('left'):
            message_parts.append(f"❌ **Left Communities ({len(changes['left'])}):**")
            for community in changes['left']:
                message_parts.append(f"   🚪 **{community.name}**")
                message_parts.append(f"      Previous role: {community.role}")
            message_parts.append("")
        
        message_parts.append(f"⏰ Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        return "\n".join(message_parts)
    
    def _create_activity_report(self, username: str, changes: Dict[str, Any]) -> str:
        """Create comprehensive activity report"""
        all_communities = changes.get('current_communities', [])
        
        message_parts = [
            f"📊 **Comprehensive Community Report**\n",
            f"User: @{username}",
            f"Scan type: {changes.get('scan_type', 'Comprehensive')}",
            f"Methods: {', '.join(changes.get('detection_methods', []))}"
        ]
        
        # Changes summary
        total_changes = (len(changes.get('joined', [])) + 
                        len(changes.get('created', [])))
        
        if total_changes > 0:
            message_parts.append(f"New changes: {total_changes}\n")
            
            if changes.get('joined'):
                message_parts.append(f"✅ **Recently Joined ({len(changes['joined'])}):**")
                for community in changes['joined']:
                    message_parts.append(f"   👤 {community.name}")
                message_parts.append("")
            
            if changes.get('created'):
                message_parts.append(f"🆕 **Recently Created ({len(changes['created'])}):**")
                for community in changes['created']:
                    message_parts.append(f"   👑 {community.name}")
                message_parts.append("")
        
        # Current status
        message_parts.append(f"📊 **Current Status:**")
        message_parts.append(f"Total communities: {len(all_communities)}")
        
        admin_count = len([c for c in all_communities if c.role in ["Admin", "Creator"]])
        member_count = len([c for c in all_communities if c.role == "Member"])
        
        message_parts.append(f"Admin/Creator roles: {admin_count}")
        message_parts.append(f"Member roles: {member_count}")
        
        # Detection source breakdown
        sources = {}
        for community in all_communities:
            source = getattr(community, 'source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        if sources:
            message_parts.append(f"\n🔍 **Detection Sources:**")
            for source, count in sources.items():
                message_parts.append(f"   • {source}: {count}")
        
        message_parts.append(f"\n⏰ Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        return "\n".join(message_parts)
    
    def _display_notification(self, notification: str):
        """Display a notification message"""
        print("\n" + "="*80)
        print("📱 TELEGRAM NOTIFICATION PREVIEW")
        print("="*80)
        print(notification)
        print("="*80)
        print()


def main():
    """Main demo function"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    demo = NotificationDemo()
    demo.demo_notification_system()
    
    print("\n🎯 HOW TO GET REAL NOTIFICATIONS:")
    print("=" * 80)
    print("1️⃣ **For Real Detection**: Run test_community_tracking_safe.py")
    print("2️⃣ **To Start Monitoring**: Use the Telegram bot commands")
    print("3️⃣ **Test Creation Detection**: Post 'Just created a new community called \"Test Community\"'")
    print("4️⃣ **Test Joining Detection**: Post 'Excited to join the AI Developers community!'")
    print("5️⃣ **View All Communities**: Check what communities you're actually in")
    print()
    print("📱 **Telegram Bot Commands:**")
    print("   /start - Initialize bot")
    print("   /track @username - Start monitoring")
    print("   /stop - Stop monitoring")
    print("   /status - Check monitoring status")
    print("=" * 80)


if __name__ == "__main__":
    main() 