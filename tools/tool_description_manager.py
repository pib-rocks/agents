import sqlite3
import os
from typing import Dict, Optional, List

# Path to the database file in the same directory as this script
DB_PATH = os.path.join(os.path.dirname(__file__), 'tool_descriptions.db')
TABLE_NAME = 'tool_descriptions'

def _get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Allows access to columns by name
    return conn

def create_table_if_not_exists():
    """Creates the table for tool descriptions if it does not already exist."""
    conn = _get_db_connection()
    try:
        with conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    tool_name TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    source_module TEXT
                )
            """)
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_tool_name ON {TABLE_NAME} (tool_name);")

            # Create agent_tools table
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS agent_tools (
                    agent_name TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    PRIMARY KEY (agent_name, tool_name),
                    FOREIGN KEY (tool_name) REFERENCES {TABLE_NAME}(tool_name)
                )
            """)
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_agent_name ON agent_tools (agent_name);")
        print(f"Tables '{TABLE_NAME}' and 'agent_tools' successfully initialized/verified in '{DB_PATH}'.")
    except sqlite3.Error as e:
        print(f"Error creating/verifying tables: {e}")
    finally:
        conn.close()

def _get_initial_tool_descriptions() -> Dict[str, Dict[str, str]]:
    """
    Provides the initial descriptions for the requirement tools.
    These are used to populate the database for the first time.
    The descriptions here should be concise and informative for the LLM agent.
    """
    return {
        # Aus tools.vector_storage.requirements
        "add_requirement": {
            "description": "Adds a new software requirement to the vector database with an automatically generated ID. Manages requirement text and metadata, including 'source_jira_ticket', 'implementation_status' (Open, In Progress, Done, etc.), and 'classification' (Functional, Non-Functional, Business).",
            "source_module": "tools.vector_storage.requirements"
        },
        "retrieve_similar_requirements": {
            "description": "Retrieves requirements from the vector database that are semantically similar to a given query text. Supports filtering by metadata (e.g., 'source_jira_ticket', 'implementation_status') and specifying the number of results.",
            "source_module": "tools.vector_storage.requirements"
        },
        "update_requirement": {
            "description": "Updates the text and/or metadata of an existing requirement in the vector database, identified by its ID. New metadata (JSON format) replaces existing metadata. 'implementation_status' and 'classification' can be updated.",
            "source_module": "tools.vector_storage.requirements"
        },
        "delete_requirement": {
            "description": "Deletes one or more requirements from the vector database based on a list of their unique IDs.",
            "source_module": "tools.vector_storage.requirements"
        },
        "get_all_requirements": {
            "description": "Retrieves all requirements currently stored in the vector database, including their IDs, text, and all associated metadata.",
            "source_module": "tools.vector_storage.requirements"
        },
        # Aus tools.neo4j_requirements_tool
        "add_or_update_requirement_neo4j": {
            "description": "Adds a new requirement node to a Neo4j graph database or updates an existing one, identified by 'req_id'. Manages requirement text and a flexible set of properties (JSON format), automatically adding a 'change_date'.",
            "source_module": "tools.neo4j_requirements_tool"
        },
        "add_relationship_neo4j": {
            "description": "Adds a directed relationship (e.g., RELATES_TO, DEPENDS_ON, DUPLICATES) between two existing requirement nodes in the Neo4j graph database, identified by their 'req_id's. Relationship type must be uppercase with underscores.",
            "source_module": "tools.neo4j_requirements_tool"
        },
        # Jira Tools (einige sind in beiden Agenten, andere spezifisch)
        "create_jira_issue": {
            "description": "Creates a new issue in Jira. Requires project key, summary, description, and issue type. Components can be optionally specified.",
            "source_module": "tools.jira_tools"
        },
        "get_jira_issue_details": {
            "description": "Retrieves detailed information about a specific Jira issue using its ID or key.",
            "source_module": "tools.jira_tools"
        },
        "update_jira_issue": {
            "description": "Updates fields of an existing Jira issue, such as summary, description, assignee, components, or category.",
            "source_module": "tools.jira_tools"
        },
        "add_jira_comment": {
            "description": "Adds a comment to a specific Jira issue.",
            "source_module": "tools.jira_tools"
        },
        "get_jira_comments": {
            "description": "Retrieves all comments from a specific Jira issue.",
            "source_module": "tools.jira_tools"
        },
        "show_jira_issue": {
            "description": "Generates a URL to view the specified Jira issue in a browser. Does not actually open the browser.",
            "source_module": "tools.jira_tools"
        },
        "get_jira_transitions": {
            "description": "Retrieves available workflow transitions for a Jira issue.",
            "source_module": "tools.jira_tools"
        },
        "transition_jira_issue": {
            "description": "Transitions a Jira issue to a new status using a transition ID.",
            "source_module": "tools.jira_tools"
        },
        "search_jira_issues_by_time": {
            "description": "Searches Jira issues based on time fields (e.g., created, updated) within a specified range. Supports additional JQL.",
            "source_module": "tools.jira_tools"
        },
        "create_jira_subtask": {
            "description": "Creates a sub-task for a given parent Jira issue. Requires parent issue key and summary. Components can be optionally specified.",
            "source_module": "tools.jira_tools"
        },
        "get_jira_subtasks": {
            "description": "Retrieves all sub-tasks associated with a parent Jira issue.",
            "source_module": "tools.jira_tools"
        },
        "delete_jira_issue": {
            "description": "Deletes a Jira issue. This action is often irreversible.",
            "source_module": "tools.jira_tools"
        },
        # Vector DB - Acceptance Criteria
        "add_acceptance_criterion": {
            "description": "Adds a new acceptance criterion to the vector database.",
            "source_module": "tools.vector_storage.acceptance_criteria"
        },
        "retrieve_similar_acceptance_criteria": {
            "description": "Retrieves acceptance criteria similar to a query text.",
            "source_module": "tools.vector_storage.acceptance_criteria"
        },
        "update_acceptance_criterion": {
            "description": "Updates an existing acceptance criterion.",
            "source_module": "tools.vector_storage.acceptance_criteria"
        },
        "delete_acceptance_criterion": {
            "description": "Deletes an acceptance criterion by its ID.",
            "source_module": "tools.vector_storage.acceptance_criteria"
        },
        "get_all_acceptance_criteria": {
            "description": "Retrieves all acceptance criteria from the database.",
            "source_module": "tools.vector_storage.acceptance_criteria"
        },
        # Vector DB - Test Cases
        "add_test_case": {
            "description": "Adds a new test case to the vector database.",
            "source_module": "tools.vector_storage.test_cases"
        },
        "retrieve_similar_test_cases": {
            "description": "Retrieves test cases similar to a query text.",
            "source_module": "tools.vector_storage.test_cases"
        },
        "update_test_case": {
            "description": "Updates an existing test case.",
            "source_module": "tools.vector_storage.test_cases"
        },
        "delete_test_case": {
            "description": "Deletes a test case by its ID.",
            "source_module": "tools.vector_storage.test_cases"
        },
        "get_all_test_cases": {
            "description": "Retrieves all test cases from the database.",
            "source_module": "tools.vector_storage.test_cases"
        },
        # Google Search
        "perform_google_search": {
            "description": "Performs a Google search for a given query and returns the results.",
            "source_module": "tools.google_search_tool"
        },
        # Requirement specific Jira generation
        "generate_jira_issues_for_requirement": {
            "description": "Generates Jira issues (e.g., Stories, Tasks) from a specified requirement in the vector database. It can use similar requirements for context and link the generated Jira issues back to the requirement's metadata.",
            "source_module": "tools.vector_storage.requirements"
        }
    }

