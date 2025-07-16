import sys
import os
from dotenv import load_dotenv
load_dotenv()
import re
import requests
from bs4 import BeautifulSoup
import argparse
import logging
from datetime import datetime, timezone, timedelta
import json
# OpenAI import - fallback to requests if package has issues
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# TaskSense AI Engine import
try:
    from task_sense import TaskSense
    TASKSENSE_AVAILABLE = True
except ImportError:
    TASKSENSE_AVAILABLE = False

# LabelingPipeline import
try:
    from labeling_pipeline import LabelingPipeline, PipelineFactory
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False

# Try to import rich for colored output, fallback to regular print
try:
    from rich.console import Console
    console = Console()
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False

class TaskSummary:
    def __init__(self):
        self.tasks_updated = 0
        self.tasks_labeled = 0
        self.tasks_skipped = 0
        self.tasks_failed = 0
        self.skipped_reasons = []
        self.failed_reasons = []
        self.domain_labels_added = {}  # Track domain-specific labels
    
    def updated(self):
        self.tasks_updated += 1
    
    def labeled(self, domain_label=None):
        self.tasks_labeled += 1
        if domain_label and domain_label != "link":
            self.domain_labels_added[domain_label] = self.domain_labels_added.get(domain_label, 0) + 1
    
    def skipped(self, reason):
        self.tasks_skipped += 1
        self.skipped_reasons.append(reason)
    
    def failed(self, reason):
        self.tasks_failed += 1
        self.failed_reasons.append(reason)
    
    def print_summary(self, dry_run=False):
        """Print a clean summary of the processing results"""
        if HAS_RICH:
            console.print("\n" + "="*50, style="bold")
            if dry_run:
                console.print("📊 DRY RUN SUMMARY", style="bold cyan")
            else:
                console.print("📊 PROCESSING SUMMARY", style="bold cyan")
            console.print("="*50, style="bold")
            
            if self.tasks_updated > 0:
                console.print(f"✅ {self.tasks_updated} tasks updated with titles", style="green")
            if self.tasks_labeled > 0:
                console.print(f"🏷️  {self.tasks_labeled} tasks tagged with 'link' label", style="blue")
                if self.domain_labels_added:
                    for domain, count in self.domain_labels_added.items():
                        console.print(f"   • {count}x #{domain} labels added", style="dim blue")
            if self.tasks_skipped > 0:
                console.print(f"⚠️  {self.tasks_skipped} tasks skipped", style="yellow")
                for reason in set(self.skipped_reasons):
                    count = self.skipped_reasons.count(reason)
                    console.print(f"   • {count}x {reason}", style="dim yellow")
            if self.tasks_failed > 0:
                console.print(f"❌ {self.tasks_failed} tasks failed", style="red")
                for reason in set(self.failed_reasons):
                    count = self.failed_reasons.count(reason)
                    console.print(f"   • {count}x {reason}", style="dim red")
        else:
            print("\n" + "="*50)
            if dry_run:
                print("📊 DRY RUN SUMMARY")
            else:
                print("📊 PROCESSING SUMMARY")
            print("="*50)
            
            if self.tasks_updated > 0:
                print(f"✅ {self.tasks_updated} tasks updated with titles")
            if self.tasks_labeled > 0:
                print(f"🏷️  {self.tasks_labeled} tasks tagged with 'link' label")
                if self.domain_labels_added:
                    for domain, count in self.domain_labels_added.items():
                        print(f"   • {count}x #{domain} labels added")
            if self.tasks_skipped > 0:
                print(f"⚠️  {self.tasks_skipped} tasks skipped")
                for reason in set(self.skipped_reasons):
                    count = self.skipped_reasons.count(reason)
                    print(f"   • {count}x {reason}")
            if self.tasks_failed > 0:
                print(f"❌ {self.tasks_failed} tasks failed")
                for reason in set(self.failed_reasons):
                    count = self.failed_reasons.count(reason)
                    print(f"   • {count}x {reason}")

def log_info(message, style="white"):
    """Print info message with optional styling"""
    if HAS_RICH and style != "white":
        console.print(message, style=style)
    else:
        print(message)

def log_success(message):
    """Print success message"""
    log_info(message, "green")

def log_warning(message):
    """Print warning message"""
    log_info(message, "yellow")
    # Force flush output for Render
    import sys
    sys.stdout.flush()

def log_error(message):
    """Print error message"""
    log_info(message, "red")


