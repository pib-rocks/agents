import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
# Import the Jira tools from the tools directory

import sys
sys.path.append("..")
from tools.jira_tools import get_jira_issue_details, update_jira_issue

root_agent = Agent(
    name="jira_agent", # Renamed for clarity
    model="gemini-2.0-flash-live-001",
    description=(
        "Agent to manage Jira issues (retrieving and updating)."
    ),
    instruction=(
        "You are a helpful agent who can retrieve details for Jira issues and"
        " update their summary, description, or assignee (using account ID)."
    ),
    tools=[
        get_jira_issue_details,
        update_jira_issue,
    ],
)
