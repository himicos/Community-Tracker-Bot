#!/usr/bin/env python3
"""
Community Difference Analysis Module

Handles comparison and change detection between community states:
- Community membership changes
- Role changes
- Detailed difference analysis
- Change notifications
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from difflib import SequenceMatcher
from bot.models import Community


class CommunityDifferenceAnalyzer:
    """Analyzes differences between community states"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detailed_community_diff(self, old_communities: List[Community], new_communities: List[Community]) -> Dict[str, List]:
        """
        Perform detailed comparison between old and new community lists
        
        Returns:
            Dict with 'joined', 'left', 'role_changed', and 'updated' communities
        """
        diff = {
            'joined': [],
            'left': [],
            'role_changed': [],
            'updated': []
        }
        
        try:
            # Create mappings for easy lookup
            old_dict = {c.id: c for c in old_communities}
            new_dict = {c.id: c for c in new_communities}
            
            old_ids = set(old_dict.keys())
            new_ids = set(new_dict.keys())
            
            # Find joined communities (in new but not in old)
            joined_ids = new_ids - old_ids
            for community_id in joined_ids:
                community = new_dict[community_id]
                diff['joined'].append({
                    'community': community,
                    'detected_at': datetime.now(),
                    'detection_method': getattr(community, 'detection_method', 'unknown')
                })
            
            # Find left communities (in old but not in new)
            left_ids = old_ids - new_ids
            for community_id in left_ids:
                community = old_dict[community_id]
                diff['left'].append({
                    'community': community,
                    'detected_at': datetime.now(),
                    'last_seen': getattr(community, 'last_seen', datetime.now())
                })
            
            # Find communities with changes (in both old and new)
            common_ids = old_ids & new_ids
            for community_id in common_ids:
                old_community = old_dict[community_id]
                new_community = new_dict[community_id]
                
                changes = self._analyze_community_changes(old_community, new_community)
                if changes:
                    if 'role' in changes:
                        diff['role_changed'].append({
                            'community': new_community,
                            'old_role': changes['role']['old'],
                            'new_role': changes['role']['new'],
                            'detected_at': datetime.now()
                        })
                    
                    if any(key != 'role' for key in changes.keys()):
                        diff['updated'].append({
                            'community': new_community,
                            'changes': changes,
                            'detected_at': datetime.now()
                        })
            
            # Log summary
            self.logger.info(f"📊 Community changes detected:")
            self.logger.info(f"  Joined: {len(diff['joined'])}")
            self.logger.info(f"  Left: {len(diff['left'])}")
            self.logger.info(f"  Role changed: {len(diff['role_changed'])}")
            self.logger.info(f"  Updated: {len(diff['updated'])}")
        
        except Exception as e:
            self.logger.error(f"Error in detailed community diff: {e}")
        
        return diff
    
    def _analyze_community_changes(self, old_community: Community, new_community: Community) -> Dict[str, Any]:
        """
        Analyze changes between two versions of the same community
        """
        changes = {}
        
        try:
            # Check role changes
            if old_community.role != new_community.role:
                changes['role'] = {
                    'old': old_community.role,
                    'new': new_community.role
                }
            
            # Check name changes
            if old_community.name != new_community.name:
                changes['name'] = {
                    'old': old_community.name,
                    'new': new_community.name
                }
            
            # Check description changes
            if old_community.description != new_community.description:
                changes['description'] = {
                    'old': old_community.description,
                    'new': new_community.description
                }
            
            # Check member count changes
            if old_community.member_count != new_community.member_count:
                changes['member_count'] = {
                    'old': old_community.member_count,
                    'new': new_community.member_count,
                    'change': new_community.member_count - old_community.member_count
                }
            
            # Check theme changes
            if old_community.theme != new_community.theme:
                changes['theme'] = {
                    'old': old_community.theme,
                    'new': new_community.theme
                }
        
        except Exception as e:
            self.logger.debug(f"Error analyzing community changes: {e}")
        
        return changes
    
    def is_duplicate_community(self, new_community: Community, existing_communities: List[Community]) -> bool:
        """
        Check if a new community is a duplicate of an existing one using fuzzy matching
        """
        try:
            for existing in existing_communities:
                # Exact ID match
                if new_community.id == existing.id:
                    return True
                
                # Fuzzy name matching
                name_similarity = SequenceMatcher(None, 
                    self._clean_community_name(new_community.name), 
                    self._clean_community_name(existing.name)
                ).ratio()
                
                if name_similarity > 0.8:  # 80% similarity threshold
                    self.logger.debug(f"Duplicate detected: '{new_community.name}' similar to '{existing.name}' ({name_similarity:.2f})")
                    return True
                
                # Check for ID patterns that might indicate the same community
                new_id_clean = self._extract_id_pattern(new_community.id)
                existing_id_clean = self._extract_id_pattern(existing.id)
                
                if new_id_clean and existing_id_clean and new_id_clean == existing_id_clean:
                    self.logger.debug(f"Duplicate detected: ID pattern match {new_id_clean}")
                    return True
        
        except Exception as e:
            self.logger.debug(f"Error checking for duplicate community: {e}")
        
        return False
    
    def _clean_community_name(self, name: str) -> str:
        """
        Clean community name for comparison
        """
        if not name:
            return ""
        
        # Convert to lowercase and remove common suffixes/prefixes
        cleaned = name.lower().strip()
        
        # Remove common community-related words for better matching
        removal_patterns = [
            ' community', ' dao', ' collective', ' group', ' club',
            'community ', 'dao ', 'collective ', 'group ', 'club ',
            '#', '@', 'the ', ' the'
        ]
        
        for pattern in removal_patterns:
            cleaned = cleaned.replace(pattern, '')
        
        return cleaned.strip()
    
    def _extract_id_pattern(self, community_id: str) -> Optional[str]:
        """
        Extract meaningful ID patterns that might indicate the same community
        """
        try:
            # For numeric IDs, extract the core number
            if community_id.isdigit():
                return community_id
            
            # For prefixed IDs, extract the meaningful part
            if '_' in community_id:
                parts = community_id.split('_')
                # Look for numeric parts
                for part in parts:
                    if part.isdigit() and len(part) >= 10:  # Likely Twitter ID
                        return part
            
            # For hash-based IDs, return None (can't meaningfully compare)
            if community_id.startswith('hashtag_') or community_id.startswith('mention_'):
                return None
            
            return community_id
        
        except Exception as e:
            self.logger.debug(f"Error extracting ID pattern: {e}")
            return None
    
    def merge_community_lists(self, *community_lists: List[Community]) -> List[Community]:
        """
        Merge multiple community lists, removing duplicates
        """
        merged = []
        
        try:
            for community_list in community_lists:
                for community in community_list:
                    if not self.is_duplicate_community(community, merged):
                        merged.append(community)
                    else:
                        self.logger.debug(f"Skipping duplicate community: {community.name}")
        
        except Exception as e:
            self.logger.error(f"Error merging community lists: {e}")
        
        return merged
    
    def calculate_confidence_score(self, communities: List[Community]) -> float:
        """
        Calculate overall confidence score for a list of communities
        """
        try:
            if not communities:
                return 0.0
            
            # Get confidence scores from communities (if they have them)
            scores = []
            for community in communities:
                # Check if community has confidence attribute
                confidence = getattr(community, 'confidence', None)
                if confidence is not None:
                    scores.append(confidence)
                else:
                    # Assign default confidence based on detection method
                    theme = getattr(community, 'theme', '')
                    if 'url' in theme or 'direct' in theme:
                        scores.append(0.9)  # High confidence for URL-based detection
                    elif 'hashtag' in theme or 'mention' in theme:
                        scores.append(0.7)  # Medium confidence for pattern-based
                    elif 'activity' in theme or 'engagement' in theme:
                        scores.append(0.6)  # Lower confidence for behavioral
                    else:
                        scores.append(0.5)  # Default confidence
            
            return sum(scores) / len(scores) if scores else 0.0
        
        except Exception as e:
            self.logger.debug(f"Error calculating confidence score: {e}")
            return 0.0
    
    def filter_high_confidence_changes(self, diff: Dict[str, List], min_confidence: float = 0.6) -> Dict[str, List]:
        """
        Filter changes to only include high-confidence detections
        """
        filtered_diff = {
            'joined': [],
            'left': [],
            'role_changed': [],
            'updated': []
        }
        
        try:
            for change_type, changes in diff.items():
                for change in changes:
                    community = change.get('community')
                    if community:
                        confidence = getattr(community, 'confidence', None)
                        if confidence is None:
                            # Calculate confidence based on detection method
                            confidence = self._estimate_confidence(community)
                        
                        if confidence >= min_confidence:
                            filtered_diff[change_type].append(change)
                        else:
                            self.logger.debug(f"Filtered low confidence change: {community.name} (confidence: {confidence})")
        
        except Exception as e:
            self.logger.error(f"Error filtering high confidence changes: {e}")
        
        return filtered_diff
    
    def _estimate_confidence(self, community: Community) -> float:
        """
        Estimate confidence score for a community based on its attributes
        """
        try:
            theme = getattr(community, 'theme', '').lower()
            
            # Selenium-based detection is HIGHEST confidence (real HTML elements)
            if 'selenium' in theme:
                return 0.95
            
            # URL-based detection is most reliable
            if 'url' in theme or 'direct' in theme:
                return 0.9
            
            # Pattern-based detection is moderately reliable
            if 'hashtag' in theme or 'mention' in theme:
                return 0.7
            
            # Activity-based detection is less reliable
            if 'activity' in theme or 'engagement' in theme or 'content' in theme:
                return 0.6
            
            # Social graph based detection
            if 'following' in theme or 'follower' in theme:
                return 0.5
            
            # Temporal or conversation based
            if 'temporal' in theme or 'conversation' in theme:
                return 0.4
            
            # Default confidence
            return 0.5
        
        except Exception as e:
            self.logger.debug(f"Error estimating confidence: {e}")
            return 0.5
    
    def generate_change_summary(self, diff: Dict[str, List]) -> str:
        """
        Generate a human-readable summary of community changes
        """
        try:
            summary_lines = []
            
            if diff['joined']:
                summary_lines.append(f"✅ Joined {len(diff['joined'])} communities:")
                for change in diff['joined'][:5]:  # Show first 5
                    community = change['community']
                    method = change.get('detection_method', 'unknown')
                    summary_lines.append(f"   👤 {community.name} (Role: {community.role}, Method: {method})")
                if len(diff['joined']) > 5:
                    summary_lines.append(f"   ... and {len(diff['joined']) - 5} more")
            
            if diff['left']:
                summary_lines.append(f"❌ Left {len(diff['left'])} communities:")
                for change in diff['left'][:5]:  # Show first 5
                    community = change['community']
                    summary_lines.append(f"   👤 {community.name}")
                if len(diff['left']) > 5:
                    summary_lines.append(f"   ... and {len(diff['left']) - 5} more")
            
            if diff['role_changed']:
                summary_lines.append(f"🔄 Role changes in {len(diff['role_changed'])} communities:")
                for change in diff['role_changed']:
                    community = change['community']
                    old_role = change['old_role']
                    new_role = change['new_role']
                    summary_lines.append(f"   👤 {community.name}: {old_role} → {new_role}")
            
            if diff['updated']:
                summary_lines.append(f"📝 Updates in {len(diff['updated'])} communities:")
                for change in diff['updated'][:3]:  # Show first 3
                    community = change['community']
                    changes = change['changes']
                    change_types = list(changes.keys())
                    summary_lines.append(f"   👤 {community.name}: {', '.join(change_types)}")
                if len(diff['updated']) > 3:
                    summary_lines.append(f"   ... and {len(diff['updated']) - 3} more")
            
            if not any(diff.values()):
                summary_lines.append("No community changes detected")
            
            return '\n'.join(summary_lines)
        
        except Exception as e:
            self.logger.error(f"Error generating change summary: {e}")
            return "Error generating summary"
    
    def calculate_differences(self, previous_communities: List[Community], current_communities: List[Community]) -> Dict[str, List]:
        """
        Calculate differences between previous and current community lists
        
        Args:
            previous_communities: List of previously detected communities
            current_communities: List of currently detected communities
            
        Returns:
            Dict with 'joined', 'left', 'created', and 'role_changes' lists
        """
        return self.detailed_community_diff(previous_communities, current_communities)
    
    def filter_and_validate_changes(self, diff: Dict[str, List]) -> Dict[str, List]:
        """
        Filter and validate detected changes for reliability
        
        Args:
            diff: Raw differences dictionary
            
        Returns:
            Filtered and validated differences
        """
        return self.filter_high_confidence_changes(diff, min_confidence=0.6)
    
    def calculate_change_confidence(self, filtered_diff: Dict[str, List], enhanced_changes: Dict[str, Any]) -> float:
        """
        Calculate confidence score for detected changes
        
        Args:
            filtered_diff: Filtered differences
            enhanced_changes: Enhanced detection results
            
        Returns:
            Overall confidence score between 0.0 and 1.0
        """
        try:
            all_communities = []
            
            # Collect all communities from changes
            for change_list in filtered_diff.values():
                for change in change_list:
                    community = change.get('community')
                    if community:
                        all_communities.append(community)
            
            # Add enhanced detections
            enhanced_detections = enhanced_changes.get('new_detections', [])
            all_communities.extend(enhanced_detections)
            
            return self.calculate_confidence_score(all_communities)
            
        except Exception as e:
            self.logger.error(f"Error calculating change confidence: {e}")
            return 0.5 