def _get_initial_agent_tool_assignments() -> Dict[str, List[str]]:
    """
    Provides the initial tool assignments for agents.
    """
    return {
        "Product-Owner": [
            "create_jira_issue", "get_jira_issue_details", "update_jira_issue",
            "add_jira_comment", "get_jira_comments", "show_jira_issue",
            "get_jira_transitions", "transition_jira_issue", "search_jira_issues_by_time",
            "add_requirement", "retrieve_similar_requirements", "update_requirement",
            "delete_requirement", "get_all_requirements", "generate_jira_issues_for_requirement",
            "add_acceptance_criterion", "retrieve_similar_acceptance_criteria",
            "update_acceptance_criterion", "delete_acceptance_criterion", "get_all_acceptance_criteria",
            "add_test_case", "retrieve_similar_test_cases", "update_test_case",
            "delete_test_case", "get_all_test_cases",
            "add_or_update_requirement_neo4j", "add_relationship_neo4j",
            "get_tool_description", "update_tool_description_in_db" # Meta-tools
        ],
        "Developer": [
            "get_jira_issue_details", "update_jira_issue", "add_jira_comment",
            "get_jira_comments", "show_jira_issue", "get_jira_transitions",
            "transition_jira_issue", "create_jira_subtask", "get_jira_subtasks",
            "delete_jira_issue", "perform_google_search"
        ]
    }

