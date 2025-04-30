import os
import requests
import json
from typing import Optional, List
from datetime import datetime
import pytz # For timezone handling
import webbrowser # Import the webbrowser module

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

def add_jira_comment(issue_id: str, comment_body: str) -> dict:
    """Adds a comment to a specified Jira issue.

    Requires JIRA_INSTANCE_URL, JIRA_EMAIL, and JIRA_API_KEY environment
    variables to be set.

    Args:
        issue_id (str): The Jira issue ID or key (e.g., 'PROJ-123').
        comment_body (str): The text content of the comment.

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

    if not comment_body:
        return {"status": "error", "error_message": "Comment body cannot be empty."}

    api_url = f"{jira_url.rstrip('/')}/rest/api/3/issue/{issue_id}/comment"
    auth = (jira_email, jira_api_key)
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

    Requires JIRA_INSTANCE_URL, JIRA_EMAIL, and JIRA_API_KEY environment
    variables to be set.

    Args:
        issue_id (str): The Jira issue ID (e.g., 'PROJ-123').

    Returns:
        dict: status and result (report with comments) or error message.
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

    api_url = f"{jira_url.rstrip('/')}/rest/api/3/issue/{issue_id}/comment"
    auth = (jira_email, jira_api_key)
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
