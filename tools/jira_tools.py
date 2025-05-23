import os
import requests
import json
from typing import Optional, List
from datetime import datetime
import pytz # For timezone handling
import webbrowser # Import the webbrowser module
# Note: 're' import removed previously

# --- Constants ---
SUBTASK_ISSUE_TYPE_ID = "10003" # Hardcoded Sub-task Issue Type ID
CUSTOM_FIELD_CATEGORY_ID = "customfield_10035" # ID for the Category custom field
# Renamed constant for broader applicability
ALLOWED_COMPONENTS = ["cerebra", "pib-backend", "pib-blockly"]

# --- General Issue Creation ---

def create_jira_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type_name: str,
    components: Optional[List[str]] = None
) -> dict:
    """Creates a new Jira issue (e.g., Story, Task).

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables.

    Args:
        project_key (str): The key of the project where the issue will be created (e.g., 'PROJ').
        summary (str): The summary (title) for the new issue.
        description (str): The description for the new issue (plain text, will be converted to ADF).
        issue_type_name (str): The name of the issue type (e.g., 'Story', 'Task', 'Bug').
        components (Optional[List[str]]): A list of component names to set.
            Must be from the allowed list.

    Returns:
        dict: status and result (new issue key) or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "error_message": "Atlassian instance configuration (URL, email, API key) missing."}
    if not all([project_key, summary, description, issue_type_name]):
        return {"status": "error", "error_message": "Project key, summary, description, and issue type name are required."}

    # Validate components if provided
    if components:
        if not isinstance(components, list):
            return {"status": "error", "error_message": "Components must be provided as a list of strings."}
        invalid_components = [c for c in components if c not in ALLOWED_COMPONENTS]
        if invalid_components:
            return {
                "status": "error",
                "error_message": f"Invalid component(s): {', '.join(invalid_components)}. Allowed components are: {', '.join(ALLOWED_COMPONENTS)}."
            }

    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    payload_fields = {
        "project": {"key": project_key},
        "summary": summary,
        "description": { # Basic ADF format for description
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}],
                }
            ],
        },
        "issuetype": {"name": issue_type_name},
    }

    if components:
        payload_fields["components"] = [{"name": c} for c in components]

    payload = {"fields": payload_fields}

    try:
        response = requests.post(
            api_url, headers=headers, auth=auth, data=json.dumps(payload), timeout=20
        )
        response.raise_for_status()

        new_issue_data = response.json()
        new_issue_key = new_issue_data.get("key")
        return {
            "status": "success",
            "report": f"Issue '{new_issue_key}' created successfully in project '{project_key}'.",
            "issue_key": new_issue_key
        }
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error creating issue: {http_err}"
        try:
            error_details = response.json()
            if "errorMessages" in error_details: error_message += f" Details: {'; '.join(error_details['errorMessages'])}"
            if "errors" in error_details: error_message += f" Field Errors: {json.dumps(error_details['errors'])}"
        except json.JSONDecodeError: pass
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "error_message": f"Error creating issue: {req_err}"}

# --- Sub-task Management Tools ---

def create_jira_subtask(
    parent_issue_key: str,
    summary: str,
    components: Optional[List[str]] = None
) -> dict:
    """Creates a new sub-task for a given parent issue using the default sub-task type ID.

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables.
    Uses the hardcoded SUBTASK_ISSUE_TYPE_ID ('10003').
    Optionally sets components if provided and valid.

    Args:
        parent_issue_key (str): The key of the parent issue (e.g., 'PROJ-123').
        summary (str): The summary (title) for the new sub-task.
        components (Optional[List[str]]): A list of component names to set.
            Must be from the allowed list: ['cerebra', 'pib-backend', 'pib-blockly'].

    Returns:
        dict: status and result (new sub-task key) or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "error_message": "Atlassian instance configuration (URL, email, API key) missing."}
    if not parent_issue_key or not summary:
        return {"status": "error", "error_message": "Parent key and summary are required."}

    # Validate components if provided (using the renamed constant)
    if components:
        invalid_components = [c for c in components if c not in ALLOWED_COMPONENTS]
        if invalid_components:
            return {
                "status": "error",
                "error_message": f"Invalid component(s): {', '.join(invalid_components)}. Allowed components are: {', '.join(ALLOWED_COMPONENTS)}."
            }

    # Need project key - fetch parent issue details to get it
    parent_details_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{parent_issue_key}?fields=project"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}
    project_key = None
    try:
        parent_response = requests.get(parent_details_url, headers=headers, auth=auth, timeout=10)
        parent_response.raise_for_status()
        project_key = parent_response.json().get("fields", {}).get("project", {}).get("key")
        if not project_key:
             raise ValueError("Could not extract project key from parent issue.")
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": f"Failed to fetch parent issue details to get project key: {e}"}
    except ValueError as e:
         return {"status": "error", "error_message": str(e)}


    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    payload_fields = {
        "project": {"key": project_key},
        "parent": {"key": parent_issue_key},
        "summary": summary,
        "issuetype": {"id": SUBTASK_ISSUE_TYPE_ID}, # Use hardcoded ID
        # Add other required fields if necessary for your project's sub-task creation screen
        # "description": { ... } # Optional description
    }

    # Add components to payload if valid ones were provided
    if components:
        payload_fields["components"] = [{"name": c} for c in components]

    payload = {"fields": payload_fields}

    try:
        response = requests.post(
            api_url, headers=headers, auth=auth, data=json.dumps(payload), timeout=20
        )
        response.raise_for_status()

        new_issue_data = response.json()
        new_issue_key = new_issue_data.get("key")
        return {
            "status": "success",
            "report": f"Sub-task '{new_issue_key}' created successfully for parent '{parent_issue_key}'.",
            "subtask_key": new_issue_key
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error creating sub-task: {http_err}"
        try:
            error_details = response.json()
            if "errorMessages" in error_details: error_message += f" Details: {'; '.join(error_details['errorMessages'])}"
            if "errors" in error_details: error_message += f" Field Errors: {json.dumps(error_details['errors'])}"
        except json.JSONDecodeError: pass
        # Add specific error checks if needed (e.g., invalid project, issue type, permissions)
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "error_message": f"Error creating sub-task: {req_err}"}


