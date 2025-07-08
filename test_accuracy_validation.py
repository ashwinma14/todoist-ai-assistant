#!/usr/bin/env python3
"""
TaskSense Accuracy Validation Framework

This script validates that TaskSense achieves 80%+ accuracy across different modes
and reasoning levels by testing against a curated set of tasks with expected labels.
"""

import json
import os
import sys
from typing import Dict, List, Tuple
from collections import defaultdict

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_sense import TaskSense
from task_sense_prompts import TaskSensePrompts


# Test dataset with expected labels for different modes
TEST_DATASET = {
    "work": [
        {"task": "Schedule team standup for Monday", "expected": ["work", "meeting"]},
        {"task": "Review quarterly budget proposal", "expected": ["work"]},
        {"task": "Follow up with client about project", "expected": ["work", "followup"]},
        {"task": "Prepare presentation for board meeting", "expected": ["work", "meeting"]},
        {"task": "Call vendor about software license", "expected": ["work", "followup"]},
        {"task": "Complete performance review forms", "expected": ["work", "admin"]},
        {"task": "Submit expense report for travel", "expected": ["work", "admin"]},
        {"task": "Debug critical production issue", "expected": ["work", "urgent"]},
        {"task": "Schedule 1:1 with team member", "expected": ["work", "meeting"]},
        {"task": "Update project documentation", "expected": ["work"]}
    ],
    "personal": [
        {"task": "Schedule dentist appointment", "expected": ["personal", "health"]},
        {"task": "Pick up prescription from pharmacy", "expected": ["personal", "health"]},
        {"task": "Book annual physical exam", "expected": ["personal", "health"]},
        {"task": "Call mom about weekend plans", "expected": ["personal", "family"]},
        {"task": "Buy birthday gift for sister", "expected": ["personal", "family"]},
        {"task": "Read chapter 3 of productivity book", "expected": ["personal", "reading"]},
        {"task": "Practice guitar for 30 minutes", "expected": ["personal"]},
        {"task": "Update LinkedIn profile", "expected": ["personal"]},
        {"task": "Plan weekend activities with kids", "expected": ["personal", "family"]},
        {"task": "Research vacation destinations", "expected": ["personal"]}
    ],
    "weekend": [
        {"task": "Clean garage and organize tools", "expected": ["home"]},
        {"task": "Fix leaky faucet in kitchen", "expected": ["home"]},
        {"task": "Mow lawn and trim hedges", "expected": ["home"]},
        {"task": "Organize family photos", "expected": ["home", "family"]},
        {"task": "Plan family barbecue", "expected": ["family", "personal"]},
        {"task": "Take kids to soccer practice", "expected": ["family"]},
        {"task": "Visit farmers market", "expected": ["personal"]},
        {"task": "Wash and wax car", "expected": ["home"]},
        {"task": "Grocery shopping for week", "expected": ["home", "personal"]},
        {"task": "Deep clean bathroom", "expected": ["home"]}
    ],
    "evening": [
        {"task": "Pay monthly utility bills", "expected": ["admin", "personal"]},
        {"task": "Review credit card statements", "expected": ["admin", "personal"]},
        {"task": "Help kids with homework", "expected": ["family", "personal"]},
        {"task": "Prepare clothes for tomorrow", "expected": ["personal"]},
        {"task": "Check school calendar for events", "expected": ["family", "personal"]},
        {"task": "Order groceries for delivery", "expected": ["personal", "home"]},
        {"task": "Write in journal", "expected": ["personal"]},
        {"task": "Plan tomorrow's meetings", "expected": ["personal", "admin"]},
        {"task": "Set up coffee maker for morning", "expected": ["personal", "home"]},
        {"task": "Review family budget", "expected": ["admin", "personal", "family"]}
    ]
}

# Reasoning levels to test
REASONING_LEVELS = ["minimal", "light", "deep"]