def setup_task_logging():
    """Setup file logging for task processing"""
    # Create a separate logger for task processing
    task_logger = logging.getLogger('task_processor')
    task_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in task_logger.handlers[:]:
        task_logger.removeHandler(handler)
    
    # Create file handler
    file_handler = logging.FileHandler('task_log.txt', mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create formatter with timestamp
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    task_logger.addHandler(file_handler)
    
    return task_logger


def get_last_run_timestamp():
    """Get the timestamp of the last successful run"""
    try:
        with open('last_run.txt', 'r') as f:
            timestamp_str = f.read().strip()
            return datetime.fromisoformat(timestamp_str)
    except FileNotFoundError:
        # First time run: default to 1 hour ago
        return datetime.now(timezone.utc) - timedelta(hours=1)
    except Exception as e:
        log_warning(f"Failed to read last run timestamp: {e}")
        return datetime.now(timezone.utc) - timedelta(hours=1)


def save_last_run_timestamp():
    """Save the current timestamp as the last successful run"""
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        with open('last_run.txt', 'w') as f:
            f.write(timestamp)
    except Exception as e:
        log_warning(f"Failed to save last run timestamp: {e}")


def parse_todoist_datetime(date_str):
    """Parse Todoist's datetime format to datetime object"""
    try:
        # Todoist uses ISO format like "2023-12-18T21:26:44.000000Z"
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        return datetime.fromisoformat(date_str)
    except Exception:
        return None


def should_process_task(task, last_run_time, task_logger=None, fix_sections=False, rules=None):
    """Determine if a task should be processed based on creation time and existing labels"""
    task_id = task['id']
    
    # If fix_sections mode, check for tasks with labels but missing sections
    if fix_sections:
        existing_labels = set(task.get('labels', []))
        section_id = task.get('section_id')
        
        # Check if task has 'link' label but no section
        if 'link' in existing_labels and not section_id:
            if task_logger:
                task_logger.info(f"Task {task_id} | Processing: has 'link' label but missing section")
            return True, "needs section routing"
            
        # Check for other rule-based labels that need section routing
        # Use provided rules if available, otherwise load them
        if rules is None:
            rules, _, _ = load_unified_config()
        
        for rule in rules:
            rule_label = rule.get('label')
            rule_move_to = rule.get('move_to')
            if rule_label and rule_move_to and rule_label in existing_labels:
                # This task has a label that should be moved to a section
                # Check if it's missing a section or in the wrong section
                if not section_id:
                    if task_logger:
                        task_logger.info(f"Task {task_id} | Processing: has '{rule_label}' label but missing section (should be in '{rule_move_to}')")
                    return True, "needs section routing"
                else:
                    # Check if task is in wrong section
                    current_section_name = get_section_name_by_id(section_id, task.get('project_id'), task_logger)
                    target_section_name = rule_move_to
                    
                    if current_section_name and current_section_name != target_section_name:
                        if task_logger:
                            task_logger.info(f"Task {task_id} | Processing: has '{rule_label}' label in wrong section ('{current_section_name}' → '{target_section_name}')")
                        return True, f"needs section routing: {current_section_name} → {target_section_name}"
        
        # In fix_sections mode, skip tasks that don't need section fixes
        if task_logger:
            task_logger.info(f"Task {task_id} | Skipping: no section fixes needed")
        return False, "no section fixes needed"
    
    # Check creation time (normal mode)
    created_at = parse_todoist_datetime(task.get('created_at', ''))
    if created_at and created_at <= last_run_time:
        if task_logger:
            task_logger.info(f"Task {task_id} | Skipping: created before last run ({created_at} <= {last_run_time})")
        return False, "created before last run"
    
    # Get task content for processing
    content = task['content']
    existing_labels = set(task.get('labels', []))
    
    # Check if task has URLs
    has_any_link = re.search(r'https?://\S+', content)
    
    if has_any_link:
        # For URL tasks, check if they have expected URL labels
        urls = extract_all_urls(content)
        expected_labels = set(['link'])
        for url_info in urls:
            domain_label = get_domain_label(url_info['url'])
            if domain_label:
                expected_labels.add(domain_label)
        
        # If task already has all expected URL labels, skip URL processing
        if expected_labels.issubset(existing_labels):
            if task_logger:
                task_logger.info(f"Task {task_id} | Skipping: already has all expected URL labels {expected_labels}")
            return False, "already fully labeled"
    
    # Always allow processing for rule-based labeling and GPT fallback
    # This ensures non-URL tasks can still be processed by rules or GPT
    return True, "needs processing"


def load_rules(rules_file='rules.json'):
    """Load labeling rules and GPT fallback config from JSON file"""
    try:
        with open(rules_file, 'r') as f:
            config = json.load(f)
        
        # Handle both old format (array) and new format (object with rules and gpt_fallback)
        if isinstance(config, list):
            # Old format - just rules array
            rules = config
            gpt_fallback = None
            log_info(f"📋 Loaded {len(rules)} labeling rules from {rules_file} (legacy format)")
        else:
            # New format - object with rules and gpt_fallback
            rules = config.get('rules', [])
            gpt_fallback = config.get('gpt_fallback')
            log_info(f"📋 Loaded {len(rules)} labeling rules from {rules_file}")
            if gpt_fallback and gpt_fallback.get('enabled'):
                log_info(f"🤖 GPT fallback enabled using model: {gpt_fallback.get('model', 'gpt-4')}")
        
        return rules, gpt_fallback
    except FileNotFoundError:
        log_warning(f"Rules file {rules_file} not found - using URL-only labeling")
        return [{"match": "url", "label": "link"}], None  # Default rule
    except json.JSONDecodeError as e:
        log_error(f"Invalid JSON in {rules_file}: {e}")
        return [{"match": "url", "label": "link"}], None  # Default rule
    except Exception as e:
        log_error(f"Error loading rules: {e}")
        return [{"match": "url", "label": "link"}], None  # Default rule


def load_unified_config(cli_args=None):
    """
    Load configuration with hierarchy: CLI flags → env vars → task_sense_config → rules.json fallback
    Returns: (rules, gpt_fallback, tasksense_config)
    """
    # Start with defaults
    rules = []
    gpt_fallback = None
    tasksense_config = None
    
    # 1. Load TaskSense config (primary source)
    config_path = os.getenv('TASK_SENSE_CONFIG_PATH', 'task_sense_config.json')
    try:
        with open(config_path, 'r') as f:
            tasksense_config = json.load(f)
            
        # Extract GPT fallback from TaskSense config
        gpt_fallback = tasksense_config.get('gpt_fallback')
        log_info("📋 Loaded TaskSense configuration")
        
        if gpt_fallback and gpt_fallback.get('enabled'):
            log_info(f"🤖 GPT fallback enabled using model: {gpt_fallback.get('model', 'gpt-3.5-turbo')}")
            
    except FileNotFoundError:
        log_warning(f"⚠️ TaskSense config not found at {config_path}, falling back to rules.json")
        if os.path.exists('task_sense_config.example.json'):
            log_info("💡 Copy task_sense_config.example.json to task_sense_config.json to customize TaskSense settings")
    except json.JSONDecodeError as e:
        log_error(f"❌ Invalid JSON in task_sense_config.json: {e}")
    except Exception as e:
        log_error(f"❌ Error loading TaskSense config: {e}")
    
    # 2. Load rules.json (for labeling rules and fallback GPT config)
    rules_path = os.getenv('RULES_CONFIG_PATH', 'rules.json')
    try:
        with open(rules_path, 'r') as f:
            rules_config = json.load(f)
            
        # Handle both old format (array) and new format (object with rules and gpt_fallback)
        if isinstance(rules_config, list):
            # Old format - just rules array
            rules = rules_config
            # Keep existing gpt_fallback from TaskSense config
        else:
            # New format - object with rules and gpt_fallback
            rules = rules_config.get('rules', [])
            
            # Use rules.json GPT fallback only if TaskSense doesn't have one
            if not gpt_fallback and rules_config.get('gpt_fallback'):
                gpt_fallback = rules_config.get('gpt_fallback')
                log_info("🤖 Using GPT fallback from rules.json")
                
        log_info(f"📋 Loaded {len(rules)} labeling rules from {rules_path}")
        
    except FileNotFoundError:
        log_warning(f"⚠️ Rules file not found at {rules_path}")
        if os.path.exists('rules.example.json'):
            log_info("💡 Copy rules.example.json to rules.json to customize labeling rules")
    except json.JSONDecodeError as e:
        log_error(f"❌ Invalid JSON in {rules_path}: {e}")
    except Exception as e:
        log_error(f"❌ Error loading rules: {e}")
    
    # 3. Apply environment variable overrides
    if os.getenv('DISABLE_GPT_FALLBACK', '').lower() in ('true', '1', 'yes'):
        if gpt_fallback:
            gpt_fallback['enabled'] = False
            log_info("🔇 GPT fallback disabled by environment variable")
    
    # 4. Apply CLI flag overrides (if provided)
    if cli_args:
        # Future: Add CLI overrides for specific config values
        pass
    
    return rules, gpt_fallback, tasksense_config


def evaluate_rule(rule, task_content):
    """Evaluate a single rule against task content"""
    content_lower = task_content.lower()
    
    # URL matcher
    if rule.get("match") == "url":
        return bool(re.search(r'https?://\S+', task_content))
    
    # Contains matcher
    if "contains" in rule:
        keywords = rule["contains"]
        if isinstance(keywords, str):
            keywords = [keywords]
        return any(keyword.lower() in content_lower for keyword in keywords)
    
    # Prefix matcher
    if "prefix" in rule:
        prefix = rule["prefix"]
        return task_content.strip().startswith(prefix)
    
    # Regex matcher
    if "regex" in rule:
        try:
            pattern = rule["regex"]
            return bool(re.search(pattern, task_content, re.IGNORECASE))
        except re.error as e:
            log_warning(f"Invalid regex pattern '{pattern}': {e}")
            return False
    
    return False


def apply_rules_to_task(task, rules, gpt_fallback=None, task_logger=None, mode=None, tasksense_config=None):
    """Apply all matching rules to a task and return labels to add, with TaskSense and GPT fallback"""
    content = task['content']
    task_id = task['id']
    labels_to_add = []
    applied_rules = []
    
    # First, try rule-based matching
    for i, rule in enumerate(rules):
        if evaluate_rule(rule, content):
            label = rule.get("label")
            if label:
                labels_to_add.append(label)
                rule_info = {
                    "rule_index": i,
                    "label": label,
                    "matcher": get_rule_matcher_type(rule),
                    "create_if_missing": rule.get("create_if_missing", False),
                    "move_to": rule.get("move_to"),
                    "source": "rule"
                }
                applied_rules.append(rule_info)
                
                if task_logger:
                    matcher_desc = get_rule_description(rule)
                    task_logger.info(f"Task {task_id} | RULE_MATCH: Rule {i} matched ({matcher_desc}) → #{label}")
    
    # If no rules matched and AI fallback is enabled, try TaskSense first, then GPT
    if not labels_to_add and gpt_fallback and gpt_fallback.get('enabled'):
        # Try TaskSense first if available
        if TASKSENSE_AVAILABLE:
            try:
                # Initialize TaskSense with updated config
                if tasksense_config:
                    task_sense = TaskSense(config_path=None)
                    task_sense.config = tasksense_config
                else:
                    task_sense = TaskSense()
                    
                result = task_sense.label(content, dry_run=False, mode=mode)
                
                if result and result.get('labels'):
                    tasksense_labels = result['labels']
                    labels_to_add.extend(tasksense_labels)
                    
                    for label in tasksense_labels:
                        rule_info = {
                            "label": label,
                            "matcher": "tasksense",
                            "create_if_missing": gpt_fallback.get("create_if_missing", False),
                            "source": "tasksense",
                            "explanation": result.get('explanation', ''),
                            "confidence": result.get('confidence', 0.8),
                            "engine_meta": result.get('engine_meta', {})
                        }
                        applied_rules.append(rule_info)
                        
                        if task_logger:
                            explanation = result.get('explanation', '')
                            confidence = result.get('confidence', 0.8)
                            version = result.get('engine_meta', {}).get('version', 'unknown')
                            task_logger.info(f"Task {task_id} | TASKSENSE_MATCH: TaskSense ({version}) suggested label → #{label} (confidence: {confidence:.2f}) | {explanation}")
                            
            except Exception as e:
                if task_logger:
                    task_logger.warning(f"Task {task_id} | TASKSENSE_ERROR: {str(e)}, falling back to GPT")
        
        # Fallback to original GPT if TaskSense failed or unavailable
        if not labels_to_add:
            gpt_labels = get_gpt_labels(content, gpt_fallback, task_logger, task_id)
            if gpt_labels:
                labels_to_add.extend(gpt_labels)
                for label in gpt_labels:
                    rule_info = {
                        "label": label,
                        "matcher": "gpt",
                        "create_if_missing": gpt_fallback.get("create_if_missing", False),
                        "source": "gpt"
                    }
                    applied_rules.append(rule_info)
                    
                    if task_logger:
                        task_logger.info(f"Task {task_id} | GPT_MATCH: GPT suggested label → #{label}")
    
    return labels_to_add, applied_rules


def get_rule_matcher_type(rule):
    """Get a description of what type of matcher the rule uses"""
    if rule.get("match") == "url":
        return "url"
    elif "contains" in rule:
        return "contains"
    elif "prefix" in rule:
        return "prefix"
    elif "regex" in rule:
        return "regex"
    else:
        return "unknown"


def get_rule_description(rule):
    """Get a human-readable description of the rule"""
    if rule.get("match") == "url":
        return "URL detected"
    elif "contains" in rule:
        keywords = rule["contains"]
        if isinstance(keywords, list):
            keywords_str = ", ".join(keywords[:2])
            if len(keywords) > 2:
                keywords_str += f", +{len(keywords)-2} more"
        else:
            keywords_str = keywords
        return f"contains: {keywords_str}"
    elif "prefix" in rule:
        return f"starts with: '{rule['prefix']}'"
    elif "regex" in rule:
        return f"regex: {rule['regex'][:20]}..."
    else:
        return "unknown rule"


def create_label_if_missing(label_name, task_logger=None):
    """Create a label if it doesn't exist"""
    try:
        # Check if label already exists
        r = requests.get(f"{TODOIST_API}/labels", headers=HEADERS)
        r.raise_for_status()
        existing_labels = {label['name'].lower(): label['id'] for label in r.json()}
        
        if label_name.lower() in existing_labels:
            return existing_labels[label_name.lower()]
        
        # Create new label
        create_resp = requests.post(f"{TODOIST_API}/labels", headers=HEADERS, 
                                  json={"name": label_name})
        if create_resp.status_code in (200, 201):
            label_data = create_resp.json()
            if task_logger:
                task_logger.info(f"LABEL_CREATED: Created new label '#{label_name}' (ID: {label_data['id']})")
            log_info(f"📝 Created new label: #{label_name}")
            return label_data['id']
        else:
            if task_logger:
                task_logger.error(f"LABEL_CREATE_FAILED: Failed to create label '#{label_name}' (HTTP {create_resp.status_code})")
            return None
    except Exception as e:
        if task_logger:
            task_logger.error(f"LABEL_CREATE_ERROR: Error creating label '#{label_name}': {e}")
        log_warning(f"Failed to create label #{label_name}: {e}")
        return None


def get_gpt_labels(content, gpt_config, task_logger=None, task_id=None):
    """Get label suggestions from GPT for a task"""
    try:
        # Check for OpenAI API key
        if not os.environ.get('OPENAI_API_KEY'):
            if task_logger and task_id:
                task_logger.warning(f"Task {task_id} | GPT_SKIP: OPENAI_API_KEY not set")
            return []
        
        # Check for mock mode for testing
        if os.environ.get('GPT_MOCK_MODE'):
            mock_labels = _get_mock_gpt_labels(content)
            if task_logger and task_id:
                task_logger.info(f"Task {task_id} | GPT_MOCK: Mock response → {mock_labels}")
            return mock_labels
        
        # Construct prompt
        base_prompt = gpt_config.get('base_prompt', 'Assign a relevant label to this Todoist task.')
        user_extension = gpt_config.get('user_prompt_extension', '')
        
        full_prompt = f"{base_prompt}\n\n{user_extension}\n\nTask: {content}\n\nRespond with only the label name(s), separated by commas if multiple. Do not include explanations."
        
        # Try OpenAI package first, fallback to direct requests
        if OPENAI_AVAILABLE:
            try:
                # Initialize OpenAI client with defensive error handling
                client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model=gpt_config.get('model', 'gpt-3.5-turbo'),
                    messages=[{"role": "user", "content": full_prompt}],
                    max_tokens=50,
                    temperature=0.3
                )
                
                if response.choices and response.choices[0].message.content:
                    raw_response = response.choices[0].message.content.strip()
                    labels = [label.strip().lower() for label in raw_response.split(',')]
                    labels = [label for label in labels if label and len(label) > 0]
                    
                    if task_logger and task_id:
                        task_logger.info(f"Task {task_id} | GPT_SUCCESS: Raw response: '{raw_response}' → Parsed labels: {labels}")
                    
                    return labels[:2]
                    
            except TypeError as e:
                # Handle potential version-specific errors like unexpected keyword arguments
                if "proxies" in str(e) or "unexpected keyword argument" in str(e):
                    if task_logger and task_id:
                        task_logger.warning(f"Task {task_id} | GPT_CLIENT_INIT_ERROR (likely version mismatch): {str(e)}, falling back to HTTP")
                else:
                    if task_logger and task_id:
                        task_logger.warning(f"Task {task_id} | GPT_TYPE_ERROR: {str(e)}, falling back to HTTP")
            except Exception as e:
                if task_logger and task_id:
                    task_logger.warning(f"Task {task_id} | GPT_PACKAGE_ERROR: {str(e)}, falling back to HTTP")
        
        # Fallback to direct HTTP requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        data = {
            "model": gpt_config.get('model', 'gpt-3.5-turbo'),
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": 50,
            "temperature": 0.3
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('choices') and result['choices'][0].get('message', {}).get('content'):
                raw_response = result['choices'][0]['message']['content'].strip()
                
                # Parse comma-separated labels
                labels = [label.strip().lower() for label in raw_response.split(',')]
                labels = [label for label in labels if label and len(label) > 0]
                
                if task_logger and task_id:
                    task_logger.info(f"Task {task_id} | GPT_HTTP_SUCCESS: Raw response: '{raw_response}' → Parsed labels: {labels}")
                
                return labels[:2]  # Limit to 2 labels max
        else:
            if task_logger and task_id:
                task_logger.error(f"Task {task_id} | GPT_HTTP_ERROR: {response.status_code} - {response.text}")
        
        if task_logger and task_id:
            task_logger.warning(f"Task {task_id} | GPT_EMPTY: No content in response")
        return []
        
    except Exception as e:
        if task_logger and task_id:
            task_logger.error(f"Task {task_id} | GPT_ERROR: {str(e)}")
        log_warning(f"GPT API error: {str(e)}")
        return []


def _get_mock_gpt_labels(content):
    """Mock GPT responses for testing"""
    content_lower = content.lower()
    
    # Simple heuristics for testing
    if any(word in content_lower for word in ['clean', 'organize', 'garage', 'basement', 'house', 'room']):
        return ['home']
    elif any(word in content_lower for word in ['work', 'meeting', 'project', 'deadline']):
        return ['work']
    elif any(word in content_lower for word in ['doctor', 'appointment', 'pay', 'tax', 'bill']):
        return ['admin']
    elif any(word in content_lower for word in ['watch', 'read', 'video', 'article']):
        return ['media']
    else:
        return ['personal']


def get_project_sections(project_id, task_logger=None):
    """Get all sections for a project"""
    try:
        response = requests.get(f"{TODOIST_API}/sections?project_id={project_id}", headers=HEADERS)
        response.raise_for_status()
        sections = response.json()
        
        if task_logger:
            task_logger.info(f"SECTIONS: Retrieved {len(sections)} sections for project {project_id}")
        
        return {section['name']: section['id'] for section in sections}
    except Exception as e:
        if task_logger:
            task_logger.error(f"SECTIONS_ERROR: Failed to get sections for project {project_id}: {e}")
        log_warning(f"Failed to get sections for project {project_id}: {e}")
        return {}


def get_section_name_by_id(section_id, project_id, task_logger=None):
    """Get section name from section_id for a specific project"""
    if not section_id:
        return None
        
    try:
        response = requests.get(f"{TODOIST_API}/sections?project_id={project_id}", headers=HEADERS)
        response.raise_for_status()
        sections = response.json()
        
        # Find section by ID
        for section in sections:
            if section['id'] == section_id:
                return section['name']
        
        # Section ID not found in this project
        if task_logger:
            task_logger.warning(f"SECTION_NOT_FOUND: Section ID {section_id} not found in project {project_id}")
        return None
        
    except Exception as e:
        if task_logger:
            task_logger.error(f"SECTION_NAME_ERROR: Failed to get section name for ID {section_id}: {e}")
        return None