def populate_initial_data():
    """Populates the database with initial tool descriptions and agent tool assignments."""
    conn = _get_db_connection()
    try:
        # Populate tool descriptions
        initial_descriptions = _get_initial_tool_descriptions()
        with conn:
            for tool_name, data in initial_descriptions.items():
                conn.execute(
                    f"INSERT OR IGNORE INTO {TABLE_NAME} (tool_name, description, source_module) VALUES (?, ?, ?)",
                    (tool_name, data["description"], data["source_module"])
                )
            print(f"{len(initial_descriptions)} initial tool descriptions inserted/ignored in '{TABLE_NAME}'.")

            # Populate agent tool assignments
            initial_agent_tools = _get_initial_agent_tool_assignments()
            for agent_name, tool_names in initial_agent_tools.items():
                for tool_name in tool_names:
                    # Ensure the tool exists in tool_descriptions before adding to agent_tools
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE tool_name = ?", (tool_name,))
                    if cursor.fetchone():
                        conn.execute(
                            "INSERT OR IGNORE INTO agent_tools (agent_name, tool_name) VALUES (?, ?)",
                            (agent_name, tool_name)
                        )
                    else:
                        print(f"Warning: Tool '{tool_name}' for agent '{agent_name}' not found in '{TABLE_NAME}'. Skipping assignment.")
            print(f"Initial agent tool assignments populated/ignored in 'agent_tools'.")

    except sqlite3.Error as e:
        print(f"Error populating initial data: {e}")
    finally:
        conn.close()

def get_tools_for_agent(agent_name: str) -> List[Dict[str, str]]:
    """
    Retrieves all tools (name and source module) assigned to a specific agent.
    """
    conn = _get_db_connection()
    tools_data = []
    try:
        cursor = conn.cursor()
        # Join agent_tools with tool_descriptions to get source_module
        cursor.execute(f"""
            SELECT at.tool_name, td.source_module
            FROM agent_tools at
            JOIN {TABLE_NAME} td ON at.tool_name = td.tool_name
            WHERE at.agent_name = ?
        """, (agent_name,))
        rows = cursor.fetchall()
        for row in rows:
            tools_data.append({"tool_name": row["tool_name"], "source_module": row["source_module"]})
    except sqlite3.Error as e:
        print(f"Error retrieving tools for agent '{agent_name}': {e}")
    finally:
        conn.close()
    return tools_data

def get_tool_description(tool_name: str) -> Optional[str]:
    """
    Retrieves the description for a specific tool from the database.

    Args:
        tool_name (str): The name of the tool's function (e.g., "add_requirement").

    Returns:
        Optional[str]: The description of the tool or None if not found.
    """
    conn = _get_db_connection()
    description: Optional[str] = None
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT description FROM {TABLE_NAME} WHERE tool_name = ?", (tool_name,))
        row = cursor.fetchone()
        if row:
            description = row['description']
    except sqlite3.Error as e:
        print(f"Error retrieving description for '{tool_name}': {e}")
    finally:
        conn.close()
    return description

def update_tool_description_in_db(tool_name: str, new_description: str) -> bool:
    """
    Updates the description of a tool in the database.
    Useful for external systems to change descriptions.

    Args:
        tool_name (str): The name of the tool whose description is to be updated.
        new_description (str): The new description.

    Returns:
        bool: True on success, False on error.
    """
    conn = _get_db_connection()
    try:
        with conn:
            result = conn.execute(
                f"UPDATE {TABLE_NAME} SET description = ? WHERE tool_name = ?",
                (new_description, tool_name)
            )
            if result.rowcount == 0:
                print(f"Warning: Tool '{tool_name}' not found in the database. No update performed.")
                return False
        print(f"Description for tool '{tool_name}' successfully updated.")
        return True
    except sqlite3.Error as e:
        print(f"Error updating description for '{tool_name}': {e}")
        return False
    finally:
        conn.close()

def get_all_tool_descriptions_from_db() -> List[Dict[str, str]]:
    """Retrieves all tool names and their descriptions from the database."""
    conn = _get_db_connection()
    tools_data = []
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT tool_name, description, source_module FROM {TABLE_NAME}")
        rows = cursor.fetchall()
        for row in rows:
            tools_data.append({"tool_name": row["tool_name"], "description": row["description"], "source_module": row["source_module"]})
    except sqlite3.Error as e:
        print(f"Error retrieving all tool descriptions: {e}")
    finally:
        conn.close()
    return tools_data

# Initialization: Create table and populate with initial data when the module is loaded.
# This ensures that the DB and table exist when other parts of the application use them.
if __name__ == "__main__":
    print(f"Database setup is being executed for: {DB_PATH}")
    create_table_if_not_exists() # This now also creates agent_tools
    populate_initial_data() # This now populates both tables
    print("\nExample retrieval of all descriptions:")
    all_descs = get_all_tool_descriptions_from_db()
    for desc_item in all_descs:
        print(f"  Tool: {desc_item['tool_name']} (from {desc_item['source_module']})")
        print(f"    Desc: {desc_item['description'][:70]}...")
    
    print("\nExample retrieval of a single description:")
    example_desc = get_tool_description("add_requirement")
    if example_desc:
        print(f"  Desc for 'add_requirement': {example_desc}")
    else:
        print("  'add_requirement' not found.")
else:
    # Ensure the DB and tables exist and are populated upon import
    create_table_if_not_exists()
    populate_initial_data()

__all__ = [
    'get_tool_description',
    'update_tool_description_in_db',
    'get_all_tool_descriptions_from_db',
    'get_tools_for_agent', # Export new function
    'DB_PATH'
]
