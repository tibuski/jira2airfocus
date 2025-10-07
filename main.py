import dotenv
import os
import constants


# Import API keys and PAT from .ENV file using dotenv
dotenv.load_dotenv()
JIRA_PAT = os.getenv("JIRA_PAT")
AIRFOCUS_API_KEY = os.getenv("AIRFOCUS_API_KEY")

