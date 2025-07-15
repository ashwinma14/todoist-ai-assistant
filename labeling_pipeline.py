"""
LabelingPipeline - Modular task labeling and processing pipeline

This module provides a clean, modular architecture for task labeling that separates
concerns and makes the system more maintainable and testable.
"""

import re
import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Import existing components
from main import apply_rules_to_task, extract_all_urls, get_domain_label, create_label_if_missing, update_task, log_task_action


@dataclass
class LabelingResult:
    """Result of labeling pipeline execution"""
    task_id: str
    task_content: str
    labels_applied: List[str] = field(default_factory=list)
    domain_labels: Set[str] = field(default_factory=set)
    rule_labels: Set[str] = field(default_factory=set)
    applied_rules: List[Dict[str, Any]] = field(default_factory=list)
    urls_found: List[Dict[str, str]] = field(default_factory=list)
    sections_to_move: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    explanations: Dict[str, str] = field(default_factory=dict)
    processing_time: float = 0.0
    soft_matched_labels: List[str] = field(default_factory=list)
    feedback_requested: bool = False
    feedback_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization to set timestamps"""
        self.timestamp = datetime.now()
    
    def has_new_labels(self) -> bool:
        """Check if any new labels were found"""
        return len(self.labels_applied) > 0
    
    def get_all_labels(self) -> Set[str]:
        """Get all labels found (rule + domain)"""
        return self.rule_labels | self.domain_labels
    
    def get_label_sources(self) -> Dict[str, str]:
        """Get mapping of label to source type"""
        sources = {}
        for rule in self.applied_rules:
            sources[rule['label']] = rule.get('source', 'unknown')
        for label in self.domain_labels:
            sources[label] = 'domain'
        return sources


class LabelingPipeline:
    """
    Modular pipeline for task labeling with clean separation of concerns.
    
    Pipeline stages:
    1. TaskSense AI labeling
    2. Rule-based labeling  
    3. Domain detection (URL analysis)
    4. Label application and section routing
    """
    
    def __init__(self, 
                 rules: List[Dict[str, Any]],
                 gpt_fallback: Optional[Dict[str, Any]] = None,
                 tasksense_config: Optional[Dict[str, Any]] = None,
                 mode: Optional[str] = None,
                 logger: Optional[logging.Logger] = None,
                 dry_run: bool = False,
                 verbose: bool = False,
                 confidence_threshold: float = 0.6,
                 soft_matching: bool = False,
                 interactive_feedback: bool = False):
        """
        Initialize the labeling pipeline.
        
        Args:
            rules: List of labeling rules
            gpt_fallback: GPT fallback configuration
            tasksense_config: TaskSense configuration
            mode: Processing mode (work, personal, etc.)
            logger: Logger instance
            dry_run: If True, don't actually apply changes
            verbose: Enable verbose logging
            confidence_threshold: Minimum confidence for label acceptance
            soft_matching: If True, suggest labels not in available_labels
            interactive_feedback: If True, enable interactive feedback loops
        """
        self.rules = rules
        self.gpt_fallback = gpt_fallback
        self.tasksense_config = tasksense_config
        self.mode = mode
        self.logger = logger or logging.getLogger(__name__)
        self.dry_run = dry_run
        self.verbose = verbose
        self.confidence_threshold = confidence_threshold
        self.soft_matching = soft_matching
        self.interactive_feedback = interactive_feedback
        
        # Statistics
        self.stats = {
            'tasks_processed': 0,
            'labels_applied': 0,
            'tasksense_used': 0,
            'rules_used': 0,
            'domains_detected': 0,
            'confidence_filtered': 0,
            'soft_matched': 0
        }
    
    def run(self, task: Dict[str, Any]) -> LabelingResult:
        """
        Execute the complete labeling pipeline for a task.
        
        Args:
            task: Task dictionary from Todoist API
            
        Returns:
            LabelingResult with all pipeline results
        """
        start_time = datetime.now()
        
        result = LabelingResult(
            task_id=task['id'],
            task_content=task['content']
        )
        
        try:
            # Stage 1: TaskSense + Rule-based labeling
            result = self._stage_intelligent_labeling(task, result)
            
            # Stage 2: Domain detection (URL analysis)
            result = self._stage_domain_detection(task, result)
            
            # Stage 3: Label consolidation and filtering
            result = self._stage_label_consolidation(task, result)
            
            # Stage 4: Application and section routing
            result = self._stage_application(task, result)
            
            # Stage 5: Interactive feedback check
            if self.interactive_feedback:
                result = self._check_feedback_needed(task, result)
            
            self.stats['tasks_processed'] += 1
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            self.logger.error(f"Pipeline error for task {task['id']}: {e}")
        
        finally:
            result.processing_time = (datetime.now() - start_time).total_seconds()
        
        return result
    
    def _stage_intelligent_labeling(self, task: Dict[str, Any], result: LabelingResult) -> LabelingResult:
        """
        Stage 1: Apply TaskSense and rule-based labeling
        """
        try:
            # Use existing apply_rules_to_task function but capture more details
            rule_labels, applied_rules = apply_rules_to_task(
                task, self.rules, self.gpt_fallback, self.logger, 
                self.mode, self.tasksense_config
            )
            
            result.rule_labels = set(rule_labels)
            result.applied_rules = applied_rules
            
            # Extract confidence scores and explanations
            for rule in applied_rules:
                label = rule['label']
                if 'confidence' in rule:
                    result.confidence_scores[label] = rule['confidence']
                if 'explanation' in rule:
                    result.explanations[label] = rule['explanation']
            
            # Track statistics
            if any(rule.get('source') == 'tasksense' for rule in applied_rules):
                self.stats['tasksense_used'] += 1
            if any(rule.get('source') == 'rule' for rule in applied_rules):
                self.stats['rules_used'] += 1
            
            if self.verbose:
                self.logger.info(f"Intelligent labeling found {len(rule_labels)} labels for task {task['id']}")
                
        except Exception as e:
            self.logger.error(f"Intelligent labeling failed for task {task['id']}: {e}")
            result.rule_labels = set()
            result.applied_rules = []
        
        return result
    
    def _stage_domain_detection(self, task: Dict[str, Any], result: LabelingResult) -> LabelingResult:
        """
        Stage 2: Detect domains from URLs in task content
        """
        try:
            content = task['content']
            has_any_link = re.search(r'https?://\S+', content)
            
            if has_any_link:
                urls = extract_all_urls(content)
                result.urls_found = urls
                
                if self.verbose:
                    url_count = len(urls)
                    self.logger.info(f"Found {url_count} URL{'s' if url_count != 1 else ''} in task {task['id']}")
                
                for url_info in urls:
                    domain_label = get_domain_label(url_info['url'])
                    if domain_label:
                        result.domain_labels.add(domain_label)
                        # Add confidence score for domain labels
                        result.confidence_scores[domain_label] = 0.95  # High confidence for domain detection
                        result.explanations[domain_label] = f"Detected from URL: {url_info['url']}"
                
                self.stats['domains_detected'] += len(result.domain_labels)
                
        except Exception as e:
            self.logger.error(f"Domain detection failed for task {task['id']}: {e}")
            result.domain_labels = set()
            result.urls_found = []
        
        return result
    
    def _stage_label_consolidation(self, task: Dict[str, Any], result: LabelingResult) -> LabelingResult:
        """
        Stage 3: Consolidate and filter labels based on confidence thresholds
        """
        try:
            # Combine all labels
            all_labels = result.rule_labels | result.domain_labels
            
            # Apply confidence filtering
            filtered_labels = set()
            for label in all_labels:
                confidence = result.confidence_scores.get(label, 0.8)  # Default confidence
                if confidence >= self.confidence_threshold:
                    filtered_labels.add(label)
                else:
                    self.stats['confidence_filtered'] += 1
                    if self.verbose:
                        self.logger.info(f"Filtered label '{label}' due to low confidence: {confidence:.2f}")
            
            # Handle soft matching - suggest labels not in available_labels
            if self.soft_matching:
                available_labels = set(self.tasksense_config.get('available_labels', []) if self.tasksense_config else [])
                
                # Find labels that aren't in available_labels but have good confidence
                soft_matches = []
                for label in filtered_labels:
                    if label not in available_labels and result.confidence_scores.get(label, 0.8) >= self.confidence_threshold:
                        soft_matches.append(label)
                        self.stats['soft_matched'] += 1
                
                result.soft_matched_labels = soft_matches
                
                if self.verbose and soft_matches:
                    self.logger.info(f"Soft matches found for task {task['id']}: {soft_matches}")
                
                # Remove soft matches from labels to apply if not in available_labels
                filtered_labels = {label for label in filtered_labels if label in available_labels or not available_labels}
            
            # Update result with filtered labels
            result.rule_labels = filtered_labels & result.rule_labels
            result.domain_labels = filtered_labels & result.domain_labels
            
            # Determine labels to apply (exclude existing)
            existing_labels = set(task.get("labels", []))
            new_labels = filtered_labels - existing_labels
            result.labels_applied = list(new_labels)
            
            if self.verbose and new_labels:
                self.logger.info(f"Will apply {len(new_labels)} new labels to task {task['id']}: {new_labels}")
            
        except Exception as e:
            self.logger.error(f"Label consolidation failed for task {task['id']}: {e}")
            result.labels_applied = []
        
        return result
    
    def _stage_application(self, task: Dict[str, Any], result: LabelingResult) -> LabelingResult:
        """
        Stage 4: Apply labels and handle section routing
        """
        try:
            if result.labels_applied:
                # Handle label creation for rules that require it
                for rule_info in result.applied_rules:
                    if rule_info.get('create_if_missing', False) and rule_info['label'] in result.labels_applied:
                        if not self.dry_run:
                            create_label_if_missing(rule_info['label'], self.logger)
                
                # Apply labels to task
                success = update_task(task, None, None, result.labels_applied, None, self.dry_run)
                result.success = success
                
                if success:
                    self.stats['labels_applied'] += len(result.labels_applied)
                    
                    # Log the labeling action
                    action = "LABELED_DRY_RUN" if self.dry_run else "LABELED"
                    first_url = result.urls_found[0]['url'] if result.urls_found else None
                    label_sources = [rule['source'] for rule in result.applied_rules if rule['label'] in result.labels_applied]
                    
                    log_task_action(self.logger, task['id'], task['content'], action, 
                                  labels=result.labels_applied, url=first_url, source=','.join(set(label_sources)))
                else:
                    result.error = "Failed to apply labels"
                    log_task_action(self.logger, task['id'], task['content'], "FAILED",
                                  error="Failed to apply labels")
            else:
                # No new labels to apply
                if result.get_all_labels():
                    log_task_action(self.logger, task['id'], task['content'], "LABELS_MATCHED_NO_NEW",
                                  reason="all matching labels already exist")
                else:
                    log_task_action(self.logger, task['id'], task['content'], "NO_LABELS",
                                  reason="no rules matched and no GPT suggestions")
            
            # Handle section routing from applied rules (for new labels)
            result.sections_to_move = []
            for rule_info in result.applied_rules:
                if rule_info.get('move_to'):  # Enable both TaskSense and rules.json section routing
                    if self.logger:
                        self.logger.info(f"SECTION_ROUTE_CANDIDATE: {rule_info['label']} → {rule_info['move_to']} (source: {rule_info.get('source', 'unknown')})")
                    result.sections_to_move.append({
                        'section_name': rule_info['move_to'],
                        'create_if_missing': rule_info.get('create_if_missing', False),
                        'rule_source': rule_info.get('matcher', 'unknown')
                    })
            
            # Universal section routing: Check ALL existing labels against rules
            # This ensures tasks with existing labels get routed even if no new labels were applied
            if not result.sections_to_move:  # Only if no routing from applied rules
                existing_labels = set(task.get('labels', []))
                current_section_id = task.get('section_id')
                
                # Only route tasks in the backlog (no section assigned)
                if current_section_id is not None:
                    if self.logger and existing_labels:
                        self.logger.info(f"SECTION_SKIP: Task {task['id']} already in section (section_id: {current_section_id}), skipping universal routing")
                elif existing_labels:
                    # Check each existing label against rules to find section routing candidates
                    for label in existing_labels:
                        for rule in self.rules:
                            if rule.get('label') == label and rule.get('move_to'):
                                if self.logger:
                                    self.logger.info(f"EXISTING_LABEL_ROUTE_CANDIDATE: {label} → {rule['move_to']} (priority: {rule.get('priority', 999)})")
                                result.sections_to_move.append({
                                    'section_name': rule['move_to'],
                                    'create_if_missing': rule.get('create_if_missing', False),
                                    'rule_source': f"existing_label:{label}"
                                })
                                break  # Only need one rule per label
            
        except Exception as e:
            self.logger.error(f"Label application failed for task {task['id']}: {e}")
            result.success = False
            result.error = str(e)
        
        return result
    
    def _check_feedback_needed(self, task: Dict[str, Any], result: LabelingResult) -> LabelingResult:
        """
        Stage 5: Check if interactive feedback is needed for this task
        """
        try:
            # Criteria for requesting feedback
            feedback_triggers = []
            
            # Low confidence labels
            low_confidence_labels = [
                label for label, confidence in result.confidence_scores.items() 
                if confidence < self.confidence_threshold + 0.1  # Close to threshold
            ]
            if low_confidence_labels:
                feedback_triggers.append(f"Low confidence labels: {low_confidence_labels}")
            
            # Soft matches (labels not in available_labels)
            if result.soft_matched_labels:
                feedback_triggers.append(f"Soft matches: {result.soft_matched_labels}")
            
            # No labels found
            if not result.labels_applied and not result.get_all_labels():
                feedback_triggers.append("No labels suggested")
            
            # Too many labels
            if len(result.labels_applied) > 3:
                feedback_triggers.append(f"Many labels suggested: {len(result.labels_applied)}")
            
            # Set feedback data if triggers exist
            if feedback_triggers:
                result.feedback_requested = True
                result.feedback_data = {
                    'triggers': feedback_triggers,
                    'suggested_labels': result.labels_applied,
                    'confidence_scores': result.confidence_scores,
                    'explanations': result.explanations,
                    'soft_matches': result.soft_matched_labels,
                    'task_preview': task['content'][:100]
                }
                
                if self.verbose:
                    self.logger.info(f"Feedback requested for task {task['id']}: {', '.join(feedback_triggers)}")
            
        except Exception as e:
            self.logger.error(f"Feedback check failed for task {task['id']}: {e}")
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline processing statistics"""
        return {
            **self.stats,
            'confidence_threshold': self.confidence_threshold,
            'mode': self.mode,
            'dry_run': self.dry_run
        }
    
    def reset_statistics(self):
        """Reset pipeline statistics"""
        self.stats = {
            'tasks_processed': 0,
            'labels_applied': 0,
            'tasksense_used': 0,
            'rules_used': 0,
            'domains_detected': 0,
            'confidence_filtered': 0,
            'soft_matched': 0
        }


