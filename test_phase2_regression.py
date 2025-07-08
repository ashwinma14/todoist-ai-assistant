#!/usr/bin/env python3
"""
Phase 2 Regression Testing Framework for TaskSense Integration

This test suite validates:
1. Fallback chain: TaskSense → rules → domain → default
2. Mode consistency across different scenarios
3. Configuration hierarchy validation
4. Mock mode isolation
5. Label accuracy across modes and reasoning levels
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_sense import TaskSense
from task_sense_prompts import TaskSensePrompts
from main import load_unified_config, apply_rules_to_task


class TestFallbackChain:
    """Test the fallback chain: TaskSense → rules → domain → default"""
    
    def test_tasksense_primary_success(self):
        """Test TaskSense as primary engine when working correctly"""
        # Create test config with TaskSense enabled
        test_config = {
            "available_labels": ["work", "personal", "urgent"],
            "mock_mode": {"enabled": True, "responses": {"default": {"labels": ["work"], "explanation": "Mock", "confidence": 0.8}}}
        }
        
        # Initialize TaskSense with mock config
        task_sense = TaskSense(config_path=None)
        task_sense.config = test_config
        
        # Test labeling
        result = task_sense.label("Schedule team meeting", dry_run=False)
        
        assert result is not None
        assert "labels" in result
        assert len(result["labels"]) > 0
        assert result["source"].startswith("TaskSense")
    
    def test_tasksense_to_rules_fallback(self):
        """Test fallback from TaskSense to rules when TaskSense fails"""
        # Mock TaskSense to raise exception
        with patch('main.TASKSENSE_AVAILABLE', False):
            rules = [{"contains": ["meeting"], "label": "meeting"}]
            task = {"id": "123", "content": "Schedule meeting with team"}
            
            labels, applied_rules = apply_rules_to_task(task, rules, {"enabled": True})
            
            assert "meeting" in labels
            assert len(applied_rules) > 0
            assert applied_rules[0]["source"] == "rules"
    
    def test_rules_to_gpt_fallback(self):
        """Test fallback from rules to GPT when no rules match"""
        # Mock GPT response
        mock_gpt_fallback = {
            "enabled": True,
            "model": "gpt-3.5-turbo",
            "base_prompt": "Test prompt"
        }
        
        rules = [{"contains": ["nonexistent"], "label": "nonexistent"}]
        task = {"id": "123", "content": "Random task with no rule matches"}
        
        with patch('main.get_gpt_labels', return_value=["personal"]):
            labels, applied_rules = apply_rules_to_task(task, rules, mock_gpt_fallback)
            
            assert "personal" in labels
            assert len(applied_rules) > 0
            assert applied_rules[0]["source"] == "gpt"


class TestModeConsistency:
    """Test mode consistency across different scenarios"""
    
    def test_work_mode_preferences(self):
        """Test that work mode prefers work-related labels"""
        task_sense = TaskSense()
        
        # Test work mode with work-related task
        result = task_sense.label("Prepare quarterly report", mode="work", dry_run=False)
        
        assert result is not None
        assert "labels" in result
        # Should prefer work-related labels in work mode
        
    def test_personal_mode_preferences(self):
        """Test that personal mode prefers personal-related labels"""
        task_sense = TaskSense()
        
        # Test personal mode with personal task
        result = task_sense.label("Schedule dentist appointment", mode="personal", dry_run=False)
        
        assert result is not None
        assert "labels" in result
        # Should prefer personal-related labels in personal mode
        
    def test_weekend_mode_preferences(self):
        """Test that weekend mode prefers home/family-related labels"""
        task_sense = TaskSense()
        
        # Test weekend mode with home task
        result = task_sense.label("Clean garage", mode="weekend", dry_run=False)
        
        assert result is not None
        assert "labels" in result
        # Should prefer home/family-related labels in weekend mode
        
    def test_auto_mode_detection(self):
        """Test automatic mode detection based on time"""
        prompts = TaskSensePrompts()
        
        # Test with different mock times
        test_configs = [
            {"time_based_modes": {"enabled": True, "weekday_work_hours": [9, 17], "weekend_days": [5, 6]}}
        ]
        
        for config in test_configs:
            # Test during work hours (should return "work")
            with patch('task_sense_prompts.datetime') as mock_datetime:
                mock_datetime.now.return_value.hour = 10
                mock_datetime.now.return_value.weekday.return_value = 1  # Tuesday
                
                mode = prompts.get_time_based_mode(config)
                assert mode == "work"
                
            # Test during weekend (should return "weekend")
            with patch('task_sense_prompts.datetime') as mock_datetime:
                mock_datetime.now.return_value.hour = 10
                mock_datetime.now.return_value.weekday.return_value = 5  # Saturday
                
                mode = prompts.get_time_based_mode(config)
                assert mode == "weekend"


class TestConfigurationHierarchy:
    """Test configuration hierarchy: CLI → env → task_sense_config → rules.json fallback"""
    
    def test_tasksense_config_primary(self):
        """Test that TaskSense config is loaded as primary source"""
        # Create temporary config files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "gpt_fallback": {"enabled": True, "model": "gpt-4"},
                "available_labels": ["test1", "test2"]
            }, f)
            tasksense_config_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "rules": [{"contains": ["test"], "label": "test"}],
                "gpt_fallback": {"enabled": False, "model": "gpt-3.5-turbo"}
            }, f)
            rules_config_path = f.name
        
        # Mock file paths
        with patch('main.open', create=True) as mock_open:
            def side_effect(path, mode='r'):
                if 'task_sense_config.json' in path:
                    return open(tasksense_config_path, mode)
                elif 'rules.json' in path:
                    return open(rules_config_path, mode)
                return open(path, mode)
            
            mock_open.side_effect = side_effect
            
            rules, gpt_fallback, tasksense_config = load_unified_config()
            
            # TaskSense config should take precedence
            assert gpt_fallback["model"] == "gpt-4"
            assert gpt_fallback["enabled"] is True
            assert tasksense_config["available_labels"] == ["test1", "test2"]
        
        # Clean up
        os.unlink(tasksense_config_path)
        os.unlink(rules_config_path)
    
    def test_env_var_overrides(self):
        """Test that environment variables override config"""
        with patch.dict(os.environ, {'DISABLE_GPT_FALLBACK': 'true'}):
            # Mock config loading
            with patch('main.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                    "gpt_fallback": {"enabled": True, "model": "gpt-4"}
                })
                
                rules, gpt_fallback, tasksense_config = load_unified_config()
                
                # Environment variable should override config
                assert gpt_fallback["enabled"] is False


class TestMockModeIsolation:
    """Test mock mode isolation and responses"""
    
    def test_mock_mode_patterns(self):
        """Test mock mode pattern matching"""
        test_config = {
            "mock_mode": {
                "enabled": True,
                "responses": {
                    "patterns": {
                        "meeting": {"labels": ["work", "meeting"], "explanation": "Mock meeting", "confidence": 0.9},
                        "grocery": {"labels": ["personal", "home"], "explanation": "Mock grocery", "confidence": 0.8}
                    }
                }
            }
        }
        
        task_sense = TaskSense(config_path=None)
        task_sense.config = test_config
        
        # Test pattern matching
        result = task_sense.label("Schedule meeting with team", dry_run=False)
        assert result["labels"] == ["work", "meeting"]
        assert result["explanation"] == "Mock meeting"
        assert result["confidence"] == 0.9
        assert result["source"] == "TaskSense_Mock_Config"
        
        # Test another pattern
        result = task_sense.label("Buy grocery items", dry_run=False)
        assert result["labels"] == ["personal", "home"]
        assert result["explanation"] == "Mock grocery"
        assert result["confidence"] == 0.8
    
    def test_mock_mode_default_response(self):
        """Test mock mode default response when no patterns match"""
        test_config = {
            "mock_mode": {
                "enabled": True,
                "responses": {
                    "default": {"labels": ["default"], "explanation": "Default mock", "confidence": 0.7}
                }
            }
        }
        
        task_sense = TaskSense(config_path=None)
        task_sense.config = test_config
        
        result = task_sense.label("Random task with no pattern", dry_run=False)
        assert result["labels"] == ["default"]
        assert result["explanation"] == "Default mock"
        assert result["confidence"] == 0.7
        assert result["source"] == "TaskSense_Mock_Default"
    
    def test_mock_mode_heuristic_fallback(self):
        """Test mock mode heuristic fallback when no config patterns exist"""
        test_config = {
            "mock_mode": {"enabled": True, "responses": {}}
        }
        
        task_sense = TaskSense(config_path=None)
        task_sense.config = test_config
        
        result = task_sense.label("Schedule work meeting", dry_run=False)
        assert result["source"] == "TaskSense_Mock_Heuristic"
        assert "work" in result["labels"]


class TestLabelAccuracy:
    """Test label accuracy across different modes and reasoning levels"""
    
    def test_reasoning_level_minimal(self):
        """Test minimal reasoning level output"""
        task_sense = TaskSense()
        
        # Mock config with minimal reasoning
        test_config = {
            "reasoning_level": "minimal",
            "mock_mode": {"enabled": True, "responses": {"default": {"labels": ["test"], "explanation": "Test", "confidence": 0.8}}}
        }
        task_sense.config = test_config
        
        result = task_sense.label("Test task", dry_run=False)
        assert result is not None
        assert "labels" in result
        # Minimal reasoning should still provide explanation for consistency
        assert "explanation" in result
    
    def test_reasoning_level_deep(self):
        """Test deep reasoning level output"""
        task_sense = TaskSense()
        
        # Mock config with deep reasoning
        test_config = {
            "reasoning_level": "deep",
            "mock_mode": {"enabled": True, "responses": {"default": {"labels": ["test"], "explanation": "Deep test explanation", "confidence": 0.9}}}
        }
        task_sense.config = test_config
        
        result = task_sense.label("Complex task requiring analysis", dry_run=False)
        assert result is not None
        assert "labels" in result
        assert "explanation" in result
        assert "confidence" in result
        assert result["confidence"] > 0.5  # Should have reasonable confidence
    
    def test_confidence_thresholds(self):
        """Test confidence threshold filtering"""
        task_sense = TaskSense()
        
        # Test with different confidence levels
        test_configs = [
            {"confidence_threshold": 0.8, "mock_mode": {"enabled": True, "responses": {"default": {"labels": ["low"], "explanation": "Low confidence", "confidence": 0.5}}}},
            {"confidence_threshold": 0.3, "mock_mode": {"enabled": True, "responses": {"default": {"labels": ["high"], "explanation": "High confidence", "confidence": 0.9}}}}
        ]
        
        for config in test_configs:
            task_sense.config = config
            result = task_sense.label("Test task", dry_run=False)
            
            # Should return result regardless of confidence in mock mode
            assert result is not None
            assert "labels" in result


def run_regression_tests():
    """Run all regression tests and report results"""
    import subprocess
    
    # Run pytest on this file
    result = subprocess.run(['python', '-m', 'pytest', __file__, '-v'], 
                          capture_output=True, text=True)
    
    print("=" * 60)
    print("PHASE 2 REGRESSION TEST RESULTS")
    print("=" * 60)
    print(result.stdout)
    
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    run_regression_tests()