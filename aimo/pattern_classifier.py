"""
Neural Pattern Classifier — Learn Problem Patterns from Examples

Replaces hardcoded regex with learned classification.
Uses sentence transformers + sklearn for pattern recognition.

Phase 1B of Hybrid Learning System
"""

import sys
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict

# Lazy imports
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: sklearn not installed. Using fallback.", file=sys.stderr)
    print("Install: pip install scikit-learn sentence-transformers", file=sys.stderr)


# Pattern taxonomy (50+ patterns organized by domain)
PATTERN_TAXONOMY = {
    # Number Theory (15)
    'number_theory': [
        'difference_of_squares',
        'modular_square_roots',
        'perfect_cube_divisible',
        'units_digit',
        'gcd_compute',
        'lcm_compute',
        'prime_factorization',
        'euler_totient',
        'wilson_theorem',
        'fermat_little_theorem',
        'chinese_remainder_theorem',
        'legendre_symbol',
        'divisor_sum',
        'perfect_number_check',
        'fibonacci_mod',
    ],
    
    # Algebra (12)
    'algebra': [
        'vieta_sum_squares',
        'geometric_sequence',
        'arithmetic_sequence',
        'polynomial_roots',
        'polynomial_division',
        'recurrence_solve',
        'generating_function',
        'binomial_expansion',
        'partial_fraction',
        'logarithm_solve',
        'exponential_solve',
        'system_solve',
    ],
    
    # Combinatorics (10)
    'combinatorics': [
        'counting_digits',
        'permutations',
        'combinations',
        'inclusion_exclusion',
        'pigeonhole',
        'circular_permutation',
        'derangement',
        'stirling_number',
        'catalan_number',
        'integer_partition',
    ],
    
    # Geometry (8)
    'geometry': [
        'chord_length',
        'triangle_area',
        'pythagorean',
        'heron_formula',
        'incircle_radius',
        'circumcircle_radius',
        'sector_area',
        'tangent_length',
    ],
    
    # Probability (5)
    'probability': [
        'binomial_probability',
        'dice_probability',
        'conditional_probability',
        'expected_value',
        'geometric_distribution',
    ],
}

# Flatten taxonomy for classification
ALL_PATTERNS = []
PATTERN_TO_DOMAIN = {}
for domain, patterns in PATTERN_TAXONOMY.items():
    ALL_PATTERNS.extend(patterns)
    for pattern in patterns:
        PATTERN_TO_DOMAIN[pattern] = domain


