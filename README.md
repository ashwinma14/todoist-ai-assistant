# Todoist Processor

A powerful task automation system that intelligently processes your Todoist tasks with smart URL handling, rule-based labeling, and AI-powered categorization. Transform chaotic task lists into organized, actionable workflows.

---

## 🔧 What It Does

### 🧠 Smart URL Processing
- **Multi-URL Detection**: Processes multiple URLs in a single task
- **Intelligent Title Fetching**: Converts URLs to `[Page Title](URL)` format
- **Platform-Aware**: Special handling for Reddit, Instagram, YouTube, and 20+ domains
- **Title Cleaning**: Removes noise and truncates overly long titles

### 🏷️ Intelligent Auto-Labeling

#### **Rule-Based Labeling** ⚡
- **URL Detection**: Automatically tags link-containing tasks
- **Content Matching**: Keywords, prefixes, and regex patterns
- **Custom Rules**: Fully configurable via `rules.json`
- **Label Creation**: Automatically creates missing labels when configured

#### **GPT Fallback Labeling** 🤖
- **AI-Powered**: Uses OpenAI GPT for tasks that don't match any rules
- **Context-Aware**: Understands task context and assigns relevant labels
- **Configurable Prompts**: Customize GPT instructions for your workflow
- **Hybrid Approach**: Rules first for speed, GPT for flexibility

### 🧪 Advanced Testing & Debugging
- `--dry-run`: Preview all changes without making modifications
- `--test`: Isolated URL parsing testing
- `--verbose`: Detailed step-by-step processing logs
- **Mock Mode**: Test GPT integration without API calls

### ⚡ Performance & Efficiency
- **Incremental Processing**: Only handles new tasks since last run
- **Smart Skipping**: Avoids re-processing already labeled tasks
- **Timestamp Tracking**: Maintains state for optimal cron performance
- **Rate Limiting Friendly**: GPT only called when necessary

### 📊 Rich Output & Monitoring
- **Colored CLI**: Enhanced interface with `rich` library support
- **Comprehensive Logging**: Separate logs for rule-based vs GPT actions
- **Source Tracking**: Know whether labels came from rules or AI
- **Detailed Summaries**: Clear breakdown of processed, skipped, and failed tasks

---

## 🚀 Installation

```bash
git clone https://github.com/ashwinma14/todoist-processor.git
cd todoist-processor
pip install -r requirements.txt

# Set up environment variables
echo "TODOIST_API_TOKEN=your_todoist_token" > .env
echo "OPENAI_API_KEY=your_openai_key" >> .env  # Optional, for GPT features
```

