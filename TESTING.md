# TodoistProcessor Testing Guide

This document provides comprehensive guidance for testing the Todoist AI Assistant using the dedicated **TodoistProcessor** testing project.

## 🎯 Overview

The TodoistProcessor project serves as a safe, isolated testing environment for validating:
- **Labeling Pipeline**: TaskSense AI, rule-based labeling, and domain detection
- **Ranking Engine**: Priority-based task scoring and Today list generation  
- **Section Routing**: Automatic task organization into appropriate sections
- **Edge Cases**: Error handling, unicode support, and boundary conditions

## 🔧 Setup

### Prerequisites
1. **Environment Configuration**:
   ```bash
   # In your .env file
   TODOIST_API_TOKEN=your_token_here
   PROJECT_NAMES=TodoistProcessor
   ```

2. **Project Safety**: 
   - TodoistProcessor project ID: `2355576487`
   - Isolated from production projects
   - Safe to clear and repopulate

### Required Sections
The testing project uses these sections:
- **Work**: Work-related tasks, meetings, bugs
- **Personal**: Personal tasks, admin, health
- **Today**: Daily focus tasks (protected from moves)
- **Links**: URL-containing tasks  
- **Follow-ups**: Follow-up and reminder tasks

## 📋 Test Task Population

### Automated Population
Use the provided script to populate comprehensive test tasks:

```bash
# Basic population
python scripts/populate_test_tasks.py

# Clear existing tasks first
python scripts/populate_test_tasks.py --clear-first

# Dry run to see what would be created
python scripts/populate_test_tasks.py --dry-run

# Verbose output
python scripts/populate_test_tasks.py --verbose
```

### Manual Population
For quick testing, create specific tasks via API:

```python
import requests

headers = {'Authorization': 'Bearer YOUR_TOKEN'}
task_data = {
    'content': 'Test task content',
    'project_id': 2355576487,
    'priority': 2,
    'due_string': 'today'
}

response = requests.post(
    'https://api.todoist.com/rest/v2/tasks',
    headers=headers, 
    json=task_data
)
```

## 🧪 Test Categories

### 1. Labeling Tests
**Purpose**: Validate label detection and application

**Test Tasks**:
- Meeting tasks → `meeting` label
- Bug tasks → `bug` label  
- Work tasks → `work` label
- Personal tasks → `personal` label
- Home tasks → `home` label
- Reading tasks → `reading` label
- URL tasks → `link` + domain labels

**Expected Behavior**:
```
Task 123456 | TaskSense: #meeting (v1.0, light) | Confidence: 0.85
Task 123456 | RULE_MATCH: meeting → #meeting (priority: 5)
Task 123456 | URL_DOMAIN: github.com → #github
```

### 2. Ranking Tests  
**Purpose**: Validate priority scoring and Today list generation

**Test Tasks**:
- High priority overdue tasks (score: ~1.0)
- Medium priority due today (score: ~0.7)
- Low priority future tasks (score: ~0.3)
- Tasks with preferred labels for mode
- Old tasks (slight age bonus)

**Commands**:
```bash
# Test ranking
python main.py --generate-today --project TodoistProcessor --dry-run

# Test different modes
python main.py --generate-today --mode=work --limit=5 --dry-run
python main.py --generate-today --mode=personal --limit=3 --dry-run
```

**Expected Behavior**:
```
RANK_CANDIDATES: Task 123456 → Score: 0.82 | Reason: High priority and overdue
RANK_TOP_1: Task 123456 (score: 0.82) - high priority (p1); overdue
TODAY_MOVE: Task 123456 moved to Today section
```

### 3. Section Routing Tests
**Purpose**: Validate automatic task organization

**Test Tasks**:
- Meeting tasks → Work section
- Personal tasks → Personal section  
- Link tasks → Links section
- Follow-up tasks → Follow-ups section
- Tasks already in correct sections (should skip)

**Expected Behavior**:
```
Task 123456 | MOVED_TO_SECTION: Work | Rule: meeting
Task 123456 | SECTION_SKIP: already in target section Work
Task 123456 | TODAY_SECTION_PROTECTED: in Today section, skipping move
```

### 4. Edge Case Tests
**Purpose**: Validate error handling and boundary conditions

**Test Tasks**:
- No metadata tasks → `NO_LABELS_FOUND`
- Priority 4 tasks → lowest ranking scores
- Tasks in Today section → protected from moves
- Long titles → proper truncation
- Unicode content → proper handling
- Duplicate tasks → idempotent processing

**Expected Behavior**:
```
Task 123456 | NO_LABELS_FOUND: no labels identified
Task 123456 | SKIP_EXISTING_LABELS: already has {'personal'}
Task 123456 | TODAY_SECTION_PROTECTED: Task in Today section, skipping move
```

## 🔍 Running Tests

### Basic Pipeline Testing
```bash
# Test labeling pipeline
python main.py --project TodoistProcessor --dry-run --verbose

# Test with full scan (ignore timestamps)
python main.py --project TodoistProcessor --dry-run --full-scan

# Test ranking pipeline  
python main.py --generate-today --project TodoistProcessor --dry-run --verbose
```

