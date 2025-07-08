"""
TaskSense Prompt Templates - Mode-aware prompt generation system.

This module provides the TaskSensePrompts class that generates context-aware
prompts based on work modes and reasoning levels for optimal GPT responses.
"""

from typing import Dict, Any
from datetime import datetime


class TaskSensePrompts:
    """
    Mode-aware prompt template system for TaskSense.
    
    Generates prompts tailored to different work modes (personal, work, weekend)
    and reasoning levels (minimal, light, deep) for optimal labeling results.
    """
    
    def __init__(self):
        """Initialize the prompt template system."""
        self.version = "v1.0"
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize all prompt templates."""
        # Base prompts for different modes
        self.base_prompts = {
            "personal": {
                "base": "You are a productivity assistant helping with personal task management. Focus on personal life, family, health, and home-related activities.",
                "context": "Consider this is personal time - prioritize family, health, home, and personal development tasks."
            },
            "work": {
                "base": "You are a productivity assistant helping with professional task management. Focus on work projects, meetings, deadlines, and business activities.",
                "context": "Consider this is work time - prioritize professional tasks, meetings, and business objectives."
            },
            "weekend": {
                "base": "You are a productivity assistant helping with weekend task management. Focus on personal life, family time, home projects, and relaxation.",
                "context": "Consider this is weekend time - prioritize personal tasks, family activities, home projects, and leisure."
            },
            "evening": {
                "base": "You are a productivity assistant helping with evening task management. Focus on personal activities, family time, and preparation for the next day.",
                "context": "Consider this is evening time - prioritize personal tasks, family activities, and next-day preparation."
            },
            "default": {
                "base": "You are a productivity assistant helping with task management. Assign the most relevant labels based on task content.",
                "context": "Analyze the task content and assign appropriate labels based on context and priority."
            }
        }
        
        # Reasoning level instructions
        self.reasoning_instructions = {
            "minimal": "Respond with only the label name(s), separated by commas if multiple. No explanations.",
            "light": "Respond with the label name(s) on the first line, then provide a brief one-sentence explanation.",
            "deep": "Respond with the label name(s) on the first line, then provide detailed reasoning with confidence level (0.0-1.0)."
        }
        
        # Special mode enhancements
        self.mode_enhancements = {
            "weekend": {
                "preferences": ["home", "personal", "family", "health", "leisure"],
                "avoid": ["work", "meeting", "deadline"],
                "note": "Weekend tasks often involve personal care, family time, home projects, or relaxation."
            },
            "work": {
                "preferences": ["work", "meeting", "urgent", "followup", "project"],
                "avoid": ["personal", "home", "leisure"],
                "note": "Work hours focus on professional responsibilities, meetings, and business objectives."
            },
            "evening": {
                "preferences": ["personal", "home", "family", "admin"],
                "avoid": ["work", "meeting"],
                "note": "Evening tasks often involve personal care, family time, home tasks, or administrative work."
            }
        }
    
    def get_prompt(self, mode: str = "default", reasoning_level: str = "light") -> str:
        """
        Generate a prompt based on mode and reasoning level.
        
        Args:
            mode: Work mode (personal, work, weekend, evening, default)
            reasoning_level: Level of reasoning (minimal, light, deep)
            
        Returns:
            Formatted prompt string
        """
        # Get base prompt for mode
        mode_template = self.base_prompts.get(mode, self.base_prompts["default"])
        base_prompt = mode_template["base"]
        context = mode_template["context"]
        
        # Get reasoning instructions
        reasoning_instruction = self.reasoning_instructions.get(reasoning_level, self.reasoning_instructions["light"])
        
        # Build the prompt
        prompt_parts = [base_prompt, context]
        
        # Add mode-specific enhancements
        if mode in self.mode_enhancements:
            enhancement = self.mode_enhancements[mode]
            prompt_parts.append(enhancement["note"])
            
            if enhancement.get("preferences"):
                pref_str = ", ".join(enhancement["preferences"])
                prompt_parts.append(f"Prefer these labels when appropriate: {pref_str}")
        
        # Add reasoning instruction
        prompt_parts.append(reasoning_instruction)
        
        return "\n\n".join(prompt_parts)
    
    def get_time_based_mode(self, config: Dict[str, Any] = None) -> str:
        """
        Determine appropriate mode based on current time and config rules.
        
        Args:
            config: Optional configuration with time-based rules
            
        Returns:
            Suggested mode based on time of day and day of week
        """
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # Load time-based configuration
        if config and config.get('time_based_modes', {}).get('enabled', True):
            time_config = config['time_based_modes']
            work_hours = time_config.get('weekday_work_hours', [9, 17])
            evening_hours = time_config.get('evening_hours', [18, 22])
            weekend_days = time_config.get('weekend_days', [5, 6])
        else:
            # Default configuration
            work_hours = [9, 17]
            evening_hours = [18, 22]
            weekend_days = [5, 6]
        
        # Weekend detection
        if weekday in weekend_days:
            return "weekend"
        
        # Weekday time-based modes
        if work_hours[0] <= hour <= work_hours[1]:  # Business hours
            return "work"
        elif evening_hours[0] <= hour <= evening_hours[1]:  # Evening
            return "evening"
        else:  # Early morning or late night
            return "personal"
    
    def get_mode_suggestions(self, task_content: str) -> Dict[str, float]:
        """
        Suggest appropriate modes based on task content.
        
        Args:
            task_content: The task content to analyze
            
        Returns:
            Dictionary of mode -> confidence scores
        """
        content_lower = task_content.lower()
        suggestions = {}
        
        # Work mode indicators
        work_keywords = ["meeting", "project", "work", "deadline", "client", "business", "presentation", "call"]
        work_score = sum(1 for keyword in work_keywords if keyword in content_lower) / len(work_keywords)
        if work_score > 0:
            suggestions["work"] = min(work_score * 2, 1.0)
        
        # Personal mode indicators
        personal_keywords = ["personal", "family", "health", "doctor", "appointment", "self", "me"]
        personal_score = sum(1 for keyword in personal_keywords if keyword in content_lower) / len(personal_keywords)
        if personal_score > 0:
            suggestions["personal"] = min(personal_score * 2, 1.0)
        
        # Home/weekend mode indicators
        home_keywords = ["home", "house", "clean", "organize", "garden", "repair", "maintenance", "chores"]
        home_score = sum(1 for keyword in home_keywords if keyword in content_lower) / len(home_keywords)
        if home_score > 0:
            suggestions["weekend"] = min(home_score * 2, 1.0)
        
        # Default to personal if no strong indicators
        if not suggestions:
            suggestions["personal"] = 0.5
        
        return suggestions
    
    def get_reasoning_examples(self, reasoning_level: str) -> Dict[str, str]:
        """
        Get examples of expected output for different reasoning levels.
        
        Args:
            reasoning_level: The reasoning level to get examples for
            
        Returns:
            Dictionary with example inputs and expected outputs
        """
        examples = {
            "minimal": {
                "input": "Schedule dentist appointment for next week",
                "output": "personal, health"
            },
            "light": {
                "input": "Schedule dentist appointment for next week",
                "output": "personal, health\nThis is a personal health-related appointment."
            },
            "deep": {
                "input": "Schedule dentist appointment for next week",
                "output": "personal, health\nThis task involves scheduling a personal healthcare appointment, which is clearly personal in nature and specifically relates to health maintenance. The task is routine administrative work for personal care. Confidence: 0.9"
            }
        }
        
        return examples.get(reasoning_level, examples["light"])
    
    def validate_prompt(self, mode: str, reasoning_level: str) -> bool:
        """
        Validate that the given mode and reasoning level are supported.
        
        Args:
            mode: The mode to validate
            reasoning_level: The reasoning level to validate
            
        Returns:
            True if valid, False otherwise
        """
        valid_modes = set(self.base_prompts.keys())
        valid_reasoning = set(self.reasoning_instructions.keys())
        
        return mode in valid_modes and reasoning_level in valid_reasoning
    
    def get_supported_modes(self) -> Dict[str, str]:
        """
        Get all supported modes and their descriptions.
        
        Returns:
            Dictionary of mode -> description
        """
        return {
            "personal": "Personal life, family, health, and individual activities",
            "work": "Professional tasks, meetings, deadlines, and business activities",
            "weekend": "Weekend activities, home projects, family time, and relaxation",
            "evening": "Evening tasks, personal care, family time, and next-day preparation",
            "default": "General task management without specific mode context"
        }
    
    def get_supported_reasoning_levels(self) -> Dict[str, str]:
        """
        Get all supported reasoning levels and their descriptions.
        
        Returns:
            Dictionary of reasoning_level -> description
        """
        return {
            "minimal": "Labels only, no explanations",
            "light": "Labels with brief one-sentence explanation",
            "deep": "Labels with detailed reasoning and confidence scores"
        }