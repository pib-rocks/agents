import unittest
from unittest.mock import patch, MagicMock
import os
import json
import requests # Import the requests library

# Assuming tools.jira_tools is accessible in the PYTHONPATH
# Adjust the import path if your project structure is different
from tools.jira_tools import get_jira_issue_links, get_jira_issue_details, CUSTOM_FIELD_CATEGORY_ID, search_jira_issues_jql

class TestGetJiraIssueLinks(unittest.TestCase):

    def _setup_mock_env_vars(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "ATLASSIAN_INSTANCE_URL": "https://test.atlassian.net",
            "ATLASSIAN_EMAIL": "test@example.com",
            "ATLASSIAN_API_KEY": "test_api_key"
        }.get(key, default)

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_success_no_links(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-123"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "issuelinks": []
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["report"], f"No issue links found for issue '{issue_id}'.")
        mock_requests_get.assert_called_once_with(
            f"https://test.atlassian.net/rest/api/3/issue/{issue_id}?fields=issuelinks",
            headers={"Accept": "application/json"},
            auth=("test@example.com", "test_api_key"),
            timeout=15
        )

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_success_with_inward_link(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-123"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "issuelinks": [
                    {
                        "type": {"name": "Blocks", "inward": "is blocked by"},
                        "inwardIssue": {
                            "key": "PROJ-456",
                            "fields": {"summary": "Another Task", "status": {"name": "Open"}}
                        }
                    }
                ]
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)

        self.assertEqual(result["status"], "success")
        expected_report_lines = [
            f"Issue links for {issue_id}:",
            "  - Type: Blocks, Direction: is blocked by PROJ-456 (Status: Open, Summary: Another Task)"
        ]
        self.assertEqual(result["report"], "\n".join(expected_report_lines))

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_success_with_outward_link(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-123"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "issuelinks": [
                    {
                        "type": {"name": "Relates", "outward": "relates to"},
                        "outwardIssue": {
                            "key": "PROJ-789",
                            "fields": {"summary": "Related Story", "status": {"name": "In Progress"}}
                        }
                    }
                ]
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)

        self.assertEqual(result["status"], "success")
        expected_report_lines = [
            f"Issue links for {issue_id}:",
            "  - Type: Relates, Direction: relates to PROJ-789 (Status: In Progress, Summary: Related Story)"
        ]
        self.assertEqual(result["report"], "\n".join(expected_report_lines))

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_success_with_multiple_links(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-123"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "issuelinks": [
                    {
                        "type": {"name": "Blocks", "inward": "is blocked by"},
                        "inwardIssue": {
                            "key": "PROJ-456",
                            "fields": {"summary": "Blocker Task", "status": {"name": "Done"}}
                        }
                    },
                    {
                        "type": {"name": "Relates", "outward": "relates to"},
                        "outwardIssue": {
                            "key": "PROJ-789",
                            "fields": {"summary": "Related Story", "status": {"name": "To Do"}}
                        }
                    }
                ]
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "success")
        # Order of links in the report should match the order from the API
        expected_report_lines = [
            f"Issue links for {issue_id}:",
            "  - Type: Blocks, Direction: is blocked by PROJ-456 (Status: Done, Summary: Blocker Task)",
            "  - Type: Relates, Direction: relates to PROJ-789 (Status: To Do, Summary: Related Story)"
        ]
        self.assertEqual(result["report"], "\n".join(expected_report_lines))


    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_missing_env_vars(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: None # Simulate no env vars
        issue_id = "PROJ-123"
        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration", result["error_message"])

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_http_error_401(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-123"

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Unauthorized")
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], "Jira authentication failed. Check email/API key.")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_http_error_403(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-FORBIDDEN"

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Forbidden")
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], f"Jira permission denied for accessing issue links for '{issue_id}'.")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_http_error_404(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-NOTFOUND"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], f"Jira issue '{issue_id}' not found.")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_other_http_error(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-ERROR"
        http_error_message = "500 Server Error"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(http_error_message)
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], f"HTTP error occurred while fetching issue links: {http_error_message}")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_request_exception(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-REQEX"
        req_exception_message = "Connection timed out"

        mock_requests_get.side_effect = requests.exceptions.RequestException(req_exception_message)

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], f"Error fetching issue links: {req_exception_message}")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_malformed_response_no_fields(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-BADJSON1"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {} # Missing 'fields'
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "success") # Should still be success as per current implementation
        self.assertEqual(result["report"], f"No issue links found for issue '{issue_id}'.")


    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_malformed_response_no_issuelinks(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-BADJSON2"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"fields": {}} # Missing 'issuelinks'
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "success") # Should still be success
        self.assertEqual(result["report"], f"No issue links found for issue '{issue_id}'.")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_issue_links_link_data_incomplete(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-INCMPLTE"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "issuelinks": [
                    { # Missing type.name
                        "type": {"inward": "is blocked by"},
                        "inwardIssue": {
                            "key": "PROJ-456",
                            "fields": {"summary": "Another Task", "status": {"name": "Open"}}
                        }
                    },
                    { # Missing inwardIssue.key
                        "type": {"name": "Relates", "outward": "relates to"},
                        "outwardIssue": {
                            "fields": {"summary": "Related Story", "status": {"name": "In Progress"}}
                        }
                    },
                    { # Missing outwardIssue.fields.summary
                        "type": {"name": "Depends", "outward": "depends on"},
                        "outwardIssue": {
                            "key": "PROJ-789",
                            "fields": {"status": {"name": "Closed"}}
                        }
                    },
                     { # Missing outwardIssue.fields.status
                        "type": {"name": "Tests", "outward": "tests"},
                        "outwardIssue": {
                            "key": "PROJ-ABC",
                            "fields": {"summary": "Test Case"}
                        }
                    }
                ]
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_links(issue_id)
        self.assertEqual(result["status"], "success")
        expected_report_lines = [
            f"Issue links for {issue_id}:",
            "  - Type: N/A, Direction: is blocked by PROJ-456 (Status: Open, Summary: Another Task)",
            "  - Type: Relates, Direction: relates to N/A (Status: In Progress, Summary: Related Story)",
            "  - Type: Depends, Direction: depends on PROJ-789 (Status: Closed, Summary: N/A)",
            "  - Type: Tests, Direction: tests PROJ-ABC (Status: N/A, Summary: Test Case)"
        ]
        self.assertEqual(result["report"], "\n".join(expected_report_lines))


