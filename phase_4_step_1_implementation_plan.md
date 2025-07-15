# 📄 Phase 4 Step 1: Efficient Core Ranking Engine (v4.0)
## Implementation Plan

---

## 🎯 **Objective**
Extend the TaskSense AI Engine with a `.rank()` method that prioritizes tasks from the backlog into a focused Today list, using an efficient, rule-based scoring algorithm and native Todoist filtering (optional).

**Target CLI Commands:**
```bash
# Generate today's task list
python main.py --generate-today --mode=work --limit=3

# Preview rankings without making changes (dry-run support)
python main.py --generate-today --mode=work --limit=3 --dry-run
```

---

## 📋 **Implementation Task Breakdown**

### 🗂️ **Group 1: Configuration Foundation**
**Priority: Critical (Build First)**

#### **Task 1.1: Create ranking_config.json**
- [ ] Design complete configuration schema
- [ ] Implement default scoring weights
- [ ] **Add fallback weights** for tasks with missing criteria (no due date, no priority, no preferred labels)
- [ ] Add mode-specific settings (work, personal, weekend, evening)
- [ ] Define Todoist filter queries per mode
- [ ] Configure Today section management settings
- [ ] Add validation schema

**Config Schema:**
```json
{
  "default_limit": 3,
  "scoring_weights": {
    "priority": 0.4,
    "due_date": 0.3,
    "age": 0.1,
    "label_preference": 0.2
  },
  "fallback_weights": {
    "no_priority": 0.3,
    "no_due_date": 0.2,
    "no_preferred_labels": 0.1
  },
  "mode_settings": {
    "work": {
      "filters": ["overdue & !@today", "(p1 | p2) & 7 days & !@today"],
      "preferred_labels": ["work", "meeting", "urgent"],
      "excluded_labels": ["personal"]
    }
  },
  "sections": {
    "today_section": "Today",
    "create_if_missing": true
  }
}
```

**Files:**
- `ranking_config.json` (new)
- `ranking_config.example.json` (new)

**Estimated Time:** 2-3 hours

#### **Task 1.2: Configuration Loading Logic**
- [ ] Add config loading to TaskSense `__init__`
- [ ] Implement config validation
- [ ] Add fallback to default config if file missing
- [ ] Merge with existing task_sense_config.json patterns
- [ ] Error handling for malformed config

**Files:**
- `task_sense.py` (modify `_load_config` method)

**Estimated Time:** 1-2 hours

---

### 🧮 **Group 2: Core Scoring Algorithm**
**Priority: Critical (Build Second)**

#### **Task 2.1: Scoring Helper Functions**
- [ ] `calculate_priority_score(task)` - Handle p1, p2, p3, p4 scoring
- [ ] `calculate_due_date_score(task)` - Overdue, today, tomorrow, week scoring
- [ ] `calculate_age_score(task)` - Task creation age scoring
- [ ] `calculate_label_preference_score(task, mode, config)` - Mode-aware label scoring
- [ ] Unit tests for each scoring function

**Files:**
- `task_sense.py` (new methods)

**Estimated Time:** 3-4 hours

#### **Task 2.2: Composite Scoring Engine**
- [ ] `calculate_composite_score(task, mode, config)` - Combine all scores
- [ ] Score component tracking for explanations
- [ ] Score normalization (0.0-1.0 range)
- [ ] **Fallback weight handling** for tasks with missing criteria (no due date, no priority, no preferred labels)
- [ ] Explanation generation logic
- [ ] Edge case handling (missing due dates, priorities, labels)

**Files:**
- `task_sense.py` (new methods)

**Estimated Time:** 2-3 hours

---

### 🎯 **Group 3: TaskSense.rank() Method**
**Priority: Critical (Build Third)**

