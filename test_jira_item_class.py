"""
Test script demonstrating the benefits of using JiraItem class
"""

from jira_item import JiraItem, JiraStatus, JiraAssignee, JiraAttachment

def test_jira_item_class():
    """Test the JiraItem class functionality."""
    
    # Example: Creating a JiraItem from raw API data
    raw_jira_data = {
        "key": "PROJ-123",
        "fields": {
            "summary": "Test Epic Item",
            "description": "This is a test epic for demonstration",
            "status": {
                "name": "In Progress",
                "id": "3",
                "statusCategory": {
                    "key": "indeterminate",
                    "name": "In Progress"
                }
            },
            "assignee": {
                "displayName": "John Doe", 
                "emailAddress": "john.doe@company.com",
                "accountId": "12345"
            },
            "attachment": [
                {
                    "filename": "test-document.pdf",
                    "content": "https://jira.example.com/secure/attachment/12345/test-document.pdf"
                },
                {
                    "filename": "screenshot.png", 
                    "content": "https://jira.example.com/secure/attachment/67890/screenshot.png",
                    "thumbnail": "https://jira.example.com/secure/thumbnail/67890/_thumb_67890.png"
                }
            ],
            "updated": "2025-10-30T14:30:45.000+0100"
        }
    }
    
    # Create JiraItem from API data
    jira_item = JiraItem.from_jira_api_data(raw_jira_data, "PROJ", "https://jira.example.com")
    
    print("=== JiraItem Class Benefits Demo ===")
    print(f"JIRA Item: {jira_item}")
    print(f"Key: {jira_item.key}")
    print(f"Summary: {jira_item.summary}")
    print(f"Status: {jira_item.get_status_name()}")
    print(f"Assignee: {jira_item.get_assignee_display_name()}")
    print(f"Has attachments: {jira_item.has_attachments()}")
    print(f"Updated: {jira_item.updated}")
    print()
    
    # Validate the item
    errors = jira_item.validate()
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("✅ JiraItem validation passed!")
    print()
    
    # Generate markdown description
    print("=== Generated Markdown Description ===")
    print(jira_item.build_markdown_description())
    print()
    
    # Convert back to dictionary (for backward compatibility)
    dict_format = jira_item.to_dict()
    print("=== Dictionary Format (for backward compatibility) ===")
    print(f"Keys: {list(dict_format.keys())}")
    print()
    
    # Test with invalid data
    print("=== Validation Test with Invalid Data ===")
    invalid_item = JiraItem(
        key="",  # Invalid: empty key
        url="",  # Invalid: empty URL
        summary=""  # Invalid: empty summary
    )
    
    validation_errors = invalid_item.validate()
    print(f"Validation errors for invalid item: {validation_errors}")
    print()
    
    # Test individual components
    print("=== Individual Components ===")
    
    # Status component
    status = JiraStatus.from_jira_data({
        "name": "Done",
        "id": "10001", 
        "statusCategory": {
            "key": "done",
            "name": "Done"
        }
    })
    print(f"Status object: name='{status.name}', category='{status.category_name}'")
    
    # Assignee component
    assignee = JiraAssignee.from_jira_data({
        "displayName": "Jane Smith",
        "emailAddress": "jane.smith@company.com", 
        "accountId": "67890"
    })
    print(f"Assignee markdown: {assignee.to_markdown()}")
    
    # Test attachment components (both formats)
    print("\n=== Attachment Tests ===")
    
    # Test raw API format (uses 'content')
    attachment_raw = JiraAttachment.from_jira_data({
        "filename": "requirements.docx",
        "content": "https://jira.example.com/secure/attachment/123/requirements.docx"
    })
    print(f"Raw API attachment markdown: {attachment_raw.to_markdown()}")
    print(f"Raw API attachment valid: {attachment_raw.is_valid()}")
    
    # Test simplified format (uses 'url')
    attachment_simplified = JiraAttachment.from_jira_data({
        "filename": "design.pdf",
        "url": "https://jira.example.com/secure/attachment/456/design.pdf"
    })
    print(f"Simplified attachment markdown: {attachment_simplified.to_markdown()}")
    print(f"Simplified attachment valid: {attachment_simplified.is_valid()}")
    
    # Test invalid attachment (missing URL)
    attachment_invalid = JiraAttachment.from_jira_data({
        "filename": "broken.doc"
        # No URL field
    })
    print(f"Invalid attachment markdown: {attachment_invalid.to_markdown()}")
    print(f"Invalid attachment valid: {attachment_invalid.is_valid()}")
    
    # Test attachment validation in JiraItem
    print(f"\nValid attachments in test item: {len(jira_item.get_valid_attachments())}")
    print(f"Invalid attachments in test item: {len(jira_item.get_invalid_attachments())}")


if __name__ == "__main__":
    test_jira_item_class()
