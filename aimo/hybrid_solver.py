# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
AIMO3 Hybrid Solver — Neural + Symbolic Integration

Combines:
1. Neural pattern classifier (learned, not hardcoded)
2. Embedding-based RAG (semantic search)
3. Feedback learning (error correction)
4. Symbolic computation (exact formulas)

Phase 1 of Hybrid Learning System (Target: 85% accuracy)
"""

import sys
sys.path.insert(0, '.')

from typing import Dict, List, Any, Optional, Tuple
import json
from pathlib import Path

from aimo.neural_rag import NeuralRAGRetriever, create_neural_retriever
from aimo.pattern_classifier import NeuralPatternClassifier, PATTERN_TAXONOMY
from aimo.feedback_learner import FeedbackLearner
from aimo.mathlib_calculator import MathLibCalculator
from aimo.aimo3_solver import ParameterExtractor, AIMO3ComputationPatterns


class AIMO3HybridSolver:
    """
    Hybrid AIMO3 solver combining neural and symbolic methods.
    
    Architecture:
    1. Neural classifier predicts pattern from problem text
    2. Feedback learner corrects prediction based on error history
    3. Neural RAG retrieves relevant theorems semantically
    4. Symbolic calculator computes exact answer
    
    Learning mechanisms:
    - Classifier trains on solved examples
    - Feedback learner tracks errors and applies corrections
    - RAG embeddings capture semantic relationships
    """
    
    def __init__(
        self,
        corpus_path: str = "data_sources/leandojo/leandojo_benchmark_4/corpus.jsonl",
        embeddings_cache: Optional[str] = "aimo/neural_rag_cache.npy",
        classifier_dir: Optional[str] = "aimo/classifier",
        feedback_path: Optional[str] = "aimo/feedback_state.json",
        confidence_threshold: float = 0.5,
        verbose: bool = False
    ):
        """
        Initialize hybrid solver.
        
        Args:
            corpus_path: Path to LeanDojo corpus
            embeddings_cache: Path to save/load RAG embeddings
            classifier_dir: Path to save/load pattern classifier
            feedback_path: Path to save/load feedback state
            confidence_threshold: Minimum confidence for neural predictions
            verbose: Print progress
        """
        self.verbose = verbose
        self.confidence_threshold = confidence_threshold
        
        # Initialize components
        if self.verbose:
            print("Initializing Hybrid Solver components...", file=sys.stderr)
        
        # 1. Neural RAG retriever
        self.rag_retriever = self._init_rag(corpus_path, embeddings_cache)
        
        # 2. Neural pattern classifier
        self.classifier = self._init_classifier(classifier_dir)
        
        # 3. Feedback learner
        self.feedback_learner = FeedbackLearner(verbose=verbose)
        if feedback_path and Path(feedback_path).exists():
            self.feedback_learner.load(feedback_path)
        
        # 4. Symbolic calculator
        self.calculator = MathLibCalculator(verbose=verbose)
        
        # 5. Parameter extractor (from existing solver)
        self.param_extractor = ParameterExtractor()
        
        if self.verbose:
            print("Hybrid Solver ready!", file=sys.stderr)
    
    def _init_rag(
        self,
        corpus_path: str,
        embeddings_cache: Optional[str]
    ) -> Optional[NeuralRAGRetriever]:
        """Initialize neural RAG retriever."""
        if not Path(corpus_path).exists():
            if self.verbose:
                print(f"Warning: Corpus not found at {corpus_path}", file=sys.stderr)
                print("Using fallback keyword retrieval", file=sys.stderr)
            return None
        
        try:
            retriever = create_neural_retriever(
                corpus_path,
                embeddings_cache=embeddings_cache,
                verbose=self.verbose
            )
            return retriever
        except Exception as e:
            if self.verbose:
                print(f"Warning: RAG initialization failed: {e}", file=sys.stderr)
            return None
    
    def _init_classifier(
        self,
        classifier_dir: Optional[str]
    ) -> NeuralPatternClassifier:
        """Initialize neural pattern classifier."""
        classifier = NeuralPatternClassifier(verbose=self.verbose)
        
        if classifier_dir and Path(classifier_dir).exists():
            classifier.load(classifier_dir)
        else:
            # Load default training data
            self._load_default_training_data(classifier)
            classifier.train()
        
        return classifier
    
    def _load_default_training_data(
        self,
        classifier: NeuralPatternClassifier
    ):
        """Load default training data from solved problems."""
        # Baseline problems with known patterns
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
            ("Arithmetic sequence: 5th term is 17, 17th term is 53. Find 10th term", "arithmetic_sequence"),
            ("Find the coefficient of x³ in (1+x)^10", "binomial_expansion"),
            
            # Combinatorics
            ("How many 3-digit numbers have all distinct digits", "counting_digits"),
            ("Find the number of derangements of 5 objects", "derangement"),
            ("Find the 5th Catalan number", "catalan_number"),
            ("Find S(5,3), the Stirling number of the second kind", "stirling_number"),
            ("Find the number of integer partitions of 10", "integer_partition"),
            
            # Geometry
            ("Circle radius 5, chord at distance 3. Find chord length", "chord_length"),
            ("Find the area of a triangle with base 12 and height 8", "triangle_area"),
            ("Find the area of a triangle with sides 13, 14, 15", "heron_formula"),
            ("Find the circumradius of a triangle with sides 5, 12, 13", "circumcircle_radius"),
            ("From a point 13 units from the center of a circle with radius 5, find the tangent length", "tangent_length"),
            
            # Probability
            ("Fair coin flipped 4 times. Probability of exactly 2 heads?", "binomial_probability"),
            ("Two fair dice are rolled. Find the probability of getting a sum of 7", "dice_probability"),
        ]
        
        for problem, pattern in training_examples:
            classifier.add_training_example(problem, pattern)
    
    def solve(
        self,
        problem_text: str,
        learn: bool = True
    ) -> Tuple[Optional[int], str]:
        """
        Solve an AIMO3 problem using hybrid approach.
        
        Args:
            problem_text: The problem statement
            learn: If True, update feedback learner with results
            
        Returns:
            (answer, trace)
        """
        if self.verbose:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Problem: {problem_text[:60]}...", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
        
        # Step 1: Neural pattern classification
        predicted_pattern, confidence, domain = self.classifier.predict(
            problem_text,
            confidence_threshold=self.confidence_threshold
        )
        
        if self.verbose:
            print(f"🧠 Neural predict: {predicted_pattern} (domain: {domain}, confidence: {confidence:.3f})", file=sys.stderr)
        
        # Step 2: Feedback correction
        corrected_pattern, corrected_confidence = self.feedback_learner.correct_prediction(
            problem_text,
            predicted_pattern,
            confidence
        )
        
        if self.verbose and corrected_pattern != predicted_pattern:
            print(f"🔧 Feedback correction: {predicted_pattern} → {corrected_pattern}", file=sys.stderr)
        
        compute_func = corrected_pattern or predicted_pattern
        
        if not compute_func:
            if self.verbose:
                print("❌ No pattern matched", file=sys.stderr)
            return None, "no_pattern_matched"
        
        # Step 3: Parameter extraction
        params = self.param_extractor.extract(problem_text, compute_func)
        
        if self.verbose:
            print(f"🔢 Parameters: {params}", file=sys.stderr)
        
        # Step 4: Neural RAG retrieval
        theorems = []
        if self.rag_retriever:
            theorems = self.rag_retriever.retrieve_with_chaining(
                problem_text,
                top_k=3
            )
        
        if self.verbose and theorems:
            print(f"📚 Retrieved {len(theorems)} theorems:", file=sys.stderr)
            for thm in theorems[:2]:
                print(f"  • {thm['name']} (similarity: {thm.get('similarity', 0):.3f}, field: {thm['field']})", file=sys.stderr)
        
        # Step 5: Symbolic computation
        try:
            result = self.calculator.compute(compute_func, params)
            
            if self.verbose:
                print(f"✅ Computed result: {result}", file=sys.stderr)
            
            if result is not None:
                theorem_name = theorems[0]['name'] if theorems else 'pattern_matched'
                trace = f"{compute_func} via {theorem_name}"
                
                # Record success for learning
                if learn:
                    self.feedback_learner.record_success(
                        problem_text,
                        compute_func,
                        corrected_confidence
                    )
                
                return result, trace
            
            return None, f"computation_failed_{compute_func}"
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Computation error: {e}", file=sys.stderr)
            
            # Record error for learning
            if learn:
                self.feedback_learner.record_error(
                    problem_text,
                    compute_func,
                    "unknown",  # We don't know the correct pattern
                    result,
                    None,  # We don't know the correct answer during inference
                    corrected_confidence
                )
            
            return None, f"error_{str(e)}"
    
    def solve_with_ground_truth(
        self,
        problem_text: str,
        expected_answer: int,
        correct_pattern: str
    ) -> Tuple[Optional[int], str, bool]:
        """
        Solve a problem and learn from the result.
        
        Args:
            problem_text: The problem statement
            expected_answer: Ground truth answer
            correct_pattern: Ground truth pattern
            
        Returns:
            (answer, trace, is_correct)
        """
        # Solve
        answer, trace = self.solve(problem_text, learn=False)
        is_correct = answer == expected_answer
        
        # Determine predicted pattern from trace
        predicted_pattern = trace.split(' via ')[0] if ' via ' in trace else None
        
        # Learn from result
        if is_correct:
            self.feedback_learner.record_success(
                problem_text,
                correct_pattern,
                self.confidence_threshold
            )
        else:
            self.feedback_learner.record_error(
                problem_text,
                predicted_pattern,
                correct_pattern,
                answer,
                expected_answer,
                self.confidence_threshold
            )
        
        return answer, trace, is_correct
    
    def train_on_examples(
        self,
        examples: List[Tuple[str, int, str]]
    ):
        """
        Train the solver on a set of examples.
        
        Args:
            examples: List of (problem_text, expected_answer, correct_pattern)
        """
        if self.verbose:
            print(f"\nTraining on {len(examples)} examples...", file=sys.stderr)
        
        correct = 0
        
        for problem_text, expected_answer, correct_pattern in examples:
            answer, trace, is_correct = self.solve_with_ground_truth(
                problem_text,
                expected_answer,
                correct_pattern
            )
            
            if is_correct:
                correct += 1
            
            if self.verbose:
                status = "✅" if is_correct else "❌"
                print(f"  {status} {correct_pattern}: {answer} (expected {expected_answer})", file=sys.stderr)
        
        accuracy = correct / len(examples) if examples else 0
        
        if self.verbose:
            print(f"\nTraining accuracy: {accuracy:.3f}", file=sys.stderr)
            print(f"Feedback state: {len(self.feedback_learner.error_log)} errors logged", file=sys.stderr)
        
        return accuracy
    
    def save_state(self, output_dir: str = "aimo"):
        """
        Save all learning state to disk.
        
        Args:
            output_dir: Directory to save state
        """
        Path(output_dir).mkdir(exist_ok=True)
        
        # Save classifier
        if self.classifier:
            self.classifier.save(f"{output_dir}/classifier")
        
        # Save feedback state
        self.feedback_learner.save(f"{output_dir}/feedback_state.json")
        
        # Save RAG embeddings (if available)
        if self.rag_retriever and self.rag_retriever.embeddings is not None:
            self.rag_retriever.save_embeddings(f"{output_dir}/neural_rag_cache.npy")
        
        if self.verbose:
            print(f"Saved learning state to {output_dir}", file=sys.stderr)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get solver statistics.
        
        Returns:
            Dictionary with statistics
        """
        feedback_stats = self.feedback_learner.get_statistics()
        
        return {
            'feedback_learning': feedback_stats,
            'confidence_threshold': self.confidence_threshold,
            'rag_available': self.rag_retriever is not None,
            'classifier_trained': self.classifier.is_trained if self.classifier else False,
        }


