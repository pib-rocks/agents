import os
import requests
import json
from typing import Optional

#AI! Move this module into the folder tools (one level above), so that it can be re-used by other agents.
def update_jira_issue(
    issue_id: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    assignee_account_id: Optional[str] = None
) -> dict:
    """Updates fields (summary, description, assignee) for a specified Jira issue.

    Requires JIRA_INSTANCE_URL, JIRA_EMAIL, and JIRA_API_KEY environment
    variables to be set.

    Args:
        issue_id (str): The Jira issue ID or key (e.g., 'PROJ-123').
        summary (Optional[str]): The new summary for the issue. Optional.
        description (Optional[str]): The new description text for the issue.
            Will be converted to basic ADF format. Optional.
        assignee_account_id (Optional[str]): The Atlassian Account ID of the new
            assignee. Set to None to leave unassigned or unchanged if already
            assigned. Optional.

    Returns:
        dict: status and result message or error message.
    """
    jira_url = os.getenv("JIRA_INSTANCE_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_key = os.getenv("JIRA_API_KEY")

    if not all([jira_url, jira_email, jira_api_key]):
        return {
            "status": "error",
            "error_message": (
                "Jira configuration (JIRA_INSTANCE_URL, JIRA_EMAIL, JIRA_API_KEY)"
                " missing in environment variables."
            ),
        }

    if not any([summary, description, assignee_account_id]):
         return {
            "status": "error",
            "error_message": "No fields provided to update.",
        }

    api_url = f"{jira_url.rstrip('/')}/rest/api/3/issue/{issue_id}"
    auth = (jira_email, jira_api_key)
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


def get_jira_issue_details(issue_id: str) -> dict:
    """Retrieves details for a specified Jira issue ID from Jira Cloud.

    Requires JIRA_INSTANCE_URL, JIRA_EMAIL, and JIRA_API_KEY environment
    variables to be set.

    Args:
        issue_id (str): The Jira issue ID (e.g., 'PROJ-123').

    Returns:
        dict: status and result (report) or error message.
    """
    jira_url = os.getenv("JIRA_INSTANCE_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_key = os.getenv("JIRA_API_KEY")

    if not all([jira_url, jira_email, jira_api_key]):
        return {
            "status": "error",
            "error_message": (
                "Jira configuration (JIRA_INSTANCE_URL, JIRA_EMAIL, JIRA_API_KEY)"
                " missing in environment variables."
            ),
        }

    api_url = f"{jira_url.rstrip('/')}/rest/api/3/issue/{issue_id}"
    auth = (jira_email, jira_api_key)
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