def get_jira_subtasks(parent_issue_key: str) -> dict:
    """Retrieves sub-tasks for a specified parent Jira issue.

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment variables.

    Args:
        parent_issue_key (str): The Jira issue ID or key of the parent (e.g., 'PROJ-123').

    Returns:
        dict: status and result (report listing sub-tasks) or error message.
              Each sub-task includes its key, summary, and status.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "error_message": "Atlassian instance configuration (URL, email, API key) missing."}

    # Fetch parent issue details including the subtasks field
    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{parent_issue_key}?fields=subtasks"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(api_url, headers=headers, auth=auth, timeout=15)
        response.raise_for_status()

        data = response.json()
        subtasks = data.get("fields", {}).get("subtasks", [])

        if not subtasks:
            return {"status": "success", "report": f"No sub-tasks found for issue '{parent_issue_key}'."}

        report_lines = [f"Sub-tasks for issue {parent_issue_key}:"]
        for task in subtasks:
            task_key = task.get("key", "N/A")
            summary = task.get("fields", {}).get("summary", "N/A")
            status = task.get("fields", {}).get("status", {}).get("name", "N/A")
            report_lines.append(f"  - Key: {task_key}, Status: {status}, Summary: {summary}")

        return {"status": "success", "report": "\n".join(report_lines)}

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401: error_message = "Jira authentication failed."
        elif response.status_code == 403: error_message = f"Permission denied for issue '{parent_issue_key}'."
        elif response.status_code == 404: error_message = f"Jira issue '{parent_issue_key}' not found."
        else: error_message = f"HTTP error getting sub-tasks: {http_err}"
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "error_message": f"Error getting sub-tasks: {req_err}"}


def delete_jira_issue(issue_key: str) -> dict:
    """Deletes a Jira issue (including sub-tasks). Use with extreme caution!

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment variables.

    Args:
        issue_key (str): The Jira issue ID or key to delete (e.g., 'PROJ-123', 'SUB-456').

    Returns:
        dict: status and result message or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "error_message": "Atlassian instance configuration (URL, email, API key) missing."}
    if not issue_key:
        return {"status": "error", "error_message": "Issue key cannot be empty."}

    # Add a confirmation step here? Or rely on agent confirmation?
    # For now, proceed directly based on agent call.

    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{issue_key}"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}

    try:
        response = requests.delete(api_url, headers=headers, auth=auth, timeout=20)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        # Successful deletion usually returns 204 No Content
        return {
            "status": "success",
            "report": f"Jira issue '{issue_key}' deleted successfully.",
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error deleting issue: {http_err}"
        try:
            error_details = response.json()
            if "errorMessages" in error_details: error_message += f" Details: {'; '.join(error_details['errorMessages'])}"
            if "errors" in error_details: error_message += f" Field Errors: {json.dumps(error_details['errors'])}"
        except json.JSONDecodeError: pass

        if response.status_code == 401: error_message = "Jira authentication failed."
        elif response.status_code == 403: error_message = f"Permission denied to delete issue '{issue_key}'."
        elif response.status_code == 404: error_message = f"Jira issue '{issue_key}' not found."
        # Jira might return 400 if issue has sub-tasks and deleteSubtasks=false (default)
        # Or other validation errors.
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "error_message": f"Error deleting issue: {req_err}"}

