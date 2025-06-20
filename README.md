# Todoist Processor

Turn raw URLs in your Todoist tasks into titled markdown links—automatically. This smart processor also applies relevant labels based on the platform, giving your task list structure, clarity, and polish.

---

## 🔧 What It Does

### 🧠 Smarter Links
- Detects multiple URLs in a task
- Fetches webpage titles and formats them as `[Title](URL)`
- Handles platforms like Reddit, YouTube, Instagram, and more
- Cleans up noisy or long titles gracefully

### 🏷️ Smarter Tags
- Tags all link tasks with `link`
- Adds platform-specific labels like `github`, `youtube`, `reddit`
- Supports over 20 popular domains out of the box

### 🧪 Safer Testing
- `--dry-run`: See what would change without editing tasks
- `--test`: Try URL parsing in isolation
- `--verbose`: View detailed step-by-step logs

### 📊 Clean Output
- Easy-to-read CLI interface (with optional color via `rich`)
- Summarizes updated, tagged, skipped, and failed tasks
- Logs everything to `task_log.txt` for debugging and auditing

---

## 🚀 Installation

```bash
git clone https://github.com/yourusername/todoist-processor.git
cd todoist-processor
pip install -r requirements.txt
echo "TODOIST_API_TOKEN=your_token_here" > .env
```

Get your Todoist token from [Integrations Settings](https://todoist.com/prefs/integrations).

---

## ▶️ How to Use It

```bash
# Process all tasks in your Inbox
python main.py

# Dry run (no changes made)
python main.py --dry-run

# Process specific projects
python main.py --project "Work,Personal"

# Test link processing only
python main.py --test

# Get verbose logging
python main.py --verbose
```

Environment variables:
- `TODOIST_API_TOKEN`: Your Todoist API token (required)
- `PROJECT_NAMES`: Comma-separated projects to target (default: "Inbox")

---

## 🌐 Platforms Recognized

- **Social**: Twitter, Reddit, LinkedIn, Facebook, Threads, Instagram, TikTok, Discord  
- **Media**: YouTube, Medium, Substack, Twitch  
- **Tech**: GitHub, StackOverflow  
- **News**: Hacker News  

---

## 🧾 Example

**Before:**
```
Check out:
https://github.com/microsoft/vscode
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

**After:**
```
Check out:
[GitHub - microsoft/vscode: Visual Studio Code](https://github.com/microsoft/vscode)
[Rick Astley - Never Gonna Give You Up (Official Video)](https://www.youtube.com/watch?v=dQw4w9WgXcQ)
```

Labels added: `link`, `github`, `youtube`

---

## 🧰 CLI Options

- `--project PROJECT`: Comma-separated list of project names
- `--dry-run`: Preview only
- `--verbose`, `-v`: Print detailed logs
- `--test`: Test URL parsing only

---

## 📁 Logging

All runs are logged in `task_log.txt`, including:
- Task updates
- API requests and errors
- Title extraction results
- Labeling actions

---

## ✅ Requirements

- Python 3.7+
- Todoist account with API token
- Internet access to fetch link titles

---

## 📜 License

MIT License. See `LICENSE` for details.