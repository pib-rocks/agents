"""
Tool for interacting with a Neo4j graph database to store and relate requirements.
"""
import os
import json
import datetime
from typing import Optional, Dict, List
from neo4j import GraphDatabase, basic_auth
from dotenv import load_dotenv

# Load environment variables for Neo4j connection
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Global driver instance (consider connection pooling for high-load scenarios)
_driver = None

def _get_driver():
    """Initializes and returns the Neo4j driver instance."""
    global _driver
    if _driver is None:
        if not NEO4J_PASSWORD:
            raise ValueError("NEO4J_PASSWORD environment variable not set.")
        try:
            # Specify the database name during driver initialization
            _driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD),
                database="pib" # Use the 'pib' database
            )
            # Verify connection
            _driver.verify_connectivity()
            print("Neo4j connection successful to database 'pib'.")
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            _driver = None # Ensure driver is None if connection fails
            raise ConnectionError(f"Could not connect to Neo4j at {NEO4J_URI}: {e}") from e
    return _driver

def _close_driver():
    """Closes the Neo4j driver instance."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        print("Neo4j connection closed.")

# Ensure driver is closed when the application exits (optional, depends on application lifecycle)
# import atexit
# atexit.register(_close_driver)

def _execute_write_query(query: str, parameters: Optional[Dict] = None) -> List[Dict]:
    """Executes a write transaction query."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.execute_write(lambda tx: tx.run(query, parameters).data())
        return result

def _execute_read_query(query: str, parameters: Optional[Dict] = None) -> List[Dict]:
    """Executes a read transaction query."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.execute_read(lambda tx: tx.run(query, parameters).data())
        return result

def add_or_update_requirement_neo4j(req_id: str, text: str, properties_json: Optional[str] = None) -> Dict:
    """
    Adds a new requirement node to Neo4j or updates an existing one based on req_id.

    Args:
        req_id (str): The unique identifier for the requirement (e.g., "REQ-123").
        text (str): The main text content of the requirement.
        properties_json (Optional[str]): A JSON string containing additional properties
                                         (e.g., '{"source_jira_ticket": "PROJ-456", "status": "Draft"}').

    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not req_id:
        return {"status": "error", "error_message": "Requirement ID (req_id) cannot be empty."}
    if not text:
        return {"status": "error", "error_message": "Requirement text cannot be empty."}

    parsed_properties = {}
    if properties_json:
        try:
            parsed_properties = json.loads(properties_json)
            if not isinstance(parsed_properties, dict):
                raise ValueError("Properties must be a JSON object (dictionary).")
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for properties."}
        except ValueError as ve:
            return {"status": "error", "error_message": str(ve)}

    # Combine mandatory fields with optional properties
    node_properties = {
        "req_id": req_id,
        "text": text,
        "change_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **parsed_properties # Add/overwrite with user-provided properties
    }

    # Cypher query using MERGE to create or update the node
    # SET n = $props ensures all properties are updated if the node exists
    query = """
    MERGE (n:Requirement {req_id: $req_id})
    SET n = $props
    RETURN n.req_id as req_id, properties(n) as properties
    """
    parameters = {"req_id": req_id, "props": node_properties}

    try:
        result = _execute_write_query(query, parameters)
        if result:
            return {"status": "success", "report": f"Requirement '{req_id}' added or updated in Neo4j.", "data": result[0]}
        else:
            # Should not happen with MERGE + RETURN, but as a safeguard
            return {"status": "error", "error_message": f"Failed to confirm update for requirement '{req_id}'."}
    except ConnectionError as ce:
         return {"status": "error", "error_message": f"Neo4j connection error: {ce}"}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to add/update requirement '{req_id}' in Neo4j: {e}"}

def add_relationship_neo4j(start_req_id: str, end_req_id: str, relationship_type: str) -> Dict:
    """
    Adds a directed relationship between two existing requirement nodes in Neo4j.

    Args:
        start_req_id (str): The ID of the starting requirement node.
        end_req_id (str): The ID of the ending requirement node.
        relationship_type (str): The type of the relationship (e.g., "RELATES_TO", "DEPENDS_ON", "DUPLICATES").
                                 Must be a valid Neo4j relationship type (uppercase, underscores).

    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not start_req_id or not end_req_id:
        return {"status": "error", "error_message": "Both start and end requirement IDs must be provided."}
    if not relationship_type or not relationship_type.isidentifier() or not relationship_type.isupper():
         return {"status": "error", "error_message": f"Invalid relationship type: '{relationship_type}'. Must be uppercase letters and underscores (e.g., 'RELATES_TO')."}

    # Cypher query using MATCH and MERGE to create the relationship only if both nodes exist
    query = f"""
    MATCH (start:Requirement {{req_id: $start_id}})
    MATCH (end:Requirement {{req_id: $end_id}})
    MERGE (start)-[r:{relationship_type}]->(end)
    RETURN start.req_id as start_id, type(r) as rel_type, end.req_id as end_id
    """
    parameters = {"start_id": start_req_id, "end_id": end_req_id}

    try:
        result = _execute_write_query(query, parameters)
        if result:
            res = result[0]
            return {"status": "success", "report": f"Relationship '{res['start_id']}-[{res['rel_type']}]->{res['end_id']}' added or confirmed in Neo4j."}
        else:
            # This happens if one or both nodes were not found
            return {"status": "error", "error_message": f"Could not create relationship. Ensure both requirements '{start_req_id}' and '{end_req_id}' exist in Neo4j."}
    except ConnectionError as ce:
         return {"status": "error", "error_message": f"Neo4j connection error: {ce}"}
    except Exception as e:
        # Catch potential CypherSyntaxError if relationship_type is invalid despite checks
        return {"status": "error", "error_message": f"Failed to add relationship '{relationship_type}' between '{start_req_id}' and '{end_req_id}' in Neo4j: {e}"}

# Example Usage (for testing)
if __name__ == '__main__':
    try:
        # Ensure driver is ready
        _get_driver()

        # Add/Update Requirements
        print(add_or_update_requirement_neo4j("REQ-N1", "User login via email", '{"source_jira_ticket": "PROJ-101", "priority": "High"}'))
        print(add_or_update_requirement_neo4j("REQ-N2", "Password reset functionality", '{"source_jira_ticket": "PROJ-102"}'))
        print(add_or_update_requirement_neo4j("REQ-N3", "Two-factor authentication", '{"source_jira_ticket": "PROJ-103", "status": "Defined"}'))
        print(add_or_update_requirement_neo4j("REQ-N1", "User login via email and username", '{"source_jira_ticket": "PROJ-101", "priority": "Highest", "status": "Refined"}')) # Update REQ-N1

        # Add Relationships
        print(add_relationship_neo4j("REQ-N1", "REQ-N2", "RELATES_TO"))
        print(add_relationship_neo4j("REQ-N3", "REQ-N1", "DEPENDS_ON"))
        print(add_relationship_neo4j("REQ-N2", "REQ-N3", "BLOCKS")) # Example custom relationship
        print(add_relationship_neo4j("REQ-N1", "REQ-N4", "RELATES_TO")) # Should fail if REQ-N4 doesn't exist

    finally:
        # Close the driver connection when done
        _close_driver()


__all__ = [
    'add_or_update_requirement_neo4j',
    'add_relationship_neo4j'
]
