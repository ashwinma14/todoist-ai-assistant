# TODO: Development Task List

**Priority Legend:** 🔴 Critical | 🟡 High | 🟢 Medium | 🔵 Low  
**Phase 4 Step 2 Prerequisites:** ⚠️ Required | ✅ Can Defer

---

## 📝 Updated to reflect Phase 4 Roadmap as of 2025-07-17

---

## 🔍 Additions from Phase 4 Step 2 Reflection

The following tasks were identified during comprehensive reflection on the GPT-Enhanced Reranker implementation to improve architecture, testing, and user experience.

---

## 🎯 Phase 4 Step 2 Prerequisites

### ⚠️ Critical for GPT-Enhanced Reranker

- [x] **Clean up temporary development files** 🔴 **(30 min)** ✅
  - Remove `Phase4_Implementation_Plan.md`, `TaskSense_Implementation_Plan.md`, `commit_tasksense.sh`, `sync_api_patch.txt`
  - Update `.gitignore` if needed
  - **Prerequisite:** Required for clean development environment

- [x] **Add GPT explanation logging framework** 🟡 **(2 hours)** ✅
  - Extend existing enhanced logging to capture GPT reasoning
  - Add explanation validation and confidence tracking
  - **Prerequisite:** Required for debugging GPT-enhanced ranking

---

## 🧪 Testing & Quality Assurance

### ✅ Can Defer (Parallel to Phase 4 Step 2)

- [ ] **Create comprehensive unit test suite** 🟡 **(8-12 hours)**
  - **Structure:** 
    ```
    tests/
    ├── unit/
    │   ├── test_task_sense.py
    │   ├── test_labeling_pipeline.py
    │   ├── test_ranking_engine.py
    │   └── test_section_manager.py
    ├── integration/
    │   ├── test_full_pipeline.py
    │   └── test_api_integration.py
    └── fixtures/
        ├── sample_tasks.json
        └── mock_responses.json
    ```
  - **Initial Test Cases:**
    - `test_task_sense.py`: Mock mode responses, confidence scoring, fallback handling
    - `test_labeling_pipeline.py`: Stage processing, label consolidation, existing label detection
    - `test_ranking_engine.py`: Composite scoring, mode-specific weights, edge cases
    - `test_section_manager.py`: Section routing, Today protection, priority selection
  - **Prerequisite:** Can defer - good for long-term maintenance

- [ ] **Add configuration validation** 🟢 **(4 hours)**
  - Create JSON schema validators for all config files
  - Add startup validation with helpful error messages
  - **Prerequisite:** Can defer - improves robustness

---

## 🏗️ Architecture Refactoring

### ✅ Can Defer (Refactor during Phase 4 Step 2)

- [ ] **Extract SectionManager class** 🟡 **(4-6 hours)**
  - **High-level Design:**
    ```python
    class SectionManager:
        def __init__(self, project_id: str, config: Dict):
            self.project_id = project_id
            self.config = config
            self.sections_cache = {}
        
        def get_or_create_section(self, name: str) -> str:
            """Get section ID, creating if needed"""
        
        def route_task_to_section(self, task: Dict, labels: Set[str]) -> Optional[str]:
            """Determine target section for task based on labels"""
        
        def is_today_protected(self, task: Dict) -> bool:
            """Check if task is in Today section and protected"""
        
        def get_priority_section(self, candidate_sections: List[Dict]) -> Optional[Dict]:
            """Select highest priority section from candidates"""
        
        def validate_section_move(self, task: Dict, target_section: str) -> bool:
            """Validate if task can be moved to target section"""
    ```
  - **Benefits:** Centralized section logic, easier testing, cleaner main.py
  - **Prerequisite:** Can defer - refactor during Step 2 development

- [ ] **Create logging utility module** 🟢 **(2 hours)**
  - Extract enhanced logging patterns into reusable functions
  - Standardize log message formatting
  - **Prerequisite:** Can defer - improves maintainability

- [ ] **Consolidate configuration management** 🟢 **(3 hours)**
  - Create unified config loader with clear hierarchy
  - Reduce duplication across modules
  - **Prerequisite:** Can defer - improves configuration consistency

---

## 🔧 Code Quality & Maintenance

### ✅ Can Defer (Ongoing improvements)

- [ ] **Extract URL processing module** 🟢 **(2 hours)**
  - Move URL extraction and domain labeling to separate module
  - Add comprehensive URL pattern tests
  - **Prerequisite:** Can defer - improves modularity

