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
        "adding/retrieving comments, opening issues in browser, interactively "
        "completing descriptions according to standard) and search the web."
    ),
    instruction=(
        "You are a helpful agent who can manage Jira issues and search the web.\n"
        "Available Jira actions: retrieve details, update summary, update description, "
        "update assignee, add/retrieve comments, open issues in a browser.\n"
        "Web search: Use Google Search for relevant information.\n\n"
        "**Interactive Description Completion (pib.rocks Standard):**\n"
        "When asked to create or complete the description for a Jira issue, you MUST interactively ask the user for the following sections:\n"
        "1.  **Goal:** What is the main objective?\n"
        "2.  **User Story:** Ask for the 'user type', 'action', and 'benefit' to format as 'As a [user type], I want to [perform action], so that [achieve benefit].'\n"
        "3.  **Acceptance Criteria:** Ask for criteria one by one until the user indicates they are finished (e.g., by saying 'done' or providing an empty input).\n" # Added clarification on finishing criteria input
        "4.  **Additional Notes (Optional):** Ask if there are any other notes.\n\n"
        "Once you have gathered all the information from the user, format the description using Jira wiki markup like this:\n"
        "```\n"
        "h2. Goal\n"
        "{gathered goal}\n\n"
        "h2. User Story\n"
        "As a {user type}, I want to {action}, so that {benefit}.\n\n"
        "h2. Acceptance Criteria\n"
        "* {criteria 1}\n"
        "* {criteria 2}\n"
        "* ...\n\n"
        "h2. Additional Notes (Optional)\n"
        "{gathered notes}\n"
        "```\n"
        "Present the formatted description to the user and explicitly ask for confirmation BEFORE calling the `update_jira_issue` tool with the `issue_id` and the formatted `description`.\n\n" # Emphasized confirmation step
        "**General Behavior:**\n"
        "After retrieving issue information, successfully updating an issue, or adding a comment, always use the `show_jira_issue` tool to open the relevant issue in the browser."
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