class PipelineFactory:
    """Factory class for creating configured LabelingPipeline instances"""
    
    @staticmethod
    def create_from_config(rules: List[Dict[str, Any]], 
                          gpt_fallback: Optional[Dict[str, Any]] = None,
                          tasksense_config: Optional[Dict[str, Any]] = None,
                          cli_args: Optional[Any] = None,
                          logger: Optional[logging.Logger] = None) -> LabelingPipeline:
        """
        Create a LabelingPipeline from configuration and CLI arguments.
        
        Args:
            rules: List of labeling rules
            gpt_fallback: GPT fallback configuration
            tasksense_config: TaskSense configuration
            cli_args: Parsed CLI arguments
            logger: Logger instance
            
        Returns:
            Configured LabelingPipeline instance
        """
        # Extract configuration from CLI args
        mode = getattr(cli_args, 'mode', None)
        dry_run = getattr(cli_args, 'dry_run', False)
        verbose = getattr(cli_args, 'verbose', False)
        
        # Get confidence threshold from CLI args, TaskSense config, or default
        confidence_threshold = getattr(cli_args, 'confidence_threshold', None)
        if confidence_threshold is None:
            if tasksense_config:
                confidence_threshold = tasksense_config.get('confidence_threshold', 0.6)
            else:
                confidence_threshold = 0.6
        
        # Get soft matching from CLI args
        soft_matching = getattr(cli_args, 'soft_matching', False)
        
        return LabelingPipeline(
            rules=rules,
            gpt_fallback=gpt_fallback,
            tasksense_config=tasksense_config,
            mode=mode,
            logger=logger,
            dry_run=dry_run,
            verbose=verbose,
            confidence_threshold=confidence_threshold,
            soft_matching=soft_matching
        )