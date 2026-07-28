# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS-III Master Scientific & Computational Audit
=====================================================

A comprehensive validation script testing:
1. Research-Grade Accuracy (full loaded literature benchmark)
2. Physical Grounding (ColabFit probabilistic constraints)
3. Computational Integrity (Category Theory + ZFC)
4. Feature Integration (Composition Engine + MOF Designer)
"""

import sys
import json
import time
from pathlib import Path
import unittest
from typing import Dict, List, Any

# Add root to path
sys.path.append(str(Path(__file__).parent.parent))

from audit.literature_ground_truth import LiteratureGroundTruth
from audit.run_audit import run_scientific_audit, run_computational_audit
from data.colabfit_loader import ColabFitClient
from oracle.material_zfc_constraints import BondConstraint
from composition_engine.predictor import CompositionPredictor
from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec

class MasterAudit:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()

    def run_all(self):
        print("=" * 80)
        print("KOMPOSOS-III MASTER AUDIT: SCIENTIFIC VALIDITY RECONFIRMATION")
        print("=" * 80)
        
        self.test_research_grade_accuracy()
        self.test_physical_grounding()
        self.test_computational_integrity()
        self.test_feature_integration()
        
        self.report_summary()

    def test_research_grade_accuracy(self):
        print("\n[MODULE 1] Research-Grade Accuracy")
        print("-" * 50)
        try:
            result = run_scientific_audit()
            status = "PASS" if result.get("pass") else "FAIL"
            evaluated = int(result.get("pairs_evaluated", 0))
            accuracy = 100.0 * float(result.get("accuracy", 0.0))
            f1 = float(result.get("f1", 0.0))
            fp = int(result.get("fp", 0))
            fn = int(result.get("fn", 0))
            self.results['accuracy'] = (
                f"{status} ({evaluated} pairs, accuracy={accuracy:.1f}%, "
                f"F1={f1:.3f}, FP={fp}, FN={fn})"
            )
        except Exception as e:
            self.results['accuracy'] = f"FAIL: {e}"

    def test_physical_grounding(self):
        print("\n[MODULE 2] Physical Grounding (ColabFit Integration)")
        print("-" * 50)
        try:
            # Clear cache to pick up new mocks
            cache_path = Path("data/cache/colabfit_cache.db")
            if cache_path.exists():
                cache_path.unlink()
                print("[OK] ColabFit cache cleared.")

            client = ColabFitClient()
            # Test Si-O (which has a real dataset ID in our loader)
            dist = client.get_bond_distribution("Si", "O")
            
            # Typical Si-O bond is ~1.62 A. Let's test plausibility.
            constraint = BondConstraint("Si", "O", client)
            p_1_62 = constraint.probability_valid(1.62)
            p_2_50 = constraint.probability_valid(2.50)
            
            print(f"Si-O Plausibility at 1.62 A (Typical): {p_1_62:.3f}")
            print(f"Si-O Plausibility at 2.50 A (Long): {p_2_50:.3f}")
            
            if p_1_62 > 0.9 and p_2_50 < 0.2:
                print("[OK] Probabilistic constraints match physical intuition.")
                self.results['physical_grounding'] = "PASS (Dynamic potentials active)"
            else:
                print("[WARN] Unexpected probability values. Check ColabFit distribution.")
                self.results['physical_grounding'] = "WARN (Probability logic mismatch)"
        except Exception as e:
            self.results['physical_grounding'] = f"FAIL: {e}"

    def test_computational_integrity(self):
        print("\n[MODULE 3] Computational Integrity (CAT + ZFC)")
        print("-" * 50)
        try:
            run_computational_audit()
            self.results['computational'] = "PASS (Axioms & Dual-Engine Verified)"
        except Exception as e:
            self.results['computational'] = f"FAIL: {e}"

    def test_feature_integration(self):
        print("\n[MODULE 4] Feature Integration Spot Checks")
        print("-" * 50)
        try:
            # 1. Composition Engine Spot Check
            predictor = CompositionPredictor()
            result = predictor.predict("LiNi0.8Mn0.1Co0.1O2")
            voltage = result.properties["voltage"].value
            confidence = result.properties["voltage"].confidence
            print(f"Predict NMC811 Voltage: {voltage:.2f} V (Confidence: {confidence:.2f})")
            
            # 2. MOF Linker Spot Check (Kulik 22-atom)
            spec = LinkerScreeningSpec(
                application_context="CO2_capture",
                num_candidates=20,
                require_all_agree=True
            )
            screener = LinkerScreener()
            # Enforce exact atom count
            screener.generator.min_atoms = 22
            screener.generator.max_atoms = 22
            
            mof_result = screener.screen(spec)
            print(f"MOF Linker Generator: {mof_result.num_passed_all} candidates passed all 5 verdicts")
            
            if voltage > 3.5 and mof_result.num_generated >= 20:
                self.results['integration'] = "PASS (Cross-feature logic consistent)"
            else:
                self.results['integration'] = "FAIL (Prediction or Generation error)"
        except Exception as e:
            self.results['integration'] = f"FAIL: {e}"

    def report_summary(self):
        duration = time.time() - self.start_time
        print("\n" + "=" * 80)
        print(f"MASTER AUDIT SUMMARY (Duration: {duration:.2f}s)")
        print("=" * 80)
        for module, status in self.results.items():
            print(f"{module.upper():20s} : {status}")
        print("=" * 80)
        
        # Save to file
        out_path = Path(__file__).parent / f"master_audit_{time.strftime('%Y%m%d')}.json"
        with open(out_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"Master report saved to: {out_path}")

if __name__ == "__main__":
    audit = MasterAudit()
    audit.run_all()
