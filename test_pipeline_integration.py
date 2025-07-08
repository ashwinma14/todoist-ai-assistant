#!/usr/bin/env python3
"""
Test script to verify Phase 3 LabelingPipeline integration
"""

import sys
import os
import json
import tempfile
from unittest.mock import MagicMock

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from labeling_pipeline import LabelingPipeline, PipelineFactory, LabelingResult


def test_pipeline_creation():
    """Test that pipeline can be created successfully"""
    print("Testing pipeline creation...")
    
    # Mock configuration
    rules = [
        {"contains": ["meeting"], "label": "meeting"},
        {"contains": ["home"], "label": "home"}
    ]
    
    gpt_fallback = {
        "enabled": True,
        "model": "gpt-3.5-turbo"
    }
    
    tasksense_config = {
        "available_labels": ["work", "personal", "meeting", "home"],
        "confidence_threshold": 0.6
    }
    
    # Create pipeline
    pipeline = LabelingPipeline(
        rules=rules,
        gpt_fallback=gpt_fallback,
        tasksense_config=tasksense_config,
        mode="work",
        verbose=True,
        confidence_threshold=0.7
    )
    
    assert pipeline.confidence_threshold == 0.7
    assert pipeline.mode == "work"
    assert len(pipeline.rules) == 2
    
    print("✅ Pipeline creation successful")


def test_pipeline_factory():
    """Test pipeline factory creation"""
    print("Testing pipeline factory...")
    
    # Mock CLI args
    class MockArgs:
        mode = "personal"
        dry_run = True
        verbose = False
        confidence_threshold = 0.8
        soft_matching = True
    
    rules = [{"contains": ["test"], "label": "test"}]
    gpt_fallback = {"enabled": True}
    tasksense_config = {"available_labels": ["test"]}
    
    pipeline = PipelineFactory.create_from_config(
        rules=rules,
        gpt_fallback=gpt_fallback,
        tasksense_config=tasksense_config,
        cli_args=MockArgs()
    )
    
    assert pipeline.mode == "personal"
    assert pipeline.dry_run == True
    assert pipeline.confidence_threshold == 0.8
    assert pipeline.soft_matching == True
    
    print("✅ Pipeline factory successful")


def test_labeling_result():
    """Test LabelingResult data structure"""
    print("Testing LabelingResult...")
    
    result = LabelingResult(
        task_id="123",
        task_content="Test task content",
        labels_applied=["work", "urgent"],
        confidence_scores={"work": 0.9, "urgent": 0.8}
    )
    
    assert result.task_id == "123"
    assert result.has_new_labels() == True
    assert "work" in result.get_all_labels()
    assert result.get_label_sources() == {}  # No sources set in this test
    
    print("✅ LabelingResult successful")


def test_pipeline_stages():
    """Test pipeline stages with mock data"""
    print("Testing pipeline stages...")
    
    # Create pipeline with mock logger
    pipeline = LabelingPipeline(
        rules=[{"contains": ["meeting"], "label": "meeting"}],
        gpt_fallback={"enabled": False},
        tasksense_config={
            "available_labels": ["meeting", "work"],
            "confidence_threshold": 0.5
        },
        mode="work",
        logger=MagicMock(),
        dry_run=True,
        verbose=True
    )
    
    # Mock task
    task = {
        "id": "test_123",
        "content": "Schedule team meeting for tomorrow",
        "labels": [],
        "project_id": "proj_123"
    }
    
    # Test individual stages
    result = LabelingResult(task_id=task["id"], task_content=task["content"])
    
    # Test stage 1 - would normally call apply_rules_to_task
    # For this test, we'll just set some mock data
    result.rule_labels = {"meeting"}
    result.confidence_scores = {"meeting": 0.8}
    result.explanations = {"meeting": "Task contains meeting keyword"}
    
    # Test stage 2 - domain detection (no URLs in test)
    result.domain_labels = set()
    result.urls_found = []
    
    # Test stage 3 - label consolidation
    result = pipeline._stage_label_consolidation(task, result)
    
    assert "meeting" in result.labels_applied
    assert result.confidence_scores["meeting"] == 0.8
    
    print("✅ Pipeline stages successful")


def test_soft_matching():
    """Test soft matching functionality"""
    print("Testing soft matching...")
    
    pipeline = LabelingPipeline(
        rules=[],
        gpt_fallback={"enabled": False},
        tasksense_config={
            "available_labels": ["work", "personal"],  # "urgent" not in available
            "confidence_threshold": 0.6
        },
        mode="work",
        logger=MagicMock(),
        dry_run=True,
        soft_matching=True
    )
    
    task = {
        "id": "test_456",
        "content": "Urgent task needs attention",
        "labels": []
    }
    
    result = LabelingResult(task_id=task["id"], task_content=task["content"])
    result.rule_labels = {"urgent", "work"}
    result.confidence_scores = {"urgent": 0.8, "work": 0.9}
    
    # Test soft matching
    result = pipeline._stage_label_consolidation(task, result)
    
    assert "urgent" in result.soft_matched_labels
    assert "work" in result.labels_applied
    assert "urgent" not in result.labels_applied
    
    print("✅ Soft matching successful")


def test_feedback_system():
    """Test feedback system foundation"""
    print("Testing feedback system...")
    
    pipeline = LabelingPipeline(
        rules=[],
        gpt_fallback={"enabled": False},
        tasksense_config={"available_labels": ["work"]},
        mode="work",
        logger=MagicMock(),
        dry_run=True,
        interactive_feedback=True,
        confidence_threshold=0.7
    )
    
    task = {
        "id": "test_789",
        "content": "Low confidence task",
        "labels": []
    }
    
    result = LabelingResult(task_id=task["id"], task_content=task["content"])
    result.confidence_scores = {"work": 0.65}  # Just below threshold + 0.1
    result.labels_applied = ["work"]
    
    # Test feedback check
    result = pipeline._check_feedback_needed(task, result)
    
    assert result.feedback_requested == True
    assert "Low confidence labels" in result.feedback_data["triggers"][0]
    
    print("✅ Feedback system successful")


def main():
    """Run all tests"""
    print("🧪 Running Phase 3 Pipeline Integration Tests")
    print("=" * 50)
    
    tests = [
        test_pipeline_creation,
        test_pipeline_factory,
        test_labeling_result,
        test_pipeline_stages,
        test_soft_matching,
        test_feedback_system
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Phase 3 pipeline integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)