# --- End of Sub-task Management Tools ---


def show_jira_issue(issue_key: str) -> dict:
    """Opens the specified Jira issue in a web browser.

    Args:
        issue_key (str): The Jira issue key (e.g., 'PROJ-123').

    Returns:
        dict: status and result message or error message.
    """
    if not issue_key:
        return {"status": "error", "error_message": "Issue key cannot be empty."}

    # Use the fixed base URL provided
    base_url = "https://pib-rocks.atlassian.net/browse/"
    issue_url = f"{base_url}{issue_key}"

    try:
        opened = webbrowser.open(issue_url, new=2) # new=2: open in new tab if possible
        if opened:
            return {"status": "success", "report": f"Attempted to open Jira issue '{issue_key}' in the browser."}
        else:
            # Provide the URL in the report if opening failed, so the user can copy it
            return {"status": "warning", "report": f"Failed to automatically open browser for issue '{issue_key}'. You can manually open: {issue_url}"}
    except Exception as e:
        return {"status": "error", "error_message": f"An error occurred while trying to open the browser: {e}"}

def _parse_adf_text(adf_node: dict) -> str:
    """Recursively extracts plain text from an ADF node."""
    text_content = []
    if adf_node.get("type") == "text":
        text_content.append(adf_node.get("text", ""))
    if "content" in adf_node and isinstance(adf_node["content"], list):
        for child_node in adf_node["content"]:
            text_content.append(_parse_adf_text(child_node))
    return "".join(text_content)

