"""
JIRA to Airfocus Integration Script

This module provides functionality to fetch data from JIRA projects and sync them with Airfocus.
It handles authentication, data retrieval, and logging for the integration process.
"""

import sys
import os
import requests
import json
from datetime import datetime
import urllib3
import glob
import dotenv

from loguru import logger

import constants

# Disable SSL warnings when certificate verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure loguru logging with both file and console output
logger.remove()  # Remove default handler
logger.add(
    "jira2airfocus.log",
    level=constants.LOGGING_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
    rotation="10 MB",
    retention="30 days"
)
logger.add(
    sys.stderr,
    level=constants.LOGGING_LEVEL,
    colorize=True
)

# Load environment variables from .env file
dotenv.load_dotenv()

# Authentication credentials from environment variables
JIRA_PAT = os.getenv("JIRA_PAT")
AIRFOCUS_API_KEY = os.getenv("AIRFOCUS_API_KEY")
logger.debug("Jira PAT: {}", JIRA_PAT)
logger.debug("Airfocus API Key: {}", AIRFOCUS_API_KEY)

def get_jira_project_data(project_key):
    """
    Fetch JIRA project data including issues, descriptions, status, and assignees.
    
    This function queries the JIRA REST API to retrieve all issues for a specified project,
    including their summary, description, status, and assignee information. The data is
    stored in a JSON file in the ./data directory for further processing.
    
    Args:
        project_key (str): The JIRA project key to fetch data from.
        
    Returns:
        dict: Complete JSON response containing all project issues if successful,
              or an error dictionary if the request fails.
    """
    all_issues = []
    start_at = 0
    max_results = 100  # Increase batch size for better performance
    total_issues = None

    # Construct API endpoint URL
    url = f"{constants.JIRA_REST_URL}/search"
    
    # Set up authentication headers
    headers = {
        "Authorization": f"Bearer {JIRA_PAT}",
        "Content-Type": "application/json"
    }

    while True:
        # Define JQL query to fetch specific fields for the project
        # Note: "key" field is included by default and contains the issue key (e.g., PROJ-123)
        # Exclude closed issues from the results
        query = {
            "jql": f"project = {project_key} AND status != Closed",
            "fields": ["key", "summary", "description", "status", "assignee", "attachment", "updated"],
            "startAt": start_at,
            "maxResults": max_results
        }
        logger.info("Requesting data from endpoint: {}", url)
        logger.debug("Using JQL query: {}", query['jql'])
        logger.info("Requesting issues {} to {}", start_at, start_at + max_results - 1)
        
        try:
            response = requests.post(url, headers=headers, json=query, verify=False, timeout=30)
            logger.info("Received response with status code {}", response.status_code)
            logger.debug("Received response with status code {}", response.json())
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error while fetching data for Jira project {project_key}: {str(e)}"
            logger.error("{}", error_msg)
            return {"error": error_msg}
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout error while fetching data for Jira project {project_key}: {str(e)}"
            logger.error("{}", error_msg)
            return {"error": error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while fetching data for Jira project {project_key}: {str(e)}"
            logger.error("{}", error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error while fetching data for Jira project {project_key}: {str(e)}"
            logger.error("{}", error_msg)
            return {"error": error_msg}
        
        if response.status_code != 200:
            error_msg = f"Failed to fetch data for Jira project {project_key}. Status code: {response.status_code}"
            logger.error("{}", error_msg)
            logger.error("Response: {}", response.text)
            return {"error": f"Failed to fetch data. Status: {response.status_code}"}

        data = response.json()
        
        # Extract issues from the response
        raw_issues = data.get("issues", [])
        
        # Extract only the needed fields from each issue
        for issue in raw_issues:
            # Get the issue key (always available)
            issue_key = issue.get("key", "")
            
            # Extract fields from the fields object
            fields = issue.get("fields", {})
            
            # Extract base URL from JIRA_REST_URL (remove /rest/api/latest)
            base_url = constants.JIRA_REST_URL.replace("/rest/api/latest", "")
            
            # Process attachments if present - only keep URLs for linking
            attachments = fields.get("attachment", [])
            attachment_list = []
            for attachment in attachments:
                attachment_info = {
                    "filename": attachment.get("filename", ""),
                    "url": attachment.get("content", ""),
                    "thumbnail": attachment.get("thumbnail", "") if attachment.get("thumbnail") else None
                }
                attachment_list.append(attachment_info)
            
            # Process the updated timestamp - remove .000+0000 suffix
            raw_updated = fields.get("updated", "")
            clean_updated = raw_updated.replace(".000+0000", "") if raw_updated else ""
            
            # Create simplified issue object with only needed data
            simplified_issue = {
                "key": issue_key,
                "url": f"{base_url}/projects/{project_key}/issues/{issue_key}",
                "summary": fields.get("summary", ""),
                "description": fields.get("description", ""),
                "status": {
                    "name": fields.get("status", {}).get("name", ""),
                    "id": fields.get("status", {}).get("id", "")
                } if fields.get("status") else None,
                "assignee": {
                    "displayName": fields.get("assignee", {}).get("displayName", ""),
                    "emailAddress": fields.get("assignee", {}).get("emailAddress", ""),
                    "accountId": fields.get("assignee", {}).get("accountId", "")
                } if fields.get("assignee") else None,
                "attachments": attachment_list,
                "updated": clean_updated
            }
            
            logger.debug("Processed issue: {}", simplified_issue['url'])

            all_issues.append(simplified_issue)
        
        # Get total count from first response
        if total_issues is None:
            total_issues = data.get("total", 0)
            logger.info("Found {} total issues for project {}", total_issues, project_key)

        logger.info("Fetched {} issues (batch {})", len(raw_issues), start_at//max_results + 1)
        
        # Check if we've fetched all issues
        if len(raw_issues) < max_results or len(all_issues) >= total_issues:
            break
        
        # Prepare for next batch
        start_at += max_results

    # Save data to JSON file in ./data directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jira_{project_key}_issues_{timestamp}.json"
    filepath = f"./data/{filename}"
    
    try:
        # Create data directory if it doesn't exist
        os.makedirs("./data", exist_ok=True)
        
        # Prepare final data structure
        final_data = {
            "project_key": project_key,
            "total_issues": len(all_issues),
            "fetched_at": datetime.now().isoformat(),
            "issues": all_issues
        }
        
        # Save to timestamped JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        # Also save to a standard filename for easy access by sync function
        standard_filepath = "./data/jira_data.json"
        with open(standard_filepath, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        logger.info("Successfully saved {} issues to {}", len(all_issues), filepath)
        logger.info("Also saved to standard file: {}", standard_filepath)
        
        # Clean up old JIRA data files, keeping only the 10 most recent
        cleanup_old_json_files(f"jira_{project_key}_issues_*.json", keep_count=10)
        
    except Exception as e:
        logger.error("Failed to save data to file: {}", e)
        return {"error": f"Failed to save data: {e}"}

    logger.info("Successfully fetched {} total issues for project {}", len(all_issues), project_key)
    return final_data


def get_airfocus_field_data(workspace_id):
    """
    Get all field data from an Airfocus workspace and save to JSON file.
    
    This function queries the Airfocus workspace API to retrieve all available fields
    and saves them to a JSON file in the ./data directory for later use.
    
    Args:
        workspace_id (str): The Airfocus workspace ID to query.
        
    Returns:
        dict: Dictionary containing all field data if successful, or None if error occurred.
    """
    # Construct Airfocus workspace API endpoint URL
    url = f"{constants.AIRFOCUS_REST_URL}/workspaces/{workspace_id}"
    
    # Set up authentication headers for Airfocus
    headers = {
        "Authorization": f"Bearer {AIRFOCUS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("Successfully retrieved workspace data for {}", workspace_id)
            
            # Extract fields data from _embedded.fields (it's a dictionary, not a list)
            embedded = data.get("_embedded", {})
            fields_dict = embedded.get("fields", {})
            statuses_dict = embedded.get("statuses", {})
            
            # Convert fields dictionary to list for easier processing
            fields = list(fields_dict.values())
            statuses = list(statuses_dict.values())
            
            # Create fields mapping for easier access
            field_data = {
                "workspace_id": workspace_id,
                "fetched_at": datetime.now().isoformat(),
                "fields": fields,
                "field_mapping": {},
                "statuses": statuses,
                "status_mapping": {}
            }
            
            # Create name-to-id mapping for fields
            for field in fields:
                field_name = field.get("name", "")
                field_id = field.get("id", "")
                if field_name and field_id:
                    field_data["field_mapping"][field_name] = field_id
            
            # Create name-to-id mapping for statuses
            for status in statuses:
                status_name = status.get("name", "")
                status_id = status.get("id", "")
                if status_name and status_id:
                    field_data["status_mapping"][status_name] = status_id
            
            # Save to JSON file
            try:
                os.makedirs("./data", exist_ok=True)
                filepath = "./data/airfocus_fields.json"
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(field_data, f, indent=2, ensure_ascii=False)
                
                logger.info("Successfully saved {} field definitions and {} statuses to {}", len(fields), len(statuses), filepath)
                logger.debug("Available fields: {}", list(field_data['field_mapping'].keys()))
                logger.debug("Available statuses: {}", list(field_data['status_mapping'].keys()))
                
                return field_data
                
            except Exception as e:
                logger.error("Failed to save field data to file: {}", e)
                return None
            
        else:
            logger.error("Failed to retrieve workspace data for {}. Status code: {}", workspace_id, response.status_code)
            logger.error("Response: {}", response.text)
            return None
    
    except Exception as e:
        logger.error("Exception occurred while retrieving workspace data for {}: {}", workspace_id, e)
        return None


def get_airfocus_field_id(field_name):
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


def get_airfocus_status_id(status_name):
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


def get_airfocus_project_data(workspace_id):
    """
    Fetch Airfocus project data including all items and their details.
    
    This function queries the Airfocus REST API to retrieve all items for a specified workspace,
    including their name, description, status, and custom fields. The data is stored in a 
    JSON file in the ./data directory for further processing.
    
    Args:
        workspace_id (str): The Airfocus workspace ID to fetch data from.
        
    Returns:
        dict: Complete JSON response containing all workspace items if successful,
              or an error dictionary if the request fails.
    """
    all_items = []
    
    # Set up authentication headers
    headers = {
        "Authorization": f"Bearer {AIRFOCUS_API_KEY}",
        "Content-Type": "application/json"
    }

    # Use the items/search endpoint with POST request
    url = f"{constants.AIRFOCUS_REST_URL}/workspaces/{workspace_id}/items/search"
    
    # Search payload to get all items (empty search criteria)
    search_payload = {
        "filters": {},
        "pagination": {
            "limit": 1000,
            "offset": 0
        }
    }
    
    logger.info("Requesting data from endpoint: {}", url)
    logger.debug("Search payload: {}", json.dumps(search_payload, indent=2))
    response = requests.post(url, headers=headers, json=search_payload, verify=False)
    
    if response.status_code != 200:
        logger.error("Failed to fetch items from endpoint. Status code: {}", response.status_code)
        logger.error("Response: {}", response.text)
        return {"error": f"Failed to fetch data. Status: {response.status_code}"}

    try:
        data = response.json()
        
        # Extract items from the response
        raw_items = data.get("items", [])
        
        # Extract only the needed fields from each item
        for item in raw_items:
            # Get basic item data
            item_id = item.get("id", "")
            item_name = item.get("name", "")
            
            # Extract status information
            status_id = item.get("statusId", "")
            
            # Extract custom fields
            fields = item.get("fields", {})
            
            # Create simplified item object with only needed data
            simplified_item = {
                "id": item_id,
                "name": item_name,
                "description": item.get("description", ""),
                "statusId": status_id,
                "color": item.get("color", ""),
                "archived": item.get("archived", False),
                "createdAt": item.get("createdAt", ""),
                "lastUpdatedAt": item.get("lastUpdatedAt", ""),
                "fields": fields
            }
            
            logger.debug("Processed Airfocus item: {} (ID: {})", item_name, item_id)
            all_items.append(simplified_item)

        logger.info("Found {} total items in Airfocus workspace {}", len(all_items), workspace_id)

        # Save data to JSON file in ./data directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"airfocus_{workspace_id}_items_{timestamp}.json"
        filepath = f"./data/{filename}"
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs("./data", exist_ok=True)
            
            # Prepare final data structure
            final_data = {
                "workspace_id": workspace_id,
                "total_items": len(all_items),
                "fetched_at": datetime.now().isoformat(),
                "items": all_items
            }
            
            # Save to timestamped JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            # Also save to a standard filename for easy access by sync function
            standard_filepath = "./data/airfocus_data.json"
            with open(standard_filepath, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Successfully saved {} items to {}", len(all_items), filepath)
            logger.info("Also saved to standard file: {}", standard_filepath)
            
            # Clean up old Airfocus data files, keeping only the 10 most recent
            cleanup_old_json_files(f"airfocus_{workspace_id}_items_*.json", keep_count=10)
            
        except Exception as e:
            logger.error("Failed to save data to file: {}", e)
            return {"error": f"Failed to save data: {e}"}

        logger.info("Successfully fetched {} total items from Airfocus workspace {}", len(all_items), workspace_id)
        return final_data

    except Exception as e:
        logger.error("Exception occurred while fetching Airfocus data: {}", e)
        return {"error": f"Exception occurred: {str(e)}"}


def get_airfocus_field_values(field_name):
    """
    Get all existing values for a specific field from the saved Airfocus data file.
    
    This function reads the Airfocus data from a JSON file and extracts
    field values for the specified field name.
    
    Args:
        field_name (str): The name of the field to extract values for.
        
    Returns:
        set: A set of existing field values, or empty set if error occurred.
    """
    existing_values = set()
    
    # Get field ID from saved field data
    field_id = get_airfocus_field_id(field_name)
    if not field_id:
        logger.error("Could not get {} field ID. Make sure to fetch field data first.", field_name)
        return existing_values
    
    try:
        filepath = "./data/airfocus_data.json"
        
        # Check if file exists
        if not os.path.exists(filepath):
            logger.warning("Airfocus data file not found at {}. Run get_airfocus_project_data() first.", filepath)
            return existing_values
        
        # Read Airfocus data from JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            airfocus_data = json.load(f)
        
        items = airfocus_data.get("items", [])
        logger.info("Retrieved {} items from saved Airfocus data", len(items))
        
        # Extract field values from each item
        for item in items:
            fields = item.get("fields", {})
            field_data = fields.get(field_id, {})
            
            # Handle different field types
            field_value = None
            if "text" in field_data:
                field_value = field_data.get("text", "").strip()
            elif "value" in field_data:
                field_value = str(field_data.get("value", "")).strip()
            elif "displayValue" in field_data:
                field_value = field_data.get("displayValue", "").strip()
            
            if field_value:
                existing_values.add(field_value)
        
        logger.info("Found {} existing {} values in Airfocus data", len(existing_values), field_name)
        logger.debug("Existing {} values: {}", field_name, sorted(existing_values))
            
    except Exception as e:
        logger.error("Exception occurred while reading Airfocus data file: {}", e)
    
    return existing_values


def create_airfocus_item(workspace_id, issue_data):
    """
    Create an item in Airfocus based on JIRA issue data.
    
    This function sends a POST request to the Airfocus API to create a new item
    using the data extracted from JIRA issues.
    
    Args:
        workspace_id (str): The Airfocus workspace ID where the item will be created.
        issue_data (dict): Dictionary containing JIRA issue data with keys:
                          - key: JIRA issue key
                          - summary: Issue summary (maps to Airfocus name)
                          - description: Issue description
                          - status: Issue status information
                          - url: Direct link to JIRA issue
                          - assignee: Assignee information
                          - attachments: List of attachments
                          - updated: Last updated timestamp (cleaned)
        
    Returns:
        dict: Airfocus API response if successful, or error dictionary if failed.
    """
    # Construct Airfocus API endpoint URL
    url = f"{constants.AIRFOCUS_REST_URL}/workspaces/{workspace_id}/items"
    
    # Set up authentication headers for Airfocus with Markdown support
    headers = {
        "Authorization": f"Bearer {AIRFOCUS_API_KEY}",
        "Content-Type": "application/vnd.airfocus.markdown+json"
    }
    
    # Add additional metadata in description
    jira_url = issue_data.get("url", "")
    jira_key = issue_data.get("key", "")
    
    # Build enhanced description using Markdown format
    assignee = issue_data.get("assignee")
    attachments = issue_data.get("attachments", [])
    
    # Build Markdown description
    markdown_parts = []
    
    # Add JIRA Issue link
    markdown_parts.append(f"**JIRA Issue:** [**{jira_key}**]({jira_url})")
    
    # Add assignee if available
    if assignee and assignee.get("displayName"):
        assignee_text = assignee['displayName']
        if assignee.get("emailAddress"):
            assignee_text += f" ({assignee['emailAddress']})"
        markdown_parts.append(f"**JIRA Assignee:** {assignee_text}")
    
    # Add description
    jira_description = issue_data.get('description', 'No description provided in JIRA.')
    markdown_parts.append(f"**JIRA Description:**\n\n{jira_description}")
    
    # Add attachments if there are any
    if attachments:
        markdown_parts.append("**JIRA Attachments:**")
        for attachment in attachments:
            filename = attachment.get("filename", "Unknown file")
            attachment_url = attachment.get("url", "")
            markdown_parts.append(f"- [{filename}]({attachment_url})")
    
    # Join all parts with double newlines
    markdown_content = "\n\n".join(markdown_parts)
    
    # Get the field ID for JIRA-KEY field from saved field data
    jira_key_field_id = get_airfocus_field_id("JIRA-KEY")
    if not jira_key_field_id:
        logger.error("Could not get JIRA-KEY field ID. Make sure to fetch field data first.")
        return {"error": "JIRA-KEY field ID not found"}
    
    # Get the field ID for JIRA-UPDATED field from saved field data
    jira_updated_field_id = get_airfocus_field_id("JIRA-UPDATED")
    if not jira_updated_field_id:
        logger.warning("Could not get JIRA-UPDATED field ID. This field will be skipped.")
    
    # Prepare fields dictionary
    fields_dict = {
        jira_key_field_id: {
            "text": issue_data.get("key", "")
        }
    }
    
    # Add JIRA-UPDATED field if field ID was found
    if jira_updated_field_id:
        updated = issue_data.get("updated", "")
        fields_dict[jira_updated_field_id] = {
            "text": updated
        }
        logger.debug("Added JIRA updated field {}: {}", jira_updated_field_id, updated)
    
    # Get status ID from JIRA status name
    jira_status_name = issue_data.get("status", {}).get("name", "") if issue_data.get("status") else ""
    status_id = None
    
    if jira_status_name:
        # Try to map JIRA status to Airfocus status
        status_id = get_airfocus_status_id(jira_status_name)
        
        # If exact match not found, try some common mappings
        if not status_id:
            status_mapping = {
                "To Do": ["TODO", "Draft", "New", "Open"],
                "In Progress": ["In Progress", "Active", "In Development", "Working"],
                "Done": ["Done", "Closed", "Completed", "Resolved"],
                "Backlog": ["Backlog", "Draft"],
                "Selected for Development": ["Active", "In Progress"],
                "Review": ["Review", "In Progress", "Active"]
            }
            
            for airfocus_status, jira_variants in status_mapping.items():
                if jira_status_name in jira_variants:
                    status_id = get_airfocus_status_id(airfocus_status)
                    if status_id:
                        logger.info("Mapped JIRA status '{}' to Airfocus status '{}'", jira_status_name, airfocus_status)
                        break
    
    # If still no status found, get the default status
    if not status_id:
        # Try to get a default status (usually "Draft" or first available)
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
                    break
            
            # If no default found, use first available status
            if not status_id and statuses:
                status_id = statuses[0].get("id")
                logger.warning("No suitable status found for JIRA status '{}', using first available status '{}' for issue {}", 
                             jira_status_name, statuses[0].get("name"), jira_key)
                
        except Exception as e:
            logger.error("Failed to get default status: {}", e)
    
    if not status_id:
        logger.error("Could not determine status ID for JIRA issue {}. Status will be left empty.", jira_key)
        return {"error": "Could not determine status ID"}
    
    # Map JIRA fields to Airfocus fields - format description with Markdown
    airfocus_item = {
        "name": issue_data.get("summary", ""),
        "description": {
            "markdown": markdown_content,
            "richText": True
        },
        "statusId": status_id,
        "color": "blue",  # Default color
        "assigneeUserIds": [],  # Empty for now
        "assigneeUserGroupIds": [],  # Empty for now
        "order": 0,  # Default order
        "fields": fields_dict
    }
    
    logger.debug("Added JIRA key field {}: {}", jira_key_field_id, issue_data.get('key', ''))
    
    logger.debug("Creating Airfocus item for JIRA issue {}", jira_key)
    logger.debug("Payload: {}", json.dumps(airfocus_item, indent=2))
    
    try:
        response = requests.post(url, headers=headers, json=airfocus_item, verify=False)
        
        if response.status_code in [200, 201]:
            data = response.json()
            logger.info("Successfully created Airfocus item for JIRA issue {}", jira_key)
            logger.debug("Airfocus response: {}", data)
            return data
        else:
            logger.error("Failed to create Airfocus item for JIRA issue {}. Status code: {}", jira_key, response.status_code)
            logger.error("Response: {}", response.text)
            return {"error": f"Failed to create item. Status: {response.status_code}", "response": response.text}
    
    except Exception as e:
        logger.error("Exception occurred while creating Airfocus item for JIRA issue {}: {}", jira_key, e)
        return {"error": f"Exception occurred: {str(e)}"}


def patch_airfocus_item(workspace_id, item_id, issue_data):
    """
    Update an existing item in Airfocus based on updated JIRA issue data.
    
    This function sends a PATCH request to the Airfocus API to update an existing item
    using the data extracted from JIRA issues when the JIRA data is newer than the 
    existing Airfocus data.
    
    Args:
        workspace_id (str): The Airfocus workspace ID where the item exists.
        item_id (str): The Airfocus item ID to update.
        issue_data (dict): Dictionary containing JIRA issue data with keys:
                          - key: JIRA issue key
                          - summary: Issue summary (maps to Airfocus name)
                          - description: Issue description
                          - status: Issue status information
                          - url: Direct link to JIRA issue
                          - assignee: Assignee information
                          - attachments: List of attachments
                          - updated: Last updated timestamp (cleaned)
        
    Returns:
        dict: Airfocus API response if successful, or error dictionary if failed.
    """
    # Construct Airfocus API endpoint URL for PATCH
    url = f"{constants.AIRFOCUS_REST_URL}/workspaces/{workspace_id}/items/{item_id}"
    
    # Set up authentication headers for Airfocus with Markdown support
    headers = {
        "Authorization": f"Bearer {AIRFOCUS_API_KEY}",
        "Content-Type": "application/vnd.airfocus.markdown+json"
    }
    
    # Add additional metadata in description
    jira_url = issue_data.get("url", "")
    jira_key = issue_data.get("key", "")
    
    # Build enhanced description using Markdown format
    assignee = issue_data.get("assignee")
    attachments = issue_data.get("attachments", [])
    
    # Build Markdown description
    markdown_parts = []
    
    # Add JIRA Issue link
    markdown_parts.append(f"**JIRA Issue:** [**{jira_key}**]({jira_url})")
    
    # Add assignee if available
    if assignee and assignee.get("displayName"):
        assignee_text = assignee['displayName']
        if assignee.get("emailAddress"):
            assignee_text += f" ({assignee['emailAddress']})"
        markdown_parts.append(f"**JIRA Assignee:** {assignee_text}")
    
    # Add description
    jira_description = issue_data.get('description', 'No description provided in JIRA.')
    markdown_parts.append(f"**JIRA Description:**\n\n{jira_description}")
    
    # Add attachments if there are any
    if attachments:
        markdown_parts.append("**JIRA Attachments:**")
        for attachment in attachments:
            filename = attachment.get("filename", "Unknown file")
            attachment_url = attachment.get("url", "")
            markdown_parts.append(f"- [{filename}]({attachment_url})")
    
    # Join all parts with double newlines
    markdown_content = "\n\n".join(markdown_parts)
    
    # Get the field ID for JIRA-KEY field from saved field data
    jira_key_field_id = get_airfocus_field_id("JIRA-KEY")
    if not jira_key_field_id:
        logger.error("Could not get JIRA-KEY field ID. Make sure to fetch field data first.")
        return {"error": "JIRA-KEY field ID not found"}
    
    # Get the field ID for JIRA-UPDATED field from saved field data
    jira_updated_field_id = get_airfocus_field_id("JIRA-UPDATED")
    if not jira_updated_field_id:
        logger.warning("Could not get JIRA-UPDATED field ID. This field will be skipped.")
    
    # Prepare fields dictionary
    fields_dict = {
        jira_key_field_id: {
            "text": issue_data.get("key", "")
        }
    }
    
    # Add JIRA-UPDATED field if field ID was found
    if jira_updated_field_id:
        updated = issue_data.get("updated", "")
        fields_dict[jira_updated_field_id] = {
            "text": updated
        }
        logger.debug("Updated JIRA updated field {}: {}", jira_updated_field_id, updated)
    
    # Get status ID from JIRA status name
    jira_status_name = issue_data.get("status", {}).get("name", "") if issue_data.get("status") else ""
    status_id = None
    
    if jira_status_name:
        # Try to map JIRA status to Airfocus status
        status_id = get_airfocus_status_id(jira_status_name)
        
        # If exact match not found, try some common mappings
        if not status_id:
            status_mapping = {
                "To Do": ["TODO", "Draft", "New", "Open"],
                "In Progress": ["In Progress", "Active", "In Development", "Working"],
                "Done": ["Done", "Closed", "Completed", "Resolved"],
                "Backlog": ["Backlog", "Draft"],
                "Selected for Development": ["Active", "In Progress"],
                "Review": ["Review", "In Progress", "Active"]
            }
            
            for airfocus_status, jira_variants in status_mapping.items():
                if jira_status_name in jira_variants:
                    status_id = get_airfocus_status_id(airfocus_status)
                    if status_id:
                        logger.info("Mapped JIRA status '{}' to Airfocus status '{}'", jira_status_name, airfocus_status)
                        break
    
    # If still no status found, get the default status
    if not status_id:
        # Try to get a default status (usually "Draft" or first available)
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
                    break
            
            # If no default found, use first available status
            if not status_id and statuses:
                status_id = statuses[0].get("id")
                logger.warning("No suitable status found for JIRA status '{}', using first available status '{}' for issue {}", 
                             jira_status_name, statuses[0].get("name"), jira_key)
                
        except Exception as e:
            logger.error("Failed to get default status: {}", e)
    
    if not status_id:
        logger.error("Could not determine status ID for JIRA issue {}. Status will be left empty.", jira_key)
        return {"error": "Could not determine status ID"}
    
    # Map JIRA fields to Airfocus fields - format description with Markdown
    airfocus_item = {
        "name": issue_data.get("summary", ""),
        "description": {
            "markdown": markdown_content,
            "richText": True
        },
        "statusId": status_id,
        "color": "blue",  # Default color
        "assigneeUserIds": [],  # Empty for now
        "assigneeUserGroupIds": [],  # Empty for now
        "order": 0,  # Default order
        "fields": fields_dict
    }
    
    logger.debug("Updated JIRA key field {}: {}", jira_key_field_id, issue_data.get('key', ''))
    
    logger.debug("Updating Airfocus item {} for JIRA issue {}", item_id, jira_key)
    logger.debug("Payload: {}", json.dumps(airfocus_item, indent=2))
    
    try:
        response = requests.patch(url, headers=headers, json=airfocus_item, verify=False)
        
        if response.status_code in [200, 201]:
            data = response.json()
            logger.info("Successfully updated Airfocus item {} for JIRA issue {}", item_id, jira_key)
            logger.debug("Airfocus response: {}", data)
            return data
        else:
            logger.error("Failed to update Airfocus item {} for JIRA issue {}. Status code: {}", item_id, jira_key, response.status_code)
            logger.error("Response: {}", response.text)
            return {"error": f"Failed to update item. Status: {response.status_code}", "response": response.text}
    
    except Exception as e:
        logger.error("Exception occurred while updating Airfocus item {} for JIRA issue {}: {}", item_id, jira_key, e)
        return {"error": f"Exception occurred: {str(e)}"}


def sync_jira_to_airfocus(jira_data_file, workspace_id):
    """
    Synchronize JIRA issues to Airfocus by creating items.
    
    This function reads the JIRA data from a JSON file and creates corresponding
    items in the specified Airfocus workspace.
    
    Args:
        jira_data_file (str): Path to the JSON file containing JIRA issue data.
        workspace_id (str): The Airfocus workspace ID where items will be created.
        
    Returns:
        dict: Summary of the synchronization process including success and failure counts.
    """
    try:
        # Read JIRA data from JSON file
        with open(jira_data_file, 'r', encoding='utf-8') as f:
            jira_data = json.load(f)
        
        issues = jira_data.get("issues", [])
        total_issues = len(issues)
        
        logger.info("Starting synchronization of {} JIRA issues to Airfocus workspace {}", total_issues, workspace_id)
        
        # Get existing JIRA keys from saved Airfocus data to avoid duplicates
        existing_jira_keys = get_airfocus_field_values("JIRA-KEY")
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        errors = []
        
        for issue in issues:
            jira_key = issue.get("key", "Unknown")
            
            try:
                # Check if JIRA issue status is "Done" or similar completed statuses
                jira_status = issue.get("status", {}).get("name", "") if issue.get("status") else ""
                completed_statuses = ["Done", "Closed", "Completed", "Resolved", "Finished", "Fixed"]
                
                if jira_status in completed_statuses:
                    skipped_count += 1
                    logger.info("JIRA issue {} has status '{}' (completed) - skipping creation in Airfocus", jira_key, jira_status)
                    continue
                
                # Check if JIRA key already exists in Airfocus
                if jira_key in existing_jira_keys:
                    skipped_count += 1
                    logger.info("JIRA issue {} already exists in Airfocus - skipping", jira_key)
                    continue
                
                # Create new item since it doesn't exist and is not completed
                result = create_airfocus_item(workspace_id, issue)
                
                if "error" in result:
                    error_count += 1
                    errors.append({"jira_key": jira_key, "error": result["error"]})
                    logger.warning("Failed to sync JIRA issue {}: {}", jira_key, result['error'])
                else:
                    success_count += 1
                    logger.info("Successfully synced JIRA issue {}", jira_key)
                    # Add the newly created key to our existing set to avoid duplicates in this batch
                    existing_jira_keys.add(jira_key)
                
            except Exception as e:
                error_count += 1
                error_msg = f"Exception during sync: {str(e)}"
                errors.append({"jira_key": jira_key, "error": error_msg})
                logger.error("Exception while syncing JIRA issue {}: {}", jira_key, e)
        
        # Log summary
        logger.info("Synchronization completed. Success: {}, Errors: {}, Skipped: {}", success_count, error_count, skipped_count)
        
        return {
            "total_issues": total_issues,
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "errors": errors
        }
        
    except Exception as e:
        logger.error("Failed to read JIRA data file {}: {}", jira_data_file, e)
        return {"error": f"Failed to read data file: {str(e)}"}


def cleanup_old_json_files(pattern, keep_count=10):
    """
    Remove old JSON files matching a pattern, keeping only the most recent ones.
    
    Args:
        pattern (str): File pattern to match (e.g., "jira_*_issues_*.json")
        keep_count (int): Number of most recent files to keep (default: 10)
    """
    try:
        # Get all files matching the pattern in the data directory
        file_pattern = f"./data/{pattern}"
        files = glob.glob(file_pattern)
        
        if len(files) <= keep_count:
            logger.debug("Found {} files matching '{}', no cleanup needed (keeping {})", len(files), pattern, keep_count)
            return
        
        # Sort files by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)
        
        # Keep only the most recent files
        files_to_keep = files[:keep_count]
        files_to_delete = files[keep_count:]
        
        logger.info("Cleaning up old files for pattern '{}': keeping {}, deleting {}", pattern, len(files_to_keep), len(files_to_delete))
        
        # Delete old files
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                logger.debug("Deleted old file: {}", file_path)
            except Exception as e:
                logger.warning("Failed to delete file {}: {}", file_path, e)
                
    except Exception as e:
        logger.error("Exception occurred during cleanup for pattern '{}': {}", pattern, e)


def main():
    """
    Main entry point for the JIRA to Airfocus integration script.
    
    Initializes the application by logging configuration details and
    starting the data synchronization process.
    """
    # Log configuration information for debugging
    logger.info("JIRA REST URL: {}", constants.JIRA_REST_URL)
    logger.info("Airfocus REST URL: {}", constants.AIRFOCUS_REST_URL)
    
    # Get Jira project data and save to file
    logger.info("Fetching JIRA project data...")
    get_jira_project_data(constants.JIRA_PROJECT_KEY)

    # Get Airfocus project data and save to file
    logger.info("Fetching Airfocus project data...")
    get_airfocus_project_data(constants.AIRFOCUS_WORKSPACE_ID)
    
    # Get Airfocus field data and save to file
    logger.info("Fetching Airfocus field data...")
    get_airfocus_field_data(constants.AIRFOCUS_WORKSPACE_ID)

    # Create items in Airfocus
    sync_jira_to_airfocus("./data/jira_data.json", constants.AIRFOCUS_WORKSPACE_ID)

    # Clean up old JSON files, keeping only the 10 most recent
    logger.info("Cleaning up old JSON files...")
    cleanup_old_json_files("jira_*_issues_*.json", keep_count=10)
    cleanup_old_json_files("airfocus_*_items_*.json", keep_count=10)

if __name__ == "__main__":
    main()