#### **Task 3.1: Core rank() Method**
- [ ] Implement method signature: `rank(tasks, mode=None, limit=3, config_override=None)`
- [ ] **Task filtering (backlog only: `section_id == None`)** - explicitly filter to only consider unorganized tasks
- [ ] Mode detection/override logic
- [ ] Config override handling
- [ ] Score calculation for all tasks with fallback weight handling
- [ ] Sorting by score (descending)
- [ ] Limit application
- [ ] Return format with task, score, explanation, components

**Files:**
- `task_sense.py` (new `.rank()` method)

**Estimated Time:** 2-3 hours

#### **Task 3.2: Todoist Filter Optimization**
- [ ] Filter query builder from config
- [ ] Pre-filtering with Todoist filters (if available)
- [ ] Fallback to full backlog if filters return empty
- [ ] Filter performance logging
- [ ] Error handling for invalid filter syntax

**Files:**
- `task_sense.py` (extend `.rank()` method)
- `main.py` (potentially new Todoist filter API calls)

**Estimated Time:** 2-3 hours

---

### 🖥️ **Group 4: CLI Integration**
**Priority: High (Build Fourth)**

#### **Task 4.1: CLI Argument Parsing**
- [ ] Add `--generate-today` flag
- [ ] Add `--mode` override flag
- [ ] Add `--limit` override flag
- [ ] **Ensure `--dry-run` support** with `--generate-today` for ranking preview
- [ ] Integrate with existing CLI parser in `main.py`
- [ ] Help text and examples
- [ ] Validation of argument combinations

**Files:**
- `main.py` (modify argument parser)

**Estimated Time:** 1-2 hours

#### **Task 4.2: CLI Processing Logic**
- [ ] Detect `--generate-today` flag
- [ ] Load ranking configuration
- [ ] Fetch backlog tasks from Todoist API
- [ ] Call TaskSense.rank() with appropriate parameters
- [ ] Handle dry-run mode for ranking
- [ ] Verbose output integration
- [ ] Error handling and user feedback

**Files:**
- `main.py` (new processing logic)

**Estimated Time:** 2-3 hours

---

### 📁 **Group 5: Today Section Management**
**Priority: High (Build Fifth)**

#### **Task 5.1: Section Management Functions**
- [ ] `ensure_today_section_exists(project_id, config)` - Create if missing
- [ ] `move_tasks_to_today_section(ranked_tasks, project_id, config)` - Bulk move
- [ ] `apply_today_labels(ranked_tasks, config)` - Apply @today labels
- [ ] Integration with existing section management utilities
- [ ] Dry-run support for section operations

**Files:**
- `main.py` (new functions, integrate with existing section management)

**Estimated Time:** 2-3 hours

#### **Task 5.2: Integration with Ranking Pipeline**
- [ ] Call section management after ranking
- [ ] Batch task updates for performance
- [ ] Error handling for failed moves
- [ ] Logging for all section operations
- [ ] Integration with existing bulk-mode settings

**Files:**
- `main.py` (integrate with ranking processing)

**Estimated Time:** 1-2 hours

---

### 📊 **Group 6: Logging & Observability**
**Priority: Medium (Build Sixth)**

#### **Task 6.1: Ranking Logs**
- [ ] `RANK_CANDIDATES` log format implementation
- [ ] Score and reason logging for each task
- [ ] Performance timing logs
- [ ] Config loading and validation logs
- [ ] Integration with existing logging infrastructure

**Example Log Output:**
```yaml
RANK_CANDIDATES: Task 12345 → Score: 0.82 | Reason: High priority and overdue
RANK_CANDIDATES: Task 67890 → Score: 0.74 | Reason: Preferred label: work
TODAY_MOVE: Task 12345 moved to Today section
```

**Files:**
- `task_sense.py` (ranking logs)
- `main.py` (section movement logs)

**Estimated Time:** 1-2 hours

---

### 🧪 **Group 7: Testing & Validation**
**Priority: High (Build Continuously)**

