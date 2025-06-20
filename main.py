import sys
import os
from dotenv import load_dotenv
load_dotenv()
import re
import requests
from bs4 import BeautifulSoup
import argparse
import logging
from datetime import datetime

# Try to import rich for colored output, fallback to regular print
try:
    from rich.console import Console
    from rich.text import Text
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
    
    log_message = " | ".join(log_parts)
    task_logger.info(log_message)

TODOIST_API = "https://api.todoist.com/rest/v2"

# Check if API token is available
if not os.environ.get('TODOIST_API_TOKEN'):
    print("❌ TODOIST_API_TOKEN environment variable is not set!")
    print("Please set your Todoist API token in your environment variables.")
    exit(1)

HEADERS = {"Authorization": f"Bearer {os.environ['TODOIST_API_TOKEN']}",
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
    except Exception as e:
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
                task_logger.info(f"Task {task_id} | Replaced '{original_text[:50]}...' with titled link: {title_preview}")
        else:
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
                        task_logger.info(f"Task {task_id} | No title found, used domain fallback: {domain}")
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
        "untitled", "no title"
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
    original_url = url
    url = resolve_redirect(url)  # Handle shortlink redirects (e.g. Reddit /s/)
    try:
        # Special handling for Reddit links: try JSON API first, then fallback to old-reddit HTML
        if "reddit.com" in url:
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
                # 1) Try JSON API for title
                json_url = f"https://www.reddit.com/r/{subreddit}/comments/{postid}.json"
                try:
                    resp_json = requests.get(json_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                    resp_json.raise_for_status()
                    data = resp_json.json()
                    title = data[0]["data"]["children"][0]["data"].get("title")
                    if title:
                        lower_title = title.lower()
                        if any(bad in lower_title for bad in ["page not found", "twitter / x", "attention required"]):
                            return None
                        return title.strip()
                except Exception as e:
                    pass
                # 2) Fallback to old Reddit HTML
                html_url = f"https://old.reddit.com/r/{subreddit}/comments/{postid}"
            else:
                html_url = url.replace("www.reddit.com", "old.reddit.com")
            resp = requests.get(html_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            if soup.title and soup.title.string:
                title = soup.title.string.split(" : ")[0].strip()
                lower_title = title.lower()
                if any(bad in lower_title for bad in ["page not found", "twitter / x", "attention required"]):
                    return None
                return title

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


def main(test_mode=False):
    summary = TaskSummary()
    task_logger = setup_task_logging()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=str, help="Comma-separated list of project names to process")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying any tasks")
    args, _ = parser.parse_known_args()

    if args.project:
        project_names = [name.strip().lower() for name in args.project.split(",")]
    elif os.getenv("PROJECT_NAMES"):
        env_projects_raw = os.getenv("PROJECT_NAMES")
        project_names = [name.strip().lower() for name in env_projects_raw.split(",")]
    else:
        project_names = ["inbox"]
    
    try:
        projects_response = requests.get(f"{TODOIST_API}/projects", headers=HEADERS)
        projects_response.raise_for_status()
        all_projects = projects_response.json()
    except requests.exceptions.JSONDecodeError:
        log_error("❌ Failed to parse Todoist API response. Check your TODOIST_API_TOKEN.")
        task_logger.error("API Error: Invalid JSON response from Todoist API - likely invalid token")
        return
    except requests.exceptions.HTTPError as e:
        log_error(f"❌ Todoist API HTTP error: {e}")
        task_logger.error(f"API Error: HTTP {projects_response.status_code} - {e}")
        return
    except Exception as e:
        log_error(f"❌ Failed to fetch projects: {e}")
        task_logger.error(f"API Error: {e}")
        return
    
    project_ids = [p["id"] for p in all_projects if p["name"].strip().lower() in project_names]
    if not project_ids:
        log_warning("No matching projects found")
        return

    # Log session start
    mode_info = []
    if test_mode:
        mode_info.append("TEST")
    if args.dry_run:
        mode_info.append("DRY_RUN")
    if args.verbose:
        mode_info.append("VERBOSE")
    
    mode_str = f"[{', '.join(mode_info)}]" if mode_info else "[NORMAL]"
    task_logger.info(f"=== SESSION START {mode_str} ===")

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
        label_id = get_label_id()
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

        log_info(f"🔍 Processing {len(tasks)} tasks from {len(project_ids)} project(s)...")
        task_logger.info(f"Processing {len(tasks)} tasks from projects: {[p['name'] for p in all_projects if p['id'] in project_ids]}")

        for task in tasks:
            if args.verbose:
                log_info(f"📋 Processing: {task['content'][:50]}{'...' if len(task['content']) > 50 else ''}")
            
            content = task['content']
            
            # Check if task contains any links
            has_any_link = re.search(r'https?://\S+', content)
            
            if has_any_link:
                # Extract all URLs from the content
                urls = extract_all_urls(content)
                
                if args.verbose:
                    url_count = len(urls)
                    log_info(f"🔗 Found {url_count} URL{'s' if url_count != 1 else ''} in task")
                
                # Collect all domain labels from all URLs
                all_labels = set(['link'])
                for url_info in urls:
                    domain_label = get_domain_label(url_info['url'])
                    if domain_label:
                        all_labels.add(domain_label)
                
                # Add labels that don't already exist
                existing_labels = task.get("labels", [])
                labels_to_add = list(all_labels)
                new_labels = [label for label in labels_to_add if label not in existing_labels]
                
                if new_labels:
                    success = update_task(task, None, None, new_labels, summary, args.dry_run)
                    if success:
                        # Track domain labels for summary
                        for label in new_labels:
                            if label != 'link':
                                summary.labeled(label)
                            else:
                                summary.labeled()
                        
                        if args.verbose and not args.dry_run:
                            log_success(f"🏷️  Tagged task with labels: {new_labels}")
                        
                        # Log the labeling action
                        action = "LABELED_DRY_RUN" if args.dry_run else "LABELED"
                        first_url = urls[0]['url'] if urls else None
                        log_task_action(task_logger, task['id'], task['content'], action, 
                                      labels=new_labels, url=first_url)

                # Process multiple links and update content
                if args.verbose:
                    log_info(f"🌐 Processing {len(urls)} URL{'s' if len(urls) != 1 else ''} for titles...")
                
                updated_content, content_labels = process_multiple_links(content, task_logger, task['id'])
                
                # Check if content was actually updated
                if updated_content != content:
                    success = update_task(task, None, None, content_labels, summary, args.dry_run, new_content=updated_content)
                    if success:
                        summary.updated()
                        
                        # Count unique titles for display
                        title_count = len([u for u in urls if fetch_page_title(u['url'])])
                        
                        if not args.dry_run:
                            log_success(f"✅ Updated task with {title_count} titled link{'s' if title_count != 1 else ''}")
                        else:
                            log_info(f"📋 Would update task with {title_count} titled link{'s' if title_count != 1 else ''}", "cyan")
                        
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
                    # No titles could be fetched
                    summary.skipped("no valid titles")
                    if args.verbose:
                        log_warning(f"⚠️  Skipped: Could not fetch valid titles for any URLs")
                    
                    # Log skipped task
                    first_url = urls[0]['url'] if urls else "multiple URLs"
                    log_task_action(task_logger, task['id'], task['content'], "SKIPPED",
                                  url=first_url, reason="no valid titles found")
            else:
                # Log tasks without URLs (no action taken)
                log_task_action(task_logger, task['id'], task['content'], "NO_ACTION",
                              reason="no URL found")

        # Log session end with summary
        task_logger.info(f"=== SESSION END | Updated: {summary.tasks_updated} | Labeled: {summary.tasks_labeled} | Skipped: {summary.tasks_skipped} | Failed: {summary.tasks_failed} ===")
        
        # Print final summary
        summary.print_summary(args.dry_run)

if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    main(test_mode=test_mode)