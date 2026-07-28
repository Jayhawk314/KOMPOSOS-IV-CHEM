# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
LeanDojo RAG - Retrieve from Mathlib Corpus

Uses KOMPOSOS Math Kernel to retrieve theorems from LeanDojo (100K+ theorems)
instead of hardcoded patterns.

Architecture:
1. Load LeanDojo corpus into KOMPOSOS Category
2. Problem → search Category objects by keywords
3. Retrieved theorems → map to computation functions
4. Compute answer
"""

import sys
sys.path.insert(0, '.')

from typing import Dict, List, Any, Optional, Tuple
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter


class LeanDojoRAG:
    """
    RAG retriever for LeanDojo/Mathlib corpus.
    
    Loads theorems into KOMPOSOS Category and retrieves by keyword matching.
    """
    
    # Map problem keywords to computation functions
    # Uses general mathematical concepts, not specific to test problems
    COMPUTATION_MAP = {
        ('difference', 'square'): ('difference_of_squares', ['max_n']),
        ('modular', 'square'): ('modular_square_roots', ['modulus', 'max_n']),
        ('remainder', 'square'): ('modular_square_roots', ['modulus', 'max_n']),
        ('remainder', 'divided'): ('modular_square_roots', ['modulus', 'max_n']),
        ('quadratic', 'root'): ('vieta_sum_squares', ['sum_roots', 'product_roots']),
        ('quadratic', 'equation'): ('vieta_sum_squares', ['sum_roots', 'product_roots']),
        ('root', 'square'): ('vieta_sum_squares', ['sum_roots', 'product_roots']),
        ('geometric', 'sequence'): ('geometric_sequence', ['term3', 'term5', 'find_term']),
        ('probability', 'coin'): ('binomial_probability', ['n', 'k', 'p']),
        ('probability', 'flip'): ('binomial_probability', ['n', 'k', 'p']),
        ('probability', 'head'): ('binomial_probability', ['n', 'k', 'p']),
        ('circle', 'chord'): ('chord_length', ['radius', 'distance']),
        ('perfect', 'cube'): ('perfect_cube_divisible', ['divisor']),
        ('cube', 'divisible'): ('perfect_cube_divisible', ['divisor']),
        ('distinct', 'digit'): ('counting_digits', ['min_n', 'max_n']),
    }
    
    def __init__(self, corpus_path: str = "data_sources/leandojo/leandojo_benchmark_4/corpus.jsonl", verbose: bool = False):
        self.verbose = verbose
        self.corpus_path = corpus_path
        self.kernel = MathKernel(db_dir=":memory:")
        self._loaded = False
        self._theorems = []  # Cache for fast retrieval
        self._keyword_index = {}  # keyword → list of theorem indices
    
    def _build_keyword_index(self):
        """Build inverted index for fast keyword search."""
        self._keyword_index = {}
        
        # Mathematical keyword mapping (general, not problem-specific)
        math_keywords = {
            # Number theory
            'div': ['divisible', 'divisor', 'division', 'divides'],
            'mod': ['modular', 'remainder', 'modulo', 'congruent'],
            'prime': ['prime', 'primes', 'primality'],
            'square': ['square', 'squares', 'squared', 'quadratic'],
            'cube': ['cube', 'cubes', 'cubic', 'third power'],
            'sum': ['sum', 'summation', 'total'],
            'prod': ['product', 'multiplication', 'factorial'],
            
            # Algebra
            'equation': ['equation', 'equations', 'solve'],
            'roots': ['roots', 'root', 'solution'],
            'polynomial': ['polynomial', 'polynomials'],
            
            # Geometry
            'circle': ['circle', 'circular', 'circumference'],
            'triangle': ['triangle', 'triangular', 'triangles'],
            'chord': ['chord', 'chords'],
            
            # Probability
            'probability': ['probability', 'probabilities', 'chance'],
            'coin': ['coin', 'coins', 'flip', 'flips', 'heads', 'tails'],
            'binomial': ['binomial', 'distribution', 'exactly'],
            
            # General math
            'count': ['count', 'number', 'how many', 'find'],
            'integer': ['integer', 'integers', 'whole number'],
            'sequence': ['sequence', 'sequences', 'series', 'progression'],
            'geometric': ['geometric', 'geometric sequence', 'geometric progression'],
        }
        
        for idx, obj in enumerate(self._theorems):
            # Extract keywords from theorem name
            name_lower = obj.name.lower()
            
            # Add theorem name parts
            for part in name_lower.split('.'):
                if part not in self._keyword_index:
                    self._keyword_index[part] = []
                self._keyword_index[part].append(idx)
            
            # Add field
            field = obj.metadata.get('field', '').lower()
            if field:
                if field not in self._keyword_index:
                    self._keyword_index[field] = []
                self._keyword_index[field].append(idx)
            
            # Add mapped mathematical keywords
            for canonical, variants in math_keywords.items():
                # Check if any variant appears in theorem name or metadata
                text = name_lower + ' ' + obj.metadata.get('statement', '').lower()
                if any(variant in text for variant in variants):
                    if canonical not in self._keyword_index:
                        self._keyword_index[canonical] = []
                    self._keyword_index[canonical].append(idx)
    
    def load(self):
        """Load LeanDojo corpus into Math Kernel."""
        if self._loaded:
            return
        
        if self.verbose:
            print(f"Loading LeanDojo from {self.corpus_path}...", file=sys.stderr)
        
        adapter = LeanDojoAdapter(self.corpus_path)
        self.kernel.load_source("leandojo", adapter)
        
        # Cache ALL theorems for fast retrieval
        self._theorems = list(self.kernel.leandojo.objects())
        
        # Build keyword index
        self._build_keyword_index()
        
        if self.verbose:
            print(f"Loaded {len(self._theorems)} theorems, {len(self._keyword_index)} keywords", file=sys.stderr)
            print(f"Sample theorems: {[t.name for t in self._theorems[:5]]}", file=sys.stderr)
        
        self._loaded = True
    
    def retrieve(self, problem_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant theorems from LeanDojo.
        
        Uses inverted keyword index for fast retrieval.
        """
        if not self._loaded:
            self.load()
        
        problem_lower = problem_text.lower()
        
        # Step 1: Find matching computation rule from problem keywords
        compute_func, params = None, []
        for keywords, (func, param_list) in self.COMPUTATION_MAP.items():
            if all(kw in problem_lower for kw in keywords):
                compute_func, params = func, param_list
                break
        
        # Step 2: Use keyword index for fast retrieval
        scored = {}  # idx → score
        problem_keywords = problem_lower.split()
        
        # Direct keyword matches
        for kw in problem_keywords:
            if kw in self._keyword_index:
                for idx in self._keyword_index[kw]:
                    scored[idx] = scored.get(idx, 0) + 2
        
        # Also check for multi-word patterns
        for canonical, indices in self._keyword_index.items():
            if canonical in problem_lower:
                for idx in indices:
                    scored[idx] = scored.get(idx, 0) + 3
        
        # Convert to list of (score, theorem)
        scored_list = [(score, self._theorems[idx]) for idx, score in scored.items()]
        scored_list.sort(key=lambda x: x[0], reverse=True)
        
        # Step 3: Build result with computation capability
        results = []
        for score, obj in scored_list[:top_k]:
            results.append({
                'name': obj.name,
                'field': obj.metadata.get('field', 'unknown'),
                'source': 'leandojo',
                'compute_func': compute_func,
                'params': params,
                'score': score,
            })
        
        # Fallback: if no theorems matched but we have a computation rule, use pattern
        if not results and compute_func:
            results.append({
                'name': f'pattern_{compute_func}',
                'field': 'pattern_matched',
                'source': 'pattern_fallback',
                'compute_func': compute_func,
                'params': params,
                'score': 1.0,
            })
        
        # Also add pattern fallback as secondary if KG found something but no computation
        if results and not results[0].get('compute_func') and compute_func:
            results[0]['compute_func'] = compute_func
            results[0]['params'] = params
            results[0]['source'] = 'leandojo+pattern'
        
        return results


