# Todoist AI Assistant

A powerful and intuitive task automation tool that transforms your [Todoist](https://todoist.com) task list into an organized, actionable workflow. Built on the **TaskSense AI Engine**, it understands your personal context, labels and organizes your tasks, and helps you focus on what matters.

---

## 🧠 TaskSense AI Engine Highlights

- **Context-Aware Labeling**: Personalized labels based on your user profile and mode (work, weekend, etc.)
- **Confidence-Scored Suggestions**: Every label includes a confidence score for transparency
- **Reasoning Levels**: Choose minimal (labels), light (explanation), or deep (rationale + confidence)
- **Soft Matching Mode**: Suggests new labels outside your set, logged for review
- **Mode Awareness**: Time-aware and CLI-controllable (work, personal, weekend, evening)
- **Version Metadata**: Logs include `TaskSense` version, prompt version, and model used
- **Feedback Hooks**: Logs low-confidence/soft matches for future correction
- **Cost-Aware Ready**: Supports caching and rate-limit mitigation (planned)

---

## 🚀 New Features (v3.x)

### 🧩 Modular Pipeline

- Clean separation: TaskSense → Rules → Domain Detection → Section Routing
- Fallback chain with graceful degradation

### 📊 Enhanced Logging

- Structured logs: confidence, explanation, source, version

### 🧪 Testing & Validation

- Mock mode: `--tasksense-mock` for isolated tests
- `validate_config.py` script to check configs

### ⚙️ Soft Matching Behavior

- New labels not in `available_labels` are logged, not applied, and await user approval

---

## 📋 Example CLI Usage

```bash
# Run in work mode
python main.py --mode=work

# Label a task with soft-matching
python main.py --label-task "Fix daycare enrollment" --mode=personal --soft-matching

# Auto-detect mode with confidence threshold
python main.py --mode=auto --confidence-threshold 0.8

# Test pipeline integration
python test_pipeline_integration.py

# Validate config
python validate_config.py
```

---

## 🧾 Feedback Workflow (Planned)

Logs highlight low-confidence and soft-matched labels for manual correction. Future versions will support user feedback loops.

---

## 📜 Versioning

- **TaskSense Engine:** v1.3.2
- **Pipeline:** v3.0.0
- See `CHANGELOG.md` for details.

---

## 🌟 Why Use It?

✅ Modular, maintainable architecture\
✅ Transparent explanations\
✅ Context-sensitive modes\
✅ Developer-friendly with mocks, tests, validation\
✅ Future-ready for interactive feedback-driven features

---

## 📜 License

MIT License. See `LICENSE` for details.

---

## 🙏 Acknowledgments

- Enhanced with the Todoist API ecosystem