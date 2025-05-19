"""
#AI!Add a new Python function `search_jira_issues` to a Python file, for example, `jira_tools.py` or a similar appropriate file for Jira integration functions.

The function `search_jira_issues` should:
1.  Be defined with the signature: `def search_jira_issues(jql_query: str, max_results: int = 50):`
2.  Take two arguments:
    *   `jql_query` (string): The JQL query string to execute for searching Jira issues.
    *   `max_results` (integer, with a default value of 50): The maximum number of issues to retrieve.
3.  Utilize the underlying Jira API or SDK to perform the search based on the `jql_query`.
4.  Process the results from Jira and return a list of dictionaries. Each dictionary should represent a Jira issue and include at least the following keys: 'key', 'summary', 'status', 'assignee_name', 'assignee_email', 'reporter_name', 'created_date', 'updated_date', 'description', and 'issue_type'.
5.  If the Jira API call encounters an error (e.g., invalid JQL, network issue, permissions error), the function should handle it gracefully. For instance, it could log the error and return an empty list or a dictionary indicating the error.
6.  Include a clear docstring explaining its purpose, parameters, return value, and any exceptions it might raise or error conditions it handles.
"""