- [ ] **Improve error messaging** 🟢 **(2 hours)**
  - Make error messages more user-friendly
  - Reduce technical stack traces in normal operation
  - **Prerequisite:** Can defer - improves user experience

- [ ] **Add performance monitoring** 🔵 **(3 hours)**
  - Add timing metrics for TaskSense, GPT calls, API operations
  - Create performance dashboard/logging
  - **Prerequisite:** Can defer - useful for optimization

- [ ] **Function extraction in main.py** 🟢 **(2 hours)**
  - Break down large functions into smaller, focused units
  - Improve readability and testability
  - **Prerequisite:** Can defer - improves maintainability

---

## 📊 Documentation & Process

### ✅ Can Defer (Ongoing improvements)

- [ ] **Add API documentation** 🟢 **(2 hours)**
  - Document key functions and classes
  - Add docstring examples
  - **Prerequisite:** Can defer - improves developer experience

- [ ] **Create deployment guide** 🔵 **(1 hour)**
  - Document Render.com deployment process
  - Add troubleshooting section
  - **Prerequisite:** Can defer - useful for production deployment

- [ ] **Add contribution guidelines** 🔵 **(1 hour)**
  - Document development workflow
  - Add code style guidelines
  - **Prerequisite:** Can defer - useful for team development

---

## 🎯 Phase 4 Step 2 Development Tasks ✅ COMPLETE

### ✅ Completed Features

- [x] **Implement GPT-Enhanced Reranker** 🔴 **(6-8 hours)** ✅
  - Add GPT-based explanation generation for ranking decisions
  - Implement confidence-based reranking
  - Integrate with existing ranking pipeline

- [x] **Add ranking explanation system** 🟡 **(4 hours)** ✅
  - Create structured explanation output
  - Add explanation validation and scoring
  - Integrate with enhanced logging framework

- [x] **Validate with TodoistProcessor** 🟡 **(2 hours)** ✅
  - Test GPT explanations on edge cases
  - Verify explanation quality and consistency
  - Update TESTING.md with new scenarios

---

## 🚀 Phase 4 Execution Roadmap

### 🔴 Critical

#### 🪜 Step 3: Feedback & Learning System (v4.3)
🎯 **Objective:** Enable a basic feedback loop to validate & improve GPT-enhanced ranking.  
🔥 **Why now?** Builds directly on GPT-enhanced output from Step 2 and closes the loop for iterative improvement.

**Tasks:**
- [ ] **Add CLI feedback command** 🔴 **(2 hours)**
  - Implement: `python main.py --feedback task_123 --action=skip`
  - Support feedback actions: skip, done, reject

- [ ] **Automatically log feedback from labels** 🔴 **(1.5 hours)**
  - Track `@today-done` and `@today-skip` labels automatically
  - Extract feedback signals from user task interactions

- [ ] **Write to feedback_log.txt** 🔴 **(1 hour)**
  - Log with timestamp, task ID/content, and action
  - Structured format for future analysis

- [ ] **Add documentation for feedback scenarios** 🟡 **(1 hour)**
  - Update `TESTING.md` with feedback usage examples
  - Document feedback command options

**Commit:** *"Implement feedback loop and logging (Step 3)"*

---

#### 🪜 Step 4: Reliability & Confidence Improvements (v4.4 – Critical Subset)
🎯 **Objective:** Improve trust and robustness of GPT-enhanced ranking.  
🧰 **Why now?** Ensures GPT outputs meet quality thresholds and are cost-efficient.

**Tasks:**
- [ ] **Add confidence threshold in ranking_config.json** 🔴 **(1.5 hours)**
  - Configure minimum confidence (e.g., exclude tasks < 0.6 confidence)
  - Implement threshold filtering in ranking logic

- [ ] **Add caching layer for GPT results** 🔴 **(2.5 hours)**
  - Cache GPT responses to avoid repeated API calls when testing
  - Implement cache invalidation and management

- [ ] **Add minimal unit tests** 🟡 **(2 hours)**
  - Test confidence filtering & fallback logic
  - Validate caching behavior

**Commit:** *"Add confidence threshold, caching, and unit tests (Step 4)"*

---

### 🟢 Nice-to-Have

#### 🪜 Step 5: Advanced Filters & Configurable Modes (v4.2)
🎨 **Objective:** Support advanced mode-aware filters, weights, and exclusions.  
🧰 **Why later?** Not essential for core functionality; can be added after MVP.

