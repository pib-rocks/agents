import os
import requests
import json
from typing import Dict, Optional, Any
import webbrowser

# Dies sind Platzhalterfunktionen. In einer echten Implementierung würden hier
# API-Aufrufe an Confluence erfolgen (z.B. mit der 'atlassian-python-api').

def create_confluence_page(space_key: str, title: str, body: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a new page in a Confluence space.
    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables.
    Args:
        space_key (str): The key of the Confluence space.
        title (str): The title of the new page.
        body (str): The content of the page (Confluence storage format).
        parent_id (Optional[str]): The ID of a parent page, if creating a child page.
    Returns:
        Dict[str, Any]: A dictionary with status, a message, and page details (id, title, link) on success.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "message": "Atlassian instance configuration (URL, email, API key) missing in environment variables."}

    if not space_key or not title or not body:
        return {"status": "error", "message": "Space key, title, and body must be provided to create a page."}

    auth = (atlassian_email, atlassian_api_key)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    api_url = f"{atlassian_instance_url.rstrip('/')}/wiki/rest/api/content"

    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": body,
                "representation": "storage"
            }
        }
    }

    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]

    try:
        response = requests.post(api_url, headers=headers, auth=auth, data=json.dumps(payload), timeout=30)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        
        created_page_data = response.json()
        page_id = created_page_data.get("id")
        page_title = created_page_data.get("title")
        page_link = created_page_data.get("_links", {}).get("webui", "")
        if page_link and page_link.startswith('/'): # If link is relative
             page_link = f"{atlassian_instance_url.rstrip('/')}{page_link}"


        return {
            "status": "success",
            "message": f"Confluence page '{page_title}' created successfully in space '{space_key}' with ID '{page_id}'.",
            "page_id": page_id,
            "title": page_title,
            "link": page_link,
            "raw_response": created_page_data
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error creating Confluence page: {http_err}"
        response_text_for_error = ""
        response_status_code = None
        if http_err.response is not None:
            response_text_for_error = http_err.response.text
            response_status_code = http_err.response.status_code
            try:
                error_details = http_err.response.json()
                # Attempt to extract a more specific error message from Confluence
                detail_msg = error_details.get("message")
                if not detail_msg and "data" in error_details and "errors" in error_details["data"]:
                    # Handle cases where errors are nested, e.g., validation errors
                    errors = error_details["data"]["errors"]
                    if isinstance(errors, list) and len(errors) > 0:
                        first_error = errors[0]
                        if "message" in first_error and "key" in first_error["message"]:
                             detail_msg = f"{first_error['message']['key']} (Args: {first_error['message'].get('args', [])})"
                        elif isinstance(first_error.get("message"), str):
                            detail_msg = first_error["message"]

                if detail_msg:
                    error_message += f" Details: {detail_msg}"
            except json.JSONDecodeError:
                 if response_text_for_error: # Add raw response if not JSON
                    error_message += f" Raw response: {response_text_for_error[:200]}" # Truncate long responses

        return {
            "status": "error", 
            "message": error_message, 
            "details": str(http_err),
            "response_status_code": response_status_code,
            "response_text": response_text_for_error
        }
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "message": f"Request error creating Confluence page: {req_err}"}

def get_confluence_page(page_id: Optional[str] = None, space_key: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves a Confluence page by its ID, or by space key and title.
    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables.
    Args:
        page_id (Optional[str]): The ID of the page to retrieve. (Prioritized if provided)
        space_key (Optional[str]): The key of the Confluence space (used with title if page_id is not given).
        title (Optional[str]): The title of the page (used with space_key if page_id is not given).
    Returns:
        Dict[str, Any]: A dictionary with status, a message, and page data on success.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "message": "Atlassian instance configuration (URL, email, API key) missing in environment variables."}

    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}
    params = {"expand": "body.storage,version,space"} # Expand to get body, version and space details

    api_base_url = f"{atlassian_instance_url.rstrip('/')}/wiki/rest/api/content"

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
            page_link = atlassian_instance_url.rstrip('/') + page_info.get("_links", {}).get("webui")


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

