import unittest
from unittest.mock import patch, MagicMock
import json
import datetime # Used for creating expected datetime objects/strings

# Module to test
from tools.vector_storage.requirements import (
    add_requirement, 
    update_requirement, # Added for new TestUpdateRequirement class
    ALLOWED_IMPLEMENTATION_STATUSES, 
    DEFAULT_IMPLEMENTATION_STATUS,
    ALLOWED_CLASSIFICATIONS,
    DEFAULT_CLASSIFICATION
)

# Patching at class level: these mocks will be passed as arguments to each test method.
# The order of decorators is bottom-up, so the arguments to test methods will be:
# mock_collection, mock_get_next_id, mock_datetime_module
@patch('tools.vector_storage.requirements.datetime') # Patches the datetime module used in requirements.py
@patch('tools.vector_storage.requirements._get_next_id')
@patch('tools.vector_storage.requirements.collection', new_callable=MagicMock) # Use MagicMock for the collection object
class TestAddRequirement(unittest.TestCase):

    def test_add_requirement_with_only_text(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_get_next_id.return_value = "REQ-1"
        requirement_text = "The system shall allow users to register."

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=None)

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['requirement_id'], "REQ-1")
        self.assertIn("Requirement 'REQ-1' added successfully.", result['report'])

        mock_get_next_id.assert_called_once_with("REQ-")
        expected_metadata = {
            'type': 'Requirement', 
            'implementation_status': DEFAULT_IMPLEMENTATION_STATUS,
            'classification': DEFAULT_CLASSIFICATION,
            'change_date': iso_fixed_timestamp 
        }
        mock_collection.upsert.assert_called_once_with(
            ids=["REQ-1"],
            documents=[requirement_text],
            metadatas=[expected_metadata]
        )

    def test_add_requirement_with_text_and_valid_metadata(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_get_next_id.return_value = "REQ-2"
        requirement_text = "Users must be able to reset their passwords."
        # This input provides "implementation_status"
        metadata_input = {"priority": "High", "source_jira_ticket": "XYZ-123", "implementation_status": "In Progress"}
        metadata_json_input = json.dumps(metadata_input)

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input)

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['requirement_id'], "REQ-2")

        mock_get_next_id.assert_called_once_with("REQ-")
        expected_metadata = {
            "priority": "High",
            "source_jira_ticket": "XYZ-123",
            "implementation_status": "In Progress", # Expect provided status
            'classification': DEFAULT_CLASSIFICATION, # Defaults as not provided in input
            'type': 'Requirement', 
            'change_date': iso_fixed_timestamp 
        }
        mock_collection.upsert.assert_called_once_with(
            ids=["REQ-2"],
            documents=[requirement_text],
            metadatas=[expected_metadata]
        )

    def test_add_requirement_with_text_and_empty_json_metadata(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_get_next_id.return_value = "REQ-3"
        requirement_text = "The system should provide an audit log."
        metadata_json_input = '{}' 

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input)

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['requirement_id'], "REQ-3")

        expected_metadata = {
            'type': 'Requirement',
            'implementation_status': DEFAULT_IMPLEMENTATION_STATUS,
            'classification': DEFAULT_CLASSIFICATION,
            'change_date': iso_fixed_timestamp
        }
        mock_collection.upsert.assert_called_once_with(
            ids=["REQ-3"],
            documents=[requirement_text],
            metadatas=[expected_metadata]
        )

    def test_add_requirement_with_empty_text(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        requirement_text = ""

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=None)

        # --- Assert ---
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Requirement text cannot be empty.")
        mock_collection.upsert.assert_not_called()
        mock_get_next_id.assert_not_called() 

    def test_add_requirement_with_invalid_json_metadata(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        mock_get_next_id.return_value = "REQ-ID-WONT-BE-USED"
        requirement_text = "The system must be responsive."
        metadata_json_input = '{"priority": "Medium", "source": unquoted_string}' 

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input)

        # --- Assert ---
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Invalid JSON format provided for metadata.")
        mock_collection.upsert.assert_not_called()
        mock_get_next_id.assert_called_once_with("REQ-") 

    def test_add_requirement_metadata_must_be_json_object_not_array_or_string(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        mock_get_next_id.return_value = "REQ-ID-WONT-BE-USED"
        requirement_text = "Valid requirement text."
        metadata_json_input_array = '[1, 2, 3]'
        metadata_json_input_string = '"just a string"'

        # --- Act & Assert for array ---
        result_array = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input_array)
        self.assertEqual(result_array['status'], "error")
        self.assertEqual(result_array['error_message'], "Metadata must be a JSON object (dictionary).")
        mock_get_next_id.assert_called_once_with("REQ-") 
        mock_collection.upsert.assert_not_called()

        mock_get_next_id.reset_mock()
        mock_get_next_id.return_value = "REQ-ID-WONT-BE-USED-AGAIN"

        # --- Act & Assert for string ---
        result_string = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input_string)
        self.assertEqual(result_string['status'], "error")
        self.assertEqual(result_string['error_message'], "Metadata must be a JSON object (dictionary).")
        mock_get_next_id.assert_called_once_with("REQ-") 
        mock_collection.upsert.assert_not_called() 

    def test_add_requirement_with_special_characters_in_text_and_metadata(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_get_next_id.return_value = "REQ-4"
        requirement_text = "The system must handle inputs like '你好' & special symbols !@#$%^&*()_+."
        metadata_input = {"details": "Test with non-ASCII: éàçüö, and quotes: \"example\""}
        metadata_json_input = json.dumps(metadata_input)

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input)

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['requirement_id'], "REQ-4")

        expected_metadata = {
            "details": "Test with non-ASCII: éàçüö, and quotes: \"example\"",
            'type': 'Requirement',
            'implementation_status': DEFAULT_IMPLEMENTATION_STATUS,
            'classification': DEFAULT_CLASSIFICATION,
            'change_date': iso_fixed_timestamp
        }
        mock_collection.upsert.assert_called_once_with(
            ids=["REQ-4"],
            documents=[requirement_text],
            metadatas=[expected_metadata]
        )

    def test_add_requirement_metadata_type_field_is_overridden(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_get_next_id.return_value = "REQ-5"
        requirement_text = "A requirement with a pre-defined type in input."
        metadata_input = {"type": "UserStory", "source": "Planning meeting"}
        metadata_json_input = json.dumps(metadata_input)

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input)

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['requirement_id'], "REQ-5")

        expected_metadata = {
            "type": "Requirement", 
            "source": "Planning meeting",
            'implementation_status': DEFAULT_IMPLEMENTATION_STATUS,
            'classification': DEFAULT_CLASSIFICATION,
            'change_date': iso_fixed_timestamp
        }
        mock_collection.upsert.assert_called_once_with(
            ids=["REQ-5"],
            documents=[requirement_text],
            metadatas=[expected_metadata]
        )

    def test_add_requirement_id_generation_failure(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        mock_get_next_id.side_effect = Exception("Failed to generate ID")
        requirement_text = "Some requirement text."

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=None)

        # --- Assert ---
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Failed to generate requirement ID: Failed to generate ID")
        mock_collection.upsert.assert_not_called()
        mock_get_next_id.assert_called_once_with("REQ-") 

    def test_add_requirement_collection_upsert_failure(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp

        mock_get_next_id.return_value = "REQ-6"
        mock_collection.upsert.side_effect = Exception("ChromaDB unavailable")
        requirement_text = "Another requirement."

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=None)

        # --- Assert ---
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Failed to add requirement 'REQ-6': ChromaDB unavailable")
        mock_get_next_id.assert_called_once_with("REQ-") 
        mock_collection.upsert.assert_called_once() 

    def test_add_requirement_sets_default_implementation_status(self, mock_collection, mock_get_next_id, mock_datetime_module):
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()
        mock_get_next_id.return_value = "REQ-DEF"
        requirement_text = "Requirement without explicit status."
        
        # Case 1: metadata_json is None
        result1 = add_requirement(requirement_text=requirement_text, metadata_json=None)
        self.assertEqual(result1['status'], "success")
        args1, kwargs1 = mock_collection.upsert.call_args_list[0]
        self.assertEqual(kwargs1['metadatas'][0]['implementation_status'], DEFAULT_IMPLEMENTATION_STATUS)
        
        mock_collection.reset_mock() # Reset for next call
        mock_get_next_id.reset_mock()
        mock_get_next_id.return_value = "REQ-DEF2"

        # Case 2: metadata_json is provided but doesn't contain implementation_status
        metadata_input = {"source": "test_source"}
        result2 = add_requirement(requirement_text=requirement_text, metadata_json=json.dumps(metadata_input))
        self.assertEqual(result2['status'], "success")
        args2, kwargs2 = mock_collection.upsert.call_args_list[0]
        self.assertEqual(kwargs2['metadatas'][0]['implementation_status'], DEFAULT_IMPLEMENTATION_STATUS)
        self.assertEqual(kwargs2['metadatas'][0]['classification'], DEFAULT_CLASSIFICATION)
        self.assertEqual(kwargs2['metadatas'][0]['source'], "test_source")

    def test_add_requirement_with_explicit_valid_classification(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()

        mock_get_next_id.return_value = "REQ-CLASS-VALID"
        requirement_text = "A requirement with an explicit classification."
        
        for valid_classification in ALLOWED_CLASSIFICATIONS:
            mock_collection.reset_mock()
            mock_get_next_id.reset_mock()
            current_req_id = f"REQ-CLASS-{valid_classification.replace(' ', '')}"
            mock_get_next_id.return_value = current_req_id

            metadata_input = {"classification": valid_classification, "source": "test"}
            metadata_json_input = json.dumps(metadata_input)

            # --- Act ---
            result = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input)

            # --- Assert ---
            self.assertEqual(result['status'], "success", f"Failed for classification: {valid_classification}")
            self.assertEqual(result['requirement_id'], current_req_id)

            expected_metadata = {
                "classification": valid_classification,
                "source": "test",
                'type': 'Requirement',
                'implementation_status': DEFAULT_IMPLEMENTATION_STATUS,
                'change_date': iso_fixed_timestamp
            }
            mock_collection.upsert.assert_called_once_with(
                ids=[current_req_id],
                documents=[requirement_text],
                metadatas=[expected_metadata]
            )

    def test_add_requirement_with_invalid_classification(self, mock_collection, mock_get_next_id, mock_datetime_module):
        # --- Arrange ---
        mock_get_next_id.return_value = "REQ-CLASS-INVALID" # ID will be generated before validation
        requirement_text = "A requirement with an invalid classification."
        invalid_classification = "DefinitelyNotAllowedClassification"
        metadata_input = {"classification": invalid_classification}
        metadata_json_input = json.dumps(metadata_input)

        # --- Act ---
        result = add_requirement(requirement_text=requirement_text, metadata_json=metadata_json_input)

        # --- Assert ---
        self.assertEqual(result['status'], "error")
        self.assertIn(f"Invalid classification '{invalid_classification}'. Must be one of {ALLOWED_CLASSIFICATIONS}", result['error_message'])
        mock_collection.upsert.assert_not_called()
        mock_get_next_id.assert_called_once_with("REQ-") # Ensure ID generation was attempted

    def test_add_requirement_with_valid_implementation_status(self, mock_collection, mock_get_next_id, mock_datetime_module):
        fixed_timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime_module.datetime.now.return_value = fixed_timestamp
        iso_fixed_timestamp = fixed_timestamp.isoformat()
        mock_get_next_id.return_value = "REQ-VALID-STATUS" # Initial value, will be reset
        requirement_text = "Requirement with valid status."
        
        for valid_status in ALLOWED_IMPLEMENTATION_STATUSES:
            mock_collection.reset_mock() # Reset for each iteration
            mock_get_next_id.reset_mock() # Reset for each iteration
            # Ensure a unique ID for each iteration to avoid issues if tests run in parallel or state leaks
            current_req_id = f"REQ-{valid_status.replace(' ', '')}"
            mock_get_next_id.return_value = current_req_id
            
            metadata_input = {"implementation_status": valid_status}
            result = add_requirement(requirement_text=requirement_text, metadata_json=json.dumps(metadata_input))
            
            self.assertEqual(result['status'], "success", f"Failed for status: {valid_status}")
            args, kwargs = mock_collection.upsert.call_args
            self.assertEqual(kwargs['metadatas'][0]['implementation_status'], valid_status)
            self.assertEqual(kwargs['metadatas'][0]['classification'], DEFAULT_CLASSIFICATION) # Should still default
            self.assertEqual(kwargs['metadatas'][0]['type'], 'Requirement')
            self.assertEqual(kwargs['metadatas'][0]['change_date'], iso_fixed_timestamp)

    def test_add_requirement_with_invalid_implementation_status(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_get_next_id.return_value = "REQ-INVALID-STATUS" # ID will be generated before validation
        requirement_text = "Requirement with invalid status."
        invalid_status = "DefinitelyNotAllowed"
        metadata_input = {"implementation_status": invalid_status}
        
        result = add_requirement(requirement_text=requirement_text, metadata_json=json.dumps(metadata_input))
        
        self.assertEqual(result['status'], "error")
        self.assertEqual(
            result['error_message'],
            f"Invalid implementation_status '{invalid_status}'. Must be one of {ALLOWED_IMPLEMENTATION_STATUSES}."
        )
        mock_collection.upsert.assert_not_called()
        mock_get_next_id.assert_called_once_with("REQ-") # Ensure ID generation was attempted


# Test class for update_requirement function
@patch('tools.vector_storage.requirements.datetime')
@patch('tools.vector_storage.requirements.collection', new_callable=MagicMock)
class TestUpdateRequirement(unittest.TestCase):

    def setUp(self):
        self.req_id = "REQ-UPDATE-1"
        self.original_text = "Original requirement text."
        self.original_metadata = {
            "type": "Requirement",
            "source": "original_source",
            "implementation_status": "Open",
            "classification": "Functional", # Assume it was set during add
            "change_date": datetime.datetime(2023, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc).isoformat()
        }
        self.fixed_now = datetime.datetime(2023, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        self.iso_fixed_now = self.fixed_now.isoformat()

    def test_update_requirement_classification_only(self, mock_collection, mock_datetime_module):
        # --- Arrange ---
        mock_datetime_module.datetime.now.return_value = self.fixed_now
        mock_collection.get.return_value = {
            'ids': [self.req_id],
            'documents': [self.original_text],
            'metadatas': [self.original_metadata]
        }
        new_classification = "Non-Functional"
        new_metadata_input = {"classification": new_classification, "source": "original_source", "implementation_status": "Open"} # provide other existing fields
        new_metadata_json = json.dumps(new_metadata_input)

        # --- Act ---
        result = update_requirement(
            requirement_id=self.req_id,
            new_metadata_json=new_metadata_json
        )

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        self.assertIn("Requirement 'REQ-UPDATE-1' updated successfully (metadata).", result['report'])
        
        expected_metadata = self.original_metadata.copy()
        expected_metadata.update({
            "classification": new_classification,
            "change_date": self.iso_fixed_now,
            "type": "Requirement" # Ensure type is preserved or set
        })
        # Adjust expected if other fields were part of new_metadata_input
        expected_metadata["source"] = new_metadata_input["source"]
        expected_metadata["implementation_status"] = new_metadata_input["implementation_status"]


        mock_collection.upsert.assert_called_once_with(
            ids=[self.req_id],
            documents=[self.original_text], # Text not changed
            metadatas=[expected_metadata]
        )

    def test_update_requirement_sets_default_classification_if_missing_in_new_metadata(self, mock_collection, mock_datetime_module):
        # --- Arrange ---
        mock_datetime_module.datetime.now.return_value = self.fixed_now
        mock_collection.get.return_value = {
            'ids': [self.req_id],
            'documents': [self.original_text],
            'metadatas': [self.original_metadata] # Original had "Functional"
        }
        # New metadata intentionally omits 'classification'
        new_metadata_input = {"source": "updated_source", "implementation_status": "In Progress"}
        new_metadata_json = json.dumps(new_metadata_input)

        # --- Act ---
        result = update_requirement(
            requirement_id=self.req_id,
            new_metadata_json=new_metadata_json
        )

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        
        expected_metadata = {
            "source": "updated_source",
            "implementation_status": "In Progress",
            "classification": DEFAULT_CLASSIFICATION, # Should default
            "type": "Requirement",
            "change_date": self.iso_fixed_now
        }
        mock_collection.upsert.assert_called_once_with(
            ids=[self.req_id],
            documents=[self.original_text],
            metadatas=[expected_metadata]
        )

    def test_update_requirement_with_invalid_classification(self, mock_collection, mock_datetime_module):
        # --- Arrange ---
        mock_datetime_module.datetime.now.return_value = self.fixed_now # Not strictly needed as it should fail before date
        mock_collection.get.return_value = { # Needed for the initial get
            'ids': [self.req_id],
            'documents': [self.original_text],
            'metadatas': [self.original_metadata]
        }
        invalid_classification = "InvalidClass"
        new_metadata_input = {"classification": invalid_classification}
        new_metadata_json = json.dumps(new_metadata_input)

        # --- Act ---
        result = update_requirement(
            requirement_id=self.req_id,
            new_metadata_json=new_metadata_json
        )

        # --- Assert ---
        self.assertEqual(result['status'], "error")
        self.assertIn(f"Invalid classification '{invalid_classification}'. Must be one of {ALLOWED_CLASSIFICATIONS}", result['error_message'])
        mock_collection.upsert.assert_not_called()

    def test_update_requirement_text_and_classification(self, mock_collection, mock_datetime_module):
        # --- Arrange ---
        mock_datetime_module.datetime.now.return_value = self.fixed_now
        mock_collection.get.return_value = {
            'ids': [self.req_id],
            'documents': [self.original_text],
            'metadatas': [self.original_metadata]
        }
        new_text = "Updated requirement text for classification test."
        new_classification = "Business"
        # Provide minimal metadata, other fields should be handled by the function (type, default classification if not this one)
        new_metadata_input = {"classification": new_classification, "source_jira_ticket": "NEW-TICKET"}
        new_metadata_json = json.dumps(new_metadata_input)

        # --- Act ---
        result = update_requirement(
            requirement_id=self.req_id,
            new_requirement_text=new_text,
            new_metadata_json=new_metadata_json
        )

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        self.assertIn("updated successfully (text, metadata)", result['report'])
        
        expected_metadata = {
            "classification": new_classification,
            "source_jira_ticket": "NEW-TICKET", # from new metadata
            "type": "Requirement", # Defaulted by update_requirement logic
            "change_date": self.iso_fixed_now
            # implementation_status would be missing if not in new_metadata_input
        }
        mock_collection.upsert.assert_called_once_with(
            ids=[self.req_id],
            documents=[new_text],
            metadatas=[expected_metadata]
        )

    def test_update_requirement_classification_persists_if_metadata_not_updated(self, mock_collection, mock_datetime_module):
        # --- Arrange ---
        mock_datetime_module.datetime.now.return_value = self.fixed_now
        # Original metadata has 'classification': 'Functional'
        mock_collection.get.return_value = {
            'ids': [self.req_id],
            'documents': [self.original_text],
            'metadatas': [self.original_metadata.copy()] 
        }
        new_text = "Only updating the text."

        # --- Act ---
        result = update_requirement(
            requirement_id=self.req_id,
            new_requirement_text=new_text,
            new_metadata_json=None # Metadata not being updated explicitly
        )

        # --- Assert ---
        self.assertEqual(result['status'], "success")
        self.assertIn("updated successfully (text)", result['report'])
        
        expected_metadata = self.original_metadata.copy()
        expected_metadata['change_date'] = self.iso_fixed_now # Change date always updates

        mock_collection.upsert.assert_called_once_with(
            ids=[self.req_id],
            documents=[new_text],
            metadatas=[expected_metadata] # Should contain original classification
        )
        self.assertEqual(mock_collection.upsert.call_args[1]['metadatas'][0]['classification'], "Functional")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
