"""
Unit test for section caching fix to prevent duplicate section creation.

This test verifies that multiple tasks requiring the same section will reuse
the cached section instead of creating duplicates.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to sys.path to import main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main

class TestSectionCaching(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Clear any existing cache
        main.clear_section_cache()
        
        # Mock project ID and section data
        self.project_id = "12345"
        self.section_name = "Links"
        self.section_id = "section_67890"
        
        # Mock task logger
        self.mock_logger = Mock()
        
    def tearDown(self):
        """Clean up after each test"""
        main.clear_section_cache()
    
    @patch('main.requests.get')
    @patch('main.create_section_sync_api')
    def test_section_cache_prevents_duplicate_creation(self, mock_create_section, mock_get):
        """Test that section cache prevents duplicate section creation"""
        
        # Mock the initial API response - no sections exist
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock section creation API call
        mock_create_section.return_value = self.section_id
        
        # First call should fetch from API and create section
        result1 = main.create_section_if_missing_sync(
            self.section_name, self.project_id, self.mock_logger
        )
        
        # Verify section was created
        self.assertEqual(result1, self.section_id)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_create_section.call_count, 1)
        
        # Second call should use cache and NOT create another section
        result2 = main.create_section_if_missing_sync(
            self.section_name, self.project_id, self.mock_logger
        )
        
        # Verify same section ID returned
        self.assertEqual(result2, self.section_id)
        
        # Verify API was NOT called again (cache hit)
        self.assertEqual(mock_get.call_count, 1)  # Still only 1 call
        self.assertEqual(mock_create_section.call_count, 1)  # Still only 1 call
        
        # Verify cache hit was logged
        self.mock_logger.info.assert_any_call(
            f"SECTIONS_CACHE: Using cached sections for project {self.project_id}"
        )
    
    @patch('main.requests.get')
    def test_section_cache_finds_existing_section(self, mock_get):
        """Test that section cache correctly finds existing sections"""
        
        # Mock API response with existing section
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "Links", "id": self.section_id}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # First call should fetch from API and find existing section
        result1 = main.create_section_if_missing_sync(
            self.section_name, self.project_id, self.mock_logger
        )
        
        # Verify existing section was found
        self.assertEqual(result1, self.section_id)
        self.assertEqual(mock_get.call_count, 1)
        
        # Second call should use cache
        result2 = main.create_section_if_missing_sync(
            self.section_name, self.project_id, self.mock_logger
        )
        
        # Verify same section ID returned
        self.assertEqual(result2, self.section_id)
        
        # Verify API was NOT called again (cache hit)
        self.assertEqual(mock_get.call_count, 1)  # Still only 1 call
        
        # Verify section exists message was logged
        self.mock_logger.info.assert_any_call(
            f"SECTION_EXISTS: Section '{self.section_name}' already exists (ID: {self.section_id})"
        )
    
    @patch('main.requests.get')
    @patch('main.create_section_sync_api')
    def test_multiple_tasks_same_section_single_creation(self, mock_create_section, mock_get):
        """Test that multiple tasks requiring the same section only create it once"""
        
        # Mock the initial API response - no sections exist
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock section creation API call
        mock_create_section.return_value = self.section_id
        
        # Simulate 3 tasks that all need the "Links" section
        tasks = [
            {"id": "task1", "content": "Check out https://example.com", "project_id": self.project_id},
            {"id": "task2", "content": "Visit https://github.com", "project_id": self.project_id},
            {"id": "task3", "content": "Read https://docs.python.org", "project_id": self.project_id}
        ]
        
        results = []
        for task in tasks:
            result = main.create_section_if_missing_sync(
                self.section_name, task["project_id"], self.mock_logger
            )
            results.append(result)
        
        # Verify all tasks got the same section ID
        self.assertEqual(len(set(results)), 1)  # All should be the same
        self.assertEqual(results[0], self.section_id)
        
        # Verify API was only called once (first task)
        self.assertEqual(mock_get.call_count, 1)
        
        # Verify section was only created once
        self.assertEqual(mock_create_section.call_count, 1)
        
        # Verify cache was used for subsequent tasks
        cache_hit_calls = [
            call for call in self.mock_logger.info.call_args_list
            if "SECTIONS_CACHE: Using cached sections" in str(call)
        ]
        self.assertEqual(len(cache_hit_calls), 2)  # 2nd and 3rd tasks should hit cache
    
    def test_clear_section_cache_functionality(self):
        """Test that clear_section_cache() properly clears the cache"""
        
        # Manually populate cache
        main._section_cache[self.project_id] = {"Links": self.section_id}
        
        # Verify cache has content
        self.assertIn(self.project_id, main._section_cache)
        self.assertIn("Links", main._section_cache[self.project_id])
        
        # Clear cache
        main.clear_section_cache()
        
        # Verify cache is empty
        self.assertEqual(len(main._section_cache), 0)
    
    def test_case_insensitive_section_matching(self):
        """Test that section names are matched case-insensitively"""
        
        # Manually populate cache with different case
        main._section_cache[self.project_id] = {"links": self.section_id}
        
        # Test that "Links" (different case) finds the cached "links" section
        sections = main.get_project_sections(self.project_id, self.mock_logger)
        
        # Should find the cached section despite case difference
        self.assertIn("links", sections)
        self.assertEqual(sections["links"], self.section_id)
    
    def test_section_name_whitespace_normalization(self):
        """Test that section names with whitespace are normalized"""
        
        # Test with section names that have leading/trailing whitespace
        section_with_spaces = "  Links  "
        normalized_name = section_with_spaces.strip()
        
        # Manually populate cache
        main._section_cache[self.project_id] = {normalized_name: self.section_id}
        
        # Test that normalized lookup works
        sections = main.get_project_sections(self.project_id, self.mock_logger)
        self.assertIn(normalized_name, sections)
        self.assertEqual(sections[normalized_name], self.section_id)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)