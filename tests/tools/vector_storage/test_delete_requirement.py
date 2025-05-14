import unittest
from unittest.mock import patch, MagicMock
import json
import datetime

from tools.vector_storage.requirements import delete_requirement

@patch('tools.vector_storage.requirements.datetime') # Not used by delete_requirement
@patch('tools.vector_storage.requirements._get_next_id') # Not used by delete_requirement
@patch('tools.vector_storage.requirements.collection', new_callable=MagicMock)
class TestDeleteRequirement(unittest.TestCase):

    def test_delete_requirement_success(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-20"
        result = delete_requirement(requirement_id=req_id) # Pass single ID
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['report'], f"Requirement '{req_id}' deleted successfully.")
        mock_collection.delete.assert_called_once_with(ids=[req_id]) # Expect list with single ID

    def test_delete_requirement_empty_id(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result = delete_requirement(requirement_id="") # Pass empty string
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Requirement ID cannot be empty.")
        mock_collection.delete.assert_not_called()

    def test_delete_requirement_collection_delete_exception(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-21"
        mock_collection.delete.side_effect = Exception("DB DELETE error")
        result = delete_requirement(requirement_id=req_id) # Pass single ID
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], f"Failed to delete requirement '{req_id}': DB DELETE error")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
