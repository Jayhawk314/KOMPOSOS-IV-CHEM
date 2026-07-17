# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-LAMBDA-max-3D-chem\mof_bridge\linker_screening.py
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
MOF Linker Screening Pipeline
===============================

Orchestrates full inverse design workflow:
1. Generate candidates (LinkerGenerator)
2. Score verdicts (LinkerVerdictEngine)
3. Filter (all-AGREE or allow-HOLLOW)
4. Rank (morphism integrity or verdict count)
5. Return top N

Pattern follows: composition_engine/designer.py (CompositionDesigner)
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from mof_bridge.mp_mof_loader import MOFLinkerCache
from mof_bridge.linker_generator import LinkerGenerator
from mof_bridge.komposos_verdicts import LinkerVerdictEngine, LinkerVerdictResult


@dataclass
class LinkerScreeningSpec:
    """Specification for linker screening run."""

    application_context: (
        str  # "breath_VOC_sensing", "food_safety", "PFAS_detection", "custom"
    )
    num_candidates: int  # How many to generate
    require_all_agree: bool = False  # legacy descriptors; grounded funnel is primary
    allow_hollow: bool = False  # Include HOLLOW verdicts
    functional_groups: Optional[List[str]] = None
    exclude_elements: Optional[List[str]] = None
    ranking_mode: str = "morphism_integrity"  # "morphism_integrity" or "verdict_count"
    # Directed-generation controls (optional; default = stochastic discovery)
    strategy_weights: Optional[Dict[str, float]] = None  # substitution/modification/template mix
    seed_smiles: Optional[str] = None  # pin generation to derivatives of this molecule
    required_groups: Optional[List[str]] = None  # functional groups every candidate must carry
    # Terminal DFT verification (optional; default OFF = no behavior change).
    # When > 0, the top-N ranked candidates are sent to the typed DFT oracle
    # (oracle/dft_integration). DFT is a terminal stage on the shortlist only,
    # never in generation/ranking. Requires a backend (pyscf/psi4); if absent the
    # stage is skipped with a note rather than crashing the run.
    dft_verify_top_n: int = 0
    dft_level: Optional[str] = None  # LevelOfTheory label; None = oracle default


@dataclass
class ScreeningResult:
    """Result from a screening run."""

    candidates: List[LinkerVerdictResult]
    num_generated: int
    num_passed_all: int  # All verdicts == AGREE
    avg_morphism_integrity: float
    best_morphism_integrity: float
    generation_time_sec: float
    verdict_statistics: Dict[str, int]  # verdict_type → count
    # Terminal DFT verdicts for the top-N shortlist (empty unless dft_verify_top_n > 0).
    dft_verifications: List[Dict] = field(default_factory=list)
    dft_status: str = "not_run"  # "not_run" | "completed" | "unavailable: <reason>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "candidates": [c.to_dict() for c in self.candidates],
            "num_generated": self.num_generated,
            "num_passed_all": self.num_passed_all,
            "avg_morphism_integrity": self.avg_morphism_integrity,
            "best_morphism_integrity": self.best_morphism_integrity,
            "generation_time_sec": self.generation_time_sec,
            "verdict_statistics": self.verdict_statistics,
            "dft_verifications": self.dft_verifications,
            "dft_status": self.dft_status,
        }


