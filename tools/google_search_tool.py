"""
This module provides a custom Google Search tool implemented as a standard
Python function for use with agents via function calling.
"""
import os
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def perform_google_search(query: str) -> dict:
    """Performs a Google search using the Custom Search JSON API.

    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables to be set.

    Args:
        query (str): The search query.

    Returns:
        dict: A dictionary containing the status ('success' or 'error') and
              either a 'report' with search results or an 'error_message'.
              The report includes titles and snippets of the top results.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        return {
            "status": "error",
            "error_message": (
                "Google Search API configuration (GOOGLE_API_KEY, GOOGLE_CSE_ID)"
                " missing in environment variables."
            ),
        }

    if not query:
        return {"status": "error", "error_message": "Search query cannot be empty."}

    try:
        # Build the search service
        service = build("customsearch", "v1", developerKey=api_key)

        # Execute the search, requesting top 5 results
        result = service.cse().list(
            q=query,
            cx=cse_id,
            num=5  # Limit number of results
        ).execute()

        # Format the results
        search_items = result.get("items", [])
        if not search_items:
            return {"status": "success", "report": f"No results found for '{query}'."}

        report_lines = [f"Search results for '{query}':"]
        for i, item in enumerate(search_items):
            title = item.get("title", "No Title")
            snippet = item.get("snippet", "No Snippet").replace("\n", " ")
            link = item.get("link", "#")
            report_lines.append(f"  {i+1}. {title}: {snippet} ({link})")

        return {"status": "success", "report": "\n".join(report_lines)}

    except HttpError as http_err:
        error_details = f"HTTP error occurred: {http_err}"
        try:
            # Attempt to parse error content for more details
            error_content = json.loads(http_err.content.decode('utf-8'))
            if 'error' in error_content and 'message' in error_content['error']:
                error_details += f" Details: {error_content['error']['message']}"
        except (json.JSONDecodeError, AttributeError, KeyError):
            pass # Ignore if content is not JSON or structure is unexpected

        if http_err.resp.status == 400:
             error_details = f"Bad request during search (check CSE ID?). Details: {error_details}"
        elif http_err.resp.status == 403:
             error_details = f"Permission denied (check API key/permissions?). Details: {error_details}"

        return {"status": "error", "error_message": error_details}
    except Exception as e:
        # Catch any other unexpected errors during API call or processing
        return {
            "status": "error",
            "error_message": f"An unexpected error occurred during Google Search: {e}",
        }

# Export the new function
__all__ = ['perform_google_search']

# Note: Ensure GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables are set
# for this tool to function correctly.