class NeuralPatternClassifier:
    """
    Neural classifier for mathematical problem patterns.
    
    Learns to map problem text → (domain, pattern) from examples.
    Falls back to regex-based classification if confidence is low.
    """
    
    def __init__(
        self,
        model_name: str = 'all-MiniLM-L6-v2',
        classifier_type: str = 'random_forest',
        verbose: bool = False
    ):
        """
        Initialize neural pattern classifier.
        
        Args:
            model_name: SentenceTransformer model
            classifier_type: 'random_forest', 'gradient_boosting', or 'logistic'
            verbose: Print progress
        """
        self.model_name = model_name
        self.classifier_type = classifier_type
        self.verbose = verbose
        
        self.model = None
        self.classifier = None
        self.training_data = []  # (problem_text, pattern_label)
        self.is_trained = False
        
        if SKLEARN_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load sentence transformer model."""
        if self.verbose:
            print(f"Loading SentenceTransformer: {self.model_name}", file=sys.stderr)
        
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Warning: Could not load model: {e}", file=sys.stderr)
            self.model = None
    
    def add_training_example(self, problem_text: str, pattern_label: str):
        """
        Add a training example.
        
        Args:
            problem_text: The problem statement
            pattern_label: The correct pattern (e.g., 'difference_of_squares')
        """
        if pattern_label not in ALL_PATTERNS:
            if self.verbose:
                print(f"Warning: Unknown pattern '{pattern_label}'", file=sys.stderr)
            return
        
        self.training_data.append((problem_text, pattern_label))
    
    def load_training_data(self, data_path: str):
        """
        Load training data from JSON file.
        
        Expected format:
        [
            {"problem": "...", "pattern": "difference_of_squares"},
            ...
        ]
        
        Args:
            data_path: Path to JSON file
        """
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            problem = item.get('problem', '')
            pattern = item.get('pattern', '')
            self.add_training_example(problem, pattern)
        
        if self.verbose:
            print(f"Loaded {len(self.training_data)} training examples", file=sys.stderr)
    
    def train(self, force_retrain: bool = False):
        """
        Train the classifier on accumulated training data.
        
        Args:
            force_retrain: If True, retrain even if already trained
        """
        if not SKLEARN_AVAILABLE:
            if self.verbose:
                print("sklearn not available, using fallback", file=sys.stderr)
            return
        
        if not self.model:
            if self.verbose:
                print("Model not loaded, cannot train", file=sys.stderr)
            return
        
        if len(self.training_data) < 10:
            if self.verbose:
                print(f"Need at least 10 examples, have {len(self.training_data)}", file=sys.stderr)
            return
        
        if self.is_trained and not force_retrain:
            if self.verbose:
                print("Already trained, skipping (use force_retrain=True)", file=sys.stderr)
            return
        
        if self.verbose:
            print(f"Training on {len(self.training_data)} examples...", file=sys.stderr)
        
        # Encode problems
        texts = [t[0] for t in self.training_data]
        labels = [t[1] for t in self.training_data]
        
        embeddings = self.model.encode(texts, batch_size=32, convert_to_numpy=True)
        
        # Train classifier
        if self.classifier_type == 'random_forest':
            self.classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                min_samples_split=2,
                class_weight='balanced',
                random_state=42,
            )
        elif self.classifier_type == 'gradient_boosting':
            self.classifier = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
            )
        elif self.classifier_type == 'logistic':
            self.classifier = LogisticRegression(
                max_iter=1000,
                class_weight='balanced',
                random_state=42,
            )
        else:
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        
        self.classifier.fit(embeddings, labels)
        self.is_trained = True
        
        # Evaluate on training set
        train_preds = self.classifier.predict(embeddings)
        train_acc = accuracy_score(labels, train_preds)
        
        if self.verbose:
            print(f"Training accuracy: {train_acc:.3f}", file=sys.stderr)
            print(f"Classes learned: {len(self.classifier.classes_)}", file=sys.stderr)
    
    def predict(
        self,
        problem_text: str,
        confidence_threshold: float = 0.5
    ) -> Tuple[Optional[str], float, str]:
        """
        Predict pattern for a problem.
        
        Args:
            problem_text: The problem statement
            confidence_threshold: Minimum confidence to use neural prediction
            
        Returns:
            (pattern, confidence, domain)
            If confidence < threshold, returns (None, confidence, 'unknown')
        """
        if not self.is_trained or not self.model:
            # Fallback to heuristic prediction
            return self._heuristic_predict(problem_text)
        
        # Encode problem
        embedding = self.model.encode([problem_text], convert_to_numpy=True)[0]
        
        # Predict
        probs = self.classifier.predict_proba([embedding])[0]
        max_idx = np.argmax(probs)
        max_prob = probs[max_idx]
        
        pattern = self.classifier.classes_[max_idx]
        domain = PATTERN_TO_DOMAIN.get(pattern, 'unknown')
        
        if self.verbose:
            print(f"  Neural predict: {pattern} (confidence: {max_prob:.3f})", file=sys.stderr)
        
        if max_prob >= confidence_threshold:
            return pattern, float(max_prob), domain
        else:
            # Below threshold, fall back to heuristic
            if self.verbose:
                print(f"  Confidence {max_prob:.3f} < {confidence_threshold}, using heuristic", file=sys.stderr)
            return self._heuristic_predict(problem_text)
    
    def _heuristic_predict(self, problem_text: str) -> Tuple[Optional[str], float, str]:
        """
        Fallback heuristic prediction (keyword-based).
        
        Returns:
            (pattern, confidence, domain)
        """
        problem_lower = problem_text.lower()
        
        # Simple keyword matching
        pattern_scores = defaultdict(float)
        
        # Number theory keywords
        if 'difference' in problem_lower and 'square' in problem_lower:
            pattern_scores['difference_of_squares'] += 0.8
        if 'mod' in problem_lower or 'remainder' in problem_lower:
            if 'square' in problem_lower:
                pattern_scores['modular_square_roots'] += 0.8
        if 'cube' in problem_lower and 'divisible' in problem_lower:
            pattern_scores['perfect_cube_divisible'] += 0.8
        if 'units digit' in problem_lower or 'last digit' in problem_lower:
            pattern_scores['units_digit'] += 0.8
        if 'gcd' in problem_lower or 'greatest common divisor' in problem_lower:
            pattern_scores['gcd_compute'] += 0.8
        if 'lcm' in problem_lower or 'least common multiple' in problem_lower:
            pattern_scores['lcm_compute'] += 0.8
        if 'phi' in problem_lower or 'totient' in problem_lower or 'coprime' in problem_lower:
            pattern_scores['euler_totient'] += 0.8
        if 'wilson' in problem_lower or ('factorial' in problem_lower and 'mod' in problem_lower):
            pattern_scores['wilson_theorem'] += 0.8
        if 'fermat' in problem_lower and 'little' in problem_lower:
            pattern_scores['fermat_little_theorem'] += 0.8
        if 'fibonacci' in problem_lower:
            pattern_scores['fibonacci_mod'] += 0.8
        
        # Algebra keywords
        if 'quadratic' in problem_lower or 'vieta' in problem_lower:
            if 'sum' in problem_lower and 'square' in problem_lower:
                pattern_scores['vieta_sum_squares'] += 0.8
        if 'geometric' in problem_lower and ('sequence' in problem_lower or 'progression' in problem_lower):
            pattern_scores['geometric_sequence'] += 0.8
        if 'arithmetic' in problem_lower and ('sequence' in problem_lower or 'progression' in problem_lower):
            pattern_scores['arithmetic_sequence'] += 0.8
        if 'polynomial' in problem_lower and 'root' in problem_lower:
            pattern_scores['polynomial_roots'] += 0.8
        if 'recurrence' in problem_lower or 'recursive' in problem_lower:
            pattern_scores['recurrence_solve'] += 0.8
        if 'binomial' in problem_lower and 'expansion' in problem_lower:
            pattern_scores['binomial_expansion'] += 0.8
        if 'log' in problem_lower and ('equation' in problem_lower or 'solve' in problem_lower):
            pattern_scores['logarithm_solve'] += 0.8
        
        # Combinatorics keywords
        if 'digit' in problem_lower and ('distinct' in problem_lower or 'count' in problem_lower):
            pattern_scores['counting_digits'] += 0.8
        if 'permutation' in problem_lower or 'arrangement' in problem_lower:
            pattern_scores['permutations'] += 0.8
        if 'combination' in problem_lower or 'choose' in problem_lower:
            pattern_scores['combinations'] += 0.8
        if 'inclusion' in problem_lower and 'exclusion' in problem_lower:
            pattern_scores['inclusion_exclusion'] += 0.8
        if 'pigeonhole' in problem_lower:
            pattern_scores['pigeonhole'] += 0.8
        if 'derangement' in problem_lower or ('no' in problem_lower and 'fixed' in problem_lower):
            pattern_scores['derangement'] += 0.8
        if 'catalan' in problem_lower:
            pattern_scores['catalan_number'] += 0.8
        if 'stirling' in problem_lower:
            pattern_scores['stirling_number'] += 0.8
        if 'partition' in problem_lower:
            pattern_scores['integer_partition'] += 0.8
        
        # Geometry keywords
        if 'chord' in problem_lower and ('circle' in problem_lower or 'radius' in problem_lower):
            pattern_scores['chord_length'] += 0.8
        if 'triangle' in problem_lower and 'area' in problem_lower:
            pattern_scores['triangle_area'] += 0.8
        if 'pythagorean' in problem_lower or ('right' in problem_lower and 'triangle' in problem_lower):
            pattern_scores['pythagorean'] += 0.8
        if 'heron' in problem_lower:
            pattern_scores['heron_formula'] += 0.8
        if 'incircle' in problem_lower or 'inradius' in problem_lower:
            pattern_scores['incircle_radius'] += 0.8
        if 'circumcircle' in problem_lower or 'circumradius' in problem_lower:
            pattern_scores['circumcircle_radius'] += 0.8
        if 'sector' in problem_lower:
            pattern_scores['sector_area'] += 0.8
        if 'tangent' in problem_lower and ('circle' in problem_lower or 'length' in problem_lower):
            pattern_scores['tangent_length'] += 0.8
        
        # Probability keywords
        if 'probability' in problem_lower and ('coin' in problem_lower or 'flip' in problem_lower):
            pattern_scores['binomial_probability'] += 0.8
        if 'probability' in problem_lower and 'dice' in problem_lower:
            pattern_scores['dice_probability'] += 0.8
        if 'expected value' in problem_lower or 'expectation' in problem_lower:
            pattern_scores['expected_value'] += 0.8
        if 'geometric distribution' in problem_lower:
            pattern_scores['geometric_distribution'] += 0.8
        
        if not pattern_scores:
            return None, 0.0, 'unknown'
        
        # Get best pattern
        best_pattern = max(pattern_scores, key=pattern_scores.get)
        best_score = pattern_scores[best_pattern]
        best_domain = PATTERN_TO_DOMAIN.get(best_pattern, 'unknown')
        
        if self.verbose:
            print(f"  Heuristic predict: {best_pattern} (confidence: {best_score:.3f})", file=sys.stderr)
        
        return best_pattern, best_score, best_domain
    
    def predict_batch(
        self,
        problem_texts: List[str],
        confidence_threshold: float = 0.5
    ) -> List[Tuple[Optional[str], float, str]]:
        """
        Predict patterns for multiple problems.
        
        Args:
            problem_texts: List of problem statements
            confidence_threshold: Minimum confidence
            
        Returns:
            List of (pattern, confidence, domain) tuples
        """
        return [
            self.predict(text, confidence_threshold)
            for text in problem_texts
        ]
    
    def evaluate(
        self,
        test_data: List[Tuple[str, str]]
    ) -> Dict[str, float]:
        """
        Evaluate classifier on test data.
        
        Args:
            test_data: List of (problem_text, true_label) tuples
            
        Returns:
            Dictionary with accuracy metrics
        """
        if not self.is_trained:
            return {'accuracy': 0.0, 'message': 'Not trained'}
        
        correct = 0
        predictions = []
        true_labels = []
        
        for problem, true_label in test_data:
            pred_pattern, confidence, _ = self.predict(problem)
            predictions.append(pred_pattern)
            true_labels.append(true_label)
            
            if pred_pattern == true_label:
                correct += 1
        
        accuracy = correct / len(test_data) if test_data else 0.0
        
        return {
            'accuracy': accuracy,
            'correct': correct,
            'total': len(test_data),
        }
    
    def save(self, output_dir: str):
        """Save trained classifier and training data."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Save training data
        training_json = [
            {'problem': t[0], 'pattern': t[1]}
            for t in self.training_data
        ]
        
        with open(os.path.join(output_dir, 'training_data.json'), 'w') as f:
            json.dump(training_json, f, indent=2)
        
        # Save model (if sklearn available)
        if self.is_trained and self.classifier:
            import joblib
            joblib.dump(self.classifier, os.path.join(output_dir, 'classifier.joblib'))
        
        if self.verbose:
            print(f"Saved to {output_dir}", file=sys.stderr)
    
    def load(self, input_dir: str):
        """Load trained classifier and training data."""
        import os
        
        # Load training data
        training_path = os.path.join(input_dir, 'training_data.json')
        if os.path.exists(training_path):
            with open(training_path, 'r', encoding='utf-8') as f:
                training_json = json.load(f)
            
            self.training_data = [
                (item['problem'], item['pattern'])
                for item in training_json
            ]
            
            if self.verbose:
                print(f"Loaded {len(self.training_data)} training examples", file=sys.stderr)
        
        # Load classifier
        classifier_path = os.path.join(input_dir, 'classifier.joblib')
        if os.path.exists(classifier_path):
            import joblib
            self.classifier = joblib.load(classifier_path)
            self.is_trained = True
            
            if self.verbose:
                print(f"Loaded trained classifier", file=sys.stderr)


