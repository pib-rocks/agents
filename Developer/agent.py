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
    get_jira_transitions,
    transition_jira_issue,
    create_jira_subtask, # Add sub-task tool
    get_jira_subtasks,   # Add sub-task tool
    delete_jira_issue,   # Add sub-task tool
)

# Get model name from environment variable, with a default fallback
# Note: This line was added in a previous step (commit abb4a04) but wasn't in the provided file content.
# Assuming it should be here based on previous steps.
from dotenv import load_dotenv
load_dotenv()
gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")

# --- Load Agent Instruction ---
instruction_file_path = os.path.join(os.path.dirname(__file__), "agent_instruction.txt")
try:
    with open(instruction_file_path, "r", encoding="utf-8") as f:
        agent_instruction = f.read()
        # Replace curly braces with angle brackets in the loaded instruction string
        agent_instruction = agent_instruction.replace("{", "<")
        agent_instruction = agent_instruction.replace("}", ">")
except FileNotFoundError:
    print(f"Error: Instruction file not found at {instruction_file_path}")
    # Provide a fallback instruction if the file is missing
    agent_instruction = "You are a helpful Jira assistant."
except Exception as e:
    print(f"Error reading instruction file: {e}")
    agent_instruction = "You are a helpful Jira assistant."


root_agent = Agent(
    name="jira_agent",
    model=gemini_model_name, # Use model from env var
    description=(
        "AI assistant for Developers using Jira. Helps with understanding assigned tasks, "
        "retrieving issue details, updating status via transitions, adding technical comments, "
        "updating assignees, opening issues in browser, and searching the web for technical context or solutions."
    ),
    instruction=agent_instruction, # Load instruction from file
    tools=[
        get_jira_issue_details,
        update_jira_issue,
        add_jira_comment,
        get_jira_comments,
        show_jira_issue,
        get_jira_transitions,
        transition_jira_issue,
        create_jira_subtask,
        get_jira_subtasks,
        delete_jira_issue,
        perform_google_search, # Use the custom Google Search function
    ],
)
