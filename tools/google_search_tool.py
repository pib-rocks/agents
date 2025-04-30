"""
This module provides the google_search tool from the google-adk library
for easy reuse in agents.
"""
from google.adk.tools import google_search

# Re-export the tool so it can be imported from this module
__all__ = ['google_search']

# Note: Ensure GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables are set
# for this tool to function correctly.
