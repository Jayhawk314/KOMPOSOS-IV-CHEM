# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Compatibility Audit Report Generator
=====================================

Produces a structured, traceable audit report from a compatibility workflow
result.  Every mathematical concept is translated into domain-specific
chemistry language so a materials scientist — not a category theorist — can
read and verify the reasoning.

The report has two parallel tracks throughout:
  - Plain-English chemistry narrative  (what does this mean for the material?)
  - Mathematical backing               (which metric, formula, and values?)

Usage:
    from reports.compatibility_report import build_compatibility_report, render_markdown

    report = build_compatibility_report(
        mat_a="LiNiO2", mat_b="LiPF6", domain="battery",
        scores=workflow.scores, viable=workflow.viable,
    )
    md   = render_markdown(report)
    data = report_to_dict(report)    # JSON-serialisable
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ─── Domain narration registry ────────────────────────────────────────────────
# Translates categorical terms into chemistry-field language per domain.

_NARRATION: Dict[str, Dict[str, str]] = {
    "battery": {
        "interface":           "electrochemical interface",
        "objects":             "electrode and electrolyte materials",
        "compatible":          "electrochemically stable at this interface",
        "incompatible":        "electrochemically unstable — likely parasitic reaction or SEI breakdown",
        "profile":             "electrochemical compatibility profile",
        "shared_partners":     "materials that can form stable interfaces with both",
        "interchangeable":     "electrochemically interchangeable (same SEI chemistry and ion-transport role)",
        "transport_via":       "compatibility inherited via similar electrolyte/electrode chemistry",
        "dissimilarity_label": "Electrochemical Profile Dissimilarity",
        "overlap_label":       "Shared Interface Chemistry",
        "domain_context":      "Battery electrochemistry — stable interfaces enable long cycle life and safe operation.",
    },
    "polymer": {
        "interface":           "polymer blend interface",
        "objects":             "polymer materials",
        "compatible":          "miscible / processable as a blend",
        "incompatible":        "immiscible — likely phase separation",
        "profile":             "polymer compatibility profile",
        "shared_partners":     "polymers that form stable blends with both",
        "interchangeable":     "functionally equivalent polymer (same blend behaviour)",
        "transport_via":       "compatibility inherited via similar polymer chemistry (e.g. shared functional groups)",
        "dissimilarity_label": "Blend Profile Dissimilarity",
        "overlap_label":       "Shared Polymer Chemistry",
        "domain_context":      "Polymer blending — miscibility and processing compatibility determine performance.",
    },
    "metal": {
        "interface":           "metallurgical joint",
        "objects":             "metal alloys",
        "compatible":          "weldable / bondable without galvanic corrosion risk",
        "incompatible":        "galvanically incompatible or unweldable",
        "profile":             "metallurgical compatibility profile",
        "shared_partners":     "metals that form sound joints with both",
        "interchangeable":     "metallurgically interchangeable alloys",
        "transport_via":       "compatibility inherited via similar alloy composition",
        "dissimilarity_label": "Alloy Profile Dissimilarity",
        "overlap_label":       "Shared Alloy Chemistry",
        "domain_context":      "Metal joining — galvanic series, weldability, and thermal expansion drive compatibility.",
    },
    "ceramic": {
        "interface":           "ceramic–ceramic interface",
        "objects":             "ceramic materials",
        "compatible":          "thermally and chemically compatible at operating conditions",
        "incompatible":        "thermally or chemically incompatible — risk of delamination or reaction",
        "profile":             "ceramic compatibility profile",
        "shared_partners":     "ceramics that interface stably with both",
        "interchangeable":     "ceramically interchangeable material",
        "transport_via":       "compatibility inherited via similar oxide chemistry",
        "dissimilarity_label": "Ceramic Profile Dissimilarity",
        "overlap_label":       "Shared Ceramic Chemistry",
        "domain_context":      "Ceramic assembly — CTE matching, chemical inertness, and bonding chemistry are key.",
    },
    "semiconductor": {
        "interface":           "heterostructure interface",
        "objects":             "semiconductor materials",
        "compatible":          "band-aligned and lattice-matched for epitaxial growth",
        "incompatible":        "band-misaligned or lattice-mismatched — likely interface trap states",
        "profile":             "semiconductor compatibility profile",
        "shared_partners":     "semiconductors that form clean heterostructures with both",
        "interchangeable":     "band-structure equivalent semiconductor",
        "transport_via":       "compatibility inherited via similar band structure and lattice parameter",
        "dissimilarity_label": "Band Structure Dissimilarity",
        "overlap_label":       "Shared Band Structure Chemistry",
        "domain_context":      "Semiconductor heterostructures — band alignment and lattice match determine device quality.",
    },
    "glass": {
        "interface":           "glass–substrate interface",
        "objects":             "glass materials",
        "compatible":          "thermally compatible and wettable",
        "incompatible":        "thermally incompatible or non-wettable — risk of delamination",
        "profile":             "glass compatibility profile",
        "shared_partners":     "glasses that interface stably with both",
        "interchangeable":     "optically and thermally interchangeable glass",
        "transport_via":       "compatibility inherited via similar glass network chemistry",
        "dissimilarity_label": "Glass Profile Dissimilarity",
        "overlap_label":       "Shared Glass Network Chemistry",
        "domain_context":      "Glass assembly — thermal expansion match and surface chemistry drive bonding quality.",
    },
    "mof": {
        "interface":           "MOF–guest interaction",
        "objects":             "metal-organic framework materials",
        "compatible":          "structurally compatible host–guest system",
        "incompatible":        "incompatible host–guest — pore geometry or chemistry mismatch",
        "profile":             "MOF compatibility profile",
        "shared_partners":     "MOFs that host the same guest molecules",
        "interchangeable":     "topologically equivalent MOF (same pore geometry and linker chemistry)",
        "transport_via":       "compatibility inherited via similar pore size and linker chemistry",
        "dissimilarity_label": "MOF Profile Dissimilarity",
        "overlap_label":       "Shared Pore Chemistry",
        "domain_context":      "MOF design — pore geometry, linker chemistry, and metal node determine guest selectivity.",
    },
}

