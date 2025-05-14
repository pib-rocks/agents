"""
Functions for managing test cases in the vector database.
"""
import json
import datetime
from typing import List, Dict, Optional

# Import shared components from the package initializer
from . import client, collection, _get_next_id
from .requirements import ALLOWED_CLASSIFICATIONS, DEFAULT_CLASSIFICATION # Import from requirements

# --- Test Case Functions ---

def add_test_case(test_case_document: str, metadata_json: Optional[str] = None) -> Dict:
    """Adds a new test case to the vector database with an automatically generated ID.

    Args:
        test_case_document (str): The primary text/description of the test case.
                                  Corresponds to the 'document' field in testcase_schema.json.
        metadata_json (Optional[str]): Optional JSON string representing metadata associated
                                       with the test case. Based on testcase_schema.json,
                                       this JSON object should contain keys like:
                                       - "type" (str): Must be "TestCase".
                                       - "title" (str): A descriptive title for the test case.
                                       - "source_jira_ticket" (str): The originating Jira ticket key (e.g., "PROJECT-123").
                                       - "classification" (str): Must be one of ALLOWED_CLASSIFICATIONS.
                                                                 Defaults to "Functional" if not provided.
                                       - "test_steps" (List[Dict]): A list of test step objects, where each object has:
                                           - "step_description" (str): Description of the step.
                                           - "is_automatable" (bool): Whether the step can be automated.
                                       Example: '{ "type": "TestCase", "title": "...", "source_jira_ticket": "...", "classification": "Functional", "test_steps": [{"step_description": "...", "is_automatable": true}] }'

    Returns:
        Dict: Status dictionary indicating success or error, including the generated test case ID.
    """
    if not test_case_document:
        return {"status": "error", "error_message": "Test case document text cannot be empty."}

    # Generate the next test case ID
    try:
        new_test_case_id = _get_next_id("TC-")
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to generate test case ID: {e}"}

    parsed_metadata = {}
    if metadata_json:
        try:
            parsed_metadata = json.loads(metadata_json)
            if not isinstance(parsed_metadata, dict):
                raise ValueError("Metadata must be a JSON object (dictionary).")
            if 'type' not in parsed_metadata:
                 # Use the generated ID in the warning message
                 print(f"Warning: Adding test case '{new_test_case_id}' without explicit 'type' metadata.")
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    # Validate and set requirement classification
    current_classification = parsed_metadata.get('classification')
    if current_classification is not None:
        if current_classification not in ALLOWED_CLASSIFICATIONS:
            return {
                "status": "error",
                "error_message": f"Invalid classification '{current_classification}'. Must be one of {ALLOWED_CLASSIFICATIONS}."
            }
    else:
        parsed_metadata['classification'] = DEFAULT_CLASSIFICATION

    # Enforce type for consistency
    if 'type' not in parsed_metadata:
        parsed_metadata['type'] = 'TestCase'
    # Add the change date
    parsed_metadata['change_date'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        # Use the generated ID in the upsert call
        collection.upsert(
            ids=[new_test_case_id],
            documents=[test_case_document],
            metadatas=[parsed_metadata]
        )
        # Use the generated ID in the success message and return value
        return {"status": "success", "report": f"Test Case '{new_test_case_id}' added successfully.", "test_case_id": new_test_case_id}
    except Exception as e:
        # Use the generated ID in the error message
        return {"status": "error", "error_message": f"Failed to add test case '{new_test_case_id}': {e}"}


def retrieve_similar_test_cases(query_text: str, n_results: int = 3, filter_metadata_json: Optional[str] = None) -> Dict:
    """Retrieves test cases from the vector database semantically similar to the query text.

    Args:
        query_text (str): The text to search for similar test cases.
        n_results (int): The maximum number of similar test cases to return. Defaults to 3.
        filter_metadata_json (Optional[str]): Optional JSON string for metadata filtering based on the
                                              stored metadata fields (e.g., "type", "title", "source_jira_ticket").
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
    """Updates the document text and/or metadata of an existing test case in the vector database.

    Args:
        test_case_id (str): The unique identifier of the test case to update.
        new_test_case_document (Optional[str]): The new document text for the test case. If None, text is not updated.
        new_metadata_json (Optional[str]): A JSON string representing the *complete* new metadata object.
                                           If provided, it *replaces* the existing metadata entirely.
                                           The structure should include keys like "type" (must be "TestCase"),
                                           "title", "source_jira_ticket", "classification" (must be one of ALLOWED_CLASSIFICATIONS,
                                           defaults to DEFAULT_CLASSIFICATION if omitted), and "test_steps".
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
    # Get current time once for consistency
    current_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

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

            # Validate classification if present in the new metadata, else set default
            new_classification = parsed_new_metadata.get('classification')
            if new_classification is not None:
                if new_classification not in ALLOWED_CLASSIFICATIONS:
                    return {
                        "status": "error",
                        "error_message": f"Invalid classification '{new_classification}'. Must be one of {ALLOWED_CLASSIFICATIONS}."
                    }
            else:
                # If new_metadata_json is provided but classification is missing, set default
                parsed_new_metadata['classification'] = DEFAULT_CLASSIFICATION

            updates_to_make['metadatas'] = [parsed_new_metadata]
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for new metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}
        # Add change_date to the new metadata if it's being updated
        parsed_new_metadata['change_date'] = current_time_iso
        updates_to_make['metadatas'] = [parsed_new_metadata]

    # If only text is updated, we still need to update the change_date in the existing metadata
    if 'documents' in updates_to_make and 'metadatas' not in updates_to_make:
         existing_metadata['change_date'] = current_time_iso
         updates_to_make['metadatas'] = [existing_metadata] # Add metadata update to the list of updates

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


def get_all_test_cases() -> Dict:
    """Retrieves all test cases stored in the vector database.

    Returns:
        Dict: Status dictionary with results or error message. Results include IDs, documents, and metadata for all test cases.
    """
    try:
        results = collection.get(
            where={"type": "TestCase"}, # Filter specifically for test cases
            include=['documents', 'metadatas'] # Specify what data to return
        )

        ids = results.get('ids', [])
        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])

        if not ids:
            return {"status": "success", "report": "No test cases found in the database."}

        report_lines = [f"Found {len(ids)} test case(s):"]
        for i in range(len(ids)):
            report_lines.append(
                f"  - ID: {ids[i]}\n"
                f"    Document: {documents[i]}\n" # Use Document for consistency with TC schema
                f"    Metadata: {metadatas[i]}"
            )

        return {"status": "success", "report": "\n".join(report_lines)}

    except Exception as e:
        return {"status": "error", "error_message": f"Failed to retrieve all test cases: {e}"}


__all__ = [
    'add_test_case',
    'retrieve_similar_test_cases',
    'update_test_case',
    'delete_test_case',
    'get_all_test_cases'
]
