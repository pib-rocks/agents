"""
Manages storing and retrieving software requirements, acceptance criteria,
test cases, and potentially other artifacts using a ChromaDB vector database.

This module acts as a facade, importing and re-exporting functions
from the specific modules within the `vector_storage` sub-package.
"""
from typing import List, Dict, Optional # Keep typing for potential future use or type hints here

# Import functions from submodules
from .vector_storage.requirements import (
    add_requirement,
    retrieve_similar_requirements,
    update_requirement,
    delete_requirement,
    get_all_requirements,
)
from .vector_storage.acceptance_criteria import (
    add_acceptance_criterion,
    retrieve_similar_acceptance_criteria,
    delete_acceptance_criterion,
    update_acceptance_criterion,
    get_all_acceptance_criteria,
)
from .vector_storage.test_cases import (
    add_test_case,
    retrieve_similar_test_cases,
    update_test_case,
    delete_test_case,
    get_all_test_cases,
)

# Export public functions
__all__ = [
    # Requirement Functions
    'add_requirement',
    'retrieve_similar_requirements',
    'update_requirement',
    'delete_requirement',
    'get_all_requirements',
    # Acceptance Criteria Functions
    'add_acceptance_criterion',
    'retrieve_similar_acceptance_criteria',
    'delete_acceptance_criterion',
    'update_acceptance_criterion',
    'get_all_acceptance_criteria',
    # Test Case Functions
    'add_test_case',
    'retrieve_similar_test_cases',
    'update_test_case',
    'delete_test_case',
    'get_all_test_cases',
]
