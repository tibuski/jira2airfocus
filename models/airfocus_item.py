"""
Airfocus Item Class

This module provides a class-based approach to handling Airfocus items,
encapsulating the data transformation and API payload generation logic.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json
from loguru import logger

import constants


@dataclass
class AirfocusItem:
    """
    Represents an Airfocus item with methods for creation and updates.
    
    This class encapsulates all the logic for handling Airfocus items,
    including field mappings, payload generation, and validation.
    """
    
    name: str
    jira_key: str
    description: str = ""
    status_id: Optional[str] = None
    team_field_value: Optional[str] = None
    color: str = "blue"
    item_id: Optional[str] = None
    assignee_user_ids: List[str] = None
    assignee_user_group_ids: List[str] = None
    order: int = 0
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.assignee_user_ids is None:
            self.assignee_user_ids = []
        if self.assignee_user_group_ids is None:
            self.assignee_user_group_ids = []
    
    @classmethod
    def from_jira_issue(cls, issue_data: Dict[str, Any]) -> 'AirfocusItem':
        """
        Create AirfocusItem from JIRA issue data.
        
        Args:
            issue_data: Dictionary containing JIRA issue data
            
        Returns:
            AirfocusItem instance populated with JIRA data
        """
        # Import here to avoid circular import
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import main
        
        jira_key = issue_data.get("key", "")
        name = issue_data.get("summary", "")
        description = main.build_markdown_description(issue_data)
        
        # Get status mapping
        jira_status_name = issue_data.get("status", {}).get("name", "") if issue_data.get("status") else ""
        status_id = main.get_mapped_status_id(jira_status_name, jira_key)
        
        # Get team field value from constants
        team_field_value = None
        if constants.TEAM_FIELD:
            for field_name, field_values in constants.TEAM_FIELD.items():
                team_field_value = field_values[0] if field_values else None
                break
        
        return cls(
            name=name,
            jira_key=jira_key,
            description=description,
            status_id=status_id,
            team_field_value=team_field_value
        )
    
    @classmethod
    def from_airfocus_data(cls, airfocus_data: Dict[str, Any]) -> 'AirfocusItem':
        """
        Create AirfocusItem from existing Airfocus API data.
        
        Args:
            airfocus_data: Dictionary containing Airfocus item data
            
        Returns:
            AirfocusItem instance populated with Airfocus data
        """
        # Extract JIRA key from fields
        fields = airfocus_data.get("fields", {})
        jira_key_field = fields.get("JIRA-KEY", {})
        jira_key = jira_key_field.get("value", "") if jira_key_field else ""
        
        return cls(
            name=airfocus_data.get("name", ""),
            jira_key=jira_key,
            description=airfocus_data.get("description", ""),
            status_id=airfocus_data.get("statusId", ""),
            color=airfocus_data.get("color", "blue"),
            item_id=airfocus_data.get("id", ""),
            assignee_user_ids=airfocus_data.get("assigneeUserIds", []),
            assignee_user_group_ids=airfocus_data.get("assigneeUserGroupIds", []),
            order=airfocus_data.get("order", 0)
        )
    
    def _get_jira_key_field_id(self) -> Optional[str]:
        """Get the JIRA-KEY field ID from field mappings."""
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import main
        return main.get_field_mappings()
    
    def _get_team_field_configuration(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get team field configuration from constants.
        
        Returns:
            tuple: (field_name, field_id, team_field_value)
        """
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import main
        
        if not constants.TEAM_FIELD:
            return None, None, None
        
        for field_name, field_values in constants.TEAM_FIELD.items():
            field_id = main.get_airfocus_field_id(field_name)
            if field_id:
                team_value = field_values[0] if field_values else None
                return field_name, field_id, team_value
            else:
                logger.error("Team field '{}' not found in Airfocus field mappings", field_name)
        
        return None, None, None
    
    def _build_fields_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Build the fields dictionary for API payloads.
        
        Returns:
            Dictionary containing field mappings for the API
        """
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import main
        
        fields_dict = {}
        
        # Add JIRA-KEY field
        jira_key_field_id = self._get_jira_key_field_id()
        if jira_key_field_id:
            fields_dict[jira_key_field_id] = {
                "text": self.jira_key
            }
        else:
            logger.error("JIRA-KEY field ID not found")
        
        # Add team field if available
        if self.team_field_value:
            field_name, team_field_id, _ = self._get_team_field_configuration()
            if team_field_id and field_name:
                team_option_id = main.get_airfocus_field_option_id(field_name, self.team_field_value)
                if team_option_id:
                    fields_dict[team_field_id] = {
                        "selection": [team_option_id]
                    }
                    logger.debug("Added team field {}: {} (option ID: {})", 
                               team_field_id, self.team_field_value, team_option_id)
                else:
                    logger.error("Could not find option ID for team value '{}' in field '{}'", 
                               self.team_field_value, field_name)
        
        return fields_dict
    
    def to_create_payload(self) -> Dict[str, Any]:
        """
        Generate payload for POST /items API call.
        
        Returns:
            Dictionary containing the complete payload for item creation
        """
        fields_dict = self._build_fields_dict()
        
        payload = {
            "name": self.name,
            "description": {
                "markdown": self.description,
                "richText": True
            },
            "statusId": self.status_id,
            "color": self.color,
            "assigneeUserIds": self.assignee_user_ids,
            "assigneeUserGroupIds": self.assignee_user_group_ids,
            "order": self.order,
            "fields": fields_dict
        }
        
        return payload
    
    def to_patch_payload(self) -> List[Dict[str, Any]]:
        """
        Generate JSON Patch operations for PATCH /items/{id} API call.
        
        Returns:
            List of JSON Patch operations
        """
        import main
        
        patch_operations = []
        
        # Update name
        patch_operations.append({
            "op": "replace",
            "path": "/name",
            "value": self.name
        })
        
        # Update description (as string when using markdown media type)
        patch_operations.append({
            "op": "replace",
            "path": "/description",
            "value": self.description
        })
        
        # Update status if we have one
        if self.status_id:
            patch_operations.append({
                "op": "replace",
                "path": "/statusId",
                "value": self.status_id
            })
        
        # Update JIRA-KEY field
        jira_key_field_id = self._get_jira_key_field_id()
        if jira_key_field_id:
            patch_operations.append({
                "op": "replace",
                "path": f"/fields/{jira_key_field_id}",
                "value": {
                    "text": self.jira_key
                }
            })
        
        # Update team field if available
        if self.team_field_value:
            field_name, team_field_id, _ = self._get_team_field_configuration()
            if team_field_id and field_name:
                team_option_id = main.get_airfocus_field_option_id(field_name, self.team_field_value)
                if team_option_id:
                    patch_operations.append({
                        "op": "replace",
                        "path": f"/fields/{team_field_id}",
                        "value": {
                            "selection": [team_option_id]
                        }
                    })
                    logger.debug("Updated team field {}: {} (option ID: {})", 
                               team_field_id, self.team_field_value, team_option_id)
                else:
                    logger.error("Could not find option ID for team value '{}' in field '{}' for update", 
                               self.team_field_value, field_name)
        
        return patch_operations
    
    def validate(self) -> List[str]:
        """
        Validate item data and return list of errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.name.strip():
            errors.append("Item name cannot be empty")
        
        if not self.jira_key.strip():
            errors.append("JIRA key cannot be empty")
        
        # Check if JIRA-KEY field exists
        jira_key_field_id = self._get_jira_key_field_id()
        if not jira_key_field_id:
            errors.append("JIRA-KEY field ID not found in Airfocus field mappings")
        
        # Validate team field configuration if specified
        if self.team_field_value:
            field_name, team_field_id, _ = self._get_team_field_configuration()
            if not team_field_id:
                errors.append(f"Team field not found in Airfocus field mappings")
        
        return errors
    
    def __str__(self) -> str:
        """String representation of the item."""
        return f"AirfocusItem(jira_key='{self.jira_key}', name='{self.name[:50]}...', item_id='{self.item_id}')"
    
    def __repr__(self) -> str:
        """Detailed string representation of the item."""
        return (f"AirfocusItem(name='{self.name}', jira_key='{self.jira_key}', "
                f"status_id='{self.status_id}', item_id='{self.item_id}')")