### Advanced Testing
```bash
# Test specific modes
python main.py --project TodoistProcessor --mode=work --dry-run
python main.py --project TodoistProcessor --mode=personal --dry-run

# Test with TaskSense mock mode
python main.py --project TodoistProcessor --tasksense-mock --dry-run

# Test section routing fixes
python main.py --project TodoistProcessor --fix-sections --dry-run
```

### Override to Production
```bash
# Test against production projects (use carefully)
python main.py --project "Inbox,Work Project" --dry-run
python main.py --project "Personal Tasks" --dry-run
```

## 📊 Expected Log Outputs

### Successful Task Processing
```
📋 Processing task 1/52: Schedule quarterly review meeting...
Task 9355969946 | TaskSense: #meeting (v1.0, light) | Confidence: 0.85
Task 9355969946 | RULE_MATCH: meeting → #meeting (priority: 5)
🔍 DRY RUN - Would update task:
   Task ID: 9355969946
   Current: Schedule quarterly review meeting with Sarah
   Labels: [] → ['meeting']
📂 Would move task to section: Work (priority: 5)
```

### Skipped Task Processing
```
Task 9355988629 | EXISTING_LABELS: {'personal'} | Content: Work task incorrectly placed...
Task 9355988629 | SKIP_EXISTING_LABELS: already has {'personal'} | New labels: set()
Task 9355988629 | SKIP_TIMESTAMP: created before last run | Content: Old task content...
Task 9355988629 | SECTION_SKIP: already in target section Personal | Content: Personal task...
```

### Today Section Protection
```
Task 9355988668 | TODAY_SECTION_PROTECTED: Task in Today section, skipping move to Personal
Task 9355988668 | Content: 'Task in Today section should not be moved' | Action: TODAY_SECTION_PROTECTED
```

### Ranking Output
```
RANK_FILTER: 42 rankable tasks from 52 total (excluded: 8 completed, 2 in Today)
RANK_CANDIDATES: Task 9355969979 → Score: 0.82 | Reason: High priority and overdue
RANK_TOP_1: Task 9355969979 (score: 0.82) - high priority (p1); overdue
TODAY_MOVE: Task 9355969979 moved to Today section
```

## 🎯 Test Validation

### Labeling Pipeline Success
- [ ] TaskSense suggestions with confidence scores
- [ ] Rule-based matches with priorities
- [ ] Domain detection for URLs
- [ ] Existing labels properly detected and skipped
- [ ] No labels found for minimal tasks

### Ranking Pipeline Success
- [ ] High priority overdue tasks score highest
- [ ] Due date proximity affects scoring
- [ ] Mode-specific label preferences work
- [ ] Age bonus applied to older tasks
- [ ] Proper filtering excludes completed/Today tasks

### Section Routing Success
- [ ] Tasks moved to appropriate sections
- [ ] Today section tasks protected from moves
- [ ] Tasks already in correct sections skipped
- [ ] Priority-based section selection works
- [ ] Section creation when missing

### Edge Case Handling
- [ ] Unicode content processes correctly
- [ ] Long titles truncate properly
- [ ] Duplicate tasks process idempotently
- [ ] No metadata tasks handle gracefully
- [ ] Low priority tasks rank appropriately

## 🔧 Troubleshooting

### Common Issues

**No tasks processed**:
```bash
# Check timestamp filter
python main.py --project TodoistProcessor --full-scan --dry-run

# Check project configuration
echo $PROJECT_NAMES
```

**OpenAI API errors**:
```bash
# Use mock mode to bypass API
python main.py --project TodoistProcessor --tasksense-mock --dry-run

# Check API key
echo $OPENAI_API_KEY
```

**Section routing failures**:
```bash
# Fix section assignments
python main.py --project TodoistProcessor --fix-sections --dry-run
```

### Log Analysis
Check detailed logs in `task_log.txt`:
```bash
# View recent processing
tail -50 task_log.txt

# Search for specific patterns
grep "SKIP_" task_log.txt
grep "ERROR" task_log.txt
grep "Task 9355969946" task_log.txt
```

## 📁 File Structure

```
todoist-ai-assistant/
├── scripts/
│   └── populate_test_tasks.py      # Test population script
├── TESTING.md                      # This documentation
├── task_log.txt                    # Detailed processing logs
├── .env                            # Environment configuration
├── task_sense_config.json          # TaskSense configuration
├── rules.json                      # Labeling rules
├── ranking_config.json             # Ranking configuration
└── main.py                         # Main application
```

## 🚀 Best Practices

1. **Always use dry-run first** to preview changes
2. **Use verbose mode** for detailed logging during testing
3. **Check task_log.txt** for detailed processing information
4. **Test with full-scan** to ignore timestamp filters
5. **Use --clear-first** when repopulating to start fresh
6. **Verify PROJECT_NAMES** is set to TodoistProcessor
7. **Never commit** personal config files (task_sense_config.json, rules.json)
8. **Use production overrides** sparingly and with caution

---

*This testing guide ensures comprehensive validation of the Todoist AI Assistant while maintaining safety and isolation from production data.*