def select_priority_section(task_labels, rules, project_id, task_logger=None):
    """
    Select the best section for a task based on label priorities and section availability.
    
    Args:
        task_labels: Set of labels on the task
        rules: List of rules from rules.json
        project_id: Todoist project ID
        task_logger: Logger instance
    
    Returns:
        dict: Selected section info with reasoning, or None if no viable section
        {
            'section_name': str,
            'create_if_missing': bool,
            'priority': int,
            'label': str,
            'exists': bool,
            'reason': str
        }
    """
    if not task_labels:
        return None
    
    # Collect all candidate sections from task labels
    candidates = []
    existing_sections = {}
    
    try:
        # Get existing sections for this project
        existing_sections = get_project_sections(project_id, task_logger)
    except Exception as e:
        if task_logger:
            task_logger.error(f"PRIORITY_SECTION_ERROR: Failed to get project sections: {e}")
        return None
    
    # Find all rules that match task labels and have move_to
    for rule in rules:
        rule_label = rule.get('label')
        rule_move_to = rule.get('move_to')
        
        if rule_label and rule_move_to and rule_label in task_labels:
            priority = rule.get('priority', 999)  # Default to low priority if not specified
            create_if_missing = rule.get('create_if_missing', False)
            section_exists = rule_move_to in existing_sections
            
            candidates.append({
                'section_name': rule_move_to,
                'create_if_missing': create_if_missing,
                'priority': priority,
                'label': rule_label,
                'exists': section_exists,
                'rule': rule
            })
    
    if not candidates:
        if task_logger:
            task_logger.debug(f"PRIORITY_SECTION: No section candidates found for labels: {task_labels}")
        return None
    
    # Sort candidates by priority (lower number = higher priority)
    candidates.sort(key=lambda x: x['priority'])
    
    # Log all candidates for transparency
    if task_logger:
        candidate_info = []
        for c in candidates:
            status = "exists" if c['exists'] else ("create" if c['create_if_missing'] else "missing")
            candidate_info.append(f"{c['label']}→{c['section_name']}(p:{c['priority']},{status})")
        task_logger.info(f"SECTION_CANDIDATES: Found {len(candidates)} candidates: {', '.join(candidate_info)}")
    
    # Select best viable candidate
    for candidate in candidates:
        section_name = candidate['section_name']
        exists = candidate['exists']
        create_if_missing = candidate['create_if_missing']
        
        if exists:
            # Section exists - this is our best choice
            candidate['reason'] = f"highest priority existing section"
            if task_logger:
                task_logger.info(f"SECTION_SELECTED: Chose '{section_name}' (priority:{candidate['priority']}, exists:true)")
            return candidate
        elif create_if_missing:
            # Section doesn't exist but can be created
            candidate['reason'] = f"highest priority with create_if_missing=true"
            if task_logger:
                task_logger.info(f"SECTION_SELECTED: Chose '{section_name}' (priority:{candidate['priority']}, will_create:true)")
            return candidate
        else:
            # Section doesn't exist and can't be created - skip
            if task_logger:
                task_logger.info(f"SECTION_SKIPPED: '{section_name}' (priority:{candidate['priority']}, missing, create_if_missing=false)")
            continue
    
    # No viable candidates found
    if task_logger:
        task_logger.warning(f"SECTION_NO_VIABLE: No viable sections found from {len(candidates)} candidates")
    return None


def route_task_to_section(task, rules, task_logger=None, dry_run=False, bulk_mode=False, context="UNIVERSAL"):
    """
    Universal section routing for any task with existing labels.
    
    Args:
        task: Task dictionary from Todoist API
        rules: List of rules from rules.json
        task_logger: Logger instance
        dry_run: If True, only log what would happen
        bulk_mode: If True, use bulk API operations
        context: String context for logging (e.g., "UNIVERSAL", "PRE_LABELED")
    
    Returns:
        bool: True if routing succeeded or no routing needed, False if failed
    """
    existing_labels = set(task.get('labels', []))
    current_section_id = task.get('section_id')
    project_id = task.get('project_id')
    
    if not project_id:
        if task_logger:
            task_logger.error(f"{context}_ROUTE_ERROR: Task {task['id']} has no project_id")
        return False
    
    if not existing_labels:
        return True  # No labels to route
    
    # Only route tasks in the backlog (no section assigned)
    if current_section_id is not None:
        if task_logger:
            current_section_name = get_section_name_by_id(current_section_id, project_id, task_logger)
            task_logger.info(f"SECTION_SKIP: Task {task['id']} already in section {current_section_name} (section_id: {current_section_id})")
        return True  # Skip tasks that already have a section
    
    # Use priority-based section selection
    selected_section = select_priority_section(existing_labels, rules, project_id, task_logger)
    
    if not selected_section:
        if task_logger:
            task_logger.debug(f"{context}_NO_SECTION: Task {task['id']} has no viable section candidates")
        return True  # No routing needed
    
    target_section_name = selected_section['section_name']
    current_section_name = get_section_name_by_id(current_section_id, project_id, task_logger)
    
    # Check if task needs to be moved
    if current_section_name == target_section_name:
        if task_logger:
            task_logger.info(f"{context}_SKIP: Task {task['id']} already in target section '{target_section_name}' (priority:{selected_section['priority']}, reason: {selected_section['reason']})")
        return True
    
    if task_logger:
        task_logger.info(f"{context}_ROUTE: Task {task['id']} with '{selected_section['label']}' label needs routing: '{current_section_name}' → '{target_section_name}' (priority:{selected_section['priority']}, reason: {selected_section['reason']})")
    
    if dry_run:
        if task_logger:
            task_logger.info(f"DRY_RUN: Would move task {task['id']} to section {target_section_name}")
        return True
    
    # Get or create target section
    section_id = None
    create_if_missing = selected_section['create_if_missing']
    
    if create_if_missing:
        section_id = create_section_if_missing_sync(target_section_name, project_id, task_logger)
    else:
        sections = get_project_sections(project_id, task_logger)
        section_id = sections.get(target_section_name)
    
    if section_id:
        # Check if already in target section (defensive check)
        if current_section_id == section_id:
            if task_logger:
                task_logger.info(f"{context}_SKIP: Task {task['id']} already in target section {target_section_name}")
            return True
        
        # Move task to correct section
        move_success = move_task_to_section(task['id'], section_id, task_logger, task['content'], bulk_mode)
        if move_success:
            if task_logger:
                task_logger.info(f"{context}_MOVED: Task {task['id']} moved to section {target_section_name} (priority:{selected_section['priority']})")
            return True
        else:
            if task_logger:
                task_logger.error(f"{context}_MOVE_FAILED: Failed to move task {task['id']} to section {target_section_name}")
            return False
    else:
        if task_logger:
            task_logger.error(f"{context}_SECTION_ERROR: Section {target_section_name} not found or could not be created")
        return False


def route_pre_labeled_task(task, rules, task_logger=None, dry_run=False, bulk_mode=False):
    """Handle section routing for tasks that already have labels (fix-sections mode)"""
    return route_task_to_section(task, rules, task_logger, dry_run, bulk_mode, context="PRE_LABELED")


def create_section_if_missing(section_name, project_id, task_logger=None):
    """Create a section if it doesn't exist, return section_id"""
    try:
        # First check if section already exists
        sections = get_project_sections(project_id, task_logger)
        if section_name in sections:
            return sections[section_name]
        
        # Create new section
        create_data = {
            "name": section_name,
            "project_id": project_id
        }
        
        response = requests.post(f"{TODOIST_API}/sections", headers=HEADERS, json=create_data)
        if response.status_code in (200, 201):
            section_data = response.json()
            section_id = section_data['id']
            
            if task_logger:
                task_logger.info(f"SECTION_CREATED: Created section '{section_name}' (ID: {section_id}) in project {project_id}")
            log_info(f"📂 Created section: {section_name}")
            
            return section_id
        else:
            if task_logger:
                task_logger.error(f"SECTION_CREATE_FAILED: Failed to create section '{section_name}' (HTTP {response.status_code})")
            return None
            
    except Exception as e:
        if task_logger:
            task_logger.error(f"SECTION_CREATE_ERROR: Error creating section '{section_name}': {e}")
        log_warning(f"Failed to create section {section_name}: {e}")
        return None