class TestGetJiraIssueDetails(unittest.TestCase):

    def _setup_mock_env_vars(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "ATLASSIAN_INSTANCE_URL": "https://test.atlassian.net",
            "ATLASSIAN_EMAIL": "test@example.com",
            "ATLASSIAN_API_KEY": "test_api_key"
        }.get(key, default)

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_success_plain_text_default(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-1"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "summary": "Test Summary",
                "status": {"name": "Open"},
                "assignee": {"displayName": "Test User"},
                CUSTOM_FIELD_CATEGORY_ID: {"value": "Test Category"},
                "description": {
                    "type": "doc", "version": 1, "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Hello world."}]}
                    ]
                }
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id) # render_html=False by default

        self.assertEqual(result["status"], "success")
        expected_report = (
            f"Issue {issue_id}:\n"
            f"  Summary: Test Summary\n"
            f"  Status: Open\n"
            f"  Assignee: Test User\n"
            f"  Category: Test Category\n"
            f"  Description: Hello world."
        )
        self.assertEqual(result["report"], expected_report)
        mock_requests_get.assert_called_once_with(
            f"https://test.atlassian.net/rest/api/3/issue/{issue_id}",
            headers={"Accept": "application/json"},
            auth=("test@example.com", "test_api_key"),
            params={"fields": f"summary,status,assignee,description,{CUSTOM_FIELD_CATEGORY_ID}"},
            timeout=15
        )

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_success_render_html_provided(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-2"
        html_description_content = "<p>Hello <b>HTML</b> world.</p>"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "renderedFields": {
                "description": html_description_content
            },
            "fields": {
                "summary": "HTML Test",
                "status": {"name": "In Progress"},
                "assignee": None, # Unassigned
                CUSTOM_FIELD_CATEGORY_ID: {"value": "Frontend"},
                "description": {"type": "doc", "version": 1, "content": []} # ADF might still exist
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id, render_html=True)

        self.assertEqual(result["status"], "success")
        expected_report = (
            f"Issue {issue_id}:\n"
            f"  Summary: HTML Test\n"
            f"  Status: In Progress\n"
            f"  Assignee: Unassigned\n"
            f"  Category: Frontend\n"
            f"  Description: {html_description_content}"
        )
        self.assertEqual(result["report"], expected_report)
        mock_requests_get.assert_called_once_with(
            f"https://test.atlassian.net/rest/api/3/issue/{issue_id}",
            headers={"Accept": "application/json"},
            auth=("test@example.com", "test_api_key"),
            params={"fields": f"summary,status,assignee,description,{CUSTOM_FIELD_CATEGORY_ID}", "expand": "renderedFields"},
            timeout=15
        )

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_success_render_html_fallback_to_adf(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-3"
        adf_description_text = "ADF fallback content."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "renderedFields": { # HTML description explicitly missing or null
                "description": None
            },
            "fields": {
                "summary": "Fallback Test",
                "status": {"name": "Done"},
                "assignee": {"displayName": "QA"},
                CUSTOM_FIELD_CATEGORY_ID: None, # Category not set
                "description": {
                    "type": "doc", "version": 1, "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": adf_description_text}]}
                    ]
                }
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id, render_html=True)

        self.assertEqual(result["status"], "success")
        expected_description = f"{adf_description_text} (Fallback: plain text from ADF, HTML not available)"
        expected_report = (
            f"Issue {issue_id}:\n"
            f"  Summary: Fallback Test\n"
            f"  Status: Done\n"
            f"  Assignee: QA\n"
            f"  Category: N/A\n" # Category should be N/A if not set or data is not dict
            f"  Description: {expected_description}"
        )
        self.assertEqual(result["report"], expected_report)
        mock_requests_get.assert_called_once_with(
            f"https://test.atlassian.net/rest/api/3/issue/{issue_id}",
            headers={"Accept": "application/json"},
            auth=("test@example.com", "test_api_key"),
            params={"fields": f"summary,status,assignee,description,{CUSTOM_FIELD_CATEGORY_ID}", "expand": "renderedFields"},
            timeout=15
        )

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_success_no_description_plain_text(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-4"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "summary": "No Desc Test",
                "status": {"name": "Open"},
                "assignee": None,
                CUSTOM_FIELD_CATEGORY_ID: {"value": "Backend"},
                "description": None # No description field
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id) # render_html=False

        self.assertEqual(result["status"], "success")
        expected_report = (
            f"Issue {issue_id}:\n"
            f"  Summary: No Desc Test\n"
            f"  Status: Open\n"
            f"  Assignee: Unassigned\n"
            f"  Category: Backend\n"
            f"  Description: No description provided."
        )
        self.assertEqual(result["report"], expected_report)

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_success_no_description_render_html(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-5"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "renderedFields": {"description": None},
            "fields": {
                "summary": "No Desc HTML Test",
                "status": {"name": "Open"},
                "assignee": None,
                CUSTOM_FIELD_CATEGORY_ID: {"value": "General"},
                "description": None
            }
        }
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id, render_html=True)

        self.assertEqual(result["status"], "success")
        expected_report = (
            f"Issue {issue_id}:\n"
            f"  Summary: No Desc HTML Test\n"
            f"  Status: Open\n"
            f"  Assignee: Unassigned\n"
            f"  Category: General\n"
            f"  Description: No description provided." # No fallback message if ADF was also None
        )
        self.assertEqual(result["report"], expected_report)

    @patch('tools.jira_tools.os.getenv')
    def test_get_details_missing_env_vars(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: None # Simulate no env vars
        issue_id = "PROJ-ENV"
        result = get_jira_issue_details(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration", result["error_message"])

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_http_error_401(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-AUTH"
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Unauthorized")
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], "Jira authentication failed. Check email/API key.")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_http_error_403(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-FORBID"
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Forbidden")
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], "Jira permission denied.")


    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_http_error_404(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-NF"
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], f"Jira issue '{issue_id}' not found (404).")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_other_http_error(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-HTTPERR"
        http_error_message = "500 Server Error"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(http_error_message)
        mock_requests_get.return_value = mock_response

        result = get_jira_issue_details(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], f"HTTP error occurred: {http_error_message}")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_request_exception(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-REQEX"
        req_exception_message = "Connection problem"
        mock_requests_get.side_effect = requests.exceptions.RequestException(req_exception_message)

        result = get_jira_issue_details(issue_id)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], f"An error occurred: {req_exception_message}")

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_adf_complex_format_plain_text(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-ADFCOMPLEX"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "summary": "Complex ADF", "status": {"name": "Open"}, "assignee": None,
                CUSTOM_FIELD_CATEGORY_ID: {"value": "Docs"},
                "description": {"type": "doc", "version": 1, "content": [{"type": "table", "content": []}]} # Example of complex ADF
            }
        }
        mock_requests_get.return_value = mock_response
        result = get_jira_issue_details(issue_id)
        self.assertIn("[Complex Description Format]", result["report"])

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_adf_complex_format_html_fallback(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-ADFCOMPLEXHTML"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "renderedFields": {"description": None},
            "fields": {
                "summary": "Complex ADF HTML Fallback", "status": {"name": "Open"}, "assignee": None,
                CUSTOM_FIELD_CATEGORY_ID: {"value": "Tech"},
                "description": {"type": "doc", "version": 1, "content": [{"type": "table", "content": []}]}
            }
        }
        mock_requests_get.return_value = mock_response
        result = get_jira_issue_details(issue_id, render_html=True)
        self.assertIn("[Complex Description Format - Fallback from HTML request]", result["report"])

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_plain_string_description_plain_text(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-STRDESC"
        plain_desc = "This is a plain string description."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "summary": "String Desc", "status": {"name": "Open"}, "assignee": None,
                CUSTOM_FIELD_CATEGORY_ID: {"value": "Misc"},
                "description": plain_desc
            }
        }
        mock_requests_get.return_value = mock_response
        result = get_jira_issue_details(issue_id)
        self.assertIn(f"Description: {plain_desc}", result["report"])

    @patch('tools.jira_tools.requests.get')
    @patch('tools.jira_tools.os.getenv')
    def test_get_details_plain_string_description_html_fallback(self, mock_getenv, mock_requests_get):
        self._setup_mock_env_vars(mock_getenv)
        issue_id = "PROJ-STRDESCHTML"
        plain_desc = "This is a plain string description for HTML fallback."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "renderedFields": {"description": None},
            "fields": {
                "summary": "String Desc HTML", "status": {"name": "Open"}, "assignee": None,
                CUSTOM_FIELD_CATEGORY_ID: {"value": "Misc"},
                "description": plain_desc
            }
        }
        mock_requests_get.return_value = mock_response
        result = get_jira_issue_details(issue_id, render_html=True)
        expected_desc_text = f"{plain_desc} (Fallback: plain text from ADF, HTML not available)"
        self.assertIn(f"Description: {expected_desc_text}", result["report"])