def update_confluence_page(page_id: str, new_title: Optional[str] = None, new_body: Optional[str] = None, new_parent_id: Optional[str] = None, version_comment: Optional[str] = "Updated via API") -> Dict[str, Any]:
    """
    Updates an existing Confluence page (title, body, or parent).
    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables for authentication.
    The page version will be incremented.
    Args:
        page_id (str): The ID of the page to update.
        new_title (Optional[str]): The new title for the page. If None, title remains unchanged.
        new_body (Optional[str]): The new content for the page in Confluence storage format. If None, body remains unchanged.
        new_parent_id (Optional[str]): The ID of a new parent page. If None, parent remains unchanged.
        version_comment (Optional[str]): A comment for the new version. Defaults to "Updated via API".
    Returns:
        Dict[str, Any]: A dictionary with status, a message, and updated page details on success, or error information.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "message": "Atlassian instance configuration (URL, email, API key) missing in environment variables."}

    if not page_id: # Should be caught by type hinting, but good practice
        return {"status": "error", "message": "Page ID must be provided for an update."}

    if not new_title and not new_body and not new_parent_id:
        return {"status": "info", "message": "No changes provided for update. Page not updated."}

    # 1. Get current page details to find the current version and title (if not updating title)
    current_page_details = get_confluence_page(page_id=page_id)
    if current_page_details.get("status") != "success":
        return {
            "status": "error",
            "message": f"Failed to retrieve current page details for page ID '{page_id}'. Error: {current_page_details.get('message')}"
        }

    current_version = current_page_details.get("version")
    current_title = current_page_details.get("title")

    if current_version is None:
        return {"status": "error", "message": f"Could not determine current version for page ID '{page_id}'."}

    # Prepare the payload for the PUT request
    payload = {
        "id": page_id,
        "type": "page",
        "title": new_title if new_title is not None else current_title,
        "version": {
            "number": current_version + 1,
            "message": version_comment
        }
    }

    if new_body is not None:
        payload["body"] = {
            "storage": {
                "value": new_body,
                "representation": "storage"
            }
        }

    if new_parent_id is not None:
        payload["ancestors"] = [{"id": new_parent_id}]

    auth = (atlassian_email, atlassian_api_key)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    api_url = f"{atlassian_instance_url.rstrip('/')}/wiki/rest/api/content/{page_id}"

    try:
        response = requests.put(api_url, headers=headers, auth=auth, data=json.dumps(payload), timeout=30)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        
        updated_page_data = response.json()
        
        updated_page_link = updated_page_data.get("_links", {}).get("webui", "")
        if updated_page_link and updated_page_link.startswith('/'): # If link is relative
            updated_page_link = f"{atlassian_instance_url.rstrip('/')}{updated_page_link}"

        return {
            "status": "success",
            "message": f"Confluence page ID '{page_id}' updated successfully to version {payload['version']['number']}.",
            "page_id": updated_page_data.get("id"),
            "title": updated_page_data.get("title"),
            "version": updated_page_data.get("version", {}).get("number"),
            "link": updated_page_link,
            "raw_response": updated_page_data
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error updating Confluence page ID '{page_id}': {http_err}"
        response_text_for_error = ""
        response_status_code = None
        if http_err.response is not None:
            response_text_for_error = http_err.response.text
            response_status_code = http_err.response.status_code
            try:
                error_details = http_err.response.json()
                detail_msg = error_details.get("message") 
                if not detail_msg:
                    data_errors = error_details.get("data", {}).get("errors")
                    if data_errors and isinstance(data_errors, list) and data_errors:
                        first_error_msg_obj = data_errors[0].get("message")
                        if isinstance(first_error_msg_obj, dict):
                            detail_msg = first_error_msg_obj.get("key")
                            if detail_msg and first_error_msg_obj.get("args"):
                                detail_msg += f" (Details: {first_error_msg_obj.get('args')})"
                        elif isinstance(first_error_msg_obj, str):
                            detail_msg = first_error_msg_obj
                if detail_msg:
                    error_message += f" Details: {detail_msg}"
            except json.JSONDecodeError:
                if response_text_for_error:
                    error_message += f" Raw response: {response_text_for_error[:200]}" # Truncate
        return {
            "status": "error", 
            "message": error_message, 
            "details": str(http_err), 
            "response_status_code": response_status_code,
            "response_text": response_text_for_error
        }
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "message": f"Request error updating Confluence page ID '{page_id}': {req_err}"}

def delete_confluence_page(page_id: str) -> Dict[str, str]:
    """
    Deletes a Confluence page by its ID.
    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables.
    Args:
        page_id (str): The ID of the page to delete.
    Returns:
        Dict[str, str]: A dictionary with status and a message.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "message": "Atlassian instance configuration (URL, email, API key) missing in environment variables."}

    if not page_id:
        return {"status": "error", "message": "Page ID must be provided for deletion."}

    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}
    api_url = f"{atlassian_instance_url.rstrip('/')}/wiki/rest/api/content/{page_id}"

    try:
        response = requests.delete(api_url, headers=headers, auth=auth, timeout=20)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        
        # Confluence DELETE typically returns 204 No Content on success
        return {"status": "success", "message": f"Confluence page ID '{page_id}' deleted successfully."}

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error deleting Confluence page ID '{page_id}': {http_err}"
        response_status_code = http_err.response.status_code if http_err.response is not None else None
        
        if response_status_code == 404:
            error_message = f"Confluence page with ID '{page_id}' not found."
        elif response_status_code == 401:
            error_message = "Confluence authentication failed. Check credentials."
        elif response_status_code == 403:
            error_message = f"Permission denied to delete Confluence page ID '{page_id}'."
        
        response_text_for_error = ""
        if http_err.response is not None:
            response_text_for_error = http_err.response.text
            try:
                error_details = http_err.response.json()
                if "message" in error_details:
                    error_message += f" Details: {error_details['message']}"
            except json.JSONDecodeError:
                if response_text_for_error: # Add raw response if not JSON
                    error_message += f" Raw response: {response_text_for_error[:200]}"


        return {
            "status": "error", 
            "message": error_message, 
            "details": str(http_err),
            "response_status_code": response_status_code,
            "response_text": response_text_for_error
        }
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "message": f"Request error deleting Confluence page ID '{page_id}': {req_err}"}