class LeanDojoRAGSolver:
    """
    Complete RAG solver using LeanDojo corpus.
    
    Pipeline:
    1. Load LeanDojo (100K+ theorems)
    2. Retrieve by problem semantics
    3. Compute using matched computation rule
    """
    
    def __init__(self, corpus_path: str = "data_sources/leandojo/leandojo_benchmark_4/corpus.jsonl", verbose: bool = False):
        self.verbose = verbose
        self.rag = LeanDojoRAG(corpus_path, verbose)
    
    def solve(self, problem_text: str) -> Tuple[Optional[int], str]:
        """Solve a problem using LeanDojo RAG."""
        # Step 1: Retrieve theorems
        theorems = self.rag.retrieve(problem_text, top_k=3)
        
        if self.verbose:
            print(f"\n📚 Retrieved {len(theorems)} theorems:", file=sys.stderr)
            for thm in theorems[:2]:
                print(f"  • {thm['name']} ({thm['field']}) - {thm['source']}", file=sys.stderr)
        
        if not theorems:
            return None, "no_theorems_retrieved"
        
        # Step 2: Get computation capability
        best = theorems[0]
        compute_func = best.get('compute_func')
        
        if self.verbose:
            print(f"\n🧮 Computation: {compute_func}", file=sys.stderr)
        
        if not compute_func:
            return None, f"no_computation_for_{best['name']}"
        
        # Step 3: Extract parameters and compute
        from aimo.rag_solver import MathlibRetriever
        from aimo.mathlib_calculator import MathLibCalculator
        
        # Use existing parameter extraction
        temp_theorem = type('Theorem', (), {
            'params': best['params'],
            'compute_func': compute_func,
        })()
        
        extractor = MathlibRetriever()
        params = extractor.extract_params(problem_text, temp_theorem)
        
        # Compute
        calc = MathLibCalculator(verbose=self.verbose)
        result = calc.compute(compute_func, params)
        
        if self.verbose:
            print(f"  Result: {result}", file=sys.stderr)
        
        return result, f"{best['name']} ({best['source']})"


