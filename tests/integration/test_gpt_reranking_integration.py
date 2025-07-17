"""
Integration tests for GPT-enhanced reranking with full pipeline.

Tests the complete flow from CLI to ranking output, including
configuration loading, cost controls, and output formatting.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from task_sense import TaskSense


class TestGPTRerankingIntegration(unittest.TestCase):
    """Test GPT reranking integration with full pipeline."""
    
    def setUp(self):
        """Set up test fixtures with temporary config files."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test config files
        self.task_sense_config = {
            "user_profile": "Productivity-focused developer working on multiple projects",
            "available_labels": ["work", "personal", "urgent", "meeting", "bug"],
            "default_mode": "work",
            "reasoning_level": "detailed",
            "model": "gpt-3.5-turbo"
        }
        
        self.ranking_config = {
            "version": "4.0",
            "default_limit": 3,
            "scoring_weights": {
                "priority": 0.45,
                "due_date": 0.3,
                "age": 0.05,
                "label_preference": 0.2
            },
            "gpt_reranking": {
                "enabled": True,
                "model": "gpt-3.5-turbo",
                "candidate_limit": 8,
                "max_tokens": 800,
                "temperature": 0.3,
                "timeout": 30,
                "cost_limit_per_run_usd": 0.10,
                "confidence_threshold": 0.75,
                "fallback_on_error": True
            },
            "mode_settings": {
                "work": {
                    "preferred_labels": ["work", "meeting", "urgent", "bug"],
                    "weights": {"priority": 0.6, "due_date": 0.3, "age": 0.05, "label_preference": 0.05}
                }
            }
        }
        
        # Write config files
        self.task_sense_config_path = os.path.join(self.temp_dir, 'task_sense_config.json')
        self.ranking_config_path = os.path.join(self.temp_dir, 'ranking_config.json')
        
        with open(self.task_sense_config_path, 'w') as f:
            json.dump(self.task_sense_config, f)
        
        with open(self.ranking_config_path, 'w') as f:
            json.dump(self.ranking_config, f)
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_full_gpt_reranking_pipeline(self):
        """Test complete GPT reranking pipeline with realistic data."""
        # Initialize TaskSense with real config loading
        task_sense = TaskSense(
            config_path=self.task_sense_config_path,
            ranking_config_path=self.ranking_config_path
        )
        
        # Mock logger
        task_sense.logger = Mock()
        
        # Sample tasks with varying priorities and content
        test_tasks = [
            {
                'id': '001',
                'content': 'URGENT: Fix authentication bug affecting all users',
                'priority': 1,
                'due': {'string': 'today'},
                'labels': ['work', 'urgent', 'bug'],
                'section_id': 'work_section'
            },
            {
                'id': '002', 
                'content': 'Schedule quarterly planning meeting with team',
                'priority': 2,
                'due': {'string': 'this week'},
                'labels': ['work', 'meeting'],
                'section_id': 'work_section'
            },
            {
                'id': '003',
                'content': 'Update project documentation',
                'priority': 3,
                'due': None,
                'labels': ['work'],
                'section_id': 'work_section'
            },
            {
                'id': '004',
                'content': 'Buy groceries for weekend',
                'priority': 4,
                'due': {'string': 'tomorrow'},
                'labels': ['personal'],
                'section_id': 'personal_section'
            },
            {
                'id': '005',
                'content': 'Review pull request from junior developer',
                'priority': 2,
                'due': {'string': 'today'},
                'labels': ['work'],
                'section_id': 'work_section'
            }
        ]
        
        # Enable mock mode to avoid actual OpenAI API calls
        os.environ['GPT_MOCK_MODE'] = '1'
        
        try:
            # Run GPT-enhanced ranking
            result = task_sense.rank_with_gpt_explanations(
                test_tasks, 
                mode='work', 
                limit=3
            )
            
            # Verify results
            self.assertEqual(len(result), 3)
            
            # Check that all required fields are present
            for i, ranked_task in enumerate(result):
                self.assertIn('task', ranked_task)
                self.assertIn('final_score', ranked_task)
                self.assertIn('gpt_explanation', ranked_task)
                self.assertIn('gpt_confidence', ranked_task)
                self.assertIn('ranking_source', ranked_task)
                self.assertIn('recommendation', ranked_task)
                self.assertIn('urgency_indicators', ranked_task)
                
                # Verify task data is preserved
                task_data = ranked_task['task']
                self.assertIn('id', task_data)
                self.assertIn('content', task_data)
            
            # Verify urgent task is prioritized (should be first or second)
            urgent_task_found = False
            for ranked_task in result[:2]:  # Check top 2
                if 'URGENT' in ranked_task['task']['content']:
                    urgent_task_found = True
                    # Just verify it has some enhancement - score varies based on base ranking
                    self.assertIn('gpt_explanation', ranked_task)
                    self.assertIn('ranking_source', ranked_task)
                    break
            
            self.assertTrue(urgent_task_found, "Urgent task should be in top 2 results")
            
            # Verify logging calls were made
            task_sense.logger.info.assert_any_call(
                unittest.mock.ANY  # GPT_RANK_START message
            )
            
            # Check for cost and configuration logging
            log_calls = [call[0][0] for call in task_sense.logger.info.call_args_list]
            config_log_found = any('GPT_RANK_CONFIG' in call for call in log_calls)
            summary_log_found = any('GPT_RANK_SUMMARY' in call for call in log_calls)
            
            self.assertTrue(config_log_found, "Should log GPT configuration")
            self.assertTrue(summary_log_found, "Should log ranking summary")
            
        finally:
            # Clean up environment
            if 'GPT_MOCK_MODE' in os.environ:
                del os.environ['GPT_MOCK_MODE']
    
    def test_gpt_reranking_disabled_integration(self):
        """Test integration when GPT reranking is disabled in config."""
        # Disable GPT reranking in config
        self.ranking_config['gpt_reranking']['enabled'] = False
        
        with open(self.ranking_config_path, 'w') as f:
            json.dump(self.ranking_config, f)
        
        task_sense = TaskSense(
            config_path=self.task_sense_config_path,
            ranking_config_path=self.ranking_config_path
        )
        task_sense.logger = Mock()
        
        test_tasks = [
            {'id': '1', 'content': 'Test task', 'priority': 1, 'labels': ['work']}
        ]
        
        result = task_sense.rank_with_gpt_explanations(test_tasks, limit=1)
        
        # Should fall back to base ranking
        self.assertEqual(len(result), 1)
        
        # Should not have GPT-specific fields
        ranked_task = result[0]
        self.assertNotIn('gpt_explanation', ranked_task)
        self.assertNotIn('final_score', ranked_task)
        
        # Should log that GPT reranking is disabled
        log_calls = [call[0][0] for call in task_sense.logger.info.call_args_list]
        disabled_log_found = any('GPT_RANK_DISABLED' in call for call in log_calls)
        self.assertTrue(disabled_log_found, "Should log that GPT reranking is disabled")
    
    def test_cost_limit_integration(self):
        """Test cost limiting in integration scenario."""
        # Set very low cost limit
        self.ranking_config['gpt_reranking']['cost_limit_per_run_usd'] = 0.001
        
        with open(self.ranking_config_path, 'w') as f:
            json.dump(self.ranking_config, f)
        
        task_sense = TaskSense(
            config_path=self.task_sense_config_path,
            ranking_config_path=self.ranking_config_path
        )
        task_sense.logger = Mock()
        
        # Multiple tasks to trigger cost limit
        test_tasks = [
            {'id': f'{i}', 'content': f'Task {i} with some content', 'priority': 1, 'labels': ['work']}
            for i in range(5)
        ]
        
        # Mock cost estimation to return high cost
        with patch.object(task_sense, '_estimate_gpt_request_cost', return_value=0.002):
            result = task_sense.rank_with_gpt_explanations(test_tasks, limit=5)
            
            # Should stop processing due to cost limit
            task_sense.logger.warning.assert_called()
            warning_call = task_sense.logger.warning.call_args[0][0]
            self.assertIn("GPT_RANK_COST_LIMIT", warning_call)
    
    def test_confidence_threshold_integration(self):
        """Test confidence threshold filtering in integration."""
        # Set high confidence threshold
        self.ranking_config['gpt_reranking']['confidence_threshold'] = 0.95
        
        with open(self.ranking_config_path, 'w') as f:
            json.dump(self.ranking_config, f)
        
        task_sense = TaskSense(
            config_path=self.task_sense_config_path,
            ranking_config_path=self.ranking_config_path
        )
        task_sense.logger = Mock()
        
        test_tasks = [
            {'id': '1', 'content': 'Regular task', 'priority': 2, 'labels': ['work']}
        ]
        
        # Enable mock mode (mock responses have 0.6 confidence for regular tasks)
        os.environ['GPT_MOCK_MODE'] = '1'
        
        try:
            result = task_sense.rank_with_gpt_explanations(test_tasks, limit=1)
            
            # Should log low confidence filtering
            log_calls = [call[0][0] for call in task_sense.logger.info.call_args_list]
            low_confidence_log = any('GPT_RANK_LOW_CONFIDENCE' in call for call in log_calls)
            self.assertTrue(low_confidence_log, "Should log low confidence filtering")
            
            # Result should still exist but with base score
            self.assertEqual(len(result), 1)
            enhanced_task = result[0]
            self.assertEqual(enhanced_task['ranking_source'], 'low_confidence_fallback')
            
        finally:
            if 'GPT_MOCK_MODE' in os.environ:
                del os.environ['GPT_MOCK_MODE']
    
    def test_multi_mode_ranking_integration(self):
        """Test GPT reranking across different modes."""
        task_sense = TaskSense(
            config_path=self.task_sense_config_path,
            ranking_config_path=self.ranking_config_path
        )
        task_sense.logger = Mock()
        
        # Tasks suitable for different modes
        work_task = {
            'id': '1',
            'content': 'Critical production bug',
            'priority': 1,
            'labels': ['work', 'urgent', 'bug']
        }
        
        personal_task = {
            'id': '2', 
            'content': 'Family dinner planning',
            'priority': 3,
            'labels': ['personal', 'family']
        }
        
        os.environ['GPT_MOCK_MODE'] = '1'
        
        try:
            # Test work mode
            work_result = task_sense.rank_with_gpt_explanations(
                [work_task, personal_task], mode='work', limit=2
            )
            
            # Work task should be ranked higher in work mode
            self.assertEqual(work_result[0]['task']['id'], '1')
            
            # Test personal mode (would need personal mode config, but testing concept)
            personal_result = task_sense.rank_with_gpt_explanations(
                [work_task, personal_task], mode='personal', limit=2
            )
            
            # Should still return results
            self.assertEqual(len(personal_result), 2)
            
        finally:
            if 'GPT_MOCK_MODE' in os.environ:
                del os.environ['GPT_MOCK_MODE']
    
    def test_error_handling_integration(self):
        """Test error handling and fallback behavior."""
        task_sense = TaskSense(
            config_path=self.task_sense_config_path,
            ranking_config_path=self.ranking_config_path
        )
        task_sense.logger = Mock()
        
        test_tasks = [
            {'id': '1', 'content': 'Test task', 'priority': 1, 'labels': ['work']}
        ]
        
        # Mock GPT explanation to return error result instead of raising exception
        def mock_gpt_explanation_error(*args, **kwargs):
            return {
                'explanation': 'Error occurred',
                'confidence': 0.0,
                'model': 'error',
                'rerank_score': args[1],  # base_score
                'source': 'base_only',
                'cost': 0.0
            }
        
        with patch.object(task_sense, '_get_gpt_ranking_explanation', side_effect=mock_gpt_explanation_error):
            # Should not crash, should fall back gracefully
            result = task_sense.rank_with_gpt_explanations(test_tasks, limit=1)
            
            # Should still return results with error handling
            self.assertEqual(len(result), 1)
            # Check that it handled the error gracefully (could be base_only or low_confidence_fallback)
            self.assertIn(result[0]['ranking_source'], ['base_only', 'low_confidence_fallback'])


if __name__ == '__main__':
    unittest.main()