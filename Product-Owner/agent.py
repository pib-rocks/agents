import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
# Import tools from the tools directory

# Ensure the tools directory is in the Python path
import sys
import os
# Add the parent directory ('..') to sys.path to find the 'tools' module
# This might not be strictly necessary if the project is structured as a package,
# but it ensures the tools module can be found when running agent.py directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.google_search_tool import perform_google_search # Import custom Google Search function
from tools.jira_tools import (
    get_jira_issue_details,
    update_jira_issue,
    add_jira_comment,
    get_jira_comments,
    show_jira_issue,
)

# Get model name from environment variable, with a default fallback
# Note: This line was added in a previous step (commit abb4a04) but wasn't in the provided file content.
# Assuming it should be here based on previous steps.
from dotenv import load_dotenv
load_dotenv()
gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

root_agent = Agent(
    name="jira_agent",
    model=gemini_model_name, # Use model from env var
    description=(
        "Agent to manage Jira issues (retrieving details, updating fields, "
        "adding/retrieving comments, opening issues in browser) and search the web."
    ),
    instruction=(
        "You are a helpful agent who can manage Jira issues (retrieve details, "
        "update summary/description/assignee, add/retrieve comments, open issues "
        "in a browser) and search the internet using Google Search for relevant "
        "information when needed to complete tasks or answer questions." \
        "After retrieving issue-information, updating an issue or" \
        "adding a comment, always show the issue in the browser."
    ),
    tools=[
        get_jira_issue_details,
        update_jira_issue,
        add_jira_comment,
        get_jira_comments,
        show_jira_issue,
        perform_google_search, # Use the custom Google Search function
    ],
)
