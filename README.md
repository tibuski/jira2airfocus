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
    ```bash
    cp constants.py.example constants.py
    ```
    
    Then edit `constants.py` and fill in the required values:
    - `JIRA_REST_URL` - Your JIRA instance URL
    - `JIRA_PROJECT_KEY` - Your JIRA project key
    - `AIRFOCUS_WORKSPACE_ID` - From Airfocus URL
    - `JIRA_PAT` - Your JIRA API token
    - `AIRFOCUS_API_KEY` - Your Airfocus API key

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

## Configuration Options

All configuration is done in `constants.py`. Here are the available options:

| Variable | Description | Default |
|----------|-------------|---------|
| `JIRA_REST_URL` | JIRA API endpoint | Required |
| `AIRFOCUS_REST_URL` | Airfocus API endpoint | `https://app.airfocus.com/api` |
| `JIRA_PROJECT_KEY` | JIRA project key to sync | Required |
| `AIRFOCUS_WORKSPACE_ID` | Airfocus workspace ID | Required |
| `JIRA_PAT` | JIRA Personal Access Token | Required |
| `AIRFOCUS_API_KEY` | Airfocus API Key | Required |
| `LOGGING_LEVEL` | Log verbosity (DEBUG, INFO, WARNING, ERROR) | `WARNING` |
| `LOG_FILE_PATH` | Path to log file | `data/jira2airfocus.log` |
| `SSL_VERIFY` | Enable SSL certificate verification | `False` |
| `DATA_DIR` | Directory for data files | `data` |
| `JIRA_TO_AIRFOCUS_STATUS_MAPPING` | Map JIRA statuses to Airfocus | Optional |
| `TEAM_FIELD` | Auto-assign team to items | Optional |

## Usage

Run the synchronization:
```bash
uv run main.py
```

The script will:
- Fetch JIRA Epic issues from your project
- Create/update corresponding items in Airfocus
- Always sync latest JIRA data (JIRA is the source of truth)
