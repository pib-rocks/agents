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
    delete_confluence_page
)

class TestConfluenceTools(unittest.TestCase):

    # --- Tests for placeholder functions (create, update, delete) ---
    @patch('builtins.print') # Mock print to avoid console output during tests
    def test_create_confluence_page(self, mock_print):
        space_key = "TESTSPACE"
        title = "Test Page Title"
        body = "This is the body of the test page."
        parent_id = "123"
        
        result = create_confluence_page(space_key, title, body, parent_id)
        
        self.assertEqual(result["status"], "success")
        self.assertIn(title, result["message"])
        self.assertIn(space_key, result["message"])
        self.assertIn("page_id", result)
        mock_print.assert_called_once_with(f"Attempting to create Confluence page: Space='{space_key}', Title='{title}', ParentID='{parent_id}'")

    @patch('builtins.print')
    def test_create_confluence_page_no_parent(self, mock_print):
        space_key = "TESTSPACE"
        title = "Test Page No Parent"
        body = "Body content."
        
        result = create_confluence_page(space_key, title, body)
        
        self.assertEqual(result["status"], "success")
        self.assertIn(title, result["message"])
        self.assertIn("page_id", result)
        mock_print.assert_called_once_with(f"Attempting to create Confluence page: Space='{space_key}', Title='{title}', ParentID='{None}'")

    @patch('builtins.print')
    def test_update_confluence_page(self, mock_print):
        page_id = "67890"
        new_title = "Updated Page Title"
        new_body = "Updated body content."
        
        result = update_confluence_page(page_id, new_title=new_title, new_body=new_body)
        
        self.assertEqual(result["status"], "success")
        self.assertIn(f"Confluence page ID '{page_id}' updated successfully.", result["message"])
        mock_print.assert_called_once_with(f"Attempting to update Confluence page ID: '{page_id}' with Title='{new_title}', ParentID='{None}'")

    @patch('builtins.print')
    def test_update_confluence_page_no_changes(self, mock_print):
        page_id = "67890"
        result = update_confluence_page(page_id)
        
        self.assertEqual(result["status"], "info")
        self.assertIn("No changes provided for update.", result["message"])
        mock_print.assert_called_once_with(f"Attempting to update Confluence page ID: '{page_id}' with Title='{None}', ParentID='{None}'")


    @patch('builtins.print')
    def test_delete_confluence_page(self, mock_print):
        page_id = "13579"
        result = delete_confluence_page(page_id)
        
        self.assertEqual(result["status"], "success")
        self.assertIn(f"Confluence page ID '{page_id}' deleted successfully.", result["message"])
        mock_print.assert_called_once_with(f"Attempting to delete Confluence page ID: '{page_id}'")

    # --- Tests for get_confluence_page (implemented function) ---

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_by_id_success(self, mock_getenv, mock_requests_get):
        # Setup mock environment variables
        mock_getenv.side_effect = lambda key: {
            "ATLASSIAN_INSTANCE_URL": "https://test.atlassian.net/wiki",
            "ATLASSIAN_EMAIL": "test@example.com",
            "ATLASSIAN_API_KEY": "test_api_key"
        }.get(key)

        # Setup mock response from requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_page_data = {
            "id": "12345", 
            "title": "Test Page", 
            "space": {"key": "TEST"},
            "body": {"storage": {"value": "<p>Test content</p>"}},
            "version": {"number": 2},
            "_links": {"webui": "/display/TEST/Test+Page", "base": "https://test.atlassian.net/wiki"}#AI! This line is not interpreted correctly in this test-case, fix it
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
        mock_getenv.side_effect = lambda key: {
            "ATLASSIAN_INSTANCE_URL": "https://test.atlassian.net/wiki",
            "ATLASSIAN_EMAIL": "test@example.com",
            "ATLASSIAN_API_KEY": "test_api_key"
        }.get(key)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_page_data = {
            "results": [{
                "id": "67890", 
                "title": "My Page Title", 
                "space": {"key": "MYSPACE"},
                "body": {"storage": {"value": "Content here"}},
                "version": {"number": 1},
                "_links": {"webui": "/display/MYSPACE/My+Page+Title"}
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

    def test_get_confluence_page_insufficient_args(self):
        # This test doesn't need os.getenv or requests.get mocks as it fails earlier
        result_no_page_id_no_title = get_confluence_page(space_key="MYSAPCE")
        self.assertEqual(result_no_page_id_no_title["status"], "error")
        self.assertIn("Either page_id or both space_key and title must be provided.", result_no_page_id_no_title["message"])

        result_no_args = get_confluence_page()
        self.assertEqual(result_no_args["status"], "error")
        self.assertIn("Either page_id or both space_key and title must be provided.", result_no_args["message"])

    @patch('requests.get')
    @patch('os.getenv')
    def test_get_confluence_page_by_space_title_not_found(self, mock_getenv, mock_requests_get):
        mock_getenv.side_effect = lambda key: "test_value" # Provide some value for env vars
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
        mock_getenv.side_effect = lambda key: "test_value"
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
        mock_getenv.side_effect = lambda key: "test_value"
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
        mock_getenv.side_effect = lambda key: "test_value"
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
        mock_getenv.side_effect = lambda key: "test_value"
        mock_requests_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = get_confluence_page(page_id="123")
        self.assertEqual(result["status"], "error")
        self.assertIn("Error retrieving Confluence page: Connection timed out", result["message"])

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
