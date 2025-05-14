import unittest
from unittest.mock import patch, MagicMock
import json
import datetime

from tools.vector_storage.requirements import update_requirement, ALLOWED_IMPLEMENTATION_STATUSES, DEFAULT_IMPLEMENTATION_STATUS

@patch('tools.vector_storage.requirements.datetime')
@patch('tools.vector_storage.requirements._get_next_id') # Not used by update_requirement
@patch('tools.vector_storage.requirements.collection', new_callable=MagicMock)
class TestUpdateRequirement(unittest.TestCase):

    def test_update_requirement_text_only(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-10"
        original_doc = "Original text"
        original_meta = {"type": "Requirement", "source": "test", "implementation_status": "Open"}
        new_text = "Updated requirement text"
        fixed_timestamp = datetime.datetime(2023, 2, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_collection.get.return_value = {'ids': [req_id], 'documents': [original_doc], 'metadatas': [original_meta]}
        
        result = update_requirement(requirement_id=req_id, new_requirement_text=new_text)
        
        self.assertEqual(result['status'], "success")
        self.assertIn("updated successfully (text)", result['report'])
        expected_meta_updated = original_meta.copy() # implementation_status should be preserved
        expected_meta_updated['change_date'] = iso_fixed_timestamp
        mock_collection.upsert.assert_called_once_with(
            ids=[req_id],
            documents=[new_text],
            metadatas=[expected_meta_updated]
        )

    def test_update_requirement_metadata_only(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-11"
        original_doc = "Some document text"
        original_meta = {"type": "Requirement", "source": "old_source", "implementation_status": "Open"}
        # new_metadata_json will replace the entire metadata
        new_meta_dict = {"type": "Requirement", "source": "new_source", "priority": "High", "implementation_status": "In Progress"}
        new_meta_json = json.dumps(new_meta_dict)
        
        fixed_timestamp = datetime.datetime(2023, 2, 2, 11, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_collection.get.return_value = {'ids': [req_id], 'documents': [original_doc], 'metadatas': [original_meta]}

        result = update_requirement(requirement_id=req_id, new_metadata_json=new_meta_json)

        self.assertEqual(result['status'], "success")
        self.assertIn("updated successfully (metadata)", result['report'])
        expected_meta_updated = new_meta_dict.copy()
        expected_meta_updated['change_date'] = iso_fixed_timestamp
        mock_collection.upsert.assert_called_once_with(
            ids=[req_id],
            documents=[original_doc], 
            metadatas=[expected_meta_updated]
        )

    def test_update_requirement_text_and_metadata(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-12"
        original_doc_text = "old text" 
        original_meta = {"type": "Requirement", "implementation_status": "Open"} 
        new_text = "Completely new text"
        new_meta_dict = {"type": "Requirement", "status": "approved", "implementation_status": "Done"}
        new_meta_json = json.dumps(new_meta_dict)
        
        fixed_timestamp = datetime.datetime(2023, 2, 3, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_collection.get.return_value = {'ids': [req_id], 'documents': [original_doc_text], 'metadatas': [original_meta]}

        result = update_requirement(requirement_id=req_id, new_requirement_text=new_text, new_metadata_json=new_meta_json)

        self.assertEqual(result['status'], "success")
        self.assertIn("updated successfully (text, metadata)", result['report'])
        expected_meta_updated = new_meta_dict.copy()
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
        mock_collection.get.return_value = {'ids': [req_id], 'documents': ["doc"], 'metadatas': [{"type": "TestCase"}]}
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
        mock_collection.get.return_value = {'ids': ["REQ-1"], 'documents': ["old"], 'metadatas': [{"type": "Requirement", "implementation_status": "Open"}]}
        result = update_requirement(requirement_id="REQ-1", new_requirement_text="   ")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "New requirement text cannot be empty.")

    def test_update_requirement_invalid_new_metadata_json(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': ["REQ-1"], 'documents': ["old"], 'metadatas': [{"type": "Requirement", "implementation_status": "Open"}]}
        result = update_requirement(requirement_id="REQ-1", new_metadata_json="not json")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Invalid JSON format provided for new metadata.")

    def test_update_requirement_new_metadata_json_not_dict(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': ["REQ-1"], 'documents': ["old"], 'metadatas': [{"type": "Requirement", "implementation_status": "Open"}]}
        result = update_requirement(requirement_id="REQ-1", new_metadata_json='["list"]')
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "New metadata must be a JSON object (dictionary).")

    @patch('builtins.print')
    def test_update_requirement_metadata_new_type_is_set_if_missing(self, mock_print, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-13"
        doc_content = "doc" 
        original_meta = {"type": "Requirement", "implementation_status": "Open"} 
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()
        mock_collection.get.return_value = {'ids': [req_id], 'documents': [doc_content], 'metadatas': [original_meta]}
        
        # new_metadata_json is empty, so 'type' will be missing, and 'implementation_status' will be missing
        # The function should default 'type' to 'Requirement'.
        # Since 'implementation_status' is not in new_metadata_json, it won't be validated or changed by the new logic.
        # The existing 'implementation_status' from original_meta will be wiped because new_metadata_json replaces entirely.
        new_metadata_dict = {}
        result = update_requirement(requirement_id=req_id, new_metadata_json=json.dumps(new_metadata_dict)) 
        
        self.assertEqual(result['status'], "success") 
        mock_print.assert_called_once_with(f"Warning: Updating metadata for '{req_id}' without a 'type' field. Setting to 'Requirement'.")
        # Expected metadata will have 'type' defaulted, and no 'implementation_status' as it wasn't in new_metadata_dict
        expected_meta = {'type': 'Requirement', 'change_date': iso_fixed_timestamp}
        mock_collection.upsert.assert_called_once_with(ids=[req_id], documents=[doc_content], metadatas=[expected_meta])

    @patch('builtins.print')
    def test_update_requirement_metadata_new_type_is_different(self, mock_print, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-14"
        doc_content = "doc" 
        original_meta = {"type": "Requirement", "implementation_status": "Open"} 
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()
        mock_collection.get.return_value = {'ids': [req_id], 'documents': [doc_content], 'metadatas': [original_meta]}
        
        # new_metadata_json has a different 'type', and no 'implementation_status'.
        # The 'implementation_status' from original_meta will be wiped.
        new_metadata_dict = {"type": "OtherType"}
        result = update_requirement(requirement_id=req_id, new_metadata_json=json.dumps(new_metadata_dict))

        self.assertEqual(result['status'], "success") 
        mock_print.assert_called_once_with(f"Warning: Updating metadata for '{req_id}' with a type other than 'Requirement' ('OtherType').")
        expected_meta = {'type': 'OtherType', 'change_date': iso_fixed_timestamp}
        mock_collection.upsert.assert_called_once_with(ids=[req_id], documents=[doc_content], metadatas=[expected_meta])

    def test_update_requirement_collection_get_exception(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.side_effect = Exception("DB GET error")
        result = update_requirement(requirement_id="REQ-1", new_requirement_text="text")
        self.assertEqual(result['status'], "error")
        self.assertIn("Error retrieving requirement 'REQ-1': DB GET error", result['error_message'])

    def test_update_requirement_collection_upsert_exception(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.get.return_value = {'ids': ["REQ-1"], 'documents': ["old"], 'metadatas': [{"type": "Requirement", "implementation_status": "Open"}]}
        mock_collection.upsert.side_effect = Exception("DB UPSERT error")
        result = update_requirement(requirement_id="REQ-1", new_requirement_text="text")
        self.assertEqual(result['status'], "error")
        self.assertIn("Failed to upsert requirement 'REQ-1': DB UPSERT error", result['error_message'])

    def test_update_requirement_to_valid_implementation_status(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-STATUS-VALID"
        original_doc = "Doc for status update"
        original_meta = {"type": "Requirement", "implementation_status": "Open"}
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()
        
        mock_collection.get.return_value = {'ids': [req_id], 'documents': [original_doc], 'metadatas': [original_meta]}

        for valid_status in ALLOWED_IMPLEMENTATION_STATUSES:
            mock_collection.upsert.reset_mock() # Reset for each iteration
            
            new_metadata_dict = {"implementation_status": valid_status, "type": "Requirement"} # Must include type
            result = update_requirement(requirement_id=req_id, new_metadata_json=json.dumps(new_metadata_dict))
            
            self.assertEqual(result['status'], "success", f"Failed for status: {valid_status}")
            expected_meta = new_metadata_dict.copy()
            expected_meta['change_date'] = iso_fixed_timestamp
            mock_collection.upsert.assert_called_once_with(
                ids=[req_id],
                documents=[original_doc],
                metadatas=[expected_meta]
            )

    def test_update_requirement_to_invalid_implementation_status(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-STATUS-INVALID"
        original_doc = "Doc for invalid status update"
        original_meta = {"type": "Requirement", "implementation_status": "Open"}
        invalid_status = "DefinitelyNotAllowed"
        
        mock_collection.get.return_value = {'ids': [req_id], 'documents': [original_doc], 'metadatas': [original_meta]}
        
        new_metadata_dict = {"implementation_status": invalid_status}
        result = update_requirement(requirement_id=req_id, new_metadata_json=json.dumps(new_metadata_dict))
        
        self.assertEqual(result['status'], "error")
        self.assertEqual(
            result['error_message'],
            f"Invalid implementation_status '{invalid_status}'. Must be one of {ALLOWED_IMPLEMENTATION_STATUSES}."
        )
        mock_collection.upsert.assert_not_called()

    def test_update_requirement_metadata_removes_status_if_not_in_new_json(self, mock_collection, mock_get_next_id, mock_datetime_module):
        req_id = "REQ-REMOVE-STATUS"
        original_doc = "Doc for status removal"
        original_meta = {"type": "Requirement", "implementation_status": "Open", "source": "A"}
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()
        
        mock_collection.get.return_value = {'ids': [req_id], 'documents': [original_doc], 'metadatas': [original_meta]}

        # New metadata only contains 'source', 'type' will be defaulted. 'implementation_status' should be gone.
        new_metadata_dict = {"source": "B"} 
        result = update_requirement(requirement_id=req_id, new_metadata_json=json.dumps(new_metadata_dict))
        
        self.assertEqual(result['status'], "success")
        args, kwargs = mock_collection.upsert.call_args
        updated_metadata = kwargs['metadatas'][0]
        
        self.assertNotIn("implementation_status", updated_metadata)
        self.assertEqual(updated_metadata["source"], "B")
        self.assertEqual(updated_metadata["type"], "Requirement") # Defaulted by the function
        self.assertEqual(updated_metadata["change_date"], iso_fixed_timestamp)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
