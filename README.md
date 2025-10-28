# JIRA to Airfocus Integration

A Python script that synchronizes JIRA issues with Airfocus workspace items. This tool fetches issues from a JIRA project and creates corresponding items in an Airfocus workspace, avoiding duplicates and maintaining data consistency.

## Features

- ✅ Fetch all JIRA Epic issues from specified project
- ✅ Create corresponding items in Airfocus workspace
- ✅ **Always sync**: Update all existing Airfocus items with current JIRA data
- ✅ Duplicate detection using JIRA-KEY custom field
- ✅ Rich Markdown formatting for issue descriptions
- ✅ Attachment linking from JIRA to Airfocus
- ✅ Status mapping between JIRA and Airfocus statuses
- ✅ Comprehensive logging with colored console output
- ✅ Automatic cleanup of old data files
- ✅ SSL certificate validation bypass for corporate environments

## Prerequisites

- Python 3.7 or higher
- JIRA Personal Access Token (PAT)
- Airfocus API Key
- Access to both JIRA and Airfocus instances

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd jira2airfocus
```

### 2. Create and Activate Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell)
venv\Scripts\Activate.ps1

# On Windows (Command Prompt)
venv\Scripts\activate.bat

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Create Environment Configuration

Create a `.env` file in the project root directory with your API credentials:

```bash
# Copy the example and edit with your values
cp .env.example .env
```

Edit the `.env` file with your actual credentials:

```env
# JIRA Configuration
JIRA_PAT=your_jira_personal_access_token_here

# Airfocus Configuration  
AIRFOCUS_API_KEY=your_airfocus_api_key_here
```

### 5. Configure Constants

Edit `constants.py` to match your environment:

```python
# JIRA REST API URL - Update with your JIRA instance URL
JIRA_REST_URL = "https://your-jira-instance.com/rest/api/latest"

# Airfocus REST API URL (usually stays the same)
AIRFOCUS_REST_URL = "https://app.airfocus.com/api"

# JIRA project key to sync
JIRA_PROJECT_KEY = "YOUR_PROJECT_KEY"

# Airfocus Workspace ID (found in Airfocus URL)
AIRFOCUS_WORKSPACE_ID = "your-workspace-id-here"

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOGGING_LEVEL = "INFO"

# Status Mapping Configuration
# Maps JIRA statuses to Airfocus statuses when exact matches aren't found
JIRA_TO_AIRFOCUS_STATUS_MAPPING = {
    "To Do": ["To Do"],
    "In Progress": ["In Progress"],
    "Done": ["Done"],
    "On Hold": ["On hold"]
}
```

## Getting Your API Credentials

### JIRA Personal Access Token (PAT)

1. Log in to your JIRA instance
2. Go to **Account Settings** → **Security** → **Create and manage API tokens**
3. Click **Create API token**
4. Give it a descriptive name (e.g., "Airfocus Integration")
5. Copy the generated token and paste it in your `.env` file

### Airfocus API Key

1. Log in to [Airfocus](https://app.airfocus.com)
2. Go to **Settings** → **API Keys**
3. Click **Generate new API key**
4. Give it a descriptive name
5. Copy the generated key and paste it in your `.env` file

### Finding Your Airfocus Workspace ID

1. Navigate to your Airfocus workspace
2. Look at the URL: `https://app.airfocus.com/workspaces/YOUR-WORKSPACE-ID/...`
3. Copy the workspace ID from the URL

## Usage

### Basic Synchronization

Run the complete synchronization process:

```bash
python main.py
```

This will:
1. Fetch all Epic issues from the configured JIRA project
2. Fetch existing items from the Airfocus workspace
3. Get Airfocus field definitions
4. **Synchronize all data:**
   - Create new items in Airfocus for JIRA issues that don't already exist
   - Always update existing Airfocus items with current JIRA data (no date comparison)
   - Ensure all Airfocus items reflect the latest JIRA information
