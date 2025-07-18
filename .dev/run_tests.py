#!/usr/bin/env python3
"""
Test runner for Phase 4 Step 2 GPT-Enhanced Reranker tests.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py unit              # Run only unit tests
    python run_tests.py integration       # Run only integration tests
    python run_tests.py --verbose         # Run with verbose output
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def discover_tests(test_type=None, verbose=False):
    """
    Discover and run tests.
    
    Args:
        test_type: 'unit', 'integration', or None for all tests
        verbose: Enable verbose test output
    """
    test_dir = project_root / "tests"
    
    if test_type == 'unit':
        suite = unittest.TestLoader().discover(test_dir / "unit", pattern="test_*.py")
    elif test_type == 'integration':
        suite = unittest.TestLoader().discover(test_dir / "integration", pattern="test_*.py")
    else:
        # Discover all tests
        suite = unittest.TestSuite()
        suite.addTests(unittest.TestLoader().discover(test_dir / "unit", pattern="test_*.py"))
        suite.addTests(unittest.TestLoader().discover(test_dir / "integration", pattern="test_*.py"))
    
    # Configure test runner
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity, buffer=True)
    
    print(f"Running {test_type or 'all'} tests...")
    print(f"Test discovery path: {test_dir}")
    print("-" * 50)
    
    result = runner.run(suite)
    
    # Print summary
    print("-" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


def main():
    """Main test runner entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Phase 4 Step 2 GPT reranking tests")
    parser.add_argument("test_type", nargs="?", choices=["unit", "integration"], 
                        help="Type of tests to run (default: all)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Enable verbose test output")
    
    args = parser.parse_args()
    
    # Set environment variables for testing
    os.environ['GPT_MOCK_MODE'] = '1'  # Enable mock mode by default for tests
    
    try:
        success = discover_tests(args.test_type, args.verbose)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)
    finally:
        # Clean up environment
        if 'GPT_MOCK_MODE' in os.environ:
            del os.environ['GPT_MOCK_MODE']


if __name__ == "__main__":
    main()