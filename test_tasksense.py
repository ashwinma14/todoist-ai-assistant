#!/usr/bin/env python3
"""
Test script for TaskSense AI Engine Phase 1 implementation.
"""

import os
import sys
import json
from task_sense import TaskSense

def test_tasksense_initialization():
    """Test TaskSense initialization."""
    print("🧪 Testing TaskSense initialization...")
    try:
        task_sense = TaskSense()
        print("✅ TaskSense initialized successfully")
        print(f"   Version: {task_sense.version}")
        print(f"   Source: {task_sense.source}")
        return True
    except Exception as e:
        print(f"❌ TaskSense initialization failed: {e}")
        return False

def test_dry_run_mode():
    """Test dry run mode functionality."""
    print("\n🧪 Testing dry run mode...")
    try:
        task_sense = TaskSense()
        result = task_sense.label('Book fall daycare tour', dry_run=True)
        
        # Verify structure
        required_keys = ['labels', 'explanation', 'confidence', 'source', 'engine_meta']
        for key in required_keys:
            if key not in result:
                print(f"❌ Missing required key: {key}")
                return False
        
        print("✅ Dry run mode working correctly")
        print(f"   Result: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        print(f"❌ Dry run mode failed: {e}")
        return False

def test_mock_mode():
    """Test mock mode functionality."""
    print("\n🧪 Testing mock mode...")
    try:
        # Set mock mode
        os.environ['GPT_MOCK_MODE'] = '1'
        
        task_sense = TaskSense()
        
        # Test different types of tasks
        test_cases = [
            ('Clean the garage this weekend', ['home']),
            ('Meeting with client about project', ['work']),
            ('Pay taxes and bills', ['admin']),
            ('Urgent: Fix the bug immediately!', ['urgent'])
        ]
        
        for task_content, expected_labels in test_cases:
            result = task_sense.label(task_content)
            
            if not result.get('labels'):
                print(f"❌ No labels returned for: {task_content}")
                return False
                
            print(f"   Task: {task_content}")
            print(f"   Labels: {result['labels']}")
            print(f"   Explanation: {result.get('explanation', 'N/A')}")
        
        print("✅ Mock mode working correctly")
        return True
    except Exception as e:
        print(f"❌ Mock mode failed: {e}")
        return False
    finally:
        # Clean up
        if 'GPT_MOCK_MODE' in os.environ:
            del os.environ['GPT_MOCK_MODE']

def test_config_loading():
    """Test configuration loading."""
    print("\n🧪 Testing configuration loading...")
    try:
        task_sense = TaskSense()
        config = task_sense.config
        
        # Check required config keys
        required_keys = ['user_profile', 'available_labels', 'default_mode', 'reasoning_level']
        for key in required_keys:
            if key not in config:
                print(f"❌ Missing required config key: {key}")
                return False
        
        print("✅ Configuration loaded successfully")
        print(f"   User profile: {config.get('user_profile', 'N/A')[:50]}...")
        print(f"   Available labels: {config.get('available_labels', [])}")
        print(f"   Default mode: {config.get('default_mode', 'N/A')}")
        print(f"   Reasoning level: {config.get('reasoning_level', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_prompt_templates():
    """Test prompt template system."""
    print("\n🧪 Testing prompt template system...")
    try:
        from task_sense_prompts import TaskSensePrompts
        
        prompts = TaskSensePrompts()
        
        # Test different modes and reasoning levels
        test_cases = [
            ('personal', 'light'),
            ('work', 'minimal'),
            ('weekend', 'deep'),
            ('default', 'light')
        ]
        
        for mode, reasoning_level in test_cases:
            prompt = prompts.get_prompt(mode, reasoning_level)
            if not prompt:
                print(f"❌ No prompt returned for mode: {mode}, reasoning: {reasoning_level}")
                return False
            
            print(f"   Mode: {mode}, Reasoning: {reasoning_level}")
            print(f"   Prompt length: {len(prompt)} characters")
        
        print("✅ Prompt template system working correctly")
        return True
    except Exception as e:
        print(f"❌ Prompt template system failed: {e}")
        return False

def test_main_integration():
    """Test integration with main.py."""
    print("\n🧪 Testing main.py integration...")
    try:
        # Test import
        from main import TASKSENSE_AVAILABLE, apply_rules_to_task
        
        if not TASKSENSE_AVAILABLE:
            print("❌ TaskSense not available in main.py")
            return False
            
        print("✅ TaskSense integration successful")
        print(f"   TASKSENSE_AVAILABLE: {TASKSENSE_AVAILABLE}")
        return True
    except Exception as e:
        print(f"❌ Main.py integration failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting TaskSense Phase 1 Regression Tests")
    print("=" * 50)
    
    tests = [
        test_tasksense_initialization,
        test_config_loading,
        test_prompt_templates,
        test_dry_run_mode,
        test_mock_mode,
        test_main_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! TaskSense Phase 1 is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)