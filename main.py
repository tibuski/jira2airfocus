"""
JIRA to Airfocus Integration Script

This module provides functionality to fetch data from JIRA projects and sync them with Airfocus.
It handles authentication, data retrieval, and logging for the integration process.
"""

import dotenv
import os
import requests
import json
import logging
from datetime import datetime
import urllib3

import constants

# Disable SSL warnings when certificate verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging with both file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jira2airfocus.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
dotenv.load_dotenv()

# Authentication credentials from environment variables
JIRA_PAT = os.getenv("JIRA_PAT")
AIRFOCUS_API_KEY = os.getenv("AIRFOCUS_API_KEY")

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
            "fields": ["key", "summary", "description", "status", "assignee", "attachment"],
            "startAt": start_at,
            "maxResults": max_results
        }

        logger.debug(f"Requesting issues {start_at} to {start_at + max_results - 1}")
        response = requests.post(url, headers=headers, json=query, verify=False)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch data for Jira project {project_key}. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
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
                "attachments": attachment_list
            }
            
            all_issues.append(simplified_issue)
        
        # Get total count from first response
        if total_issues is None:
            total_issues = data.get("total", 0)
            logger.info(f"Found {total_issues} total issues for project {project_key}")

        logger.info(f"Fetched {len(raw_issues)} issues (batch {start_at//max_results + 1})")
        
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
        
        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved {len(all_issues)} issues to {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save data to file: {e}")
        return {"error": f"Failed to save data: {e}"}

    logger.info(f"Successfully fetched {len(all_issues)} total issues for project {project_key}")
    return final_data


def main():
    """
    Main entry point for the JIRA to Airfocus integration script.
    
    Initializes the application by logging configuration details and
    starting the data synchronization process.
    """
    # Log configuration information for debugging
    logger.info(f"JIRA REST URL: {constants.JIRA_REST_URL}")
    logger.info(f"Airfocus REST URL: {constants.AIRFOCUS_REST_URL}")
    
    # Start data fetching process
    get_jira_project_data(constants.JIRA_PROJECT_KEY)

if __name__ == "__main__":
    main()
    