def update_jira_issue(
    issue_id: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    assignee_account_id: Optional[str] = None,
    components: Optional[List[str]] = None,
    category: Optional[str] = None # Added category parameter
) -> dict:
    """Updates fields (summary, description, assignee, components, category) for a specified Jira issue.

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment
    variables to be set.

    Args:
        issue_id (str): The Jira issue ID or key (e.g., 'PROJ-123').
        summary (Optional[str]): The new summary for the issue. Optional.
        description (Optional[str]): The new description text for the issue.
            Will be converted to basic ADF format. Optional.
        assignee_account_id (Optional[str]): The Atlassian Account ID of the new
            assignee. Set to None to leave unassigned or unchanged if already
            assigned. Optional.
        components (Optional[List[str]]): A list of component names to set.
            Must be from the allowed list: ['cerebra', 'pib-backend', 'pib-blockly'].
            Provide an empty list `[]` to clear components. Optional.
        category (Optional[str]): The value to set for the Category custom field
            (customfield_10035). Optional.

    Returns:
        dict: status and result message or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {
            "status": "error",
            "error_message": (
                "Atlassian instance configuration (URL, email, API key)" 
                " missing in environment variables."
            ),
        }

    # Check if at least one field is provided for update
    if not any([summary, description, assignee_account_id is not None, components is not None, category is not None]):
         return {
            "status": "error",
            "error_message": "No fields provided to update (summary, description, assignee, components, or category).",
        }

    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{issue_id}"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    payload_fields = {}
    if summary:
        payload_fields["summary"] = summary
    if description:
        # Convert plain text description to basic ADF
        payload_fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}],
                }
            ],
        }
    if assignee_account_id is not None: # Allow explicitly setting assignee
         # Use {'id': None} to unassign, or {'id': 'account_id'} to assign
        payload_fields["assignee"] = {"id": assignee_account_id} if assignee_account_id else None
    # Handle components update
    if components is not None:
        if not isinstance(components, list):
             return {"status": "error", "error_message": "Components must be provided as a list of strings."}
        # Validate non-empty list against allowed components
        if components: # Only validate if the list is not empty
            invalid_components = [c for c in components if c not in ALLOWED_COMPONENTS]
            if invalid_components:
                return {
                    "status": "error",
                    "error_message": f"Invalid component(s): {', '.join(invalid_components)}. Allowed components are: {', '.join(ALLOWED_COMPONENTS)}."
                }
            # Format for Jira API [{ "name": "comp1" }, { "name": "comp2" }]
            payload_fields["components"] = [{"name": c} for c in components]
        else:
            # Set components to empty list to clear them
            payload_fields["components"] = []
    # Handle category update (assuming value is provided directly)
    if category is not None:
         # For select list (single choice) custom fields, the format is usually {"value": "Option Name"}
         # If category is an empty string, we might want to clear the field (set to None or omit)
         if category:
             payload_fields[CUSTOM_FIELD_CATEGORY_ID] = {"value": category}
         else:
             # To clear a single-select custom field, set it to null
             payload_fields[CUSTOM_FIELD_CATEGORY_ID] = None


    payload = {"fields": payload_fields}

    try:
        response = requests.put(
            api_url, headers=headers, auth=auth, data=json.dumps(payload), timeout=20
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Jira PUT request returns 204 No Content on success
        return {
            "status": "success",
            "report": f"Jira issue '{issue_id}' updated successfully.",
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        try:
            # Try to get more specific error details from Jira response
            error_details = response.json()
            if "errorMessages" in error_details:
                 error_message += f" Details: {'; '.join(error_details['errorMessages'])}"
            if "errors" in error_details:
                 error_message += f" Field Errors: {json.dumps(error_details['errors'])}"
        except json.JSONDecodeError:
            pass # Ignore if response is not JSON

        if response.status_code == 400:
             error_message = f"Bad request updating issue '{issue_id}'. Check fields/values. Details: {error_message}"
        elif response.status_code == 401:
            error_message = "Jira authentication failed. Check email/API key."
        elif response.status_code == 403:
            error_message = f"Jira permission denied for updating issue '{issue_id}'."
        elif response.status_code == 404:
            error_message = f"Jira issue '{issue_id}' not found."

        return {"status": "error", "error_message": error_message}
    except requests.exceptions.ConnectionError as conn_err:
        return {
            "status": "error",
            "error_message": f"Connection error: {conn_err}",
        }
    except requests.exceptions.Timeout as timeout_err:
        return {
            "status": "error",
            "error_message": f"Request timed out: {timeout_err}",
        }
    except requests.exceptions.RequestException as req_err:
        return {
            "status": "error",
            "error_message": f"An error occurred: {req_err}",
        }

# --- Time-based Search ---

def search_jira_issues_by_time(
    time_field: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    additional_jql: Optional[str] = None,
    max_results: int = 50
) -> dict:
    """Searches for Jira issues based on time criteria (created or updated).

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment variables.
    Time format should be 'YYYY-MM-DD' or 'YYYY-MM-DD HH:mm'.

    Args:
        time_field (str): The time field to search on ('created', 'updated', or 'resolutiondate').
        start_time (Optional[str]): The start date/time (inclusive). Format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:mm'.
        end_time (Optional[str]): The end date/time (inclusive). Format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:mm'.
        additional_jql (Optional[str]): Extra JQL clauses to combine with the time query (e.g., 'project = PIB AND status = Done').
        max_results (int): Maximum number of issues to return. Defaults to 50.

    Returns:
        dict: status and result (report listing issues) or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "error_message": "Atlassian instance configuration (URL, email, API key) missing."}

    if time_field not in ['created', 'updated', 'resolutiondate']:
        return {"status": "error", "error_message": "Invalid time_field. Must be 'created', 'updated', or 'resolutiondate'."}
    if not start_time and not end_time:
        return {"status": "error", "error_message": "At least start_time or end_time must be provided."}

    # Basic format validation (does not check date validity)
    time_format_pattern = r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$"
    import re # Import re locally for this check
    if start_time and not re.match(time_format_pattern, start_time):
        return {"status": "error", "error_message": "Invalid start_time format. Use 'YYYY-MM-DD' or 'YYYY-MM-DD HH:mm'."}
    if end_time and not re.match(time_format_pattern, end_time):
        return {"status": "error", "error_message": "Invalid end_time format. Use 'YYYY-MM-DD' or 'YYYY-MM-DD HH:mm'."}

    # Construct JQL
    jql_parts = []
    if start_time:
        jql_parts.append(f"{time_field} >= '{start_time}'")
    if end_time:
        jql_parts.append(f"{time_field} <= '{end_time}'")
    if additional_jql:
        jql_parts.append(f"({additional_jql})") # Wrap additional JQL in parentheses

    jql = " AND ".join(jql_parts)
    jql += " ORDER BY updated DESC" # Order by most recently updated by default

    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/search"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {
        "jql": jql,
        "maxResults": max_results,
        "fields": ["summary", "status", "created", "updated", "resolutiondate"] # Fields to retrieve
    }

    try:
        response = requests.post(
            api_url, headers=headers, auth=auth, data=json.dumps(payload), timeout=30
        )
        response.raise_for_status()

        data = response.json()
        issues = data.get("issues", [])

        if not issues:
            return {"status": "success", "report": f"No issues found matching the criteria:\nJQL: {jql}"}

        report_lines = [f"Found {len(issues)} issue(s) matching criteria (JQL: {jql}):"]
        for issue in issues:
            key = issue.get("key", "N/A")
            fields = issue.get("fields", {})
            summary = fields.get("summary", "N/A")
            status = fields.get("status", {}).get("name", "N/A")
            created_ts = fields.get("created", "N/A")
            updated_ts = fields.get("updated", "N/A")
            resolution_ts = fields.get("resolutiondate", "N/A") # Get resolutiondate
            report_lines.append(f"  - Key: {key}, Status: {status}, Created: {created_ts}, Updated: {updated_ts}, Resolved: {resolution_ts}, Summary: {summary}")

        return {"status": "success", "report": "\n".join(report_lines)}

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error searching issues: {http_err}"
        try:
            error_details = response.json()
            if "errorMessages" in error_details: error_message += f" Details: {'; '.join(error_details['errorMessages'])}"
            if "errors" in error_details: error_message += f" Field Errors: {json.dumps(error_details['errors'])}"
        except json.JSONDecodeError: pass
        if response.status_code == 400: error_message += f"\nCheck JQL syntax: {jql}"
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "error_message": f"Error searching issues: {req_err}"}


