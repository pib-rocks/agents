import unittest
from unittest.mock import patch
import sys
import os

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
    def test_get_confluence_page_by_id(self, mock_print):
        page_id = "12345"
        result = get_confluence_page(page_id=page_id)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["page_id"], page_id)
        self.assertIn("title", result)
        self.assertIn("body", result)
        mock_print.assert_called_once_with(f"Attempting to get Confluence page by ID: '{page_id}'")

    @patch('builtins.print')
    def test_get_confluence_page_by_space_and_title(self, mock_print):
        space_key = "MYSPACE"
        title = "My Page Title"
        result = get_confluence_page(page_id=None, space_key=space_key, title=title)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["space_key"], space_key)
        self.assertEqual(result["title"], title)
        self.assertIn("page_id", result)
        mock_print.assert_called_once_with(f"Attempting to get Confluence page by Space='{space_key}', Title='{title}'")

    def test_get_confluence_page_insufficient_args(self):
        result = get_confluence_page(page_id=None, space_key="MYSAPCE", title=None)
        self.assertEqual(result["status"], "error")
        self.assertIn("Either page_id or both space_key and title must be provided.", result["message"])

        result_no_args = get_confluence_page(page_id=None, space_key=None, title=None)
        self.assertEqual(result_no_args["status"], "error")

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

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
