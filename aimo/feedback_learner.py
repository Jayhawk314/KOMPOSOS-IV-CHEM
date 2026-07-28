# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Feedback Learning Layer — Learn from Errors and Corrections

Tracks prediction errors and updates the system to avoid repeating them.
Implements meta-learning: learning how to learn from mistakes.

Phase 1C of Hybrid Learning System
"""

import sys
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict
from datetime import datetime


class ErrorRecord:
    """Record of a prediction error."""
    
    def __init__(
        self,
        problem_text: str,
        predicted_pattern: Optional[str],
        correct_pattern: str,
        predicted_answer: Optional[int],
        correct_answer: int,
        confidence: float,
        error_type: str,
        timestamp: Optional[str] = None
    ):
        self.problem_text = problem_text
        self.predicted_pattern = predicted_pattern
        self.correct_pattern = correct_pattern
        self.predicted_answer = predicted_answer
        self.correct_answer = correct_answer
        self.confidence = confidence
        self.error_type = error_type
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'problem_text': self.problem_text,
            'predicted_pattern': self.predicted_pattern,
            'correct_pattern': self.correct_pattern,
            'predicted_answer': self.predicted_answer,
            'correct_answer': self.correct_answer,
            'confidence': self.confidence,
            'error_type': self.error_type,
            'timestamp': self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorRecord':
        return cls(
            problem_text=data['problem_text'],
            predicted_pattern=data['predicted_pattern'],
            correct_pattern=data['correct_pattern'],
            predicted_answer=data.get('predicted_answer'),
            correct_answer=data['correct_answer'],
            confidence=data['confidence'],
            error_type=data['error_type'],
            timestamp=data.get('timestamp'),
        )


class FeedbackLearner:
    """
    Learns from prediction and computation errors.
    
    Mechanisms:
    1. Error logging: Track all mistakes
    2. Pattern correction: Learn when to override predictions
    3. Confidence calibration: Adjust confidence thresholds
    4. Feature extraction: Identify problem features that predict patterns
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize feedback learner.
        
        Args:
            verbose: Print progress
        """
        self.verbose = verbose
        
        self.error_log: List[ErrorRecord] = []
        self.correction_rules: Dict[str, Dict[str, Any]] = {}
        self.confidence_history: Dict[str, List[float]] = defaultdict(list)
        self.success_history: Dict[str, List[bool]] = defaultdict(list)
        
        # Pattern statistics
        self.pattern_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    def record_success(
        self,
        problem_text: str,
        pattern: str,
        confidence: float
    ):
        """
        Record a successful prediction.
        
        Args:
            problem_text: The problem statement
            pattern: The correct pattern
            confidence: Prediction confidence
        """
        self.pattern_stats[pattern]['correct'] += 1
        self.pattern_stats[pattern]['total'] += 1
        self.confidence_history[pattern].append(confidence)
        self.success_history[pattern].append(True)
    
    def record_error(
        self,
        problem_text: str,
        predicted_pattern: Optional[str],
        correct_pattern: str,
        predicted_answer: Optional[int],
        correct_answer: int,
        confidence: float
    ):
        """
        Record a prediction or computation error.
        
        Args:
            problem_text: The problem statement
            predicted_pattern: What the system predicted
            correct_pattern: The actual pattern
            predicted_answer: What the system computed
            correct_answer: The actual answer
            confidence: Prediction confidence
        """
        # Determine error type
        error_type = self._classify_error(
            predicted_pattern,
            correct_pattern,
            predicted_answer,
            correct_answer
        )
        
        # Create error record
        error = ErrorRecord(
            problem_text=problem_text,
            predicted_pattern=predicted_pattern,
            correct_pattern=correct_pattern,
            predicted_answer=predicted_answer,
            correct_answer=correct_answer,
            confidence=confidence,
            error_type=error_type,
        )
        
        self.error_log.append(error)
        
        # Update statistics
        if predicted_pattern:
            self.pattern_stats[predicted_pattern]['total'] += 1
        self.pattern_stats[correct_pattern]['total'] += 1
        self.confidence_history[correct_pattern].append(confidence)
        self.success_history[correct_pattern].append(False)
        
        # Learn correction rule
        self._learn_correction(error)
        
        if self.verbose:
            print(f"  📝 Recorded error: {error_type}", file=sys.stderr)
    
    def _classify_error(
        self,
        predicted_pattern: Optional[str],
        correct_pattern: str,
        predicted_answer: Optional[int],
        correct_answer: int
    ) -> str:
        """
        Classify the type of error.
        
        Returns:
            Error type string
        """
        if predicted_pattern is None:
            return 'pattern_not_found'
        
        if predicted_pattern != correct_pattern:
            return 'pattern_mismatch'
        
        if predicted_answer != correct_answer:
            return 'computation_error'
        
        return 'unknown'
    
    def _learn_correction(self, error: ErrorRecord):
        """
        Learn a correction rule from an error.
        
        Extracts features from the problem and creates a rule
        to correct similar mistakes in the future.
        """
        # Extract keywords from problem
        keywords = self._extract_keywords(error.problem_text)
        
        # Create correction rule
        rule_key = f"{error.predicted_pattern}→{error.correct_pattern}"
        
        if rule_key not in self.correction_rules:
            self.correction_rules[rule_key] = {
                'from_pattern': error.predicted_pattern,
                'to_pattern': error.correct_pattern,
                'keywords': set(keywords),
                'count': 0,
                'avg_confidence': 0.0,
            }
        
        rule = self.correction_rules[rule_key]
        rule['count'] += 1
        rule['keywords'].update(keywords)
        
        # Update average confidence
        n = rule['count']
        rule['avg_confidence'] = (rule['avg_confidence'] * (n - 1) + error.confidence) / n
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract important keywords from problem text.
        
        Returns:
            List of keywords
        """
        # Simple keyword extraction
        words = text.lower().split()
        
        # Filter: length > 3, not common words
        stop_words = {'the', 'and', 'for', 'are', 'that', 'this', 'with', 'find', 'number', 'when'}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return keywords[:10]  # Top 10 keywords
    
    def correct_prediction(
        self,
        problem_text: str,
        predicted_pattern: Optional[str],
        confidence: float
    ) -> Tuple[Optional[str], float]:
        """
        Apply correction rules to a prediction.
        
        Args:
            problem_text: The problem statement
            predicted_pattern: Original prediction
            confidence: Original confidence
            
        Returns:
            (corrected_pattern, corrected_confidence)
        """
        if predicted_pattern is None:
            return None, confidence
        
        # Extract keywords
        keywords = set(self._extract_keywords(problem_text))
        
        # Check for applicable correction rules
        best_correction = None
        best_score = 0
        
        for rule_key, rule in self.correction_rules.items():
            if rule['from_pattern'] != predicted_pattern:
                continue
            
            # Check keyword overlap
            overlap = len(keywords & rule['keywords'])
            
            if overlap >= 2 and rule['count'] >= 1:
                # Score by keyword overlap and rule confidence
                score = overlap * rule['count'] * rule['avg_confidence']
                
                if score > best_score:
                    best_score = score
                    best_correction = rule['to_pattern']
        
        if best_correction:
            if self.verbose:
                print(f"  🔧 Corrected: {predicted_pattern} → {best_correction}", file=sys.stderr)
            return best_correction, min(confidence + 0.1, 1.0)
        
        return predicted_pattern, confidence
    
    def get_pattern_accuracy(self, pattern: str) -> float:
        """
        Get historical accuracy for a pattern.
        
        Args:
            pattern: Pattern name
            
        Returns:
            Accuracy (0.0 to 1.0)
        """
        stats = self.pattern_stats.get(pattern, {'correct': 0, 'total': 0})
        
        if stats['total'] == 0:
            return 0.5  # Default
        
        return stats['correct'] / stats['total']
    
    def get_optimal_confidence_threshold(self, pattern: str) -> float:
        """
        Get optimal confidence threshold for a pattern.
        
        Based on historical confidence distributions for correct vs incorrect predictions.
        
        Args:
            pattern: Pattern name
            
        Returns:
            Optimal threshold
        """
        successes = self.confidence_history.get(pattern, [])
        
        if not successes:
            return 0.5  # Default
        
        # Use mean confidence as threshold
        return np.mean(successes)
    
    def suggest_training_examples(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Suggest problems for manual labeling (active learning).
        
        Returns problems where the system is uncertain or frequently wrong.
        
        Args:
            n: Number of suggestions
            
        Returns:
            List of suggested problems with metadata
        """
        suggestions = []
        
        # Find patterns with low accuracy
        low_acc_patterns = []
        for pattern, stats in self.pattern_stats.items():
            if stats['total'] >= 3:
                acc = stats['correct'] / stats['total']
                if acc < 0.7:
                    low_acc_patterns.append((pattern, acc))
        
        # Find errors that occurred multiple times
        repeated_errors = defaultdict(list)
        for error in self.error_log:
            key = f"{error.predicted_pattern}→{error.correct_pattern}"
            repeated_errors[key].append(error)
        
        for key, errors in repeated_errors.items():
            if len(errors) >= 2:
                # Add representative problem
                error = errors[0]
                suggestions.append({
                    'problem': error.problem_text,
                    'predicted': error.predicted_pattern,
                    'correct': error.correct_pattern,
                    'reason': f'Repeated error ({len(errors)} times)',
                })
        
        return suggestions[:n]
    
    def save(self, output_path: str):
        """
        Save learning state to disk.
        
        Args:
            output_path: Path to JSON file
        """
        data = {
            'error_log': [e.to_dict() for e in self.error_log],
            'correction_rules': {
                k: {**v, 'keywords': list(v['keywords'])}
                for k, v in self.correction_rules.items()
            },
            'pattern_stats': dict(self.pattern_stats),
            'confidence_history': dict(self.confidence_history),
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        if self.verbose:
            print(f"Saved learning state to {output_path}", file=sys.stderr)
    
    def load(self, input_path: str):
        """
        Load learning state from disk.
        
        Args:
            input_path: Path to JSON file
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.error_log = [ErrorRecord.from_dict(e) for e in data.get('error_log', [])]
        
        rules = data.get('correction_rules', {})
        self.correction_rules = {
            k: {**v, 'keywords': set(v['keywords'])}
            for k, v in rules.items()
        }
        
        self.pattern_stats = defaultdict(
            lambda: {'correct': 0, 'total': 0},
            {k: defaultdict(int, v) for k, v in data.get('pattern_stats', {}).items()}
        )
        
        self.confidence_history = defaultdict(list, data.get('confidence_history', {}))
        
        if self.verbose:
            print(f"Loaded {len(self.error_log)} errors, {len(self.correction_rules)} rules", file=sys.stderr)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get learning statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_errors = len(self.error_log)
        total_successes = sum(
            len(successes) for successes in self.success_history.values()
        )
        
        pattern_accuracies = {
            pattern: self.get_pattern_accuracy(pattern)
            for pattern in set(self.pattern_stats.keys())
        }
        
        return {
            'total_errors': total_errors,
            'total_successes': total_successes,
            'total_examples': total_errors + total_successes,
            'correction_rules': len(self.correction_rules),
            'pattern_accuracies': pattern_accuracies,
            'overall_accuracy': total_successes / max(1, total_errors + total_successes),
        }


if __name__ == "__main__":
    # Test feedback learner
    print("\n" + "="*80)
    print("  FEEDBACK LEARNER TEST")
    print("="*80)
    
    learner = FeedbackLearner(verbose=True)
    
    # Simulate some successes
    learner.record_success(
        "Find the number of integers between 1 and 1000 that can be expressed as difference of squares",
        "difference_of_squares",
        0.85
    )
    
    learner.record_success(
        "Fair coin flipped 4 times. Probability of exactly 2 heads?",
        "binomial_probability",
        0.90
    )
    
    # Simulate some errors
    learner.record_error(
        "Find φ(100), the Euler totient of 100",
        predicted_pattern="prime_factorization",
        correct_pattern="euler_totient",
        predicted_answer=None,
        correct_answer=40,
        confidence=0.65
    )
    
    learner.record_error(
        "Find the 5th Catalan number",
        predicted_pattern="integer_partition",
        correct_pattern="catalan_number",
        predicted_answer=7,
        correct_answer=42,
        confidence=0.55
    )
    
    # Test correction
    print("\n" + "="*80)
    print("  CORRECTION TEST")
    print("="*80)
    
    test_problem = "Find φ(50), the Euler totient function"
    predicted = "prime_factorization"
    confidence = 0.70
    
    print(f"\nProblem: {test_problem}")
    print(f"Original prediction: {predicted} (confidence: {confidence:.2f})")
    
    corrected_pattern, corrected_confidence = learner.correct_prediction(
        test_problem,
        predicted,
        confidence
    )
    
    print(f"Corrected prediction: {corrected_pattern} (confidence: {corrected_confidence:.2f})")
    
    # Statistics
    print("\n" + "="*80)
    print("  STATISTICS")
    print("="*80)
    
    stats = learner.get_statistics()
    print(f"Total examples: {stats['total_examples']}")
    print(f"Overall accuracy: {stats['overall_accuracy']:.2f}")
    print(f"Correction rules learned: {stats['correction_rules']}")
    print(f"Pattern accuracies: {stats['pattern_accuracies']}")
    
    print("\n" + "="*80 + "\n")
