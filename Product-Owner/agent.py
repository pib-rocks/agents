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
    create_jira_issue,
    get_jira_issue_details,
    update_jira_issue,
    add_jira_comment,
    get_jira_comments,
    show_jira_issue,
    get_jira_transitions,
    transition_jira_issue,
    search_jira_issues_by_time, # Added time search tool
)
from tools.vector_storage.requirements import ( # Import vector DB tools
    # Requirement Functions
    add_requirement,
    retrieve_similar_requirements,
    update_requirement,
    delete_requirement,
    get_all_requirements,
    generate_jira_issues_for_requirement,
)

from tools.vector_storage.acceptance_criteria import ( # Import vector DB tools
    # Acceptance Criteria Functions
    add_acceptance_criterion,
    retrieve_similar_acceptance_criteria,
    update_acceptance_criterion,
    delete_acceptance_criterion,
    get_all_acceptance_criteria,
)

from tools.vector_storage.test_cases import (
    # Test Case Functions
    add_test_case,
    retrieve_similar_test_cases,
    update_test_case,
    delete_test_case,
    get_all_test_cases
)
from tools.neo4j_requirements_tool import ( # Import Neo4j tools
    add_or_update_requirement_neo4j,
    add_relationship_neo4j
)
# Importiere die Funktionen zum Laden von Werkzeugbeschreibungen und Agenten-Tools
from tools.tool_description_manager import (
    get_tool_description,
    update_tool_description_in_db,
    get_tools_for_agent # Neue Funktion
)
import importlib # Für dynamische Importe, falls benötigt, aber wir mappen direkt


# Definiere den Agentennamen
AGENT_NAME = "Product-Owner"

# Globale Map aller verfügbaren Werkzeugfunktionen für diesen Agenten-Typ
# Dies hilft, von String-Namen (aus der DB) auf tatsächliche Python-Funktionen zu mappen.
AVAILABLE_TOOLS_MAP = {
    # Jira Tools
    "create_jira_issue": create_jira_issue,
    "get_jira_issue_details": get_jira_issue_details,
    "update_jira_issue": update_jira_issue,
    "add_jira_comment": add_jira_comment,
    "get_jira_comments": get_jira_comments,
    "show_jira_issue": show_jira_issue,
    "get_jira_transitions": get_jira_transitions,
    "transition_jira_issue": transition_jira_issue,
    "search_jira_issues_by_time": search_jira_issues_by_time,
    # Vector DB - Requirements
    "add_requirement": add_requirement,
    "retrieve_similar_requirements": retrieve_similar_requirements,
    "update_requirement": update_requirement,
    "delete_requirement": delete_requirement,
    "get_all_requirements": get_all_requirements,
    "generate_jira_issues_for_requirement": generate_jira_issues_for_requirement,
    # Vector DB - Acceptance Criteria
    "add_acceptance_criterion": add_acceptance_criterion,
    "retrieve_similar_acceptance_criteria": retrieve_similar_acceptance_criteria,
    "update_acceptance_criterion": update_acceptance_criterion,
    "delete_acceptance_criterion": delete_acceptance_criterion,
    "get_all_acceptance_criteria": get_all_acceptance_criteria,
    # Vector DB - Test Cases
    "add_test_case": add_test_case,
    "retrieve_similar_test_cases": retrieve_similar_test_cases,
    "update_test_case": update_test_case,
    "delete_test_case": delete_test_case,
    "get_all_test_cases": get_all_test_cases,
    # Neo4j Tools
    "add_or_update_requirement_neo4j": add_or_update_requirement_neo4j,
    "add_relationship_neo4j": add_relationship_neo4j,
    # Meta-Tools (Werkzeugbeschreibungen verwalten)
    "get_tool_description": get_tool_description,
    "update_tool_description_in_db": update_tool_description_in_db,
    # Google Search (obwohl nicht in der initialen Liste für PO, hier für Vollständigkeit, falls später hinzugefügt)
    "perform_google_search": perform_google_search
}

def load_configured_tools_for_agent(agent_name: str) -> list:
    """Lädt die konfigurierten Werkzeuge für den Agenten aus der Datenbank."""
    configured_tools_data = get_tools_for_agent(agent_name)
    agent_tools_list = []
    for tool_info in configured_tools_data:
        tool_name = tool_info["tool_name"]
        tool_func = AVAILABLE_TOOLS_MAP.get(tool_name)
        if tool_func:
            # Die __doc__ wird dynamisch von der ADK über die Funktion selbst gelesen.
            # Wir stellen sicher, dass die Beschreibung in der DB aktuell ist
            # und die ADK diese über get_tool_description (falls als Tool übergeben)
            # oder direkt aus der Funktion (falls __doc__ modifiziert wurde) holt.
            # Der Lambda-Ansatz stellt sicher, dass __doc__ zur Laufzeit für die ADK korrekt ist.
            description = get_tool_description(tool_name) or getattr(tool_func, '__doc__', 'No description available.')
            # Erzeuge eine neue Funktion (Lambda), die die __doc__ setzt und die Originalfunktion zurückgibt.
            # Dies ist der empfohlene Weg, um die __doc__ für die ADK zur Laufzeit zu setzen, ohne die Originalfunktion global zu ändern.
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
        "AI assistant acting as a Product Owner helper. Manages Jira backlog items: "
        "retrieves details, updates fields (summary, description, assignee), "
        "handles comments, manages status via transitions, interactively refines "
        "descriptions to meet standards, opens issues in browser, uses web search for context, "
        "and manages requirements in a vector database."
    ),
    instruction=agent_instruction, # Load instruction from file
    tools=load_configured_tools_for_agent(AGENT_NAME),
)
