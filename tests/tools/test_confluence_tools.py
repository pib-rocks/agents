import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import requests # Import requests for exceptions
import json

# Füge das Projekt-Stammverzeichnis zum sys.path hinzu, um das 'tools'-Modul zu finden
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.confluence_tools import (
    create_confluence_page,
    get_confluence_page,
    update_confluence_page,
    delete_confluence_page,
    get_confluence_child_pages,
    show_confluence_page,
    show_confluence_version_comparison,
    search_confluence_cql
)

class TestConfluenceTools(unittest.TestCase):

    def _setup_mock_env_vars(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "ATLASSIAN_INSTANCE_URL": "https://test.atlassian.net",
            "ATLASSIAN_EMAIL": "test@example.com",
            "ATLASSIAN_API_KEY": "test_api_key"
        }.get(key, default)

    # --- Tests for create_confluence_page ---
    @patch('requests.post')
    @patch('os.getenv')
    def test_create_confluence_page_success_with_parent(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        space_key = "TESTSPACE"
        title = "My New Page"
        body = "<p>Page content</p>"
        parent_id = "12345"

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "id": "67890",
            "title": title,
            "space": {"key": space_key},
            "_links": {"webui": "/wiki/display/TESTSPACE/My+New+Page", "base": "https://test.atlassian.net"}
        }
        mock_requests_post.return_value = mock_post_response

        result = create_confluence_page(space_key, title, body, parent_id=parent_id)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["page_id"], "67890")
        self.assertEqual(result["title"], title)
        self.assertEqual(result["link"], "https://test.atlassian.net/wiki/display/TESTSPACE/My+New+Page")
        self.assertIn(f"Confluence page '{title}' created successfully in space '{space_key}' with ID '67890'.", result["message"])
        
        mock_requests_post.assert_called_once()
        called_url = mock_requests_post.call_args[0][0]
        self.assertTrue(called_url.endswith("/wiki/rest/api/content"))
        sent_payload = json.loads(mock_requests_post.call_args[1]['data'])
        self.assertEqual(sent_payload["title"], title)
        self.assertEqual(sent_payload["space"]["key"], space_key)
        self.assertEqual(sent_payload["body"]["storage"]["value"], body)
        self.assertEqual(sent_payload["ancestors"][0]["id"], parent_id)

    @patch('requests.post')
    @patch('os.getenv')
    def test_create_confluence_page_success_no_parent(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        space_key = "PROJ"
        title = "Another Page"
        body = "<h1>Hello</h1>"

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "id": "11223",
            "title": title,
            "space": {"key": space_key},
            "_links": {"webui": "/wiki/display/PROJ/Another+Page"} # Test relative link
        }
        mock_requests_post.return_value = mock_post_response

        result = create_confluence_page(space_key, title, body)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["page_id"], "11223")
        self.assertEqual(result["link"], "https://test.atlassian.net/wiki/display/PROJ/Another+Page")
        sent_payload = json.loads(mock_requests_post.call_args[1]['data'])
        self.assertNotIn("ancestors", sent_payload)

    @patch('os.getenv')
    def test_create_confluence_page_env_vars_missing(self, mock_getenv):
        mock_getenv.return_value = None # Simulate one var missing
        result = create_confluence_page("SK", "T", "B")
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration", result["message"])

    @patch('os.getenv')
    def test_create_confluence_page_missing_args(self, mock_getenv):
        self._setup_mock_env_vars(mock_getenv)
        result = create_confluence_page(space_key="", title="T", body="B")
        self.assertEqual(result["status"], "error")
        self.assertIn("Space key, title, and body must be provided", result["message"])
        
        result = create_confluence_page(space_key="SK", title="", body="B")
        self.assertEqual(result["status"], "error")
        self.assertIn("Space key, title, and body must be provided", result["message"])

        result = create_confluence_page(space_key="SK", title="T", body="")
        self.assertEqual(result["status"], "error")
        self.assertIn("Space key, title, and body must be provided", result["message"])

    @patch('requests.post')
    @patch('os.getenv')
    def test_create_confluence_page_http_error_400_detailed(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        mock_error_response = MagicMock()
        mock_error_response.status_code = 400
        error_json = {
            "message": "Top level error from API.",
            "data": {"errors": [{"message": {"key": "validation.error.key", "args": ["details"]}}]}
        }
        mock_error_response.json.return_value = error_json
        mock_error_response.text = json.dumps(error_json)
        mock_requests_post.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = create_confluence_page("SK", "T", "B")
        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP error creating Confluence page", result["message"])
        # The function currently extracts the top-level message first.
        self.assertIn("Details: Top level error from API.", result["message"])
        self.assertEqual(result["response_status_code"], 400)

    @patch('requests.post')
    @patch('os.getenv')
    def test_create_confluence_page_http_error_401(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        mock_error_response = MagicMock()
        mock_error_response.status_code = 401
        mock_error_response.json.return_value = {"message": "Authentication failed by API"}
        mock_error_response.text = '{"message": "Authentication failed by API"}'
        mock_requests_post.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = create_confluence_page("SK", "T", "B")
        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP error creating Confluence page", result["message"])
        self.assertIn("Details: Authentication failed by API", result["message"])
        self.assertEqual(result["response_status_code"], 401)

    @patch('requests.post')
    @patch('os.getenv')
    def test_create_confluence_page_request_exception(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        mock_requests_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = create_confluence_page("SK", "T", "B")
        self.assertEqual(result["status"], "error")
        self.assertIn("Request error creating Confluence page: Connection timed out", result["message"])

    # --- Tests for delete_confluence_page ---
    @patch('requests.delete')
    @patch('os.getenv')
    def test_delete_confluence_page_success(self, mock_getenv, mock_requests_delete):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "todelete_123"

        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 204 # Typical for successful DELETE
        mock_delete_response.raise_for_status = MagicMock() # Ensure it doesn't raise
        mock_requests_delete.return_value = mock_delete_response
        
        result = delete_confluence_page(page_id)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], f"Confluence page ID '{page_id}' deleted successfully.")
        mock_requests_delete.assert_called_once()
        called_url = mock_requests_delete.call_args[0][0]
        self.assertTrue(called_url.endswith(f"/wiki/rest/api/content/{page_id}"))

    @patch('os.getenv')
    def test_delete_confluence_page_env_vars_missing(self, mock_getenv):
        mock_getenv.return_value = None
        result = delete_confluence_page("any_id")
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration", result["message"])

    @patch('os.getenv')
    def test_delete_confluence_page_no_page_id(self, mock_getenv):
        self._setup_mock_env_vars(mock_getenv)
        result = delete_confluence_page("")
        self.assertEqual(result["status"], "error")
        self.assertIn("Page ID must be provided for deletion.", result["message"])

        result_none = delete_confluence_page(None)
        self.assertEqual(result_none["status"], "error")
        self.assertIn("Page ID must be provided for deletion.", result_none["message"])
        
    @patch('requests.delete')
    @patch('os.getenv')
    def test_delete_confluence_page_http_error_404(self, mock_getenv, mock_requests_delete):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "notfound_404"
        mock_error_response = MagicMock()
        mock_error_response.status_code = 404
        mock_error_response.json.return_value = {"message": "API says not found"}
        mock_error_response.text = '{"message": "API says not found"}'
        mock_requests_delete.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = delete_confluence_page(page_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], f"Confluence page with ID '{page_id}' not found. Details: API says not found")
        self.assertEqual(result["response_status_code"], 404)

    @patch('requests.delete')
    @patch('os.getenv')
    def test_delete_confluence_page_http_error_401(self, mock_getenv, mock_requests_delete):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "authfail_401"
        mock_error_response = MagicMock()
        mock_error_response.status_code = 401
        mock_error_response.json.return_value = {"message": "API says auth failed"}
        mock_error_response.text = '{"message": "API says auth failed"}'
        mock_requests_delete.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = delete_confluence_page(page_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Confluence authentication failed. Check credentials. Details: API says auth failed")
        self.assertEqual(result["response_status_code"], 401)

    @patch('requests.delete')
    @patch('os.getenv')
    def test_delete_confluence_page_http_error_403(self, mock_getenv, mock_requests_delete):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "forbidden_403"
        mock_error_response = MagicMock()
        mock_error_response.status_code = 403
        mock_error_response.json.return_value = {"message": "API says forbidden"}
        mock_error_response.text = '{"message": "API says forbidden"}'
        mock_requests_delete.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = delete_confluence_page(page_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], f"Permission denied to delete Confluence page ID '{page_id}'. Details: API says forbidden")
        self.assertEqual(result["response_status_code"], 403)

    @patch('requests.delete')
    @patch('os.getenv')
    def test_delete_confluence_page_request_exception(self, mock_getenv, mock_requests_delete):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "timeout_err"
        mock_requests_delete.side_effect = requests.exceptions.Timeout("Connection failed")

        result = delete_confluence_page(page_id)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Request error deleting Confluence page ID '{page_id}': Connection failed", result["message"])

    # --- Tests for update_confluence_page (implemented function) ---
    @patch('requests.put')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_update_page_success_all_fields(self, mock_getenv, mock_get_confluence_page, mock_requests_put):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_123"
        current_version = 2
        new_title = "New Awesome Title"
        new_body = "<p>New awesome body</p>"
        new_parent_id = "parent_page_789"
        version_comment = "Major update with all fields"

        mock_get_confluence_page.return_value = {
            "status": "success", "page_id": page_id, "title": "Old Title", 
            "version": current_version, "body": "<p>Old Body</p>"
        }

        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "id": page_id, "title": new_title, 
            "version": {"number": current_version + 1},
            "_links": {"webui": "/wiki/display/SPACE/New+Awesome+Title", "base": "https://test.atlassian.net"}
        }
        mock_requests_put.return_value = mock_put_response

        result = update_confluence_page(page_id, new_title=new_title, new_body=new_body, new_parent_id=new_parent_id, version_comment=version_comment)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["page_id"], page_id)
        self.assertEqual(result["title"], new_title)
        self.assertEqual(result["version"], current_version + 1)
        self.assertEqual(result["link"], "https://test.atlassian.net/wiki/display/SPACE/New+Awesome+Title")
        self.assertIn(f"updated successfully to version {current_version + 1}", result["message"])

        mock_get_confluence_page.assert_called_once_with(page_id=page_id)
        mock_requests_put.assert_called_once()
        
        called_url = mock_requests_put.call_args[0][0]
        self.assertTrue(called_url.endswith(f"/wiki/rest/api/content/{page_id}"))
        
        sent_payload = json.loads(mock_requests_put.call_args[1]['data'])
        self.assertEqual(sent_payload["title"], new_title)
        self.assertEqual(sent_payload["body"]["storage"]["value"], new_body)
        self.assertEqual(sent_payload["ancestors"][0]["id"], new_parent_id)
        self.assertEqual(sent_payload["version"]["number"], current_version + 1)
        self.assertEqual(sent_payload["version"]["message"], version_comment)

    @patch('requests.put')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_update_page_success_only_title(self, mock_getenv, mock_get_confluence_page, mock_requests_put):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_456"
        current_version = 1
        new_title = "Just a New Title"
        
        mock_get_confluence_page.return_value = {
            "status": "success", "page_id": page_id, "title": "Old Title", "version": current_version
        }
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "id": page_id, "title": new_title, "version": {"number": current_version + 1},
            "_links": {"webui": "/display/SPACE/Just+a+New+Title"} # Test relative link
        }
        mock_requests_put.return_value = mock_put_response

        result = update_confluence_page(page_id, new_title=new_title)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["title"], new_title)
        self.assertEqual(result["link"], "https://test.atlassian.net/display/SPACE/Just+a+New+Title")
        sent_payload = json.loads(mock_requests_put.call_args[1]['data'])
        self.assertEqual(sent_payload["title"], new_title)
        self.assertNotIn("body", sent_payload)
        self.assertNotIn("ancestors", sent_payload)

    @patch('os.getenv')
    def test_update_page_env_vars_missing(self, mock_getenv):
        mock_getenv.return_value = None # Simulate one var missing is enough
        result = update_confluence_page("any_id", new_title="Some Title")
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration", result["message"])

    @patch('os.getenv')
    def test_update_page_no_page_id(self, mock_getenv):
        self._setup_mock_env_vars(mock_getenv)
        result = update_confluence_page(page_id="", new_title="Some Title")
        self.assertEqual(result["status"], "error")
        self.assertIn("Page ID must be provided", result["message"])
        
        result_none = update_confluence_page(page_id=None, new_title="Some Title")
        self.assertEqual(result_none["status"], "error")
        self.assertIn("Page ID must be provided", result_none["message"])


    @patch('os.getenv')
    def test_update_page_no_changes_provided(self, mock_getenv):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_789"
        # No call to get_confluence_page or requests.put should happen
        result = update_confluence_page(page_id)
        self.assertEqual(result["status"], "info")
        self.assertIn("No changes provided for update", result["message"])

    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_update_page_get_page_details_fails(self, mock_getenv, mock_get_confluence_page):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_000"
        mock_get_confluence_page.return_value = {"status": "error", "message": "Failed to get page"}
        
        result = update_confluence_page(page_id, new_title="A Title")
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Failed to retrieve current page details for page ID '{page_id}'", result["message"])
        self.assertIn("Failed to get page", result["message"])

    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_update_page_get_page_details_no_version(self, mock_getenv, mock_get_confluence_page):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_111"
        mock_get_confluence_page.return_value = {
            "status": "success", "page_id": page_id, "title": "Old Title", "version": None # Missing version
        }
        result = update_confluence_page(page_id, new_title="A Title")
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Could not determine current version for page ID '{page_id}'", result["message"])

    @patch('requests.put')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_update_page_put_request_http_error_400_detailed_msg(self, mock_getenv, mock_get_confluence_page, mock_requests_put):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_222"
        current_version = 1
        mock_get_confluence_page.return_value = {"status": "success", "version": current_version, "title": "Old"}

        mock_error_response = MagicMock()
        mock_error_response.status_code = 400
        # Simulate Confluence's more complex error structure
        error_json = {
            "statusCode": 400,
            "data": {
                "errors": [
                    {
                        "message": {
                            "key": "some.error.key",
                            "args": ["details about error"]
                        }
                    }
                ],
                "authorized": False, "valid": True, "allowedInReadOnlyMode": True, "successful": False
            },
            "message": "com.atlassian.confluence.api.service.exceptions.BadRequestException: ..." # Top level message
        }
        mock_error_response.json.return_value = error_json
        mock_error_response.text = json.dumps(error_json) # For the raw text part
        mock_requests_put.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = update_confluence_page(page_id, new_title="Trigger Error")
        self.assertEqual(result["status"], "error")
        self.assertIn(f"HTTP error updating Confluence page ID '{page_id}'", result["message"])
        self.assertIn("Details: com.atlassian.confluence.api.service.exceptions.BadRequestException", result["message"]) # Checks if top-level message is used
        self.assertEqual(result["response_status_code"], 400)

    @patch('requests.put')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_update_page_put_request_http_error_401(self, mock_getenv, mock_get_confluence_page, mock_requests_put):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_333"
        current_version = 3
        mock_get_confluence_page.return_value = {"status": "success", "version": current_version, "title": "Old"}

        mock_error_response = MagicMock()
        mock_error_response.status_code = 401
        mock_error_response.json.return_value = {"message": "Authentication failed"}
        mock_error_response.text = '{"message": "Authentication failed"}'
        mock_requests_put.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = update_confluence_page(page_id, new_body="Update attempt")
        self.assertEqual(result["status"], "error")
        self.assertIn("Authentication failed", result["message"])
        self.assertEqual(result["response_status_code"], 401)

    @patch('requests.put')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_update_page_put_request_http_error_non_json_response(self, mock_getenv, mock_get_confluence_page, mock_requests_put):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_444"
        current_version = 1
        mock_get_confluence_page.return_value = {"status": "success", "version": current_version, "title": "Old"}

        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.json.side_effect = json.JSONDecodeError("Error", "doc", 0) # Simulate non-JSON response
        mock_error_response.text = "Internal Server Error HTML page"
        mock_requests_put.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = update_confluence_page(page_id, new_title="Trigger 500")
        self.assertEqual(result["status"], "error")
        self.assertIn(f"HTTP error updating Confluence page ID '{page_id}'", result["message"])
        self.assertIn("Raw response: Internal Server Error HTML page", result["message"])
        self.assertEqual(result["response_status_code"], 500)

    @patch('requests.put')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_update_page_put_request_exception(self, mock_getenv, mock_get_confluence_page, mock_requests_put):
        self._setup_mock_env_vars(mock_getenv)
        page_id = "test_page_555"
        current_version = 1
        mock_get_confluence_page.return_value = {"status": "success", "version": current_version, "title": "Old"}
        mock_requests_put.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = update_confluence_page(page_id, new_title="Trigger Timeout")
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Request error updating Confluence page ID '{page_id}': Connection timed out", result["message"])

    # --- Tests for get_confluence_page (implemented function) ---

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_by_id_success(self, mock_getenv, mock_requests_get):
        # Setup mock environment variables
        self._setup_mock_env_vars(mock_getenv)

        # Setup mock response from requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_page_data = {
            "id": "12345", 
            "title": "Test Page", 
            "space": {"key": "TEST"},
            "body": {"storage": {"value": "<p>Test content</p>"}},
            "version": {"number": 2},
            "_links": {"webui": "https://test.atlassian.net/wiki/display/TEST/Test+Page", "base": "https://test.atlassian.net/wiki"}
        }
        mock_response.json.return_value = mock_page_data
        mock_requests_get.return_value = mock_response

        page_id = "12345"
        result = get_confluence_page(page_id=page_id)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["page_id"], page_id)
        self.assertEqual(result["title"], "Test Page")
        self.assertEqual(result["space_key"], "TEST")
        self.assertEqual(result["body"], "<p>Test content</p>")
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["link"], "https://test.atlassian.net/wiki/display/TEST/Test+Page")
        mock_requests_get.assert_called_once()
        self.assertIn(f"/rest/api/content/{page_id}", mock_requests_get.call_args[0][0])

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_by_space_and_title_success(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_page_data = {
            "results": [{
                "id": "67890", 
                "title": "My Page Title", 
                "space": {"key": "MYSPACE"},
                "body": {"storage": {"value": "Content here"}},
                "version": {"number": 1},
                "_links": {"webui": "/wiki/display/MYSPACE/My+Page+Title"}
            }],
            "size": 1
        }
        mock_response.json.return_value = mock_page_data
        mock_requests_get.return_value = mock_response

        space_key = "MYSPACE"
        title = "My Page Title"
        result = get_confluence_page(space_key=space_key, title=title)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["page_id"], "67890")
        self.assertEqual(result["title"], title)
        self.assertEqual(result["space_key"], space_key)
        self.assertEqual(result["link"], "https://test.atlassian.net/wiki/display/MYSPACE/My+Page+Title")
        mock_requests_get.assert_called_once()
        self.assertIn(f"/rest/api/content", mock_requests_get.call_args[0][0])
        self.assertEqual(mock_requests_get.call_args[1]['params']['spaceKey'], space_key)
        self.assertEqual(mock_requests_get.call_args[1]['params']['title'], title)

    @patch('os.getenv')
    def test_get_confluence_page_missing_env_vars(self, mock_getenv):
        mock_getenv.return_value = None # Simulate missing env var
        result = get_confluence_page(page_id="123")
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration (URL, email, API key) missing", result["message"])

    @patch('os.getenv') # Mock os.getenv for this test
    def test_get_confluence_page_insufficient_args(self, mock_getenv):
        # Configure mock_getenv to return valid values so the env var check passes
        self._setup_mock_env_vars(mock_getenv)

        result_no_page_id_no_title = get_confluence_page(space_key="MYSAPCE")
        self.assertEqual(result_no_page_id_no_title["status"], "error")
        self.assertIn("Either page_id or both space_key and title must be provided.", result_no_page_id_no_title["message"])

        result_no_args = get_confluence_page() # This call will also use the mocked getenv
        self.assertEqual(result_no_args["status"], "error")
        self.assertIn("Either page_id or both space_key and title must be provided.", result_no_args["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_by_space_title_not_found(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "size": 0} # Page not found
        mock_requests_get.return_value = mock_response

        result = get_confluence_page(space_key="TEST", title="NonExistent")
        self.assertEqual(result["status"], "not_found")
        self.assertIn("Confluence page with title 'NonExistent' in space 'TEST' not found.", result["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_http_error_404(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        # Simulate a JSON response for the error, though it might not always be present
        mock_response.json.return_value = {"message": "Page not found via API"}
        mock_requests_get.return_value = mock_response

        result = get_confluence_page(page_id="nonexistent_id")
        self.assertEqual(result["status"], "error")
        self.assertIn("Confluence page not found.", result["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_http_error_401(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_response.json.return_value = {"message": "Auth failed"}
        mock_requests_get.return_value = mock_response

        result = get_confluence_page(page_id="123")
        self.assertEqual(result["status"], "error")
        self.assertIn("Confluence authentication failed.", result["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_http_error_403(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_response.json.return_value = {"message": "Forbidden"}
        mock_requests_get.return_value = mock_response

        result = get_confluence_page(page_id="123")
        self.assertEqual(result["status"], "error")
        self.assertIn("Permission denied to access Confluence page.", result["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_request_exception(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_requests_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = get_confluence_page(page_id="123")
        self.assertEqual(result["status"], "error")
        self.assertIn("Error retrieving Confluence page: Connection timed out", result["message"])

    # --- Tests for get_confluence_child_pages ---

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_child_pages_success(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        parent_page_id = "parent_123"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "child_1", "title": "Child Page 1", "_links": {"webui": "/child1", "base": "https://test.atlassian.net"}},
                {"id": "child_2", "title": "Child Page 2", "_links": {"webui": "/child2", "base": "https://test.atlassian.net"}}
            ],
            "size": 2
        }
        mock_requests_get.return_value = mock_response

        result = get_confluence_child_pages(parent_page_id)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["child_pages"]), 2)
        self.assertEqual(result["child_pages"][0]["id"], "child_1")
        self.assertEqual(result["child_pages"][0]["title"], "Child Page 1")
        self.assertEqual(result["child_pages"][0]["link"], "https://test.atlassian.net/child1")
        self.assertEqual(result["child_pages"][1]["id"], "child_2")
        mock_requests_get.assert_called_once()
        called_url = mock_requests_get.call_args[0][0]
        self.assertTrue(called_url.endswith(f"/wiki/rest/api/content/{parent_page_id}/child/page"))

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_child_pages_success_no_children(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        parent_page_id = "parent_456"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "size": 0}
        mock_requests_get.return_value = mock_response

        result = get_confluence_child_pages(parent_page_id)

        self.assertEqual(result["status"], "success") # As per current implementation, success for no children
        self.assertEqual(len(result["child_pages"]), 0)
        self.assertIn(f"No child pages found for parent page ID '{parent_page_id}'", result["message"])

    @patch('os.getenv')
    def test_get_confluence_child_pages_missing_env_vars(self, mock_getenv):
        mock_getenv.return_value = None # Simulate one var missing
        result = get_confluence_child_pages("any_parent_id")
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration", result["message"])

    @patch('os.getenv')
    def test_get_confluence_child_pages_no_parent_id(self, mock_getenv):
        self._setup_mock_env_vars(mock_getenv) # Env vars are fine
        result_empty = get_confluence_child_pages("")
        self.assertEqual(result_empty["status"], "error")
        self.assertIn("Parent Page ID must be provided", result_empty["message"])
        
        result_none = get_confluence_child_pages(None)
        self.assertEqual(result_none["status"], "error")
        self.assertIn("Parent Page ID must be provided", result_none["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_child_pages_http_error_404_parent_not_found(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        parent_page_id = "non_existent_parent"

        mock_error_response = MagicMock()
        mock_error_response.status_code = 404
        mock_error_response.json.return_value = {"message": "Parent not found"}
        mock_error_response.text = '{"message": "Parent not found"}'
        mock_requests_get.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = get_confluence_child_pages(parent_page_id)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Parent Confluence page with ID '{parent_page_id}' not found", result["message"])
        self.assertEqual(result["response_status_code"], 404)

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_child_pages_http_error_401_auth_failed(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        parent_page_id = "parent_789"

        mock_error_response = MagicMock()
        mock_error_response.status_code = 401
        mock_error_response.json.return_value = {"message": "Authentication failed"}
        mock_error_response.text = '{"message": "Authentication failed"}'
        mock_requests_get.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = get_confluence_child_pages(parent_page_id)
        self.assertEqual(result["status"], "error")
        self.assertIn("Confluence authentication failed", result["message"])
        self.assertEqual(result["response_status_code"], 401)

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_child_pages_request_exception(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        parent_page_id = "parent_000"
        mock_requests_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = get_confluence_child_pages(parent_page_id)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Request error retrieving child pages for parent ID '{parent_page_id}': Connection timed out", result["message"])

    # --- Tests for show_confluence_page ---
    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    def test_show_confluence_page_by_id_success(self, mock_get_page, mock_webbrowser_open):
        page_id = "12345"
        page_link = "https://test.atlassian.net/wiki/display/TEST/Test+Page"
        mock_get_page.return_value = {
            "status": "success",
            "page_id": page_id,
            "link": page_link,
            "title": "Test Page",
            "space_key": "TEST"
        }
        mock_webbrowser_open.return_value = True

        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "success")
        self.assertIn(f"Attempted to open Confluence page ID '{page_id}' in browser.", result["message"])
        self.assertIn(page_link, result["message"])
        mock_get_page.assert_called_once_with(page_id=page_id, space_key=None, title=None)
        mock_webbrowser_open.assert_called_once_with(page_link)

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    def test_show_confluence_page_by_space_title_success(self, mock_get_page, mock_webbrowser_open):
        space_key = "MYSPACE"
        title = "My Page Title"
        page_link = "https://test.atlassian.net/wiki/display/MYSPACE/My+Page+Title"
        resolved_page_id = "67890"
        mock_get_page.return_value = {
            "status": "success",
            "page_id": resolved_page_id,
            "link": page_link,
            "title": title,
            "space_key": space_key
        }
        mock_webbrowser_open.return_value = True

        result = show_confluence_page(space_key=space_key, title=title)
        self.assertEqual(result["status"], "success")
        self.assertIn(f"Attempted to open Confluence page ID '{resolved_page_id}' in browser.", result["message"])
        mock_get_page.assert_called_once_with(page_id=None, space_key=space_key, title=title)
        mock_webbrowser_open.assert_called_once_with(page_link)

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    def test_show_confluence_page_get_page_fails(self, mock_get_page, mock_webbrowser_open):
        page_id = "bad_id"
        mock_get_page.return_value = {"status": "error", "message": "Page not found"}

        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Could not retrieve Confluence page with ID '{page_id}'. Error: Page not found", result["message"])
        mock_webbrowser_open.assert_not_called()

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    def test_show_confluence_page_no_link(self, mock_get_page, mock_webbrowser_open):
        page_id = "no_link_id"
        mock_get_page.return_value = {
            "status": "success",
            "page_id": page_id,
            "link": None # No link provided
        }
        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"No web link found for Confluence page ID '{page_id}'.", result["message"])
        mock_webbrowser_open.assert_not_called()

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    def test_show_confluence_page_webbrowser_open_fails(self, mock_get_page, mock_webbrowser_open):
        page_id = "webbrowser_fail_id"
        page_link = "https://some.link"
        mock_get_page.return_value = {"status": "success", "page_id": page_id, "link": page_link}
        mock_webbrowser_open.return_value = False # Simulate browser open failure

        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"Failed to open Confluence page link in browser: {page_link}", result["message"])
        mock_webbrowser_open.assert_called_once_with(page_link)

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    def test_show_confluence_page_webbrowser_open_exception(self, mock_get_page, mock_webbrowser_open):
        page_id = "webbrowser_exception_id"
        page_link = "https://another.link"
        mock_get_page.return_value = {"status": "success", "page_id": page_id, "link": page_link}
        mock_webbrowser_open.side_effect = Exception("Test browser error")

        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "error")
        self.assertIn(f"An error occurred while trying to open Confluence page link {page_link} in browser: Test browser error", result["message"])

    def test_show_confluence_page_insufficient_args(self):
        result = show_confluence_page() # No args
        self.assertEqual(result["status"], "error")
        self.assertIn("Either page_id or both space_key and title must be provided", result["message"])

        result_space_only = show_confluence_page(space_key="TEST")
        self.assertEqual(result_space_only["status"], "error")
        self.assertIn("Either page_id or both space_key and title must be provided", result_space_only["message"])

        result_title_only = show_confluence_page(title="Test Title")
        self.assertEqual(result_title_only["status"], "error")
        self.assertIn("Either page_id or both space_key and title must be provided", result_title_only["message"])

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_show_confluence_page_relative_link_with_wiki_prefix(self, mock_getenv, mock_get_page, mock_webbrowser_open):
        self._setup_mock_env_vars(mock_getenv) # Configure getenv for ATLASSIAN_INSTANCE_URL
        page_id = "rel_wiki_id"
        relative_link = "/wiki/display/TEST/RelPage"
        # ATLASSIAN_INSTANCE_URL from _setup_mock_env_vars is "https://test.atlassian.net"
        expected_link = "https://test.atlassian.net/wiki/display/TEST/RelPage"
        
        mock_get_page.return_value = {
            "status": "success", "page_id": page_id, "link": relative_link, "title": "Test Page"
        }
        mock_webbrowser_open.return_value = True

        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "success")
        mock_webbrowser_open.assert_called_once_with(expected_link)
        self.assertIn(expected_link, result["message"])

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_show_confluence_page_relative_link_without_wiki_prefix(self, mock_getenv, mock_get_page, mock_webbrowser_open):
        self._setup_mock_env_vars(mock_getenv) # Configure getenv
        page_id = "rel_no_wiki_id"
        relative_link = "/display/TEST/RelPage2"
        # Expected: ATLASSIAN_INSTANCE_URL + /wiki + relative_link
        expected_link = "https://test.atlassian.net/wiki/display/TEST/RelPage2"
        
        mock_get_page.return_value = {
            "status": "success", "page_id": page_id, "link": relative_link, "title": "Test Page 2"
        }
        mock_webbrowser_open.return_value = True

        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "success")
        mock_webbrowser_open.assert_called_once_with(expected_link)
        self.assertIn(expected_link, result["message"])

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_show_confluence_page_relative_link_env_var_missing(self, mock_getenv, mock_get_page, mock_webbrowser_open):
        # Simulate ATLASSIAN_INSTANCE_URL is not set when show_confluence_page calls os.getenv
        mock_getenv.side_effect = lambda key, default=None: None if key == "ATLASSIAN_INSTANCE_URL" else {
            "ATLASSIAN_EMAIL": "test@example.com", # Keep others for get_confluence_page if it were real
            "ATLASSIAN_API_KEY": "test_api_key"
        }.get(key, default)

        page_id = "rel_env_missing_id"
        relative_link = "/wiki/display/TEST/RelPage3"
        
        # get_confluence_page is mocked, so it will succeed and return the relative link
        mock_get_page.return_value = {
            "status": "success", "page_id": page_id, "link": relative_link, "title": "Test Page 3"
        }
        mock_webbrowser_open.return_value = True

        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "success") 
        # Expects to open the relative link as is, because ATLASSIAN_INSTANCE_URL was missing for prefixing
        mock_webbrowser_open.assert_called_once_with(relative_link)
        self.assertIn(relative_link, result["message"])

    @patch('webbrowser.open')
    @patch('tools.confluence_tools.get_confluence_page')
    @patch('os.getenv')
    def test_show_confluence_page_absolute_link_no_change(self, mock_getenv, mock_get_page, mock_webbrowser_open):
        self._setup_mock_env_vars(mock_getenv) # Env var is available
        page_id = "abs_link_id"
        absolute_link = "https://my.custom.confluence/wiki/display/ANY/AbsPage"
        
        mock_get_page.return_value = {
            "status": "success", "page_id": page_id, "link": absolute_link, "title": "Absolute Page"
        }
        mock_webbrowser_open.return_value = True

        result = show_confluence_page(page_id=page_id)
        self.assertEqual(result["status"], "success")
        # Absolute link should not be changed
        mock_webbrowser_open.assert_called_once_with(absolute_link)
        self.assertIn(absolute_link, result["message"])

    # --- Tests for search_confluence_cql ---
    @patch('requests.get')
    @patch('os.getenv')
    def test_search_confluence_cql_success_with_results(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        cql_query = "type = page and space = TEST"
        limit = 10
        start = 0
        expand = "content.body.view"

        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "results": [
                {
                    "content": {
                        "id": "123", "title": "Test Page 1", "type": "page",
                        "_links": {"webui": "/display/TEST/Test+Page+1", "base": "https://test.atlassian.net"}
                    },
                    "excerpt": "Excerpt for page 1",
                    "url": "api/link/123"
                },
                {
                    "content": {
                        "id": "456", "title": "Test Blogpost 1", "type": "blogpost",
                        "_links": {"webui": "/display/TEST/Test+Blogpost+1"} # Test relative link without base in content
                    },
                    "excerpt": "Excerpt for blogpost 1",
                    "url": "api/link/456"
                }
            ],
            "totalSize": 2,
            "limit": limit,
            "start": start
        }
        mock_requests_get.return_value = mock_search_response

        result = search_confluence_cql(cql_query, limit=limit, start=start, expand=expand)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["total_size"], 2)
        self.assertEqual(result["results"][0]["id"], "123")
        self.assertEqual(result["results"][0]["title"], "Test Page 1")
        self.assertEqual(result["results"][0]["link"], "https://test.atlassian.net/display/TEST/Test+Page+1")
        self.assertEqual(result["results"][1]["id"], "456")
        self.assertEqual(result["results"][1]["title"], "Test Blogpost 1")
        self.assertEqual(result["results"][1]["link"], "https://test.atlassian.net/display/TEST/Test+Blogpost+1") # Assuming base from instance URL
        
        mock_requests_get.assert_called_once()
        called_url = mock_requests_get.call_args[0][0]
        self.assertTrue(called_url.endswith("/wiki/rest/api/search"))
        called_params = mock_requests_get.call_args[1]['params']
        self.assertEqual(called_params["cql"], cql_query)
        self.assertEqual(called_params["limit"], limit)
        self.assertEqual(called_params["start"], start)
        self.assertEqual(called_params["expand"], expand)

    @patch('requests.get')
    @patch('os.getenv')
    def test_search_confluence_cql_success_no_results(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        cql_query = "label = non_existent_label"

        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "results": [], "totalSize": 0, "limit": 25, "start": 0
        }
        mock_requests_get.return_value = mock_search_response

        result = search_confluence_cql(cql_query)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["results"]), 0)
        self.assertEqual(result["total_size"], 0)
        self.assertIn("Found 0 results", result["message"])

    @patch('os.getenv')
    def test_search_confluence_cql_env_vars_missing(self, mock_getenv):
        mock_getenv.return_value = None # Simulate one var missing
        result = search_confluence_cql("any query")
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration", result["message"])

    @patch('os.getenv')
    def test_search_confluence_cql_empty_query(self, mock_getenv):
        self._setup_mock_env_vars(mock_getenv)
        result = search_confluence_cql("")
        self.assertEqual(result["status"], "error")
        self.assertIn("CQL query must be provided", result["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_search_confluence_cql_http_error_400_bad_cql(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_error_response = MagicMock()
        mock_error_response.status_code = 400
        error_json = {"errorMessages": ["Invalid CQL: some error"], "message": "Bad request from API"}
        mock_error_response.json.return_value = error_json
        mock_error_response.text = json.dumps(error_json)
        mock_requests_get.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = search_confluence_cql("invalid cql here")
        self.assertEqual(result["status"], "error")
        self.assertIn("Bad request during Confluence search (Code 400)", result["message"])
        self.assertIn("Details: Invalid CQL: some error", result["message"])
        self.assertEqual(result["response_status_code"], 400)

    @patch('requests.get')
    @patch('os.getenv')
    def test_search_confluence_cql_http_error_401_auth(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_error_response = MagicMock()
        mock_error_response.status_code = 401
        mock_error_response.json.return_value = {"message": "Auth failed by API"}
        mock_error_response.text = '{"message": "Auth failed by API"}'
        mock_requests_get.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = search_confluence_cql("type=page")
        self.assertEqual(result["status"], "error")
        self.assertIn("Confluence authentication failed (Code 401)", result["message"])
        self.assertIn("Details: Auth failed by API", result["message"])
        self.assertEqual(result["response_status_code"], 401)

    @patch('requests.get')
    @patch('os.getenv')
    def test_search_confluence_cql_http_error_403_permission(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_error_response = MagicMock()
        mock_error_response.status_code = 403
        mock_error_response.json.return_value = {"message": "Permission denied by API"}
        mock_error_response.text = '{"message": "Permission denied by API"}'
        mock_requests_get.side_effect = requests.exceptions.HTTPError(response=mock_error_response)

        result = search_confluence_cql("type=page")
        self.assertEqual(result["status"], "error")
        self.assertIn("Permission denied for Confluence search (Code 403)", result["message"])
        self.assertIn("Details: Permission denied by API", result["message"])
        self.assertEqual(result["response_status_code"], 403)

    @patch('requests.get')
    @patch('os.getenv')
    def test_search_confluence_cql_request_exception(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        mock_requests_get.side_effect = requests.exceptions.Timeout("Connection timed out for search")

        result = search_confluence_cql("type=page")
        self.assertEqual(result["status"], "error")
        self.assertIn("Request error during Confluence search: Connection timed out for search", result["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_search_confluence_cql_fallback_link_construction(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        cql_query = "type = page and id = 789"
        
        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "results": [
                {
                    "content": {
                        "id": "789", "title": "Page With No WebUI Link", "type": "page",
                        "space": {"key": "NOSPC"},
                        "_links": {} # No webui or base link in content._links
                    },
                    "excerpt": "Excerpt for page with no webui",
                    "url": "api/link/789"
                }
            ],
            "totalSize": 1, "limit": 25, "start": 0
        }
        mock_requests_get.return_value = mock_search_response

        result = search_confluence_cql(cql_query)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["id"], "789")
        # Expect fallback link construction
        expected_link = "https://test.atlassian.net/wiki/spaces/NOSPC/pages/789"
        self.assertEqual(result["results"][0]["link"], expected_link)

    # --- Tests for show_confluence_version_comparison ---

    @patch('tools.confluence_tools.webbrowser.open')
    @patch('os.getenv')
    def test_show_confluence_version_comparison_success(self, mock_getenv, mock_webbrowser_open):
        # Arrange
        mock_getenv.return_value = "https://test.atlassian.net"
        mock_webbrowser_open.return_value = True
        page_id = "12345"
        version_1 = 5
        version_2 = 10
        expected_url = f"https://test.atlassian.net/wiki/pages/diffpagesbyversion.action?pageId={page_id}&selectedPageVersions={version_1}&selectedPageVersions={version_2}"

        # Act
        result = show_confluence_version_comparison(page_id, version_1, version_2)

        # Assert
        mock_getenv.assert_called_once_with("ATLASSIAN_INSTANCE_URL")
        mock_webbrowser_open.assert_called_once_with(expected_url)
        self.assertEqual(result['status'], 'success')
        self.assertIn(f"Attempted to open comparison for page ID '{page_id}' (versions {version_1} and {version_2})", result['message'])

    @patch('tools.confluence_tools.webbrowser.open')
    @patch('os.getenv')
    def test_show_confluence_version_comparison_version_order_swapped(self, mock_getenv, mock_webbrowser_open):
        # Arrange
        mock_getenv.return_value = "https://test.atlassian.net"
        mock_webbrowser_open.return_value = True
        page_id = "12345"
        version_1 = 10 # larger
        version_2 = 5  # smaller
        # The function should order them, so 5 comes before 10 in the URL
        expected_url = f"https://test.atlassian.net/wiki/pages/diffpagesbyversion.action?pageId={page_id}&selectedPageVersions=5&selectedPageVersions=10"

        # Act
        result = show_confluence_version_comparison(page_id, version_1, version_2)

        # Assert
        mock_webbrowser_open.assert_called_once_with(expected_url)
        self.assertEqual(result['status'], 'success')
        self.assertIn("versions 5 and 10", result['message'])

    @patch('tools.confluence_tools.webbrowser.open')
    @patch('os.getenv')
    def test_show_confluence_version_comparison_no_instance_url(self, mock_getenv, mock_webbrowser_open):
        # Arrange
        mock_getenv.return_value = None

        # Act
        result = show_confluence_version_comparison("123", 1, 2)

        # Assert
        mock_getenv.assert_called_once_with("ATLASSIAN_INSTANCE_URL")
        mock_webbrowser_open.assert_not_called()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], "ATLASSIAN_INSTANCE_URL environment variable is not set.")

    @patch('tools.confluence_tools.webbrowser.open')
    @patch('os.getenv')
    def test_show_confluence_version_comparison_invalid_inputs(self, mock_getenv, mock_webbrowser_open):
        # Arrange
        mock_getenv.return_value = "https://test.atlassian.net"

        # Test with missing page_id
        result_no_id = show_confluence_version_comparison("", 1, 2)
        self.assertEqual(result_no_id['status'], 'error')
        self.assertEqual(result_no_id['message'], "Page ID and two integer version numbers must be provided.")

        # Test with non-integer version
        result_bad_version = show_confluence_version_comparison("123", 1, "two")
        self.assertEqual(result_bad_version['status'], 'error')
        self.assertEqual(result_bad_version['message'], "Page ID and two integer version numbers must be provided.")

        # Assert that webbrowser.open was not called for these invalid input cases
        mock_webbrowser_open.assert_not_called()

    @patch('tools.confluence_tools.webbrowser.open')
    @patch('os.getenv')
    def test_show_confluence_version_comparison_webbrowser_fails(self, mock_getenv, mock_webbrowser_open):
        # Arrange
        mock_getenv.return_value = "https://test.atlassian.net"
        mock_webbrowser_open.return_value = False
        page_id = "12345"
        version_1 = 1
        version_2 = 2
        expected_url = f"https://test.atlassian.net/wiki/pages/diffpagesbyversion.action?pageId={page_id}&selectedPageVersions={version_1}&selectedPageVersions={version_2}"

        # Act
        result = show_confluence_version_comparison(page_id, version_1, version_2)

        # Assert
        mock_webbrowser_open.assert_called_once_with(expected_url)
        self.assertEqual(result['status'], 'error')
        self.assertIn("Failed to open Confluence page comparison link in browser", result['message'])

    @patch('tools.confluence_tools.webbrowser.open')
    @patch('os.getenv')
    def test_show_confluence_version_comparison_webbrowser_raises_exception(self, mock_getenv, mock_webbrowser_open):
        # Arrange
        mock_getenv.return_value = "https://test.atlassian.net"
        mock_webbrowser_open.side_effect = Exception("Test exception")
        page_id = "12345"
        version_1 = 1
        version_2 = 2
        expected_url = f"https://test.atlassian.net/wiki/pages/diffpagesbyversion.action?pageId={page_id}&selectedPageVersions={version_1}&selectedPageVersions={version_2}"

        # Act
        result = show_confluence_version_comparison(page_id, version_1, version_2)

        # Assert
        mock_webbrowser_open.assert_called_once_with(expected_url)
        self.assertEqual(result['status'], 'error')
        self.assertIn("An error occurred while trying to open Confluence page comparison link", result['message'])
        self.assertIn("Test exception", result['message'])


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
