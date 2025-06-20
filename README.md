# Todoist Processor

A comprehensive task automation system that intelligently processes your Todoist tasks with smart URL handling, rule-based labeling, AI-powered categorization, and automatic section organization. Transform chaotic task lists into beautifully organized, actionable workflows.

---

## 🔧 What It Does

### 🧠 Smart URL Processing
- **Multi-URL Detection**: Processes multiple URLs in a single task
- **Intelligent Title Fetching**: Converts URLs to `[Page Title](URL)` format
- **Platform-Aware**: Special handling for Reddit, Instagram, YouTube, and 20+ domains
- **Title Cleaning**: Removes noise and truncates overly long titles
- **Domain Labels**: Automatic platform-specific labels (github, youtube, reddit, etc.)

### 🏷️ Intelligent Auto-Labeling

#### **Rule-Based Labeling** ⚡
- **URL Detection**: Automatically tags link-containing tasks
- **Content Matching**: Keywords, prefixes, and regex patterns
- **Custom Rules**: Fully configurable via `rules.json`
- **Label Creation**: Automatically creates missing labels when configured
- **Universal Coverage**: Evaluates ALL tasks, not just those with URLs

#### **GPT Fallback Labeling** 🤖
- **AI-Powered**: Uses OpenAI GPT for tasks that don't match any rules
- **Context-Aware**: Understands task context and assigns relevant labels
- **Configurable Prompts**: Customize GPT instructions for your workflow
- **Hybrid Approach**: Rules first for speed, GPT for flexibility

### 📂 Smart Section Router ✨
- **Automatic Organization**: Moves tasks to appropriate sections within Inbox
- **Rule-Based Routing**: Uses same `rules.json` configuration as labeling
- **Dynamic Section Creation**: Creates sections when needed (configurable)
- **Manual Control**: Fine-grained control over which sections get created
- **Visual Organization**: Separates links, meetings, urgent tasks, etc.

### 🧪 Advanced Testing & Debugging
- `--dry-run`: Preview all changes without making modifications
- `--test`: Isolated URL parsing testing
- `--verbose`: Detailed step-by-step processing logs
- **Mock Mode**: Test GPT integration without API calls

### ⚡ Performance & Efficiency
- **Incremental Processing**: Only handles new tasks since last run
- **Smart Skipping**: Avoids re-processing already labeled/organized tasks
- **Timestamp Tracking**: Maintains state for optimal cron performance
- **Rate Limiting Friendly**: GPT only called when necessary

### 📊 Rich Output & Monitoring
- **Colored CLI**: Enhanced interface with `rich` library support
- **Comprehensive Logging**: Separate logs for rule-based vs GPT vs section actions
- **Source Tracking**: Know whether labels came from rules, AI, or domain detection
- **Section Tracking**: Monitor all task movements and section operations
- **Detailed Summaries**: Clear breakdown of processed, labeled, moved, skipped, and failed tasks

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

### Complete Rules Configuration (`rules.json`)

The system uses a sophisticated rule engine supporting labeling, section routing, and GPT fallback:

```json
{
  "rules": [
    {
      "match": "url",
      "label": "link",
      "move_to": "Links",
      "create_if_missing": true
    },
    {
      "contains": ["follow up", "email", "reach out", "contact"],
      "label": "followup",
      "move_to": "Follow-ups",
      "create_if_missing": false
    },
    {
      "prefix": "!",
      "label": "urgent",
      "move_to": "Urgent",
      "create_if_missing": false
    },
    {
      "contains": ["meeting", "call", "zoom", "teams"],
      "label": "meeting",
      "move_to": "Meetings",
      "create_if_missing": false
    },
    {
      "regex": "\\b(bug|fix|issue|error)\\b",
      "label": "bug",
      "move_to": "Issues",
      "create_if_missing": false
    }
  ],
  "gpt_fallback": {
    "enabled": true,
    "model": "gpt-3.5-turbo",
    "base_prompt": "You are a productivity assistant. Assign the most relevant label to this Todoist task using one or two from this list: ['work', 'personal', 'admin', 'media', 'urgent', 'followup', 'home']",
    "user_prompt_extension": "If it's a household chore, prefer 'home'."
  }
}
```

