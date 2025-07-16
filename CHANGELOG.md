# Changelog

All notable changes to the Todoist AI Assistant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TodoistProcessor testing ground with 64 comprehensive test tasks
- Automated test population script with safety checks (`scripts/populate_test_tasks.py`)
- TESTING.md with full instructions, scenarios, and CLI examples
- Enhanced logging for skipped tasks, labels, sections, and Today protection
- Edge case test tasks for no metadata, priority 4, section routing, Today protection, unicode, and duplicates
- Improved visibility into task processing decisions with detailed log messages

### Enhanced
- Task processing logging now shows content previews for skipped tasks
- Section routing logging includes detailed skip reasons and content context
- Label consolidation stage provides clear visibility into existing vs new labels
- Today section protection clearly logged with task content and target section

### Fixed
- Variable scope issue in `should_process_task()` function
- Enhanced error handling for edge cases in task processing