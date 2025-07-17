# Changelog

All notable changes to the Todoist AI Assistant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v4.1] - 2025-07-16

### Added
- **GPT-Enhanced Reranker** with semantic reranking and human-readable explanations
- **JSON-based prompting** for structured, reliable AI interactions with OpenAI API
- **Cost controls** with configurable spending limits ($0.10 default) and real-time tracking
- **Confidence filtering** to ensure quality recommendations (0.7 threshold with fallback)
- **Rich CLI output** with urgency indicators (🔥📋), score changes (↑), and detailed insights
- **Enhanced logging** with GPT_RANK_* patterns for comprehensive monitoring and debugging
- **Comprehensive test suite** with 15 tests (9 unit, 6 integration) achieving 100% pass rate
- **Production documentation** with detailed usage guide, troubleshooting, and examples
- **Mock mode support** for development and testing without API costs

### Enhanced
- **CLI display** now shows confidence scores, urgency indicators, and mode alignment
- **Task ranking** with GPT explanations providing transparent reasoning for priorities
- **Error resilience** with graceful fallbacks when OpenAI API is unavailable
- **Cost transparency** with detailed logging of API usage and spending per session

### Changed
- Cleaned up debug logging from development phase to production-ready levels
- Enhanced production logging for GPT ranking sessions with structured patterns
- Updated README.md with new GPT reranking features and CLI examples

### Verified
- **Live OpenAI API integration** confirmed working with proper authentication
- **Production performance**: ~$0.009 cost per run, ~4-5 seconds latency for 10 candidates
- **Robust fallback behavior** maintains functionality when API limits reached or errors occur
- **Quality filtering** ensures only high-confidence recommendations affect rankings
- **Full production readiness** with monitoring, cost controls, and error handling

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