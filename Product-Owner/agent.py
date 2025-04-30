import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
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
    model="gemini-2.0-flash-live-001",
    description=(
        "Agent to manage Jira issues (retrieving details, updating fields, "
        "adding comments, and retrieving comments)."
    ),
    instruction=(
        "You are a helpful agent who can retrieve details for Jira issues,"
        " update their summary, description, or assignee (using account ID),"
        " add comments, and retrieve existing comments."
    ),
    tools=[
        get_jira_issue_details,
        update_jira_issue,
        add_jira_comment,
        get_jira_comments,
    ],
)