__all__ = [
    # General issue creation
    'create_jira_issue',
    # Sub-task tools
    'create_jira_subtask',
    'get_jira_subtasks',
    'delete_jira_issue', # Note: Also deletes sub-tasks
    # General issue tools
    'show_jira_issue',
    'update_jira_issue',
    'get_jira_transitions',
    'transition_jira_issue',
    'add_jira_comment',
    'get_jira_comments',
    'get_jira_issue_details',
    'search_jira_issues_by_time', # Added time search tool
]


def get_jira_transitions(issue_id: str) -> dict:
    """Retrieves available workflow transitions for a specified Jira issue.

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment variables.

    Args:
        issue_id (str): The Jira issue ID or key (e.g., 'PROJ-123').

    Returns:
        dict: status and result (report listing transitions) or error message.
              Each transition includes its ID and the target status name.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {
            "status": "error",
            "error_message": "Atlassian instance configuration (URL, email, API key) missing in environment variables.",
        }

    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{issue_id}/transitions"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(api_url, headers=headers, auth=auth, timeout=15)
        response.raise_for_status()

        data = response.json()
        transitions = data.get("transitions", [])

        if not transitions:
            return {"status": "success", "report": f"No available transitions found for issue '{issue_id}'."}

        report_lines = [f"Available transitions for issue {issue_id}:"]
        for t in transitions:
            transition_id = t.get("id", "N/A")
            target_status_name = t.get("to", {}).get("name", "N/A")
            report_lines.append(f"  - Transition ID: {transition_id}, Target Status: {target_status_name}")

        return {"status": "success", "report": "\n".join(report_lines)}

    except requests.exceptions.HTTPError as http_err:
        # Handle common errors
        if response.status_code == 401: error_message = "Jira authentication failed."
        elif response.status_code == 403: error_message = f"Permission denied for transitions on issue '{issue_id}'."
        elif response.status_code == 404: error_message = f"Jira issue '{issue_id}' not found."
        else: error_message = f"HTTP error getting transitions: {http_err}"
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "error_message": f"Error getting transitions: {req_err}"}


def transition_jira_issue(issue_id: str, transition_id: str) -> dict:
    """Performs a workflow transition on a specified Jira issue.

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment variables.

    Args:
        issue_id (str): The Jira issue ID or key (e.g., 'PROJ-123').
        transition_id (str): The ID of the workflow transition to execute.

    Returns:
        dict: status and result message or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {
            "status": "error",
            "error_message": "Atlassian instance configuration (URL, email, API key) missing in environment variables.",
        }
    if not transition_id:
        return {"status": "error", "error_message": "Transition ID cannot be empty."}


    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{issue_id}/transitions"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"transition": {"id": transition_id}}

    try:
        response = requests.post(
            api_url, headers=headers, auth=auth, data=json.dumps(payload), timeout=20
        )
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        # Successful transition usually returns 204 No Content
        return {
            "status": "success",
            "report": f"Jira issue '{issue_id}' transitioned successfully using transition ID '{transition_id}'.",
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        try:
            error_details = response.json()
            if "errorMessages" in error_details: error_message += f" Details: {'; '.join(error_details['errorMessages'])}"
            if "errors" in error_details: error_message += f" Field Errors: {json.dumps(error_details['errors'])}"
        except json.JSONDecodeError: pass

        if response.status_code == 400: error_message = f"Bad request transitioning issue '{issue_id}'. Invalid transition ID '{transition_id}' or transition not allowed? Details: {error_message}"
        elif response.status_code == 401: error_message = "Jira authentication failed."
        elif response.status_code == 403: error_message = f"Permission denied for transition '{transition_id}' on issue '{issue_id}'."
        elif response.status_code == 404: error_message = f"Jira issue '{issue_id}' or transition '{transition_id}' not found."

        return {"status": "error", "error_message": error_message}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "error_message": f"Error transitioning issue: {req_err}"}


