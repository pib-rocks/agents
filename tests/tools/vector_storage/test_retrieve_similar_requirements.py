import unittest
from unittest.mock import patch, MagicMock
import json
import datetime

from tools.vector_storage.requirements import retrieve_similar_requirements

@patch('tools.vector_storage.requirements.datetime')
@patch('tools.vector_storage.requirements._get_next_id') # Not used by retrieve_similar_requirements, but kept for consistency
@patch('tools.vector_storage.requirements.collection', new_callable=MagicMock)
class TestRetrieveSimilarRequirements(unittest.TestCase):

    def test_retrieve_similar_requirements_basic(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.query.return_value = {
            'ids': [['REQ-1', 'REQ-2']],
            'documents': [['Doc 1', 'Doc 2']],
            'distances': [[0.1, 0.2]],
            'metadatas': [[{'type': 'Requirement', 'key': 'val1'}, {'type': 'Requirement', 'key': 'val2'}]]
        }
        query_text = "find similar docs"
        result = retrieve_similar_requirements(query_text=query_text, n_results=2)
        self.assertEqual(result['status'], "success")
        self.assertIn("Found 2 similar requirement(s)", result['report'])
        self.assertIn("ID: REQ-1", result['report'])
        self.assertIn("ID: REQ-2", result['report'])
        mock_collection.query.assert_called_once_with(
            query_texts=[query_text],
            n_results=2,
            where=None,
            include=['documents', 'distances', 'metadatas']
        )

    def test_retrieve_similar_requirements_with_filter(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.query.return_value = {'ids': [[]], 'documents': [[]], 'distances': [[]], 'metadatas': [[]]} 
        query_text = "filter test"
        filter_json = '{"source_jira_ticket": "PROJ-1"}'
        parsed_filter = json.loads(filter_json)
        result = retrieve_similar_requirements(query_text=query_text, n_results=3, filter_metadata_json=filter_json)
        self.assertEqual(result['status'], "success") 
        mock_collection.query.assert_called_once_with(
            query_texts=[query_text],
            n_results=3,
            where=parsed_filter,
            include=['documents', 'distances', 'metadatas']
        )

    def test_retrieve_similar_requirements_no_results_found(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.query.return_value = {'ids': [[]], 'documents': [[]], 'distances': [[]], 'metadatas': [[]]}
        result = retrieve_similar_requirements(query_text="anything")
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['report'], "No similar requirements found.")

    def test_retrieve_similar_requirements_empty_query_text(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result = retrieve_similar_requirements(query_text="")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Query text cannot be empty.")
        mock_collection.query.assert_not_called()

    def test_retrieve_similar_requirements_invalid_n_results(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result_zero = retrieve_similar_requirements(query_text="test", n_results=0)
        self.assertEqual(result_zero['status'], "error")
        self.assertEqual(result_zero['error_message'], "Number of results must be positive.")
        result_neg = retrieve_similar_requirements(query_text="test", n_results=-1)
        self.assertEqual(result_neg['status'], "error")
        self.assertEqual(result_neg['error_message'], "Number of results must be positive.")
        mock_collection.query.assert_not_called()

    def test_retrieve_similar_requirements_invalid_filter_json(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result = retrieve_similar_requirements(query_text="test", filter_metadata_json="not json")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Invalid JSON format provided for filter metadata.")

    def test_retrieve_similar_requirements_filter_json_not_dict(self, mock_collection, mock_get_next_id, mock_datetime_module):
        result = retrieve_similar_requirements(query_text="test", filter_metadata_json='["a list"]')
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Filter metadata must be a JSON object (dictionary).")

    def test_retrieve_similar_requirements_collection_query_exception(self, mock_collection, mock_get_next_id, mock_datetime_module):
        mock_collection.query.side_effect = Exception("DB error")
        result = retrieve_similar_requirements(query_text="test")
        self.assertEqual(result['status'], "error")
        self.assertEqual(result['error_message'], "Failed to retrieve requirements: DB error")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