def get_confluence_child_pages(parent_page_id: str) -> Dict[str, Any]:
    """
    Retrieves a list of direct child pages for a given parent Confluence page ID.
    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables.
    Args:
        parent_page_id (str): The ID of the parent page.
    Returns:
        Dict[str, Any]: A dictionary with status, a message, and a list of child pages on success.
                        Each child page entry contains 'id', 'title', and 'link'.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "message": "Atlassian instance configuration (URL, email, API key) missing in environment variables."}

    if not parent_page_id:
        return {"status": "error", "message": "Parent Page ID must be provided."}

    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}
    # API endpoint for child pages (only direct children of type 'page')
    api_url = f"{atlassian_instance_url.rstrip('/')}/wiki/rest/api/content/{parent_page_id}/child/page"
    params = {"expand": "version"} # Expand to ensure basic fields are present, adjust if more needed

    try:
        response = requests.get(api_url, headers=headers, auth=auth, params=params, timeout=20)
        response.raise_for_status()
        response_data = response.json()

        child_pages = []
        if "results" in response_data:
            for page_info in response_data["results"]:
                child_page_link = page_info.get("_links", {}).get("webui", "")
                if child_page_link and child_page_link.startswith('/'): # If link is relative
                    base_url = page_info.get("_links", {}).get("base", atlassian_instance_url.rstrip('/'))
                    child_page_link = f"{base_url.rstrip('/')}{child_page_link}"
                
                child_pages.append({
                    "id": page_info.get("id"),
                    "title": page_info.get("title"),
                    "link": child_page_link
                })
        
        if not child_pages:
             return {
                "status": "success", # Or "info" if preferred for no children
                "message": f"No child pages found for parent page ID '{parent_page_id}'.",
                "child_pages": []
            }

        return {
            "status": "success",
            "message": f"Successfully retrieved {len(child_pages)} child page(s) for parent ID '{parent_page_id}'.",
            "child_pages": child_pages
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error retrieving child pages for parent ID '{parent_page_id}': {http_err}"
        response_status_code = http_err.response.status_code if http_err.response else None
        
        if response_status_code == 404:
            error_message = f"Parent Confluence page with ID '{parent_page_id}' not found or has no child pages of type 'page'."
        elif response_status_code == 401:
            error_message = "Confluence authentication failed. Check credentials."
        elif response_status_code == 403:
            error_message = f"Permission denied to access child pages for parent ID '{parent_page_id}'."
        
        try:
            if http_err.response:
                error_details = http_err.response.json()
                if "message" in error_details:
                    error_message += f" Details: {error_details['message']}"
        except json.JSONDecodeError:
            if http_err.response and http_err.response.text:
                 error_message += f" Raw response: {http_err.response.text[:200]}"


        return {"status": "error", "message": error_message, "details": str(http_err), "response_status_code": response_status_code}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "message": f"Request error retrieving child pages for parent ID '{parent_page_id}': {req_err}"}

def show_confluence_page(page_id: Optional[str] = None, space_key: Optional[str] = None, title: Optional[str] = None) -> Dict[str, str]:
    """
    Opens a Confluence page in the default web browser.
    Requires either a page_id or both space_key and title.
    Args:
        page_id (Optional[str]): The ID of the page.
        space_key (Optional[str]): The key of the Confluence space (used with title).
        title (Optional[str]): The title of the page (used with space_key).
    Returns:
        Dict[str, str]: A dictionary with status and a message.
    """
    if not page_id and not (space_key and title):
        return {"status": "error", "message": "Either page_id or both space_key and title must be provided to show the page."}

    page_details = get_confluence_page(page_id=page_id, space_key=space_key, title=title)

    if page_details.get("status") != "success":
        message = page_details.get("message", "Failed to retrieve page details.")
        if page_id:
            return {"status": "error", "message": f"Could not retrieve Confluence page with ID '{page_id}'. Error: {message}"}
        else:
            return {"status": "error", "message": f"Could not retrieve Confluence page with title '{title}' in space '{space_key}'. Error: {message}"}

    page_link = page_details.get("link")
    actual_page_id = page_details.get("page_id", "N/A") # Get the actual ID if found by title/space

    if page_link and page_link.startswith("/"):
        atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
        if atlassian_instance_url:
            base_url = atlassian_instance_url.rstrip('/')
            if page_link.startswith("/wiki/"): # e.g. /wiki/display/FOO
                page_link = f"{base_url}{page_link}"
            else: # e.g. /display/FOO, needs /wiki prefix
                page_link = f"{base_url}/wiki{page_link}"
    
    if not page_link:
        if page_id:
            return {"status": "error", "message": f"No web link found for Confluence page ID '{page_id}'."}
        else:
            return {"status": "error", "message": f"No web link found for Confluence page with title '{title}' in space '{space_key}' (Resolved ID: {actual_page_id})."}

    try:
        if webbrowser.open(page_link):
            page_identifier = f"ID '{actual_page_id}'" if actual_page_id != "N/A" else f"title '{title}' in space '{space_key}'"
            return {"status": "success", "message": f"Attempted to open Confluence page {page_identifier} in browser. Link: {page_link}"}
        else:
            return {"status": "error", "message": f"Failed to open Confluence page link in browser: {page_link}. webbrowser.open returned false."}
    except Exception as e:
        return {"status": "error", "message": f"An error occurred while trying to open Confluence page link {page_link} in browser: {e}"}

# Write a function for accessing the confluence search endpoint, including the ability to perform CQL queries

def search_confluence_cql(cql_query: str, limit: int = 25, start: int = 0, expand: Optional[str] = None) -> Dict[str, Any]:
    """
    Searches Confluence using a CQL (Confluence Query Language) query.
    Requires ATLASSIAN_INSTANCE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_KEY environment variables.

    Args:
        cql_query (str): The CQL query string.
        limit (int): The maximum number of results to return. Defaults to 25.
        start (int): The starting index of the results (for pagination). Defaults to 0.
        expand (Optional[str]): A comma-separated list of properties to expand in the results
                                 (e.g., "content.body.storage,content.version").

    Returns:
        Dict[str, Any]: A dictionary with status, a message, and a list of search results on success.
                        Each result typically includes 'content' (page/blogpost details), 'title', 'excerpt', 'url'.
    """
    atlassian_instance_url = os.getenv("ATLASSIAN_INSTANCE_URL")
    atlassian_email = os.getenv("ATLASSIAN_EMAIL")
    atlassian_api_key = os.getenv("ATLASSIAN_API_KEY")

    if not all([atlassian_instance_url, atlassian_email, atlassian_api_key]):
        return {"status": "error", "message": "Atlassian instance configuration (URL, email, API key) missing in environment variables."}

    if not cql_query:
        return {"status": "error", "message": "CQL query must be provided."}

    auth = (atlassian_email, atlassian_api_key)
    headers = {"Accept": "application/json"}
    api_url = f"{atlassian_instance_url.rstrip('/')}/wiki/rest/api/search"
    
    params: Dict[str, Any] = {
        "cql": cql_query,
        "limit": limit,
        "start": start
    }
    if expand:
        params["expand"] = expand

    try:
        response = requests.get(api_url, headers=headers, auth=auth, params=params, timeout=30)
        response.raise_for_status()
        search_data = response.json()

        results = []
        if "results" in search_data:
            for item in search_data["results"]:
                content = item.get("content", {})
                item_id = content.get("id")
                item_title = content.get("title")
                item_type = content.get("type") # page, blogpost, comment, attachment
                
                # Construct a basic link, might need adjustment based on actual _links structure for search results
                item_link = content.get("_links", {}).get("webui")
                if item_link and item_link.startswith('/'):
                    base_url = content.get("_links", {}).get("base", atlassian_instance_url.rstrip('/'))
                    item_link = f"{base_url.rstrip('/')}{item_link}"
                elif not item_link and item_id: # Fallback if webui is not directly in content._links
                    item_link = f"{atlassian_instance_url.rstrip('/')}/wiki/spaces/{content.get('space',{}).get('key','~')}/pages/{item_id}"


                results.append({
                    "id": item_id,
                    "title": item_title,
                    "type": item_type,
                    "excerpt": item.get("excerpt"),
                    "url": item.get("url"), # This is usually the API URL of the result itself
                    "link": item_link, # This is the web UI link
                    "raw_result": item # Include the full item for more details if needed
                })
        
        total_size = search_data.get("totalSize", len(results))
        
        return {
            "status": "success",
            "message": f"Search completed. Found {len(results)} results (total matching: {total_size}).",
            "results": results,
            "total_size": total_size,
            "limit": search_data.get("limit", limit),
            "start": search_data.get("start", start),
            "cql_query": cql_query
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error during Confluence search: {http_err}"
        response_text_for_error = ""
        response_status_code = None
        if http_err.response is not None:
            response_text_for_error = http_err.response.text
            response_status_code = http_err.response.status_code
            if response_status_code == 400: # Bad Request, often CQL syntax error
                error_message = f"Bad request during Confluence search (Code 400). Check CQL syntax or parameters."
            elif response_status_code == 401:
                error_message = "Confluence authentication failed (Code 401). Check credentials."
            elif response_status_code == 403:
                error_message = "Permission denied for Confluence search (Code 403)."
            
            try:
                error_details = http_err.response.json()
                specific_detail_found = False
                # Prioritize 'errorMessages' as it often contains more specific CQL errors
                if "errorMessages" in error_details and isinstance(error_details["errorMessages"], list) and error_details["errorMessages"]:
                    error_message += f" Details: {'; '.join(error_details['errorMessages'])}"
                    specific_detail_found = True
                elif "message" in error_details: # Fallback to general 'message'
                    error_message += f" Details: {error_details['message']}"
                    specific_detail_found = True
                
                # If no specific detail was found from the common fields, but we have a JSON response,
                # and the generic error_message doesn't already include the raw response snippet.
                if not specific_detail_found and response_text_for_error and f" Raw response: {response_text_for_error[:200]}" not in error_message:
                    # This case might be redundant if the outer except json.JSONDecodeError handles it,
                    # but ensures some detail if JSON is valid but unexpected structure.
                    # However, the current structure means this part might not be hit if specific_detail_found is false.
                    # The primary goal is to fix the errorMessages vs message priority.
                    pass # The existing logic below for non-JSON or no specific message will be caught by the outer try-except.

            except json.JSONDecodeError:
                if response_text_for_error:
                    error_message += f" Raw response: {response_text_for_error[:200]}"
        
        return {
            "status": "error", 
            "message": error_message, 
            "details": str(http_err),
            "response_status_code": response_status_code,
            "response_text": response_text_for_error
        }
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "message": f"Request error during Confluence search: {req_err}"}


__all__ = [
    "create_confluence_page",
    "get_confluence_page",
    "show_confluence_page",
    "update_confluence_page",
    "delete_confluence_page",
    "get_confluence_child_pages",
    "search_confluence_cql"
]