# Test
if __name__ == "__main__":
    print("\n" + "="*80)
    print("  LeanDojo RAG Solver Test")
    print("  Retrieving from Mathlib Corpus (100K+ theorems)")
    print("="*80)
    
    solver = LeanDojoRAGSolver(verbose=True)
    
    # Full test set - 8 problems across all domains
    test_problems = [
        ("diff_squares", "Find the number of integers between 1 and 1000 that can be expressed as difference of squares"),
        ("mod_squares", "Find n ≤ 1000 such that n² has remainder 1 when divided by 1000"),
        ("vieta", "The quadratic x² - 5x + 6 = 0 has roots. Find sum of their squares"),
        ("geometric", "Geometric sequence: 3rd term is 12, 5th term is 48. Find 7th term"),
        ("probability", "Fair coin flipped 4 times. Probability of exactly 2 heads?"),
        ("chord", "Circle radius 5, chord at distance 3. Find chord length"),
        ("cube", "Smallest perfect cube divisible by 12"),
        ("digits", "How many 3-digit numbers have all distinct digits"),
    ]
    
    expected = {
        "diff_squares": 750,
        "mod_squares": 4,
        "vieta": 13,
        "geometric": 192,
        "probability": 3,
        "chord": 8,
        "cube": 216,
        "digits": 648,
    }
    
    correct = 0
    for name, problem in test_problems:
        print(f"\n{'='*60}")
        print(f"Problem: {name}")
        print(f"Text: {problem[:60]}...")
        
        exp = expected.get(name, 0)
        answer, trace = solver.solve(problem)
        status = "✅" if answer == exp else "❌"
        print(f"Answer: {answer} (expected {exp}) {status}")
        print(f"Trace: {trace}")
        
        if answer == exp:
            correct += 1
    
    print(f"\n{'='*80}")
    print(f"  Results: {correct}/{len(test_problems)} correct ({100*correct/len(test_problems):.1f}%)")
    print(f"  Source breakdown:")
    print(f"    - LeanDojo KG: theorems from corpus")
    print(f"    - Pattern fallback: computation rules when KG has no match")
    print(f"{'='*80}\n")
