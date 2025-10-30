#!/usr/bin/env python3
"""
Test script for the AirfocusItem class to ensure it works correctly.
"""

import json
from airfocus_item import AirfocusItem

# Sample JIRA issue data for testing
sample_jira_issue = {
    "key": "TEST-123",
    "summary": "Test Epic Issue",
    "description": "This is a test description for the epic",
    "status": {
        "name": "In Progress",
        "id": "3",
        "statusCategory": {
            "key": "indeterminate",
            "name": "In Progress"
        }
    },
    "url": "https://example.atlassian.net/browse/TEST-123",
    "assignee": {
        "displayName": "John Doe",
        "emailAddress": "john.doe@example.com",
        "accountId": "12345"
    },
    "attachments": [
        {
            "filename": "requirements.pdf",
            "url": "https://example.atlassian.net/attachments/123/requirements.pdf"
        }
    ],
    "updated": "2025-10-30T10:30:00"
}

# Sample Airfocus item data for testing
sample_airfocus_item = {
    "id": "af-item-123",
    "name": "Test Epic Issue",
    "description": "This is a test description",
    "statusId": "status-123",
    "color": "blue",
    "archived": False,
    "createdAt": "2025-10-30T10:00:00Z",
    "lastUpdatedAt": "2025-10-30T10:30:00Z",
    "fields": {
        "JIRA-KEY": {
            "id": "field-123",
            "value": "TEST-123"
        }
    }
}

def test_airfocus_item_class():
    """Test the AirfocusItem class functionality."""
    
    print("Testing AirfocusItem class...")
    print("=" * 50)
    
    # Test 1: Create from JIRA issue data
    print("Test 1: Creating AirfocusItem from JIRA issue data")
    try:
        # This will fail because we don't have the main module properly imported
        # but we can test the basic structure
        item = AirfocusItem(
            name=sample_jira_issue["summary"],
            jira_key=sample_jira_issue["key"],
            description=sample_jira_issue["description"],
            status_id="test-status-id",
            team_field_value="Test Team"
        )
        print(f"✓ Created item: {item}")
        print(f"  - Name: {item.name}")
        print(f"  - JIRA Key: {item.jira_key}")
        print(f"  - Status ID: {item.status_id}")
        print(f"  - Team Value: {item.team_field_value}")
    except Exception as e:
        print(f"✗ Error creating from JIRA data: {e}")
    
    # Test 2: Create from Airfocus data
    print("\nTest 2: Creating AirfocusItem from Airfocus data")
    try:
        item = AirfocusItem.from_airfocus_data(sample_airfocus_item)
        print(f"✓ Created item: {item}")
        print(f"  - Name: {item.name}")
        print(f"  - JIRA Key: {item.jira_key}")
        print(f"  - Item ID: {item.item_id}")
        print(f"  - Status ID: {item.status_id}")
    except Exception as e:
        print(f"✗ Error creating from Airfocus data: {e}")
    
    # Test 3: Validation
    print("\nTest 3: Validation")
    try:
        # Valid item
        valid_item = AirfocusItem(
            name="Valid Item",
            jira_key="VALID-123",
            description="Valid description"
        )
        errors = valid_item.validate()
        print(f"✓ Valid item errors: {errors}")
        
        # Invalid item
        invalid_item = AirfocusItem(
            name="",  # Empty name
            jira_key="",  # Empty JIRA key
            description="Invalid item"
        )
        errors = invalid_item.validate()
        print(f"✓ Invalid item errors: {errors}")
    except Exception as e:
        print(f"✗ Error during validation: {e}")
    
    # Test 4: String representations
    print("\nTest 4: String representations")
    try:
        item = AirfocusItem(
            name="Test Item with Long Name That Should Be Truncated",
            jira_key="TEST-456",
            item_id="af-456"
        )
        print(f"✓ str(): {str(item)}")
        print(f"✓ repr(): {repr(item)}")
    except Exception as e:
        print(f"✗ Error with string representations: {e}")
    
    print("\n" + "=" * 50)
    print("AirfocusItem class tests completed!")

if __name__ == "__main__":
    test_airfocus_item_class()