### Rule Field Reference

| Field | Purpose | Required | Description |
|-------|---------|----------|-------------|
| `match` | Content matcher | Yes* | Matches "url" for URL detection |
| `contains` | Content matcher | Yes* | Array of keywords to match |
| `prefix` | Content matcher | Yes* | String that task must start with |
| `regex` | Content matcher | Yes* | Regular expression pattern |
| `label` | Labeling | Yes | Label to apply when rule matches |
| `move_to` | Section routing | No | Target section name for task |
| `create_if_missing` | Auto-creation | No | Create label/section if missing |

*One matcher field required per rule

### Understanding `create_if_missing`

This powerful field controls **both** label and section creation:

#### **`create_if_missing: true`** (Fully Automated)
- ✅ **Label missing** → Creates label automatically
- ✅ **Section missing** → Creates section automatically  
- ✅ **Always applies** labels and moves tasks

#### **`create_if_missing: false`** (Manual Control)
- ❌ **Label missing** → Rule doesn't apply
- ❌ **Section missing** → Task doesn't get moved
- ✅ **Both exist** → Applies label and moves task

### Smart Configuration Strategy

#### **URLs (Fully Automated)**
```json
{
  "match": "url",
  "label": "link", 
  "move_to": "Links",
  "create_if_missing": true    // Always works
}
```

#### **Other Rules (Manual Control)**
```json
{
  "contains": ["meeting"],
  "label": "meeting",
  "move_to": "Meetings", 
  "create_if_missing": false   // Only works if you create them
}
```

**Workflow:**
1. Create labels in Todoist for categories you want (e.g., `meeting`, `urgent`)
2. Create sections in Todoist for organization you want (e.g., `Meetings`, `Urgent`)
3. System automatically applies labels and organizes matching tasks
4. URLs work automatically regardless of manual setup

---

## ▶️ Usage Examples

### Basic Usage
```bash
# Process Inbox with full automation (labeling + section routing)
python main.py

# Preview all changes without making them
python main.py --dry-run

# Process specific projects
python main.py --project "Work,Personal"

# Detailed logging with section operations
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

## 🎯 Processing Examples

### Rule-Based Processing
```
"Follow up with John about the project" 
→ Label: followup
→ Section: Follow-ups (if it exists)

"! Fix the website bug ASAP" 
→ Labels: urgent, bug
→ Sections: Urgent (if it exists)

"Schedule Zoom meeting for Friday" 
→ Label: meeting
→ Section: Meetings (if it exists)