class TestSearchJiraIssuesJQL(unittest.TestCase):

    def _setup_mock_env_vars(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "ATLASSIAN_INSTANCE_URL": "https://test.atlassian.net",
            "ATLASSIAN_EMAIL": "test@example.com",
            "ATLASSIAN_API_KEY": "test_api_key"
        }.get(key, default)

    @patch('tools.jira_tools.requests.post')
    @patch('tools.jira_tools.os.getenv')
    def test_search_success_with_results_default_fields(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        jql_query = "project = TEST"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "Test Issue 1",
                        "status": {"name": "Open"},
                        "assignee": {"displayName": "User A"},
                        "reporter": {"displayName": "User B"},
                        "created": "2023-01-01T10:00:00.000+0000",
                        "updated": "2023-01-02T10:00:00.000+0000"
                    }
                },
                {
                    "key": "TEST-2",
                    "fields": {
                        "summary": "Test Issue 2",
                        "status": {"name": "In Progress"},
                        "assignee": None, # Unassigned
                        "reporter": {"displayName": "User C"},
                        "created": "2023-01-03T10:00:00.000+0000",
                        "updated": "2023-01-04T10:00:00.000+0000"
                    }
                }
            ],
            "maxResults": 50,
            "total": 2
        }
        mock_requests_post.return_value = mock_response

        result = search_jira_issues_jql(jql_query)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["issues"]), 2)
        self.assertEqual(result["issues"][0]["key"], "TEST-1")
        self.assertEqual(result["issues"][0]["summary"], "Test Issue 1")
        self.assertEqual(result["issues"][0]["assignee"], "User A")
        self.assertEqual(result["issues"][1]["key"], "TEST-2")
        self.assertEqual(result["issues"][1]["assignee"], None)
        self.assertIn("Found 2 issue(s) matching JQL", result["report"])
        
        expected_payload = {
            "jql": jql_query,
            "maxResults": 50,
            "fields": ["summary", "status", "assignee", "reporter", "created", "updated"]
        }
        mock_requests_post.assert_called_once_with(
            "https://test.atlassian.net/rest/api/3/search",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            auth=("test@example.com", "test_api_key"),
            data=json.dumps(expected_payload),
            timeout=30
        )

    @patch('tools.jira_tools.requests.post')
    @patch('tools.jira_tools.os.getenv')
    def test_search_success_with_custom_fields_and_max_results(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        jql_query = "assignee = currentUser()"
        custom_fields = ["summary", "customfield_10001", "labels"]
        max_res = 10

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issues": [
                {
                    "key": "TEST-3",
                    "fields": {
                        "summary": "Custom Field Test",
                        "customfield_10001": {"value": "OptionA"}, # Single select custom field
                        "labels": ["label1", "label2"] # List of strings
                    }
                }
            ],
            "maxResults": max_res,
            "total": 1
        }
        mock_requests_post.return_value = mock_response

        result = search_jira_issues_jql(jql_query, fields=custom_fields, max_results=max_res)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(result["issues"][0]["key"], "TEST-3")
        self.assertEqual(result["issues"][0]["customfield_10001"], "OptionA")
        self.assertEqual(result["issues"][0]["labels"], ["label1", "label2"])
        self.assertIn(f"Found 1 issue(s) matching JQL (returning up to {max_res})", result["report"])

        expected_payload = {
            "jql": jql_query,
            "maxResults": max_res,
            "fields": custom_fields
        }
        mock_requests_post.assert_called_once_with(
            "https://test.atlassian.net/rest/api/3/search",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            auth=("test@example.com", "test_api_key"),
            data=json.dumps(expected_payload),
            timeout=30
        )

    @patch('tools.jira_tools.requests.post')
    @patch('tools.jira_tools.os.getenv')
    def test_search_success_no_results(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        jql_query = "project = XYZ AND status = Resolved"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"issues": [], "maxResults": 50, "total": 0}
        mock_requests_post.return_value = mock_response

        result = search_jira_issues_jql(jql_query)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["issues"]), 0)
        self.assertIn(f"No issues found matching the JQL query: {jql_query}", result["report"])

    @patch('tools.jira_tools.os.getenv')
    def test_search_missing_env_vars(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: None # Simulate no env vars
        result = search_jira_issues_jql("project = TEST")
        self.assertEqual(result["status"], "error")
        self.assertIn("Atlassian instance configuration", result["error_message"])

    def test_search_empty_jql_query(self):
        result = search_jira_issues_jql("")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], "JQL query cannot be empty.")

    @patch('tools.jira_tools.requests.post')
    @patch('tools.jira_tools.os.getenv')
    def test_search_http_error_400_bad_jql(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        jql_query = "project = INVALID JQL"
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"errorMessages": ["Invalid JQL query."]}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Bad Request")
        mock_requests_post.return_value = mock_response

        result = search_jira_issues_jql(jql_query)

        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP error searching issues with JQL", result["error_message"])
        self.assertIn("Invalid JQL query.", result["error_message"])
        self.assertIn(f"Check JQL syntax: {jql_query}", result["error_message"])
        self.assertEqual(result["issues"], [])

    @patch('tools.jira_tools.requests.post')
    @patch('tools.jira_tools.os.getenv')
    def test_search_http_error_401_unauthorized(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"errorMessages": ["Authentication failed."]}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Unauthorized")
        mock_requests_post.return_value = mock_response

        result = search_jira_issues_jql("project = TEST")

        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP error searching issues with JQL", result["error_message"])
        self.assertIn("Authentication failed.", result["error_message"])

    @patch('tools.jira_tools.requests.post')
    @patch('tools.jira_tools.os.getenv')
    def test_search_request_exception(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        req_exception_message = "Connection timed out"
        mock_requests_post.side_effect = requests.exceptions.RequestException(req_exception_message)

        result = search_jira_issues_jql("project = TEST")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_message"], f"Error searching issues with JQL: {req_exception_message}")
        self.assertEqual(result["issues"], [])

    @patch('tools.jira_tools.requests.post')
    @patch('tools.jira_tools.os.getenv')
    def test_search_field_type_handling(self, mock_getenv, mock_requests_post):
        self._setup_mock_env_vars(mock_getenv)
        jql_query = "project = TEST"
        fields_to_request = ["status", "assignee", "components", "custom_single_select", "custom_multi_select", "priority"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issues": [
                {
                    "key": "TEST-COMPLEX",
                    "fields": {
                        "status": {"name": "Blocked", "description": "Issue is blocked"}, # 'name'
                        "assignee": {"displayName": "Dev Lead", "accountId": "123"}, # 'displayName'
                        "components": [{"name": "Backend"}, {"name": "API"}], # list of dicts with 'name'
                        "custom_single_select": {"value": "High"}, # 'value'
                        "custom_multi_select": [ # list of dicts with 'value'
                            {"value": "Feature"}, 
                            {"value": "Improvement"}
                        ],
                        "priority": {"name": "Highest"} # 'name'
                    }
                }
            ],
            "maxResults": 1, "total": 1
        }
        mock_requests_post.return_value = mock_response

        result = search_jira_issues_jql(jql_query, fields=fields_to_request, max_results=1)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["issues"]), 1)
        issue = result["issues"][0]
        self.assertEqual(issue["key"], "TEST-COMPLEX")
        self.assertEqual(issue["status"], "Blocked")
        self.assertEqual(issue["assignee"], "Dev Lead")
        self.assertEqual(issue["components"], ["Backend", "API"])
        self.assertEqual(issue["custom_single_select"], "High")
        self.assertEqual(issue["custom_multi_select"], ["Feature", "Improvement"])
        self.assertEqual(issue["priority"], "Highest")


if __name__ == '__main__':
    # This is to allow running the tests directly from this file
    # Add the project root to sys.path if tools.jira_tools cannot be found
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Need to import requests for the side_effect of HTTPError
    import requests 
    unittest.main()
