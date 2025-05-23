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
from tools.confluence_tools import ( # Importiere Confluence Werkzeuge
    get_confluence_page,
    show_confluence_page
)
from tools.aider_tools import add_agent_feature # Import the new aider tool
# Importiere die Funktionen zum Laden von Werkzeugbeschreibungen und Agenten-Tools
from tools.tool_description_manager import (
    get_tool_description,
    # update_tool_description_in_db, # Developer agent might not need this
    get_tools_for_agent # Neue Funktion
)
import importlib # Für dynamische Importe, falls benötigt, aber wir mappen direkt


# Definiere den Agentennamen
AGENT_NAME = "Developer"

# Globale Map aller verfügbaren Werkzeugfunktionen für diesen Agenten-Typ
AVAILABLE_TOOLS_MAP = {
    # Jira Tools
    "get_jira_issue_details": get_jira_issue_details,
    "update_jira_issue": update_jira_issue,
    "add_jira_comment": add_jira_comment,
    "get_jira_comments": get_jira_comments,
    "show_jira_issue": show_jira_issue,
    "get_jira_transitions": get_jira_transitions,
    "transition_jira_issue": transition_jira_issue,
    "create_jira_subtask": create_jira_subtask,
    "get_jira_subtasks": get_jira_subtasks,
    "delete_jira_issue": delete_jira_issue,
    # Google Search
    "perform_google_search": perform_google_search,
    # Confluence Tools
    "get_confluence_page": get_confluence_page,
    "show_confluence_page": show_confluence_page,
    # Aider Tool
    "add_agent_feature": add_agent_feature,
}

def load_configured_tools_for_agent(agent_name: str) -> list:
    """Lädt die konfigurierten Werkzeuge für den Agenten aus der Datenbank."""
    configured_tools_data = get_tools_for_agent(agent_name)
    agent_tools_list = []
    for tool_info in configured_tools_data:
        tool_name = tool_info["tool_name"]
        tool_func = AVAILABLE_TOOLS_MAP.get(tool_name)
        if tool_func:
            description = get_tool_description(tool_name) or getattr(tool_func, '__doc__', 'No description available.')
            wrapped_tool = (lambda f, d: setattr(f, '__doc__', d) or f)(tool_func, description)
            agent_tools_list.append(wrapped_tool)
        else:
            print(f"Warnung: Werkzeug '{tool_name}' für Agent '{agent_name}' in DB konfiguriert, aber nicht in AVAILABLE_TOOLS_MAP gefunden.")
    return agent_tools_list

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
    tools=load_configured_tools_for_agent(AGENT_NAME),
)
