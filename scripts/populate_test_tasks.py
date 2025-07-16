#!/usr/bin/env python3
"""
TodoistProcessor Test Population Script

This script safely populates the TodoistProcessor project with comprehensive test tasks
for validating labeling, ranking, and section routing functionality.

Usage:
    python scripts/populate_test_tasks.py [options]

Options:
    --clear-first    Clear existing tasks before populating
    --dry-run        Show what would be created without actually creating
    --verbose        Show detailed output
    --help           Show this help message

Safety:
    - Only works with TodoistProcessor project (ID: 2355576487)
    - Requires PROJECT_NAMES=TodoistProcessor in .env
    - Will not affect production projects
"""

import requests
import json
import os
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = 2355576487
PROJECT_NAME = "TodoistProcessor"
API_BASE = 'https://api.todoist.com/rest/v2'

def get_headers():
    """Get API headers with authentication"""
    token = os.getenv('TODOIST_API_TOKEN')
    if not token:
        raise ValueError("TODOIST_API_TOKEN not found in environment")
    return {'Authorization': f'Bearer {token}'}

def verify_project_safety():
    """Verify we're working with the correct test project"""
    headers = get_headers()
    
    # Check .env PROJECT_NAMES setting
    env_projects = os.getenv('PROJECT_NAMES', '').lower()
    if 'todoistprocessor' not in env_projects:
        print("⚠️  Warning: PROJECT_NAMES does not include TodoistProcessor")
        print("   Consider setting PROJECT_NAMES=TodoistProcessor in .env")
    
    # Verify project exists and is correct
    response = requests.get(f'{API_BASE}/projects', headers=headers)
    response.raise_for_status()
    
    projects = response.json()
    target_project = None
    for project in projects:
        if project['id'] == str(PROJECT_ID):
            target_project = project
            break
    
    if not target_project:
        raise ValueError(f"Project ID {PROJECT_ID} not found")
    
    if target_project['name'] != PROJECT_NAME:
        raise ValueError(f"Project ID {PROJECT_ID} name is '{target_project['name']}', expected '{PROJECT_NAME}'")
    
    print(f"✅ Safety check passed: Using project '{target_project['name']}' (ID: {PROJECT_ID})")
    return target_project

def get_or_create_sections(headers, verbose=False):
    """Get existing sections or create them if needed"""
    response = requests.get(f'{API_BASE}/sections?project_id={PROJECT_ID}', headers=headers)
    response.raise_for_status()
    
    existing_sections = {section['name']: section['id'] for section in response.json()}
    
    required_sections = ['Work', 'Personal', 'Today', 'Links', 'Follow-ups']
    created_sections = {}
    
    for section_name in required_sections:
        if section_name in existing_sections:
            created_sections[section_name] = existing_sections[section_name]
            if verbose:
                print(f"📂 Found existing section: {section_name}")
        else:
            # Create section
            section_data = {
                'name': section_name,
                'project_id': PROJECT_ID
            }
            response = requests.post(f'{API_BASE}/sections', headers=headers, json=section_data)
            response.raise_for_status()
            
            section = response.json()
            created_sections[section_name] = section['id']
            if verbose:
                print(f"📂 Created section: {section_name}")
    
    return created_sections

def clear_existing_tasks(headers, verbose=False):
    """Clear all existing tasks in the project"""
    response = requests.get(f'{API_BASE}/tasks?project_id={PROJECT_ID}', headers=headers)
    response.raise_for_status()
    
    tasks = response.json()
    
    if not tasks:
        print("📋 No existing tasks to clear")
        return
    
    print(f"🗑️  Clearing {len(tasks)} existing tasks...")
    
    for task in tasks:
        try:
            delete_response = requests.delete(f'{API_BASE}/tasks/{task["id"]}', headers=headers)
            delete_response.raise_for_status()
            if verbose:
                print(f"   ✅ Deleted: {task['content'][:50]}...")
        except Exception as e:
            print(f"   ❌ Failed to delete task {task['id']}: {e}")