_NARRATION["default"] = {
    "interface":           "material interface",
    "objects":             "materials",
    "compatible":          "compatible",
    "incompatible":        "incompatible",
    "profile":             "material compatibility profile",
    "shared_partners":     "materials that can interface with both",
    "interchangeable":     "functionally interchangeable",
    "transport_via":       "compatibility inherited via structurally similar intermediates",
    "dissimilarity_label": "Profile Dissimilarity",
    "overlap_label":       "Shared Compatibility Profile",
    "domain_context":      "General materials compatibility.",
}


def _nar(domain: str, key: str) -> str:
    primary = domain.split("-")[0] if "-" in domain else domain
    d = _NARRATION.get(primary, _NARRATION["default"])
    return d.get(key, _NARRATION["default"].get(key, key))


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class EvidenceEntry:
    """One strategy vote, with both chemistry narrative and mathematical backing."""
    strategy_name:   str
    strategy_label:  str          # Human-readable chemistry name
    verdict:         str          # PASS / FAIL / N/A
    score:           float
    confidence:      float
    evidence_quality: str         # formal / structural / none
    chemistry_narrative: str      # plain-English interpretation
    math_backing:    str          # the formula/metric that produced this
    detail:          Dict[str, Any] = field(default_factory=dict)


@dataclass
class YonedaProofSummary:
    sieve_distance:      float
    presheaf_overlap:    float
    is_isomorphic:       bool
    shared_source_count: int
    proof_steps:         List[str]
    max_transfer_threshold: float


@dataclass
class CompatibilityAuditReport:
    report_id:    str
    generated_at: str
    mat_a:        str
    mat_b:        str
    domain:       str
    verdict:      str          # AGREE / HOLLOW / ORPHAN / REJECT
    score:        float
    confidence:   float
    viable:       bool

    executive_summary:   str
    domain_context:      str
    evidence_entries:    List[EvidenceEntry]
    zfc_summary:         Dict[str, Any]
    yoneda_proof:        Optional[YonedaProofSummary]
    methodology_note:    str
    raw_scores:          Dict[str, Any]


