"""
Manages storing and retrieving software requirements, acceptance criteria,
test cases, and potentially other artifacts using a ChromaDB vector database.
"""
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
                                       with the requirement. Based on requirement_schema.json,
                                       this JSON object should contain the following keys:
                                       - "type" (str): Must be "Requirement".
                                       - "source_jira_ticket" (str): The originating Jira ticket key (e.g., "PROJECT-123").
                                       - "acceptance_criteria_ids" (List[str]): A list of IDs for associated acceptance criteria (e.g., ["AC-1", "AC-2"]).
                                       Example: '{ "type": "Requirement", "source_jira_ticket": "PROJECT-123", "acceptance_criteria_ids": ["AC-1"] }'

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
                                              to filter results based on the stored metadata fields defined
                                              in requirement_schema.json (e.g., "type", "source_jira_ticket").
                                              Example: To find requirements from a specific ticket:
                                              '{"type": "Requirement", "source_jira_ticket": "PROJECT-123"}'
                                              Uses ChromaDB's 'where' filter format (see ChromaDB docs for operators like $in, $eq, etc.).

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
        metadata_json (Optional[str]): Optional JSON string representing metadata associated
                                       with the acceptance criterion. Based on acceptance_criteria_schema.json,
                                       this JSON object should contain the following keys:
                                       - "type" (str): Must be "AcceptanceCriterion".
                                       - "source_jira_ticket" (str): The originating Jira ticket key (e.g., "PROJECT-123").
                                       - "requirement_ids" (List[str]): A list of IDs for associated requirements (e.g., ["REQ-1"]).
                                       - "test_case_ids" (List[str]): A list of IDs for associated test cases (e.g., ["TC-1"]).
                                       Example: '{ "type": "AcceptanceCriterion", "source_jira_ticket": "PROJECT-123", "requirement_ids": ["REQ-1"], "test_case_ids": ["TC-1"] }'

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
        filter_metadata_json (Optional[str]): Optional JSON string for metadata filtering based on the
                                              fields defined in acceptance_criteria_schema.json
                                              (e.g., "type", "source_jira_ticket", "requirement_ids", "test_case_ids").
                                              It's recommended to include '{"type": "AcceptanceCriterion"}'
                                              in the filter unless filtering by other specific AC metadata.
                                              Example: To find ACs for a specific ticket:
                                              '{"type": "AcceptanceCriterion", "source_jira_ticket": "PROJECT-123"}'
                                              Uses ChromaDB's 'where' filter format (see ChromaDB docs for operators like $in, $eq, etc.).

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


