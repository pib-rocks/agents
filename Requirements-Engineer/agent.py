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
from tools.os_tools import get_current_time
from tools.jira_tools import (
    get_jira_issue_details,
    # update_jira_issue,
    # add_jira_comment,
    get_jira_comments,
    show_jira_issue,
    get_jira_transitions,
    get_jira_issue_links,
    # transition_jira_issue,
    search_jira_issues_by_time, # Added time search tool
    get_jira_subtasks,
)

from tools.confluence_tools import (
    # Reading:
    get_confluence_page,
    get_confluence_child_pages,
    show_confluence_page,

    # Writing:
    create_confluence_page,
    update_confluence_page,
    delete_confluence_page,


)

from tools.vector_storage.requirements import ( # Import vector DB tools
    # Requirement Functions
    add_requirement,
    retrieve_similar_requirements,
    update_requirement, 
    delete_requirement,
    get_all_requirements,
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
# Importiere die Funktion zum Laden von Werkzeugbeschreibungen
from tools.tool_description_manager import (get_tool_description, update_tool_description_in_db)


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
        "AI assistant acting as a Requirements Engineer helper. Analyzes Jira backlog items: "
        "retrieves details, "
        "handles comments, "
        "summarizes descriptions, opens issues in browser, uses web search for context, "
        "and manages requirements in a vector database."
    ),
    instruction=agent_instruction, # Load instruction from file
    tools=(lambda: [
        # OS Tools
        get_current_time,#
        # Google Search
        perform_google_search,
        # Jira Tools
        get_jira_issue_details,
        # update_jira_issue,
        # add_jira_comment,
        get_jira_comments,
        show_jira_issue,
        get_jira_transitions,
        get_jira_issue_links,
        # transition_jira_issue,
        # Time Search Tool
        search_jira_issues_by_time,
        get_jira_subtasks,
        # Confluence tools
        get_confluence_page,
        get_confluence_child_pages,
        show_confluence_page,
        create_confluence_page,
        update_confluence_page,
        delete_confluence_page,
        # Vector DB Tools - Lade Beschreibungen dynamisch
        (lambda f: setattr(f, '__doc__', get_tool_description(f.__name__) or f.__doc__) or f)(add_requirement),
        (lambda f: setattr(f, '__doc__', get_tool_description(f.__name__) or f.__doc__) or f)(retrieve_similar_requirements),
        (lambda f: setattr(f, '__doc__', get_tool_description(f.__name__) or f.__doc__) or f)(update_requirement),
        (lambda f: setattr(f, '__doc__', get_tool_description(f.__name__) or f.__doc__) or f)(delete_requirement),
        (lambda f: setattr(f, '__doc__', get_tool_description(f.__name__) or f.__doc__) or f)(get_all_requirements),
        # Acceptance Criteria Functions (nicht Teil der Anforderungs-Tools, daher keine Änderung der Beschreibung)
        # add_acceptance_criterion,
        # retrieve_similar_acceptance_criteria,
        # delete_acceptance_criterion,
        # update_acceptance_criterion,
        # get_all_acceptance_criteria,
        # Test Case Functions (nicht Teil der Anforderungs-Tools, daher keine Änderung der Beschreibung)
        # add_test_case,
        # retrieve_similar_test_cases,
        # update_test_case,
        # delete_test_case,
        # get_all_test_cases,
        # Neo4j Tools - Lade Beschreibungen dynamisch
        (lambda f: setattr(f, '__doc__', get_tool_description(f.__name__) or f.__doc__) or f)(add_or_update_requirement_neo4j),
        (lambda f: setattr(f, '__doc__', get_tool_description(f.__name__) or f.__doc__) or f)(add_relationship_neo4j),
        # Working with tools
        get_tool_description,
        update_tool_description_in_db,
    ])(),
)
