# Todoist AI Assistant

The Todoist AI Assistant is an intelligent, context-aware automation system that transforms your [Todoist](https://todoist.com) into a clean, actionable workspace.  
Powered by the **TaskSense AI Engine**, it labels, organizes, and prioritizes your tasks — adapting to your personal work patterns and helping you focus on what matters most.  
All while maintaining transparency, configurability, and reliability.

---

## 🧠 What It Does

### Smart Task Labeling

- Understands task content in the context of your **user profile** and **current mode** (work, personal, weekend, etc.)
- Applies the most relevant labels with **confidence scores** and clear explanations
- Supports **reasoning levels**: minimal (labels only), light (labels + explanation), deep (labels + explanation + rationale)
- Offers **soft matching mode**, suggesting new labels outside your predefined set for later review

### Smart Daily Focus

- Ranks your backlog tasks and selects the most relevant ones for **Today**
- Populates a dedicated **Today section** with your top priorities
- Takes into account task priority, due date, age, and your preferred labels
- Mode-aware prioritization (work, personal, weekend, evening) for context-appropriate suggestions
- Supports `--dry-run` so you can preview your Today list before applying

### URL & Domain Awareness

- Detects and formats URLs in tasks into clean, readable `[Title](URL)` links
- Adds platform-specific labels for common services like GitHub, YouTube, Reddit, and more

### Section Routing

- Moves tasks into appropriate sections (e.g., Links, Meetings, Urgent, Today) based on applied labels and rules
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

✅ Personalized, context-aware task organization  
✅ Transparent and trustworthy with clear explanations and logs  
✅ Automatically identifies what to focus on today  
✅ Modular and extensible architecture, ready for advanced features  
✅ Developer-friendly with mock modes, validation tools, and structured logging  
✅ Backward compatible with your existing Todoist setup and rules

---

## 🧰 Key Components

- **TaskSense AI Engine:** Core semantic engine responsible for intelligent labeling, reasoning, and prioritization
- **Pipeline Architecture:** Modular stages for labeling, rules, domain detection, ranking, and section routing
- **Unified Configuration:** Centralized `task_sense_config.json` and `ranking_config.json` plus optional overrides via CLI or env vars
- **Testing & Validation:** Mock modes, regression tests, config validation script (`validate_config.py`)
- **Logging:** Detailed, structured logs with explanations, scores, confidence levels, and version metadata

---

## 🔧 Configuration Setup

After cloning the repository, you'll need to set up your personal configuration files:

```bash
# Copy the example configuration files
cp task_sense_config.example.json task_sense_config.json
cp rules.example.json rules.json
cp ranking_config.example.json ranking_config.json

# Edit them for your personal workflow
# task_sense_config.json - Contains your user profile, labels, and AI settings
# rules.json - Contains your labeling rules and section routing preferences
# ranking_config.json - Controls scoring weights and Today list preferences
```

**Important:**  
⚠️ **Never commit `task_sense_config.json`, `rules.json`, or `ranking_config.json` to GitHub** — they contain your personal data  
✅ The `.example.json` files are templates provided for your customization  
📝 Customize the `user_profile` field in `task_sense_config.json` and the scoring weights in `ranking_config.json` to match your priorities

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
   - `RANKING_CONFIG_PATH=/path/to/your/ranking_config.json`

---

## 📋 Example CLI Usage

```bash
# Process inbox in work mode
python main.py --mode=work

# Generate today’s prioritized task list
python main.py --generate-today --mode=work --limit=3

# Preview today’s ranking without making changes
python main.py --generate-today --mode=work --limit=3 --dry-run

# Refresh Today section and regenerate
python main.py --generate-today --mode=personal --limit=5 --refresh-today

# Auto-detect mode based on time
python main.py --generate-today --mode=auto
```

---

## 📊 Example Output

```text
Task 123 | TaskSense: #personal (v1.4.0, light) | Confidence: 0.85 | Explanation: Daycare tour aligns with parenting goals

RANK_CANDIDATES: Task 12345 → Score: 0.82 | Reason: High priority and overdue
TODAY_MOVE: Task 12345 moved to Today section
```

Soft-matched labels and daily focus scores are logged and surfaced in the feedback workflow for later review.

---

## 📜 License

MIT License. See `LICENSE` for details.

---

## 🙏 Acknowledgments

- Enhanced with the Todoist API ecosystem

---

The Todoist AI Assistant turns your cluttered task list into a personalized, focused, and manageable system — so you can spend less time organizing and more time doing.
