"""
Manages storing and retrieving software requirements, acceptance criteria,
and potentially other artifacts using a ChromaDB vector database.
"""#AI! Add a function to update an acceptance-criterium
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional

# --- Configuration ---
# Use environment variables or defaults
PERSIST_DIRECTORY = os.getenv("VECTOR_DB_PATH", "./chroma_db")
COLLECTION_NAME = os.getenv("VECTOR_DB_COLLECTION", "cerebra_requirements")
# Using default embedding function (requires sentence-transformers)
# For production, consider specifying a model explicitly or using a different provider.
# ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
# Or use OpenAI, Cohere, etc. if configured:
# ef = embedding_functions.OpenAIEmbeddingFunction(api_key="...", model_name="...")
# Using default for simplicity now:
ef = embedding_functions.DefaultEmbeddingFunction() # Requires sentence-transformers

# Ensure the persistence directory exists
os.makedirs(PERSIST_DIRECTORY, exist_ok=True)

# --- ChromaDB Client and Collection ---
# Initialize client (persistent)
client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

# Get or create the collection
# Using allow_reset=True for development ease, might remove for production
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=ef,
    # metadata={"hnsw:space": "cosine"} # Optional: Specify distance metric if needed
)

import json # Add json import for parsing

# --- Tool Functions ---

