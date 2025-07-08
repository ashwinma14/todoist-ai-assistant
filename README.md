# Todoist AI Assistant

A powerful and intuitive task automation tool that transforms your [Todoist](https://todoist.com) task list into an organized, manageable workflow. It intelligently processes tasks by detecting and formatting URLs, applying smart labels based on customizable rules, leveraging AI to categorize tasks without clear matches, and automatically organizing tasks into appropriate sections. Whether you’re managing work projects, personal errands, or media links, this tool helps you save time and stay focused with minimal manual effort.

---

## 🔧 What It Does

### 🧠 Smart URL Processing
- **Multi-URL Detection**: Identifies and processes multiple URLs within a single task
- **Intelligent Title Fetching**: Converts URLs into `[Page Title](URL)` markdown links for clarity
- **Platform-Aware**: Specialized handling for Reddit, Instagram, YouTube, and 20+ popular domains
- **Title Cleaning**: Removes unnecessary noise and truncates overly long titles for neatness
- **Domain Labels**: Automatically adds platform-specific labels (e.g., github, youtube, reddit)

### 🏷️ Intelligent Auto-Labeling

#### **Rule-Based Labeling** ⚡  
Labeling now applies to **all tasks**, not just those containing links. This system uses flexible matchers to determine when to apply labels:

- **URL Matcher (`"match": "url"`)**: Detects tasks containing one or more URLs  
- **Keyword Matcher (`"contains": [...]`)**: Matches tasks containing specified keywords  
- **Prefix Matcher (`"prefix": "@"`)**: Matches tasks starting with a specific character or string (e.g., tasks beginning with `@` for mentions)  
- **Regex Matcher (`"regex": "pattern"`)**: Matches tasks using regular expressions for advanced pattern matching  

These matchers allow for precise and customizable labeling rules, ensuring your tasks are categorized exactly how you want.

#### **GPT-Powered Labeling (Fallback)** 🤖  
When no rule-based match is found, the system can optionally use OpenAI GPT to suggest labels:  

- **Triggered only if no rules match** to maintain speed and control  
- **Default behavior assigns a single most relevant label**, but can be configured to assign multiple labels by adjusting the prompt  
- **Context-aware**: Understands the task’s content to provide meaningful categorization  
- **Customizable prompts** let you tailor AI behavior to your workflow  

This hybrid approach combines the reliability of rules with the flexibility of AI.

### 📂 Smart Section Router ✨  
Tasks are automatically moved to appropriate sections **only if the matched label was actually applied**. For example:  

- Tasks labeled as `link` are moved to the "Links" section (which is auto-created if configured)  
- Sections like "Meetings," "Urgent," or "Follow-ups" are only triggered when the corresponding label has been successfully applied  
- This ensures that section routing reflects the true categorization of tasks and avoids misplacement  

---

## 🏁 Getting Started

**What is this tool?**  
Todoist AI Assistant is an automation assistant that helps you keep your Todoist Inbox neat and actionable by automatically labeling tasks, formatting URLs, and organizing tasks into sections based on your personalized rules and AI suggestions.

**Who is it for?**  
- Busy professionals juggling multiple projects  
- Anyone overwhelmed by unorganized task lists  
- Users who want smarter task categorization without manual tagging  
- Teams looking to streamline task management  

**Why use it?**  
- Save time by automating repetitive task labeling and organization  
- Gain clearer overviews with well-structured task lists  
- Leverage AI to handle ambiguous tasks intelligently  
- Maintain consistent workflows with customizable, rule-driven logic  

---

## 🚀 Installation

```bash
git clone https://github.com/ashwinma14/todoist-ai-assistant.git
cd todoist-ai-assistant
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
| `match` | Content matcher | Yes* | Matches `"url"` to detect tasks containing URLs |
| `contains` | Content matcher | Yes* | Array of keywords to match within task content |
| `prefix` | Content matcher | Yes* | String that the task must start with (e.g., `"@"` for mentions) |
| `regex` | Content matcher | Yes* | Regular expression pattern for advanced matching |
| `label` | Labeling | Yes | Label to apply when the rule matches |
| `move_to` | Section routing | No | Target section name to move the task to |
| `create_if_missing` | Auto-creation | No | Create label and/or section automatically if missing |

*Each rule requires exactly one matcher field to define matching logic.

### Understanding `create_if_missing`

This powerful field controls **both** label and section creation:

#### **`create_if_missing: true`** (Fully Automated)
- ✅ **Label missing** → Creates the label automatically  
- ✅ **Section missing** → Creates the section automatically  
- ✅ **Always applies** labels and moves tasks accordingly  

#### **`create_if_missing: false`** (Manual Control)
- ❌ **Label missing** → Rule does not apply to the task  
- ❌ **Section missing** → Task is labeled but not moved  
- ✅ **Both exist** → Label applied and task moved as configured  

### Smart Configuration Strategy

#### **URLs (Fully Automated)**
```json
{
  "match": "url",
  "label": "link", 
  "move_to": "Links",
  "create_if_missing": true    // Always works automatically
}
```

#### **Other Rules (Manual Control)**
```json
{
  "contains": ["meeting"],
  "label": "meeting",
  "move_to": "Meetings", 
  "create_if_missing": false   // Requires manual label and section creation
}
```

**Workflow:**
1. Create labels in Todoist for categories you want (e.g., `meeting`, `urgent`)  
2. Create sections in Todoist for organization you want (e.g., `Meetings`, `Urgent`)  
3. The system automatically applies labels and organizes matching tasks  
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
→ Section: None (GPT fallback does not move tasks)

"Review quarterly sales report by Friday" 
→ Labels: work, urgent (GPT-assigned)
→ Section: None (GPT fallback does not move tasks)
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
1. **Fetch Tasks**: Get new or modified tasks from specified projects  
2. **Rule Evaluation**: Apply all rules from `rules.json` to each task  
3. **GPT Fallback**: For unmatched tasks, get AI label suggestions  
4. **Label Application**: Apply matched labels (create if configured)  
5. **Section Routing**: Move tasks to target sections (only if label applied and create if missing configured)  
6. **URL Processing**: Fetch titles and format as markdown links  
7. **Domain Labeling**: Add platform-specific labels for URLs  
8. **Logging**: Record all operations with source attribution  

### Smart Decision Making
- **Rules processed in order** → First match wins for section routing  
- **Multiple rules can match** → All matching labels applied  
- **GPT only triggers** → When no rules match  
- **Section routing only for rules** → GPT fallback does not move tasks  
- **URL processing independent** → Always runs for links regardless of labeling  

---

## ✅ Requirements

- **Python 3.7+**  
- **Todoist account** with API access  
- **Internet connection** for URL title fetching  
- **OpenAI API key** (optional, for GPT fallback features)  

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

- Powered by OpenAI GPT for intelligent labeling  
- Enhanced with the Todoist API ecosystem  

---

## 🚀 Major Updates: TaskSense AI Integration

The Todoist AI Assistant has undergone a complete transformation with three major phases of development, evolving from a simple rule-based processor into a sophisticated AI-powered productivity platform.

### Phase 1: TaskSense AI Engine Integration

#### 🧠 **New AI-Powered Task Labeling**
- **TaskSense Engine**: Advanced AI labeling system that understands context and user preferences
- **Intelligent Fallback Chain**: TaskSense → Rule-based matching → GPT fallback → Default labels
- **Mode-Aware Processing**: Different behavior for work, personal, weekend, and evening contexts

#### 🎯 **Smart Features**
- **Context Understanding**: Analyzes task content with user profile awareness
- **Confidence Scoring**: Each suggestion includes confidence levels (0.0-1.0)
- **Detailed Explanations**: Provides reasoning behind each label suggestion
- **Multi-Label Support**: Can suggest multiple relevant labels per task

#### ⚙️ **Configuration System**
- **`task_sense_config.json`**: Centralized configuration file with:
  - User profile customization
  - Available labels and descriptions
  - Mode-specific preferences (work vs personal vs weekend)
  - Time-based auto-detection rules
  - API settings and fallback options

#### 🔧 **Enhanced CLI**
- **`--mode=work/personal/weekend/evening/auto`**: Set TaskSense processing mode
- **`--label-task "task content" --mode=work`**: Label individual tasks
- **`--tasksense-mock`**: Testing mode with mock responses
- **Auto-detection**: Automatically detects appropriate mode based on time/day

### Phase 2: Configuration Consolidation & Advanced Mode Switching

#### 🔧 **Unified Configuration System**
- **Configuration Hierarchy**: CLI flags → Environment variables → `task_sense_config.json` → `rules.json` fallback
- **GPT Settings Migration**: Moved GPT fallback configuration from `rules.json` to `task_sense_config.json`
- **Environment Overrides**: Support for `DISABLE_GPT_FALLBACK=true` and other env vars
- **Backward Compatibility**: Maintains support for existing `rules.json` configurations

#### 🎯 **Advanced Mode Switching**
- **Time-Based Auto-Detection**: Automatically detects work/personal/weekend/evening modes based on:
  - Current time of day
  - Day of week (weekdays vs weekends)
  - Configurable work hours and evening hours
- **Manual Mode Override**: CLI flags override auto-detection
- **Mode-Specific Prompts**: Tailored AI prompts for each mode context

#### 🧪 **Advanced Testing Framework**
- **TaskSense-Specific Mocks**: Independent of global `GPT_MOCK_MODE`
- **Pattern-Based Mock Responses**: Configurable mock responses for different task types
- **Fallback Chain Validation**: Tests TaskSense → rules → GPT → default progression
- **Accuracy Validation**: 80%+ accuracy testing across all modes and reasoning levels

### Phase 3: Pipeline Abstraction & Advanced Features

#### 🏗️ **Modular Pipeline Architecture**
- **LabelingPipeline Class**: Clean, testable pipeline with `task.run()` interface
- **Stage Separation**: Distinct processing stages:
  - TaskSense AI labeling
  - Rule-based labeling
  - Domain detection (URL analysis)
  - Label consolidation & filtering
  - Application & section routing
- **Graceful Fallback**: Automatic fallback to legacy processing if pipeline unavailable

#### 📊 **Advanced Analytics & Logging**
- **Structured TaskSense Output**: Rich metadata in logging system with:
  - Confidence scores per label
  - Detailed explanations for suggestions
  - Processing time tracking
  - Version information
- **Pipeline Statistics**: Comprehensive performance monitoring

#### ⚙️ **Enhanced Configuration & CLI**
- **Confidence Thresholds**: `--confidence-threshold 0.8` for label acceptance control
- **Soft Matching Mode**: `--soft-matching` suggests labels outside available_labels
- **Advanced Statistics**: Detailed pipeline performance reporting in verbose mode

#### 🔮 **Future-Ready Features**
- **Interactive Feedback Foundation**: Framework for user feedback loops
- **Multi-Pass Processing Ready**: Architecture prepared for advanced label ranking
- **Extensible Design**: Easy addition of new pipeline stages and features

### 🌟 **Complete Feature Set**

```bash
# Basic TaskSense usage
python main.py --mode=work

# Advanced pipeline with confidence control
python main.py --mode=auto --confidence-threshold 0.8 --verbose

# Discover new labels with soft matching
python main.py --soft-matching --dry-run

# Label individual tasks
python main.py --label-task "Schedule quarterly review" --mode=work

# Test with mock responses
python main.py --tasksense-mock --dry-run

# Environment-based overrides
DISABLE_GPT_FALLBACK=true python main.py --mode=work
```

### 📈 **Performance Benefits**
- **Smarter labeling** with context awareness
- **Personalized suggestions** based on user profile
- **Time-aware processing** (work hours vs evenings vs weekends)
- **Transparent reasoning** with explanations
- **Reliable fallback** system ensuring consistent operation
- **Production-ready** with comprehensive testing and monitoring

---

## 🆕 Version History

- **v1.0**: Smart Link Cleaner with URL processing  
- **v1.1**: Rule-based labeling system  
- **v1.2**: GPT fallback labeling integration  
- **v1.3**: Universal task labeling (not just links)  
- **v2.0**: Smart Section Router with automatic organization ✨
- **v3.0**: TaskSense AI Engine Integration (Phase 1)
- **v3.1**: Configuration Consolidation & Advanced Mode Switching (Phase 2)
- **v3.2**: Pipeline Abstraction & Advanced Features (Phase 3)