class LinkerScreener:
    """Screen MOF linker candidates through full KOMPOSOS pipeline.

    Workflow:
    1. Load known 22-atom linkers from cache
    2. Generate N novel candidates
    3. Score each with 5 KOMPOSOS verdicts
    4. Filter by verdict criteria
    5. Rank by morphism integrity or verdict count
    6. Return top 50
    """

    def __init__(self):
        """Initialize screener with cache, generator, and verdict engine."""
        self.cache = MOFLinkerCache()

        # Check if cache available
        if not self.cache.is_available():
            print("WARNING: MOF linker cache not available.")
            print("Run: python scripts/download_mof_linkers.py --api-key YOUR_KEY")
            print("Using minimal demo cache...")
            # Create minimal demo cache for testing
            try:
                self.cache.download(api_key="demo", max_mofs=10)
            except Exception as e:
                print(f"Could not create demo cache: {e}")
                raise

        # Load known linkers
        try:
            known_linkers = self.cache.load_linkers()
            print(f"Loaded {len(known_linkers)} known 22-atom linkers")
        except Exception as e:
            print(f"Error loading known linkers: {e}")
            known_linkers = []

        self.generator = LinkerGenerator(known_linkers)
        self.verdict_engine = LinkerVerdictEngine()

    def screen(self, spec: LinkerScreeningSpec) -> ScreeningResult:
        """Run full screening pipeline.

        Args:
            spec: LinkerScreeningSpec with generation parameters

        Returns:
            ScreeningResult with ranked candidates

        Raises:
            ImportError: If RDKit not installed
        """
        start_time = time.perf_counter()

        print(f"\n{'=' * 70}")
        print(f"KOMPOSOS-MOF Linker Screening")
        print(f"{'=' * 70}")
        print(f"Application: {spec.application_context}")
        print(f"Candidates to generate: {spec.num_candidates}")
        print(f"Require all AGREE: {spec.require_all_agree}")
        print(f"Allow HOLLOW: {spec.allow_hollow}")
        print(f"Ranking mode: {spec.ranking_mode}")
        print(f"{'=' * 70}\n")

        # Step 1: Generate candidates
        print("Step 1: Generating candidates...")
        candidate_smiles = self.generator.generate_candidates(
            n_candidates=spec.num_candidates,
            application_context=spec.application_context,
            functional_groups=spec.functional_groups,
            exclude_elements=spec.exclude_elements,
            strategy_weights=spec.strategy_weights,
            seed_smiles=spec.seed_smiles,
            required_groups=spec.required_groups,
        )
        print(f"  Generated {len(candidate_smiles)} candidates\n")

        # Step 2: Score verdicts
        print("Step 2: Scoring verdicts...")
        scored_candidates = []
        for i, smiles in enumerate(candidate_smiles, 1):
            try:
                result = self.verdict_engine.score_verdicts(
                    smiles, spec.application_context
                )
                scored_candidates.append(result)

                if i % 10 == 0:
                    print(f"  Scored: {i}/{len(candidate_smiles)}")
            except Exception as e:
                print(f"  Error scoring {smiles[:40]}...: {e}")

        print(f"  Scored {len(scored_candidates)} candidates\n")

        # Step 3: Filter by verdict criteria
        print("Step 3: Filtering...")
        filtered_candidates = []

        for candidate in scored_candidates:
            # Check if passes filter
            if spec.require_all_agree:
                if candidate.overall_viable:  # All AGREE
                    filtered_candidates.append(candidate)
            elif spec.allow_hollow:
                # Allow AGREE or HOLLOW
                verdicts = set(candidate.verdicts.values())
                if "REJECT" not in verdicts:  # No REJECT verdicts
                    filtered_candidates.append(candidate)
            else:
                # Default: do not gate on the legacy categorical descriptors.
                # The benchmarked grounded funnel is applied by the application
                # layer and is the primary screen for novel linkers.
                filtered_candidates.append(candidate)

        print(f"  Passed filter: {len(filtered_candidates)}/{len(scored_candidates)}\n")

        # Step 4: Rank
        print("Step 4: Ranking...")

        # Composite score: morphism + verdict structure + ZFC/CAT tension + size normalization
        def _composite_score(c):
            try:
                from rdkit import Chem

                mol = Chem.MolFromSmiles(c.linker_smiles)
                n = mol.GetNumHeavyAtoms() if mol is not None else 22
            except Exception:
                n = 22

            score = c.morphism_integrity

            verdicts = list(c.verdicts.values())
            agree = sum(1 for v in verdicts if v == "AGREE")
            hollow = sum(1 for v in verdicts if v == "HOLLOW")
            orphan = sum(1 for v in verdicts if v == "ORPHAN")
            reject = sum(1 for v in verdicts if v == "REJECT")

            # Reward agreement
            score += 0.05 * agree

            # Penalize logical/structural issues
            score -= 0.10 * hollow
            score -= 0.20 * orphan
            score -= 0.40 * reject

            # Size normalization (fiber over atom count)
            score /= n**0.5

            return score

        if spec.ranking_mode == "morphism_integrity":
            # Rank by composite score (descending)
            ranked = sorted(
                filtered_candidates,
                key=lambda c: _composite_score(c),
                reverse=True,
            )
        elif spec.ranking_mode == "verdict_count":
            # Rank by number of AGREE verdicts (descending), then composite score
            ranked = sorted(
                filtered_candidates,
                key=lambda c: (
                    sum(1 for v in c.verdicts.values() if v == "AGREE"),
                    _composite_score(c),
                ),
                reverse=True,
            )
        else:
            # Default: composite score
            ranked = sorted(
                filtered_candidates,
                key=lambda c: _composite_score(c),
                reverse=True,
            )

        # Take top 50
        top_candidates = ranked[:50]
        print(f"  Top candidates: {len(top_candidates)}\n")

        # Step 5: Compute statistics
        num_passed_all = sum(1 for c in scored_candidates if c.overall_viable)

        if scored_candidates:
            avg_morphism = sum(c.morphism_integrity for c in scored_candidates) / len(
                scored_candidates
            )
            best_morphism = max(c.morphism_integrity for c in scored_candidates)
        else:
            avg_morphism = 0.0
            best_morphism = 0.0

        # Verdict statistics
        verdict_stats = {}
        for verdict_name in [
            "synthesizability",
            "toxicity",
            "stability",
            "activity",
            "conductivity",
        ]:
            verdict_stats[verdict_name] = {
                "AGREE": sum(
                    1
                    for c in scored_candidates
                    if c.verdicts.get(verdict_name) == "AGREE"
                ),
                "HOLLOW": sum(
                    1
                    for c in scored_candidates
                    if c.verdicts.get(verdict_name) == "HOLLOW"
                ),
                "ORPHAN": sum(
                    1
                    for c in scored_candidates
                    if c.verdicts.get(verdict_name) == "ORPHAN"
                ),
                "REJECT": sum(
                    1
                    for c in scored_candidates
                    if c.verdicts.get(verdict_name) == "REJECT"
                ),
            }

        # Step 6 (optional): terminal DFT verification of the top-N shortlist.
        # Off by default; never affects generation/ranking above.
        dft_verifications: List[Dict] = []
        dft_status = "not_run"
        if spec.dft_verify_top_n and top_candidates:
            print(f"Step 6: DFT-verifying top {spec.dft_verify_top_n} (terminal)...")
            try:
                from oracle.dft_integration import verify_candidates
                from core.level_of_theory import STANDARD_LEVELS, B3LYP_def2TZVP_D3
                from core.errors import OracleUnavailable

                level = STANDARD_LEVELS.get(spec.dft_level or "", B3LYP_def2TZVP_D3)
                shortlist = [c.linker_smiles for c in top_candidates[: spec.dft_verify_top_n]]
                try:
                    verdicts = verify_candidates(shortlist, level=level)
                    dft_verifications = [v.to_dict() for v in verdicts]
                    dft_status = "completed"
                    print(f"  DFT verified {len(dft_verifications)} candidates "
                          f"at {level.label}\n")
                except OracleUnavailable as oe:
                    dft_status = f"unavailable: {oe.reason}"
                    print(f"  DFT skipped (no backend): {oe.reason}")
                    print(f"  remediation: {oe.remediation}\n")
            except Exception as e:  # never let optional DFT crash a screening run
                dft_status = f"error: {e}"
                print(f"  DFT stage error (non-fatal): {e}\n")

        elapsed = time.perf_counter() - start_time

        print(f"{'=' * 70}")
        print(f"Screening Complete")
        print(f"{'=' * 70}")
        print(f"Generated: {len(candidate_smiles)}")
        print(f"Scored: {len(scored_candidates)}")
        print(f"Passed all AGREE: {num_passed_all}")
        print(f"Returned: {len(top_candidates)}")
        print(f"Best morphism: {best_morphism:.3f}")
        print(f"Avg morphism: {avg_morphism:.3f}")
        print(f"Time: {elapsed:.1f}s")
        print(f"{'=' * 70}\n")

        return ScreeningResult(
            candidates=top_candidates,
            num_generated=len(candidate_smiles),
            num_passed_all=num_passed_all,
            avg_morphism_integrity=avg_morphism,
            best_morphism_integrity=best_morphism,
            generation_time_sec=elapsed,
            verdict_statistics=verdict_stats,
            dft_verifications=dft_verifications,
            dft_status=dft_status,
        )


if __name__ == "__main__":
    # Demo usage
    print("Testing MOF Linker Screening Pipeline...\n")

    spec = LinkerScreeningSpec(
        application_context="breath_VOC_sensing",
        num_candidates=20,
        require_all_agree=True,
        ranking_mode="morphism_integrity",
    )

    try:
        screener = LinkerScreener()
        result = screener.screen(spec)

        print("\nTop 5 Candidates:")
        for i, candidate in enumerate(result.candidates[:5], 1):
            print(f"\n{i}. SMILES: {candidate.linker_smiles[:60]}...")
            print(f"   Morphism: {candidate.morphism_integrity:.3f}")
            print(f"   Verdicts: {list(candidate.verdicts.values())}")
            print(f"   Overall viable: {candidate.overall_viable}")

    except ImportError as e:
        print(f"Error: {e}")
        print("Install RDKit: pip install rdkit")
