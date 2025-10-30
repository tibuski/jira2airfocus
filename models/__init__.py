"""
Models package for JIRA to Airfocus integration.

This package contains data model classes for handling JIRA and Airfocus items
with proper encapsulation, validation, and type safety.
"""

import json
import os
from typing import Optional
from loguru import logger

from .jira_item import JiraItem, JiraStatus, JiraAssignee, JiraAttachment
from .airfocus_item import AirfocusItem


def get_airfocus_field_id(field_name: str) -> Optional[str]:
    """
    Get a specific field ID from the saved Airfocus fields data.
    
    Args:
        field_name (str): The name of the field to retrieve the ID for.
    
    Returns:
        str: The field ID for the specified field, or None if not found.
    """
    try:
        filepath = "./data/airfocus_fields.json"
        
        # Check if file exists
        if not os.path.exists(filepath):
            logger.warning("Airfocus fields file not found at {}. Run get_airfocus_field_data() first.", filepath)
            return None
        
        # Read the field data
        with open(filepath, 'r', encoding='utf-8') as f:
            field_data = json.load(f)
        
        # Get field ID from mapping
        field_mapping = field_data.get("field_mapping", {})
        field_id = field_mapping.get(field_name)
        
        if field_id:
            logger.debug("Found {} field ID: {}", field_name, field_id)
            return field_id
        else:
            logger.warning("{} field not found in saved field mapping", field_name)
            logger.debug("Available fields: {}", list(field_mapping.keys()))
            return None
            
    except Exception as e:
        logger.error("Exception occurred while reading field data: {}", e)
        return None


def get_airfocus_status_id(status_name: str) -> Optional[str]:
    """
    Get a specific status ID from the saved Airfocus fields data.
    
    Args:
        status_name (str): The name of the status to retrieve the ID for.
    
    Returns:
        str: The status ID for the specified status, or None if not found.
    """
    try:
        filepath = "./data/airfocus_fields.json"
        
        # Check if file exists
        if not os.path.exists(filepath):
            logger.warning("Airfocus fields file not found at {}. Run get_airfocus_field_data() first.", filepath)
            return None
        
        # Read the field data
        with open(filepath, 'r', encoding='utf-8') as f:
            field_data = json.load(f)
        
        # Get status ID from mapping
        status_mapping = field_data.get("status_mapping", {})
        status_id = status_mapping.get(status_name)
        
        if status_id:
            logger.debug("Found {} status ID: {}", status_name, status_id)
            return status_id
        else:
            logger.warning("{} status not found in saved status mapping", status_name)
            logger.debug("Available statuses: {}", list(status_mapping.keys()))
            return None
            
    except Exception as e:
        logger.error("Exception occurred while reading status data: {}", e)
        return None


def get_mapped_status_id(jira_status_name: str, jira_key: str) -> Optional[str]:
    """
    Get Airfocus status ID from JIRA status name using mappings and fallbacks.
    
    Args:
        jira_status_name (str): JIRA status name to map
        jira_key (str): JIRA issue key for logging purposes
        
    Returns:
        str: Airfocus status ID, or None if no suitable status found
    """
    import constants
    
    if not jira_status_name:
        return None
    
    # Try mappings from constants.py first
    for airfocus_status, jira_variants in constants.JIRA_TO_AIRFOCUS_STATUS_MAPPING.items():
        if jira_status_name in jira_variants:
            status_id = get_airfocus_status_id(airfocus_status)
            if status_id:
                logger.info("Mapped JIRA status '{}' to Airfocus status '{}'", jira_status_name, airfocus_status)
                return status_id
    
    # If no mapping found, warn and fall back to Draft
    logger.warning("JIRA status '{}' not found in status mappings. Falling back to 'Draft' status.", jira_status_name)
    status_id = get_airfocus_status_id("Draft")
    
    # If still no status found, get the default status
    if not status_id:
        try:
            filepath = "./data/airfocus_fields.json"
            with open(filepath, 'r', encoding='utf-8') as f:
                field_data = json.load(f)
            
            # Look for default status or fall back to first available
            statuses = field_data.get("statuses", [])
            for status in statuses:
                if status.get("default", False):
                    status_id = status.get("id")
                    logger.info("Using default status '{}' for JIRA issue {}", status.get("name"), jira_key)
                    return status_id
            
            # If no default found, use first available status
            if statuses:
                status_id = statuses[0].get("id")
                logger.warning("No suitable status found for JIRA status '{}', using first available status '{}' for issue {}", 
                             jira_status_name, statuses[0].get("name"), jira_key)
                return status_id
                
        except Exception as e:
            logger.error("Failed to get default status: {}", e)
    
    if not status_id:
        logger.error("Could not determine status ID for JIRA issue {}. Status will be left empty.", jira_key)
    
    return status_id


__all__ = [
    'JiraItem', 
    'JiraStatus', 
    'JiraAssignee', 
    'JiraAttachment',
    'AirfocusItem',
    'get_airfocus_field_id',
    'get_airfocus_status_id',
    'get_mapped_status_id'
]