# ─── Narrative builders ────────────────────────────────────────────────────────

def _verdict_sentence(verdict: str, mat_a: str, mat_b: str,
                      score: float, domain: str) -> str:
    iface = _nar(domain, "interface")
    compat = _nar(domain, "compatible")
    incompat = _nar(domain, "incompatible")

    if verdict == "AGREE":
        return (
            f"Both the categorical oracle and ZFC constraint verifier agree that "
            f"**{mat_a} + {mat_b}** forms a viable {iface} "
            f"(score {score:.3f}). This pair is {compat}."
        )
    elif verdict == "HOLLOW":
        return (
            f"The categorical oracle finds a viable {iface} pathway "
            f"(score {score:.3f}), but the ZFC constraint verifier rejects it. "
            f"The interface looks structurally plausible but a hard physical or "
            f"chemical constraint prevents it. This pair is {incompat} under "
            f"current constraints."
        )
    elif verdict == "ORPHAN":
        return (
            f"The ZFC constraint verifier finds no hard veto, but the categorical "
            f"scorer falls below threshold (score {score:.3f}). Structural evidence "
            f"for this {iface} is weak. This pair is tentatively {incompat}."
        )
    else:
        return (
            f"Both engines reject **{mat_a} + {mat_b}**. "
            f"No viable {iface} pathway was found (score {score:.3f}). "
            f"This pair is {incompat}."
        )


def _strategy_label(strategy: str, domain: str) -> str:
    iface = _nar(domain, "interface")
    labels = {
        "rule_scorer":         f"Domain {iface} model",
        "typed_morphism":      "Typed interface classifier",
        "calibration":         "Statistical reliability calibration",
        "yoneda_transfer_guard": "Structural transfer guard",
        "zfc_constraint":      "ZFC logical constraint",
        "failure_memory_gate": "Historical failure pattern gate",
        "real_tool_evidence":  "Molecular dynamics measurement",
        "gray_coherence":      "Reasoning coherence check",
        "simplicial_yoneda":   f"Structural role analysis ({_nar(domain, 'overlap_label')})",
        "fibration_transport": "Inherited compatibility (transport paths)",
        "rezk_equivalence":    f"Equivalent material check ({_nar(domain, 'interchangeable')})",
    }
    return labels.get(strategy, strategy.replace("_", " ").title())


