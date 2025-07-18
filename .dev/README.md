# 🛠️ Development Resources

This `.dev/` directory contains internal development files, testing resources, and contributor documentation for the Todoist AI Assistant project.

> **📝 Note for End Users:** If you're just using the Todoist AI Assistant, you can safely ignore this folder. All user-facing documentation and configuration examples are in the main repository root.

---

## 📁 Directory Contents

| Category | File/Directory | Description |
|----------|----------------|-------------|
| **Project Planning** | `TODO.md` | Development roadmap, task prioritization, and feature planning |
| **Documentation** | `docs/GPT_RERANKING.md` | Technical documentation for GPT-enhanced ranking features |
| **Test Runners** | `run_tests.py` | Main test runner for all test suites |
| | `run_phase2_tests.py` | Legacy test runner for Phase 2 regression tests |
| **Individual Tests** | `test_tasksense.py` | TaskSense AI engine unit tests |
| | `test_accuracy_validation.py` | Accuracy validation tests for AI labeling |
| | `test_phase2_regression.py` | Regression tests for Phase 2 features |
| | `test_pipeline_integration.py` | Integration tests for the labeling pipeline |
| **Test Framework** | `tests/` | Organized test suite with unit, integration, and fixtures |
| | `tests/unit/` | Unit tests for individual components |
| | `tests/integration/` | Integration tests for component interactions |
| | `tests/fixtures/` | Test data and mock responses |
| **Development Scripts** | `scripts/populate_test_tasks.py` | Script to populate test data in Todoist |

---

## 🧪 Testing Guide

### Running Tests

**All Tests:**
```bash
python .dev/run_tests.py
```

**Specific Test Categories:**
```bash
# TaskSense AI engine tests
python .dev/test_tasksense.py

# Pipeline integration tests  
python .dev/test_pipeline_integration.py

# Accuracy validation tests
python .dev/test_accuracy_validation.py

# GPT reranking tests
python .dev/tests/unit/test_gpt_reranking.py
```

**Using pytest (if available):**
```bash
# Run all tests
pytest .dev/tests/

# Run specific test modules
pytest .dev/tests/unit/
pytest .dev/tests/integration/
```

### Test Environment Setup

1. **Install test dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up test environment variables:**
   ```bash
   export TODOIST_TOKEN="your_test_token"
   export OPENAI_API_KEY="your_openai_key"  # Optional, for GPT tests
   export GPT_MOCK_MODE=1  # Use mock responses for testing
   ```

3. **Configure test project:**
   - Use a dedicated Todoist project for testing
   - Set `TODOIST_PROJECT_ID` in your test environment
   - Run `python .dev/scripts/populate_test_tasks.py` to create test data

### Mock Testing

For testing without API calls:
```bash
export GPT_MOCK_MODE=1
python .dev/test_tasksense.py --mock
```

---

## 📚 Development Documentation

### Core Architecture Documents

- **`docs/GPT_RERANKING.md`** - Comprehensive guide to GPT-enhanced ranking system
  - Configuration options
  - Usage examples
  - Troubleshooting guide
  - Performance considerations

### Development Planning

- **`TODO.md`** - Active development roadmap
  - Prioritized task list
  - Feature roadmap (Steps 3-5)
  - Architecture improvements
  - Testing enhancements

---

## 🔧 Development Scripts

### Test Data Management

**Populate Test Tasks:**
```bash
python .dev/scripts/populate_test_tasks.py
```
- Creates sample tasks in your test Todoist project
- Includes various task types for comprehensive testing
- Useful for testing labeling and ranking functionality

### Running Development Builds

**With Development Flags:**
```bash
# Enable verbose testing mode
python main.py --debug --test --dry

# Test with mock responses
GPT_MOCK_MODE=1 python main.py --test
```

---

## 🏗️ Contributing Guidelines

### Before Making Changes

1. **Run the test suite:**
   ```bash
   python .dev/run_tests.py
   ```

2. **Check your changes don't break existing functionality:**
   ```bash
   python .dev/test_pipeline_integration.py
   ```

### Adding New Tests

1. **Unit tests** → `tests/unit/test_[component].py`
2. **Integration tests** → `tests/integration/test_[feature].py`
3. **Test fixtures** → `tests/fixtures/[data].json`

### Test Naming Conventions

- Test files: `test_[component_name].py`
- Test functions: `test_[specific_functionality]()`
- Test classes: `Test[ComponentName]`

### Mock Data Guidelines

- Use realistic task examples in test fixtures
- Include edge cases (empty tasks, special characters, long titles)
- Mock GPT responses should reflect actual API response format

---

## 🚀 Release Testing

Before any release:

1. **Full test suite:**
   ```bash
   python .dev/run_tests.py
   ```

2. **Integration validation:**
   ```bash
   python .dev/test_pipeline_integration.py
   ```

3. **Accuracy validation:**
   ```bash
   python .dev/test_accuracy_validation.py
   ```

4. **Manual smoke tests:**
   - Test with real Todoist data (small subset)
   - Verify GPT integration works
   - Check section routing functionality

---

## 📝 Development Notes

- **Test Coverage:** Aim for >80% coverage on core functionality
- **Performance:** Monitor API call efficiency in integration tests
- **Security:** Never commit real API tokens or personal data
- **Documentation:** Update relevant docs when adding new features

---

*For questions about development setup or testing, refer to the main project documentation or open an issue.*