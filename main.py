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
from typing import Dict, List, Tuple, Optional, Any

from loguru import logger

import constants
from models import (
    AirfocusItem,
    JiraItem,
    get_airfocus_field_id,
    get_airfocus_status_id,
    get_mapped_status_id,
)

# Conditionally disable SSL warnings when certificate verification is disabled
if not constants.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure loguru logging with both file and console output
logger.remove()  # Remove default handler
# File Logging
logger.add(
    constants.LOG_FILE_PATH,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
    rotation="10 MB",
    retention="30 days",
)
# Console Logging
logger.add(sys.stderr, level=constants.LOGGING_LEVEL, colorize=True)

# Authentication credentials from constants
JIRA_PAT = constants.JIRA_PAT
AIRFOCUS_API_KEY = constants.AIRFOCUS_API_KEY

# Do NOT log secrets. Log only presence to avoid leaking credentials.
if JIRA_PAT and constants.JIRA_PAT != "your-jira-personal-access-token-here":
    logger.debug("JIRA_PAT is set.")
else:
    logger.warning("JIRA_PAT is not set.")

if AIRFOCUS_API_KEY and constants.AIRFOCUS_API_KEY != "your-airfocus-api-key-here":
    logger.debug("AIRFOCUS_API_KEY is set.")
else:
    logger.warning("AIRFOCUS_API_KEY is not set.")


# Helper Functions