def add_jira_comment(issue_id: str, comment_body: str) -> dict:
    """Adds a comment to a specified Jira issue.

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment
    variables to be set.

    Args:
        issue_id (str): The Jira issue ID or key (e.g., 'PROJ-123').
        comment_body (str): The text content of the comment.

    Returns:
        dict: status and result message or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {
            "status": "error",
            "error_message": (
                "Atlassian instance configuration (URL, email, API key)" 
                " missing in environment variables."
            ),
        }

    if not comment_body:
        return {"status": "error", "error_message": "Comment body cannot be empty."}

    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{issue_id}/comment"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # Construct comment body in ADF format
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment_body}],
                }
            ],
        }
    }

    try:
        response = requests.post(
            api_url, headers=headers, auth=auth, data=json.dumps(payload), timeout=20
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        comment_id = response.json().get("id", "N/A")
        return {
            "status": "success",
            "report": f"Comment added successfully to issue '{issue_id}'. Comment ID: {comment_id}",
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        try:
            error_details = response.json()
            if "errorMessages" in error_details:
                 error_message += f" Details: {'; '.join(error_details['errorMessages'])}"
            if "errors" in error_details:
                 error_message += f" Field Errors: {json.dumps(error_details['errors'])}"
        except json.JSONDecodeError:
            pass

        if response.status_code == 400:
             error_message = f"Bad request adding comment to '{issue_id}'. Check comment format/permissions. Details: {error_message}"
        elif response.status_code == 401:
            error_message = "Jira authentication failed. Check email/API key."
        elif response.status_code == 403:
             error_message = f"Jira permission denied for adding comment to issue '{issue_id}'."
        elif response.status_code == 404:
            error_message = f"Jira issue '{issue_id}' not found."

        return {"status": "error", "error_message": error_message}
    except requests.exceptions.ConnectionError as conn_err:
        return {
            "status": "error",
            "error_message": f"Connection error: {conn_err}",
        }
    except requests.exceptions.Timeout as timeout_err:
        return {
            "status": "error",
            "error_message": f"Request timed out: {timeout_err}",
        }
    except requests.exceptions.RequestException as req_err:
        return {
            "status": "error",
            "error_message": f"An error occurred: {req_err}",
        }


def get_jira_comments(issue_id: str) -> dict:
    """Retrieves all comments for a specified Jira issue ID from Jira Cloud.

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment
    variables to be set.

    Args:
        issue_id (str): The Jira issue ID (e.g., 'PROJ-123').

    Returns:
        dict: status and result (report with comments) or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {
            "status": "error",
            "error_message": (
                "Atlassian instance configuration (URL, email, API key)" 
                " missing in environment variables."
            ),
        }

    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{issue_id}/comment"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(
            api_url, headers=headers, auth=auth, timeout=15
        )
        response.raise_for_status()

        comments_data = response.json()
        comments = comments_data.get("comments", [])

        if not comments:
            return {"status": "success", "report": f"No comments found for issue '{issue_id}'."}

        report_lines = [f"Comments for issue {issue_id}:"]
        for comment in comments:
            author = comment.get("author", {}).get("displayName", "Unknown Author")
            # Parse and format the created date/time
            created_str = comment.get("created", "")
            created_dt = None
            if created_str:
                try:
                    # Parse the ISO 8601 string, assuming UTC if no offset
                    created_dt_aware = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    # Convert to local timezone (e.g., Berlin) for display
                    local_tz = pytz.timezone('Europe/Berlin') # Or configure as needed
                    created_dt = created_dt_aware.astimezone(local_tz)
                    created_formatted = created_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
                except (ValueError, TypeError):
                    created_formatted = created_str # Fallback to original string

            # Extract text from ADF body
            body_adf = comment.get("body")
            comment_text = "[Empty or Complex Comment Format]"
            if isinstance(body_adf, dict):
                 comment_text = _parse_adf_text(body_adf).strip()
            elif isinstance(body_adf, str): # Handle potential plain text comments
                 comment_text = body_adf.strip()


            report_lines.append(f"  - [{created_formatted}] {author}: {comment_text}")

        return {"status": "success", "report": "\n".join(report_lines)}

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            error_message = "Jira authentication failed. Check email/API key."
        elif response.status_code == 403:
            error_message = f"Jira permission denied for accessing comments on issue '{issue_id}'."
        elif response.status_code == 404:
            error_message = f"Jira issue '{issue_id}' not found."
        else:
            error_message = f"HTTP error occurred: {http_err}"
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.ConnectionError as conn_err:
        return {
            "status": "error",
            "error_message": f"Connection error: {conn_err}",
        }
    except requests.exceptions.Timeout as timeout_err:
        return {
            "status": "error",
            "error_message": f"Request timed out: {timeout_err}",
        }
    except requests.exceptions.RequestException as req_err:
        return {
            "status": "error",
            "error_message": f"An error occurred: {req_err}",
        }