# Auto-generate training data from solved problems
def generate_training_data_from_solutions(
    solver,
    problems: List[Tuple[str, str, str]],
    output_path: str
):
    """
    Generate training data from solved problems.
    
    Args:
        solver: AIMO3RAGSolver instance
        problems: List of (id, problem_text, pattern_label)
        output_path: Path to save training data
    """
    training_data = []
    
    for prob_id, problem_text, pattern_label in problems:
        training_data.append({
            'problem': problem_text,
            'pattern': pattern_label,
        })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2)
    
    print(f"Generated {len(training_data)} training examples → {output_path}")


if __name__ == "__main__":
    # Test neural pattern classifier
    print("\n" + "="*80)
    print("  NEURAL PATTERN CLASSIFIER TEST")
    print("="*80)
    
    classifier = NeuralPatternClassifier(verbose=True)
    
    # Create synthetic training data
    training_examples = [
        # Number Theory
        ("Find the number of integers between 1 and 1000 that can be expressed as difference of squares", "difference_of_squares"),
        ("Find n ≤ 1000 such that n² has remainder 1 when divided by 1000", "modular_square_roots"),
        ("Find the smallest perfect cube divisible by 12", "perfect_cube_divisible"),
        ("Find the units digit of 7^2024", "units_digit"),
        ("Find gcd(48, 18)", "gcd_compute"),
        ("Find φ(100), the Euler totient of 100", "euler_totient"),
        ("Find 16! mod 17 using Wilson's theorem", "wilson_theorem"),
        ("Find F_100 mod 1000", "fibonacci_mod"),
        
        # Algebra
        ("The quadratic x² - 5x + 6 = 0 has roots. Find sum of their squares", "vieta_sum_squares"),
        ("Geometric sequence: 3rd term is 12, 5th term is 48. Find 7th term", "geometric_sequence"),
        ("Find the coefficient of x³ in (1+x)^10", "binomial_expansion"),
        
        # Combinatorics
        ("How many 3-digit numbers have all distinct digits", "counting_digits"),
        ("Find the number of derangements of 5 objects", "derangement"),
        ("Find the 5th Catalan number", "catalan_number"),
        
        # Geometry
        ("Circle radius 5, chord at distance 3. Find chord length", "chord_length"),
        ("Find the area of a triangle with base 12 and height 8", "triangle_area"),
        
        # Probability
        ("Fair coin flipped 4 times. Probability of exactly 2 heads?", "binomial_probability"),
    ]
    
    # Add training examples
    for problem, pattern in training_examples:
        classifier.add_training_example(problem, pattern)
    
    # Train
    classifier.train()
    
    # Test
    test_problems = [
        ("Find the number of integers between 1 and 500 that can be expressed as difference of squares", "difference_of_squares"),
        ("Find the remainder when 3^100 is divided by 17", "fermat_little_theorem"),
        ("Find the area of triangle with sides 5, 12, 13", "heron_formula"),
    ]
    
    print("\n" + "="*80)
    print("  PREDICTION TESTS")
    print("="*80)
    
    for problem, expected in test_problems:
        pattern, confidence, domain = classifier.predict(problem)
        status = "✅" if pattern == expected else "❌"
        print(f"\nProblem: {problem[:60]}...")
        print(f"Predicted: {pattern} (domain: {domain}, confidence: {confidence:.3f})")
        print(f"Expected: {expected} {status}")
    
    print("\n" + "="*80 + "\n")
