# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Math Context Builder - Builds LLM context from Theorem KG.

Given a classified problem, queries the TheoremKG using KOMPOSOS math
(spectral clustering, composition paths, Yoneda similarity) to retrieve
the right theorems, then formats them as context for the LLM.

The LLM doesn't guess which theorems matter -- the KG tells it.
"""

import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

sys.path.insert(0, '.')

from aimo.theorem_kg import TheoremKG, get_global_kg, KGQueryResult
from aimo.problem_classifier import ProblemFeatures, MathDomain


@dataclass
class MathContext:
    """Context built from KG for LLM injection."""
    # Formatted text ready for LLM prompt
    context_text: str = ""
    # Computation hint from calculator (or None)
    computation_hint: Optional[int] = None
    # Raw KG query result
    kg_result: Optional[KGQueryResult] = None
    # Retrieved theorem names
    theorem_names: List[str] = field(default_factory=list)
    # Domain of the problem
    domain: str = "general"


class MathContextBuilder:
    """
    Builds LLM context by querying the TheoremKG.

    Pipeline:
    1. Get or create global TheoremKG
    2. Query KG with problem text + domain
    3. Format results as context text
    4. Optionally compute a hint via calculator
    """

    def __init__(self, kg: Optional[TheoremKG] = None, verbose: bool = False):
        self.kg = kg
        self.verbose = verbose

    def _get_kg(self) -> TheoremKG:
        """Get the KG, initializing if needed."""
        if self.kg is None:
            self.kg = get_global_kg()
        if not self.kg._loaded:
            # Load full LeanDojo corpus (180K theorems)
            from domains.mathematics.leandojo_adapter import LeanDojoAdapter
            import os
            corpus_dir = "data_sources/leandojo/leandojo_benchmark_4"
            if os.path.isdir(corpus_dir):
                adapter = LeanDojoAdapter(data_path=corpus_dir)
                if self.verbose:
                    print(f"Loading full corpus from {corpus_dir}...")
                self.kg.ingest_corpus(adapter)
            else:
                if self.verbose:
                    print("Corpus not found, using demo data")
                self.kg.ingest_corpus()
        return self.kg

    def build_context(self, problem_text: str,
                      features: Optional[ProblemFeatures] = None) -> MathContext:
        """
        Build math context for a problem.

        Args:
            problem_text: The problem statement
            features: Classified problem features (domain, difficulty, etc.)

        Returns:
            MathContext with context_text ready for LLM injection
        """
        kg = self._get_kg()

        # Determine domain
        domain = None
        if features and features.domain:
            domain = features.domain.name.lower()

        # Query the KG
        kg_result = kg.query(problem_text, domain=domain, top_k=10)

        # Get theorem names
        theorem_names = [name for name, _ in kg_result.ranked_theorems]

        # Format for LLM
        context_text = kg_result.format_for_llm(kg)

        # Try computation hint
        computation_hint = self._try_computation_hint(problem_text, features)

        if computation_hint is not None and context_text:
            context_text += f"\n\n## Computation Hint\nA direct calculation suggests the answer may be {computation_hint}. Verify this with your reasoning."
        elif computation_hint is not None:
            context_text = f"## Computation Hint\nA direct calculation suggests the answer may be {computation_hint}. Verify this with your reasoning."

        if self.verbose and context_text:
            n_theorems = len(theorem_names)
            n_chains = len(kg_result.theorem_chains)
            print(f"  [MathContext] {n_theorems} theorems, "
                  f"{n_chains} chains, domain={domain}", file=sys.stderr)

        return MathContext(
            context_text=context_text,
            computation_hint=computation_hint,
            kg_result=kg_result,
            theorem_names=theorem_names,
            domain=domain or "general",
        )

    def _try_computation_hint(self, problem_text: str,
                              features: Optional[ProblemFeatures]) -> Optional[int]:
        """Try to get a computation hint from the calculator."""
        if features is None or features.direct_compute_func is None:
            return None

        try:
            from aimo.aimo3_solver import ParameterExtractor
            from aimo.mathlib_calculator import MathLibCalculator

            params = ParameterExtractor.extract(problem_text, features.direct_compute_func)
            calculator = MathLibCalculator(verbose=False)
            result = calculator.compute(features.direct_compute_func, params)
            return result
        except Exception:
            return None