def update_acceptance_criterion(criterion_id: str, new_criterion_text: Optional[str] = None, new_metadata_json: Optional[str] = None) -> Dict:
    """Updates the text and/or metadata of an existing acceptance criterion.

    Args:
        criterion_id (str): The unique identifier of the criterion to update.
        new_criterion_text (Optional[str]): The new text for the criterion. If None, text is not updated.
        new_metadata_json (Optional[str]): A JSON string representing the *complete* new metadata object.
                                           If provided, it *replaces* the existing metadata entirely.
                                           The structure should follow acceptance_criteria_schema.json, including
                                           keys like "type" (must be "AcceptanceCriterion"), "source_jira_ticket",
                                           "requirement_ids", and "test_case_ids".
                                           If None, metadata is not updated.

    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not criterion_id:
        return {"status": "error", "error_message": "Criterion ID cannot be empty."}
    if new_criterion_text is None and new_metadata_json is None:
        return {"status": "error", "error_message": "Must provide either new text or new metadata to update."}

    # Check if the criterion exists and is an Acceptance Criterion
    try:
        existing = collection.get(ids=[criterion_id], include=['metadatas'])
        if not existing or not existing.get('ids'):
            return {"status": "error", "error_message": f"Acceptance Criterion '{criterion_id}' not found."}
        
        existing_metadata = existing['metadatas'][0] if existing.get('metadatas') else {}
        if existing_metadata.get('type') != 'AcceptanceCriterion':
             return {"status": "error", "error_message": f"Item '{criterion_id}' found, but it is not an Acceptance Criterion (type: {existing_metadata.get('type')}). Update aborted."}

    except Exception as e:
        return {"status": "error", "error_message": f"Error checking existence of criterion '{criterion_id}': {e}"}


    updates_to_make = {}
    parsed_new_metadata = None

    if new_criterion_text is not None:
        if not new_criterion_text.strip():
             return {"status": "error", "error_message": "New criterion text cannot be empty."}
        updates_to_make['documents'] = [new_criterion_text]

    if new_metadata_json is not None:
        try:
            parsed_new_metadata = json.loads(new_metadata_json)
            if not isinstance(parsed_new_metadata, dict):
                raise ValueError("New metadata must be a JSON object (dictionary).")
            # Ensure the type remains correct, or warn if it's changed/missing
            if 'type' not in parsed_new_metadata:
                 print(f"Warning: Updating metadata for '{criterion_id}' without a 'type' field. Setting to 'AcceptanceCriterion'.")
                 parsed_new_metadata['type'] = 'AcceptanceCriterion'
            elif parsed_new_metadata.get('type') != 'AcceptanceCriterion':
                 print(f"Warning: Updating metadata for '{criterion_id}' with a type other than 'AcceptanceCriterion' ('{parsed_new_metadata.get('type')}').")
            
            updates_to_make['metadatas'] = [parsed_new_metadata]
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for new metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    if not updates_to_make:
         # This case should be caught earlier, but as a safeguard
         return {"status": "error", "error_message": "No valid updates provided."}

    try:
        collection.update(
            ids=[criterion_id],
            **updates_to_make
        )
        update_fields = []
        if 'documents' in updates_to_make: update_fields.append("text")
        if 'metadatas' in updates_to_make: update_fields.append("metadata")
        return {"status": "success", "report": f"Acceptance Criterion '{criterion_id}' updated successfully ({', '.join(update_fields)})."}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to update criterion '{criterion_id}': {e}"}


# --- Test Case Functions ---

def add_test_case(test_case_id: str, test_case_document: str, metadata_json: Optional[str] = None) -> Dict:
    """Adds or updates a test case in the vector database.

    Args:
        test_case_id (str): A unique identifier for the test case (e.g., 'TC-1').
        test_case_document (str): The primary text/description of the test case.
                                  Corresponds to the 'document' field in testcase_schema.json.
        metadata_json (Optional[str]): Optional JSON string representing metadata associated
                                       with the test case. Based on testcase_schema.json,
                                       this JSON object should contain the following keys:
                                       - "type" (str): Must be "TestCase".
                                       - "title" (str): A descriptive title for the test case.
                                       - "source_jira_ticket" (str): The originating Jira ticket key (e.g., "PROJECT-123").
                                       - "validates_ac_ids" (List[str]): A list of IDs for acceptance criteria this test case validates (e.g., ["AC-1"]).
                                       - "test_steps" (List[Dict]): A list of test step objects, where each object has:
                                           - "step_description" (str): Description of the step.
                                           - "is_automatable" (bool): Whether the step can be automated.
                                       Example: '{ "type": "TestCase", "title": "...", "source_jira_ticket": "...", "validates_ac_ids": ["AC-1"], "test_steps": [{"step_description": "...", "is_automatable": true}] }'

    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not test_case_id or not test_case_document:
        return {"status": "error", "error_message": "Test Case ID and document text cannot be empty."}

    parsed_metadata = {}
    if metadata_json:
        try:
            parsed_metadata = json.loads(metadata_json)
            if not isinstance(parsed_metadata, dict):
                raise ValueError("Metadata must be a JSON object (dictionary).")
            if 'type' not in parsed_metadata:
                 print(f"Warning: Adding test case '{test_case_id}' without explicit 'type' metadata.")
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    # Enforce type for consistency
    if 'type' not in parsed_metadata:
        parsed_metadata['type'] = 'TestCase'

    try:
        collection.upsert(
            ids=[test_case_id],
            documents=[test_case_document],
            metadatas=[parsed_metadata]
        )
        return {"status": "success", "report": f"Test Case '{test_case_id}' added/updated successfully."}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to add/update test case '{test_case_id}': {e}"}


