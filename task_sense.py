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
        self.config = self._load_config(config_path)
        self.ranking_config = self._load_ranking_config(ranking_config_path)
        self.prompts = TaskSensePrompts() if PROMPTS_AVAILABLE else None
        self.logger = logging.getLogger('task_sense')
        
        # Engine metadata
        self.version = "v1.0"
        self.source = "TaskSense"
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load TaskSense configuration from JSON file."""
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
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Loaded ranking config from {config_path}")
            return config
        except FileNotFoundError:
            self.logger.warning(f"Ranking config file not found: {config_path}, using defaults")
            return self._get_default_ranking_config()
        except Exception as e:
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
                client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.3
                )
                
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
                    
            except Exception as e:
                self.logger.warning(f"OpenAI package error: {e}, falling back to HTTP")
        
        # Fallback to direct HTTP
        return self._call_openai_http(prompt, model)
    
    def _call_openai_http(self, prompt: str, model: str) -> Optional[str]:
        """Direct HTTP call to OpenAI API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
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
                self.logger.error(f"OpenAI HTTP error: {response.status_code} - {response.text}")
                
        except Exception as e:
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