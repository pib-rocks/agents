import unittest
from unittest.mock import patch, MagicMock
import json
import datetime

from tools.vector_storage.requirements import update_requirement

@patch('tools.vector_storage.requirements.datetime')
@patch('tools.vector_storage.requirements._get_next_id') # Not used by update_requirement
@patch('tools.vector_storage.requirements.collection', new_callable=MagicMock)
class TestUpdateRequirement(unittest.TestCase):

    def test_update_requirement_text_only(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-10"
        original_doc = "Original text"
        original_meta = {"type": "Requirement", "source": "test"}
        new_text = "Updated requirement text"
        fixed_timestamp = datetime.datetime(2023, 2, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_collection.get.return_value = {'ids': [req_id], 'documents': [[original_doc]], 'metadatas': [[original_meta]]}
        
        result = update_requirement(requirement_id=req_id, new_requirement_text=new_text)
        
        self.assertEqual(result['status'], "success")
        self.assertIn("updated successfully (text)", result['report'])
        expected_meta_updated = original_meta.copy()
        expected_meta_updated['change_date'] = iso_fixed_timestamp
        mock_collection.upsert.assert_called_once_with(
            ids=[req_id],
            documents=[new_text],
            metadatas=[expected_meta_updated]
        )

    def test_update_requirement_metadata_only(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-11"
        original_doc = "Some document text"
        original_meta = {"type": "Requirement", "source": "old_source"}
        new_meta_json = '{"type": "Requirement", "source": "new_source", "priority": "High"}'
        parsed_new_meta = json.loads(new_meta_json)
        fixed_timestamp = datetime.datetime(2023, 2, 2, 11, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_collection.get.return_value = {'ids': [req_id], 'documents': [[original_doc]], 'metadatas': [[original_meta]]}

        result = update_requirement(requirement_id=req_id, new_metadata_json=new_meta_json)

        self.assertEqual(result['status'], "success")
        self.assertIn("updated successfully (metadata)", result['report'])
        expected_meta_updated = parsed_new_meta.copy()
        expected_meta_updated['change_date'] = iso_fixed_timestamp
        mock_collection.upsert.assert_called_once_with(
            ids=[req_id],
            documents=[original_doc], 
            metadatas=[expected_meta_updated]
        )

    def test_update_requirement_text_and_metadata(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-12"
        new_text = "Completely new text"
        new_meta_json = '{"type": "Requirement", "status": "approved"}'
        parsed_new_meta = json.loads(new_meta_json)
        fixed_timestamp = datetime.datetime(2023, 2, 3, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_collection.get.return_value = {'ids': [req_id], 'documents': [["old text"]], 'metadatas': [[{"type": "Requirement"}]]}

        result = update_requirement(requirement_id=req_id, new_requirement_text=new_text, new_metadata_json=new_meta_json)

        self.assertEqual(result['status'], "success")
        self.assertIn("updated successfully (text, metadata)", result['report'])
        expected_meta_updated = parsed_new_meta.copy()
        expected_meta_updated['change_date'] = iso_fixed_timestamp
        mock_collection.upsert.assert_called_once_with(
            ids=[req_id],
            documents=[new_text],
            metadatas=[expected_meta_updated]
        )

    def test_update_requirement_id_not_found(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': [], 'documents': [], 'metadatas': []} 
        result = update_requirement(requirement_id="REQ-NONEXIST", new_requirement_text="text")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Requirement 'REQ-NONEXIST' not found.")

    def test_update_requirement_item_not_a_requirement_type(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "ITEM-1"
        mock_collection.get.return_value = {'ids': [req_id], 'documents': [["doc"]], 'metadatas': [[{"type": "TestCase"}]]}
        result = update_requirement(requirement_id=req_id, new_requirement_text="text")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], f"Item '{req_id}' found, but it is not a Requirement (type: TestCase). Update aborted.")

    def test_update_requirement_empty_id(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result = update_requirement(requirement_id="", new_requirement_text="text")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Requirement ID cannot be empty.")

    def test_update_requirement_no_changes_provided(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result = update_requirement(requirement_id="REQ-1", new_requirement_text=None, new_metadata_json=None)
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Must provide either new text or new metadata to update.")

    def test_update_requirement_empty_new_text(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': ["REQ-1"], 'documents': [["old"]], 'metadatas': [[{"type": "Requirement"}]]}
        result = update_requirement(requirement_id="REQ-1", new_requirement_text="   ")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "New requirement text cannot be empty.")

    def test_update_requirement_invalid_new_metadata_json(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': ["REQ-1"], 'documents': [["old"]], 'metadatas': [[{"type": "Requirement"}]]}
        result = update_requirement(requirement_id="REQ-1", new_metadata_json="not json")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Invalid JSON format provided for new metadata.")

    def test_update_requirement_new_metadata_json_not_dict(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': ["REQ-1"], 'documents': [["old"]], 'metadatas': [[{"type": "Requirement"}]]}
        result = update_requirement(requirement_id="REQ-1", new_metadata_json='["list"]')
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "New metadata must be a JSON object (dictionary).")

    @patch('builtins.print')
    def test_update_requirement_metadata_new_type_is_set_if_missing(self, mock_print, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-13"
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()
        mock_collection.get.return_value = {'ids': [req_id], 'documents': [["doc"]], 'metadatas': [[{"type": "Requirement"}]]}
        
        update_requirement(requirement_id=req_id, new_metadata_json='{}') 
        
        mock_print.assert_called_once_with(f"Warning: Updating metadata for '{req_id}' without a 'type' field. Setting to 'Requirement'.")
        expected_meta = {'type': 'Requirement', 'change_date': iso_fixed_timestamp}
        mock_collection.upsert.assert_called_once_with(ids=[req_id], documents=["doc"], metadatas=[expected_meta])

    @patch('builtins.print')
    def test_update_requirement_metadata_new_type_is_different(self, mock_print, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-14"
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()
        mock_collection.get.return_value = {'ids': [req_id], 'documents': [["doc"]], 'metadatas': [[{"type": "Requirement"}]]}
        
        update_requirement(requirement_id=req_id, new_metadata_json='{"type": "OtherType"}')
        
        mock_print.assert_called_once_with(f"Warning: Updating metadata for '{req_id}' with a type other than 'Requirement' ('OtherType').")
        expected_meta = {'type': 'OtherType', 'change_date': iso_fixed_timestamp}
        mock_collection.upsert.assert_called_once_with(ids=[req_id], documents=["doc"], metadatas=[expected_meta])

    def test_update_requirement_collection_get_exception(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.side_effect = Exception("DB GET error")
        result = update_requirement(requirement_id="REQ-1", new_requirement_text="text")
        self.assertEqual(result['status'], "error")
        self.assertIn("Error retrieving requirement 'REQ-1': DB GET error", result['error_message'])

    def test_update_requirement_collection_upsert_exception(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': ["REQ-1"], 'documents': [["old"]], 'metadatas': [[{"type": "Requirement"}]]}
        mock_collection.upsert.side_effect = Exception("DB UPSERT error")
        result = update_requirement(requirement_id="REQ-1", new_requirement_text="text")
        self.assertEqual(result['status'], "error")
        self.assertIn("Failed to upsert requirement 'REQ-1': DB UPSERT error", result['error_message'])

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