def _chemistry_narrative(vote: Dict[str, Any], domain: str,
                         mat_a: str, mat_b: str) -> str:
    strategy = vote.get("strategy", "")
    score    = vote.get("score", 0.5)
    meta     = vote.get("metadata", {})
    reason   = vote.get("reason", "")

    if strategy == "rule_scorer":
        compat = _nar(domain, "compatible") if score >= 0.5 else _nar(domain, "incompatible")
        return (
            f"The {_nar(domain, 'interface')} model scores this pair at "
            f"{score:.3f}. Verdict: {compat}. "
            f"This is the primary domain-specific score."
        )

    if strategy == "typed_morphism":
        return (
            f"The interface type classifier examined the chemical relationship "
            f"between {mat_a} and {mat_b}. "
            + (f"Finding: {reason}" if reason else "")
        )

    if strategy == "simplicial_yoneda":
        yp = meta.get("yoneda_proof") or {}
        d  = yp.get("sieve_distance", None)
        ov = yp.get("presheaf_overlap", None)
        ns = len(yp.get("shared_sources", []))
        nb = meta.get("neighbor", "")
        sim = meta.get("similarity", 0.0)
        parts = []
        if d is not None:
            parts.append(
                f"{_nar(domain, 'dissimilarity_label')}: {d:.3f} "
                f"({_nar(domain, 'overlap_label')}: {1-d:.3f}). "
            )
        if ns:
            parts.append(
                f"{ns} {_nar(domain, 'shared_partners')} were found — "
                f"materials in the {domain} network that can interface with "
                f"both {mat_a} and {mat_b}. "
            )
        else:
            parts.append(
                f"No {_nar(domain, 'shared_partners')} were found in the "
                f"{domain} network. "
            )
        if nb:
            parts.append(
                f"Closest structural analogue to {mat_a} among {mat_b}'s "
                f"known partners: {nb} (similarity {sim:.3f})."
            )
        return "".join(parts) if parts else reason

    if strategy == "fibration_transport":
        paths = meta.get("transport_paths", [])
        if paths:
            top = paths[0]
            return (
                f"{_nar(domain, 'transport_via')}. "
                f"{mat_a} is known compatible with {len(paths)} material(s) "
                f"that share {_nar(domain, 'interface')} properties with {mat_b}. "
                f"Strongest path: via {top['via']} "
                f"(transport strength {top['strength']:.3f}, "
                f"{len(top.get('shared_properties', []))} shared property features)."
            )
        return f"No transport paths found from {mat_a}'s known partners to {mat_b}."

    if strategy == "rezk_equivalence":
        witness = meta.get("isomorphism_witness") or {}
        eq = witness.get("equivalent", "")
        if eq:
            n_rel = witness.get("shared_relation_count", 0)
            return (
                f"{mat_a} and {eq} are {_nar(domain, 'interchangeable')} — "
                f"they have identical {_nar(domain, 'profile')}s "
                f"({n_rel} shared interface relationships). "
                f"Since {eq} is compatible with {mat_b}, "
                f"{mat_a} is also compatible by equivalence substitution."
            )
        eq_count = meta.get("equivalents_found", 0)
        if eq_count:
            return (
                f"{eq_count} material(s) with the same {_nar(domain, 'profile')} "
                f"as {mat_a} were found, but none are compatible with {mat_b}."
            )
        return f"No material in the {domain} network has an identical {_nar(domain, 'profile')} to {mat_a}."

    if strategy == "zfc_constraint":
        return (
            f"A hard logical constraint (ZFC layer) was triggered. "
            f"This overrides structural reasoning: {reason}."
        )

    if strategy == "failure_memory_gate":
        return (
            f"This pair matches a historical failure pattern in the {domain} domain. "
            f"The score has been adjusted accordingly: {reason}."
        )

    if strategy == "real_tool_evidence":
        return (
            f"Molecular dynamics simulation evidence was available for this pair. "
            f"MD verdict: {reason}."
        )

    if strategy == "calibration":
        return (
            f"Statistical reliability calibration adjusted the base score "
            f"to {score:.3f} based on historical accuracy in the {domain} domain."
        )

    if strategy == "gray_coherence":
        return (
            f"The reasoning coherence checker (Gray 3-cell guard) found "
            f"{'a contradiction between indirect strategy paths' if score < 0.5 else 'no coherence issues'}. "
            f"{reason}"
        )

    return reason


def _math_backing(vote: Dict[str, Any]) -> str:
    strategy = vote.get("strategy", "")
    score    = vote.get("score", 0.5)
    conf     = vote.get("confidence", 0.0)
    meta     = vote.get("metadata", {})

    if strategy == "simplicial_yoneda":
        yp = meta.get("yoneda_proof") or {}
        if yp:
            d = yp.get("sieve_distance", "n/a")
            ov = yp.get("presheaf_overlap", "n/a")
            steps = yp.get("proof_steps", [])
            proof_str = " → ".join(steps) if steps else "n/a"
            return (
                f"Metric: Yoneda sieve distance d(y(A),y(B)) = |Δ|/|∪| = {d}. "
                f"Presheaf overlap = {ov}. "
                f"Score = 0.5 + 0.5 × Jaccard(fingerprint_A, best_neighbour). "
                f"Proof trace: {proof_str}"
            )
        return f"Score = 0.5 + 0.5 × Jaccard(YonedaFingerprint). Confidence = {conf:.3f}."

    if strategy == "fibration_transport":
        paths = meta.get("transport_paths", [])
        total = meta.get("total_strength", 0.0)
        return (
            f"Transport strength = Σ Jaccard(PropertyFP(b_known), PropertyFP(B)) "
            f"for each known-compatible b_known. "
            f"Total = {total:.4f} across {len(paths)} path(s). "
            f"Score = 0.5 + 0.5 × min(1.0, total_strength)."
        )

    if strategy == "rezk_equivalence":
        witness = meta.get("isomorphism_witness") or {}
        if witness:
            n = witness.get("shared_relation_count", 0)
            return (
                f"Rezk equivalence: A≅A' iff Hom(−,A)=Hom(−,A') (identical Yoneda fingerprints). "
                f"Proved by {n} shared morphism relations. "
                f"Then: A'→B exists ⟹ A→B by substitution. Score = 0.95."
            )
        return "Yoneda fingerprint exact-match search. No equivalence found."

    if strategy == "zfc_constraint":
        return "ZFC logical constraint veto: score bounded to min(base, veto_score)."

    if strategy == "typed_morphism":
        tm = meta or {}
        return (
            f"TypedMorphismInference: relation={tm.get('relation','?')}, "
            f"score={score:.3f}, confidence={conf:.3f}."
        )

    if strategy == "failure_memory_gate":
        return (
            f"Failure pattern match: count={meta.get('historical_count',0)}, "
            f"pattern={meta.get('pattern','?')}. "
            f"Score bounded to {'≤0.42 (FP gate)' if score <= 0.42 else '≥0.58 (FN gate)'}."
        )

    if strategy == "calibration":
        return (
            f"Platt/isotonic calibration on score bin. "
            f"Calibrator: {meta.get('calibrator','?')}. "
            f"Calibrated probability: {score:.4f}."
        )

    return f"Score={score:.4f}, Confidence={conf:.4f}."