def test_hybrid_solver():
    """Test the hybrid solver on baseline problems."""
    from aimo.expanded_test import EXPANDED_TESTS
    
    print("\n" + "="*80)
    print("  AIMO3 HYBRID SOLVER TEST")
    print("  Neural + Symbolic Integration")
    print("="*80)
    
    solver = AIMO3HybridSolver(verbose=True)
    
    # Test on baseline problems
    baseline_tests = [
        ("diff_squares", "Find the number of integers between 1 and 1000 that can be expressed as difference of squares", 750, "difference_of_squares"),
        ("vieta", "The quadratic x² - 5x + 6 = 0 has roots. Find sum of their squares", 13, "vieta_sum_squares"),
        ("geometric", "Geometric sequence: 3rd term is 12, 5th term is 48. Find 7th term", 192, "geometric_sequence"),
        ("probability", "Fair coin flipped 4 times. Probability of exactly 2 heads?", 3, "binomial_probability"),
        ("chord", "Circle radius 5, chord at distance 3. Find chord length", 8, "chord_length"),
        ("cube", "Find the smallest perfect cube divisible by 12", 216, "perfect_cube_divisible"),
        ("digits", "How many 3-digit numbers have all distinct digits", 648, "counting_digits"),
    ]
    
    correct = 0
    
    for name, problem, expected, pattern in baseline_tests:
        print(f"\n{'='*60}")
        print(f"Problem: {name}")
        print(f"Expected: {expected}")
        
        answer, trace = solver.solve(problem)
        is_correct = answer == expected
        
        status = "✅" if is_correct else "❌"
        print(f"Answer: {answer} (expected {expected}) {status}")
        print(f"Trace: {trace}")
        
        if is_correct:
            correct += 1
    
    print(f"\n{'='*80}")
    print(f"  RESULTS: {correct}/{len(baseline_tests)} correct ({100*correct/len(baseline_tests):.1f}%)")
    print(f"{'='*80}\n")
    
    # Show statistics
    stats = solver.get_statistics()
    print(f"Statistics: {stats}")
    
    return correct / len(baseline_tests)


if __name__ == "__main__":
    test_hybrid_solver()
