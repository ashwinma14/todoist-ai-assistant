"""
Unit tests for GPT-enhanced reranking functionality (Phase 4 Step 2).

Tests the JSON-based prompt construction, response parsing, cost limiting,
and confidence-based filtering.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from task_sense import TaskSense


class TestGPTReranking(unittest.TestCase):
    """Test GPT reranking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "user_profile": "Test user focused on productivity",
            "available_labels": ["work", "personal", "urgent"],
            "default_mode": "personal",
            "reasoning_level": "light",
            "model": "gpt-3.5-turbo"
        }
        
        self.test_ranking_config = {
            "version": "4.0",
            "default_limit": 3,
            "gpt_reranking": {
                "enabled": True,
                "model": "gpt-3.5-turbo",
                "candidate_limit": 5,
                "max_tokens": 500,
                "temperature": 0.3,
                "timeout": 30,
                "cost_limit_per_run_usd": 0.05,
                "confidence_threshold": 0.7,
                "fallback_on_error": True
            }
        }
        
        # Mock TaskSense with test configs
        with patch('task_sense.TaskSense._load_config'), \
             patch('task_sense.TaskSense._load_ranking_config'):
            self.task_sense = TaskSense()
            self.task_sense.config = self.test_config
            self.task_sense.ranking_config = self.test_ranking_config
            self.task_sense.logger = Mock()
    
    def test_gpt_reranking_disabled_fallback(self):
        """Test fallback to base ranking when GPT reranking is disabled."""
        # Disable GPT reranking
        self.task_sense.ranking_config['gpt_reranking']['enabled'] = False
        
        tasks = [
            {'id': '1', 'content': 'Test task 1', 'priority': 2},
            {'id': '2', 'content': 'Test task 2', 'priority': 1}
        ]
        
        with patch.object(self.task_sense, 'rank') as mock_rank:
            mock_rank.return_value = [
                {'task': tasks[0], 'score': 0.8, 'explanation': 'High priority'}
            ]
            
            result = self.task_sense.rank_with_gpt_explanations(tasks, limit=1)
            
            # Should fall back to base ranking
            mock_rank.assert_called_once()
            self.assertEqual(len(result), 1)
            self.task_sense.logger.info.assert_called_with(
                "GPT_RANK_DISABLED: GPT reranking is disabled in configuration"
            )
    
    def test_json_prompt_construction(self):
        """Test JSON-based prompt construction."""
        task = {
            'id': 'test_123',
            'content': 'URGENT: Fix critical bug',
            'priority': 1,
            'due': {'string': 'today'},
            'labels': ['work', 'urgent']
        }
        
        prompt = self.task_sense._construct_gpt_ranking_prompt(
            task, 0.85, "high priority task", "work"
        )
        
        # Verify prompt contains JSON structure
        self.assertIn('INPUT DATA:', prompt)
        self.assertIn('REQUIRED JSON RESPONSE FORMAT:', prompt)
        
        # Extract and validate JSON from prompt
        lines = prompt.split('\n')
        json_start = None
        for i, line in enumerate(lines):
            if line.strip() == 'INPUT DATA:':
                json_start = i + 1
                break
        
        self.assertIsNotNone(json_start)
        
        # Find the JSON block
        json_lines = []
        for i in range(json_start, len(lines)):
            if lines[i].strip() == 'INSTRUCTIONS:':
                break
            json_lines.append(lines[i])
        
        json_text = '\n'.join(json_lines).strip()
        
        # Parse the JSON to ensure it's valid
        try:
            prompt_data = json.loads(json_text)
            self.assertEqual(prompt_data['task']['content'], 'URGENT: Fix critical bug')
            self.assertEqual(prompt_data['task']['priority'], 1)
            self.assertEqual(prompt_data['context']['mode'], 'work')
            self.assertEqual(prompt_data['context']['base_score'], 0.85)
        except json.JSONDecodeError as e:
            self.fail(f"Generated prompt does not contain valid JSON: {e}")
    
    def test_json_response_parsing_success(self):
        """Test successful JSON response parsing."""
        task = {'id': 'test_123', 'content': 'Test task'}
        base_score = 0.75
        base_explanation = "Base explanation"
        
        # Mock GPT response with valid JSON
        gpt_response = """{
            "explanation": "This task needs immediate attention due to urgency indicators",
            "confidence": 0.9,
            "rerank_score": 0.85,
            "reasoning": "Detected urgent keywords",
            "urgency_indicators": ["urgent", "immediate"],
            "mode_alignment": "high priority alignment",
            "recommendation": "prioritize"
        }"""
        
        result = self.task_sense._parse_gpt_ranking_response(
            gpt_response, task, base_score, base_explanation
        )
        
        self.assertEqual(result['explanation'], "This task needs immediate attention due to urgency indicators")
        self.assertEqual(result['confidence'], 0.9)
        self.assertEqual(result['rerank_score'], 0.85)
        self.assertEqual(result['source'], 'gpt_reranked')  # Significant score change
        self.assertEqual(result['reasoning'], "Detected urgent keywords")
        self.assertEqual(result['urgency_indicators'], ["urgent", "immediate"])
        self.assertEqual(result['recommendation'], "prioritize")
    
    def test_json_response_parsing_fallback(self):
        """Test fallback regex parsing for non-JSON responses."""
        task = {'id': 'test_123', 'content': 'Test task'}
        base_score = 0.75
        base_explanation = "Base explanation"
        
        # Mock non-JSON response (legacy format)
        gpt_response = """
        EXPLANATION: This task should be prioritized
        CONFIDENCE: 0.8
        RERANK_SCORE: 0.8
        """
        
        with patch.object(self.task_sense, '_parse_gpt_ranking_response_regex_fallback') as mock_fallback:
            mock_fallback.return_value = {
                'explanation': 'Fallback explanation',
                'confidence': 0.8,
                'rerank_score': 0.8,
                'source': 'gpt_enhanced'
            }
            
            result = self.task_sense._parse_gpt_ranking_response(
                gpt_response, task, base_score, base_explanation
            )
            
            mock_fallback.assert_called_once()
            self.assertEqual(result['explanation'], 'Fallback explanation')
    
    def test_cost_estimation(self):
        """Test GPT request cost estimation."""
        task = {
            'content': 'This is a test task with some content to estimate tokens'
        }
        
        gpt_config = {
            'model': 'gpt-3.5-turbo',
            'max_tokens': 500
        }
        
        cost = self.task_sense._estimate_gpt_request_cost(task, gpt_config)
        
        # Should return a reasonable cost estimate
        self.assertIsInstance(cost, float)
        self.assertGreater(cost, 0)
        self.assertLess(cost, 1.0)  # Should be less than $1
    
    def test_cost_limiting_stops_processing(self):
        """Test that cost limiting stops processing when limit is reached."""
        # Set very low cost limit
        self.task_sense.ranking_config['gpt_reranking']['cost_limit_per_run_usd'] = 0.001
        
        tasks = [
            {'id': '1', 'content': 'Task 1', 'priority': 1},
            {'id': '2', 'content': 'Task 2', 'priority': 1},
            {'id': '3', 'content': 'Task 3', 'priority': 1}
        ]
        
        with patch.object(self.task_sense, 'rank') as mock_rank, \
             patch.object(self.task_sense, '_estimate_gpt_request_cost') as mock_cost:
            
            # Mock base ranking
            mock_rank.return_value = [
                {'task': tasks[0], 'score': 0.9, 'explanation': 'High priority'},
                {'task': tasks[1], 'score': 0.8, 'explanation': 'Medium priority'},
                {'task': tasks[2], 'score': 0.7, 'explanation': 'Lower priority'}
            ]
            
            # Mock high cost estimate to trigger limit
            mock_cost.return_value = 0.002  # Higher than limit
            
            result = self.task_sense.rank_with_gpt_explanations(tasks, limit=3)
            
            # Should stop processing due to cost limit
            self.task_sense.logger.warning.assert_called()
            warning_call = self.task_sense.logger.warning.call_args[0][0]
            self.assertIn("GPT_RANK_COST_LIMIT", warning_call)
    
    def test_confidence_threshold_filtering(self):
        """Test that low confidence results fall back to base score."""
        tasks = [{'id': '1', 'content': 'Test task', 'priority': 1}]
        
        with patch.object(self.task_sense, 'rank') as mock_rank, \
             patch.object(self.task_sense, '_get_gpt_ranking_explanation') as mock_gpt:
            
            mock_rank.return_value = [
                {'task': tasks[0], 'score': 0.8, 'explanation': 'Base explanation'}
            ]
            
            # Mock low confidence GPT response
            mock_gpt.return_value = {
                'explanation': 'Low confidence explanation',
                'confidence': 0.5,  # Below threshold of 0.7
                'rerank_score': 0.9,
                'source': 'gpt_enhanced',
                'cost': 0.001
            }
            
            result = self.task_sense.rank_with_gpt_explanations(tasks, limit=1)
            
            # Should log low confidence and use base score
            self.task_sense.logger.info.assert_any_call(
                unittest.mock.ANY  # Allow any string containing GPT_RANK_LOW_CONFIDENCE
            )
            
            # Verify the result uses base score due to low confidence
            enhanced_task = result[0]
            self.assertEqual(enhanced_task['final_score'], 0.8)  # Base score
    
    def test_mock_mode_gpt_explanation(self):
        """Test mock GPT explanation generation."""
        task = {
            'id': 'test_123',
            'content': 'URGENT: Critical bug fix needed',
            'priority': 1
        }
        
        result = self.task_sense._get_mock_gpt_explanation(
            task, 0.8, "High priority task", "work"
        )
        
        # Should detect urgency and recommend prioritization
        self.assertIn('urgent', result['explanation'].lower())
        self.assertEqual(result['confidence'], 0.9)
        self.assertEqual(result['recommendation'], 'prioritize')
        self.assertIn('urgent', result['urgency_indicators'])
        self.assertEqual(result['cost'], 0.0)  # Mock has no cost
    
    def test_enhanced_task_structure(self):
        """Test that enhanced tasks contain all required fields."""
        tasks = [{'id': '1', 'content': 'Test task', 'priority': 2}]
        
        with patch.object(self.task_sense, 'rank') as mock_rank:
            mock_rank.return_value = [
                {'task': tasks[0], 'score': 0.7, 'explanation': 'Base explanation'}
            ]
            
            # Enable mock mode
            self.task_sense.config['mock_mode'] = {'enabled': True}
            
            result = self.task_sense.rank_with_gpt_explanations(tasks, limit=1)
            
            self.assertEqual(len(result), 1)
            enhanced_task = result[0]
            
            # Verify all expected fields are present
            required_fields = [
                'task', 'base_score', 'base_explanation', 'gpt_explanation',
                'gpt_confidence', 'gpt_model', 'gpt_rerank_score', 'final_score',
                'ranking_source', 'gpt_reasoning', 'urgency_indicators',
                'mode_alignment', 'recommendation', 'cost'
            ]
            
            for field in required_fields:
                self.assertIn(field, enhanced_task, f"Missing field: {field}")


if __name__ == '__main__':
    unittest.main()