def _methodology_note(domain: str) -> str:
    iface   = _nar(domain, "interface")
    profile = _nar(domain, "profile")
    inter   = _nar(domain, "interchangeable")
    return f"""
## Methodology

This report uses **KOMPOSOS-IV categorical reasoning** applied to {domain} materials.

### What the math means in chemistry terms

| Mathematical concept | Chemistry meaning ({domain}) |
|---|---|
| Category object | A material in the {domain} network |
| Morphism (arrow) | A {iface} relationship between two materials |
| Representable presheaf Hom(−,A) | The full {profile} of material A — every material that can form a {iface} with it, weighted by confidence |
| Yoneda distance d(y(A),y(B)) | How different A and B are in terms of what they can interface with. d=0 means identical role; d=1 means completely different role |
| Yoneda Lemma | Two materials are structurally identical iff their {profile}s are isomorphic. This is a theorem, not a heuristic |
| Rezk equivalence A≅A' | A and A' are {inter} — they have exactly the same set of {iface} partners |
| Fibration transport | If A is compatible with B, and B' is chemically similar to B, then A is likely compatible with B'. Compatibility "lifts" along structural similarity |
| ZFC constraint | A hard logical rule derived from known chemistry (e.g. electrochemical stability window). Cannot be overridden by structural similarity |

### Evidence quality levels
- **Formal proof** — the vote is backed by a computed mathematical proof (presheaf comparison, sieve distance). Fully reproducible.
- **Structural** — comparison is made but no formal category was available. Heuristic-level.
- **No category** — the domain's material network was not available; vote is a neutral prior only.

### Reproducibility
All scores are deterministic given the material database version. The domain category
is built from the same pairwise validation rules used in the benchmark audit (41/41, 100%).
""".strip()


# ─── Report builder ───────────────────────────────────────────────────────────