def retrieve_similar_test_cases(query_text: str, n_results: int = 3, filter_metadata_json: Optional[str] = None) -> Dict:
    """Retrieves test cases semantically similar to the query text.

    Args:
        query_text (str): The text to search for similar test cases.
        n_results (int): The maximum number of similar test cases to return. Defaults to 3.
        filter_metadata_json (Optional[str]): Optional JSON string for metadata filtering based on the
                                              fields defined in testcase_schema.json
                                              (e.g., "type", "title", "source_jira_ticket", "validates_ac_ids").
                                              Note: Filtering on nested fields like "test_steps" might require specific ChromaDB syntax or might not be directly supported.
                                              It's recommended to include '{"type": "TestCase"}'
                                              in the filter unless filtering by other specific TC metadata.
                                              Example: To find TCs for a specific ticket:
                                              '{"type": "TestCase", "source_jira_ticket": "PROJECT-123"}'
                                              Uses ChromaDB's 'where' filter format (see ChromaDB docs for operators like $in, $eq, etc.).

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
            if 'type' not in parsed_filter:
                 print(f"Warning: Retrieving test cases without explicit 'type' filter. Consider adding '\"type\": \"TestCase\"' to the filter.")
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for filter metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}
    else:
        # Default filter to only get Test Cases if no filter is provided
        parsed_filter = {"type": "TestCase"}
        print("Info: No filter provided. Defaulting to retrieve only items with metadata 'type': 'TestCase'.")

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
            if filter_metadata_json:
                return {"status": "success", "report": f"No similar test cases found matching the filter: {filter_metadata_json}"}
            else:
                count = collection.count(where={"type": "TestCase"})
                if count == 0:
                    return {"status": "success", "report": "No test cases found in the database."}
                else:
                    return {"status": "success", "report": "No similar test cases found for the query."}

        report_lines = [f"Found {len(ids)} similar test case(s) for query '{query_text[:50]}...':"]
        for i in range(len(ids)):
            report_lines.append(
                f"  - ID: {ids[i]}, Distance: {distances[i]:.4f}\n"
                f"    Document: {documents[i]}\n" # Changed from Text to Document for clarity
                f"    Metadata: {metadatas[i]}"
            )

        return {"status": "success", "report": "\n".join(report_lines)}

    except Exception as e:
        return {"status": "error", "error_message": f"Failed to retrieve test cases: {e}"}


def update_test_case(test_case_id: str, new_test_case_document: Optional[str] = None, new_metadata_json: Optional[str] = None) -> Dict:
    """Updates the document text and/or metadata of an existing test case.

    Args:
        test_case_id (str): The unique identifier of the test case to update.
        new_test_case_document (Optional[str]): The new document text for the test case. If None, text is not updated.
        new_metadata_json (Optional[str]): A JSON string representing the *complete* new metadata object.
                                           If provided, it *replaces* the existing metadata entirely.
                                           The structure should follow testcase_schema.json, including
                                           keys like "type" (must be "TestCase"), "title", "source_jira_ticket",
                                           "validates_ac_ids", and "test_steps" (with its nested structure).
                                           If None, metadata is not updated.

    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not test_case_id:
        return {"status": "error", "error_message": "Test Case ID cannot be empty."}
    if new_test_case_document is None and new_metadata_json is None:
        return {"status": "error", "error_message": "Must provide either new document text or new metadata to update."}

    # Check if the test case exists and is a TestCase
    try:
        existing = collection.get(ids=[test_case_id], include=['metadatas'])
        if not existing or not existing.get('ids'):
            return {"status": "error", "error_message": f"Test Case '{test_case_id}' not found."}

        existing_metadata = existing['metadatas'][0] if existing.get('metadatas') else {}
        if existing_metadata.get('type') != 'TestCase':
             return {"status": "error", "error_message": f"Item '{test_case_id}' found, but it is not a Test Case (type: {existing_metadata.get('type')}). Update aborted."}

    except Exception as e:
        return {"status": "error", "error_message": f"Error checking existence of test case '{test_case_id}': {e}"}

    updates_to_make = {}
    parsed_new_metadata = None

    if new_test_case_document is not None:
        if not new_test_case_document.strip():
             return {"status": "error", "error_message": "New test case document text cannot be empty."}
        updates_to_make['documents'] = [new_test_case_document]

    if new_metadata_json is not None:
        try:
            parsed_new_metadata = json.loads(new_metadata_json)
            if not isinstance(parsed_new_metadata, dict):
                raise ValueError("New metadata must be a JSON object (dictionary).")
            # Ensure the type remains correct
            if 'type' not in parsed_new_metadata:
                 print(f"Warning: Updating metadata for '{test_case_id}' without a 'type' field. Setting to 'TestCase'.")
                 parsed_new_metadata['type'] = 'TestCase'
            elif parsed_new_metadata.get('type') != 'TestCase':
                 print(f"Warning: Updating metadata for '{test_case_id}' with a type other than 'TestCase' ('{parsed_new_metadata.get('type')}').")

            updates_to_make['metadatas'] = [parsed_new_metadata]
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for new metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    if not updates_to_make:
         return {"status": "error", "error_message": "No valid updates provided."}

    try:
        collection.update(
            ids=[test_case_id],
            **updates_to_make
        )
        update_fields = []
        if 'documents' in updates_to_make: update_fields.append("document")
        if 'metadatas' in updates_to_make: update_fields.append("metadata")
        return {"status": "success", "report": f"Test Case '{test_case_id}' updated successfully ({', '.join(update_fields)})."}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to update test case '{test_case_id}': {e}"}


def delete_test_case(test_case_id: str) -> Dict:
    """Deletes a test case from the vector database by its ID."""
    if not test_case_id:
        return {"status": "error", "error_message": "Test Case ID cannot be empty."}
    try:
        # Optional: Verify it's a TC before deleting?
        # item = collection.get(ids=[test_case_id], include=['metadatas'])
        # if not item or item['metadatas'][0].get('type') != 'TestCase':
        #     return {"status": "error", "error_message": f"Item '{test_case_id}' not found or is not a Test Case."}

        collection.delete(ids=[test_case_id])
        return {"status": "success", "report": f"Test Case '{test_case_id}' deleted successfully."}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to delete test case '{test_case_id}': {e}"}


# Export public functions
__all__ = [
    'add_requirement',
    'retrieve_similar_requirements',
    'delete_requirement',
    'add_acceptance_criterion',
    'retrieve_similar_acceptance_criteria',
    'delete_acceptance_criterion',
    'update_acceptance_criterion',
    'add_test_case',
    'retrieve_similar_test_cases',
    'update_test_case',
    'delete_test_case'
]