def add_requirement(requirement_id: str, requirement_text: str, metadata_json: Optional[str] = None) -> Dict:
    """Adds or updates a software requirement in the vector database.

    Args:
        requirement_id (str): A unique identifier for the requirement (e.g., 'REQ-1', 'USERSTORY-LOGIN').
        requirement_text (str): The full text of the requirement.
        metadata_json (Optional[str]): Optional JSON string representing metadata associated
                                       with the requirement. The expected schema, based on
                                       requirement_schema.json, includes fields like:
                                       '{
                                           "type": "Requirement",
                                           "source_jira_ticket": "PR-123",
                                           "acceptance_criteria_ids": ["AC-1", "AC-2"]
                                       }'
                                       However, any valid JSON object is accepted.

    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not requirement_id or not requirement_text:
        return {"status": "error", "error_message": "Requirement ID and text cannot be empty."}

    parsed_metadata = {}
    if metadata_json:
        try:
            parsed_metadata = json.loads(metadata_json)
            if not isinstance(parsed_metadata, dict):
                raise ValueError("Metadata must be a JSON object (dictionary).")
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    # You might want to add standard metadata fields automatically, e.g., timestamp
    # parsed_metadata['last_updated'] = datetime.datetime.utcnow().isoformat()

    try:
        # Use upsert to add or update based on ID
        collection.upsert(
            ids=[requirement_id],
            documents=[requirement_text],
            metadatas=[parsed_metadata] # Chroma expects a list for each argument
        )
        return {"status": "success", "report": f"Requirement '{requirement_id}' added/updated successfully."}
    except Exception as e:
        # Catch potential ChromaDB errors or other issues
        return {"status": "error", "error_message": f"Failed to add/update requirement '{requirement_id}': {e}"}


def retrieve_similar_requirements(query_text: str, n_results: int = 3, filter_metadata_json: Optional[str] = None) -> Dict:
    """Retrieves requirements from the vector database that are semantically similar to the query text.

    Args:
        query_text (str): The text to search for similar requirements (e.g., a new user story, a feature description).
        n_results (int): The maximum number of similar requirements to return. Defaults to 3.
        filter_metadata_json (Optional[str]): Optional JSON string representing a metadata dictionary
                                              to filter results based on the stored metadata.
                                              Example: '{"type": "Requirement", "source_jira_ticket": "PR-123"}'
                                              Uses ChromaDB's 'where' filter format.

    Returns:
        Dict: Status dictionary with results or error message. Results include IDs, text, distance, and metadata.
    """
    if not query_text:
        return {"status": "error", "error_message": "Query text cannot be empty."}
    if n_results <= 0:
        return {"status": "error", "error_message": "Number of results must be positive."}

    parsed_filter = None
    if filter_metadata_json:
        try:
            parsed_filter = json.loads(filter_metadata_json)
            if not isinstance(parsed_filter, dict):
                raise ValueError("Filter metadata must be a JSON object (dictionary).")
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for filter metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=parsed_filter, # Use the parsed filter dictionary
            include=['documents', 'distances', 'metadatas'] # Specify what data to return
        )

        # Process results (query returns lists within lists for batch queries, even for a single query)
        ids = results.get('ids', [[]])[0]
        documents = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]

        if not ids:
            return {"status": "success", "report": "No similar requirements found."}

        report_lines = [f"Found {len(ids)} similar requirement(s) for query '{query_text[:50]}...':"]
        for i in range(len(ids)):
            report_lines.append(
                f"  - ID: {ids[i]}, Distance: {distances[i]:.4f}\n"
                f"    Text: {documents[i]}\n"
                f"    Metadata: {metadatas[i]}"
            )

        return {"status": "success", "report": "\n".join(report_lines)}

    except Exception as e:
        return {"status": "error", "error_message": f"Failed to retrieve requirements: {e}"}


# --- Optional: Add delete/get by ID if needed ---
def delete_requirement(requirement_id: str) -> Dict:
    """Deletes a requirement from the vector database by its ID."""
    if not requirement_id:
        return {"status": "error", "error_message": "Requirement ID cannot be empty."}
    try:
        collection.delete(ids=[requirement_id])
        return {"status": "success", "report": f"Requirement '{requirement_id}' deleted successfully."}
    except Exception as e:
         # Catch potential ChromaDB errors (e.g., ID not found - though delete might not error)
         # Check ChromaDB documentation for specific delete error handling if needed.
        return {"status": "error", "error_message": f"Failed to delete requirement '{requirement_id}': {e}"}


# --- Acceptance Criteria Functions ---

def add_acceptance_criterion(criterion_id: str, criterion_text: str, metadata_json: Optional[str] = None) -> Dict:
    """Adds or updates an acceptance criterion in the vector database.

    Args:
        criterion_id (str): A unique identifier for the criterion (e.g., 'AC-1').
        criterion_text (str): The full text of the acceptance criterion.
        metadata_json (Optional[str]): Optional JSON string representing metadata.
                                       Expected schema based on acceptance_criteria_schema.json:
                                       '{
                                           "type": "AcceptanceCriterion",
                                           "source_jira_ticket": "PROJECT-123",
                                           "requirement_ids": ["REQ-1"],
                                           "test_case_ids": ["TC-1"]
                                       }'
                                       The 'type' field is strongly recommended.

    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not criterion_id or not criterion_text:
        return {"status": "error", "error_message": "Criterion ID and text cannot be empty."}

    parsed_metadata = {}
    if metadata_json:
        try:
            parsed_metadata = json.loads(metadata_json)
            if not isinstance(parsed_metadata, dict):
                raise ValueError("Metadata must be a JSON object (dictionary).")
            # Ensure type is set if provided, or default if appropriate
            if 'type' not in parsed_metadata:
                 print(f"Warning: Adding acceptance criterion '{criterion_id}' without explicit 'type' metadata.")
                 # parsed_metadata['type'] = 'AcceptanceCriterion' # Optionally enforce type
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    # Automatically add type if not present? Consider implications.
    if 'type' not in parsed_metadata:
        parsed_metadata['type'] = 'AcceptanceCriterion' # Enforce type for consistency

    try:
        collection.upsert(
            ids=[criterion_id],
            documents=[criterion_text],
            metadatas=[parsed_metadata]
        )
        return {"status": "success", "report": f"Acceptance Criterion '{criterion_id}' added/updated successfully."}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to add/update criterion '{criterion_id}': {e}"}