def build_compatibility_report(
    mat_a: str,
    mat_b: str,
    domain: str,
    scores: Dict[str, Any],
    viable: bool,
) -> CompatibilityAuditReport:
    """Build a full audit report from a compatibility workflow result."""

    total      = float(scores.get("total", 0.5))
    ensemble   = scores.get("ensemble", {}) or {}
    votes      = ensemble.get("votes", [])
    zfc        = scores.get("zfc", {}) or {}
    calibration = scores.get("calibration", {}) or {}

    # Calibrated score if available
    cal_prob = calibration.get("calibrated_probability")
    confidence_overall = float(ensemble.get("confidence", 0.5))

    # Determine dual-engine verdict
    zfc_available = bool(zfc.get("available"))
    zfc_viable    = bool(zfc.get("interface_viable")) if zfc_available else False
    if viable and zfc_viable:
        verdict = "AGREE"
    elif viable and zfc_available and not zfc_viable:
        verdict = "HOLLOW"
    elif not viable and zfc_viable:
        verdict = "ORPHAN"
    else:
        verdict = "REJECT"

    # Extract Yoneda proof summary from the simplicial_yoneda vote
    yoneda_proof_summary = None
    for v in votes:
        if v.get("strategy") == "simplicial_yoneda":
            yp = v.get("metadata", {}).get("yoneda_proof") or {}
            if yp:
                yoneda_proof_summary = YonedaProofSummary(
                    sieve_distance=yp.get("sieve_distance", 1.0),
                    presheaf_overlap=yp.get("presheaf_overlap", 0.0),
                    is_isomorphic=yp.get("is_isomorphic", False),
                    shared_source_count=len(yp.get("shared_sources", [])),
                    proof_steps=yp.get("proof_steps", []),
                    max_transfer_threshold=yp.get("max_transfer_threshold", 0.0),
                )
            break

    # Build evidence entries
    evidence_entries = []
    for v in votes:
        strategy = v.get("strategy", "")
        eq       = v.get("metadata", {}).get("evidence_quality", "")
        entry = EvidenceEntry(
            strategy_name    = strategy,
            strategy_label   = _strategy_label(strategy, domain),
            verdict          = "PASS" if v.get("compatible") else "FAIL",
            score            = float(v.get("score", 0.5)),
            confidence       = float(v.get("confidence", 0.0)),
            evidence_quality = eq,
            chemistry_narrative = _chemistry_narrative(v, domain, mat_a, mat_b),
            math_backing     = _math_backing(v),
            detail           = dict(v.get("metadata", {})),
        )
        evidence_entries.append(entry)

    exec_summary = _verdict_sentence(verdict, mat_a, mat_b, total, domain)
    if cal_prob is not None:
        exec_summary += (
            f"\n\nStatistical calibration adjusts the raw score to a "
            f"reliability-corrected probability of **{cal_prob:.3f}** "
            f"(calibrator: {calibration.get('calibrator','unknown')})."
        )

    return CompatibilityAuditReport(
        report_id    = f"COMPAT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-"
                       + uuid.uuid4().hex[:6].upper(),
        generated_at = datetime.now(timezone.utc).isoformat(),
        mat_a        = mat_a,
        mat_b        = mat_b,
        domain       = domain,
        verdict      = verdict,
        score        = round(total, 4),
        confidence   = round(confidence_overall, 4),
        viable       = viable,
        executive_summary  = exec_summary,
        domain_context     = _nar(domain, "domain_context"),
        evidence_entries   = evidence_entries,
        zfc_summary        = dict(zfc),
        yoneda_proof       = yoneda_proof_summary,
        methodology_note   = _methodology_note(domain),
        raw_scores         = dict(scores),
    )


# ─── Renderers ────────────────────────────────────────────────────────────────

