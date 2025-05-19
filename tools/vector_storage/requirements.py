"""
Functions for managing software requirements in the vector database.
"""
import json
import datetime
from typing import List, Dict, Optional

# Import shared components from the package initializer
from . import client, collection, _get_next_id
from ..jira_tools import create_jira_issue # Import for creating Jira issues

# Define allowed implementation statuses
ALLOWED_IMPLEMENTATION_STATUSES = {"Open", "In Progress", "Done", "Deferred", "Blocked", "Unknown"}
DEFAULT_IMPLEMENTATION_STATUS = "Open"

# Define allowed requirement classifications
ALLOWED_CLASSIFICATIONS = {"Functional", "Non-Functional", "Business"}
DEFAULT_CLASSIFICATION = "Functional"

# --- Requirement Functions ---
def add_requirement(requirement_text: str, metadata_json: Optional[str] = None) -> Dict:
    """Adds a new software requirement to the vector database with an automatically generated ID.

    Args:
        requirement_text (str): The full text of the requirement.
        metadata_json (Optional[str]): Optional JSON string representing metadata associated
                                       with the requirement. Based on requirement_schema.json,
                                       this JSON object can contain keys like:
                                       - "type" (str): Must be "Requirement".
                                       - "source_jira_ticket" (str): The originating Jira ticket key.
                                       - "implementation_status" (str): Must be one of ALLOWED_IMPLEMENTATION_STATUSES.
                                                                        Defaults to "Open" if not provided.
                                       - "classification" (str): Must be one of ALLOWED_CLASSIFICATIONS.
                                                                 Defaults to "Functional" if not provided.
                                       Example: '{ "type": "Requirement", "source_jira_ticket": "PROJECT-123", "implementation_status": "Open", "classification": "Functional" }'

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

    # Validate and set implementation_status
    current_status = parsed_metadata.get('implementation_status')
    if current_status is not None:
        if current_status not in ALLOWED_IMPLEMENTATION_STATUSES:
            return {
                "status": "error",
                "error_message": f"Invalid implementation_status '{current_status}'. Must be one of {ALLOWED_IMPLEMENTATION_STATUSES}."
            }
    else:
        parsed_metadata['implementation_status'] = DEFAULT_IMPLEMENTATION_STATUS

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
                                              to filter results based on the stored metadata fields
                                              (e.g., "type", "source_jira_ticket", "implementation_status").
                                              Example: To find requirements from a specific ticket:
                                              '{"type": "Requirement", "source_jira_ticket": "PROJECT-123", "implementation_status": "Open"}'
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
                                           - If 'implementation_status' is included, it must be one of ALLOWED_IMPLEMENTATION_STATUSES.
                                           - If 'classification' is included, it must be one of ALLOWED_CLASSIFICATIONS.
                                             If 'classification' is omitted, it defaults to DEFAULT_CLASSIFICATION.
                                           The structure of the metadata must be like this:
                                            {
                                                "type": "Requirement",
                                                "source_jira_ticket": "PR-123",
                                                "implementation_status": "In Progress",
                                                "classification": "Functional"
                                                # Add other relevant metadata fields here
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

    final_metadata = existing_metadata # Start with existing metadata
    if new_metadata_json is not None:
        try:
            parsed_new_metadata = json.loads(new_metadata_json)
            if not isinstance(parsed_new_metadata, dict):
                raise ValueError("New metadata must be a JSON object (dictionary).")

            # Validate implementation_status if present in the new metadata
            new_status = parsed_new_metadata.get('implementation_status')
            if new_status is not None and new_status not in ALLOWED_IMPLEMENTATION_STATUSES:
                return {
                    "status": "error",
                    "error_message": f"Invalid implementation_status '{new_status}'. Must be one of {ALLOWED_IMPLEMENTATION_STATUSES}."
                }

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
            
            # Replace entire metadata as per function contract
            final_metadata = parsed_new_metadata

            # Ensure the type remains correct or is defaulted
            if 'type' not in final_metadata: # Check final_metadata after potential replacement
                 print(f"Warning: Updating metadata for '{requirement_id}' without a 'type' field. Setting to 'Requirement'.")
                 final_metadata['type'] = 'Requirement'
            elif final_metadata.get('type') != 'Requirement':
                 print(f"Warning: Updating metadata for '{requirement_id}' with a type other than 'Requirement' ('{final_metadata.get('type')}').")
        
        except json.JSONDecodeError:
            return {"status": "error", "error_message": "Invalid JSON format provided for new metadata."}
        except ValueError as ve: # Catches the "New metadata must be a JSON object"
             return {"status": "error", "error_message": str(ve)}

    # Add/Update the change date before upserting
    final_metadata['change_date'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 3. Use upsert to perform the update
    try:
        collection.upsert(
            ids=[requirement_id],
            documents=[final_document_text], 
            metadatas=[final_metadata]      
        )
        update_fields = []
        if new_requirement_text is not None: update_fields.append("text")
        if new_metadata_json is not None: update_fields.append("metadata")
        return {"status": "success", "report": f"Requirement '{requirement_id}' updated successfully ({', '.join(update_fields)})."}
    except Exception as e:
        # Catch potential ChromaDB errors or other issues during upsert
        return {"status": "error", "error_message": f"Failed to upsert requirement '{requirement_id}': {e}"}


def delete_requirement(requirement_ids: List[str]) -> Dict:
    """Deletes one or more requirements from the vector database by their IDs.

    Args:
        requirement_ids (List[str]): A list of unique identifiers of the requirements to delete.

    Returns:
        Dict: Status dictionary indicating success or error.
    """
    if not requirement_ids:
        return {"status": "error", "error_message": "Requirement ID list cannot be empty."}
    
    valid_ids = [req_id for req_id in requirement_ids if req_id and isinstance(req_id, str) and req_id.strip()]
    
    if not valid_ids:
        return {"status": "error", "error_message": "No valid requirement IDs provided in the list. Ensure IDs are non-empty strings."}
    
    ignored_ids_count = len(requirement_ids) - len(valid_ids)
    if ignored_ids_count > 0:
        print(f"Warning: {ignored_ids_count} invalid or empty ID(s) were provided and will be ignored. Attempting to delete: {valid_ids}")

    try:
        collection.delete(ids=valid_ids)
        if len(valid_ids) == 1:
            return {"status": "success", "report": f"Requirement '{valid_ids[0]}' deleted successfully."}
        return {"status": "success", "report": f"Successfully deleted {len(valid_ids)} requirement(s): {', '.join(valid_ids)}."}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to delete requirements. IDs attempted: {', '.join(valid_ids)}. Error: {e}"}


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
    'generate_jira_issues_for_requirement',
]

def generate_jira_issues_for_requirement(
    requirement_id: str,
    project_key: str,
    issue_type_name: str,
    components: Optional[List[str]] = None,
    num_context_requirements: int = 3
) -> Dict:
    """
    Retrieves a requirement, gets context from similar requirements,
    splits the requirement into actionable Jira issues, creates them,
    and updates the original requirement with links to these issues.

    Args:
        requirement_id (str): The ID of the requirement to process.
        project_key (str): The Jira project key where issues will be created.
        issue_type_name (str): The name of the Jira issue type (e.g., "Story", "Task").
        components (Optional[List[str]]): Optional list of component names for the Jira issues.
        num_context_requirements (int): Number of similar requirements to fetch for context.

    Returns:
        Dict: Status dictionary with a report, including created Jira issue keys and any errors.
    """
    if not all([requirement_id, project_key, issue_type_name]):
        return {"status": "error", "error_message": "Requirement ID, project key, and issue type name are required."}

    # 1. Retrieve the requirement
    try:
        existing_req_data = collection.get(ids=[requirement_id], include=['documents', 'metadatas'])
        if not existing_req_data or not existing_req_data.get('ids') or not existing_req_data.get('documents'):
            return {"status": "error", "error_message": f"Requirement '{requirement_id}' not found or has no document."}
        
        original_requirement_text = existing_req_data['documents'][0]
        original_metadata = existing_req_data['metadatas'][0] if existing_req_data.get('metadatas') else {}

        if original_metadata.get('type') != 'Requirement':
            return {"status": "error", "error_message": f"Item '{requirement_id}' is not of type 'Requirement'."}

    except Exception as e:
        return {"status": "error", "error_message": f"Error retrieving requirement '{requirement_id}': {e}"}

    # 2. Retrieve similar requirements for context
    similar_reqs_report = "No similar requirements found or an error occurred."
    try:
        similar_results = retrieve_similar_requirements(
            query_text=original_requirement_text,
            n_results=num_context_requirements
        )
        if similar_results.get("status") == "success" and "report" in similar_results:
            # Extract relevant parts of the report for conciseness in Jira description
            report_lines = similar_results["report"].splitlines()
            if len(report_lines) > 1: # Has actual results beyond "Found X similar..."
                 # Limit the amount of context to avoid overly long descriptions
                similar_reqs_report = "\n".join(report_lines[:1 + num_context_requirements * 4]) # Header + N * (ID, Text, Meta, Blank)
            else:
                similar_reqs_report = similar_results["report"]

    except Exception as e:
        similar_reqs_report = f"Error retrieving similar requirements: {e}"

    # 3. Split requirement text into actionable tasks (simple line-based split)
    actionable_tasks_text = [line.strip() for line in original_requirement_text.splitlines() if line.strip()]
    if not actionable_tasks_text:
        actionable_tasks_text = [original_requirement_text] # Use full text if no lines

    created_issue_keys = []
    error_messages = []
    report_details = []

    # 4. Create Jira issues for each task
    for i, task_text in enumerate(actionable_tasks_text):
        summary = f"{requirement_id} - Part {i+1}: {task_text[:100]}" # Truncate summary if too long
        description = (
            f"This task is derived from requirement: {requirement_id}\n"
            f"Original requirement text snippet for this task: \"{task_text}\"\n\n"
            f"Full original requirement text:\n---\n{original_requirement_text}\n---\n\n"
            f"Context from similar requirements:\n---\n{similar_reqs_report}\n---"
        )

        jira_result = create_jira_issue(
            project_key=project_key,
            summary=summary,
            description=description,
            issue_type_name=issue_type_name,
            components=components
        )

        if jira_result.get("status") == "success" and jira_result.get("issue_key"):
            issue_key = jira_result["issue_key"]
            created_issue_keys.append(issue_key)
            report_details.append(f"Successfully created Jira issue '{issue_key}' for task: \"{task_text[:50]}...\"")
        else:
            err_msg = jira_result.get("error_message", f"Unknown error creating Jira issue for task: \"{task_text[:50]}...\"")
            error_messages.append(err_msg)
            report_details.append(f"Failed to create Jira issue for task: \"{task_text[:50]}...\". Error: {err_msg}")

    # 5. Update original requirement metadata with links to Jira issues
    if created_issue_keys:
        updated_metadata = original_metadata.copy()
        if 'generated_jira_issues' not in updated_metadata:
            updated_metadata['generated_jira_issues'] = []
        
        # Add only new, unique keys
        for key in created_issue_keys:
            if key not in updated_metadata['generated_jira_issues']:
                 updated_metadata['generated_jira_issues'].append(key)
        
        updated_metadata['change_date'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        try:
            collection.upsert(
                ids=[requirement_id],
                metadatas=[updated_metadata]
                # Note: We are only updating metadata here. Document remains the same.
            )
            report_details.append(f"Successfully updated requirement '{requirement_id}' with generated Jira issue keys: {created_issue_keys}")
        except Exception as e:
            err_msg = f"Failed to update requirement '{requirement_id}' with Jira issue links: {e}"
            error_messages.append(err_msg)
            report_details.append(err_msg)

    final_status = "success" if created_issue_keys and not error_messages else "partial_success" if created_issue_keys else "error"
    if not created_issue_keys and not error_messages: # No tasks to create issues for
        final_status = "success" # Or "no_action_needed"
        report_details.append("No actionable tasks found in the requirement to create Jira issues for.")


    return {
        "status": final_status,
        "report": "\n".join(report_details),
        "created_issue_keys": created_issue_keys,
        "errors": error_messages
    }