# --- End of removed Implementation Step Management Tools ---


def get_jira_issue_details(issue_id: str) -> dict:
    """Retrieves details for a specified Jira issue ID from Jira Cloud.

    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_KEY environment
    variables to be set.

    Args:
        issue_id (str): The Jira issue ID (e.g., 'PROJ-123').

    Returns:
        dict: status and result (report) or error message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {
            "status": "error",
            "error_message": (
                "Atlassian instance configuration (URL, email, API key)" 
                " missing in environment variables."
            ),
        }

    # Request the category custom field along with standard fields
    fields_to_request = f"summary,status,assignee,description,{CUSTOM_FIELD_CATEGORY_ID}"
    api_url = f"{atlassian_instance_url.rstrip('/')}/rest/api/3/issue/{issue_id}?fields={fields_to_request}"
    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(
            api_url, headers=headers, auth=auth, timeout=15
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        issue_data = response.json()
        fields = issue_data.get("fields", {})
        summary = fields.get("summary", "N/A")
        status = fields.get("status", {}).get("name", "N/A")
        assignee_data = fields.get("assignee")
        assignee = assignee_data.get("displayName", "Unassigned") if assignee_data else "Unassigned"
        # Extract category - it's often an object with a 'value' field for single-select lists
        category_data = fields.get(CUSTOM_FIELD_CATEGORY_ID)
        category = category_data.get("value", "N/A") if isinstance(category_data, dict) else "N/A"
        description_data = fields.get('description')
        description_text = "No description provided."
        if description_data:
            # Basic check for ADF format (JSON object with type 'doc')
            if isinstance(description_data, dict) and description_data.get('type') == 'doc':
                # Attempt to extract plain text from ADF (simplistic approach)
                try:
                    content_texts = []
                    for content_block in description_data.get('content', []):
                        if content_block.get('type') == 'paragraph':
                            for text_node in content_block.get('content', []):
                                if text_node.get('type') == 'text':
                                    content_texts.append(text_node.get('text', ''))
                    description_text = "\n".join(content_texts) if content_texts else "[Complex Description Format]"
                except Exception:
                    description_text = "[Error parsing description]"
            elif isinstance(description_data, str): # Handle plain text descriptions if any
                 description_text = description_data
            else:
                 description_text = "[Unknown Description Format]"


        report = (
            f"Issue {issue_id}:\n"
            f"  Summary: {summary}\n"
            f"  Status: {status}\n"
            f"  Assignee: {assignee}\n"
            f"  Category: {category}\n" # Added Category to report
            f"  Description: {description_text}"
        )
        return {"status": "success", "report": report}

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            error_message = "Jira authentication failed. Check email/API key."
        elif response.status_code == 403:
            error_message = "Jira permission denied."
        elif response.status_code == 404:
            error_message = f"Jira issue '{issue_id}' not found."
        else:
            error_message = f"HTTP error occurred: {http_err}"
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.ConnectionError as conn_err:
        return {
            "status": "error",
            "error_message": f"Connection error: {conn_err}",
        }
    except requests.exceptions.Timeout as timeout_err:
        return {
            "status": "error",
            "error_message": f"Request timed out: {timeout_err}",
        }
    except requests.exceptions.RequestException as req_err:
        return {
            "status": "error",
            "error_message": f"An error occurred: {req_err}",
        }
