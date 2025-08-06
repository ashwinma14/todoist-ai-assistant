"""
TaskSense AI Engine - Core labeling engine for semantic task understanding.

This module provides the TaskSense class that wraps GPT functionality with
user profile awareness, mode-based prompting, and structured output.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import requests

# Import OpenAI with fallback handling (matching main.py pattern)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# Import task_sense_prompts for mode-aware prompting
try:
    from task_sense_prompts import TaskSensePrompts
    PROMPTS_AVAILABLE = True
except ImportError:
    PROMPTS_AVAILABLE = False


class TaskSense:
    """
    TaskSense AI Engine for semantic task labeling.
    
    Provides context-aware labeling using user profile, work modes, and
    configurable reasoning levels with structured output.
    """
    
    def __init__(self, config_path: str = "task_sense_config.json", ranking_config_path: str = "ranking_config.json"):
        """
        Initialize TaskSense engine with configuration.
        
        Args:
            config_path: Path to TaskSense configuration file
            ranking_config_path: Path to ranking configuration file
        """
        # Initialize logger first
        self.logger = logging.getLogger('task_sense')
        
        # Engine metadata
        self.version = "v1.0"
        self.source = "TaskSense"
        
        # Load configurations with environment variable support
        self.config = self._load_config(config_path)
        
        # Support RANKING_CONFIG_PATH environment variable (optional for deployment)
        ranking_config_env_path = os.environ.get('RANKING_CONFIG_PATH')
        if ranking_config_env_path:
            ranking_config_path = ranking_config_env_path
            
        self.ranking_config = self._load_ranking_config(ranking_config_path)
        self.prompts = TaskSensePrompts() if PROMPTS_AVAILABLE else None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load TaskSense configuration from JSON file."""
        # Handle None config_path (fallback to default config)
        if config_path is None:
            if self.logger:
                self.logger.info("TaskSense config_path is None, using default configuration")
            return self._get_default_config()
            
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            # Return default configuration if file doesn't exist
            return {
                "user_profile": "I'm a productivity-focused user who values efficient task management.",
                "available_labels": ["work", "personal", "urgent", "followup", "admin", "home"],
                "default_mode": "personal",
                "reasoning_level": "light",
                "fallback_to_rules": True,
                "prompt_version": "v1.0",
                "model": "gpt-3.5-turbo"
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading TaskSense config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when config file is unavailable."""
        return {
            "user_profile": "I'm a productivity-focused user who values efficient task management.",
            "available_labels": ["work", "personal", "urgent", "followup", "admin", "home"],
            "default_mode": "personal",
            "reasoning_level": "light",
            "fallback_to_rules": True,
            "prompt_version": "v1.0",
            "model": "gpt-3.5-turbo"
        }
    
    def _load_ranking_config(self, config_path: str) -> Dict[str, Any]:
        """Load ranking configuration from JSON file."""
        # Handle None config_path (fallback to default config)
        if config_path is None:
            if self.logger:
                self.logger.info("Ranking config_path is None, using default configuration")
            return self._get_default_ranking_config()
            
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            if self.logger:
                self.logger.info(f"Loaded ranking config from {config_path}")
            return config
        except FileNotFoundError:
            if self.logger:
                self.logger.warning(f"Ranking config file not found: {config_path}, using defaults")
            return self._get_default_ranking_config()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading ranking config: {e}")
            return self._get_default_ranking_config()
    
    def _get_default_ranking_config(self) -> Dict[str, Any]:
        """Get default ranking configuration when config file is unavailable."""
        return {
            "version": "4.0",
            "default_limit": 3,
            "scoring_weights": {
                "priority": 0.4,
                "due_date": 0.3,
                "age": 0.1,
                "label_preference": 0.2
            },
            "fallback_weights": {
                "no_priority": 0.3,
                "no_due_date": 0.2,
                "no_preferred_labels": 0.1
            },
            "priority_scores": {
                "1": 1.0, "2": 0.8, "3": 0.6, "4": 0.4
            },
            "due_date_scores": {
                "overdue": 1.0, "today": 0.9, "tomorrow": 0.7, "this_week": 0.5, "future": 0.2
            },
            "mode_settings": {
                "work": {
                    "filters": ["@work & !@today"],
                    "preferred_labels": ["work", "meeting", "urgent"],
                    "excluded_labels": ["personal"]
                },
                "personal": {
                    "filters": ["@personal & !@today"],
                    "preferred_labels": ["personal", "health", "family"],
                    "excluded_labels": ["work"]
                }
            },
            "labels": {
                "today_marker": "@today",
                "feedback_labels": ["@today-done", "@today-skip", "@rank-ignore"]
            },
            "sections": {
                "today_section": "Today",
                "create_if_missing": True
            },
            "filtering": {
                "enabled": True,
                "fallback_to_full_backlog": True,
                "backlog_only": True
            },
            "logging": {
                "verbose_scoring": True,
                "log_candidates": True,
                "log_moves": True
            }
        }
    
    def label(self, 
              task_content: str, 
              available_labels: Optional[List[str]] = None,
              dry_run: bool = False,
              mode: Optional[str] = None) -> Dict[str, Any]:
        """
        Label a task using TaskSense AI engine.
        
        Args:
            task_content: The task content to label
            available_labels: List of available labels (uses config default if None)
            dry_run: If True, return mock response without API call
            mode: Work mode (personal, work, weekend, etc.)
            
        Returns:
            Dictionary with labels, explanation, confidence, and metadata
        """
        # Use provided labels or fall back to config
        if available_labels is None:
            available_labels = self.config.get("available_labels", ["work", "personal"])
        
        # Use provided mode or fall back to config
        if mode is None:
            mode = self.config.get("default_mode", "personal")
            
        # Handle dry run mode
        if dry_run:
            return self._get_dry_run_response(task_content, available_labels, mode)
        
        # Handle mock mode for testing
        if os.environ.get('GPT_MOCK_MODE') or self.config.get("mock_mode", {}).get("enabled", False):
            return self._get_mock_response(task_content, available_labels, mode)
        
        # Attempt GPT labeling
        try:
            return self._get_gpt_labels(task_content, available_labels, mode)
        except Exception as e:
            if self.logger:
                self.logger.error(f"TaskSense GPT error: {e}")
            return self._get_fallback_response(task_content, available_labels, mode, str(e))
    
    def _get_gpt_labels(self, task_content: str, available_labels: List[str], mode: str) -> Dict[str, Any]:
        """Get labels from GPT API with structured output."""
        # Check for API key
        if not os.environ.get('OPENAI_API_KEY'):
            raise Exception("OPENAI_API_KEY not set")
        
        # Get prompt from template system or use fallback
        if self.prompts:
            reasoning_level = self.config.get("reasoning_level", "light")
            prompt = self.prompts.get_prompt(mode, reasoning_level)
        else:
            prompt = self._get_fallback_prompt(mode)
        
        # Construct full prompt
        user_profile = self.config.get("user_profile", "")
        full_prompt = self._construct_prompt(prompt, user_profile, task_content, available_labels)
        
        # Try OpenAI package first, then direct HTTP
        response_data = self._call_openai_api(full_prompt)
        
        if response_data:
            return self._parse_gpt_response(response_data, task_content, available_labels, mode)
        else:
            raise Exception("No response from OpenAI API")
    
    def _construct_prompt(self, base_prompt: str, user_profile: str, task_content: str, available_labels: List[str]) -> str:
        """Construct the full prompt for GPT."""
        labels_str = ", ".join(available_labels)
        
        prompt = f"""{base_prompt}

User Profile: {user_profile}

Available Labels: {labels_str}

Task: {task_content}

Please respond with one or two relevant labels from the available labels list."""
        
        reasoning_level = self.config.get("reasoning_level", "light")
        if reasoning_level == "light":
            prompt += "\n\nBriefly explain your reasoning in one sentence."
        elif reasoning_level == "deep":
            prompt += "\n\nProvide detailed reasoning with confidence level (0.0-1.0)."
        
        return prompt
    
    def _call_openai_api(self, prompt: str) -> Optional[str]:
        """Call OpenAI API with fallback to direct HTTP."""
        model = self.config.get("model", "gpt-3.5-turbo")
        
        # Try OpenAI package first
        if OPENAI_AVAILABLE:
            try:
                # Initialize OpenAI client with cleaned API key
                api_key_raw = os.environ.get('OPENAI_API_KEY')
                api_key_to_use = api_key_raw.strip() if api_key_raw else None
                
                client = OpenAI(api_key=api_key_to_use)
                
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.3
                )
                
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
                    
            except TypeError as e:
                # Handle potential version-specific errors like unexpected keyword arguments
                if "proxies" in str(e) or "unexpected keyword argument" in str(e):
                    if self.logger:
                        self.logger.warning(f"OpenAI client initialization error (likely version mismatch): {e}, falling back to HTTP")
                else:
                    if self.logger:
                        self.logger.warning(f"OpenAI TypeError: {e}, falling back to HTTP")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"OpenAI package error: {e}, falling back to HTTP")
        
        # Fallback to direct HTTP
        return self._call_openai_http(prompt, model)
    
    def _call_openai_http(self, prompt: str, model: str) -> Optional[str]:
        """Direct HTTP call to OpenAI API."""
        url = "https://api.openai.com/v1/chat/completions"
        
        # Get cleaned API key
        api_key_raw = os.environ.get('OPENAI_API_KEY')
        api_key_cleaned = api_key_raw.strip() if api_key_raw else None
        
        headers = {
            "Authorization": f"Bearer {api_key_cleaned}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('choices') and result['choices'][0].get('message', {}).get('content'):
                    return result['choices'][0]['message']['content'].strip()
            else:
                if self.logger:
                    self.logger.error(f"OpenAI HTTP error: {response.status_code} - {response.text}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"OpenAI HTTP request error: {e}")
            
        return None
    
    def _parse_gpt_response(self, response_text: str, task_content: str, available_labels: List[str], mode: str) -> Dict[str, Any]:
        """Parse GPT response into structured output."""
        lines = response_text.strip().split('\n')
        
        # Extract labels (first line or comma-separated)
        labels_line = lines[0] if lines else ""
        raw_labels = [label.strip().lower() for label in labels_line.split(',')]
        
        # Filter to only available labels
        valid_labels = [label for label in raw_labels if label in [l.lower() for l in available_labels]]
        
        # Extract explanation if available
        explanation = ""
        confidence = 0.8  # Default confidence
        
        if len(lines) > 1:
            explanation = " ".join(lines[1:]).strip()
            
            # Extract confidence if in deep reasoning mode
            if self.config.get("reasoning_level") == "deep":
                confidence_match = self._extract_confidence(explanation)
                if confidence_match:
                    confidence = confidence_match
        
        return {
            "labels": valid_labels[:2],  # Limit to 2 labels
            "explanation": explanation,
            "confidence": confidence,
            "source": self.source,
            "engine_meta": {
                "version": self.version,
                "reasoning_level": self.config.get("reasoning_level", "light"),
                "model": self.config.get("model", "gpt-3.5-turbo"),
                "mode": mode
            }
        }
    
    def _extract_confidence(self, text: str) -> Optional[float]:
        """Extract confidence score from text."""
        import re
        # Look for patterns like "confidence: 0.8" or "0.85 confidence"
        patterns = [
            r'confidence:\s*([0-9]\.[0-9]+)',
            r'([0-9]\.[0-9]+)\s*confidence',
            r'confidence\s*([0-9]\.[0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None
    
    def _get_fallback_prompt(self, mode: str) -> str:
        """Get fallback prompt when template system is unavailable."""
        base_prompt = "You are a productivity assistant. Assign the most relevant label to this Todoist task."
        
        if mode == "weekend":
            base_prompt += " Consider this is weekend time, so prefer personal and home-related tasks."
        elif mode == "work":
            base_prompt += " Consider this is work time, so prefer work-related labels."
        
        return base_prompt
    
    def _get_mock_response(self, task_content: str, available_labels: List[str], mode: str) -> Dict[str, Any]:
        """Generate mock response for testing."""
        content_lower = task_content.lower()
        
        # Check for config-based mock responses
        mock_config = self.config.get("mock_mode", {})
        mock_responses = mock_config.get("responses", {})
        
        # Check patterns from config
        if "patterns" in mock_responses:
            for pattern, response in mock_responses["patterns"].items():
                if pattern in content_lower:
                    return {
                        "labels": response["labels"],
                        "explanation": response["explanation"],
                        "confidence": response["confidence"],
                        "source": "TaskSense_Mock_Config",
                        "engine_meta": {
                            "version": self.version,
                            "reasoning_level": self.config.get("reasoning_level", "light"),
                            "model": "mock",
                            "mode": mode,
                            "pattern_matched": pattern
                        }
                    }
        
        # Use default response from config or fallback heuristics
        if "default" in mock_responses:
            default_response = mock_responses["default"]
            return {
                "labels": default_response["labels"],
                "explanation": default_response["explanation"],
                "confidence": default_response["confidence"],
                "source": "TaskSense_Mock_Default",
                "engine_meta": {
                    "version": self.version,
                    "reasoning_level": self.config.get("reasoning_level", "light"),
                    "model": "mock",
                    "mode": mode
                }
            }
        
        # Fallback heuristics if no config
        if any(word in content_lower for word in ['clean', 'organize', 'house', 'home', 'garage']):
            labels = ['home']
            explanation = "Task involves home maintenance and organization"
        elif any(word in content_lower for word in ['work', 'meeting', 'project', 'deadline']):
            labels = ['work']
            explanation = "Task is work-related and involves professional activities"
        elif any(word in content_lower for word in ['doctor', 'appointment', 'pay', 'tax', 'bill']):
            labels = ['admin']
            explanation = "Task involves administrative or financial responsibilities"
        elif any(word in content_lower for word in ['urgent', '!', 'asap', 'immediately']):
            labels = ['urgent']
            explanation = "Task has urgent priority indicators"
        else:
            labels = ['personal']
            explanation = "Task appears to be personal in nature"
        
        return {
            "labels": labels,
            "explanation": explanation,
            "confidence": 0.8,
            "source": "TaskSense_Mock_Heuristic",
            "engine_meta": {
                "version": self.version,
                "reasoning_level": self.config.get("reasoning_level", "light"),
                "model": "mock",
                "mode": mode
            }
        }
    
    def _get_dry_run_response(self, task_content: str, available_labels: List[str], mode: str) -> Dict[str, Any]:
        """Generate dry run response."""
        return {
            "labels": ["personal"],
            "explanation": "DRY RUN: Would analyze task and return appropriate labels",
            "confidence": 1.0,
            "source": "TaskSense_DryRun",
            "engine_meta": {
                "version": self.version,
                "reasoning_level": self.config.get("reasoning_level", "light"),
                "model": "dry_run",
                "mode": mode
            }
        }
    
    def _get_fallback_response(self, task_content: str, available_labels: List[str], mode: str, error: str) -> Dict[str, Any]:
        """Generate fallback response when GPT fails."""
        return {
            "labels": ["personal"],  # Safe default
            "explanation": f"TaskSense fallback due to error: {error}",
            "confidence": 0.5,
            "source": "TaskSense_Fallback",
            "engine_meta": {
                "version": self.version,
                "reasoning_level": self.config.get("reasoning_level", "light"),
                "model": "fallback",
                "mode": mode
            }
        }
    
    # ==========================================
    # PHASE 4: RANKING ENGINE IMPLEMENTATION
    # ==========================================
    
    def calculate_priority_score(self, task: Dict[str, Any]) -> float:
        """
        Calculate priority score for a task.
        
        Args:
            task: Task dictionary from Todoist API
            
        Returns:
            float: Priority score (0.0-1.0)
        """
        priority = task.get('priority', 4)  # Default to lowest priority
        priority_scores = self.ranking_config.get('priority_scores', {})
        fallback_weights = self.ranking_config.get('fallback_weights', {})
        
        # Convert priority to string for lookup
        priority_str = str(priority)
        
        if priority_str in priority_scores:
            return priority_scores[priority_str]
        else:
            # Use fallback weight for missing priority
            return fallback_weights.get('no_priority', 0.3)
    
    def calculate_due_date_score(self, task: Dict[str, Any]) -> float:
        """
        Calculate due date proximity score for a task.
        
        Args:
            task: Task dictionary from Todoist API
            
        Returns:
            float: Due date score (0.0-1.0)
        """
        from datetime import datetime, timezone
        
        due_info = task.get('due')
        if not due_info or not due_info.get('date'):
            # Use fallback weight for no due date
            fallback_weights = self.ranking_config.get('fallback_weights', {})
            return fallback_weights.get('no_due_date', 0.2)
        
        due_date_scores = self.ranking_config.get('due_date_scores', {})
        
        try:
            # Parse due date
            due_date_str = due_info['date']
            if 'T' in due_date_str:
                # Full datetime
                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            else:
                # Date only - assume end of day
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                due_date = due_date.replace(hour=23, minute=59, second=59)
            
            # Get current time
            now = datetime.now(timezone.utc)
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            
            # Calculate days difference
            days_diff = (due_date - now).days
            
            if days_diff < 0:
                return due_date_scores.get('overdue', 1.0)
            elif days_diff == 0:
                return due_date_scores.get('today', 0.9)
            elif days_diff == 1:
                return due_date_scores.get('tomorrow', 0.7)
            elif days_diff <= 7:
                return due_date_scores.get('this_week', 0.5)
            else:
                return due_date_scores.get('future', 0.2)
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error parsing due date for task {task.get('id', 'unknown')}: {e}")
            fallback_weights = self.ranking_config.get('fallback_weights', {})
            return fallback_weights.get('no_due_date', 0.2)
    
    def calculate_age_score(self, task: Dict[str, Any]) -> float:
        """
        Calculate age score for a task (older tasks get slight boost).
        
        Args:
            task: Task dictionary from Todoist API
            
        Returns:
            float: Age score (0.0-1.0)
        """
        from datetime import datetime, timezone
        
        created_at = task.get('created_at')
        if not created_at:
            return 0.1  # Default for missing creation date
        
        try:
            # Parse creation date
            if isinstance(created_at, str):
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                created_date = created_at
            
            # Get current time
            now = datetime.now(timezone.utc)
            if created_date.tzinfo is None:
                created_date = created_date.replace(tzinfo=timezone.utc)
            
            # Calculate days since creation
            days_old = (now - created_date).days
            
            # Give slight boost to older tasks (0.0-1.0 scale)
            # Cap at 30 days for reasonable range
            age_score = min(days_old / 30.0, 1.0)
            
            return age_score
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error parsing creation date for task {task.get('id', 'unknown')}: {e}")
            return 0.1
    
    def calculate_label_preference_score(self, task: Dict[str, Any], mode: str) -> float:
        """
        Calculate label preference score based on mode-specific preferences.
        
        Args:
            task: Task dictionary from Todoist API
            mode: Current mode (work, personal, weekend, evening)
            
        Returns:
            float: Label preference score (0.0-1.0)
        """
        task_labels = set(task.get('labels', []))
        if not task_labels:
            # Use fallback weight for no preferred labels
            fallback_weights = self.ranking_config.get('fallback_weights', {})
            return fallback_weights.get('no_preferred_labels', 0.1)
        
        mode_settings = self.ranking_config.get('mode_settings', {})
        current_mode_settings = mode_settings.get(mode, {})
        
        preferred_labels = set(current_mode_settings.get('preferred_labels', []))
        excluded_labels = set(current_mode_settings.get('excluded_labels', []))
        
        # Check for excluded labels (penalty)
        if task_labels & excluded_labels:
            return 0.0
        
        # Check for preferred labels (bonus)
        preferred_matches = task_labels & preferred_labels
        if preferred_matches:
            # Score based on number of preferred label matches
            return min(len(preferred_matches) * 0.4, 1.0)
        
        # Neutral score for non-preferred, non-excluded labels
        return 0.5
    
    def calculate_composite_score(self, task: Dict[str, Any], mode: str, config_override: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Calculate composite score for a task combining all scoring components.
        
        Args:
            task: Task dictionary from Todoist API
            mode: Current mode (work, personal, weekend, evening)
            config_override: Optional config override
            
        Returns:
            dict: Score result with components and explanation
        """
        # Use override config or default
        config = config_override or self.ranking_config
        
        # Get mode-specific weights or fall back to default
        mode_settings = config.get('mode_settings', {})
        current_mode = mode_settings.get(mode, {})
        weights = current_mode.get('weights') or config.get('scoring_weights', {})
        
        # Calculate individual component scores
        priority_score = self.calculate_priority_score(task)
        due_date_score = self.calculate_due_date_score(task)
        age_score = self.calculate_age_score(task)
        label_score = self.calculate_label_preference_score(task, mode)
        
        # Calculate weighted composite score
        components = {
            'priority': priority_score * weights.get('priority', 0.4),
            'due_date': due_date_score * weights.get('due_date', 0.3),
            'age': age_score * weights.get('age', 0.1),
            'label_preference': label_score * weights.get('label_preference', 0.2)
        }
        
        total_score = sum(components.values())
        
        # Generate explanation
        explanations = []
        if priority_score > 0.7:
            explanations.append(f"high priority (p{task.get('priority', 4)})")
        
        due_info = task.get('due')
        if due_info and due_date_score > 0.8:
            explanations.append("due soon")
        elif due_date_score == 1.0:
            explanations.append("overdue")
        
        task_labels = task.get('labels', [])
        if label_score > 0.5 and task_labels:
            mode_settings = config.get('mode_settings', {})
            preferred = mode_settings.get(mode, {}).get('preferred_labels', [])
            matching_labels = [label for label in task_labels if label in preferred]
            if matching_labels:
                explanations.append(f"preferred labels: {', '.join(matching_labels)}")
        
        if age_score > 0.5:
            explanations.append("older task")
        
        explanation = "; ".join(explanations) if explanations else "standard scoring"
        
        return {
            'score': round(total_score, 3),
            'components': components,
            'explanation': explanation,
            'raw_components': {
                'priority': priority_score,
                'due_date': due_date_score,
                'age': age_score,
                'label_preference': label_score
            }
        }
    
    def rank(self, tasks: List[Dict[str, Any]], mode: Optional[str] = None, limit: int = 3, config_override: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Rank tasks for daily focus selection using priority-based scoring.
        
        Args:
            tasks: List of task dictionaries from Todoist API
            mode: Override mode (work, personal, weekend, evening, auto)
            limit: Maximum tasks to return (default: 3)
            config_override: Override default ranking config
            
        Returns:
            List of ranked tasks with scores and explanations:
            [
                {
                    'task': {...},  # Original task dict
                    'score': 0.85,
                    'explanation': 'High priority work task due today',
                    'components': {
                        'priority': 0.4,
                        'due_date': 0.3,
                        'age': 0.05,
                        'label_preference': 0.1
                    }
                }
            ]
        """
        # Use override config or default
        config = config_override or self.ranking_config
        
        # Determine mode
        if mode is None:
            mode = self.config.get('default_mode', 'personal')
        elif mode == 'auto':
            mode = self._detect_mode()
        
        # Filter to rankable tasks (all uncompleted tasks, optionally excluding Today section)
        filtering_config = config.get('filtering', {})
        
        # Get Today section ID if we need to exclude it
        today_section_id = None
        section_config = config.get('sections', {})
        today_section_name = section_config.get('today_section', 'Today')
        
        # Try to find Today section ID from tasks (simple approach)
        if filtering_config.get('exclude_today_section', True):
            for task in tasks:
                task_section_id = task.get('section_id')
                if task_section_id:
                    # This is a simplified approach - in a full implementation we'd query sections API
                    # For now, we'll skip this optimization and rank all non-completed tasks
                    pass
        
        rankable_tasks = []
        for task in tasks:
            # Skip completed tasks
            if task.get('checked', False) or task.get('completed', False):
                continue
                
            # Skip Today section tasks if configured (avoid re-ranking already selected tasks)
            task_section_id = task.get('section_id')
            if today_section_id and task_section_id == today_section_id:
                continue
                
            # Skip tasks that only have excluded labels (e.g., only #link)
            # These are passive reference items, not actionable tasks for daily focus
            task_labels = set(task.get('labels', []))
            excluded_labels = {'link'}  # Labels that alone trigger exclusion from ranking
            
            if task_labels and task_labels.issubset(excluded_labels):
                if self.logger:
                    self.logger.info(f"RANK_FILTER_EXCLUDED: Task {task.get('id', 'unknown')} excluded (only has excluded labels: {task_labels})")
                continue
            
            # Future: Support for link-only tasks in special modes like 'research'
            # For now, exclusion applies globally across all modes
                
            rankable_tasks.append(task)
        
        if self.logger and filtering_config.get('log_candidates', True):
            completed_count = len([t for t in tasks if t.get('checked', False) or t.get('completed', False)])
            today_count = len([t for t in tasks if t.get('section_id') == today_section_id]) if today_section_id else 0
            excluded_labels = {'link'}
            excluded_count = len([t for t in tasks if set(t.get('labels', [])) and set(t.get('labels', [])).issubset(excluded_labels)])
            self.logger.info(f"RANK_FILTER: {len(rankable_tasks)} rankable tasks from {len(tasks)} total (excluded: {completed_count} completed, {today_count} in Today, {excluded_count} link-only)")
        
        if not rankable_tasks:
            if self.logger:
                self.logger.info("RANK_NO_CANDIDATES: No rankable tasks found (all completed, in Today section, or excluded)")
            return []
        
        # Score all tasks
        scored_tasks = []
        for task in rankable_tasks:
            try:
                score_result = self.calculate_composite_score(task, mode, config)
                
                scored_task = {
                    'task': task,
                    'score': score_result['score'],
                    'explanation': score_result['explanation'],
                    'components': score_result['components'],
                    'raw_components': score_result['raw_components']
                }
                scored_tasks.append(scored_task)
                
                # Log candidate if verbose logging enabled
                if config.get('logging', {}).get('log_candidates', True) and self.logger:
                    task_id = task.get('id', 'unknown')
                    task_content = task.get('content', 'No content')[:50]
                    self.logger.info(f"RANK_CANDIDATES: Task {task_id} → Score: {score_result['score']} | Reason: {score_result['explanation']} | Content: {task_content}")
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error scoring task {task.get('id', 'unknown')}: {e}")
                continue
        
        # Sort by score (descending)
        scored_tasks.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply limit
        ranked_tasks = scored_tasks[:limit]
        
        # Log ranking summary
        if ranked_tasks and self.logger:
            self.logger.info(f"RANK_SUMMARY: Selected {len(ranked_tasks)} tasks from {len(scored_tasks)} candidates (mode: {mode})")
            for i, ranked_task in enumerate(ranked_tasks, 1):
                task_id = ranked_task['task'].get('id', 'unknown')
                score = ranked_task['score']
                explanation = ranked_task['explanation']
                self.logger.info(f"RANK_TOP_{i}: Task {task_id} (score: {score}) - {explanation}")
        elif not ranked_tasks and self.logger:
            self.logger.info("RANK_EMPTY: No tasks qualified for ranking")
        
        return ranked_tasks
    
    def rank_with_gpt_explanations(self, tasks: List[Dict[str, Any]], mode: Optional[str] = None, limit: int = 3, config_override: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Rank tasks with GPT-enhanced explanations and reranking.
        
        Args:
            tasks: List of task dictionaries from Todoist API
            mode: Override mode (work, personal, weekend, evening, auto)
            limit: Maximum tasks to return (default: 3)
            config_override: Override default ranking config
            
        Returns:
            List of ranked tasks with GPT explanations and potential reranking
        """
        # Use override config or default
        config = config_override or self.ranking_config
        
        # Check if GPT reranking is enabled
        gpt_config = config.get('gpt_reranking', {})
        if not gpt_config.get('enabled', False):
            if self.logger:
                self.logger.info("GPT_RANK_DISABLED: GPT reranking is disabled in configuration")
            # Fall back to base ranking
            return self.rank(tasks, mode, limit, config_override)
        
        # First, get the base ranking with more candidates for reranking
        candidate_limit = gpt_config.get('candidate_limit', 10)
        base_candidates = max(limit * 2, candidate_limit)
        base_ranking = self.rank(tasks, mode, base_candidates, config_override)
        
        if not base_ranking:
            if self.logger:
                self.logger.info("GPT_RANK_EMPTY: No base ranking candidates for GPT enhancement")
            return []
        
        # Determine mode
        if mode is None:
            mode = self.config.get('default_mode', 'personal')
        elif mode == 'auto':
            mode = self._detect_mode()
        
        # Limit candidates based on configuration
        candidates_to_process = base_ranking[:candidate_limit]
        
        # Initialize cost tracking
        estimated_cost = 0.0
        cost_limit = gpt_config.get('cost_limit_per_run_usd', 0.10)
        
        # Log GPT ranking start with cost info
        if self.logger:
            self.logger.info(f"GPT_RANK_START: Processing {len(candidates_to_process)} candidates for GPT-enhanced ranking (mode: {mode})")
            self.logger.info(f"GPT_RANK_CONFIG: Model={gpt_config.get('model', 'gpt-3.5-turbo')}, Max tokens={gpt_config.get('max_tokens', 1000)}, Cost limit=${cost_limit:.3f}")
        
        # Get GPT explanations for top candidates
        gpt_enhanced_tasks = []
        for i, ranked_task in enumerate(candidates_to_process):
            task = ranked_task['task']
            base_score = ranked_task['score']
            base_explanation = ranked_task['explanation']
            
            # Check cost limit before making API call
            estimated_request_cost = self._estimate_gpt_request_cost(task, gpt_config)
            if estimated_cost + estimated_request_cost > cost_limit:
                if self.logger:
                    task_id = task.get('id', 'unknown')
                    self.logger.warning(f"GPT_RANK_COST_LIMIT: Stopping at task {task_id} | Estimated cost: ${estimated_cost + estimated_request_cost:.4f} > limit: ${cost_limit:.3f}")
                break
            
            # Get GPT explanation with cost tracking
            gpt_result = self._get_gpt_ranking_explanation(task, base_score, base_explanation, mode, gpt_config)
            
            # Update actual cost
            actual_cost = gpt_result.get('cost', estimated_request_cost)
            estimated_cost += actual_cost
            
            # Apply confidence threshold filtering
            confidence_threshold = gpt_config.get('confidence_threshold', 0.7)
            if gpt_result.get('confidence', 0.0) < confidence_threshold:
                if self.logger:
                    task_id = task.get('id', 'unknown')
                    confidence = gpt_result.get('confidence', 0.0)
                    self.logger.info(f"GPT_RANK_LOW_CONFIDENCE: Task {task_id} | Confidence: {confidence:.2f} < threshold: {confidence_threshold:.2f}")
                
                # Use base score for low confidence results
                gpt_result['rerank_score'] = base_score
                gpt_result['source'] = 'low_confidence_fallback'
            
            enhanced_task = {
                'task': task,
                'base_score': base_score,
                'base_explanation': base_explanation,
                'gpt_explanation': gpt_result.get('explanation', ''),
                'gpt_confidence': gpt_result.get('confidence', 0.0),
                'gpt_model': gpt_result.get('model', 'unknown'),
                'gpt_rerank_score': gpt_result.get('rerank_score', base_score),
                'final_score': gpt_result.get('rerank_score', base_score),
                'ranking_source': gpt_result.get('source', 'base_only'),
                'gpt_reasoning': gpt_result.get('reasoning', ''),
                'urgency_indicators': gpt_result.get('urgency_indicators', []),
                'mode_alignment': gpt_result.get('mode_alignment', ''),
                'recommendation': gpt_result.get('recommendation', 'standard'),
                'cost': actual_cost
            }
            
            gpt_enhanced_tasks.append(enhanced_task)
            
            # Log GPT ranking for each candidate with enhanced data
            if self.logger:
                task_id = task.get('id', 'unknown')
                task_content = task.get('content', 'No content')[:50]
                gpt_source = gpt_result.get('source', 'base_only')
                gpt_confidence = gpt_result.get('confidence', 0.0)
                gpt_model = gpt_result.get('model', 'unknown')
                
                self.logger.info(f"GPT_RANK_CANDIDATE: Task {task_id} → Base: {base_score:.3f} | GPT: {gpt_result.get('rerank_score', base_score):.3f} | Confidence: {gpt_confidence:.2f} | Model: {gpt_model} | Source: {gpt_source} | Cost: ${actual_cost:.4f}")
                self.logger.info(f"GPT_RANK_EXPLANATION: Task {task_id} | Base: {base_explanation} | GPT: {gpt_result.get('explanation', 'No explanation')} | Content: {task_content}")
                
                # Log additional structured data
                if gpt_result.get('urgency_indicators'):
                    self.logger.info(f"GPT_RANK_URGENCY: Task {task_id} | Indicators: {', '.join(gpt_result.get('urgency_indicators', []))}")
                
                if gpt_result.get('recommendation') != 'standard':
                    self.logger.info(f"GPT_RANK_RECOMMENDATION: Task {task_id} | {gpt_result.get('recommendation', 'standard').upper()}: {gpt_result.get('reasoning', '')}")
        
        # Sort by final score (which may include GPT reranking)
        gpt_enhanced_tasks.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Apply limit
        final_ranking = gpt_enhanced_tasks[:limit]
        
        # Log GPT ranking summary with cost information
        if self.logger:
            gpt_enhanced_count = len([t for t in gpt_enhanced_tasks if t['ranking_source'] == 'gpt_enhanced'])
            gpt_reranked_count = len([t for t in gpt_enhanced_tasks if t['ranking_source'] == 'gpt_reranked'])
            total_cost = sum(t.get('cost', 0.0) for t in gpt_enhanced_tasks)
            
            self.logger.info(f"GPT_RANK_SUMMARY: Selected {len(final_ranking)} tasks from {len(gpt_enhanced_tasks)} candidates | GPT enhanced: {gpt_enhanced_count}, reranked: {gpt_reranked_count} | Total cost: ${total_cost:.4f}")
            
            # Log top ranked tasks with enhanced details
            for i, ranked_task in enumerate(final_ranking, 1):
                task_id = ranked_task['task'].get('id', 'unknown')
                final_score = ranked_task['final_score']
                base_score = ranked_task['base_score']
                source = ranked_task['ranking_source']
                gpt_explanation = ranked_task['gpt_explanation']
                recommendation = ranked_task.get('recommendation', 'standard')
                
                score_change = f" (↑{final_score - base_score:.3f})" if final_score > base_score else f" (↓{base_score - final_score:.3f})" if final_score < base_score else ""
                
                self.logger.info(f"GPT_RANK_TOP_{i}: Task {task_id} (score: {final_score:.3f}{score_change}) - {source} | Rec: {recommendation} | GPT: {gpt_explanation}")
        
        return final_ranking
    
    def _get_gpt_ranking_explanation(self, task: Dict[str, Any], base_score: float, base_explanation: str, mode: str, gpt_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get GPT explanation and potential reranking for a task.
        
        Args:
            task: Task dictionary
            base_score: Base ranking score
            base_explanation: Base ranking explanation
            mode: Current mode (work, personal, etc.)
            
        Returns:
            Dictionary with GPT explanation, confidence, and potential rerank score
        """
        # Check if OpenAI is available
        if not OPENAI_AVAILABLE or not os.environ.get('OPENAI_API_KEY'):
            return {
                'explanation': base_explanation,
                'confidence': 0.0,
                'model': 'none',
                'rerank_score': base_score,
                'source': 'base_only'
            }
        
        # Handle mock mode for testing
        if os.environ.get('GPT_MOCK_MODE') or self.config.get('mock_mode', {}).get('enabled', False):
            return self._get_mock_gpt_explanation(task, base_score, base_explanation, mode)
        
        try:
            # Construct GPT prompt for ranking explanation
            prompt = self._construct_gpt_ranking_prompt(task, base_score, base_explanation, mode)
            
            # Get response from OpenAI
            response = self._call_openai_api(prompt)
            
            if response:
                return self._parse_gpt_ranking_response(response, task, base_score, base_explanation)
            else:
                return {
                    'explanation': base_explanation,
                    'confidence': 0.0,
                    'model': 'api_error',
                    'rerank_score': base_score,
                    'source': 'base_only'
                }
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"GPT ranking explanation error for task {task.get('id', 'unknown')}: {e}")
            
            return {
                'explanation': base_explanation,
                'confidence': 0.0,
                'model': 'error',
                'rerank_score': base_score,
                'source': 'base_only'
            }
    
    def _construct_gpt_ranking_prompt(self, task: Dict[str, Any], base_score: float, base_explanation: str, mode: str) -> str:
        """Construct JSON-based GPT prompt for ranking explanation."""
        task_content = task.get('content', 'No content')
        task_priority = task.get('priority', 4)
        task_due = task.get('due', {}).get('string', 'No due date') if task.get('due') else 'No due date'
        task_labels = ', '.join(task.get('labels', [])) or 'No labels'
        
        # Get user profile for context
        user_profile = self.config.get('user_profile', 'Productivity-focused user')
        
        # Build JSON prompt structure
        prompt_data = {
            "task": {
                "content": task_content,
                "priority": task_priority,
                "due_date": task_due,
                "labels": task.get('labels', []),
                "id": task.get('id', 'unknown')
            },
            "context": {
                "mode": mode,
                "user_profile": user_profile,
                "base_score": base_score,
                "base_explanation": base_explanation
            },
            "request": {
                "analyze_task_priority": True,
                "provide_explanation": True,
                "suggest_rerank_score": True,
                "confidence_assessment": True
            }
        }
        
        prompt = f"""You are a productivity assistant analyzing task prioritization. Please analyze this task and provide a JSON response.

INPUT DATA:
{json.dumps(prompt_data, indent=2)}

INSTRUCTIONS:
1. Analyze the task's priority in the context of the current mode ({mode})
2. Consider the user profile and base ranking explanation
3. Provide a clear, human-readable explanation for your recommendation
4. Assess your confidence in the analysis (0.0-1.0)
5. Suggest a rerank score (0.0-1.0) if the base score should be adjusted

REQUIRED JSON RESPONSE FORMAT:
{{
  "explanation": "Your human-readable explanation of why this task should/shouldn't be prioritized",
  "confidence": 0.85,
  "rerank_score": {base_score:.3f},
  "reasoning": "Brief technical reasoning for score adjustment",
  "urgency_indicators": ["list", "of", "detected", "urgency", "signals"],
  "mode_alignment": "how well this task fits the current mode",
  "recommendation": "prioritize|defer|standard"
}}

Respond ONLY with valid JSON. Do not include any text before or after the JSON response."""
        
        return prompt
    
    def _parse_gpt_ranking_response(self, response: str, task: Dict[str, Any], base_score: float, base_explanation: str) -> Dict[str, Any]:
        """Parse JSON-based GPT ranking response into structured format."""
        # Default values
        result = {
            'explanation': base_explanation,
            'confidence': 0.5,
            'model': self.config.get('model', 'gpt-3.5-turbo'),
            'rerank_score': base_score,
            'source': 'base_only',
            'reasoning': base_explanation,
            'urgency_indicators': [],
            'mode_alignment': 'unknown',
            'recommendation': 'standard'
        }
        
        try:
            # Clean response (remove any text before/after JSON)
            response = response.strip()
            
            # Find JSON content (handle cases where GPT adds extra text)
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_content = response[start_idx:end_idx]
                gpt_data = json.loads(json_content)
                
                # Extract structured data
                if 'explanation' in gpt_data:
                    result['explanation'] = str(gpt_data['explanation']).strip()
                    result['source'] = 'gpt_enhanced'
                
                if 'confidence' in gpt_data:
                    confidence = float(gpt_data['confidence'])
                    result['confidence'] = max(0.0, min(1.0, confidence))  # Clamp to 0-1
                
                if 'rerank_score' in gpt_data:
                    new_score = float(gpt_data['rerank_score'])
                    # Only accept reasonable score adjustments (within 0.0-1.0 range)
                    if 0.0 <= new_score <= 1.0:
                        result['rerank_score'] = new_score
                        if abs(new_score - base_score) > 0.05:  # Significant change
                            result['source'] = 'gpt_reranked'
                        else:
                            result['source'] = 'gpt_enhanced'
                
                # Extract additional structured fields
                if 'reasoning' in gpt_data:
                    result['reasoning'] = str(gpt_data['reasoning']).strip()
                
                if 'urgency_indicators' in gpt_data and isinstance(gpt_data['urgency_indicators'], list):
                    result['urgency_indicators'] = [str(x) for x in gpt_data['urgency_indicators'][:10]]  # Limit to 10
                
                if 'mode_alignment' in gpt_data:
                    result['mode_alignment'] = str(gpt_data['mode_alignment']).strip()
                
                if 'recommendation' in gpt_data:
                    rec = str(gpt_data['recommendation']).lower()
                    if rec in ['prioritize', 'defer', 'standard']:
                        result['recommendation'] = rec
                
                # Log successful JSON parsing
                if self.logger:
                    task_id = task.get('id', 'unknown')
                    self.logger.debug(f"GPT_JSON_PARSE_SUCCESS: Task {task_id} | Confidence: {result['confidence']:.2f} | Recommendation: {result['recommendation']}")
            
            else:
                # Fallback to regex parsing for non-JSON responses
                if self.logger:
                    task_id = task.get('id', 'unknown') 
                    self.logger.warning(f"GPT_JSON_PARSE_FALLBACK: Task {task_id} | No valid JSON found, using regex fallback")
                
                return self._parse_gpt_ranking_response_regex_fallback(response, task, base_score, base_explanation)
        
        except json.JSONDecodeError as e:
            if self.logger:
                task_id = task.get('id', 'unknown')
                self.logger.warning(f"GPT_JSON_PARSE_ERROR: Task {task_id} | JSON decode error: {e}")
            
            # Fallback to regex parsing
            return self._parse_gpt_ranking_response_regex_fallback(response, task, base_score, base_explanation)
        
        except Exception as e:
            if self.logger:
                task_id = task.get('id', 'unknown')
                self.logger.error(f"GPT_PARSE_ERROR: Task {task_id} | Unexpected error: {e}")
        
        return result
    
    def _parse_gpt_ranking_response_regex_fallback(self, response: str, task: Dict[str, Any], base_score: float, base_explanation: str) -> Dict[str, Any]:
        """Fallback regex-based parsing for non-JSON GPT responses."""
        import re
        
        # Default values
        result = {
            'explanation': base_explanation,
            'confidence': 0.5,
            'model': self.config.get('model', 'gpt-3.5-turbo'),
            'rerank_score': base_score,
            'source': 'base_only',
            'reasoning': base_explanation,
            'urgency_indicators': [],
            'mode_alignment': 'unknown',
            'recommendation': 'standard'
        }
        
        try:
            # Extract explanation
            explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?=CONFIDENCE:|RERANK_SCORE:|$)', response, re.DOTALL)
            if explanation_match:
                result['explanation'] = explanation_match.group(1).strip()
                result['source'] = 'gpt_enhanced'
            
            # Extract confidence
            confidence_match = re.search(r'CONFIDENCE:\s*([0-9]*\.?[0-9]+)', response)
            if confidence_match:
                result['confidence'] = float(confidence_match.group(1))
            
            # Extract rerank score
            rerank_match = re.search(r'RERANK_SCORE:\s*([0-9]*\.?[0-9]+)', response)
            if rerank_match:
                new_score = float(rerank_match.group(1))
                # Only accept reasonable score adjustments (within 0.0-1.0 range)
                if 0.0 <= new_score <= 1.0:
                    result['rerank_score'] = new_score
                    if abs(new_score - base_score) > 0.05:  # Significant change
                        result['source'] = 'gpt_reranked'
                    else:
                        result['source'] = 'gpt_enhanced'
        
        except Exception as e:
            if self.logger:
                task_id = task.get('id', 'unknown')
                self.logger.warning(f"GPT_REGEX_PARSE_ERROR: Task {task_id} | Error: {e}")
        
        return result
    
    def _get_mock_gpt_explanation(self, task: Dict[str, Any], base_score: float, base_explanation: str, mode: str) -> Dict[str, Any]:
        """Generate mock GPT explanation for testing with enhanced JSON structure."""
        content = task.get('content', '').lower()
        
        # Mock reasoning based on task content
        if 'urgent' in content or 'critical' in content:
            explanation = f"This task contains urgent indicators and should be prioritized in {mode} mode"
            confidence = 0.9
            rerank_score = min(base_score + 0.1, 1.0)
            source = 'gpt_reranked'
            reasoning = "Detected urgency keywords requiring immediate attention"
            urgency_indicators = ['urgent', 'critical']
            mode_alignment = "high priority alignment with current mode"
            recommendation = "prioritize"
        elif 'meeting' in content:
            explanation = f"Meeting tasks require coordination and should be prioritized in {mode} mode"
            confidence = 0.8
            rerank_score = base_score + 0.05
            source = 'gpt_enhanced'
            reasoning = "Meeting tasks require coordination and timing"
            urgency_indicators = ['meeting']
            mode_alignment = "requires time coordination"
            recommendation = "prioritize"
        elif mode == 'work' and any(word in content for word in ['work', 'project', 'deadline']):
            explanation = f"Work-related task aligns well with current {mode} mode"
            confidence = 0.7
            rerank_score = base_score + 0.03
            source = 'gpt_enhanced'
            reasoning = "Task content matches work mode context"
            urgency_indicators = ['deadline', 'project']
            mode_alignment = "strong alignment with work mode"
            recommendation = "standard"
        else:
            explanation = f"Standard task prioritization for {mode} mode"
            confidence = 0.6
            rerank_score = base_score
            source = 'gpt_enhanced'
            reasoning = "No specific urgency or mode indicators detected"
            urgency_indicators = []
            mode_alignment = "neutral alignment"
            recommendation = "standard"
        
        return {
            'explanation': explanation,
            'confidence': confidence,
            'model': 'mock',
            'rerank_score': rerank_score,
            'source': source,
            'reasoning': reasoning,
            'urgency_indicators': urgency_indicators,
            'mode_alignment': mode_alignment,
            'recommendation': recommendation,
            'cost': 0.0  # Mock responses have no cost
        }
    
    def _detect_mode(self) -> str:
        """
        Auto-detect current mode based on time and day.
        
        Returns:
            str: Detected mode (work, personal, weekend, evening)
        """
        from datetime import datetime
        
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # Weekend detection
        if weekday >= 5:  # Saturday, Sunday
            return 'weekend'
        
        # Evening detection (6 PM - 10 PM)
        if 18 <= hour <= 22:
            return 'evening'
        
        # Work hours detection (9 AM - 5 PM on weekdays)
        if 9 <= hour <= 17:
            return 'work'
        
        # Default to personal for other times
        return 'personal'
    
    def _estimate_gpt_request_cost(self, task: Dict[str, Any], gpt_config: Dict[str, Any]) -> float:
        """
        Estimate the cost of a GPT API request for ranking explanation.
        
        Args:
            task: Task dictionary
            gpt_config: GPT configuration with model and token limits
            
        Returns:
            float: Estimated cost in USD
        """
        model = gpt_config.get('model', 'gpt-3.5-turbo')
        max_tokens = gpt_config.get('max_tokens', 1000)
        
        # Rough estimation based on task content length and prompt structure
        task_content = task.get('content', '')
        base_prompt_tokens = 200  # Approximate tokens for base prompt structure
        task_tokens = len(task_content.split()) * 1.3  # Rough token estimation
        total_input_tokens = base_prompt_tokens + task_tokens
        
        # Model-specific pricing (approximate rates as of 2024)
        pricing = {
            'gpt-3.5-turbo': {'input': 0.0015 / 1000, 'output': 0.002 / 1000},  # per token
            'gpt-4': {'input': 0.03 / 1000, 'output': 0.06 / 1000},
            'gpt-4-turbo': {'input': 0.01 / 1000, 'output': 0.03 / 1000}
        }
        
        model_pricing = pricing.get(model, pricing['gpt-3.5-turbo'])
        
        # Estimate cost: input tokens + estimated output tokens
        estimated_output_tokens = min(max_tokens, 300)  # Most responses are shorter
        estimated_cost = (total_input_tokens * model_pricing['input'] + 
                         estimated_output_tokens * model_pricing['output'])
        
        return estimated_cost