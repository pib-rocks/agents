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

from tools.vector_storage.requirements import delete_requirement

@patch('tools.vector_storage.requirements.datetime') # Not used by delete_requirement
@patch('tools.vector_storage.requirements._get_next_id') # Not used by delete_requirement
@patch('tools.vector_storage.requirements.collection', new_callable=MagicMock)
class TestDeleteRequirement(unittest.TestCase):

    def test_delete_requirement_success_single_id(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-20"
        result = delete_requirement(requirement_ids=[req_id]) 
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['report'], f"Requirement '{req_id}' deleted successfully.")
        mock_collection.delete.assert_called_once_with(ids=[req_id])

    def test_delete_requirement_success_multiple_ids(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_ids = ["REQ-21", "REQ-22", "REQ-23"]
        result = delete_requirement(requirement_ids=req_ids)
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['report'], f"Successfully deleted {len(req_ids)} requirement(s): {', '.join(req_ids)}.")
        mock_collection.delete.assert_called_once_with(ids=req_ids)

    def test_delete_requirement_empty_id_list(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result = delete_requirement(requirement_ids=[]) 
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Requirement ID list cannot be empty.")
        mock_collection.delete.assert_not_called()

    def test_delete_requirement_list_with_invalid_ids_only(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result = delete_requirement(requirement_ids=["", "   ", None]) # type: ignore
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "No valid requirement IDs provided in the list. Ensure IDs are non-empty strings.")
        mock_collection.delete.assert_not_called()

    @patch('builtins.print')
    def test_delete_requirement_list_with_mixed_valid_invalid_ids(self, mock_print, mock_collection, mock_get_next_id, mock_datetime_module):
        req_ids_mixed = ["REQ-VALID1", "", "REQ-VALID2", "   ", None]
        valid_ids_expected = ["REQ-VALID1", "REQ-VALID2"]
        
        result = delete_requirement(requirement_ids=req_ids_mixed) # type: ignore
        
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['report'], f"Successfully deleted {len(valid_ids_expected)} requirement(s): {', '.join(valid_ids_expected)}.")
        mock_collection.delete.assert_called_once_with(ids=valid_ids_expected)
        ignored_count = len(req_ids_mixed) - len(valid_ids_expected)
        mock_print.assert_called_once_with(f"Warning: {ignored_count} invalid or empty ID(s) were provided and will be ignored. Attempting to delete: {valid_ids_expected}")

    def test_delete_requirement_collection_delete_exception(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_ids = ["REQ-25", "REQ-26"]
        mock_collection.delete.side_effect = Exception("DB DELETE error")
        result = delete_requirement(requirement_ids=req_ids) 
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], f"Failed to delete requirements. IDs attempted: {', '.join(req_ids)}. Error: DB DELETE error")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
