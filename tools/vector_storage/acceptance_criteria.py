"""
Functions for managing acceptance criteria in the vector database.
"""
import json
from typing import List, Dict, Optional

# Import shared components from the package initializer
from . import client, collection, _get_next_id

# --- Acceptance Criteria Functions ---

def add_acceptance_criterion(criterion_text: str, metadata_json: Optional[str] = None) -> Dict:
    """Adds a new acceptance criterion to the vector database with an automatically generated ID.

    Args:
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
        Dict: Status dictionary indicating success or error, including the generated criterion ID.
    """
    if not criterion_text:
        return {"status": "error", "error_message": "Criterion text cannot be empty."}

    # Generate the next criterion ID
    try:
        new_criterion_id = _get_next_id("AC-")
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to generate criterion ID: {e}"}

    parsed_metadata = {}
    if metadata_json:
        try:
            parsed_metadata = json.loads(metadata_json)
            if not isinstance(parsed_metadata, dict):
                raise ValueError("Metadata must be a JSON object (dictionary).")
            # Ensure type is set if provided
            if 'type' not in parsed_metadata:
                 # Use the generated ID in the warning message
                 print(f"Warning: Adding acceptance criterion '{new_criterion_id}' without explicit 'type' metadata. Defaulting to 'AcceptanceCriterion'.")
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    # Automatically add type if not present? Consider implications.
    if 'type' not in parsed_metadata:
        parsed_metadata['type'] = 'AcceptanceCriterion' # Enforce type for consistency

    try:
        # Use the generated ID in the upsert call
        collection.upsert(
            ids=[new_criterion_id],
            documents=[criterion_text],
            metadatas=[parsed_metadata]
        )
        # Use the generated ID in the success message and return value
        return {"status": "success", "report": f"Acceptance Criterion '{new_criterion_id}' added successfully.", "criterion_id": new_criterion_id}
    except Exception as e:
        # Use the generated ID in the error message
        return {"status": "error", "error_message": f"Failed to add criterion '{new_criterion_id}': {e}"}


def retrieve_similar_acceptance_criteria(query_text: str, n_results: int = 3, filter_metadata_json: Optional[str] = None) -> Dict:
    """Retrieves from the vector database acceptance criteria semantically similar to the query text.

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
    """Updates the text and/or metadata of an existing acceptance criterion in the vector database.

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


def get_all_acceptance_criteria() -> Dict:
    """Retrieves all acceptance criteria stored in the vector database.

    Returns:
        Dict: Status dictionary with results or error message. Results include IDs, text, and metadata for all acceptance criteria.
    """
    try:
        results = collection.get(
            where={"type": "AcceptanceCriterion"}, # Filter specifically for acceptance criteria
            include=['documents', 'metadatas'] # Specify what data to return
        )

        ids = results.get('ids', [])
        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])

        if not ids:
            return {"status": "success", "report": "No acceptance criteria found in the database."}

        report_lines = [f"Found {len(ids)} acceptance criteria(s):"]
        for i in range(len(ids)):
            report_lines.append(
                f"  - ID: {ids[i]}\n"
                f"    Text: {documents[i]}\n"
                f"    Metadata: {metadatas[i]}"
            )

        return {"status": "success", "report": "\n".join(report_lines)}

    except Exception as e:
        return {"status": "error", "error_message": f"Failed to retrieve all acceptance criteria: {e}"}


__all__ = [
    'add_acceptance_criterion',
    'retrieve_similar_acceptance_criteria',
    'delete_acceptance_criterion',
    'update_acceptance_criterion',
    'get_all_acceptance_criteria',
]