#### **Task 7.1: Unit Tests**
- [ ] Scoring function tests with known inputs/outputs
- [ ] TaskSense.rank() method tests with mock tasks
- [ ] Configuration loading and validation tests
- [ ] Edge case testing (empty task lists, missing fields)
- [ ] Mode-specific scoring tests

**Test Cases:**
```python
# Priority-only tie breakers
test_tasks_priority = [
    {'priority': 1, 'due': None, 'labels': []},  # Should rank highest
    {'priority': 2, 'due': None, 'labels': []},
    {'priority': 4, 'due': None, 'labels': []}
]

# Due-date-only tie breakers  
test_tasks_due_date = [
    {'priority': 4, 'due': {'date': 'today'}, 'labels': []},     # Should rank highest
    {'priority': 4, 'due': {'date': 'tomorrow'}, 'labels': []},
    {'priority': 4, 'due': None, 'labels': []}
]

# Label preference influencing ranking
test_tasks_labels = [
    {'priority': 4, 'due': None, 'labels': ['work']},      # Should rank highest in work mode
    {'priority': 4, 'due': None, 'labels': ['personal']},
    {'priority': 4, 'due': None, 'labels': []}
]
```

**Files:**
- `test_ranking.py` (new)
- `test_tasksense_ranking.py` (new)

**Estimated Time:** 4-5 hours

#### **Task 7.2: Integration Tests**
- [ ] End-to-end CLI testing
- [ ] Today section creation and task movement
- [ ] Configuration file loading
- [ ] Mode detection and override testing
- [ ] Performance testing with large task lists

**Files:**
- `test_ranking_integration.py` (new)

**Estimated Time:** 2-3 hours

---

## 🚀 **Suggested Implementation Order**

### **Phase A: Foundation (Days 1-2)**
1. **Task 1.1**: Create ranking_config.json schema
2. **Task 1.2**: Configuration loading logic
3. **Task 7.1**: Basic unit test framework setup
4. **Milestone**: Configuration system working and tested

### **Phase B: Core Algorithm (Days 3-4)**
1. **Task 2.1**: Individual scoring functions
2. **Task 2.2**: Composite scoring engine
3. **Task 3.1**: Core rank() method implementation
4. **Task 7.1**: Scoring algorithm unit tests
5. **Milestone**: TaskSense.rank() working with mock data

### **Phase C: API Integration (Days 5-6)**
1. **Task 3.2**: Todoist filter optimization
2. **Task 4.1**: CLI argument parsing
3. **Task 4.2**: CLI processing logic
4. **Task 6.1**: Logging implementation
5. **Milestone**: CLI command working end-to-end

### **Phase D: Section Management (Days 7-8)**
1. **Task 5.1**: Section management functions
2. **Task 5.2**: Integration with ranking pipeline
3. **Task 7.2**: Integration testing
4. **Milestone**: Complete ranking and section routing pipeline

### **Phase E: Polish & Testing (Day 9)**
1. **Task 7.1**: Complete unit test coverage
2. **Task 7.2**: Complete integration tests
3. Performance optimization
4. Documentation updates
5. **Milestone**: Production-ready implementation

---

## ⚠️ **Potential Pitfalls & Testing Focus Areas**

### **Configuration Pitfalls**
- **Issue**: Missing or malformed ranking_config.json
- **Testing Focus**: Graceful degradation with sensible defaults
- **Solution**: Comprehensive validation and fallback logic

### **Scoring Algorithm Pitfalls**
- **Issue**: Score normalization and edge cases
- **Testing Focus**: Tasks with missing priority, due dates, or labels
- **Solution**: Defensive scoring with default values

### **Todoist API Pitfalls**
- **Issue**: Filter syntax errors or API rate limits
- **Testing Focus**: Filter query validation and fallback behavior
- **Solution**: Robust error handling and fallback to unfiltered queries

### **Section Management Pitfalls**
- **Issue**: Today section creation or task movement failures
- **Testing Focus**: Permission errors, rate limits, concurrent updates
- **Solution**: Batch operations with error handling and retry logic

