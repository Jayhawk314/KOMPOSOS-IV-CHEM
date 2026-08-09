# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Crystal Dreamer search-strategy ablation.

This is a development/spent self-consistency benchmark. Target windows and
candidate values come from the same forward predictor. It compares candidate
search behavior; it does not measure voltage/capacity accuracy, experimental
performance, or blind generalization.

The hidden-composition neighbour is an oracle diagnostic because it uses the
held-out target formula. It is not a deployable inverse-design baseline.
Direct Materials Project voltage/capacity filtering is recorded as unavailable
because the local MP summary cache has no such labels.
"""

from __future__ import annotations

import hashlib
import json
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from audit.run_crystal_recovery import (
    EXACT_EPS,
    K,
    NEAR_EPS,
    PROP_TOL,
    TARGETS,
    _HeldOutDB,
    _comp_distance,
    _norm_comp,
    _props,
)
from composition_engine.designer import (
    CompositionDesigner,
    DesignCandidate,
    DesignSpec,
    PropertyTarget,
)
from composition_engine.known_compositions import get_db
from composition_engine.predictor import CompositionPredictor

REPORT_PATH = ROOT / "audit" / "crystal_search_ablation_report.json"
MAX_CANDIDATES = 300
RANDOM_SEED = 20260809

VARIANTS = (
    "direct_labelled_filter",
    "oracle_composition_neighbour",
    "random_union",
    "perturbation",
    "interpolation",
    "substitution",
    "stoichiometry",
    "four_strategy_union",
)


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _revision() -> Optional[str]:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
    except Exception:
        return None


def _normalised_entry_comp(entry) -> Dict[str, float]:
    total = sum(entry.composition.values()) or 1.0
    return {element: amount / total for element, amount in entry.composition.items()}


def _in_window(candidate: DesignCandidate, targets: List[PropertyTarget]) -> bool:
    for target in targets:
        value = candidate.predicted_properties.get(target.name)
        if value is None or not target.is_met(value):
            return False
    return True


def _topk_diversity(candidates: List[DesignCandidate]) -> Optional[float]:
    comps = []
    for candidate in candidates[:K]:
        try:
            comps.append(_norm_comp(candidate.formula))
        except Exception:
            continue
    distances = [
        _comp_distance(comps[left], comps[right])
        for left in range(len(comps))
        for right in range(left + 1, len(comps))
    ]
    return mean(distances) if distances else None


class VariantDesigner(CompositionDesigner):
    """CompositionDesigner with one frozen candidate-pool policy."""

    def __init__(
        self,
        variant: str,
        target_comp: Dict[str, float],
        seed: int,
        predictor: CompositionPredictor,
        db,
    ):
        super().__init__(predictor=predictor, db=db)
        if variant not in VARIANTS:
            raise ValueError(f"Unknown variant: {variant}")
        self.variant = variant
        self.target_comp = target_comp
        self.seed = seed
        self.raw_pool_size = 0
        self.unique_pool_size = 0
        self.labelled_pool_size = 0

    def _generate_candidates(
        self,
        spec: DesignSpec,
    ) -> List[Tuple[str, str, Optional[str]]]:
        entries = self.db.entries
        if spec.domain:
            entries = [entry for entry in entries if entry.domain == spec.domain]
        anchors = self._sample_anchors(entries)

        if self.variant == "direct_labelled_filter":
            labelled = [
                entry
                for entry in entries
                if all(entry.properties.get(target.name) is not None for target in spec.targets)
            ]
            self.labelled_pool_size = len(labelled)
            labelled.sort(
                key=lambda entry: sum(
                    target.weight * target.distance(entry.properties[target.name])
                    for target in spec.targets
                )
            )
            raw = [
                (entry.formula, "direct_labelled_filter", entry.name)
                for entry in labelled
            ]
        elif self.variant == "oracle_composition_neighbour":
            ordered = sorted(
                entries,
                key=lambda entry: _comp_distance(
                    _normalised_entry_comp(entry),
                    self.target_comp,
                ),
            )
            raw = [
                (entry.formula, "oracle_composition_neighbour", entry.name)
                for entry in ordered
            ]
        elif self.variant == "perturbation":
            raw = self._strategy_perturbation(anchors)
        elif self.variant == "interpolation":
            raw = self._strategy_interpolation(anchors)
        elif self.variant == "substitution":
            raw = self._strategy_substitution(anchors)
        elif self.variant == "stoichiometry":
            raw = self._strategy_stoichiometry(entries)
        else:
            raw = super()._generate_candidates(spec)

        self.raw_pool_size = len(raw)
        unique = self._deduplicate(raw)
        if self.variant == "random_union":
            random.Random(self.seed).shuffle(unique)
            unique = [
                (formula, "random_union", anchor)
                for formula, _strategy, anchor in unique
            ]
        self.unique_pool_size = len(unique)
        return unique


def _evaluate_variant(
    variant: str,
    target_name: str,
    target_comp: Dict[str, float],
    targets: List[PropertyTarget],
    predictor: CompositionPredictor,
    heldout,
    seed: int,
) -> Dict:
    designer = VariantDesigner(
        variant=variant,
        target_comp=target_comp,
        seed=seed,
        predictor=predictor,
        db=heldout,
    )
    result = designer.design(
        DesignSpec(
            targets=targets,
            domain="battery",
            max_candidates=MAX_CANDIDATES,
        )
    )
    topk = result.candidates[:K]
    distances = []
    for candidate in topk:
        try:
            distances.append(_comp_distance(_norm_comp(candidate.formula), target_comp))
        except Exception:
            continue
    minimum_distance = min(distances) if distances else None
    gate_total = (
        result.num_physical_assessed
        + result.num_physical_unassessed
        + result.num_physical_gated
    )
    return {
        "target": target_name,
        "variant": variant,
        "status": "assessed",
        "candidate_budget": MAX_CANDIDATES,
        "raw_pool_size": designer.raw_pool_size,
        "unique_pool_size": designer.unique_pool_size,
        "labelled_pool_size": designer.labelled_pool_size,
        "evaluated": result.num_evaluated,
        "returned": len(result.candidates),
        "top_one_property_window_match": bool(topk and _in_window(topk[0], targets)),
        "any_top_k_property_window_match": any(
            _in_window(candidate, targets) for candidate in topk
        ),
        "minimum_composition_distance_at_k": minimum_distance,
        "composition_exact_at_k": (
            minimum_distance is not None and minimum_distance <= EXACT_EPS
        ),
        "composition_near_at_k": (
            minimum_distance is not None and minimum_distance <= NEAR_EPS
        ),
        "top_k_diversity": _topk_diversity(topk),
        "elapsed_seconds": result.elapsed_seconds,
        "gate": {
            "assessed": result.num_physical_assessed,
            "vetoed": result.num_physical_gated,
            "unassessable": result.num_physical_unassessed,
            "assessment_coverage": (
                result.num_physical_assessed / gate_total if gate_total else None
            ),
        },
        "top_k": [
            {
                "rank": rank,
                "formula": candidate.formula,
                "overall_score": candidate.overall_score,
                "physical_gate_status": candidate.physical_gate_status,
                "strategy": candidate.strategy,
            }
            for rank, candidate in enumerate(topk, start=1)
        ],
    }


def _summarise(rows: List[Dict]) -> Dict[str, Dict]:
    summary = {}
    for variant in VARIANTS:
        selected = [
            row for row in rows
            if row.get("status") == "assessed" and row.get("variant") == variant
        ]
        if not selected:
            continue
        gate = {
            key: sum(row["gate"][key] for row in selected)
            for key in ("assessed", "vetoed", "unassessable")
        }
        gate_total = sum(gate.values())
        distances = [
            row["minimum_composition_distance_at_k"]
            for row in selected
            if row["minimum_composition_distance_at_k"] is not None
        ]
        diversities = [
            row["top_k_diversity"]
            for row in selected
            if row["top_k_diversity"] is not None
        ]
        summary[variant] = {
            "assessed_targets": len(selected),
            "top_one_property_hits": sum(
                row["top_one_property_window_match"] for row in selected
            ),
            "any_top_k_property_hits": sum(
                row["any_top_k_property_window_match"] for row in selected
            ),
            "exact_hits_at_k": sum(row["composition_exact_at_k"] for row in selected),
            "near_hits_at_k": sum(row["composition_near_at_k"] for row in selected),
            "mean_minimum_composition_distance_at_k": (
                mean(distances) if distances else None
            ),
            "mean_top_k_diversity": mean(diversities) if diversities else None,
            "mean_evaluated": mean(row["evaluated"] for row in selected),
            "mean_returned": mean(row["returned"] for row in selected),
            "total_elapsed_seconds": sum(row["elapsed_seconds"] for row in selected),
            "gate_totals": gate,
            "gate_assessment_coverage": (
                gate["assessed"] / gate_total if gate_total else None
            ),
        }
    return summary


def main() -> None:
    db = get_db()
    predictor = CompositionPredictor()
    by_name = {entry.name: entry for entry in db.entries}
    battery_entries = [entry for entry in db.entries if entry.domain == "battery"]
    labelled_battery = [
        entry
        for entry in battery_entries
        if entry.properties.get("voltage") is not None
        and entry.properties.get("theoretical_capacity") is not None
    ]
    labelled_mp = [entry for entry in labelled_battery if entry.name.startswith("mp-")]

    rows = []
    for target_index, target_name in enumerate(TARGETS):
        entry = by_name.get(target_name)
        if entry is None:
            rows.append({
                "target": target_name,
                "status": "skipped",
                "reason": "not_an_anchor",
            })
            continue
        target_comp = _normalised_entry_comp(entry)
        target_props = _props(predictor.predict(target_name))
        voltage = target_props.get("voltage")
        capacity = target_props.get("theoretical_capacity")
        if voltage is None or capacity is None:
            rows.append({
                "target": target_name,
                "status": "skipped",
                "reason": "missing_voltage_or_capacity",
            })
            continue

        targets = [
            PropertyTarget(
                "voltage",
                voltage * (1 - PROP_TOL),
                voltage * (1 + PROP_TOL),
            ),
            PropertyTarget(
                "theoretical_capacity",
                capacity * (1 - PROP_TOL),
                capacity * (1 + PROP_TOL),
            ),
        ]
        heldout = _HeldOutDB(db, target_name, target_comp)
        for variant_index, variant in enumerate(VARIANTS):
            row = _evaluate_variant(
                variant=variant,
                target_name=target_name,
                target_comp=target_comp,
                targets=targets,
                predictor=predictor,
                heldout=heldout,
                seed=RANDOM_SEED + target_index * 100 + variant_index,
            )
            rows.append(row)
            print(
                f"{target_name:9s} {variant:30s} "
                f"top1={int(row['top_one_property_window_match'])} "
                f"anyK={int(row['any_top_k_property_window_match'])} "
                f"near={int(row['composition_near_at_k'])} "
                f"n={row['returned']}"
            )

    from composition_engine.mp_loader import MPCache

    cache = MPCache()
    report = {
        "schema": "crystal_dreamer_search_ablation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "development_spent",
        "claim_scope": (
            "Candidate-search comparison using target windows and candidate "
            "properties from the same forward predictor; not predictive accuracy, "
            "blind evidence, or experimental validation."
        ),
        "command": "python -u audit/run_crystal_search_ablation.py",
        "python": platform.python_version(),
        "base_revision_before_ablation_change": _revision(),
        "parameters": {
            "targets": TARGETS,
            "variants": VARIANTS,
            "candidate_budget": MAX_CANDIDATES,
            "top_k": K,
            "property_tolerance": PROP_TOL,
            "exact_epsilon": EXACT_EPS,
            "near_epsilon": NEAR_EPS,
            "random_seed": RANDOM_SEED,
        },
        "data_coverage": {
            "battery_entries": len(battery_entries),
            "voltage_and_capacity_labelled_entries": len(labelled_battery),
            "materials_project_voltage_and_capacity_labelled_entries": len(labelled_mp),
        },
        "unavailable_baselines": [
            {
                "name": "direct_materials_project_voltage_capacity_filter",
                "status": "NOT_ASSESSED",
                "reason": (
                    "The local Materials Project summary cache contains zero rows "
                    "with both voltage and theoretical-capacity labels."
                ),
            }
        ],
        "oracle_warning": (
            "oracle_composition_neighbour uses the hidden held-out target "
            "composition and is a diagnostic ceiling, not a deployable method."
        ),
        "inputs": {
            "known_database_entries": db.size,
            "materials_project_summary_sha256": _sha256(cache.summary_path),
            "materials_project_metadata_sha256": _sha256(cache.meta_path),
            "audit_script_sha256": _sha256(Path(__file__)),
            "recovery_receipt_sha256": _sha256(
                ROOT / "audit" / "crystal_recovery_report.json"
            ),
        },
        "rows": rows,
        "summary": _summarise(rows),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print()
    print("Summary")
    print("variant                         top1 anyK exact near gate_cov")
    for variant, item in report["summary"].items():
        print(
            f"{variant:31s} "
            f"{item['top_one_property_hits']:>4d} "
            f"{item['any_top_k_property_hits']:>4d} "
            f"{item['exact_hits_at_k']:>5d} "
            f"{item['near_hits_at_k']:>4d} "
            f"{item['gate_assessment_coverage']:.1%}"
        )
    print(f"Receipt: {REPORT_PATH}")
    print(f"Receipt SHA-256: {_sha256(REPORT_PATH)}")


if __name__ == "__main__":
    main()