def get_test_tasks(sections):
    """Define all test tasks with comprehensive coverage"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    test_tasks = [
        # === LABELING TEST TASKS ===
        {
            'content': 'Schedule quarterly review meeting with Sarah',
            'priority': 2,
            'due_string': 'tomorrow',
            'category': 'Meeting Labeling'
        },
        {
            'content': 'Fix critical bug in user authentication system',
            'priority': 1,
            'due_string': 'today',
            'category': 'Bug Labeling'
        },
        {
            'content': 'Draft project proposal for Q2 roadmap',
            'priority': 2,
            'category': 'Work Labeling'
        },
        {
            'content': 'Review pull request from dev team',
            'priority': 3,
            'due_string': 'this week',
            'category': 'Work Labeling'
        },
        {
            'content': 'Prepare presentation for stakeholder meeting',
            'priority': 2,
            'due_string': 'next week',
            'category': 'Work + Meeting Labeling'
        },
        {
            'content': 'Buy groceries for the week',
            'priority': 3,
            'due_string': 'tomorrow',
            'category': 'Personal Labeling'
        },
        {
            'content': 'Call dentist to schedule appointment',
            'priority': 3,
            'category': 'Personal + Admin Labeling'
        },
        {
            'content': 'Research vacation destinations for summer',
            'priority': 4,
            'category': 'Personal Labeling'
        },
        {
            'content': 'Organize home office and clean desk',
            'priority': 3,
            'category': 'Home Labeling'
        },
        {
            'content': 'Read article about machine learning trends',
            'priority': 4,
            'category': 'Reading Labeling'
        },
        
        # === URL LABELING TEST TASKS ===
        {
            'content': 'Check out this GitHub repository https://github.com/example/repo',
            'priority': 3,
            'category': 'URL + GitHub Labeling'
        },
        {
            'content': 'Watch tutorial video https://youtube.com/watch?v=example',
            'priority': 3,
            'category': 'URL + YouTube Labeling'
        },
        {
            'content': 'Review documentation at https://example.com/docs',
            'priority': 2,
            'category': 'URL Labeling'
        },
        {
            'content': 'Multiple links: https://example.com/one and https://example-app.com/two',
            'priority': 3,
            'category': 'Multiple URL Labeling'
        },
        
        # === RANKING TEST TASKS ===
        {
            'content': 'High priority overdue task',
            'priority': 1,
            'due_string': 'yesterday',
            'category': 'High Priority Ranking'
        },
        {
            'content': 'Medium priority due today',
            'priority': 2,
            'due_string': 'today',
            'category': 'Medium Priority Ranking'
        },
        {
            'content': 'Low priority future task',
            'priority': 3,
            'due_string': 'next month',
            'category': 'Low Priority Ranking'
        },
        {
            'content': 'Work task for ranking',
            'priority': 2,
            'due_string': 'this week',
            'category': 'Work Ranking'
        },
        {
            'content': 'Personal task for ranking',
            'priority': 2,
            'due_string': 'this week',
            'category': 'Personal Ranking'
        },
        {
            'content': 'Old task created long ago',
            'priority': 3,
            'category': 'Age Ranking'
        },
        
        # === SECTION ROUTING TEST TASKS ===
        {
            'content': 'Meeting task should go to Work section',
            'priority': 2,
            'due_string': 'tomorrow',
            'category': 'Meeting → Work Routing'
        },
        {
            'content': 'Personal admin task',
            'priority': 3,
            'category': 'Personal Routing'
        },
        {
            'content': 'Important work deliverable',
            'priority': 1,
            'due_string': 'today',
            'category': 'Work Routing'
        },
        {
            'content': 'Follow up with client about project',
            'priority': 2,
            'category': 'Follow-up Routing'
        },
        {
            'content': 'Link to save for later https://example.com/save',
            'priority': 4,
            'category': 'Links Routing'
        },
        
        # === MIXED SCENARIO TEST TASKS ===
        {
            'content': 'Urgent meeting with team about bug fix https://github.com/example/issue',
            'priority': 1,
            'due_string': 'today',
            'category': 'Complex Mixed Scenario'
        },
        {
            'content': 'Personal development: read book and take notes',
            'priority': 3,
            'category': 'Personal Development'
        },
        {
            'content': 'Weekend project: organize garage',
            'priority': 4,
            'category': 'Weekend Task'
        },
        {
            'content': 'Team building lunch with colleagues',
            'priority': 3,
            'due_string': 'friday',
            'category': 'Team Building'
        },
        {
            'content': 'Evening admin task',
            'priority': 3,
            'category': 'Evening Task'
        },
        
        # === EDGE CASES ===
        {
            'content': 'Minimal task no metadata',
            'priority': 4,
            'category': 'No Metadata Edge Case'
        },
        {
            'content': 'Another minimal task',
            'priority': 4,
            'category': 'No Metadata Edge Case'
        },
        {
            'content': 'Priority 4 task with no due date for ranking edge case',
            'priority': 4,
            'category': 'Priority 4 Edge Case'
        },
        {
            'content': 'Another low priority task without deadline',
            'priority': 4,
            'category': 'Priority 4 Edge Case'
        },
        {
            'content': 'Personal task already in Personal section',
            'priority': 2,
            'section_id': sections.get('Personal'),
            'category': 'Section Skip Edge Case'
        },
        {
            'content': 'Work task already in Work section',
            'priority': 2,
            'section_id': sections.get('Work'),
            'category': 'Section Skip Edge Case'
        },
        {
            'content': 'Task in Today section should not be moved',
            'priority': 1,
            'due_string': 'today',
            'section_id': sections.get('Today'),
            'category': 'Today Protection Edge Case'
        },
        {
            'content': 'Another Today task to test protection',
            'priority': 2,
            'due_string': 'today',
            'section_id': sections.get('Today'),
            'category': 'Today Protection Edge Case'
        },
        {
            'content': 'This is an extremely long task title that contains many words and should test how the system handles long content with various edge cases and boundary conditions to ensure proper text processing and truncation',
            'priority': 3,
            'category': 'Long Title Edge Case'
        },
        {
            'content': 'Unicode test: café résumé naïve façade 中文 العربية 🚀 emoji test',
            'priority': 2,
            'category': 'Unicode Edge Case'
        },
        {
            'content': 'Duplicate task for idempotence testing',
            'priority': 3,
            'category': 'Duplicate Edge Case'
        },
        {
            'content': 'Duplicate task for idempotence testing',
            'priority': 3,
            'category': 'Duplicate Edge Case'
        }
    ]
    
    return test_tasks

def create_test_tasks(headers, test_tasks, dry_run=False, verbose=False):
    """Create the test tasks"""
    if dry_run:
        print(f"🧪 DRY RUN: Would create {len(test_tasks)} test tasks")
        categories = {}
        for task in test_tasks:
            cat = task['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        print("📋 Tasks by category:")
        for category, count in sorted(categories.items()):
            print(f"   • {count}x {category}")
        return []
    
    created_tasks = []
    
    for task_data in test_tasks:
        category = task_data.pop('category')
        
        try:
            response = requests.post(f'{API_BASE}/tasks', headers=headers, json=task_data)
            response.raise_for_status()
            
            task = response.json()
            created_tasks.append({
                'id': task['id'],
                'content': task['content'],
                'category': category,
                'priority': task.get('priority', 4),
                'section_id': task.get('section_id'),
                'due': task.get('due')
            })
            
            if verbose:
                print(f"✅ Created {category}: {task['content'][:50]}...")
                
        except Exception as e:
            print(f"❌ Error creating {category}: {e}")
            continue
    
    return created_tasks

def main():
    parser = argparse.ArgumentParser(description='Populate TodoistProcessor with test tasks')
    parser.add_argument('--clear-first', action='store_true', help='Clear existing tasks first')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    try:
        print("🔍 Verifying project safety...")
        project = verify_project_safety()
        
        headers = get_headers()
        
        print("📂 Setting up sections...")
        sections = get_or_create_sections(headers, args.verbose)
        
        if args.clear_first and not args.dry_run:
            clear_existing_tasks(headers, args.verbose)
        
        print("📋 Preparing test tasks...")
        test_tasks = get_test_tasks(sections)
        
        print(f"🚀 Creating {len(test_tasks)} test tasks...")
        created_tasks = create_test_tasks(headers, test_tasks, args.dry_run, args.verbose)
        
        if not args.dry_run:
            print(f"✅ Successfully created {len(created_tasks)} test tasks")
            
            # Summary by category
            categories = {}
            for task in created_tasks:
                cat = task['category']
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"📊 Test tasks by category:")
            for category, count in sorted(categories.items()):
                print(f"   • {count}x {category}")
            
            print(f"\\n🎯 TodoistProcessor is now ready for testing!")
            print("   Run: python main.py --dry-run --project TodoistProcessor --verbose")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())