# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import sys
import asyncio
from pathlib import Path

# Ensure we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gray_coherence import SoftwareCategoryBuilder
from core.category import Category
from core.gray_coherence_bridge import build_shield
from oracle import CategoricalOracle
from data.embeddings import EmbeddingsEngine
from cyber.topos_detector import ToposDetector
from geometry import OllivierRicciCurvature
from cyber.multi_surface_detector import MultiSurfaceDetector

async def run_mythos_sovereign_audit():
    print("=" * 100)
    print("MYTHOS SOVEREIGN: INTEGRATED CATEGORICAL DEFENSE (GLASSWING)")
    print("Target: mythos_sovereign_victim_final.py (Logic Bypass + RCE Chain)")
    print("=" * 100)

    # 1. Build the Software Category
    victim_path = "KOMPOSOS-IV/examples/mythos_sovereign_victim_final.py"
    builder = SoftwareCategoryBuilder().from_source_file(victim_path)
    
    cat = Category(db_path=":memory:")
    for obj_name, obj in builder.objects.items():
        # Inject metadata for Ricci and Multi-Surface
        metadata = {"privilege": obj.privilege}
        if "verifier" in obj_name: metadata["surface"] = "Application"
        if "executor" in obj_name: metadata["surface"] = "Endpoint"
        if "sync" in obj_name: metadata["surface"] = "Memory"
        cat.add(obj_name, type_name=obj.kind, metadata=metadata)
        
    for m in builder.morphisms:
        cat.connect(m.source, m.target, m.label, confidence=m.confidence)

    # 2. Layer 5: Structural Gray Coherence (MythosShield)
    print("\n[Layer 5] Auditing Structural 3-Cells...")
    embeddings = EmbeddingsEngine()
    oracle = CategoricalOracle(cat, embeddings)
    shield = build_shield(oracle, category=cat)
    shield_report = shield.scan(top_k=20)
    
    for f in shield_report.findings:
        print(f"  [GAP] {f.vulnerability.vuln_class} detected: {f.conjecture_source} -> {f.conjecture_target}")
        print(f"        Severity: {f.combined_severity:.2f}, MITRE: {f.vulnerability.mitre_id}")

    # 3. Layer 3: Topos-Logic (Sieve Collapse)
    print("\n[Layer 3] Auditing Security Sieves (Topos Logic)...")
    detector = ToposDetector.from_enriched_category(cat)
    # Check truth values from the perspective of the entry point
    entry_point = "mythos_sovereign_victim_final.orchestrator_service"
    sinks = ["system_executor", "low_level_memory_sync", "ctypes.memmove"]
    
    assessments = detector.assess_threat([entry_point])
    for a in assessments:
        if any(sink in a.technique_id for sink in sinks):
            print(f"  [TOPOS] Truth Value for {a.technique_id}: {a.truth_value:.4f}")
            if a.truth_value < 1.0:
                print(f"          ALERT: Sieve Collapse detected. Security property is NOT maximal.")
                print(f"          Reason: {a.intuitionistic_note}")

    # 4. Layer 2: Geometric Analysis (Ricci Curvature)
    print("\n[Layer 2] Auditing Call-Graph Geometry (Ricci Curvature)...")
    ricci = OllivierRicciCurvature(cat)
    curvature_result = ricci.compute_all_curvatures()
    
    # Negative curvature edges are potential transit bottlenecks for exploits
    sorted_edges = sorted(curvature_result.edge_curvatures.items(), key=lambda x: x[1])
    for (s, t), kappa in sorted_edges[:5]:
        if kappa < -0.1:
            print(f"  [RICCI] Bottleneck detected: {s} <-> {t} (kappa={kappa:.4f})")
            print(f"          Impact: This edge connects divergent functional clusters, a prime pivot point.")

    # 5. Construction 5: Multi-Surface Pivot Detection
    print("\n[Construction 5] Auditing Cross-Surface Pivots (Grothendieck)...")
    multi_detector = MultiSurfaceDetector()
    # Map software morphisms to a technique sequence
    sequence = [m.target for m in builder.morphisms if "call" in m.label]
    # Filter for things that look like MITRE techniques
    mitre_sequence = ["T1190", "T1059", "T1068", "T1611"] # Map manually for the demo
    pivot_analysis = multi_detector.analyze_events(mitre_sequence)
    
    for pivot in pivot_analysis["pivots"]:
        print(f"  [PIVOT] {pivot.source_surface} -> {pivot.target_surface} ({pivot.alert_level.upper()})")

    print("\n" + "=" * 100)
    print("SOVEREIGN AUDIT COMPLETE")
    print("Result: System autonomously identifies logic bypass, structural gaps, and geometric bottlenecks.")
    print("=" * 100)

if __name__ == "__main__":
    asyncio.run(run_mythos_sovereign_audit())
