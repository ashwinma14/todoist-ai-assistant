import os
from dotenv import load_dotenv  # 👈 new line
import re
import requests
from bs4 import BeautifulSoup

load_dotenv()  # 👈 new line

TODOIST_API = "https://api.todoist.com/rest/v2"
HEADERS = {"Authorization": f"Bearer {os.environ['TODOIST_API_TOKEN']}"}

print(f"📋 Raw task content: {repr(task['content'])}")
def is_plain_url(text):
    # Normalize line breaks and spaces
    text = text.strip().replace("\n", "").replace(" ", "")
    return re.fullmatch(r'https?://\S+', text) is not None


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
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        return soup.title.string.strip() if soup.title else None
    except Exception as e:
        print(f"⚠️ Failed to fetch title for {url}: {e}")
        return None


def get_label_id(label_name="link"):
    r = requests.get(f"{TODOIST_API}/labels", headers=HEADERS)
    r.raise_for_status()
    for label in r.json():
        if label['name'].lower() == label_name:
            return label['id']
    return None


def update_task(task_id, title, url, label_id=None):
    content = f"[{title}]({url})"
    payload = {"content": content}
    if label_id:
        payload["label_ids"] = [label_id]
    r = requests.post(f"{TODOIST_API}/tasks/{task_id}", headers=HEADERS, json=payload)
    return r.status_code == 204


def main():
    inbox_id = get_inbox_project_id()
    label_id = get_label_id()
    tasks = fetch_tasks(inbox_id)

    for task in tasks:
        if is_plain_url(task['content']):
            print(f"🔍 Found URL task: {task['content']}")
            title = fetch_page_title(task['content'])
            if title:
                success = update_task(task['id'], title, task['content'], label_id)
                print("✅ Updated task" if success else "❌ Update failed")
            else:
                print("⚠️ Skipped due to missing title")


if __name__ == "__main__":
    main()