def create_section_sync_api(section_name, project_id, task_logger=None):
    """Create a section using Sync API v9"""
    import uuid
    
    try:
        sync_url = "https://api.todoist.com/sync/v9/sync"
        
        # Create a command to add the section
        temp_id = str(uuid.uuid4())
        command = {
            "type": "section_add",
            "uuid": str(uuid.uuid4()),
            "temp_id": temp_id,
            "args": {
                "name": section_name,
                "project_id": project_id
            }
        }
        
        sync_data = {
            "commands": [command]
        }
        
        if task_logger:
            task_logger.info(f"SYNC_SECTION_REQUEST: URL={sync_url}, command={command}")
        
        headers = {"Authorization": f"Bearer {os.environ['TODOIST_API_TOKEN'].strip()}",
                  "Content-Type": "application/json"}
        response = requests.post(sync_url, json=sync_data, headers=headers)
        
        if task_logger:
            task_logger.info(f"SYNC_SECTION_RESPONSE: status={response.status_code}, content={response.text}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if the command was successful
            command_uuid = command["uuid"]
            if result.get("sync_status", {}).get(command_uuid) == "ok":
                # Get the temp_id mapping to find the real section ID
                temp_id = command.get("temp_id")
                if temp_id and temp_id in result.get("temp_id_mapping", {}):
                    section_id = result["temp_id_mapping"][temp_id]
                    if task_logger:
                        task_logger.info(f"SECTION_CREATED_SYNC: Section '{section_name}' created with ID {section_id}")
                    return section_id
                else:
                    # Try to fetch the section by name to get its ID
                    sections = get_project_sections(project_id, task_logger)
                    if section_name in sections:
                        if task_logger:
                            task_logger.info(f"SECTION_CREATED_SYNC: Section '{section_name}' created, retrieved ID {sections[section_name]}")
                        return sections[section_name]
            else:
                if task_logger:
                    task_logger.error(f"SYNC_SECTION_FAILED: Command failed with status: {result.get('sync_status', {}).get(command_uuid)}")
                return None
        else:
            if task_logger:
                task_logger.error(f"SYNC_SECTION_ERROR: HTTP {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        if task_logger:
            task_logger.error(f"SYNC_SECTION_EXCEPTION: Error creating section '{section_name}': {e}")
        return None


def create_section_if_missing_sync(section_name, project_id, task_logger=None):
    """Create a section if it doesn't exist using Sync API, return section_id"""
    try:
        # First check if section already exists
        sections = get_project_sections(project_id, task_logger)
        if section_name in sections:
            return sections[section_name]
        
        # Create new section using Sync API
        return create_section_sync_api(section_name, project_id, task_logger)
            
    except Exception as e:
        if task_logger:
            task_logger.error(f"SECTION_CREATE_ERROR: Error creating section '{section_name}': {e}")
        log_warning(f"Failed to create section {section_name}: {e}")
        return None


def move_task_to_section_sync_api(task_id, section_id, task_logger=None, bulk_mode=False):
    """Move a task to a specific section using Sync API v9 with rate limiting"""
    import uuid
    import time
    
    try:
        # Use Sync API v9 for task movement
        sync_url = "https://api.todoist.com/sync/v9/sync"
        
        # Create a command to move the task
        command = {
            "type": "item_move",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": task_id,
                "section_id": section_id
            }
        }
        
        sync_data = {
            "commands": [command]
        }
        
        if task_logger:
            task_logger.info(f"SYNC_MOVE_REQUEST: URL={sync_url}, command={command}")
        
        # Add rate limiting delay - more aggressive in bulk mode
        if bulk_mode:
            time.sleep(2.0)  # 2 seconds for bulk processing
        else:
            time.sleep(1.0)  # 1 second for normal processing
        
        response = requests.post(sync_url, headers=HEADERS, json=sync_data)
        
        if task_logger:
            task_logger.info(f"SYNC_MOVE_RESPONSE: status={response.status_code}, content={response.text[:300]}")
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Check if the command was successful
            if "sync_status" in response_data:
                command_uuid = command["uuid"]
                if command_uuid in response_data["sync_status"] and response_data["sync_status"][command_uuid] == "ok":
                    if task_logger:
                        task_logger.info(f"TASK_MOVED_SYNC: Task {task_id} moved to section {section_id} via Sync API")
                    return True
                else:
                    if task_logger:
                        error_details = response_data.get('sync_status', {}).get(command_uuid, 'unknown error')
                        task_logger.error(f"SYNC_MOVE_FAILED: Task {task_id} to section {section_id} | Error: {error_details} | Full response: {response.text[:500]}")
                    return False
            else:
                # If no sync_status, assume success if no error
                if task_logger:
                    task_logger.info(f"TASK_MOVED_SYNC: Task {task_id} moved to section {section_id} via Sync API (assumed success)")
                return True
        elif response.status_code == 429:
            # Rate limit hit - implement retry with shorter wait in bulk mode
            try:
                error_data = response.json()
                retry_after = error_data.get('error_extra', {}).get('retry_after', 60)
                
                # In bulk mode, use shorter retry delays to avoid falling back to broken REST API
                if bulk_mode and retry_after > 45:
                    wait_time = min(retry_after, 45)  # Cap at 45 seconds in bulk mode
                    if task_logger:
                        task_logger.warning(f"SYNC_RATE_LIMITED: Bulk mode - waiting {wait_time}s instead of {retry_after}s")
                    time.sleep(wait_time)
                    
                    # Retry once with Sync API
                    retry_response = requests.post(sync_url, headers=HEADERS, json=sync_data)
                    if retry_response.status_code == 200:
                        retry_data = retry_response.json()
                        command_uuid = command["uuid"]
                        if retry_data.get("sync_status", {}).get(command_uuid) == "ok":
                            if task_logger:
                                task_logger.info(f"TASK_MOVED_SYNC_RETRY: Task {task_id} moved to section {section_id} after retry")
                            return True
                    
                    if task_logger:
                        task_logger.warning(f"SYNC_RETRY_FAILED: Retry failed, skipping task {task_id} for next run")
                    return False
                else:
                    if task_logger:
                        task_logger.warning(f"SYNC_RATE_LIMITED: Hit rate limit, need to wait {retry_after} seconds. Skipping for next run.")
                    return False
            except:
                if task_logger:
                    task_logger.warning(f"SYNC_RATE_LIMITED: Hit rate limit (429), skipping for next run")
                return False
        else:
            if task_logger:
                task_logger.error(f"SYNC_MOVE_HTTP_ERROR: Task {task_id} to section {section_id} | Status: {response.status_code} | Response: {response.text[:300]}")
            return False
            
    except Exception as e:
        if task_logger:
            task_logger.error(f"SYNC_MOVE_EXCEPTION: Task {task_id} to section {section_id} | Exception: {str(e)}")
        log_warning(f"Failed to move task {task_id} to section via Sync API: {e}")
        return False


def move_task_to_section(task_id, section_id, task_logger=None, task_content=None, bulk_mode=False):
    """Move a task to a specific section using Sync API v9 with retry logic"""
    
    # Use Sync API v9 exclusively - no fallback to broken REST API v2
    success = move_task_to_section_sync_api(task_id, section_id, task_logger, bulk_mode)
    
    if not success and task_logger:
        task_logger.warning(f"TASK_MOVE_SKIPPED: Task {task_id} skipped due to rate limits - will retry in next run")
    
    return success


def log_task_action(task_logger, task_id, task_content, action, **kwargs):
    """Log task processing action with details"""
    # Truncate very long content for readability
    content_preview = task_content[:100] + "..." if len(task_content) > 100 else task_content
    
    log_parts = [
        f"Task {task_id}",
        f"Content: {repr(content_preview)}",
        f"Action: {action}"
    ]
    
    # Add optional details
    if 'title' in kwargs and kwargs['title']:
        title_preview = kwargs['title'][:80] + "..." if len(kwargs['title']) > 80 else kwargs['title']
        log_parts.append(f"Title: {repr(title_preview)}")
    
    if 'labels' in kwargs and kwargs['labels']:
        log_parts.append(f"Labels: {kwargs['labels']}")
    
    if 'url' in kwargs and kwargs['url']:
        log_parts.append(f"URL: {kwargs['url']}")
    
    if 'error' in kwargs and kwargs['error']:
        log_parts.append(f"Error: {kwargs['error']}")
    
    if 'reason' in kwargs and kwargs['reason']:
        log_parts.append(f"Reason: {kwargs['reason']}")
    
    if 'source' in kwargs and kwargs['source']:
        log_parts.append(f"Source: {kwargs['source']}")
    
    if 'section' in kwargs and kwargs['section']:
        log_parts.append(f"Section: {kwargs['section']}")
    
    if 'rule_source' in kwargs and kwargs['rule_source']:
        log_parts.append(f"Rule: {kwargs['rule_source']}")
    
    # Add TaskSense-specific structured output
    if 'tasksense_data' in kwargs and kwargs['tasksense_data']:
        ts_data = kwargs['tasksense_data']
        
        # Add confidence scores
        if 'confidence_scores' in ts_data:
            scores = ts_data['confidence_scores']
            if scores:
                score_strs = [f"{label}:{score:.2f}" for label, score in scores.items()]
                log_parts.append(f"Confidence: {{{', '.join(score_strs)}}}")
        
        # Add explanations
        if 'explanations' in ts_data:
            explanations = ts_data['explanations']
            if explanations:
                # Log detailed explanations separately for readability
                for label, explanation in explanations.items():
                    log_parts.append(f"Explanation[{label}]: {explanation}")
        
        # Add processing time
        if 'processing_time' in ts_data:
            log_parts.append(f"ProcessingTime: {ts_data['processing_time']:.3f}s")
        
        # Add mode information
        if 'mode' in ts_data:
            log_parts.append(f"Mode: {ts_data['mode']}")
        
        # Add version tracking
        if 'version' in ts_data:
            log_parts.append(f"Version: {ts_data['version']}")
    
    log_message = " | ".join(log_parts)
    task_logger.info(log_message)

# Using REST API v2 for basic operations (projects, tasks, labels, sections)
# Sync API v9 is used for task movement operations
TODOIST_API = "https://api.todoist.com/rest/v2"

# Check if API token is available
if not os.environ.get('TODOIST_API_TOKEN'):
    print("❌ TODOIST_API_TOKEN environment variable is not set!")
    print("Please set your Todoist API token in your environment variables.")
    exit(1)

HEADERS = {"Authorization": f"Bearer {os.environ['TODOIST_API_TOKEN'].strip()}",
           "Content-Type": "application/json"}

# Domain-to-label mapping for platform-specific tagging
DOMAIN_LABELS = {
    # Social Media
    "x.com": "x",
    "twitter.com": "x", 
    "reddit.com": "reddit",
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "threads.net": "threads",
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "discord.com": "discord",
    "discord.gg": "discord",
    
    # Content/Media
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "medium.com": "medium",
    "substack.com": "substack",
    "twitch.tv": "twitch",
    
    # Development/Tech
    "github.com": "github",
    "stackoverflow.com": "stackoverflow",
    "stackexchange.com": "stackoverflow",
    
    # News/Reading
    "news.ycombinator.com": "hackernews",
    "hn.com": "hackernews",
}


def resolve_redirect(url):
    try:
        r = requests.head(url, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        return r.url
    except Exception:
        return url


def get_domain_label(url):
    """Extract domain from URL and return corresponding label if it exists"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Check if we have a label for this domain
        return DOMAIN_LABELS.get(domain)
    except Exception:
        return None


def extract_all_urls(content):
    """Extract all URLs from task content, handling both plain URLs and markdown links"""
    urls = []
    
    # First, extract markdown links [text](url)
    markdown_links = re.findall(r'\[([^\]]*)\]\((https?://[^\)]+)\)', content)
    for text, url in markdown_links:
        urls.append({
            'url': url,
            'original_text': f'[{text}]({url})',
            'link_text': text,
            'type': 'markdown'
        })
    
    # Then find plain URLs that aren't already in markdown links
    # Remove markdown links from content first to avoid duplicates
    content_without_markdown = re.sub(r'\[([^\]]*)\]\((https?://[^\)]+)\)', '', content)
    plain_urls = re.findall(r'https?://[^\s\]\)]+', content_without_markdown)
    
    for url in plain_urls:
        urls.append({
            'url': url,
            'original_text': url,
            'link_text': None,
            'type': 'plain'
        })
    
    return urls


def process_multiple_links(content, task_logger=None, task_id=None):
    """Process multiple links in content and return updated content with titles"""
    urls = extract_all_urls(content)
    
    if not urls:
        return content, []
    
    updated_content = content
    all_labels = set(['link'])  # Always include the basic link label
    
    # Process each URL and replace with titled version
    for url_info in urls:
        url = url_info['url']
        original_text = url_info['original_text']
        
        if task_logger and task_id:
            task_logger.info(f"Task {task_id} | Processing URL: {url}")
        
        # Fetch title for this URL
        title = fetch_page_title(url)
        
        if title:
            # Create markdown link with title
            new_link = f"[{title}]({url})"
            updated_content = updated_content.replace(original_text, new_link)
            
            if task_logger and task_id:
                title_preview = title[:60] + "..." if len(title) > 60 else title
                task_logger.info(f"Task {task_id} | SUCCESS: Replaced '{original_text[:50]}...' with titled link: {title_preview}")
        else:
            # Log the failed URL for debugging
            if task_logger and task_id:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                task_logger.info(f"Task {task_id} | FAILED: No title found for {domain} - {url[:100]}")
            
            # If no title found, convert plain URL to markdown link with domain as title
            if url_info['type'] == 'plain':
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    fallback_link = f"[{domain}]({url})"
                    updated_content = updated_content.replace(original_text, fallback_link)
                    
                    if task_logger and task_id:
                        task_logger.info(f"Task {task_id} | FALLBACK: Used domain fallback: {domain}")
                except Exception:
                    pass
        
        # Collect domain labels
        domain_label = get_domain_label(url)
        if domain_label:
            all_labels.add(domain_label)
    
    return updated_content, list(all_labels)

def is_plain_url(text):
    # Normalize line breaks and spaces
    text = text.strip().replace("\n", "").replace(" ", "")
    return re.fullmatch(r'https?://\S+', text) is not None


def is_good_title(title):
    """Check if a title is worth using (not generic, not error page, etc.)"""
    if not title or len(title.strip()) < 3:
        return False
    
    title_lower = title.lower()
    bad_patterns = [
        "page not found", "404", "403", "500", "error",
        "twitter / x", "attention required", "just a moment",
        "loading", "please wait", "redirecting",
        "access denied", "forbidden", "not found",
        "untitled", "no title", "blocked", "unavailable"
    ]
    
    # Check for bad patterns
    if any(bad in title_lower for bad in bad_patterns):
        return False
    
    # Check for overly generic titles
    generic_patterns = [
        r"^(home|welcome|index)$",
        r"^(github|youtube|medium|twitter|facebook|linkedin)$",
        r"^.*\s*-\s*(github|youtube|medium|twitter|facebook|linkedin)$"
    ]
    
    for pattern in generic_patterns:
        if re.match(pattern, title_lower):
            return False
    
    return True


def clean_title(title):
    """Clean up and truncate titles to reasonable length"""
    title = title.strip()
    
    # Remove common suffixes that add noise
    suffixes_to_remove = [
        " - YouTube", " | YouTube", 
        " | Hacker News", " - Hacker News",
        " | GitHub", " - GitHub",
        " | Medium", " - Medium",
        " | LinkedIn", " - LinkedIn",
        " | Facebook", " - Facebook",
        " | Twitter", " - Twitter"
    ]
    
    for suffix in suffixes_to_remove:
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
            break
    
    # Truncate very long titles
    if len(title) > 100:
        # Try to break at a natural point (sentence, clause)
        for break_char in ['.', '!', '?', ':', ';', ' - ', ' | ']:
            idx = title.find(break_char, 50)  # Look for break after 50 chars
            if idx > 0 and idx < 90:  # But before 90 chars
                title = title[:idx].strip()
                break
        else:
            # No natural break found, truncate at word boundary
            title = title[:97].rsplit(' ', 1)[0] + "..."
    
    return title


def get_inbox_project_id():
    r = requests.get(f"{TODOIST_API}/projects", headers=HEADERS)
    r.raise_for_status()
    for project in r.json():
        if project['name'].lower() == 'inbox':
            return project['id']
    raise Exception("Inbox project not found")


def fetch_tasks(project_id):
    r = requests.get(f"{TODOIST_API}/tasks?project_id={project_id}", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def fetch_page_title(url):
    # Fixed variable scope and Reddit blocking issues - v3
    url = resolve_redirect(url)  # Handle shortlink redirects (e.g. Reddit /s/)
    try:
        # Special handling for Reddit links: try JSON API first, then fallback to old-reddit HTML
        if "reddit.com" in url:
            # Better User-Agent that looks like a real browser
            reddit_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            m = re.match(r'https?://(?:www\.)?reddit\.com/r/([^/]+)/s/([^/?#]+)', url)
            if m:
                subreddit, postid = m.groups()
            else:
                m2 = re.match(r'https?://(?:www\.)?reddit\.com/r/([^/]+)/comments/([^/]+)/', url)
                if m2:
                    subreddit, postid = m2.groups()
                else:
                    subreddit = postid = None

            if subreddit and postid:
                # Skip JSON API since Reddit is blocking it completely
                # Go straight to HTML scraping approaches
                
                # 1) Try old Reddit with better headers and session
                try:
                    session = requests.Session()
                    session.headers.update(reddit_headers)
                    html_url = f"https://old.reddit.com/r/{subreddit}/comments/{postid}"
                    resp = session.get(html_url, timeout=15)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    if soup.title and soup.title.string:
                        title = soup.title.string.split(" : ")[0].strip()
                        if title.lower() not in ["blocked", "page not found", "reddit"]:
                            # Success! Add subreddit context to title
                            return f"{title} (r/{subreddit})"
                except Exception as e:
                    pass
                
                # 2) Try alternative old reddit approach without www
                try:
                    no_www_url = url.replace("www.reddit.com", "reddit.com").replace("reddit.com", "old.reddit.com")
                    resp = requests.get(no_www_url, headers=reddit_headers, timeout=15)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    if soup.title and soup.title.string:
                        title = soup.title.string.split(" : ")[0].strip()
                        if title.lower() not in ["blocked", "page not found", "reddit"]:
                            return f"{title} (r/{subreddit})"
                except Exception as e:
                    pass
            
            # If all else fails, return a generic Reddit title
            return f"Reddit Post in r/{subreddit}" if subreddit else "Reddit Post"

        # Special handling for Instagram links
        if "instagram.com" in url:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Try Open Graph title first (often contains the caption)
            og = soup.find("meta", property="og:title")
            if og and og.get("content"):
                title = og["content"].strip()
                if title and title.lower() not in ["instagram", "page not found"]:
                    return title
            
            # Try Open Graph description (contains caption text)
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = og_desc["content"].strip()
                if desc and len(desc) > 10 and "instagram" not in desc.lower():
                    # Truncate long descriptions to reasonable length
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    return desc
            
            # Try Twitter card description
            twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})
            if twitter_desc and twitter_desc.get("content"):
                desc = twitter_desc["content"].strip()
                if desc and len(desc) > 10 and "instagram" not in desc.lower():
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    return desc
                    
            # Fallback to just "Instagram Reel" or "Instagram Post"
            if "/reel/" in url:
                return "Instagram Reel"
            else:
                return "Instagram Post"

        # Generic fallback: HTML <title>
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Try Open Graph title first (often cleaner than HTML title)
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            title = og["content"].strip()
            if is_good_title(title):
                return clean_title(title)
        
        # Try HTML title
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            if is_good_title(title):
                return clean_title(title)
        
        # Try Twitter card title
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content"):
            title = twitter_title["content"].strip()
            if is_good_title(title):
                return clean_title(title)

    except Exception as e:
        # Only log unexpected errors, not common blocking issues
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc
            error_str = str(e).lower()
            # Don't spam logs with common blocking errors
            if not any(x in error_str for x in ['blocked', 'forbidden', '403', '401', 'timeout', 'connection', 'ssl']):
                log_warning(f"Unexpected error fetching title for {domain}: {str(e)}")
        except:
            pass
    return None


def get_label_id(label_name="link"):
    r = requests.get(f"{TODOIST_API}/labels", headers=HEADERS)
    r.raise_for_status()
    for label in r.json():
        if label['name'].lower() == label_name:
            return label['id']
    # Create the label if not found
    create_resp = requests.post(f"{TODOIST_API}/labels", headers=HEADERS, json={"name": label_name})
    if create_resp.status_code in (200, 201):
        label_data = create_resp.json()
        return label_data['id']
    else:
        return None


def update_task(task, title=None, url=None, labels_to_add=None, summary=None, dry_run=False, new_content=None):
    payload = {}
    
    # Ensure labels_to_add is a list
    if labels_to_add is None:
        labels_to_add = []
    elif isinstance(labels_to_add, str):
        labels_to_add = [labels_to_add]

    # Handle different content update scenarios
    if new_content:
        # Direct content replacement (for multiple links)
        payload["content"] = new_content
    elif title and url:
        # Single title/URL replacement
        payload["content"] = f"[{title}]({url})"
    elif labels_to_add:
        # For label-only updates, include content but add a description to force update
        payload["content"] = task["content"]
        payload["description"] = task.get("description", "")

    if labels_to_add:
        existing_labels = task.get("labels", [])
        # Only add labels that don't already exist
        new_labels = [label for label in labels_to_add if label not in existing_labels]
        if new_labels:
            payload["labels"] = list(set(existing_labels + new_labels))

    if not payload:
        if summary:
            summary.skipped("empty payload")
        return False

    # In dry run mode, just preview the changes
    if dry_run:
        log_info("🔍 DRY RUN - Would update task:", "cyan")
        log_info(f"   Task ID: {task['id']}")
        log_info(f"   Current: {task['content']}")
        if new_content:
            log_info(f"   New content: {new_content}", "green")
        elif title and url:
            log_info(f"   New content: {payload['content']}", "green")
        if labels_to_add:
            current_labels = task.get("labels", [])
            new_labels_result = payload.get("labels", current_labels)
            if new_labels_result != current_labels:
                log_info(f"   Labels: {current_labels} → {new_labels_result}", "blue")
        return True

    # Actually make the API call
    r = requests.post(f"{TODOIST_API}/tasks/{task['id']}", headers=HEADERS, json=payload)
    if r.status_code in (200, 204):
        return True

    error_msg = f"API error {r.status_code}"
    if summary:
        summary.failed(error_msg)
    return False


def ensure_today_section_exists(project_id, config, task_logger=None):
    """
    Ensure Today section exists in the project, create if missing.
    
    Args:
        project_id: Todoist project ID
        config: Ranking configuration containing section settings
        task_logger: Logger for task operations
        
    Returns:
        str: Section ID if successful, None if failed
    """
    section_config = config.get('sections', {})
    today_section_name = section_config.get('today_section', 'Today')
    create_if_missing = section_config.get('create_if_missing', True)
    
    try:
        # Check if Today section already exists
        sections = get_project_sections(project_id, task_logger)
        if today_section_name in sections:
            section_id = sections[today_section_name]
            if task_logger:
                task_logger.info(f"TODAY_SECTION_EXISTS: Found existing '{today_section_name}' section (ID: {section_id})")
            return section_id
        
        # Create Today section if missing and configured to do so
        if create_if_missing:
            section_id = create_section_if_missing_sync(today_section_name, project_id, task_logger)
            if section_id:
                if task_logger:
                    task_logger.info(f"TODAY_SECTION_CREATED: Created '{today_section_name}' section (ID: {section_id})")
                log_info(f"📁 Created 'Today' section in project")
                return section_id
            else:
                if task_logger:
                    task_logger.error(f"TODAY_SECTION_CREATE_FAILED: Failed to create '{today_section_name}' section")
                return None
        else:
            if task_logger:
                task_logger.warning(f"TODAY_SECTION_MISSING: '{today_section_name}' section not found and creation disabled")
            return None
            
    except Exception as e:
        if task_logger:
            task_logger.error(f"TODAY_SECTION_ERROR: Error ensuring Today section exists: {e}")
        log_warning(f"Failed to ensure Today section exists: {e}")
        return None


def apply_today_markers(ranked_tasks, config, task_logger=None, dry_run=False, bulk_mode=False):
    """
    Apply today markers to ranked tasks (due date = today + optional label).
    
    Args:
        ranked_tasks: List of ranked task objects from TaskSense.rank()
        config: Ranking configuration containing today marker settings
        task_logger: Logger for task operations
        dry_run: If True, only simulate marker application
        bulk_mode: Enable bulk processing rate limiting
        
    Returns:
        int: Number of tasks successfully marked
    """
    today_config = config.get('today_markers', {})
    use_due_date = today_config.get('use_due_date', True)
    use_label = today_config.get('use_label', False)
    today_marker = today_config.get('label_name', '@today')
    
    if not ranked_tasks:
        return 0
    
    marked_count = 0
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # Get today label ID if we're using labels
        today_label_id = None
        if use_label:
            labels_response = requests.get(f"{TODOIST_API}/labels", headers=HEADERS)
            labels_response.raise_for_status()
            existing_labels = {label['name']: label['id'] for label in labels_response.json()}
            
            today_label_id = existing_labels.get(today_marker)
            if not today_label_id and not dry_run:
                today_label_id = create_label_if_missing(today_marker, task_logger)
                if not today_label_id:
                    if task_logger:
                        task_logger.error(f"TODAY_LABEL_CREATE_FAILED: Failed to create '{today_marker}' label")
                    use_label = False  # Continue without labels
        
        # Apply today markers to each ranked task
        for ranked_task in ranked_tasks:
            task_data = ranked_task['task']
            task_id = task_data.get('id')
            task_content = task_data.get('content', 'No content')[:50]
            
            if not task_id:
                continue
            
            # Check current state
            current_due = task_data.get('due')
            current_due_date = current_due.get('date') if current_due else None
            current_labels = set(task_data.get('labels', []))
            
            # Determine what updates are needed
            updates_needed = {}
            actions_taken = []
            
            # 1. Set due date to today if enabled and not already set
            if use_due_date and current_due_date != today_date:
                updates_needed['due_string'] = 'today'
                actions_taken.append('due_date')
            
            # 2. Add @today label if enabled and not already present
            if use_label and today_label_id and str(today_label_id) not in current_labels:
                updates_needed['labels'] = list(current_labels) + [today_label_id]
                actions_taken.append('label')
            
            # Skip if no updates needed
            if not updates_needed:
                if task_logger:
                    task_logger.info(f"TODAY_MARKER_SKIP: Task {task_id} already marked for today")
                continue
            
            if dry_run:
                if task_logger:
                    actions_str = '+'.join(actions_taken)
                    task_logger.info(f"TODAY_MARKER_DRY_RUN: Would apply {actions_str} to task {task_id}")
                marked_count += 1
            else:
                # Apply updates via API
                try:
                    response = requests.post(f"{TODOIST_API}/tasks/{task_id}", headers=HEADERS, json=updates_needed)
                    
                    if response.status_code == 200:
                        marked_count += 1
                        actions_str = '+'.join(actions_taken)
                        if task_logger:
                            task_logger.info(f"TODAY_MARKER_APPLIED: Applied {actions_str} to task {task_id} | Content: {task_content}")
                    else:
                        if task_logger:
                            task_logger.error(f"TODAY_MARKER_FAILED: Failed to apply today markers to task {task_id} (HTTP {response.status_code})")
                            
                    # Rate limiting for bulk mode
                    if bulk_mode:
                        import time
                        time.sleep(0.1)
                        
                except Exception as e:
                    if task_logger:
                        task_logger.error(f"TODAY_MARKER_ERROR: Error applying today markers to task {task_id}: {e}")
                    
    except Exception as e:
        if task_logger:
            task_logger.error(f"TODAY_MARKERS_ERROR: Error in apply_today_markers: {e}")
        log_warning(f"Failed to apply today markers: {e}")
        
    return marked_count


def clear_today_section(project_id, section_id, config, task_logger=None, dry_run=False, bulk_mode=False):
    """
    Clear tasks from Today section by removing @today labels and moving back to backlog.
    
    Args:
        project_id: Todoist project ID
        section_id: Today section ID  
        config: Ranking configuration containing label settings
        task_logger: Logger for task operations
        dry_run: If True, only simulate clearing
        bulk_mode: Enable bulk processing rate limiting
        
    Returns:
        int: Number of tasks cleared from Today section
    """
    if not section_id:
        return 0
    
    cleared_count = 0
    
    try:
        # Get all tasks in Today section
        response = requests.get(f"{TODOIST_API}/tasks?project_id={project_id}&section_id={section_id}", headers=HEADERS)
        response.raise_for_status()
        today_tasks = response.json()
        
        if not today_tasks:
            if task_logger:
                task_logger.info("TODAY_CLEAR_EMPTY: Today section is already empty")
            return 0
        
        label_config = config.get('labels', {})
        today_marker = label_config.get('today_marker', '@today')
        
        # Get @today label ID
        labels_response = requests.get(f"{TODOIST_API}/labels", headers=HEADERS)
        labels_response.raise_for_status()
        existing_labels = {label['name']: label['id'] for label in labels_response.json()}
        today_label_id = existing_labels.get(today_marker)
        
        for task in today_tasks:
            task_id = task.get('id')
            task_content = task.get('content', 'No content')[:50]
            
            if not task_id:
                continue
            
            if dry_run:
                if task_logger:
                    task_logger.info(f"TODAY_CLEAR_DRY_RUN: Would clear task {task_id} from Today section | Content: {task_content}")
                cleared_count += 1
            else:
                try:
                    # Remove @today label if present
                    current_labels = set(task.get('labels', []))
                    if today_label_id and str(today_label_id) in current_labels:
                        new_labels = [label for label in current_labels if str(label) != str(today_label_id)]
                        update_data = {"labels": new_labels}
                        label_response = requests.post(f"{TODOIST_API}/tasks/{task_id}", headers=HEADERS, json=update_data)
                        
                        if label_response.status_code != 200:
                            if task_logger:
                                task_logger.error(f"TODAY_CLEAR_LABEL_FAILED: Failed to remove @today label from task {task_id}")
                    
                    # Move task out of Today section (back to no section/backlog)
                    move_data = {"section_id": None}
                    move_response = requests.post(f"{TODOIST_API}/tasks/{task_id}", headers=HEADERS, json=move_data)
                    
                    if move_response.status_code == 200:
                        cleared_count += 1
                        if task_logger:
                            task_logger.info(f"TODAY_CLEAR_SUCCESS: Cleared task {task_id} from Today section | Content: {task_content}")
                    else:
                        if task_logger:
                            task_logger.error(f"TODAY_CLEAR_MOVE_FAILED: Failed to move task {task_id} out of Today section")
                    
                    # Rate limiting for bulk mode
                    if bulk_mode:
                        import time
                        time.sleep(0.1)
                        
                except Exception as e:
                    if task_logger:
                        task_logger.error(f"TODAY_CLEAR_ERROR: Error clearing task {task_id}: {e}")
        
        if cleared_count > 0:
            if task_logger:
                task_logger.info(f"TODAY_CLEAR_COMPLETE: Cleared {cleared_count} tasks from Today section")
        
    except Exception as e:
        if task_logger:
            task_logger.error(f"TODAY_CLEAR_ERROR: Error clearing Today section: {e}")
        log_warning(f"Failed to clear Today section: {e}")
    
    return cleared_count


def move_tasks_to_today_section(ranked_tasks, project_id, section_id, task_logger=None, dry_run=False, bulk_mode=False):
    """
    Move ranked tasks to Today section.
    
    Args:
        ranked_tasks: List of ranked task objects from TaskSense.rank()
        project_id: Todoist project ID  
        section_id: Today section ID
        task_logger: Logger for task operations
        dry_run: If True, only simulate task movement
        bulk_mode: Enable bulk processing rate limiting
        
    Returns:
        int: Number of tasks successfully moved
    """
    if not ranked_tasks or not section_id:
        return 0
    
    moved_count = 0
    
    for ranked_task in ranked_tasks:
        task_data = ranked_task['task']
        task_id = task_data.get('id')
        task_content = task_data.get('content', 'No content')[:50]
        current_section = task_data.get('section_id')
        
        if not task_id:
            continue
            
        # Skip if task is already in Today section
        if current_section == section_id:
            if task_logger:
                task_logger.info(f"TODAY_MOVE_SKIP: Task {task_id} already in Today section")
            continue
        
        if dry_run:
            if task_logger:
                task_logger.info(f"TODAY_MOVE_DRY_RUN: Would move task {task_id} to Today section | Content: {task_content}")
            moved_count += 1
        else:
            # Move task to Today section
            success = move_task_to_section(task_id, section_id, task_logger, task_content, bulk_mode)
            if success:
                moved_count += 1
                if task_logger:
                    task_logger.info(f"TODAY_MOVE_SUCCESS: Moved task {task_id} to Today section | Content: {task_content}")
            else:
                if task_logger:
                    task_logger.error(f"TODAY_MOVE_FAILED: Failed to move task {task_id} to Today section")
    
    return moved_count


def main(test_mode=False):
    summary = TaskSummary()
    task_logger = setup_task_logging()
    
    # Parse CLI arguments first
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=str, help="Comma-separated list of project names to process")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying any tasks")
    parser.add_argument("--full-scan", action="store_true", help="Process all tasks, ignoring last run timestamp")
    parser.add_argument("--mode", type=str, choices=['personal', 'work', 'weekend', 'evening', 'auto'], 
                        help="Set TaskSense mode (personal, work, weekend, evening, auto)")
    parser.add_argument("--label-task", type=str, help="Label a single task and exit (requires --mode)")
    parser.add_argument("--tasksense-mock", action="store_true", help="Enable TaskSense mock mode for testing")
    parser.add_argument("--confidence-threshold", type=float, help="Minimum confidence threshold for label acceptance (0.0-1.0)")
    parser.add_argument("--soft-matching", action="store_true", help="Enable soft matching for labels not in available_labels")
    parser.add_argument("--bulk-mode", action="store_true", help="Enable bulk processing mode with extra rate limiting for large task volumes")
    parser.add_argument("--fix-sections", action="store_true", help="Force section routing for tasks with labels but missing section assignments")
    
    # Phase 4: Ranking and Today list generation
    parser.add_argument("--generate-today", action="store_true", help="Generate today's prioritized task list using TaskSense ranking")
    parser.add_argument("--limit", type=int, default=3, help="Number of tasks to select for today (default: 3)")
    parser.add_argument("--refresh-today", action="store_true", help="Clear and regenerate today's task list")
    
    args, _ = parser.parse_known_args()
    
    # Load unified configuration (CLI flags → env vars → task_sense_config → rules.json fallback)
    rules, gpt_fallback, tasksense_config = load_unified_config()
    
    # Apply CLI overrides to TaskSense config
    if args.tasksense_mock and tasksense_config:
        if "mock_mode" not in tasksense_config:
            tasksense_config["mock_mode"] = {}
        tasksense_config["mock_mode"]["enabled"] = True
        log_info("🎭 TaskSense mock mode enabled via CLI flag")

    # Handle standalone task labeling
    if args.label_task:
        if not args.mode:
            log_error("❌ --label-task requires --mode to be specified")
            return
        
        # Initialize TaskSense with specified mode
        if TASKSENSE_AVAILABLE:
            try:
                # Initialize TaskSense with updated config
                if tasksense_config:
                    task_sense = TaskSense(config_path=None)
                    task_sense.config = tasksense_config
                else:
                    task_sense = TaskSense()
                
                # Use auto mode detection if specified
                if args.mode == 'auto':
                    from task_sense_prompts import TaskSensePrompts
                    prompts = TaskSensePrompts()
                    detected_mode = prompts.get_time_based_mode(tasksense_config)
                    actual_mode = detected_mode
                else:
                    actual_mode = args.mode
                
                # Get labels for the task
                result = task_sense.label(args.label_task, dry_run=args.dry_run, mode=actual_mode)
                
                if result and result.get('labels'):
                    labels = result['labels']
                    explanation = result.get('explanation', '')
                    confidence = result.get('confidence', 0.8)
                    
                    if HAS_RICH:
                        console.print(f"\n📝 Task: {args.label_task}", style="bold")
                        console.print(f"🎯 Mode: {actual_mode}", style="blue")
                        console.print(f"🏷️  Labels: {', '.join(labels)}", style="green")
                        console.print(f"💡 Explanation: {explanation}", style="dim")
                        console.print(f"🎯 Confidence: {confidence:.2f}", style="cyan")
                    else:
                        print(f"\n📝 Task: {args.label_task}")
                        print(f"🎯 Mode: {actual_mode}")
                        print(f"🏷️  Labels: {', '.join(labels)}")
                        print(f"💡 Explanation: {explanation}")
                        print(f"🎯 Confidence: {confidence:.2f}")
                else:
                    log_error("❌ No labels suggested for the task")
                    
            except Exception as e:
                log_error(f"❌ TaskSense error: {str(e)}")
        else:
            log_error("❌ TaskSense not available")
        
        return

    if args.project:
        project_names = [name.strip().lower() for name in args.project.split(",")]
    elif os.getenv("PROJECT_NAMES"):
        env_projects_raw = os.getenv("PROJECT_NAMES")
        project_names = [name.strip().lower() for name in env_projects_raw.split(",")]
    else:
        project_names = ["inbox"]
    
    try:
        projects_response = requests.get(f"{TODOIST_API}/projects", headers=HEADERS)
        task_logger.info(f"API Response Status: {projects_response.status_code}")
        task_logger.info(f"API Response Headers: {dict(projects_response.headers)}")
        task_logger.info(f"API Response Content (first 500 chars): {projects_response.text[:500]}")
        
        projects_response.raise_for_status()
        all_projects = projects_response.json()
    except requests.exceptions.JSONDecodeError:
        log_error("❌ Failed to parse Todoist API response. Check your TODOIST_API_TOKEN.")
        log_error(f"Response status: {projects_response.status_code}")
        log_error(f"Response content: {projects_response.text[:500]}")
        task_logger.error("API Error: Invalid JSON response from Todoist API - likely invalid token")
        task_logger.error(f"Response status: {projects_response.status_code}")
        task_logger.error(f"Response content: {projects_response.text[:500]}")
        return
    except requests.exceptions.HTTPError as e:
        log_error(f"❌ Todoist API HTTP error: {e}")
        log_error(f"Response content: {projects_response.text[:500]}")
        task_logger.error(f"API Error: HTTP {projects_response.status_code} - {e}")
        task_logger.error(f"Response content: {projects_response.text[:500]}")
        return
    except Exception as e:
        log_error(f"❌ Failed to fetch projects: {e}")
        task_logger.error(f"API Error: {e}")
        return
    
    project_ids = [p["id"] for p in all_projects if p["name"].strip().lower() in project_names]
    if not project_ids:
        log_warning("No matching projects found")
        return

    # Get last run timestamp for incremental processing
    last_run_time = None
    force_full_scan = args.full_scan or os.getenv("FORCE_FULL_SCAN", "").lower() in ("true", "1", "yes")
    if not force_full_scan and not test_mode:
        last_run_time = get_last_run_timestamp()
    
    # Log session start
    mode_info = []
    if test_mode:
        mode_info.append("TEST")
    if args.dry_run:
        mode_info.append("DRY_RUN")
    if args.verbose:
        mode_info.append("VERBOSE")
    if force_full_scan:
        mode_info.append("FULL_SCAN")
    elif last_run_time:
        mode_info.append("INCREMENTAL")
    
    mode_str = f"[{', '.join(mode_info)}]" if mode_info else "[NORMAL]"
    # Log masked token for debugging (show first 8 and last 4 chars)
    token = os.environ.get('TODOIST_API_TOKEN', '')
    masked_token = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "TOKEN_TOO_SHORT"
    task_logger.info(f"=== SESSION START {mode_str} ===")
    task_logger.info(f"Using API token: {masked_token}")
    task_logger.info(f"Token length: {len(token)}")
    task_logger.info(f"Token has whitespace: {token != token.strip()}")
    task_logger.info(f"Authorization header: Bearer {token[:8]}...{token[-4:] if len(token) > 12 else 'SHORT'}")
    
    if last_run_time:
        task_logger.info(f"Last run timestamp: {last_run_time}")
        log_info(f"🕒 Processing tasks created after: {last_run_time.strftime('%Y-%m-%d %H:%M:%S UTC')}", "cyan")

    if test_mode:
        log_info("🧪 Running in test mode...")
        test_links = [
            "https://www.reddit.com/r/ChatGPTPro/s/8PeCrJRzI8",
            "https://www.toughtongueai.com/",
            "https://open.substack.com/pub/thegeneralist/p/the-generalists-productivity-stack"
        ]
        for url in test_links:
            title = fetch_page_title(url)
            log_info(f"🔗 {url} → {title or 'Failed to fetch title'}")
            task_logger.info(f"TEST | URL: {url} | Title: {title or 'FAILED'}")
        task_logger.info("=== TEST SESSION END ===")
        return  # Exit after test mode

    if not test_mode:
        tasks = []
        for pid in project_ids:
            tasks.extend(fetch_tasks(pid))

        if not tasks:
            log_info("ℹ️  No tasks found in specified projects")
            return

        # Add dry run header
        if args.dry_run:
            log_info("🧪 DRY RUN MODE - No changes will be made to your tasks", "yellow")
            log_info("=" * 60, "yellow")

        # Filter tasks based on incremental processing logic
        tasks_to_process = []
        skipped_count = 0
        
        for task in tasks:
            if last_run_time:
                should_process, reason = should_process_task(task, last_run_time, task_logger, args.fix_sections, rules)
                if should_process:
                    tasks_to_process.append(task)
                else:
                    skipped_count += 1
                    summary.skipped(reason)
            else:
                tasks_to_process.append(task)
        
        log_info(f"🔍 Found {len(tasks)} total tasks, processing {len(tasks_to_process)} tasks from {len(project_ids)} project(s)...")
        if skipped_count > 0:
            log_info(f"⏭️  Skipped {skipped_count} tasks (already processed or no changes needed)", "yellow")
        
        # Count domains being processed
        domain_count = {}
        for task in tasks_to_process:
            urls = extract_all_urls(task['content'])
            for url_info in urls:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url_info['url']).netloc.lower()
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    domain_count[domain] = domain_count.get(domain, 0) + 1
                except:
                    pass
        
        if domain_count:
            top_domains = sorted(domain_count.items(), key=lambda x: x[1], reverse=True)[:5]
            domain_summary = ", ".join([f"{domain}({count})" for domain, count in top_domains])
            log_info(f"🌐 Top domains: {domain_summary}")
        
        task_logger.info(f"Processing {len(tasks_to_process)}/{len(tasks)} tasks from projects: {[p['name'] for p in all_projects if p['id'] in project_ids]}")
        task_logger.info(f"Domain breakdown: {domain_count}")

        # Determine TaskSense mode for this session
        current_mode = None
        if args.mode:
            if args.mode == 'auto':
                # Auto-detect mode based on time
                if TASKSENSE_AVAILABLE:
                    try:
                        from task_sense_prompts import TaskSensePrompts
                        prompts = TaskSensePrompts()
                        current_mode = prompts.get_time_based_mode(tasksense_config)
                        task_logger.info(f"TaskSense auto-detected mode: {current_mode}")
                    except Exception as e:
                        task_logger.warning(f"Failed to auto-detect mode: {e}, using default")
                        current_mode = None
            else:
                current_mode = args.mode
                task_logger.info(f"TaskSense mode set to: {current_mode}")
        
        # Add mode to session info
        if current_mode:
            log_info(f"🎯 TaskSense mode: {current_mode}")

        # Phase 4: Handle ranking and today list generation
        if args.generate_today:
            if TASKSENSE_AVAILABLE:
                try:
                    # Initialize TaskSense with ranking config
                    task_sense = TaskSense()
                    
                    # Use CLI mode or default
                    ranking_mode = current_mode or task_sense.config.get('default_mode', 'personal')
                    
                    # Get ranking limit from CLI or config
                    ranking_limit = args.limit or task_sense.ranking_config.get('default_limit', 3)
                    
                    log_info(f"🎯 Generating today's task list (mode: {ranking_mode}, limit: {ranking_limit})")
                    task_logger.info(f"RANKING_START: Mode={ranking_mode}, Limit={ranking_limit}, Tasks={len(tasks_to_process)}")
                    
                    # Run ranking on all available tasks
                    ranked_tasks = task_sense.rank(tasks_to_process, mode=ranking_mode, limit=ranking_limit)
                    
                    if ranked_tasks:
                        if args.dry_run:
                            log_info("🧪 DRY RUN: Today's prioritized tasks would be:", "yellow")
                        else:
                            log_info("🎯 Today's prioritized tasks:")
                        
                        # Display ranked results
                        for i, ranked_task in enumerate(ranked_tasks, 1):
                            task_data = ranked_task['task']
                            score = ranked_task['score']
                            explanation = ranked_task['explanation']
                            task_content = task_data.get('content', 'No content')[:60]
                            if len(task_data.get('content', '')) > 60:
                                task_content += "..."
                            
                            if HAS_RICH:
                                console.print(f"  {i}. [{score:.2f}] {task_content}", style="green")
                                console.print(f"      💡 {explanation}", style="dim")
                            else:
                                print(f"  {i}. [{score:.2f}] {task_content}")
                                print(f"      💡 {explanation}")
                        
                        # Today section management
                        today_section_id = None
                        labeled_count = 0
                        moved_count = 0
                        
                        # Get project ID from first ranked task
                        if ranked_tasks:
                            project_id = ranked_tasks[0]['task'].get('project_id')
                            if project_id:
                                # Ensure Today section exists
                                today_section_id = ensure_today_section_exists(project_id, task_sense.ranking_config, task_logger)
                                
                                if today_section_id:
                                    # Clear Today section if refresh requested
                                    if args.refresh_today:
                                        cleared_count = clear_today_section(
                                            project_id, today_section_id, task_sense.ranking_config,
                                            task_logger, args.dry_run, args.bulk_mode
                                        )
                                        if cleared_count > 0:
                                            if args.dry_run:
                                                log_info(f"🧪 DRY RUN: Would clear {cleared_count} existing tasks from Today section", "yellow")
                                            else:
                                                log_info(f"🧹 Cleared {cleared_count} existing tasks from Today section")
                                            task_logger.info(f"TODAY_REFRESH: Cleared {cleared_count} tasks from Today section")
                                        else:
                                            log_info("🧹 Today section was already empty")
                                
                                    # Move tasks to Today section
                                    moved_count = move_tasks_to_today_section(
                                        ranked_tasks, project_id, today_section_id, 
                                        task_logger, args.dry_run, args.bulk_mode
                                    )
                                    
                                    # Apply today markers (due date + optional label)
                                    labeled_count = apply_today_markers(
                                        ranked_tasks, task_sense.ranking_config,
                                        task_logger, args.dry_run, args.bulk_mode
                                    )
                                else:
                                    log_warning("⚠️  Could not create/find Today section, skipping section management")
                                    task_logger.warning("TODAY_SECTION_UNAVAILABLE: Skipping section and label management")
                            else:
                                log_warning("⚠️  No project ID found in ranked tasks")
                                task_logger.warning("TODAY_NO_PROJECT_ID: Cannot perform section management without project ID")
                        
                        # Final success message
                        if not args.dry_run:
                            success_parts = [f"Selected {len(ranked_tasks)} tasks for today's focus"]
                            if moved_count > 0:
                                success_parts.append(f"moved {moved_count} to Today section")
                            if labeled_count > 0:
                                success_parts.append(f"marked {labeled_count} for today")
                            
                            success_msg = "✅ " + ", ".join(success_parts)
                            log_success(success_msg)
                            task_logger.info(f"RANKING_COMPLETE: Selected={len(ranked_tasks)}, Moved={moved_count}, Labeled={labeled_count}")
                        else:
                            dry_run_parts = [f"Would select {len(ranked_tasks)} tasks for today"]
                            if moved_count > 0:
                                dry_run_parts.append(f"move {moved_count} to Today section")
                            if labeled_count > 0:
                                dry_run_parts.append(f"mark {labeled_count} for today")
                            
                            dry_run_msg = "🧪 DRY RUN: " + ", ".join(dry_run_parts)
                            log_info(dry_run_msg, "yellow")
                    else:
                        log_info("ℹ️  No tasks qualified for today's ranking")
                        task_logger.info("RANKING_EMPTY: No tasks qualified for ranking")
                    
                    # Exit early if only doing ranking (skip normal labeling pipeline)
                    if args.generate_today:
                        task_logger.info("=== RANKING SESSION END ===")
                        return
                        
                except Exception as e:
                    log_error(f"❌ Ranking failed: {str(e)}")
                    task_logger.error(f"RANKING_ERROR: {str(e)}")
                    return
            else:
                log_error("❌ TaskSense not available for ranking")
                task_logger.error("RANKING_ERROR: TaskSense not available")
                return

        # Create labeling pipeline
        if PIPELINE_AVAILABLE:
            pipeline = PipelineFactory.create_from_config(
                rules=rules,
                gpt_fallback=gpt_fallback,
                tasksense_config=tasksense_config,
                cli_args=args,
                logger=task_logger
            )
            
            log_info(f"📋 Using LabelingPipeline for task processing")
            
            # Process tasks using pipeline
            pipeline_results = []
            total_tasks = len(tasks_to_process)
            
            for i, task in enumerate(tasks_to_process, 1):
                # Show progress for bulk processing
                if total_tasks > 10:
                    log_info(f"📋 Processing task {i}/{total_tasks}: {task['content'][:40]}{'...' if len(task['content']) > 40 else ''}")
                elif args.verbose:
                    log_info(f"📋 Processing: {task['content'][:50]}{'...' if len(task['content']) > 50 else ''}")
                
                # Run pipeline
                result = pipeline.run(task)
                pipeline_results.append(result)
                
                # Handle pre-labeled task routing in fix-sections mode
                if args.fix_sections and not result.labels_applied:
                    # Task didn't get new labels from pipeline, but might need section routing for existing labels
                    route_success = route_pre_labeled_task(task, rules, task_logger, args.dry_run, args.bulk_mode)
                    if route_success and args.verbose:
                        log_success(f"🔄 Routed pre-labeled task to correct section")
                
                # Update summary based on pipeline results
                if result.success and result.labels_applied:
                    # Track labels for summary
                    for label in result.labels_applied:
                        if label in result.domain_labels and label != 'link':
                            summary.labeled(label)  # Domain-specific label
                        else:
                            summary.labeled()  # Rule-based or GPT label
                    
                    if args.verbose and not args.dry_run:
                        log_success(f"🏷️  Tagged task with labels: {result.labels_applied}")
                    
                    # Enhanced logging with TaskSense data
                    action = "LABELED_DRY_RUN" if args.dry_run else "LABELED"
                    first_url = result.urls_found[0]['url'] if result.urls_found else None
                    label_sources = result.get_label_sources()
                    
                    # Prepare TaskSense data for logging
                    tasksense_data = {
                        'confidence_scores': result.confidence_scores,
                        'explanations': result.explanations,
                        'processing_time': result.processing_time,
                        'mode': current_mode,
                        'version': 'pipeline_v1.0'
                    }
                    
                    log_task_action(task_logger, task['id'], task['content'], action, 
                                  labels=result.labels_applied, 
                                  url=first_url, 
                                  source=','.join(set(label_sources.values())),
                                  tasksense_data=tasksense_data)
                elif not result.success:
                    # Log failure with TaskSense data
                    tasksense_data = {
                        'processing_time': result.processing_time,
                        'mode': current_mode,
                        'version': 'pipeline_v1.0'
                    }
                    log_task_action(task_logger, task['id'], task['content'], "FAILED",
                                  error=result.error, tasksense_data=tasksense_data)
                else:
                    # Log no labels with TaskSense data
                    tasksense_data = {
                        'confidence_scores': result.confidence_scores,
                        'explanations': result.explanations,
                        'processing_time': result.processing_time,
                        'mode': current_mode,
                        'version': 'pipeline_v1.0'
                    }
                    
                    if result.get_all_labels():
                        log_task_action(task_logger, task['id'], task['content'], "LABELS_MATCHED_NO_NEW",
                                      reason="all matching labels already exist", tasksense_data=tasksense_data)
                    else:
                        log_task_action(task_logger, task['id'], task['content'], "NO_LABELS",
                                      reason="no rules matched and no GPT suggestions", tasksense_data=tasksense_data)
                
                # Handle section routing for this task using priority-based selection
                if result.sections_to_move and not args.dry_run:
                    # Extract labels from applied rules for priority selection
                    task_labels = set()
                    for rule_info in result.applied_rules:
                        if rule_info.get('label'):
                            task_labels.add(rule_info['label'])
                    
                    project_id = task.get('project_id')
                    if project_id and task_labels:
                        # Use priority-based section selection
                        selected_section = select_priority_section(task_labels, rules, project_id, task_logger)
                        
                        if selected_section:
                            section_name = selected_section['section_name']
                            
                            # Get or create section
                            section_id = None
                            if selected_section['create_if_missing']:
                                section_id = create_section_if_missing_sync(section_name, project_id, task_logger)
                            else:
                                sections = get_project_sections(project_id, task_logger)
                                section_id = sections.get(section_name)
                            
                            # Move task to section
                            if section_id:
                                # Check if task is already in target section to avoid duplicate moves
                                current_section = task.get('section_id')
                                if current_section == section_id:
                                    if task_logger:
                                        task_logger.info(f"SECTION_SKIP: Task {task['id']} already in target section {section_name}")
                                else:
                                    move_success = move_task_to_section(task['id'], section_id, task_logger, task['content'], args.bulk_mode)
                                    if move_success:
                                        if args.verbose:
                                            log_success(f"📁 Moved task to section: {section_name}")
                                        log_task_action(task_logger, task['id'], task['content'], "MOVED_TO_SECTION",
                                                      section=section_name, priority=selected_section['priority'], 
                                                      rule_source=selected_section['label'])
                                    else:
                                        log_task_action(task_logger, task['id'], task['content'], "MOVE_FAILED",
                                                      error=f"Failed to move to section: {section_name}")
                            else:
                                log_task_action(task_logger, task['id'], task['content'], "SECTION_NOT_FOUND",
                                              error=f"Section '{section_name}' not found or could not be created")
                        else:
                            log_task_action(task_logger, task['id'], task['content'], "NO_VIABLE_SECTION",
                                          error="No viable section found from candidates")
                    else:
                        log_task_action(task_logger, task['id'], task['content'], "NO_PROJECT_ID",
                                      error="Cannot move task without project_id")
                elif result.sections_to_move and args.dry_run:
                    # Use priority-based section selection for dry run preview
                    task_labels = set()
                    for rule_info in result.applied_rules:
                        if rule_info.get('label'):
                            task_labels.add(rule_info['label'])
                    
                    project_id = task.get('project_id')
                    if project_id and task_labels:
                        selected_section = select_priority_section(task_labels, rules, project_id, task_logger)
                        
                        if selected_section:
                            section_name = selected_section['section_name']
                            if args.verbose:
                                log_info(f"📂 Would move task to section: {section_name} (priority: {selected_section['priority']})", "cyan")
                            log_task_action(task_logger, task['id'], task['content'], "WOULD_MOVE_TO_SECTION",
                                          section=section_name, priority=selected_section['priority'], 
                                          rule_source=selected_section['label'])
                        else:
                            log_task_action(task_logger, task['id'], task['content'], "NO_VIABLE_SECTION",
                                          error="No viable section found from candidates")
                    else:
                        # Fallback to old behavior if no labels
                        section_info = result.sections_to_move[0]
                        section_name = section_info['section_name']
                        if args.verbose:
                            log_info(f"📂 Would move task to section: {section_name}", "cyan")
                        log_task_action(task_logger, task['id'], task['content'], "WOULD_MOVE_TO_SECTION",
                                      section=section_name, rule_source=section_info['rule_source'])
            
            # Show pipeline statistics
            if args.verbose:
                stats = pipeline.get_statistics()
                log_info(f"📊 Pipeline stats: {stats['tasks_processed']} tasks, {stats['labels_applied']} labels applied")
                if stats['tasksense_used'] > 0:
                    log_info(f"🧠 TaskSense used for {stats['tasksense_used']} tasks")
                if stats['confidence_filtered'] > 0:
                    log_info(f"🎯 Filtered {stats['confidence_filtered']} labels due to low confidence")
            
            # Universal section routing: Ensure ALL tasks with existing labels are properly routed
            # This catches tasks that already had labels but weren't processed for section routing
            if args.verbose:
                log_info(f"🔄 Running universal section routing check on {len(tasks_to_process)} tasks")
            
            for task in tasks_to_process:
                existing_labels = set(task.get('labels', []))
                current_section_id = task.get('section_id')
                
                # Only route backlog tasks (no section assigned) with labels
                if existing_labels and current_section_id is None:
                    # Route any backlog task with existing labels to ensure proper section placement
                    route_task_to_section(task, rules, task_logger, args.dry_run, args.bulk_mode, context="UNIVERSAL")
        else:
            # Fallback to original processing if pipeline not available
            log_warning("⚠️ LabelingPipeline not available, using legacy processing")
            
            for task in tasks_to_process:
                if args.verbose:
                    log_info(f"📋 Processing: {task['content'][:50]}{'...' if len(task['content']) > 50 else ''}")
                
                content = task['content']
                
                # Apply rule-based labeling with GPT fallback to ALL tasks
                rule_labels, applied_rules = apply_rules_to_task(task, rules, gpt_fallback, task_logger, current_mode, tasksense_config)
                
                # Check if task contains any links for URL processing
                has_any_link = re.search(r'https?://\S+', content)
                
                # Collect domain labels from URLs (if any)
                domain_labels = set()
                if has_any_link:
                    urls = extract_all_urls(content)
                    
                    if args.verbose:
                        url_count = len(urls)
                        log_info(f"🔗 Found {url_count} URL{'s' if url_count != 1 else ''} in task")
                    
                    for url_info in urls:
                        domain_label = get_domain_label(url_info['url'])
                        if domain_label:
                            domain_labels.add(domain_label)
                
                # Combine all labels (rule-based/GPT + domain-specific)
                all_labels = set(rule_labels) | domain_labels
                
                # Apply labels if we have any
                if all_labels:
                    existing_labels = task.get("labels", [])
                    new_labels = [label for label in all_labels if label not in existing_labels]
                    
                    # Handle label creation for rules that require it
                    for rule_info in applied_rules:
                        if rule_info.get('create_if_missing', False) and rule_info['label'] in new_labels:
                            if not args.dry_run:
                                create_label_if_missing(rule_info['label'], task_logger)
                    
                    if new_labels:
                        success = update_task(task, None, None, new_labels, summary, args.dry_run)
                        if success:
                            # Track labels for summary
                            for label in new_labels:
                                if label in domain_labels and label != 'link':
                                    summary.labeled(label)  # Domain-specific label
                                else:
                                    summary.labeled()  # Rule-based or GPT label
                            
                            if args.verbose and not args.dry_run:
                                log_success(f"🏷️  Tagged task with labels: {new_labels}")
                            
                            # Log the labeling action
                            action = "LABELED_DRY_RUN" if args.dry_run else "LABELED"
                            first_url = urls[0]['url'] if has_any_link and 'urls' in locals() else None
                            label_sources = [rule['source'] for rule in applied_rules if rule['label'] in new_labels]
                            log_task_action(task_logger, task['id'], task['content'], action, 
                                          labels=new_labels, url=first_url, source=','.join(set(label_sources)))
                        else:
                            log_task_action(task_logger, task['id'], task['content'], "FAILED",
                                          error="Failed to apply labels")
                    else:
                        # Labels matched but no new labels to add
                        log_task_action(task_logger, task['id'], task['content'], "LABELS_MATCHED_NO_NEW",
                                      reason="all matching labels already exist")
                else:
                    # No labels to apply
                    log_task_action(task_logger, task['id'], task['content'], "NO_LABELS",
                                  reason="no rules matched and no GPT suggestions")

                # Handle section routing for matching rules
                sections_to_move = []
                for rule_info in applied_rules:
                    if rule_info.get('move_to') and rule_info.get('source') == 'rule':
                        sections_to_move.append({
                            'section_name': rule_info['move_to'],
                            'create_if_missing': rule_info.get('create_if_missing', False),
                            'rule_source': rule_info.get('matcher', 'unknown')
                        })
                
                # Move to section if specified in rules using priority-based selection
                if sections_to_move and not args.dry_run:
                    # Extract labels from applied rules for priority selection
                    task_labels = set()
                    for rule_info in applied_rules:
                        if rule_info.get('label'):
                            task_labels.add(rule_info['label'])
                    
                    project_id = task.get('project_id')
                    if project_id and task_labels:
                        # Use priority-based section selection
                        selected_section = select_priority_section(task_labels, rules, project_id, task_logger)
                        
                        if selected_section:
                            section_name = selected_section['section_name']
                            
                            # Get or create section
                            section_id = None
                            if selected_section['create_if_missing']:
                                section_id = create_section_if_missing_sync(section_name, project_id, task_logger)
                            else:
                                sections = get_project_sections(project_id, task_logger)
                                section_id = sections.get(section_name)
                            
                            # Move task to section
                            if section_id:
                                # Check if task is already in target section to avoid duplicate moves
                                current_section = task.get('section_id')
                                if current_section == section_id:
                                    if task_logger:
                                        task_logger.info(f"SECTION_SKIP: Task {task['id']} already in target section {section_name}")
                                else:
                                    move_success = move_task_to_section(task['id'], section_id, task_logger, task['content'], args.bulk_mode)
                                    if move_success:
                                        if args.verbose:
                                            log_success(f"📂 Moved task to section: {section_name}")
                                        log_task_action(task_logger, task['id'], task['content'], "MOVED_TO_SECTION",
                                                      section=section_name, priority=selected_section['priority'], 
                                                      rule_source=selected_section['label'])
                                    else:
                                        log_task_action(task_logger, task['id'], task['content'], "MOVE_FAILED",
                                                      error=f"Failed to move to section: {section_name}")
                            else:
                                log_task_action(task_logger, task['id'], task['content'], "SECTION_NOT_FOUND",
                                              error=f"Section '{section_name}' not found or could not be created")
                        else:
                            log_task_action(task_logger, task['id'], task['content'], "NO_VIABLE_SECTION",
                                          error="No viable section found from candidates")
                    else:
                        # Fallback to old behavior if no labels
                        section_info = sections_to_move[0]
                        section_name = section_info['section_name']
                        
                        if project_id:
                            # Get or create section
                            section_id = None
                            if section_info['create_if_missing']:
                                section_id = create_section_if_missing_sync(section_name, project_id, task_logger)
                            else:
                                sections = get_project_sections(project_id, task_logger)
                                section_id = sections.get(section_name)
                            
                            # Move task to section
                            if section_id:
                                # Check if task is already in target section to avoid duplicate moves
                                current_section = task.get('section_id')
                                if current_section == section_id:
                                    if task_logger:
                                        task_logger.info(f"SECTION_SKIP: Task {task['id']} already in target section {section_name}")
                                else:
                                    move_success = move_task_to_section(task['id'], section_id, task_logger, task['content'], args.bulk_mode)
                                    if move_success:
                                        if args.verbose:
                                            log_success(f"📂 Moved task to section: {section_name}")
                                        log_task_action(task_logger, task['id'], task['content'], "MOVED_TO_SECTION",
                                                      section=section_name, rule_source=section_info['rule_source'])
                                    else:
                                        log_task_action(task_logger, task['id'], task['content'], "MOVE_FAILED",
                                                      error=f"Failed to move to section {section_name}")
                            else:
                                log_task_action(task_logger, task['id'], task['content'], "SECTION_NOT_FOUND",
                                              reason=f"Section '{section_name}' not found and create_if_missing=False")
                        else:
                            log_task_action(task_logger, task['id'], task['content'], "NO_PROJECT_ID",
                                          reason="Cannot move to section without project_id")
                elif sections_to_move and args.dry_run:
                    # Use priority-based section selection for dry run preview in legacy mode
                    task_labels = set()
                    for rule_info in applied_rules:
                        if rule_info.get('label'):
                            task_labels.add(rule_info['label'])
                    
                    project_id = task.get('project_id')
                    if project_id and task_labels:
                        selected_section = select_priority_section(task_labels, rules, project_id, task_logger)
                        
                        if selected_section:
                            section_name = selected_section['section_name']
                            log_info(f"📂 Would move task to section: {section_name} (priority: {selected_section['priority']})", "cyan")
                            log_task_action(task_logger, task['id'], task['content'], "WOULD_MOVE_TO_SECTION",
                                          section=section_name, priority=selected_section['priority'], 
                                          rule_source=selected_section['label'])
                        else:
                            log_task_action(task_logger, task['id'], task['content'], "NO_VIABLE_SECTION",
                                          error="No viable section found from candidates")
                    else:
                        # Fallback to old behavior if no labels
                        section_name = sections_to_move[0]['section_name']
                        log_info(f"📂 Would move task to section: {section_name}", "cyan")
                        log_task_action(task_logger, task['id'], task['content'], "WOULD_MOVE_TO_SECTION",
                                      section=section_name, rule_source=sections_to_move[0]['rule_source'])

            # Separate URL processing for link formatting (independent of labeling)
            if has_any_link:
                # Process multiple links and update content with titles
                if args.verbose:
                    log_info(f"🌐 Processing {len(urls)} URL{'s' if len(urls) != 1 else ''} for titles...")
                
                updated_content, content_labels = process_multiple_links(content, task_logger, task['id'])
                
                # Check if content was actually updated with new titles
                if updated_content != content:
                    # Content was updated with new titles
                    success = update_task(task, None, None, content_labels, summary, args.dry_run, new_content=updated_content)
                    if success:
                        summary.updated()
                        
                        # Count URLs that got titles
                        urls_with_titles = len(urls)
                        
                        if not args.dry_run:
                            log_success(f"✅ Updated task with {urls_with_titles} titled link{'s' if urls_with_titles != 1 else ''}")
                        else:
                            log_info(f"📋 Would update task with {urls_with_titles} titled link{'s' if urls_with_titles != 1 else ''}", "cyan")
                        
                        # Log the update action
                        action = "MULTI_LINK_UPDATE_DRY_RUN" if args.dry_run else "MULTI_LINK_UPDATE"
                        log_task_action(task_logger, task['id'], task['content'], action,
                                      title=f"Updated {len(urls)} URLs with titles", 
                                      labels=content_labels, url=f"{len(urls)} URLs processed")
                    else:
                        # Log failed update
                        log_task_action(task_logger, task['id'], task['content'], "FAILED",
                                      error="API error during multi-link update")
                else:
                    # Content didn't change - check if it already has valid titles
                    existing_markdown_links = len([u for u in urls if u['type'] == 'markdown'])
                    if existing_markdown_links > 0:
                        # Task already has properly formatted markdown links
                        summary.skipped("already has titled links")
                        if args.verbose:
                            log_info(f"✅ Task already has {existing_markdown_links} properly titled link{'s' if existing_markdown_links != 1 else ''}")
                        
                        log_task_action(task_logger, task['id'], task['content'], "ALREADY_TITLED",
                                      reason=f"already has {existing_markdown_links} markdown links")
                    else:
                        # No titles could be fetched for plain URLs
                        summary.skipped("no valid titles")
                        if args.verbose:
                            log_warning(f"⚠️  Skipped: Could not fetch valid titles for any URLs")
                        
                        # Log skipped task
                        first_url = urls[0]['url'] if urls else "multiple URLs"
                        log_task_action(task_logger, task['id'], task['content'], "SKIPPED",
                                      url=first_url, reason="no valid titles found")
                
                # Handle pre-labeled task routing in fix-sections mode (legacy processing)
                if args.fix_sections and not rule_labels:
                    # Task didn't get new labels from rules, but might need section routing for existing labels
                    route_success = route_pre_labeled_task(task, rules, task_logger, args.dry_run, args.bulk_mode)
                    if route_success and args.verbose:
                        log_success(f"🔄 Routed pre-labeled task to correct section")
            
            # Universal section routing for legacy processing: Ensure ALL tasks with existing labels are properly routed
            # This catches any labeled tasks that weren't processed in the main loop
            if args.verbose:
                log_info(f"🔄 Running universal section routing check on {len(tasks_to_process)} tasks (legacy mode)")
            
            for task in tasks_to_process:
                existing_labels = set(task.get('labels', []))
                current_section_id = task.get('section_id')
                
                # Only route backlog tasks (no section assigned) with labels
                if existing_labels and current_section_id is None:
                    # Route any backlog task with existing labels to ensure proper section placement
                    route_task_to_section(task, rules, task_logger, args.dry_run, args.bulk_mode, context="UNIVERSAL_LEGACY")

        # Save timestamp for next incremental run (only if not dry run and not test mode)
        if not args.dry_run and not test_mode and not force_full_scan:
            save_last_run_timestamp()
            task_logger.info("Saved timestamp for next incremental run")
        
        # Log session end with summary
        task_logger.info(f"=== SESSION END | Updated: {summary.tasks_updated} | Labeled: {summary.tasks_labeled} | Skipped: {summary.tasks_skipped} | Failed: {summary.tasks_failed} ===")
        
        # Print final summary
        summary.print_summary(args.dry_run)

if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    main(test_mode=test_mode)