"https://github.com/microsoft/vscode" 
→ Labels: link, github
→ Section: Links (auto-created)
→ Content: [Visual Studio Code - Microsoft](https://github.com/microsoft/vscode)
```

### GPT Fallback Processing
```
"Clean the garage and organize tools" 
→ Label: home (GPT-assigned)
→ Section: None (GPT doesn't route to sections)

"Review quarterly sales report by Friday" 
→ Labels: work, urgent (GPT-assigned)
→ Section: None (GPT doesn't route to sections)
```

### Complete URL Processing
```
Before: https://www.youtube.com/watch?v=dQw4w9WgXcQ
After:  [Rick Astley - Never Gonna Give You Up](https://www.youtube.com/watch?v=dQw4w9WgXcQ)
Labels: link, youtube
Section: Links (auto-created)
```

---

## 📂 Section Organization Examples

### Ideal Inbox Structure
```
📁 Inbox
├── 📎 Links (auto-created)
│   ├── [GitHub Repo](https://github.com/...)
│   ├── [YouTube Video](https://youtube.com/...)
│   └── [Article Title](https://medium.com/...)
├── 📞 Meetings (you create manually)
│   ├── Schedule Zoom call with team
│   └── Prepare agenda for client meeting
├── ⚡ Urgent (you create manually)
│   ├── ! Fix production bug
│   └── ! Submit report by EOD
└── 📧 Follow-ups (you create manually)
    ├── Follow up with John about interview
    └── Reach out to supplier for quote
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
- **Section Operations**: Task movements, section creation, routing decisions
- **URL Processing**: Title fetching success/failure details
- **Source Tracking**: Whether actions came from rules, GPT, or domain detection

### Enhanced Log Examples
```
2024-01-15 10:30:15 | Task 123456 | RULE_MATCH: Rule 0 matched (URL detected) → #link
2024-01-15 10:30:16 | Task 123456 | MOVED_TO_SECTION | Section: Links | Rule: url
2024-01-15 10:30:17 | Task 123457 | GPT_SUCCESS: Raw response: 'home' → Parsed labels: ['home']
2024-01-15 10:30:18 | Task 123458 | SECTION_NOT_FOUND | Reason: Section 'Meetings' not found and create_if_missing=False
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
    "base_prompt": "You are a project manager. Categorize this task for maximum productivity using these labels: ['sprint', 'backlog', 'blocked', 'review', 'done']",
    "user_prompt_extension": "Prioritize 'blocked' for tasks waiting on others. Use 'sprint' for current work."
  }
}
```

### Section Management Strategy

#### **Option 1: Minimal Automation (Recommended)**
- Only URLs auto-create sections
- Manually create other sections you want
- Maximum control, minimal clutter

#### **Option 2: Full Automation**
```json
{
  "create_if_missing": true  // For all rules
}
```
- All matching rules create sections
- More automation, potential for clutter

#### **Option 3: Mixed Approach**
```json
[
  {"label": "urgent", "move_to": "Urgent", "create_if_missing": true},
  {"label": "meeting", "move_to": "Meetings", "create_if_missing": false}
]
```

### Automation Setup
Perfect for cron jobs and CI/CD pipelines:

```bash
# Process tasks every 15 minutes
*/15 * * * * cd /path/to/todoist-processor && python main.py

# Daily full scan at midnight with verbose logging
0 0 * * * cd /path/to/todoist-processor && python main.py --full-scan --verbose
```

---

## 🔄 Processing Flow

### Complete Automation Pipeline
1. **Fetch Tasks**: Get new/modified tasks from specified projects
2. **Rule Evaluation**: Apply all rules from `rules.json` to each task
3. **GPT Fallback**: For unmatched tasks, get AI label suggestions
4. **Label Application**: Apply matched labels (create if configured)
5. **Section Routing**: Move tasks to target sections (create if configured)
6. **URL Processing**: Fetch titles and format as markdown links
7. **Domain Labeling**: Add platform-specific labels for URLs
8. **Logging**: Record all operations with source attribution

### Smart Decision Making
- **Rules processed in order** → First match wins for section routing
- **Multiple rules can match** → All matching labels applied
- **GPT only triggers** → When no rules match
- **Section routing only for rules** → GPT doesn't move tasks
- **URL processing independent** → Always runs for links regardless of labeling

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
- Advanced section organization strategies
- Performance optimizations

---

## 📜 License

MIT License. See `LICENSE` for details.

---

## 🙏 Acknowledgments

- Built with [Claude Code](https://claude.ai/code)
- Powered by OpenAI GPT for intelligent labeling
- Enhanced with the Todoist API ecosystem

---

## 🆕 Version History

- **v1.0**: Smart Link Cleaner with URL processing
- **v1.1**: Rule-based labeling system
- **v1.2**: GPT fallback labeling integration
- **v1.3**: Universal task labeling (not just links)
- **v2.0**: Smart Section Router with automatic organization ✨