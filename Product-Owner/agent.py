import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.tools import google_search # Import Google Search tool
# Import the Jira tools from the tools directory

# Ensure the tools directory is in the Python path
import sys
import os
# Add the parent directory ('..') to sys.path to find the 'tools' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.jira_tools import (
    get_jira_issue_details,
    update_jira_issue,
    add_jira_comment,
    get_jira_comments,
)

root_agent = Agent(
    name="jira_agent",
    model="gemini-2.5-pro-preview-03-25", # Changed model to support tool use
    description=(
        "Agent to manage Jira issues (retrieving details, updating fields, "
        "adding comments, retrieving comments) and search the web for information."
    ),
    instruction=(
        "You are a helpful agent who can manage Jira issues (retrieve details, "
        "update summary/description/assignee, add/retrieve comments) and "
        "search the internet using Google Search for relevant information "
        "when needed to complete tasks or answer questions."
    ),
    tools=[
        get_jira_issue_details,
        update_jira_issue,
        add_jira_comment,
        get_jira_comments,
        google_search, # Add Google Search tool
    ],
)
