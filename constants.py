# JIRA Configuration
# Update this URL to match your JIRA instance
# Format: https://your-jira-instance.com/rest/api/latest
# Documentation: https://developer.atlassian.com/server/jira/platform/rest/v11001/intro/#gettingstarted
JIRA_REST_URL = "https://jira.brichet.be

# Airfocus Configuration  
# This URL typically stays the same for all Airfocus instances
# Documentation: https://developer.airfocus.com/endpoints.html#/Items
AIRFOCUS_REST_URL = "https://app.airfocus.com/api"

# JIRA Project Configuration
# The project key of the JIRA project you want to sync
# Example: "PROJ", "DEV", "SUPPORT", etc.
JIRA_PROJECT_KEY = "JIRA"

# Airfocus Workspace Configuration
# Your Airfocus workspace ID (found in the workspace URL)
# Example: https://app.airfocus.com/workspaces/YOUR-WORKSPACE-ID/items
AIRFOCUS_WORKSPACE_ID = "b22eade1-b00b-4015-8a19-6f4db6a8db32"

# Logging Configuration
# Available levels: DEBUG, INFO, WARNING, ERROR
# DEBUG - Detailed information for troubleshooting
# INFO - General information about script execution (recommended)
# WARNING - Only warning and error messages
# ERROR - Only error messages
LOGGING_LEVEL = "INFO"