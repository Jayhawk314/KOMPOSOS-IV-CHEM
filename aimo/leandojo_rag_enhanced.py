# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
LeanDojo RAG Layer - Enhanced with Proof Method Extraction

Dynamic RAG retrieval from LeanDojo corpus (100K+ theorems) that feeds
KOMPOSOS-IV oracle strategies with proof methods, tactics, and patterns.

Architecture:
1. Load and embed LeanDojo corpus
2. Real-time semantic search by problem
3. Extract proof methods and tactics from Lean code
4. Feed retrieved methods to oracle strategies
5. Guide Kan extensions with retrieved patterns
"""

from __future__ import annotations

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import math

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Data Classes for Retrieved Methods
# =============================================================================

@dataclass
class ProofMethod:
    """Extracted proof method from Lean theorem."""
    theorem_name: str
    theorem_statement: str
    field: str
    proof_method: str  # e.g., "factorization", "induction", "contradiction"
    tactics: List[str]  # e.g., ["ring", "simp", "linarith"]
    relevance_score: float
    lean_code: str = ""
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'theorem': self.theorem_name,
            'statement': self.theorem_statement,
            'field': self.field,
            'proof_method': self.proof_method,
            'tactics': self.tactics,
            'relevance': self.relevance_score,
            'lean_code': self.lean_code,
            'dependencies': self.dependencies,
        }


@dataclass
class RetrievedContext:
    """Full context retrieved for a problem."""
    problem_text: str
    methods: List[ProofMethod]
    computation_pattern: Optional[str]
    parameters: Dict[str, Any]
    field_hints: List[str]


# =============================================================================
# Proof Method Extractor
# =============================================================================

class ProofMethodExtractor:
    """
    Extract proof methods and tactics from Lean code.

    Analyzes Lean theorem statements and proofs to identify:
    - Proof strategy (induction, contradiction, construction, etc.)
    - Tactics used (ring, simp, linarith, etc.)
    - Key lemmas referenced
    """

    # Tactic patterns in Lean code
    TACTIC_PATTERNS = {
        'ring': r'\b(ring|Ring)\b',
        'simp': r'\b(simp|Simp|simp_all)\b',
        'linarith': r'\b(linarith|Linarith|linarith)\b',
        'field_simp': r'\b(field_simp|Field_simp)\b',
        'norm_num': r'\b(norm_num|Norm_num)\b',
        'rw': r'\b(rw|rewrite|Rewrite)\b',
        'apply': r'\b(apply|Apply)\b',
        'exact': r'\b(exact|Exact)\b',
        'refine': r'\b(refine|Refine)\b',
        'constructor': r'\b(constructor|Constructor)\b',
        'intro': r'\b(intro|Intro|intros)\b',
        'have': r'\b(have|Have)\b',
        'let': r'\b(let|Let)\b',
        'use': r'\b(use|Use)\b',
        'exists': r'\b(exists|Exists|obtain)\b',
        'induction': r'\b(induction|Induction|induct)\b',
        'cases': r'\b(cases|Cases|case_tac)\b',
        'contradiction': r'\b(contradiction|Contradiction|absurd)\b',
        'by_contra': r'\b(by_contra|By_contra)\b',
        'contrapose': r'\b(contrapose|Contrapose)\b',
        'unfold': r'\b(unfold|Unfold)\b',
        'fold': r'\b(fold|Fold)\b',
        'generalize': r'\b(generalize|Generalize)\b',
        'specialize': r'\b(specialize|Specialize)\b',
        'replace': r'\b(replace|Replace)\b',
        'suffices': r'\b(suffices|Suffices)\b',
        'convert': r'\b(convert|Convert)\b',
        'congr': r'\b(congr|Congr|congr_arg)\b',
        'ext': r'\b(ext|Ext|extensionality)\b',
        'apply_fun': r'\b(apply_fun|Apply_fun)\b',
        'calc': r'\b(calc|Calc)\b',
        'trans': r'\b(trans|Trans|transitivity)\b',
        'refl': r'\b(refl|Refl|reflexivity)\b',
        'symm': r'\b(symm|Symm|symmetry)\b',
        'exact_mod_cast': r'\b(exact_mod_cast|Exact_mod_cast)\b',
        'norm_cast': r'\b(norm_cast|Norm_cast)\b',
        'push_cast': r'\b(push_cast|Push_cast)\b',
        'rw_mod_cast': r'\b(rw_mod_cast|Rw_mod_cast)\b',
    }

    # Proof method indicators
    PROOF_METHOD_INDICATORS = {
        'induction': ['induction', 'induct', 'cases on', 'recursive', 'base case', 'inductive step'],
        'contradiction': ['contradiction', 'absurd', 'false', '¬', 'by_contra', 'assume', 'suppose not'],
        'contraposition': ['contrapose', 'contrapositive', '¬q → ¬p'],
        'direct': ['exact', 'apply', 'suffices', 'have'],
        'construction': ['use', 'exists', 'obtain', 'let', 'take'],
        'case_analysis': ['cases', 'case_tac', 'if then else', 'dichotomy'],
        'substitution': ['rw', 'rewrite', 'subst', 'substitution'],
        'simplification': ['simp', 'simplify', 'ring', 'field_simp', 'norm_num'],
        'calculation': ['calc', 'trans', 'transitivity'],
        'extensionality': ['ext', 'extensionality', 'funext', 'function.ext'],
        'universal': ['intro', 'intros', 'take', 'arbitrary'],
        'existential': ['use', 'exists', 'witness'],
        'equality_chain': ['calc', 'trans_eq', 'eq_trans'],
        'inequality_chain': ['trans_le', 'trans_lt', 'le_trans'],
        'algebraic': ['ring', 'field_simp', 'linear_combination', 'polynomial'],
        'arithmetic': ['norm_num', 'decide', 'native_decide'],
        'set_theory': ['ext', 'subset', 'inter', 'union', 'setOf'],
        'order_theory': ['le_refl', 'le_trans', 'lt_irrefl', 'well_founded'],
    }

    def extract_from_code(self, lean_code: str, theorem_name: str) -> Tuple[str, List[str]]:
        """
        Extract proof method and tactics from Lean code.

        Returns:
            (proof_method, tactics_list)
        """
        tactics = self._extract_tactics(lean_code)
        proof_method = self._infer_proof_method(lean_code, tactics, theorem_name)

        return proof_method, tactics

    def _extract_tactics(self, lean_code: str) -> List[str]:
        """Extract all tactics used in the proof."""
        tactics = []

        for tactic_name, pattern in self.TACTIC_PATTERNS.items():
            if re.search(pattern, lean_code):
                tactics.append(tactic_name)

        # Sort by frequency/importance
        tactic_priority = ['induction', 'contradiction', 'cases', 'calc', 'ext', 'ring', 'field_simp', 'simp', 'linarith']
        tactics.sort(key=lambda t: (tactic_priority.index(t) if t in tactic_priority else 99, t))

        return tactics

    def _infer_proof_method(self, lean_code: str, tactics: List[str], theorem_name: str) -> str:
        """Infer the main proof method from code and tactics."""
        code_lower = lean_code.lower()

        # Check for strong indicators first
        for method, indicators in self.PROOF_METHOD_INDICATORS.items():
            # Check tactics
            if any(tac in tactics for tac in indicators):
                return method
            # Check code
            if any(ind in code_lower for ind in indicators):
                return method

        # Check theorem name for hints
        name_lower = theorem_name.lower()
        if 'induction' in name_lower or 'recursive' in name_lower:
            return 'induction'
        if 'contradiction' in name_lower or 'not' in name_lower:
            return 'contradiction'
        if 'exists' in name_lower or 'exist' in name_lower:
            return 'construction'
        if 'unique' in name_lower:
            return 'construction'
        if 'eq' in name_lower or 'equal' in name_lower:
            return 'equality_chain'
        if 'ineq' in name_lower or 'inequal' in name_lower:
            return 'inequality_chain'
        if 'sum' in name_lower or 'prod' in name_lower:
            return 'induction'
        if 'div' in name_lower or 'mod' in name_lower:
            return 'induction'

        # Default to direct proof
        return 'direct'


# =============================================================================
# Semantic Embedding (Lightweight - No External Dependencies)
# =============================================================================

class LightweightEmbedder:
    """
    Lightweight text embedder using TF-IDF-like approach.

    No external dependencies - uses term frequency and inverse document frequency.
    """

    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.documents: List[Dict[str, float]] = []

    def build_index(self, documents: List[str]):
        """Build vocabulary and IDF from documents."""
        # Build vocabulary
        word_doc_count: Dict[str, int] = {}

        for doc in documents:
            words = set(doc.lower().split())
            for word in words:
                if word not in word_doc_count:
                    word_doc_count[word] = 0
                word_doc_count[word] += 1

        # Create vocabulary
        self.vocabulary = {word: idx for idx, word in enumerate(sorted(word_doc_count.keys()))}

        # Compute IDF
        n_docs = len(documents)
        for word, count in word_doc_count.items():
            self.idf[word] = math.log((n_docs + 1) / (count + 1)) + 1

    def encode(self, text: str) -> Dict[str, float]:
        """Encode text as sparse vector (term -> weight)."""
        weights: Dict[str, float] = {}
        words = text.lower().split()

        # Term frequency
        for word in words:
            if word not in weights:
                weights[word] = 0
            weights[word] += 1

        # Apply IDF
        total = len(words)
        for word in weights:
            tf = weights[word] / total
            idf = self.idf.get(word, 1.0)
            weights[word] = tf * idf

        return weights

    def similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Compute cosine similarity between sparse vectors."""
        # Dot product
        dot = 0.0
        for word, weight in vec1.items():
            if word in vec2:
                dot += weight * vec2[word]

        # Magnitudes
        mag1 = math.sqrt(sum(w * w for w in vec1.values()))
        mag2 = math.sqrt(sum(w * w for w in vec2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot / (mag1 * mag2)


# =============================================================================
# LeanDojo RAG Layer
# =============================================================================

class LeanDojoRAGLayer:
    """
    Real-time RAG retrieval from LeanDojo corpus.

    For each AIMO problem:
    1. Encode problem semantics
    2. Search 100K theorems by relevance
    3. Extract proof methods/tactics
    4. Feed to oracle strategies
    """

    def __init__(
        self,
        corpus_path: str = "data_sources/leandojo/leandojo_benchmark_4/corpus.jsonl",
        verbose: bool = False
    ):
        self.corpus_path = corpus_path
        self.verbose = verbose
        self.theorems: List[Dict[str, Any]] = []
        self.embedder = LightweightEmbedder()
        self.theorem_embeddings: List[Dict[str, float]] = []
        self.extractor = ProofMethodExtractor()
        self._loaded = False

        # Keyword index for fast retrieval
        self.keyword_index: Dict[str, List[int]] = {}

    def load(self, max_theorems: int = 100000):
        """Load and index LeanDojo corpus."""
        if self._loaded:
            return

        if self.verbose:
            print(f"Loading LeanDojo corpus from {self.corpus_path}...", file=sys.stderr)

        # Load theorems
        count = 0
        documents = []

        try:
            with open(self.corpus_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if count >= max_theorems:
                        break

                    try:
                        data = json.loads(line)
                        file_path = data.get('path', '')
                        premises = data.get('premises', [])

                        for p in premises:
                            if not isinstance(p, dict):
                                continue

                            name = p.get('full_name', '')
                            code = p.get('code', '')

                            # Filter for Mathlib theorems
                            if 'Mathlib' not in file_path:
                                continue

                            field = self._extract_field(file_path)
                            keywords = self._extract_keywords(name, code, field)

                            self.theorems.append({
                                'name': name,
                                'file': file_path,
                                'field': field,
                                'keywords': keywords,
                                'code': code,
                                'statement': self._extract_statement(code),
                            })

                            documents.append(f"{name} {field} {' '.join(keywords)}")
                            count += 1

                    except (json.JSONDecodeError, KeyError):
                        continue

        except FileNotFoundError:
            if self.verbose:
                print(f"Warning: Corpus not found at {self.corpus_path}", file=sys.stderr)
                print("Using demo data...", file=sys.stderr)
            self._load_demo_data()
            documents = [f"{t['name']} {t['field']}" for t in self.theorems]
            count = len(self.theorems)

        if self.verbose:
            print(f"Loaded {count} Mathlib theorems", file=sys.stderr)

        # Build embeddings
        if self.verbose:
            print("Building theorem embeddings...", file=sys.stderr)
        self.embedder.build_index(documents)
        self.theorem_embeddings = [self.embedder.encode(doc) for doc in documents]

        # Build keyword index
        self._build_keyword_index()

        self._loaded = True

    def _build_keyword_index(self):
        """Build inverted index for fast keyword search."""
        self.keyword_index = {}

        for idx, thm in enumerate(self.theorems):
            for kw in thm['keywords']:
                if kw not in self.keyword_index:
                    self.keyword_index[kw] = []
                self.keyword_index[kw].append(idx)

    def retrieve_methods(
        self,
        problem_text: str,
        top_k: int = 10,
        min_relevance: float = 0.1
    ) -> List[ProofMethod]:
        """
        Retrieve relevant proof methods from LeanDojo.

        Returns:
            List of ProofMethod objects with theorem, proof_method, tactics, relevance
        """
        if not self._loaded:
            self.load()

        # Encode problem
        problem_embedding = self.embedder.encode(problem_text)
        problem_lower = problem_text.lower()

        # Score theorems
        scored: List[Tuple[float, int]] = []

        for idx, (thm, emb) in enumerate(zip(self.theorems, self.theorem_embeddings)):
            # Semantic similarity
            sim = self.embedder.similarity(problem_embedding, emb)

            # Keyword boost
            keyword_boost = 0.0
            for kw in thm['keywords']:
                if kw in problem_lower:
                    keyword_boost += 0.2

            # Field boost
            if thm['field'] in problem_lower:
                keyword_boost += 0.3

            total_score = sim + keyword_boost

            if total_score >= min_relevance:
                scored.append((total_score, idx))

        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Extract proof methods for top results
        methods: List[ProofMethod] = []

        for score, idx in scored[:top_k]:
            thm = self.theorems[idx]

            # Extract proof method from code
            proof_method, tactics = self.extractor.extract_from_code(
                thm['code'],
                thm['name']
            )

            methods.append(ProofMethod(
                theorem_name=thm['name'],
                theorem_statement=thm['statement'],
                field=thm['field'],
                proof_method=proof_method,
                tactics=tactics,
                relevance_score=score,
                lean_code=thm['code'],
            ))

        if self.verbose and methods:
            print(f"\n📚 Retrieved {len(methods)} proof methods:", file=sys.stderr)
            for m in methods[:3]:
                print(f"  • {m.theorem_name} ({m.field})", file=sys.stderr)
                print(f"    Method: {m.proof_method}, Tactics: {m.tactics[:3]}", file=sys.stderr)

        return methods

    def retrieve_context(self, problem_text: str, top_k: int = 10) -> RetrievedContext:
        """
        Retrieve full context for a problem.

        Returns:
            RetrievedContext with methods, computation pattern, parameters, field hints
        """
        from aimo.aimo3_solver import AIMO3ComputationPatterns, ParameterExtractor

        # Retrieve proof methods
        methods = self.retrieve_methods(problem_text, top_k=top_k)

        # Match computation pattern
        compute_func, param_names = AIMO3ComputationPatterns.match(problem_text)

        # Extract parameters
        params = {}
        if compute_func:
            params = ParameterExtractor.extract(problem_text, compute_func)

        # Extract field hints
        field_hints = list(set(m.field for m in methods if m.relevance_score > 0.3))

        return RetrievedContext(
            problem_text=problem_text,
            methods=methods,
            computation_pattern=compute_func,
            parameters=params,
            field_hints=field_hints,
        )

    def _extract_field(self, file_path: str) -> str:
        """Extract mathematical field from file path."""
        path_lower = file_path.lower()

        if 'number' in path_lower or 'arith' in path_lower or 'nat' in path_lower:
            return 'number_theory'
        if 'algebra' in path_lower or 'group' in path_lower or 'ring' in path_lower:
            return 'algebra'
        if 'topology' in path_lower:
            return 'topology'
        if 'analysis' in path_lower:
            return 'analysis'
        if 'combinat' in path_lower or 'finset' in path_lower:
            return 'combinatorics'
        if 'probab' in path_lower:
            return 'probability'
        if 'geometry' in path_lower or 'metric' in path_lower:
            return 'geometry'

        return 'other'

    def _extract_keywords(self, name: str, code: str, field: str) -> List[str]:
        """Extract searchable keywords from theorem."""
        keywords = set()
        text = (name + ' ' + code).lower()

        # Add name parts
        for part in name.split('.'):
            if len(part) > 2:
                keywords.add(part.lower())

        # Add field
        keywords.add(field)

        # Mathematical keywords
        math_kw = ['sum', 'prod', 'div', 'mod', 'square', 'cube', 'root',
                   'prime', 'gcd', 'lcm', 'equation', 'polynomial',
                   'triangle', 'circle', 'angle', 'probability']

        for kw in math_kw:
            if kw in text:
                keywords.add(kw)

        return list(keywords)

    def _extract_statement(self, code: str) -> str:
        """Extract theorem statement from Lean code."""
        # Simple extraction - find text between ':=' and first tactic
        match = re.search(r':\s*(.*?)\s*:=', code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return code[:200]  # Fallback

    def _load_demo_data(self):
        """Load demo data for testing without real corpus."""
        demo_theorems = [
            {
                'name': 'Mathlib.Algebra.Group.DifferenceOfSquares',
                'file': 'Mathlib/Algebra/Group/Basic.lean',
                'field': 'algebra',
                'code': 'theorem difference_of_squares (a b : ℕ) : a^2 - b^2 = (a + b) * (a - b) := by ring',
                'statement': 'a² - b² = (a + b)(a - b)',
                'keywords': ['difference', 'squares', 'algebra', 'ring'],
            },
            {
                'name': 'Mathlib.NumberTheory.Modular.SquareRoots',
                'file': 'Mathlib/NumberTheory/Modular.lean',
                'field': 'number_theory',
                'code': 'theorem mod_square_roots (n : ℕ) : n^2 % 1000 = 1 ↔ n % 1000 ∈ {1, 249, 251, 499, 501, 749, 751, 999} := by norm_num',
                'statement': 'n² ≡ 1 (mod 1000) has 8 solutions',
                'keywords': ['modular', 'square', 'number_theory', 'norm_num'],
            },
            {
                'name': 'Mathlib.Algebra.Quadratic.Vieta',
                'file': 'Mathlib/Algebra/Quadratic.lean',
                'field': 'algebra',
                'code': 'theorem vieta_sum_squares (a b c : ℝ) : (a + b)^2 - 2*a*b = a^2 + b^2 := by ring',
                'statement': 'Sum of squares via Vieta',
                'keywords': ['quadratic', 'vieta', 'algebra', 'sum', 'squares'],
            },
            {
                'name': 'Mathlib.Probability.Binomial',
                'file': 'Mathlib/Probability/Binomial.lean',
                'field': 'probability',
                'code': 'theorem binomial_probability (n k : ℕ) (p : ℝ) : C(n,k) * p^k * (1-p)^(n-k) = ... := by simp',
                'statement': 'Binomial probability formula',
                'keywords': ['probability', 'binomial', 'coin', 'simp'],
            },
            {
                'name': 'Mathlib.Geometry.Circle.Chord',
                'file': 'Mathlib/Geometry/Circle.lean',
                'field': 'geometry',
                'code': 'theorem chord_length (r d : ℝ) : chord = 2 * sqrt(r^2 - d^2) := by field_simp',
                'statement': 'Chord length formula',
                'keywords': ['circle', 'chord', 'geometry', 'field_simp'],
            },
        ]

        self.theorems = demo_theorems


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("  LeanDojo RAG Layer - Enhanced with Proof Method Extraction")
    print("="*80)

    rag = LeanDojoRAGLayer(verbose=True)

    test_problems = [
        "Find the number of integers between 1 and 1000 that can be expressed as difference of squares",
        "Geometric sequence: 3rd term is 12, 5th term is 48. Find 7th term",
        "Fair coin flipped 4 times. Probability of exactly 2 heads?",
        "Circle radius 5, chord at distance 3. Find chord length",
    ]

    for problem in test_problems:
        print(f"\n{'='*60}")
        print(f"Problem: {problem[:60]}...")

        context = rag.retrieve_context(problem, top_k=5)

        print(f"\n📚 Retrieved {len(context.methods)} methods:")
        for m in context.methods[:3]:
            print(f"  • {m.theorem_name} ({m.field})")
            print(f"    Method: {m.proof_method}")
            print(f"    Tactics: {m.tactics[:5]}")

        print(f"\n🧮 Computation pattern: {context.computation_pattern}")
        print(f"🔢 Parameters: {context.parameters}")
        print(f"📐 Field hints: {context.field_hints}")

    print(f"\n{'='*80}\n")