### **Performance Pitfalls**
- **Issue**: Large task lists causing slow ranking
- **Testing Focus**: Performance with 1000+ tasks
- **Solution**: Efficient filtering and scoring algorithms

---

## 📝 **Recommended Git Commit Granularity**

### **Configuration Commits**
```bash
git commit -m "Add ranking_config.json schema and loading logic

- Create ranking_config.json with scoring weights and mode settings
- Add configuration loading to TaskSense.__init__
- Implement validation and fallback logic
- Add ranking_config.example.json template"
```

### **Scoring Algorithm Commits**
```bash
git commit -m "Implement core task scoring algorithm

- Add priority, due date, age, and label preference scoring functions
- Implement composite scoring with configurable weights
- Add score explanation generation
- Include unit tests for all scoring functions"
```

### **TaskSense.rank() Method Commit**
```bash
git commit -m "Add TaskSense.rank() method for task prioritization

- Implement rank() method with signature: rank(tasks, mode, limit, config_override)
- Add backlog filtering (section_id == None)
- Integrate scoring algorithm with task ranking
- Return structured results with scores and explanations"
```

### **CLI Integration Commit**
```bash
git commit -m "Add CLI support for task ranking and today list generation

- Add --generate-today, --mode, --limit CLI flags
- Implement ranking processing pipeline in main.py
- Add integration with existing dry-run and verbose modes
- Support for ranking configuration override"
```

### **Section Management Commit**
```bash
git commit -m "Implement Today section management for ranked tasks

- Add automatic Today section creation if missing
- Implement bulk task movement to Today section
- Add @today label application for selected tasks
- Integrate with existing section routing infrastructure"
```

### **Testing & Polish Commit**
```bash
git commit -m "Add comprehensive testing and logging for task ranking

- Complete unit test coverage for scoring algorithms
- Add integration tests for end-to-end ranking pipeline
- Implement detailed logging for ranking decisions
- Add performance optimizations and error handling"
```

---

## ✅ **Success Criteria Checklist**

### **Functional Requirements**
- [ ] Tasks in backlog are prioritized using configurable scoring
- [ ] Top N tasks are moved to Today section
- [ ] @today labels are applied to selected tasks
- [ ] CLI command works: `python main.py --generate-today --mode=work --limit=3`
- [ ] Configurable weights, limits, and modes through ranking_config.json
- [ ] Todoist filter optimization (optional, with fallback)

### **Quality Requirements**
- [ ] Logs show scores and reasons for ranking decisions
- [ ] Backward-compatible with existing labeling & section routing
- [ ] Graceful error handling for missing data or API failures
- [ ] Performance acceptable with large task lists (1000+ tasks)
- [ ] Comprehensive test coverage (>80% for new code)

### **User Experience Requirements**
- [ ] Clear, actionable log output
- [ ] Intuitive CLI interface
- [ ] Works out-of-box with sensible defaults
- [ ] Rich verbose output for debugging
- [ ] Dry-run support for safe testing

---

## 📚 **Implementation Resources**

### **Key Files to Reference**
- `task_sense.py` - Existing TaskSense class patterns
- `main.py` - CLI parsing and task processing patterns
- `rules.json` - Priority and section routing patterns
- `task_sense_config.json` - Configuration loading patterns

### **Existing Utilities to Leverage**
- `select_priority_section()` - Priority-based section selection
- `get_project_sections()` - Section management
- `route_task_to_section()` - Task movement utilities
- `log_task_action()` - Standardized logging

### **Testing Patterns to Follow**
- Mock TaskSense responses for unit tests
- Use existing test data patterns
- Follow existing assertion and logging patterns
- Integrate with existing test infrastructure

---

**🎯 This implementation plan provides a clear, step-by-step roadmap for building the Phase 4 Step 1 Efficient Core Ranking Engine while maintaining code quality, testability, and integration with your existing TaskSense architecture.**