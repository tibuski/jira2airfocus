"""
Models package for JIRA to Airfocus integration.

This package contains data model classes for handling JIRA and Airfocus items
with proper encapsulation, validation, and type safety.
"""

from .jira_item import JiraItem, JiraStatus, JiraAssignee, JiraAttachment
from .airfocus_item import AirfocusItem

__all__ = [
    'JiraItem', 
    'JiraStatus', 
    'JiraAssignee', 
    'JiraAttachment',
    'AirfocusItem'
]