5. Clean up old data files

### Sync Behavior

The script performs complete synchronization between JIRA and Airfocus:

**For New Issues:**
- Creates new items in Airfocus with all JIRA data
- Sets JIRA-KEY field to the JIRA issue key for duplicate prevention

**For Existing Issues:**
- Always updates with current JIRA data (name, description, status, custom fields)
- Overwrites any manual changes made in Airfocus
- Ensures consistency with JIRA as the single source of truth

### Data Files

The script creates several data files in the `./data/` directory:

- `jira_data.json` - Latest JIRA issues data
- `airfocus_data.json` - Latest Airfocus items data
- `airfocus_fields.json` - Airfocus field definitions
- Timestamped backup files (automatically cleaned up)

## Configuration Options

### Logging Levels

Set the `LOGGING_LEVEL` in `constants.py`:

- `DEBUG` - Detailed information for debugging
- `INFO` - General information (default)
- `WARNING` - Warning messages only
- `ERROR` - Error messages only

### Status Mapping Configuration

The script includes a flexible status mapping system that allows you to map JIRA statuses to Airfocus statuses when exact matches aren't found. This is configured in the `JIRA_TO_AIRFOCUS_STATUS_MAPPING` dictionary in `constants.py`.

**How it works:**
- Key: Airfocus status name (must exist in your Airfocus workspace)
- Value: List of JIRA status names that should map to this Airfocus status

**To customize the mapping:**
1. Check your Airfocus workspace for available status names
2. Check your JIRA project for status names
3. Update the mappings in `constants.py` as needed

**Example configuration:**
```python
JIRA_TO_AIRFOCUS_STATUS_MAPPING = {
    "To Do": ["To Do", "Open", "New", "Backlog"],
    "In Progress": ["In Progress", "In Development", "Active"],
    "Done": ["Done", "Closed", "Resolved", "Fixed"],
    "On Hold": ["On hold", "Blocked", "Waiting"]
}
```

**Important notes:**
- Status names are **case sensitive**
- Make sure the Airfocus status names (keys) exist in your workspace
- If no mapping is found, the script will attempt to use the JIRA status as-is

### Custom Field Requirements

The script requires one custom field in your Airfocus workspace:

#### JIRA-KEY Field (Required)
This field stores JIRA issue keys and prevents duplicate items:

1. Go to your Airfocus workspace settings
2. Navigate to **Custom Fields**
3. Create a new **Text** field named "JIRA-KEY"

**Note:** This field is essential for the script to identify existing items and avoid creating duplicates.

## Troubleshooting

### Common Issues

**SSL Certificate Errors:**
- The script disables SSL verification for corporate environments
- If you need to enable SSL verification, remove `verify=False` from all `requests` calls

**Authentication Errors:**
- Verify your JIRA PAT and Airfocus API key are correct
- Check that your JIRA user has permission to access the project
- Ensure your Airfocus API key has workspace access

**JIRA-KEY Field Not Found:**
- Create the custom field in Airfocus workspace settings
- Run the script again to fetch updated field definitions

**Items Always Being Updated:**
- This is the expected behavior - the script always syncs all JIRA data to Airfocus
- JIRA is treated as the single source of truth

**400 Bad Request Errors:**
- Check that your custom fields exist and have the correct names
- Verify that status mappings in constants.py match your Airfocus workspace statuses

### Log Files

Check `jira2airfocus.log` for detailed execution logs. The log file rotates at 10MB and keeps 30 days of history.

## Project Structure

```
jira2airfocus/
├── main.py              # Main application script
├── constants.py         # Configuration constants
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
├── .env.example        # Environment variables template
├── README.md           # This file
├── LICENSE             # Project license
├── jira2airfocus.log   # Application log file
└── data/              # Data directory (auto-created)
    ├── jira_data.json
    ├── airfocus_data.json
    └── airfocus_fields.json
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

See the [LICENSE](LICENSE) file for license information.
