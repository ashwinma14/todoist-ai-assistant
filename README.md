# Todoist AI Assistant

The Todoist AI Assistant is an intelligent, context-aware automation system that transforms your [Todoist](https://todoist.com) into a clean, actionable workspace. Powered by the **TaskSense AI Engine**, it labels and organizes your tasks, adapts to your personal work patterns, and helps you focus on what matters most — all while maintaining transparency, configurability, and reliability.

---

## 🧠 What It Does

### Smart Task Labeling

- Understands task content in the context of your **user profile** and **current mode** (work, personal, weekend, etc.)
- Applies the most relevant labels with **confidence scores** and clear explanations
- Supports **reasoning levels**: minimal (labels only), light (labels + explanation), deep (labels + explanation + rationale)
- Offers **soft matching mode**, suggesting new labels outside your predefined set for later review

### URL & Domain Awareness

- Detects and formats URLs in tasks into clean, readable `[Title](URL)` links
- Adds platform-specific labels for common services like GitHub, YouTube, Reddit, and more

### Section Routing

- Moves tasks into appropriate sections (e.g., Links, Meetings, Urgent) based on applied labels and rules
- Respects existing `create_if_missing` and manual section setup

### Rule & Fallback Logic

- Processes tasks through a robust pipeline:
  1. TaskSense AI Engine
  2. Configurable Rule-Based Labeler (`rules.json`)
  3. GPT fallback (if enabled)
  4. Default label
- Ensures graceful degradation even in case of network errors or API limits

### Mode Awareness

- Automatically adapts to the day of week and time of day (work hours, evenings, weekends)
- CLI flags let you override or specify mode (`--mode=work`, `--mode=personal`, etc.)

---

## 🚀 Why Use It?

✅ Personalized, context-aware task organization\
✅ Transparent and trustworthy with clear explanations and logs\
✅ Modular and extensible architecture, ready for advanced features\
✅ Developer-friendly with mock modes, validation tools, and structured logging\
✅ Backward compatible with your existing Todoist setup and rules

---

## 🧰 Key Components

- **TaskSense AI Engine:** Core semantic engine responsible for intelligent labeling and reasoning
- **Pipeline Architecture:** Modular stages for labeling, rules, domain detection, and section routing
- **Unified Configuration:** Centralized `task_sense_config.json` plus optional overrides via CLI or env vars
- **Testing & Validation:** Mock modes, regression tests, config validation script (`validate_config.py`)
- **Logging:** Detailed, structured logs with explanations, confidence levels, and version metadata

---

## 🔧 Configuration Setup

After cloning the repository, you'll need to set up your personal configuration files:

```bash
# Copy the example configuration files
cp task_sense_config.example.json task_sense_config.json
cp rules.example.json rules.json

# Edit them for your personal workflow
# task_sense_config.json - Contains your user profile, labels, and AI settings
# rules.json - Contains your labeling rules and section routing preferences
```

**Important:** 
- ⚠️ **Never commit `task_sense_config.json` or `rules.json` to GitHub** - they contain your personal data
- ✅ The `.example.json` files are templates provided for your customization
- 📝 Customize the `user_profile` field in `task_sense_config.json` to match your role and priorities

### Environment Variables

Create a `.env` file for your API keys and settings:

```bash
TODOIST_API_TOKEN=your_todoist_token_here
OPENAI_API_KEY=your_openai_key_here  # Optional, for GPT fallback
PROJECT_NAMES=YourProjectName
```

### Render Deployment

For deploying to Render.com or similar platforms:
1. Upload your personalized config files directly to the deployment environment
2. Or use environment variables to specify custom config paths:
   - `TASK_SENSE_CONFIG_PATH=/path/to/your/config.json`
   - `RULES_CONFIG_PATH=/path/to/your/rules.json`

---

## 📋 Example CLI Usage

```bash
# Process inbox in work mode
python main.py --mode=work

# Label a specific task interactively
python main.py --label-task "Schedule quarterly review" --mode=work

# Run in soft-matching mode and log suggestions
python main.py --mode=auto --soft-matching

# Validate configuration
python validate_config.py
```

---

## 📊 Example Output

```text
Task 123 | TaskSense: #personal (v1.3.2, light) | Confidence: 0.85 | Explanation: Daycare tour aligns with parenting goals
```

Soft-matched labels are logged and surfaced in the feedback workflow for later review.

---

## 🧾 Feedback & Continuous Improvement

Low-confidence or soft-matched suggestions are logged for future correction. Feedback workflows and interactive correction interfaces are planned for future releases.

---

## 📜 Versioning

- **TaskSense Engine:** v1.3.2
- **Pipeline:** v3.0.0
- See `CHANGELOG.md` for full history

---

## 📜 License

MIT License. See `LICENSE` for details.

---

## 🙏 Acknowledgments

- Enhanced with the Todoist API ecosystem

---

The Todoist AI Assistant turns your cluttered task list into a personalized, focused, and manageable system — so you can spend less time organizing and more time doing.

