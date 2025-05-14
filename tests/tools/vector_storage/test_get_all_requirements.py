import unittest
from unittest.mock import patch, MagicMock
import json
import datetime
import sys
import os

# Fügt das Projektstammverzeichnis zum Python-Pfad hinzu
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.vector_storage.requirements import get_all_requirements, DEFAULT_CLASSIFICATION

@patch('tools.vector_storage.requirements.datetime') # Not used by get_all_requirements
@patch('tools.vector_storage.requirements._get_next_id') # Not used by get_all_requirements
@patch('tools.vector_storage.requirements.collection', new_callable=MagicMock)
class TestGetAllRequirements(unittest.TestCase):

    def test_get_all_requirements_success_with_data(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {
            'ids': ['REQ-A', 'REQ-B'],
            'documents': ['Doc A text', 'Doc B text'],
            'metadatas': [
                {'type': 'Requirement', 'source': 'A', 'classification': DEFAULT_CLASSIFICATION, 'implementation_status': 'Open', 'change_date': '...'}, 
                {'type': 'Requirement', 'source': 'B', 'classification': DEFAULT_CLASSIFICATION, 'implementation_status': 'Open', 'change_date': '...'}
            ]
        }
        result = get_all_requirements()
        self.assertEqual(result['status'], "success")
        self.assertIn("Found 2 requirement(s):", result['report'])
        self.assertIn("ID: REQ-A", result['report'])
        self.assertIn("ID: REQ-B", result['report'])
        mock_collection.get.assert_called_once_with(
            where={"type": "Requirement"},
            include=['documents', 'metadatas']
        )

    def test_get_all_requirements_no_requirements_found(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': [], 'documents': [], 'metadatas': []}
        result = get_all_requirements()
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['report'], "No requirements found in the database.")

    def test_get_all_requirements_collection_get_exception(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.side_effect = Exception("DB GET ALL error")
        result = get_all_requirements()
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Failed to retrieve all requirements: DB GET ALL error")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
