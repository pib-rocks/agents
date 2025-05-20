"""
#AI!{Add a new Python function named `search_jira_issues_advanced` to the file `tools/jira_tools.py`.
This function should allow searching Jira issues using a JQL query string.

Function signature:
`search_jira_issues_advanced(jql_query: str, max_results: int = 50) -> dict`

Functionality:
1.  Accepts a `jql_query` (string) and an optional `max_results` (integer, default 50).
2.  Executes the `jql_query` against the Jira instance using the existing Jira connection/client (e.g., the `jira` Python library if used elsewhere in the specified file or project).
3.  Retrieves standard issue fields: key, summary, status, assignee, reporter, created, updated, description.
4.  Returns a dictionary:
    - On success: `{'status': 'success', 'issues': [{'key': 'PROJ-123', 'summary': '...', ...}, ...]}`
    - On failure (e.g., invalid JQL, connection error): `{'status': 'error', 'message': 'Error description'}`
5.  Ensure this function is exposed as a tool for the agent, callable appropriately (e.g. as a method of a class if `tools/jira_tools.py` contains a class, or as a standalone function if it's a collection of functions).}
"""