def retrieve_similar_acceptance_criteria(query_text: str, n_results: int = 3, filter_metadata_json: Optional[str] = None) -> Dict:
    """Retrieves acceptance criteria semantically similar to the query text.

    Args:
        query_text (str): The text to search for similar criteria.
        n_results (int): The maximum number of similar criteria to return. Defaults to 3.
        filter_metadata_json (Optional[str]): Optional JSON string for metadata filtering.
                                              It's recommended to include '{"type": "AcceptanceCriterion"}'
                                              in the filter if not filtering by other specific AC metadata.
                                              Example: '{"type": "AcceptanceCriterion", "source_jira_ticket": "PR-123"}'
                                              Uses ChromaDB's 'where' filter format.

    Returns:
        Dict: Status dictionary with results or error message.
    """
    if not query_text:
        return {"status": "error", "error_message": "Query text cannot be empty."}
    if n_results <= 0:
        return {"status": "error", "error_message": "Number of results must be positive."}

    parsed_filter = None
    if filter_metadata_json:
        try:
            parsed_filter = json.loads(filter_metadata_json)
            if not isinstance(parsed_filter, dict):
                raise ValueError("Filter metadata must be a JSON object (dictionary).")
            # Recommend adding type filter if not present
            if 'type' not in parsed_filter:
                 print(f"Warning: Retrieving acceptance criteria without explicit 'type' filter. Consider adding '\"type\": \"AcceptanceCriterion\"' to the filter.")
                 # You could enforce adding it: parsed_filter['type'] = 'AcceptanceCriterion'
                 # Or use a more complex 'where' like {"$and": [{"type": "AcceptanceCriterion"}, user_filter]}
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for filter metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}
    else:
        # Default filter to only get Acceptance Criteria if no filter is provided
        parsed_filter = {"type": "AcceptanceCriterion"}
        print("Info: No filter provided. Defaulting to retrieve only items with metadata 'type': 'AcceptanceCriterion'.")


    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=parsed_filter,
            include=['documents', 'distances', 'metadatas']
        )

        ids = results.get('ids', [[]])[0]
        documents = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]

        if not ids:
             # Check if the filter might be too restrictive
            if filter_metadata_json:
                return {"status": "success", "report": f"No similar acceptance criteria found matching the filter: {filter_metadata_json}"}
            else:
                # Check if *any* ACs exist if the default filter was used
                count = collection.count(where={"type": "AcceptanceCriterion"})
                if count == 0:
                    return {"status": "success", "report": "No acceptance criteria found in the database."}
                else:
                    return {"status": "success", "report": "No similar acceptance criteria found for the query."}


        report_lines = [f"Found {len(ids)} similar acceptance criteria(s) for query '{query_text[:50]}...':"]
        for i in range(len(ids)):
            report_lines.append(
                f"  - ID: {ids[i]}, Distance: {distances[i]:.4f}\n"
                f"    Text: {documents[i]}\n"
                f"    Metadata: {metadatas[i]}"
            )

        return {"status": "success", "report": "\n".join(report_lines)}

    except Exception as e:
        return {"status": "error", "error_message": f"Failed to retrieve acceptance criteria: {e}"}


def delete_acceptance_criterion(criterion_id: str) -> Dict:
    """Deletes an acceptance criterion from the vector database by its ID."""
    if not criterion_id:
        return {"status": "error", "error_message": "Criterion ID cannot be empty."}
    try:
        # Optional: Verify it's an AC before deleting?
        # item = collection.get(ids=[criterion_id], include=['metadatas'])
        # if not item or item['metadatas'][0].get('type') != 'AcceptanceCriterion':
        #     return {"status": "error", "error_message": f"Item '{criterion_id}' not found or is not an Acceptance Criterion."}

        collection.delete(ids=[criterion_id])
        return {"status": "success", "report": f"Acceptance Criterion '{criterion_id}' deleted successfully."}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to delete criterion '{criterion_id}': {e}"}


# Export public functions
__all__ = [
    'add_requirement',
    'retrieve_similar_requirements',
    'delete_requirement',
    'add_acceptance_criterion',
    'retrieve_similar_acceptance_criteria',
    'delete_acceptance_criterion'
]
