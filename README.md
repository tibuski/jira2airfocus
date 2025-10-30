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

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Configuration**
   
   Copy `constants.py.example` to `constants.py` and update:
   ```python
   # JIRA Configuration
   JIRA_REST_URL = "https://your-jira-instance.com/rest/api/latest"
   JIRA_PROJECT_KEY = "YOUR_PROJECT_KEY"
   JIRA_PAT = "your_jira_token_here"
   
   # Airfocus Configuration
   AIRFOCUS_WORKSPACE_ID = "your-workspace-id-here"
   AIRFOCUS_API_KEY = "your_airfocus_api_key_here"
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

**Required Custom Field in Airfocus:**
- Create a **Text** field named "JIRA-KEY" in your Airfocus workspace settings
- This prevents duplicate items during sync

## Usage

Run the synchronization:
```bash
python main.py
```

The script will:
- Fetch JIRA Epic issues from your project
- Create/update corresponding items in Airfocus
- Always sync latest JIRA data (JIRA is the source of truth)