**Tasks:**
- [ ] **Extend ranking_config.json with per-mode filters** 🟢 **(2 hours)**
  - Add per-mode Todoist filter queries (optional)
  - Support mode-specific task filtering

- [ ] **Add preferred/excluded labels per mode** 🟢 **(1.5 hours)**
  - Configure labels to prefer or avoid by mode
  - Implement label-based mode filtering

- [ ] **Add per-mode weights** 🟢 **(2 hours)**
  - Configure priority, overdue, etc. weights per mode
  - Support different scoring strategies by mode

- [ ] **Refine auto-detect mode logic** 🟢 **(1.5 hours)**
  - Time/day-based mode detection
  - CLI override support

**Commit:** *"Implement advanced mode filters & weights (Step 5)"*

---

#### 🧪 Ongoing/Parallel Work
🧰 **These can happen in parallel or after MVP milestones are shipped:**

- [ ] **Comprehensive unit test suite** 🟡 **(8-12 hours)**
- [ ] **SectionManager class extraction** 🟡 **(4-6 hours)**
  - Centralized routing logic for section management
- [ ] **Config management consolidation** 🟢 **(3 hours)**
  - Clarity and maintainability improvements
- [ ] **CLI polish** 🟢 **(2 hours)**
  - `--refresh-today`, improved verbose output formatting
- [ ] **Add deployment & contribution documentation** 🔵 **(2 hours)**
- [ ] **Performance monitoring** 🔵 **(3 hours)**
  - Timing metrics and dashboard
- [ ] **URL processing module extraction** 🟢 **(2 hours)**

---

## 📋 Execution Priority

**Immediate Focus (Critical):**
1. ✅ **Phase 4 Step 2 GPT-Enhanced Reranker** (completed)
2. **Phase 4 Step 3 Feedback & Learning System** (next)
3. **Phase 4 Step 4 Reliability & Confidence** (follow-up)

**Future Enhancements (Nice-to-Have):**
4. **Phase 4 Step 5 Advanced Filters & Modes**
5. **Ongoing/Parallel Work** (as time permits)

---

## 🏗️ Architecture Improvements (From Phase 4 Step 2 Reflection)

- [ ] **Extract GPTRerankingConfig class** 🟢 **(2–3 hours)**
  - Centralize GPT reranking configuration logic into a dedicated class
  - Improve readability and reduce duplication when passing configuration dictionaries
  - See reflection suggestion: `GPTRerankingConfig`

- [ ] **Extract CostTracker class** 🟢 **(2–3 hours)**
  - Centralize cost tracking and limit checking logic into a reusable component
  - Improve clarity around cost controls and reporting
  - See reflection suggestion: `CostTracker`

- [ ] **Abstract GPTResponseParser factory** 🟢 **(3 hours)**
  - Use a strategy pattern to support multiple parsing strategies: JSON, regex fallback, default
  - Makes response parsing extensible and easier to maintain

---

## 🧪 Testing & Mock Improvements (From Phase 4 Step 2 Reflection)

- [ ] **Enhance mock GPT responses realism** 🟡 **(1–2 hours)**
  - Improve variety and complexity of mock GPT responses in test fixtures
  - Helps simulate more realistic edge cases during development and testing

---

## ⚡ Performance Optimization (Nice-to-Have)

- [ ] **Batch Processing for GPT** 🔵 **(4 hours)**
  - Investigate batching multiple tasks into a single GPT call
  - Reduce API overhead and improve throughput

- [ ] **Async/Await Processing** 🔵 **(4–5 hours)**
  - Implement async GPT requests for better concurrency during large runs

---

## 🤖 Intelligence & UX Enhancements (Nice-to-Have)

- [ ] **Feedback-Driven Learning System** 🔵 **(5–6 hours)**
  - Track user acceptance/rejection of GPT recommendations to refine future suggestions

- [ ] **Custom Prompt Templates** 🔵 **(3–4 hours)**
  - Allow user-defined prompt templates for specific contexts (e.g., engineering, personal)

- [ ] **Interactive Mode** 🔵 **(4–5 hours)**
  - Prompt user to accept/reject GPT suggestions before applying them

- [ ] **Visual Monitoring Dashboard** 🔵 **(8–10 hours)**
  - Build a web-based dashboard to monitor GPT usage, costs, and effectiveness over time

---

*This task list provides a clear roadmap for completing Phase 4 Step 2 while maintaining code quality and long-term maintainability.*