import os
import requests
import json
from typing import Dict, Optional, Any

# Dies sind Platzhalterfunktionen. In einer echten Implementierung würden hier
# API-Aufrufe an Confluence erfolgen (z.B. mit der 'atlassian-python-api').

def create_confluence_page(space_key: str, title: str, body: str, parent_id: Optional[str] = None) -> Dict[str, str]:
    """
    Creates a new page in a Confluence space.
    Args:
        space_key (str): The key of the Confluence space.
        title (str): The title of the new page.
        body (str): The content of the page (Confluence storage format or wiki markup).
        parent_id (Optional[str]): The ID of a parent page, if creating a child page.
    Returns:
        Dict[str, str]: A dictionary with status and a message, including the new page ID on success.
    """
    # Hier würde die Logik zum Erstellen einer Confluence-Seite implementiert
    print(f"Attempting to create Confluence page: Space='{space_key}', Title='{title}', ParentID='{parent_id}'")
    # Simulierte Erfolgsmeldung mit einer fiktiven Seiten-ID
    new_page_id = "12345" # Beispiel-ID
    return {"status": "success", "message": f"Confluence page '{title}' created successfully in space '{space_key}' with ID '{new_page_id}'.", "page_id": new_page_id}

def get_confluence_page(page_id: Optional[str] = None, space_key: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves a Confluence page by its ID, or by space key and title.
    Requires CONFLUENCE_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables.
    Args:
        page_id (Optional[str]): The ID of the page to retrieve. (Prioritized if provided)
        space_key (Optional[str]): The key of the Confluence space (used with title if page_id is not given).
        title (Optional[str]): The title of the page (used with space_key if page_id is not given).
    Returns:
        Dict[str, Any]: A dictionary with status, a message, and page data on success.
    """
    confluence_url = os.getenv("CONFLUENCE_INSTANCE_URL")#AI! Change this to ATLASSIAN_INSTANCE_URL and do the same in jira_tools.py, too, so that all Atlassian-Backends can be accessed with the same credentials
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([confluence_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "message": "Confluence configuration (URL, Atlassian email, Atlassian API key) missing in environment variables."}

    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}
    params = {"expand": "body.storage,version,space"} # Expand to get body, version and space details

    api_base_url = f"{confluence_url.rstrip('/')}/rest/api/content"

    if page_id:
        api_url = f"{api_base_url}/{page_id}"
    elif space_key and title:
        api_url = f"{api_base_url}"
        params["spaceKey"] = space_key
        params["title"] = title
    else:
        return {"status": "error", "message": "Either page_id or both space_key and title must be provided."}

    try:
        response = requests.get(api_url, headers=headers, auth=auth, params=params, timeout=20)
        response.raise_for_status()
        page_data = response.json()

        # If searching by space and title, the result is a list
        if not page_id and space_key and title:
            if page_data.get("results") and len(page_data["results"]) > 0:
                # Take the first result, assuming title and space key are unique enough
                page_info = page_data["results"][0]
            else:
                return {"status": "not_found", "message": f"Confluence page with title '{title}' in space '{space_key}' not found."}
        else: # Searched by ID
            page_info = page_data


        retrieved_page_id = page_info.get("id")
        retrieved_title = page_info.get("title")
        retrieved_space_key = page_info.get("space", {}).get("key")
        # Content is usually in body.storage.value
        page_body = page_info.get("body", {}).get("storage", {}).get("value", "")
        page_version = page_info.get("version", {}).get("number")
        page_link = page_info.get("_links", {}).get("webui", "")
        if not page_link and "base" in page_info.get("_links", {}): # Construct from base and webui if webui is relative
            page_link = confluence_url.rstrip('/') + page_info.get("_links", {}).get("webui")


        return {
            "status": "success",
            "message": f"Details for Confluence page retrieved successfully.",
            "page_id": retrieved_page_id,
            "title": retrieved_title,
            "space_key": retrieved_space_key,
            "body": page_body,
            "version": page_version,
            "link": page_link,
            "raw_response": page_info # Optional: include full response for more complex use cases
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error retrieving Confluence page: {http_err}"
        if response.status_code == 404:
            error_message = f"Confluence page not found. URL: {api_url}"
        elif response.status_code == 401:
            error_message = "Confluence authentication failed. Check credentials."
        elif response.status_code == 403:
            error_message = "Permission denied to access Confluence page."
        try:
            error_details = response.json()
            if "message" in error_details:
                error_message += f" Details: {error_details['message']}"
        except json.JSONDecodeError:
            pass # No JSON in error response
        return {"status": "error", "message": error_message, "details": str(http_err)}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "message": f"Error retrieving Confluence page: {req_err}"}

def update_confluence_page(page_id: str, new_title: Optional[str] = None, new_body: Optional[str] = None, new_parent_id: Optional[str] = None, version_comment: Optional[str] = "Updated via API") -> Dict[str, str]:
    """
    Updates an existing Confluence page (title, body, or parent).
    Args:
        page_id (str): The ID of the page to update.
        new_title (Optional[str]): The new title for the page.
        new_body (Optional[str]): The new content for the page.
        new_parent_id (Optional[str]): The ID of a new parent page.
        version_comment (Optional[str]): A comment for the new version.
    Returns:
        Dict[str, str]: A dictionary with status and a message.
    """
    # Hier würde die Logik zum Aktualisieren einer Confluence-Seite implementiert
    print(f"Attempting to update Confluence page ID: '{page_id}' with Title='{new_title}', ParentID='{new_parent_id}'")
    if not new_title and not new_body and not new_parent_id:
        return {"status": "info", "message": "No changes provided for update."}
    return {"status": "success", "message": f"Confluence page ID '{page_id}' updated successfully."}

def delete_confluence_page(page_id: str) -> Dict[str, str]:
    """
    Deletes a Confluence page by its ID.
    Args:
        page_id (str): The ID of the page to delete.
    Returns:
        Dict[str, str]: A dictionary with status and a message.
    """
    # Hier würde die Logik zum Löschen einer Confluence-Seite implementiert
    print(f"Attempting to delete Confluence page ID: '{page_id}'")
    return {"status": "success", "message": f"Confluence page ID '{page_id}' deleted successfully."}

__all__ = [
    "create_confluence_page",
    "get_confluence_page",
    "update_confluence_page",
    "delete_confluence_page"
]