**Get your tokens:**
- **Todoist**: [Integrations Settings](https://todoist.com/prefs/integrations)
- **OpenAI**: [API Keys](https://platform.openai.com/api-keys) (optional, enables GPT fallback)

---

## ⚙️ Configuration

### Rules Configuration (`rules.json`)

The system uses a flexible rule engine that supports both manual rules and GPT fallback:

```json
{
  "rules": [
    {
      "match": "url",
      "label": "link"
    },
    {
      "contains": ["meeting", "call", "zoom"],
      "label": "meeting",
      "create_if_missing": true
    },
    {
      "prefix": "!",
      "label": "urgent",
      "create_if_missing": true
    },
    {
      "regex": "\\b(bug|fix|issue|error)\\b",
      "label": "bug",
      "create_if_missing": true
    }
  ],
  "gpt_fallback": {
    "enabled": true,
    "model": "gpt-3.5-turbo",
    "base_prompt": "You are a productivity assistant. Assign the most relevant label to this Todoist task using one or two from this list: ['work', 'personal', 'admin', 'media', 'urgent', 'followup', 'home']",
    "user_prompt_extension": "If it's a household chore, prefer 'home'.",
    "create_if_missing": false
  }
}
```

### Rule Types Supported
- **URL Matching**: `"match": "url"`
- **Keyword Matching**: `"contains": ["word1", "word2"]`
- **Prefix Matching**: `"prefix": "!"`
- **Regex Matching**: `"regex": "\\b(pattern)\\b"`

---

## ▶️ Usage Examples

### Basic Usage
```bash
# Process Inbox with rule-based + GPT labeling
python main.py

# Preview changes without making them
python main.py --dry-run

# Process specific projects
python main.py --project "Work,Personal"

# Detailed logging
python main.py --verbose
```

### Advanced Usage
```bash
# Force full scan (ignore incremental mode)
python main.py --full-scan

# Test URL processing only
python main.py --test

# Test GPT integration without real API calls
GPT_MOCK_MODE=1 python main.py --dry-run
```

### Environment Variables
```bash
# Required
TODOIST_API_TOKEN=your_token_here

# Optional
OPENAI_API_KEY=your_key_here          # Enables GPT fallback
PROJECT_NAMES=Inbox,Work              # Default projects to process
FORCE_FULL_SCAN=true                  # Always process all tasks
GPT_MOCK_MODE=1                       # Use mock GPT responses for testing
```

---

## 🎯 Labeling Examples

### Rule-Based Labeling
```
"Follow up with John about the project" → followup
"! Fix the website bug ASAP" → urgent
"Schedule Zoom meeting for Friday" → meeting
"https://github.com/microsoft/vscode" → link, github
```

### GPT Fallback Labeling
```
"Clean the garage and organize tools" → home
"Review quarterly sales report by Friday" → work, urgent
"Schedule dentist appointment next week" → personal, admin
"Watch the new Netflix documentary" → media
```

---

## 🌐 Supported Platforms

### Social Media
- **Twitter/X**, **Reddit**, **LinkedIn**, **Facebook**, **Threads**
- **Instagram**, **TikTok**, **Discord**

### Content & Media
- **YouTube**, **Medium**, **Substack**, **Twitch**

### Development & Tech
- **GitHub**, **StackOverflow**, **Stack Exchange**

### News & Reading
- **Hacker News**

---

## 📊 Real-World Example

**Before Processing:**
```
Todo: Check out these resources:
https://github.com/microsoft/vscode
https://www.youtube.com/watch?v=dQw4w9WgXcQ
Clean the garage this weekend
! Fix the login bug
```

**After Processing:**
```
Todo: Check out these resources:
[Visual Studio Code - Microsoft](https://github.com/microsoft/vscode)
[Rick Astley - Never Gonna Give You Up](https://www.youtube.com/watch?v=dQw4w9WgXcQ)

Labels: link, github, youtube

---

Todo: Clean the garage this weekend
Labels: home (GPT-assigned)

---

Todo: ! Fix the login bug
Labels: urgent, bug (rule-assigned)
```

---

## 🧰 CLI Reference

| Option | Description |
|--------|-------------|
| `--project PROJECT` | Comma-separated project names to process |
| `--dry-run` | Preview changes without making modifications |
| `--verbose`, `-v` | Enable detailed logging output |
| `--test` | Test URL parsing functionality only |
| `--full-scan` | Process all tasks (ignore incremental mode) |

---

## 📁 Logging & Monitoring

### Task Logs (`task_log.txt`)
- **Rule Matching**: Which rules triggered for each task
- **GPT Interactions**: API calls, responses, and fallback actions
- **URL Processing**: Title fetching success/failure details
- **Source Tracking**: Whether labels came from rules or GPT

### Log Examples
```
2024-01-15 10:30:15 | Task 123456 | RULE_MATCH: Rule 0 matched (URL detected) → #link
2024-01-15 10:30:16 | Task 123457 | GPT_SUCCESS: Raw response: 'home' → Parsed labels: ['home']
2024-01-15 10:30:17 | Task 123458 | LABELED | Labels: ['link', 'github'] | Source: rule
```

---

## 🔧 Advanced Configuration

### Custom GPT Prompts
Tailor the AI to your workflow by customizing the GPT configuration:

```json
{
  "gpt_fallback": {
    "enabled": true,
    "model": "gpt-4",
    "base_prompt": "You are a project manager. Categorize this task for maximum productivity.",
    "user_prompt_extension": "Focus on urgency and project context.",
    "create_if_missing": true
  }
}
```

### Automation Setup
Perfect for cron jobs and CI/CD pipelines:

```bash
# Process tasks every 15 minutes
*/15 * * * * cd /path/to/todoist-processor && python main.py

# Daily full scan at midnight
0 0 * * * cd /path/to/todoist-processor && python main.py --full-scan
```

---

## ✅ Requirements

- **Python 3.7+**
- **Todoist account** with API access
- **Internet connection** for URL title fetching
- **OpenAI API key** (optional, for GPT features)

---

## 🤝 Contributing

We welcome contributions! Areas for enhancement:
- Additional platform support for URL processing
- More sophisticated rule matching patterns
- Enhanced GPT prompt engineering
- Performance optimizations

---

## 📜 License

MIT License. See `LICENSE` for details.

---

## 🙏 Acknowledgments

- Built with [Claude Code](https://claude.ai/code)
- Powered by OpenAI GPT for intelligent labeling
- Enhanced with the Todoist API ecosystem