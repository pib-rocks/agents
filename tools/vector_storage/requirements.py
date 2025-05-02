"""
Functions for managing software requirements in the vector database.
"""
import json
import datetime
from typing import List, Dict, Optional

# Import shared components from the package initializer
from . import client, collection, _get_next_id

# --- Requirement Functions ---
def add_requirement(requirement_text: str, metadata_json: Optional[str] = None) -> Dict:
    """Adds a new software requirement to the vector database with an automatically generated ID.

    Args:
        requirement_text (str): The full text of the requirement.
        metadata_json (Optional[str]): Optional JSON string representing metadata associated
                                       with the requirement. Based on requirement_schema.json,
                                       this JSON object should contain the following keys:
                                       - "type" (str): Must be "Requirement".
                                       - "source_jira_ticket" (str): The originating Jira ticket key (e.g., "PROJECT-123").
                                       - "acceptance_criteria_ids" (List[str]): A list of IDs for associated acceptance criteria (e.g., ["AC-1", "AC-2"]).
                                       Example: '{ "type": "Requirement", "source_jira_ticket": "PROJECT-123", "acceptance_criteria_ids": ["AC-1"] }'

    Returns:
        Dict: Status dictionary indicating success or error, including the generated requirement ID.
    """
    if not requirement_text:
        return {"status": "error", "error_message": "Requirement text cannot be empty."}

    # Generate the next requirement ID
    try:
        new_requirement_id = _get_next_id("REQ-")
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to generate requirement ID: {e}"}


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

    # Ensure 'type' is set in metadata
    parsed_metadata['type'] = 'Requirement'
    # Add the change date
    parsed_metadata['change_date'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        # Use upsert with the generated ID
        collection.upsert(
            ids=[new_requirement_id],
            documents=[requirement_text],
            metadatas=[parsed_metadata] # Chroma expects a list for each argument
        )
        return {"status": "success", "report": f"Requirement '{new_requirement_id}' added successfully.", "requirement_id": new_requirement_id}
    except Exception as e:
        # Catch potential ChromaDB errors or other issues
        return {"status": "error", "error_message": f"Failed to add requirement '{new_requirement_id}': {e}"}


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


def update_requirement(requirement_id: str, new_requirement_text: Optional[str] = None, new_metadata_json: Optional[str] = None) -> Dict:
    """Updates the text and/or metadata of an existing requirement using upsert for metadata compatibility.

    Args:
        requirement_id (str): The unique identifier of the requirement to update.
        new_requirement_text (Optional[str]): The new text for the requirement. If None, text is not updated.
        new_metadata_json (Optional[str]): A JSON string representing the *complete* new metadata object.
                                           If provided, it *replaces* the existing metadata entirely.
                                           The structure of the metadata must be like this:

                                            {
                                            "metadata": {
                                                "type": "functional", # type can only be "functional" or "non-functional"
                                                "source_jira_ticket": "PR-123",
                                                "acceptance_criteria_ids": [
                                                    "AC-1",
                                                    "AC-2"
                                                ]}
                                            }


    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not requirement_id:
        return {"status": "error", "error_message": "Requirement ID cannot be empty."}
    if new_requirement_text is None and new_metadata_json is None:
        return {"status": "error", "error_message": "Must provide either new text or new metadata to update."}

    # 1. Check if the requirement exists, is a Requirement, and get current data
    try:
        # Include documents to get current text if only metadata is updated
        existing = collection.get(ids=[requirement_id], include=['metadatas', 'documents'])
        if not existing or not existing.get('ids'):
            return {"status": "error", "error_message": f"Requirement '{requirement_id}' not found."}

        existing_metadata = existing['metadatas'][0] if existing.get('metadatas') else {}
        existing_document = existing['documents'][0] if existing.get('documents') else None

        if existing_metadata.get('type') != 'Requirement':
             return {"status": "error", "error_message": f"Item '{requirement_id}' found, but it is not a Requirement (type: {existing_metadata.get('type')}). Update aborted."}
        if existing_document is None and new_requirement_text is None:
             # Should not happen if item exists, but safeguard
             return {"status": "error", "error_message": f"Could not retrieve existing document text for requirement '{requirement_id}' and no new text provided."}

    except Exception as e:
        return {"status": "error", "error_message": f"Error retrieving requirement '{requirement_id}': {e}"}

    # 2. Determine the final document text and metadata
    final_document_text = existing_document
    if new_requirement_text is not None:
        if not new_requirement_text.strip():
             return {"status": "error", "error_message": "New requirement text cannot be empty."}
        final_document_text = new_requirement_text

    final_metadata = existing_metadata
    if new_metadata_json is not None:
        try:
            parsed_new_metadata = json.loads(new_metadata_json)
            if not isinstance(parsed_new_metadata, dict):
                raise ValueError("New metadata must be a JSON object (dictionary).")
            # Ensure the type remains correct
            if 'type' not in parsed_new_metadata:
                 print(f"Warning: Updating metadata for '{requirement_id}' without a 'type' field. Setting to 'Requirement'.")
                 parsed_new_metadata['type'] = 'Requirement'
            elif parsed_new_metadata.get('type') != 'Requirement':
                 print(f"Warning: Updating metadata for '{requirement_id}' with a type other than 'Requirement' ('{parsed_new_metadata.get('type')}').")
            # Replace entire metadata
            final_metadata = parsed_new_metadata
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for new metadata."}
        except ValueError as ve:
             return {"status": "error", "error_message": str(ve)}

    # Add/Update the change date before upserting
    final_metadata['change_date'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 3. Use upsert to perform the update
    try:
        collection.upsert(
            ids=[requirement_id],
            documents=[final_document_text], # Provide the final text
            metadatas=[final_metadata]      # Provide the final metadata
        )
        update_fields = []
        if new_requirement_text is not None: update_fields.append("text")
        if new_metadata_json is not None: update_fields.append("metadata")
        return {"status": "success", "report": f"Requirement '{requirement_id}' updated successfully ({', '.join(update_fields)})."}
    except Exception as e:
        # Catch potential ChromaDB errors or other issues during upsert
        return {"status": "error", "error_message": f"Failed to upsert requirement '{requirement_id}': {e}"}


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


def get_all_requirements() -> Dict:
    """Retrieves all requirements stored in the vector database.

    Returns:
        Dict: Status dictionary with results or error message. Results include IDs, text, and metadata for all requirements.
    """
    try:
        results = collection.get(
            where={"type": "Requirement"}, # Filter specifically for requirements
            include=['documents', 'metadatas'] # Specify what data to return
        )

        ids = results.get('ids', [])
        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])

        if not ids:
            return {"status": "success", "report": "No requirements found in the database."}

        report_lines = [f"Found {len(ids)} requirement(s):"]
        for i in range(len(ids)):
            report_lines.append(
                f"  - ID: {ids[i]}\n"
                f"    Text: {documents[i]}\n"
                f"    Metadata: {metadatas[i]}"
            )

        return {"status": "success", "report": "\n".join(report_lines)}

    except Exception as e:
        return {"status": "error", "error_message": f"Failed to retrieve all requirements: {e}"}


__all__ = [
    'add_requirement',
    'retrieve_similar_requirements',
    'update_requirement',
    'delete_requirement',
    'get_all_requirements',
]