def validate_api_response(
    response: requests.Response,
    operation_name: str,
    expected_status_codes: Optional[List[int]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate API response and return standardized result.

    Args:
        response: requests.Response object
        operation_name (str): Name of the operation for logging
        expected_status_codes (list): List of acceptable status codes

    Returns:
        tuple: (success: bool, data: dict or error_dict)
    """
    # Avoid mutable default argument
    if expected_status_codes is None:
        expected_status_codes = [200]

    if response.status_code in expected_status_codes:
        try:
            data = response.json()
            logger.debug("{} successful. Response: {}", operation_name, data)
            return True, data
        except Exception as e:
            error_msg = f"Failed to parse JSON response for {operation_name}: {str(e)}"
            logger.error(error_msg)
            return False, {"error": error_msg}
    else:
        error_msg = f"{operation_name} failed. Status code: {response.status_code}"
        logger.error(error_msg)
        logger.error("Response: {}", response.text)
        return False, {"error": error_msg, "response": response.text}


def get_field_mappings() -> Optional[str]:
    """
    Get JIRA field ID mappings from saved field data.

    Returns:
        str: jira_key_field_id or None if JIRA-KEY not found
    """
    jira_key_field_id = get_airfocus_field_id("JIRA-KEY")

    if not jira_key_field_id:
        logger.error(
            "Could not get JIRA-KEY field ID. Make sure to fetch field data first."
        )
        return None

    return jira_key_field_id


def get_jira_project_data(project_key: str) -> Dict[str, Any]:
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
        "Content-Type": "application/json",
    }

    while True:
        # Define JQL query to fetch specific fields for the project
        # Note: "key" field is included by default and contains the issue key (e.g., PROJ-123)
        # Fetch only Epic issues for the project
        query = {
            "jql": f"project = {project_key} AND issuetype = Epic",
            "fields": [
                "key",
                "summary",
                "description",
                "status",
                "assignee",
                "attachment",
                "updated",
            ],
            "expand": ["names"],
            "startAt": start_at,
            "maxResults": max_results,
        }
        logger.info("Requesting data from endpoint: {}", url)
        logger.info("Using JQL query: {}", query["jql"])
        logger.info("Requesting issues {} to {}", start_at, start_at + max_results - 1)

        try:
            response = requests.post(
                url,
                headers=headers,
                json=query,
                verify=constants.SSL_VERIFY,
                timeout=30,
            )
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

            # Create JiraItem from the raw API data
            jira_item = JiraItem.from_jira_api_data(issue, project_key, base_url)

            # Validate the item
            validation_errors = jira_item.validate()
            if validation_errors:
                logger.warning(
                    "Validation issues for JIRA issue {}: {}",
                    issue_key,
                    ", ".join(validation_errors),
                )

            logger.debug("Processed issue: {}", jira_item.url)

            # Store JiraItem objects directly for streamlined data flow
            all_issues.append(jira_item.to_dict())

        # Get total count from first response
        if total_issues is None:
            total_issues = data.get("total", 0)
            logger.info(
                "Found {} total issues for project {}", total_issues, project_key
            )

        logger.info(
            "Fetched {} issues (batch {})", len(raw_issues), start_at // max_results + 1
        )

        # Check if we've fetched all issues
        if len(raw_issues) < max_results or len(all_issues) >= total_issues:
            break

        # Prepare for next batch
        start_at += max_results

    # Save data to JSON file in ./data directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jira_{project_key}_issues_{timestamp}.json"
    filepath = f"{constants.DATA_DIR}/{filename}"

    try:
        # Create data directory if it doesn't exist
        os.makedirs(constants.DATA_DIR, exist_ok=True)

        # Prepare final data structure
        final_data = {
            "project_key": project_key,
            "total_issues": len(all_issues),
            "fetched_at": datetime.now().isoformat(),
            "issues": all_issues,
        }

        # Save to timestamped JSON file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)

        # Also save to a standard filename for easy access by sync function
        standard_filepath = f"{constants.DATA_DIR}/jira_data.json"
        with open(standard_filepath, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)

        logger.info("Successfully saved {} issues to {}", len(all_issues), filepath)
        logger.info("Also saved to standard file: {}", standard_filepath)

        # Clean up old JIRA data files, keeping only the 10 most recent
        cleanup_old_json_files(f"jira_{project_key}_issues_*.json", keep_count=10)

    except Exception as e:
        logger.error("Failed to save data to file: {}", e)
        return {"error": f"Failed to save data: {e}"}

    logger.info(
        "Successfully fetched {} total issues for project {}",
        len(all_issues),
        project_key,
    )
    return final_data


def get_airfocus_field_data(workspace_id: str) -> Optional[Dict[str, Any]]:
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
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, verify=constants.SSL_VERIFY)

        success, data = validate_api_response(
            response, f"Get workspace data for {workspace_id}"
        )
        if not success:
            return None

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
            "status_mapping": {},
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

        # Get field ID for JIRA-KEY
        jira_key_field_id = field_data["field_mapping"].get("JIRA-KEY")

        # Fetch workspace items to get field values using field names as keys
        field_values = {}

        # Create a reverse mapping from field ID to field name for easier lookup
        id_to_name_mapping = {}
        for field_name, field_id in field_data["field_mapping"].items():
            id_to_name_mapping[field_id] = field_name

        if jira_key_field_id:
            try:
                # Fetch items from workspace
                items_url = f"{constants.AIRFOCUS_REST_URL}/workspaces/{workspace_id}/items/search"
                search_payload = {
                    "filters": {},
                    "pagination": {"limit": 1000, "offset": 0},
                }

                items_response = requests.post(
                    items_url,
                    headers=headers,
                    json=search_payload,
                    verify=constants.SSL_VERIFY,
                )

                if items_response.status_code == 200:
                    items_data = items_response.json()
                    items = items_data.get("items", [])

                    # Extract field values from each item, using field names as keys
                    for item in items:
                        item_fields = item.get("fields", {})

                        # Process all fields that we have mappings for
                        for field_id, field_data_obj in item_fields.items():
                            field_name = id_to_name_mapping.get(field_id)

                            # Only process fields we recognize and have names for
                            if field_name:
                                # Initialize field values list if not exists
                                if field_name not in field_values:
                                    field_values[field_name] = []

                                # Extract field value (handle different field types)
                                field_value = ""
                                if "text" in field_data_obj:
                                    field_value = field_data_obj.get("text", "")
                                elif "value" in field_data_obj:
                                    field_value = str(field_data_obj.get("value", ""))
                                elif "displayValue" in field_data_obj:
                                    field_value = field_data_obj.get("displayValue", "")

                                # Add unique values only
                                if (
                                    field_value
                                    and field_value not in field_values[field_name]
                                ):
                                    field_values[field_name].append(field_value)

                    # Log extracted values for JIRA fields specifically
                    jira_key_count = len(field_values.get("JIRA-KEY", []))
                    total_fields = len(field_values)

                    logger.info(
                        "Extracted field values for {} fields from workspace items",
                        total_fields,
                    )
                    logger.info("JIRA-KEY: {} values", jira_key_count)

                else:
                    logger.warning(
                        "Failed to fetch workspace items for field values. Status code: {}",
                        items_response.status_code,
                    )

            except Exception as e:
                logger.warning(
                    "Failed to fetch workspace items for field values: {}", e
                )

        # Add field values to field_data
        field_data["field_values"] = field_values

        # Save to JSON file
        try:
            os.makedirs(constants.DATA_DIR, exist_ok=True)
            filepath = f"{constants.DATA_DIR}/airfocus_fields.json"

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(field_data, f, indent=2, ensure_ascii=False)

            logger.info(
                "Successfully saved {} field definitions, {} statuses, and field values to {}",
                len(fields),
                len(statuses),
                filepath,
            )
            logger.debug(
                "Available fields: {}", list(field_data["field_mapping"].keys())
            )
            logger.debug(
                "Available statuses: {}", list(field_data["status_mapping"].keys())
            )
            logger.debug(
                "Field values extracted: {}", list(field_data["field_values"].keys())
            )

            # Log specific JIRA field values if they exist
            if "JIRA-KEY" in field_data["field_values"]:
                logger.debug(
                    "JIRA-KEY values: {}", field_data["field_values"]["JIRA-KEY"]
                )

            return field_data

        except Exception as e:
            logger.error("Failed to save field data to file: {}", e)
            return None

    except Exception as e:
        logger.error(
            "Exception occurred while retrieving workspace data for {}: {}",
            workspace_id,
            e,
        )
        return None


def get_airfocus_project_data(workspace_id: str) -> Dict[str, Any]:
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
        "Content-Type": "application/json",
    }

    # Use the items/search endpoint with POST request
    url = f"{constants.AIRFOCUS_REST_URL}/workspaces/{workspace_id}/items/search"

    # Search payload to get all items (empty search criteria)
    search_payload = {"filters": {}, "pagination": {"limit": 1000, "offset": 0}}

    logger.info("Requesting data from endpoint: {}", url)
    logger.debug("Search payload: {}", json.dumps(search_payload, indent=2))
    response = requests.post(
        url, headers=headers, json=search_payload, verify=constants.SSL_VERIFY
    )

    success, data = validate_api_response(
        response, f"Fetch items from workspace {workspace_id}"
    )
    if not success:
        return data  # Return error dict

    try:
        # Extract items from the response
        raw_items = data.get("items", [])

        # Get field mapping for better readability
        jira_key_field_id = get_airfocus_field_id("JIRA-KEY")

        # Extract only the needed fields from each item
        for item in raw_items:
            # Get basic item data
            item_id = item.get("id", "")
            item_name = item.get("name", "")

            # Extract status information
            status_id = item.get("statusId", "")

            # Extract custom fields and transform them for better readability
            raw_fields = item.get("fields", {})
            transformed_fields = {}

            # Process each field and make JIRA fields more readable
            for field_id, field_data in raw_fields.items():
                if field_id == jira_key_field_id:
                    # Transform JIRA-KEY field
                    transformed_fields["JIRA-KEY"] = {
                        "id": field_id,
                        "value": field_data.get("text", ""),
                    }
                else:
                    # Keep other fields as they are
                    transformed_fields[field_id] = field_data

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
                "fields": transformed_fields,
            }

            logger.debug("Processed Airfocus item: {} (ID: {})", item_name, item_id)
            all_items.append(simplified_item)

        logger.info(
            "Found {} total items in Airfocus workspace {}",
            len(all_items),
            workspace_id,
        )

        # Save data to JSON file in ./data directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"airfocus_{workspace_id}_items_{timestamp}.json"
        filepath = f"{constants.DATA_DIR}/{filename}"

        try:
            # Create data directory if it doesn't exist
            os.makedirs(constants.DATA_DIR, exist_ok=True)

            # Prepare final data structure
            final_data = {
                "workspace_id": workspace_id,
                "total_items": len(all_items),
                "fetched_at": datetime.now().isoformat(),
                "items": all_items,
            }

            # Save to timestamped JSON file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            # Also save to a standard filename for easy access by sync function
            standard_filepath = f"{constants.DATA_DIR}/airfocus_data.json"
            with open(standard_filepath, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            logger.info("Successfully saved {} items to {}", len(all_items), filepath)
            logger.info("Also saved to standard file: {}", standard_filepath)

            # Clean up old Airfocus data files, keeping only the 10 most recent
            cleanup_old_json_files(
                f"airfocus_{workspace_id}_items_*.json", keep_count=10
            )

        except Exception as e:
            logger.error("Failed to save data to file: {}", e)
            return {"error": f"Failed to save data: {e}"}

        logger.info(
            "Successfully fetched {} total items from Airfocus workspace {}",
            len(all_items),
            workspace_id,
        )
        return final_data

    except Exception as e:
        logger.error("Exception occurred while fetching Airfocus data: {}", e)
        return {"error": f"Exception occurred: {str(e)}"}


def create_airfocus_item(workspace_id: str, jira_item: JiraItem) -> Dict[str, Any]:
    """
    Create an item in Airfocus based on JIRA issue data.

    This function sends a POST request to the Airfocus API to create a new item
    using the data from a JiraItem object.

    Args:
        workspace_id (str): The Airfocus workspace ID where the item will be created.
        jira_item (JiraItem): JiraItem instance containing JIRA issue data

    Returns:
        dict: Airfocus API response if successful, or error dictionary if failed.
    """
    # Create AirfocusItem from JIRA data
    item = AirfocusItem.from_jira_item(jira_item)
    jira_key = item.jira_key

    # Validate item data before API call
    validation_errors = item.validate()
    if validation_errors:
        error_msg = f"Validation failed: {', '.join(validation_errors)}"
        logger.error("Validation failed for JIRA issue {}: {}", jira_key, error_msg)
        return {"error": error_msg}

    # Generate payload using the item
    payload = item.to_create_payload()

    # Construct Airfocus API endpoint URL
    url = f"{constants.AIRFOCUS_REST_URL}/workspaces/{workspace_id}/items"

    # Set up authentication headers for Airfocus with Markdown support
    headers = {
        "Authorization": f"Bearer {AIRFOCUS_API_KEY}",
        "Content-Type": "application/vnd.airfocus.markdown+json",
    }

    logger.debug("Creating Airfocus item for JIRA issue {}", jira_key)
    logger.debug("Payload: {}", json.dumps(payload, indent=2))

    try:
        response = requests.post(
            url, headers=headers, json=payload, verify=constants.SSL_VERIFY
        )

        success, result = validate_api_response(
            response, f"Create Airfocus item for JIRA issue {jira_key}", [200, 201]
        )
        if success:
            team_info = (
                f" with team field '{item.team_field_value}'"
                if item.team_field_value
                else ""
            )
            logger.info(
                "Successfully created Airfocus item for JIRA issue {}{}",
                jira_key,
                team_info,
            )
            return result
        else:
            team_info = (
                f" (attempted to set team field '{item.team_field_value}')"
                if item.team_field_value
                else ""
            )
            logger.error(
                "Failed to create Airfocus item for JIRA issue {}{}: {}",
                jira_key,
                team_info,
                result.get("error", "Unknown error"),
            )
            return result

    except Exception as e:
        team_info = (
            f" (attempted to set team field '{item.team_field_value}')"
            if item.team_field_value
            else ""
        )
        logger.error(
            "Exception occurred while creating Airfocus item for JIRA issue {}{}: {}",
            jira_key,
            team_info,
            e,
        )
        return {"error": f"Exception occurred: {str(e)}"}


def patch_airfocus_item(
    workspace_id: str, item_id: str, jira_item: JiraItem
) -> Dict[str, Any]:
    """
    Update an existing item in Airfocus based on updated JIRA issue data.

    This function sends a PATCH request to the Airfocus API to update an existing item
    using the data from a JiraItem object.

    Args:
        workspace_id (str): The Airfocus workspace ID where the item exists.
        item_id (str): The Airfocus item ID to update.
        jira_item (JiraItem): JiraItem instance containing JIRA issue data

    Returns:
        dict: Airfocus API response if successful, or error dictionary if failed.
    """
    # Create AirfocusItem from JIRA data
    item = AirfocusItem.from_jira_item(jira_item)
    jira_key = item.jira_key

    # Validate item data before API call
    validation_errors = item.validate()
    if validation_errors:
        error_msg = f"Validation failed: {', '.join(validation_errors)}"
        logger.error(
            "Validation failed for JIRA issue {} update: {}", jira_key, error_msg
        )
        return {"error": error_msg}

    # Generate patch operations using the item
    patch_operations = item.to_patch_payload()

    # Construct Airfocus API endpoint URL for PATCH
    url = f"{constants.AIRFOCUS_REST_URL}/workspaces/{workspace_id}/items/{item_id}"

    # Set up authentication headers for Airfocus with Markdown support
    headers = {
        "Authorization": f"Bearer {AIRFOCUS_API_KEY}",
        "Content-Type": "application/vnd.airfocus.markdown+json",
    }

    logger.debug(
        "Updating Airfocus item {} for JIRA issue {} with {} patch operations",
        item_id,
        jira_key,
        len(patch_operations),
    )
    logger.debug("Patch operations: {}", json.dumps(patch_operations, indent=2))

    try:
        response = requests.patch(
            url, headers=headers, json=patch_operations, verify=constants.SSL_VERIFY
        )

        success, result = validate_api_response(
            response,
            f"Update Airfocus item {item_id} for JIRA issue {jira_key}",
            [200, 201],
        )
        if success:
            team_info = (
                f" with team field '{item.team_field_value}'"
                if item.team_field_value
                else ""
            )
            logger.info(
                "Successfully updated Airfocus item {} for JIRA issue {}{}",
                item_id,
                jira_key,
                team_info,
            )
            return result
        else:
            team_info = (
                f" (attempted to set team field '{item.team_field_value}')"
                if item.team_field_value
                else ""
            )
            logger.error(
                "Failed to update Airfocus item {} for JIRA issue {}{}: {}",
                item_id,
                jira_key,
                team_info,
                result.get("error", "Unknown error"),
            )
            return result

    except Exception as e:
        team_info = (
            f" (attempted to set team field '{item.team_field_value}')"
            if item.team_field_value
            else ""
        )
        logger.error(
            "Exception occurred while updating Airfocus item {} for JIRA issue {}{}: {}",
            item_id,
            jira_key,
            team_info,
            e,
        )
        return {"error": f"Exception occurred: {str(e)}"}


def get_airfocus_field_option_id(field_name: str, option_name: str) -> Optional[str]:
    """
    Get a specific option ID from a select field in the saved Airfocus fields data.

    Args:
        field_name (str): The name of the field to search in.
        option_name (str): The name of the option to retrieve the ID for.

    Returns:
        str: The option ID for the specified option, or None if not found.
    """
    try:
        filepath = f"{constants.DATA_DIR}/airfocus_fields.json"

        # Check if file exists
        if not os.path.exists(filepath):
            logger.warning(
                "Airfocus fields file not found at {}. Run get_airfocus_field_data() first.",
                filepath,
            )
            return None

        # Read the field data
        with open(filepath, "r", encoding="utf-8") as f:
            field_data = json.load(f)

        # Find the field by name
        fields = field_data.get("fields", [])
        for field in fields:
            if field.get("name") == field_name:
                # Check if it's a select field with options
                if field.get("typeId") == "select":
                    options = field.get("settings", {}).get("options", [])
                    for option in options:
                        if option.get("name") == option_name:
                            option_id = option.get("id")
                            logger.debug(
                                "Found option '{}' in field '{}' with ID: {}",
                                option_name,
                                field_name,
                                option_id,
                            )
                            return option_id

                    logger.warning(
                        "Option '{}' not found in select field '{}'",
                        option_name,
                        field_name,
                    )
                    logger.debug(
                        "Available options in '{}': {}",
                        field_name,
                        [opt.get("name") for opt in options],
                    )
                    return None
                else:
                    logger.error(
                        "Field '{}' is not a select field (type: {})",
                        field_name,
                        field.get("typeId"),
                    )
                    return None

        logger.warning("Field '{}' not found in saved field data", field_name)
        return None

    except Exception as e:
        logger.error("Exception occurred while reading field option data: {}", e)
        return None


def _load_and_prepare_sync_data(
    jira_data_file: str, workspace_id: str
) -> Tuple[List[JiraItem], Dict[str, Any], Dict[str, Any]]:
    """
    Helper function to load and prepare data for synchronization.

    Args:
        jira_data_file (str): Path to the JSON file containing JIRA issue data.
        workspace_id (str): The Airfocus workspace ID where items will be created/updated.

    Returns:
        tuple: (jira_items, airfocus_by_jira_key, sync_stats)
    """
    # Read JIRA data from JSON file
    with open(jira_data_file, "r", encoding="utf-8") as f:
        jira_data = json.load(f)

    # Read Airfocus data from JSON file
    airfocus_data_file = f"{constants.DATA_DIR}/airfocus_data.json"
    airfocus_data = {}
    if os.path.exists(airfocus_data_file):
        with open(airfocus_data_file, "r", encoding="utf-8") as f:
            airfocus_data = json.load(f)
    else:
        logger.warning(
            "Airfocus data file not found at {}. All items will be treated as new.",
            airfocus_data_file,
        )

    # Convert all issues to JiraItem objects with validation
    raw_issues = jira_data.get("issues", [])
    jira_items = []
    validation_failures = 0

    for issue_dict in raw_issues:
        try:
            jira_item = JiraItem.from_simplified_data(issue_dict)
            validation_errors = jira_item.validate()

            if validation_errors:
                logger.warning(
                    "Skipping JIRA issue {} due to validation errors: {}",
                    jira_item.key,
                    ", ".join(validation_errors),
                )
                validation_failures += 1
                continue

            jira_items.append(jira_item)

        except Exception as e:
            logger.error(
                "Failed to create JiraItem from issue data {}: {}",
                issue_dict.get("key", "Unknown"),
                e,
            )
            validation_failures += 1
            continue

    logger.info(
        "Successfully converted {} JIRA issues to JiraItem objects ({} validation failures)",
        len(jira_items),
        validation_failures,
    )

    # Build Airfocus lookup mapping
    airfocus_items = airfocus_data.get("items", [])
    airfocus_by_jira_key = {}

    for item_data in airfocus_items:
        fields = item_data.get("fields", {})
        jira_key_field = fields.get("JIRA-KEY", {})
        if jira_key_field and "value" in jira_key_field:
            jira_key = jira_key_field["value"]
            if jira_key:
                airfocus_item = AirfocusItem.from_airfocus_data(item_data)
                airfocus_by_jira_key[jira_key] = airfocus_item

    logger.info(
        "Starting synchronization of {} JIRA issues to Airfocus workspace {}",
        len(jira_items),
        workspace_id,
    )
    logger.info("Found {} existing Airfocus items for comparison", len(airfocus_items))
    logger.debug(
        "Built lookup mapping for {} Airfocus items with JIRA keys",
        len(airfocus_by_jira_key),
    )

    sync_stats = {
        "total_raw_issues": len(raw_issues),
        "validation_failures": validation_failures,
        "processed_issues": len(jira_items),
    }

    return jira_items, airfocus_by_jira_key, sync_stats


def _perform_sync_operations(
    workspace_id: str, jira_items: List[JiraItem], airfocus_by_jira_key: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Helper function to perform the actual sync operations.

    Args:
        workspace_id (str): The Airfocus workspace ID.
        jira_items (list): List of JiraItem objects.
        airfocus_by_jira_key (dict): Mapping of JIRA keys to Airfocus items.

    Returns:
        dict: Results of sync operations.
    """
    success_count = 0
    error_count = 0
    updated_count = 0
    created_count = 0
    errors = []

    for jira_item in jira_items:
        jira_key = jira_item.key

        try:
            # Check if item exists in Airfocus
            existing_item = airfocus_by_jira_key.get(jira_key)

            if existing_item:
                # Item exists - update it with JIRA data
                item_id = existing_item.item_id

                logger.info(
                    "JIRA issue {} - updating existing Airfocus item {}",
                    jira_key,
                    item_id,
                )

                # Update existing item directly with JiraItem
                result = patch_airfocus_item(workspace_id, item_id, jira_item)

                if "error" in result:
                    error_count += 1
                    errors.append(
                        {
                            "jira_key": jira_key,
                            "action": "update",
                            "error": result["error"],
                        }
                    )
                    logger.error(
                        "Failed to update JIRA issue {}: {}", jira_key, result["error"]
                    )
                else:
                    success_count += 1
                    updated_count += 1
                    logger.info(
                        "Successfully updated Airfocus item for JIRA issue {}", jira_key
                    )
            else:
                # Item doesn't exist - create new one
                logger.info(
                    "JIRA issue {} not found in Airfocus - creating new item", jira_key
                )

                # Create new item directly with JiraItem
                result = create_airfocus_item(workspace_id, jira_item)

                if "error" in result:
                    error_count += 1
                    errors.append(
                        {
                            "jira_key": jira_key,
                            "action": "create",
                            "error": result["error"],
                        }
                    )
                    logger.warning(
                        "Failed to create JIRA issue {}: {}", jira_key, result["error"]
                    )
                else:
                    success_count += 1
                    created_count += 1
                    logger.info(
                        "Successfully created Airfocus item for JIRA issue {}", jira_key
                    )

        except Exception as e:
            error_count += 1
            error_msg = f"Exception during sync: {str(e)}"
            errors.append(
                {"jira_key": jira_key, "action": "unknown", "error": error_msg}
            )
            logger.error("Exception while syncing JIRA issue {}: {}", jira_key, e)

    return {
        "success_count": success_count,
        "error_count": error_count,
        "created_count": created_count,
        "updated_count": updated_count,
        "errors": errors,
    }


def sync_jira_to_airfocus(jira_data_file: str, workspace_id: str) -> Dict[str, Any]:
    """
    Synchronize JIRA issues to Airfocus by creating new items and updating existing ones.

    This function reads the JIRA data from a JSON file and creates corresponding
    items in the specified Airfocus workspace. For existing items, it always updates
    them with the current JIRA data, overwriting any changes in Airfocus.

    Args:
        jira_data_file (str): Path to the JSON file containing JIRA issue data.
        workspace_id (str): The Airfocus workspace ID where items will be created/updated.

    Returns:
        dict: Summary of the synchronization process including success and failure counts.
    """
    try:
        # Load and prepare data using helper function
        jira_items, airfocus_by_jira_key, sync_stats = _load_and_prepare_sync_data(
            jira_data_file, workspace_id
        )

        # Perform sync operations
        results = _perform_sync_operations(
            workspace_id, jira_items, airfocus_by_jira_key
        )

        # Log summary
        logger.info(
            "Synchronization completed. Success: {}, Errors: {} (Created: {}, Updated: {}, Validation failures: {})",
            results["success_count"],
            results["error_count"],
            results["created_count"],
            results["updated_count"],
            sync_stats["validation_failures"],
        )

        return {
            "total_issues": sync_stats["total_raw_issues"],
            "processed_issues": sync_stats["processed_issues"],
            "validation_failures": sync_stats["validation_failures"],
            "success_count": results["success_count"],
            "error_count": results["error_count"],
            "created_count": results["created_count"],
            "updated_count": results["updated_count"],
            "errors": results["errors"],
        }

    except Exception as e:
        logger.error("Failed to read JIRA data file {}: {}", jira_data_file, e)
        return {"error": f"Failed to read data file: {str(e)}"}


def cleanup_old_json_files(pattern: str, keep_count: int = 10) -> None:
    """
    Remove old JSON files matching a pattern, keeping only the most recent ones.

    Args:
        pattern (str): File pattern to match (e.g., "jira_*_issues_*.json")
        keep_count (int): Number of most recent files to keep (default: 10)
    """
    try:
        # Get all files matching the pattern in the data directory
        file_pattern = f"{constants.DATA_DIR}/{pattern}"
        files = glob.glob(file_pattern)

        if len(files) <= keep_count:
            logger.debug(
                "Found {} files matching '{}', no cleanup needed (keeping {})",
                len(files),
                pattern,
                keep_count,
            )
            return

        # Sort files by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)

        # Keep only the most recent files
        files_to_keep = files[:keep_count]
        files_to_delete = files[keep_count:]

        logger.info(
            "Cleaning up old files for pattern '{}': keeping {}, deleting {}",
            pattern,
            len(files_to_keep),
            len(files_to_delete),
        )

        # Delete old files
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                logger.debug("Deleted old file: {}", file_path)
            except Exception as e:
                logger.warning("Failed to delete file {}: {}", file_path, e)

    except Exception as e:
        logger.error(
            "Exception occurred during cleanup for pattern '{}': {}", pattern, e
        )


def main() -> None:
    """
    Main entry point for the JIRA to Airfocus integration script.

    Initializes the application by logging configuration details and
    starting the data synchronization process.
    """
    # Log configuration information for debugging
    logger.info("JIRA REST URL: {}", constants.JIRA_REST_URL)
    logger.info("Airfocus REST URL: {}", constants.AIRFOCUS_REST_URL)

    # Get Airfocus field data and save to file
    logger.info("Fetching Airfocus field data...")
    get_airfocus_field_data(constants.AIRFOCUS_WORKSPACE_ID)

    # Get Jira project data and save to file
    logger.info("Fetching JIRA project data...")
    get_jira_project_data(constants.JIRA_PROJECT_KEY)

    # Get Airfocus project data and save to file
    logger.info("Fetching Airfocus project data...")
    get_airfocus_project_data(constants.AIRFOCUS_WORKSPACE_ID)

    # Create items in Airfocus
    sync_jira_to_airfocus(
        f"{constants.DATA_DIR}/jira_data.json", constants.AIRFOCUS_WORKSPACE_ID
    )

    # Clean up old JSON files, keeping only the 10 most recent
    logger.info("Cleaning up old JSON files...")
    cleanup_old_json_files("jira_*_issues_*.json", keep_count=10)
    cleanup_old_json_files("airfocus_*_items_*.json", keep_count=10)


if __name__ == "__main__":
    main()
