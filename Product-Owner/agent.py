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
from tools.google_search_tool import perform_google_search
from tools.jira_tools import (
    get_jira_issue_details,
    update_jira_issue,
    add_jira_comment,
    get_jira_comments,
    show_jira_issue,
    get_jira_transitions,
    transition_jira_issue,
)
from tools.vector_database import ( # Import vector DB tools
    add_requirement,
    retrieve_similar_requirements,
    delete_requirement,
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
        "AI assistant acting as a Product Owner helper. Manages Jira backlog items: "
        "retrieves details, updates fields (summary, description, assignee), "
        "handles comments, manages status via transitions, interactively refines "
        "descriptions to meet standards, opens issues in browser, uses web search for context, "
        "and manages requirements in a vector database."
    ),
    instruction=agent_instruction, # Load instruction from file
    tools=[
        # Jira Tools
        get_jira_issue_details,
        update_jira_issue,
        add_jira_comment,
        get_jira_comments,
        show_jira_issue,
        get_jira_transitions,
        transition_jira_issue,
        # Vector DB Tools
        add_requirement,
        retrieve_similar_requirements,
        delete_requirement,
        # Other Tools
        perform_google_search,
    ],
)