def render_markdown(report: CompatibilityAuditReport) -> str:
    """Render the report as human-readable Markdown."""
    domain  = report.domain
    iface   = _nar(domain, "interface")
    profile = _nar(domain, "profile")

    lines: List[str] = []

    lines += [
        f"# KOMPOSOS-IV Compatibility Audit Report",
        f"",
        f"**Report ID:** `{report.report_id}`  ",
        f"**Generated:** {report.generated_at}  ",
        f"**Pair:** {report.mat_a} + {report.mat_b}  ",
        f"**Domain:** {report.domain.title()}  ",
        f"**Verdict:** {report.verdict}  ",
        f"**Score:** {report.score:.4f}  ",
        f"**Confidence:** {report.confidence:.4f}  ",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
        report.executive_summary,
        f"",
        f"> **Domain context:** {report.domain_context}",
        f"",
        f"---",
        f"",
        f"## Evidence Chain",
        f"",
        f"Each vote is shown with the chemistry interpretation first, then the "
        f"mathematical formula that produced it.",
        f"",
    ]

    for entry in report.evidence_entries:
        eq_badge = {
            "formal":    "✓ Formal proof",
            "structural": "~ Structural",
            "none":      "✗ No category",
        }.get(entry.evidence_quality, "")

        lines += [
            f"### {entry.strategy_label}",
            f"",
            f"| Field | Value |",
            f"|---|---|",
            f"| Verdict | **{entry.verdict}** |",
            f"| Score | {entry.score:.4f} |",
            f"| Confidence | {entry.confidence:.4f} |",
            f"| Evidence quality | {eq_badge} |",
            f"",
            f"**Chemistry interpretation:**  ",
            entry.chemistry_narrative,
            f"",
            f"**Mathematical backing:**  ",
            f"*{entry.math_backing}*",
            f"",
        ]

        # Yoneda proof steps inline for simplicial_yoneda
        if entry.strategy_name == "simplicial_yoneda":
            yp = entry.detail.get("yoneda_proof") or {}
            steps = yp.get("proof_steps", [])
            if steps:
                lines += [f"**Formal proof trace:**", f""]
                for i, step in enumerate(steps, 1):
                    lines.append(f"{step}  ")
                lines.append("")
            shared = yp.get("shared_sources", [])
            if shared:
                lines += [
                    f"**Shared {_nar(domain, 'shared_partners')} "
                    f"({len(shared)} materials):**",
                    f"",
                    f"| Material | Conf→{report.mat_a} | Conf→{report.mat_b} |",
                    f"|---|---|---|",
                ]
                for s in shared:
                    lines.append(
                        f"| {s['source']} | {s['conf_to_a']:.4f} | {s['conf_to_b']:.4f} |"
                    )
                lines.append("")

        # Fibration transport paths
        if entry.strategy_name == "fibration_transport":
            paths = entry.detail.get("transport_paths", [])
            if paths:
                lines += [
                    f"**Transport paths ({len(paths)}):**",
                    f"",
                    f"| Via material | Strength | Shared properties |",
                    f"|---|---|---|",
                ]
                for p in paths:
                    sp = ", ".join(p.get("shared_properties", [])[:5])
                    lines.append(
                        f"| {p['via']} | {p['strength']:.4f} | {sp} |"
                    )
                lines.append("")

        # Rezk isomorphism witness
        if entry.strategy_name == "rezk_equivalence":
            witness = entry.detail.get("isomorphism_witness") or {}
            if witness:
                eq_mat = witness.get("equivalent", "")
                n_rel  = witness.get("shared_relation_count", 0)
                logic  = witness.get("logic", "")
                lines += [
                    f"**Isomorphism witness:**",
                    f"",
                    f"- Equivalent material: **{eq_mat}**",
                    f"- Shared interface relations proving equivalence: {n_rel}",
                    f"- Logic chain: {logic}",
                    f"",
                ]

    # ZFC section
    lines += [
        f"---",
        f"",
        f"## ZFC Constraint Verification",
        f"",
    ]
    if report.zfc_summary.get("available"):
        n_c   = report.zfc_summary.get("num_constraints", 0)
        vetos = report.zfc_summary.get("veto_constraints", [])
        lines += [
            f"**{n_c} constraint(s) evaluated.**",
            f"",
        ]
        if vetos:
            lines += [
                f"**Hard vetoes triggered ({len(vetos)}):**",
                "",
            ]
            for v in vetos:
                lines.append(f"- `{v}`")
            lines.append("")
        else:
            lines.append(f"No hard vetoes detected. All {n_c} constraint(s) passed.")
            lines.append("")
    else:
        lines += [
            "ZFC constraint verification was not available for this domain/environment.",
            "",
        ]

    # Methodology
    lines += [
        "---",
        "",
        report.methodology_note,
        "",
        "---",
        "",
        f"*This report was generated by KOMPOSOS-IV-CHEM. "
        f"All scores are deterministic given the material database. "
        f"Report ID: `{report.report_id}`*",
    ]

    return "\n".join(lines)


def report_to_dict(report: CompatibilityAuditReport) -> Dict[str, Any]:
    """Return a JSON-serialisable dict (for download / programmatic use)."""
    d = asdict(report)
    # YonedaProofSummary may be None — asdict handles that
    return d