class AccuracyValidator:
    """Validates TaskSense accuracy across different configurations"""
    
    def __init__(self):
        self.results = defaultdict(lambda: defaultdict(list))
        self.task_sense = TaskSense()
        
    def calculate_accuracy(self, predicted_labels: List[str], expected_labels: List[str]) -> float:
        """Calculate accuracy as intersection over union (Jaccard index)"""
        predicted_set = set(predicted_labels)
        expected_set = set(expected_labels)
        
        if not expected_set:
            return 1.0 if not predicted_set else 0.0
        
        intersection = predicted_set & expected_set
        union = predicted_set | expected_set
        
        return len(intersection) / len(union) if union else 0.0
    
    def test_mode_accuracy(self, mode: str, reasoning_level: str = "light") -> Tuple[float, List[Dict]]:
        """Test accuracy for a specific mode and reasoning level"""
        if mode not in TEST_DATASET:
            return 0.0, []
        
        test_cases = TEST_DATASET[mode]
        results = []
        total_accuracy = 0.0
        
        # Update TaskSense config for this test
        self.task_sense.config["default_mode"] = mode
        self.task_sense.config["reasoning_level"] = reasoning_level
        
        for test_case in test_cases:
            task_content = test_case["task"]
            expected_labels = test_case["expected"]
            
            try:
                # Get TaskSense prediction
                result = self.task_sense.label(task_content, mode=mode, dry_run=False)
                predicted_labels = result.get("labels", [])
                
                # Calculate accuracy
                accuracy = self.calculate_accuracy(predicted_labels, expected_labels)
                total_accuracy += accuracy
                
                # Store result
                test_result = {
                    "task": task_content,
                    "expected": expected_labels,
                    "predicted": predicted_labels,
                    "accuracy": accuracy,
                    "explanation": result.get("explanation", ""),
                    "confidence": result.get("confidence", 0.0)
                }
                results.append(test_result)
                
            except Exception as e:
                # Handle errors gracefully
                test_result = {
                    "task": task_content,
                    "expected": expected_labels,
                    "predicted": [],
                    "accuracy": 0.0,
                    "error": str(e),
                    "explanation": "",
                    "confidence": 0.0
                }
                results.append(test_result)
        
        average_accuracy = total_accuracy / len(test_cases) if test_cases else 0.0
        return average_accuracy, results
    
    def run_comprehensive_validation(self) -> Dict[str, Dict[str, float]]:
        """Run comprehensive validation across all modes and reasoning levels"""
        print("=" * 60)
        print("TASKSENSE ACCURACY VALIDATION")
        print("=" * 60)
        
        all_results = {}
        
        for mode in TEST_DATASET.keys():
            all_results[mode] = {}
            
            print(f"\nTesting mode: {mode.upper()}")
            print("-" * 40)
            
            for reasoning_level in REASONING_LEVELS:
                accuracy, detailed_results = self.test_mode_accuracy(mode, reasoning_level)
                all_results[mode][reasoning_level] = accuracy
                
                # Store detailed results for reporting
                self.results[mode][reasoning_level] = detailed_results
                
                status = "✅ PASS" if accuracy >= 0.8 else "❌ FAIL"
                print(f"  {reasoning_level.ljust(10)}: {accuracy:.2%} {status}")
        
        return all_results
    
    def generate_detailed_report(self) -> str:
        """Generate a detailed accuracy report"""
        report = []
        report.append("DETAILED ACCURACY REPORT")
        report.append("=" * 60)
        
        for mode in self.results:
            report.append(f"\n{mode.upper()} MODE")
            report.append("-" * 30)
            
            for reasoning_level in self.results[mode]:
                report.append(f"\n{reasoning_level.upper()} REASONING:")
                results = self.results[mode][reasoning_level]
                
                # Calculate statistics
                accuracies = [r["accuracy"] for r in results]
                avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
                pass_count = sum(1 for a in accuracies if a >= 0.8)
                
                report.append(f"  Average accuracy: {avg_accuracy:.2%}")
                report.append(f"  Tasks passing (≥80%): {pass_count}/{len(results)}")
                report.append(f"  Pass rate: {pass_count/len(results):.2%}")
                
                # Show failed tasks
                failed_tasks = [r for r in results if r["accuracy"] < 0.8]
                if failed_tasks:
                    report.append(f"  Failed tasks:")
                    for task in failed_tasks[:3]:  # Show first 3 failures
                        report.append(f"    - '{task['task']}' (accuracy: {task['accuracy']:.2%})")
                        report.append(f"      Expected: {task['expected']}")
                        report.append(f"      Predicted: {task['predicted']}")
                
                report.append("")
        
        return "\n".join(report)
    
    def calculate_overall_performance(self, results: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate overall performance metrics"""
        all_accuracies = []
        mode_averages = {}
        
        for mode in results:
            mode_accuracies = list(results[mode].values())
            mode_average = sum(mode_accuracies) / len(mode_accuracies)
            mode_averages[mode] = mode_average
            all_accuracies.extend(mode_accuracies)
        
        overall_average = sum(all_accuracies) / len(all_accuracies)
        
        return {
            "overall_average": overall_average,
            "mode_averages": mode_averages,
            "passing_configurations": sum(1 for a in all_accuracies if a >= 0.8),
            "total_configurations": len(all_accuracies)
        }


def main():
    """Main function to run accuracy validation"""
    validator = AccuracyValidator()
    
    # Run comprehensive validation
    results = validator.run_comprehensive_validation()
    
    # Calculate overall performance
    performance = validator.calculate_overall_performance(results)
    
    # Print summary
    print("\n" + "=" * 60)
    print("OVERALL PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Overall average accuracy: {performance['overall_average']:.2%}")
    print(f"Configurations passing (≥80%): {performance['passing_configurations']}/{performance['total_configurations']}")
    print(f"Overall pass rate: {performance['passing_configurations']/performance['total_configurations']:.2%}")
    
    print("\nMode-specific averages:")
    for mode, avg in performance["mode_averages"].items():
        status = "✅ PASS" if avg >= 0.8 else "❌ FAIL"
        print(f"  {mode.ljust(10)}: {avg:.2%} {status}")
    
    # Check if overall target is met
    target_met = performance["overall_average"] >= 0.8
    print(f"\n🎯 Target (≥80% accuracy): {'✅ MET' if target_met else '❌ NOT MET'}")
    
    # Generate detailed report
    detailed_report = validator.generate_detailed_report()
    
    # Save report to file
    with open("accuracy_validation_report.txt", "w") as f:
        f.write(detailed_report)
    
    print(f"\nDetailed report saved to: accuracy_validation_report.txt")
    
    return target_met


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)