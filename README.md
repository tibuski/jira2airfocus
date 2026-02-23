# JIRA to Airfocus Integration

A Python script that synchronizes JIRA issues with Airfocus workspace items.

## Features

- Fetch JIRA Epic issues and sync to Airfocus workspace
- Update existing items with current JIRA data
- Duplicate detection and prevention
- Automatic team assignment
- Status mapping between JIRA and Airfocus
- Attachment linking and rich Markdown formatting

## Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/tibuski/jira2airfocus
   cd jira2airfocus
   ```

2. **Install Dependencies with uv**
   ```bash
   uv sync
   ```

3. **Configure the Application**
    
    Copy `constants.py.example` to `constants.py` and update with your credentials:
   ```python
   # JIRA Configuration
   JIRA_REST_URL = "https://your-jira-instance.com/rest/api/latest"
   JIRA_PROJECT_KEY = "YOUR_PROJECT_KEY"  # Your JIRA project key
   
   # Airfocus Configuration  
   AIRFOCUS_WORKSPACE_ID = "your-workspace-id-here"  # From Airfocus URL
   ```
   
   **Optional Configuration:**
   ```python
   # Status Mapping (maps JIRA statuses to Airfocus statuses)
   JIRA_TO_AIRFOCUS_STATUS_MAPPING = {
       "Draft": ["To Do", "Open"],
       "In Progress": ["In Progress", "IN REFINEMENT"],
       "Done": ["Done", "Cancelled"],
       "On Hold": ["On hold"]
   }
   
   # Team Assignment (automatically assign team to items)
   TEAM_FIELD = {"YOUR_TEAM_FIELD_NAME": ["YOUR_TEAM_VALUE"]}
   ```

## Getting API Credentials

**JIRA Personal Access Token:**
1. Go to JIRA → Account Settings → Security → API tokens
2. Create API token and copy it

**Airfocus API Key:**
1. Go to Airfocus → Settings → API Keys
2. Generate new API key and copy it

**Airfocus Workspace ID:**
- Find it in your Airfocus workspace URL: `https://app.airfocus.com/workspaces/YOUR-WORKSPACE-ID/...`

## Setup Requirements

No custom fields required in Airfocus. The JIRA key is stored in the item description with a sync warning header.

## Usage

Run the synchronization:
```bash
python main.py
```

The script will:
- Fetch JIRA Epic issues from your project
- Create/update corresponding items in Airfocus
- Always sync latest JIRA data (JIRA is the source of truth)
