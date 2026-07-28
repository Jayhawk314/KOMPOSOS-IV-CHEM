# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Simplicial Type Theory (STT) Strategies for KOMPOSOS-IV-CHEM.

Implements structural metrics and transport laws to remove heuristics:
1. SimplicialYonedaStrategy  - Formal Yoneda presheaf distance + neighbor comparison.
2. FibrationTransportStrategy - Lifts compatibility along base morphisms.
3. RezkEquivalenceStrategy   - Isomorphic-presheaf label propagation.

Each strategy returns rich metadata for the audit/evidence UI:
  - evidence_quality: "formal" | "structural" | "none"
  - yoneda_proof:     formal sieve-distance proof steps + shared-source table
  - isomorphism_witness / transport_paths: specific morphism chains

Adapted from KOMPOSOS-IV-PHARM's stt_repurposing.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from core.category import Category, Object, Morphism
from oracle.prediction import Prediction, PredictionType
from oracle.strategies import InferenceStrategy


# ─── Domain-category cache ────────────────────────────────────────────────────
# Built once per domain per process lifetime so audit runs don't repeat O(n²)
# pairwise validation calls.

_DOMAIN_CATEGORY_CACHE: Dict[str, Any] = {}


def build_domain_category(domain: str):
    """Return a cached chemistry category for *domain* (builds on first call).

    Handles composite domains like "battery-polymer" by using the primary part.
    Returns None if the domain bridge has no ``build_{domain}_category`` function.
    """
    primary = domain.split("-")[0] if "-" in domain else domain
    if primary in _DOMAIN_CATEGORY_CACHE:
        return _DOMAIN_CATEGORY_CACHE[primary]
    cat = _try_build_domain_category(primary)
    _DOMAIN_CATEGORY_CACHE[primary] = cat
    return cat


def _try_build_domain_category(primary_domain: str):
    import importlib

    for mod_path in (
        f"{primary_domain}_bridge.integration",
        f"{primary_domain}_bridge",
    ):
        try:
            mod = importlib.import_module(mod_path)
            builder_name = f"build_{primary_domain}_category"
            if hasattr(mod, builder_name):
                return getattr(mod, builder_name)()
        except (ImportError, AttributeError, ModuleNotFoundError):
            continue
    return None


# ─── Category adapter helpers (III-style and IV-style) ───────────────────────
# III-style (categorical.category.Category): .objects is a dict, .morphisms is
#   a dict; Morphism.source/.target are Object instances; confidence lives in
#   Morphism.data['score'].
# IV-style (core.category.Category): .objects() / .morphisms() are callable
#   methods; Morphism.source/.target are plain strings; .confidence is a float.

def _iter_morphisms_to(obj_name: str, category) -> List[Tuple[str, float]]:
    """Return [(source_name, confidence)] for every non-identity X→obj_name morphism."""
    result: List[Tuple[str, float]] = []

    obj_attr = getattr(category, "morphisms", None)
    if isinstance(obj_attr, dict):
        # III-style
        for m in obj_attr.values():
            if m.data.get("is_identity"):
                continue
            t_name = m.target.name if hasattr(m.target, "name") else str(m.target)
            if t_name == obj_name:
                conf = float(m.data.get("score", m.data.get("confidence", 1.0)))
                s_name = m.source.name if hasattr(m.source, "name") else str(m.source)
                result.append((s_name, conf))
    elif callable(getattr(category, "morphisms_to", None)):
        # IV-style
        for m in category.morphisms_to(obj_name):
            result.append((str(m.source), float(m.confidence)))

    return result


def _iter_all_morphisms(category) -> List[Tuple[str, str, float, str]]:
    """Return [(src, tgt, confidence, morph_name)] for all non-identity morphisms."""
    result: List[Tuple[str, str, float, str]] = []

    obj_attr = getattr(category, "morphisms", None)
    if isinstance(obj_attr, dict):
        # III-style
        for m in obj_attr.values():
            if m.data.get("is_identity"):
                continue
            s = m.source.name if hasattr(m.source, "name") else str(m.source)
            t = m.target.name if hasattr(m.target, "name") else str(m.target)
            conf = float(m.data.get("score", m.data.get("confidence", 1.0)))
            result.append((s, t, conf, m.name))
    elif callable(getattr(category, "morphisms", None)):
        # IV-style
        for m in category.morphisms():
            result.append((str(m.source), str(m.target), float(m.confidence), m.name))

    return result


# ─── Formal Yoneda evidence ────────────────────────────────────────────────────

def _build_formal_yoneda_evidence(obj_a: str, obj_b: str, category) -> Dict[str, Any]:
    """Compute the formal Yoneda presheaf evidence for *obj_a* vs *obj_b*.

    Builds representable presheaves y(A)=Hom(−,A) and y(B)=Hom(−,B), then
    computes the weighted sieve distance d(y(A),y(B)) = |y(A)Δy(B)| / |y(A)∪y(B)|.

    By the Yoneda Lemma two objects are structurally isomorphic iff d=0.
    The presheaf_overlap = 1−d is the formally-grounded similarity score.
    Returns a dict with proof steps and a shared-source evidence table for the UI.
    """
    proof_steps: List[str] = []

    # Step 1: Build representable presheaves (identity morphism = confidence 1.0)
    proof_steps.append(
        f"Step 1: Build y({obj_a})=Hom(−,{obj_a}) and y({obj_b})=Hom(−,{obj_b})"
    )
    presheaf_a: Dict[str, float] = {obj_a: 1.0}
    presheaf_b: Dict[str, float] = {obj_b: 1.0}

    for src, conf in _iter_morphisms_to(obj_a, category):
        presheaf_a[src] = max(presheaf_a.get(src, 0.0), conf)
    for src, conf in _iter_morphisms_to(obj_b, category):
        presheaf_b[src] = max(presheaf_b.get(src, 0.0), conf)

    sources_a = set(presheaf_a)
    sources_b = set(presheaf_b)
    shared   = sources_a & sources_b
    only_a   = sources_a - sources_b
    only_b   = sources_b - sources_a

    proof_steps.append(
        f"Step 2: |Hom(−,{obj_a})|={len(sources_a)}, "
        f"|Hom(−,{obj_b})|={len(sources_b)}"
    )
    proof_steps.append(
        f"  Shared sources: {len(shared)} | "
        f"Exclusive to {obj_a}: {len(only_a)} | "
        f"Exclusive to {obj_b}: {len(only_b)}"
    )

    # Step 2: Compute weighted sieve distance
    all_keys = sources_a | sources_b
    if not all_keys:
        return {
            "presheaf_a": {}, "presheaf_b": {},
            "shared_sources": [], "exclusive_to_a": [], "exclusive_to_b": [],
            "sieve_distance": 1.0, "presheaf_overlap": 0.0,
            "is_isomorphic": False, "proof_steps": proof_steps,
            "max_transfer_threshold": 0.0,
        }

    sym_diff  = sum(abs(presheaf_a.get(k, 0.0) - presheaf_b.get(k, 0.0)) for k in all_keys)
    union_w   = sum(max(presheaf_a.get(k, 0.0), presheaf_b.get(k, 0.0)) for k in all_keys)
    inter_w   = sum(min(presheaf_a.get(k, 0.0), presheaf_b.get(k, 0.0)) for k in all_keys)

    sieve_distance   = sym_diff / union_w if union_w > 0 else 1.0
    presheaf_overlap = inter_w / union_w  if union_w > 0 else 0.0

    proof_steps.append(
        f"Step 3: d(y(A),y(B)) = |Δ|/|∪| = "
        f"{sym_diff:.3f}/{union_w:.3f} = {sieve_distance:.4f}"
    )
    proof_steps.append(
        f"  Presheaf overlap (1−d) = {presheaf_overlap:.4f}"
    )

    # Step 3: Isomorphism check (bidirectional high-confidence morphisms)
    all_morphs = _iter_all_morphisms(category)
    ab_confs = [c for s, t, c, _ in all_morphs if s == obj_a and t == obj_b]
    ba_confs = [c for s, t, c, _ in all_morphs if s == obj_b and t == obj_a]
    is_isomorphic = bool(ab_confs and ba_confs and max(ab_confs) * max(ba_confs) >= 0.95)

    if sieve_distance == 0.0:
        proof_steps.append(
            f"Step 4: d=0 → {obj_a} ≅ {obj_b}  (Yoneda fully faithful)"
        )
    elif is_isomorphic:
        proof_steps.append(
            f"Step 4: Bidirectional morphisms confirm {obj_a} ≅ {obj_b}"
        )
    else:
        proof_steps.append(
            f"Step 4: d={sieve_distance:.4f} > 0, not isomorphic; "
            f"max transfer threshold = {1.0 - sieve_distance:.4f}"
        )

    # Build shared-source evidence table (for UI)
    shared_details = [
        {
            "source":     src,
            "conf_to_a":  round(presheaf_a.get(src, 0.0), 4),
            "conf_to_b":  round(presheaf_b.get(src, 0.0), 4),
        }
        for src in sorted(shared)
    ]

    return {
        "presheaf_a":            {k: round(v, 4) for k, v in presheaf_a.items()},
        "presheaf_b":            {k: round(v, 4) for k, v in presheaf_b.items()},
        "shared_sources":        shared_details,
        "exclusive_to_a":        sorted(only_a),
        "exclusive_to_b":        sorted(only_b),
        "sieve_distance":        round(sieve_distance, 4),
        "presheaf_overlap":      round(presheaf_overlap, 4),
        "is_isomorphic":         is_isomorphic,
        "proof_steps":           proof_steps,
        "max_transfer_threshold": round(1.0 - sieve_distance, 4),
    }


# ─── Public scoring functions ─────────────────────────────────────────────────

def score_simplicial_yoneda(
    material_a: str,
    material_b: str,
    domain: str,
    category=None,
) -> Dict[str, Any]:
    """Score compatibility via Yoneda similarity to known-compatible neighbours.

    Score formula is unchanged from the original Jaccard implementation so that
    the audit benchmark is not disturbed.  The ``metadata`` dict is enriched with
    a full ``yoneda_proof`` block for UI evidence display.
    """
    if category is None:
        category = build_domain_category(domain)

    if category is None:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.3,
            "reason": f"simplicial yoneda: no category for {domain}",
            "metadata": {"evidence_quality": "none"},
        }

    # Formal Yoneda evidence (A vs B directly — for audit chain)
    try:
        yoneda_proof = _build_formal_yoneda_evidence(material_a, material_b, category)
    except Exception:
        yoneda_proof = None

    # Neighbour-based score (original logic — score unchanged)
    known_compatibles = _find_compatible_with(material_b, category)
    if not known_compatibles:
        overlap = yoneda_proof["presheaf_overlap"] if yoneda_proof else 0.0
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.4,
            "reason": f"simplicial yoneda: no known compatibles for {material_b}",
            "metadata": {
                "evidence_quality": "formal" if yoneda_proof else "none",
                "yoneda_proof": yoneda_proof,
            },
        }

    best_sim = 0.0
    best_neighbor = ""
    fp_a = _compute_yoneda_fingerprint(material_a, category)

    for neighbor in known_compatibles:
        if neighbor == material_a:
            continue
        fp_n = _compute_yoneda_fingerprint(neighbor, category)
        sim = _jaccard_similarity(fp_a, fp_n)
        if sim > best_sim:
            best_sim = sim
            best_neighbor = neighbor

    if best_sim > 0.0:
        return {
            "score": 0.5 + (0.5 * best_sim),
            "compatible": True,
            "confidence": 0.4 + (0.5 * best_sim),
            "reason": (
                f"simplicial yoneda: neighbour_sim={best_sim:.3f} to {best_neighbor}"
                + (
                    f", d(y(A),y(B))={yoneda_proof['sieve_distance']:.3f}"
                    if yoneda_proof else ""
                )
            ),
            "metadata": {
                "evidence_quality": "formal" if yoneda_proof else "structural",
                "yoneda_proof":     yoneda_proof,
                "neighbor":         best_neighbor,
                "similarity":       round(best_sim, 4),
                "fingerprint_a":    list(fp_a),
                "fingerprint_n":    list(_compute_yoneda_fingerprint(best_neighbor, category)),
            },
        }

    return {
        "score": 0.5,
        "compatible": True,
        "confidence": 0.4,
        "reason": "simplicial yoneda: no similar neighbours found",
        "metadata": {
            "evidence_quality": "formal" if yoneda_proof else "structural",
            "yoneda_proof": yoneda_proof,
        },
    }


def score_fibration_transport(
    material_a: str,
    material_b: str,
    domain: str,
    category=None,
) -> Dict[str, Any]:
    """Score compatibility via fibration transport.

    Score formula is unchanged; ``metadata`` is enriched with per-contributor
    morphism details and shared property features.
    """
    if category is None:
        category = build_domain_category(domain)

    if category is None:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.3,
            "reason": "fibration transport: no category",
            "metadata": {"evidence_quality": "none"},
        }

    targets_for_a = _find_compatible_with(material_a, category)
    if not targets_for_a:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.4,
            "reason": "fibration transport: source has no known compatibles",
            "metadata": {"evidence_quality": "structural", "transport_paths": []},
        }

    total_strength = 0.0
    transport_paths: List[Dict[str, Any]] = []
    fp_b = _get_property_fingerprint_from_cat(material_b, category)

    for b_known in targets_for_a:
        if b_known == material_b:
            continue
        fp_known = _get_property_fingerprint_from_cat(b_known, category)
        strength = _jaccard_similarity(fp_b, fp_known)
        if strength > 0.2:
            shared_props = sorted(fp_b & fp_known)
            total_strength += strength
            transport_paths.append({
                "via":            b_known,
                "strength":       round(strength, 4),
                "shared_properties": shared_props,
                "reasoning": (
                    f"{material_a}→{b_known} (known), "
                    f"{b_known}≈{material_b} via {len(shared_props)} shared props "
                    f"(strength {strength:.3f})"
                ),
            })

    if transport_paths:
        confidence = min(0.9, 0.4 + total_strength)
        transport_paths.sort(key=lambda x: x["strength"], reverse=True)
        return {
            "score": 0.5 + (0.5 * min(1.0, total_strength)),
            "compatible": True,
            "confidence": confidence,
            "reason": (
                f"fibration transport via {len(transport_paths)} path(s), "
                f"total strength {total_strength:.3f}"
            ),
            "metadata": {
                "evidence_quality": "formal",
                "contributors":     [p["via"] for p in transport_paths],
                "total_strength":   round(total_strength, 4),
                "transport_paths":  transport_paths,
            },
        }

    return {
        "score": 0.5,
        "compatible": True,
        "confidence": 0.4,
        "reason": "fibration transport: no transport paths found",
        "metadata": {"evidence_quality": "structural", "transport_paths": []},
    }


def score_rezk_equivalence(
    material_a: str,
    material_b: str,
    domain: str,
    category=None,
) -> Dict[str, Any]:
    """Score via Rezk-style equivalence completion.

    If A≅A' (identical Yoneda presheaves) and (A',B) is compatible, then (A,B)
    is compatible with mathematical certainty.  Score formula is unchanged;
    ``metadata`` is enriched with the full isomorphism witness.
    """
    if category is None:
        category = build_domain_category(domain)

    if category is None:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.3,
            "reason": "rezk equivalence: no category",
            "metadata": {"evidence_quality": "none"},
        }

    equivalents = _find_rezk_equivalents(material_a, category)
    if not equivalents:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.4,
            "reason": "rezk equivalence: no equivalents found",
            "metadata": {"evidence_quality": "structural", "equivalents_found": 0},
        }

    best_conf  = 0.0
    matching_eq = ""

    for eq in equivalents:
        if eq == material_a:
            continue
        neighbors = _find_compatible_with(eq, category)
        if material_b in neighbors:
            best_conf   = 0.95
            matching_eq = eq
            break

    if best_conf > 0:
        # Build isomorphism witness: shared fingerprint + transport morphisms
        fp_a  = _compute_yoneda_fingerprint(material_a, category)
        fp_eq = _compute_yoneda_fingerprint(matching_eq, category)
        shared_fp = fp_a & fp_eq

        transport_morphs = [
            {"morphism": name, "direction": "forward" if s == matching_eq else "reverse",
             "confidence": round(conf, 4)}
            for s, t, conf, name in _iter_all_morphisms(category)
            if (s == matching_eq and t == material_b) or (s == material_b and t == matching_eq)
        ]

        isomorphism_witness = {
            "equivalent":          matching_eq,
            "shared_relations":    [list(r) for r in sorted(shared_fp)],
            "shared_relation_count": len(shared_fp),
            "transport_morphisms": transport_morphs,
            "logic": (
                f"Hom(−,{material_a}) = Hom(−,{matching_eq}) "
                f"({len(shared_fp)} shared relations → identical presheaves → A≅A'); "
                f"{matching_eq}→{material_b} exists "
                f"({len(transport_morphs)} morphism(s)) → {material_a}→{material_b} holds."
            ),
        }

        return {
            "score": 0.95,
            "compatible": True,
            "confidence": best_conf,
            "reason": (
                f"rezk: {material_a}≅{matching_eq} "
                f"({len(shared_fp)} shared relations), "
                f"{matching_eq}→{material_b} exists"
            ),
            "metadata": {
                "evidence_quality":    "formal",
                "equivalent":          matching_eq,
                "isomorphism_witness": isomorphism_witness,
            },
        }

    return {
        "score": 0.5,
        "compatible": True,
        "confidence": 0.4,
        "reason": "rezk equivalence: no compatible equivalents found",
        "metadata": {
            "evidence_quality": "structural",
            "equivalents_found": len(equivalents),
        },
    }


# ─── Private helpers (unchanged logic) ────────────────────────────────────────

def _find_rezk_equivalents(obj_name: str, category) -> List[str]:
    """Find materials with the exact same Yoneda fingerprint (≡ Rezk-equivalent)."""
    fp_target = _compute_yoneda_fingerprint(obj_name, category)
    if not fp_target:
        return []

    objects: List[str] = []
    if hasattr(category, "objects") and isinstance(getattr(category, "objects", None), dict):
        objects = list(category.objects.keys())
    elif hasattr(category, "_objects") and isinstance(getattr(category, "_objects", None), dict):
        objects = list(category._objects.keys())

    return [
        other for other in objects
        if other != obj_name and _compute_yoneda_fingerprint(other, category) == fp_target
    ]


def _compute_yoneda_fingerprint(obj_name: str, category) -> Set[Tuple[str, str]]:
    """Compute the Yoneda presheaf fingerprint as a set of (neighbour, relation) pairs."""
    fp: Set[Tuple[str, str]] = set()

    obj_attr = getattr(category, "morphisms", None)
    if isinstance(obj_attr, dict):
        # III-style
        for m in obj_attr.values():
            s = m.source.name if hasattr(m.source, "name") else str(m.source)
            t = m.target.name if hasattr(m.target, "name") else str(m.target)
            if s == obj_name:
                fp.add((t, m.name))
            if t == obj_name:
                fp.add((s, m.name))
    elif callable(getattr(category, "morphisms_from", None)):
        # IV-style
        for m in category.morphisms_from(obj_name):
            fp.add((m.target, m.name))
        for m in category.morphisms_to(obj_name):
            fp.add((m.source, m.name))

    return fp


def _find_compatible_with(obj_name: str, category) -> List[str]:
    """Return all objects connected to obj_name via any morphism."""
    neighbours: List[str] = []

    obj_attr = getattr(category, "morphisms", None)
    if isinstance(obj_attr, dict):
        for m in obj_attr.values():
            s = m.source.name if hasattr(m.source, "name") else str(m.source)
            t = m.target.name if hasattr(m.target, "name") else str(m.target)
            if s == obj_name:
                neighbours.append(t)
            elif t == obj_name:
                neighbours.append(s)
    elif callable(getattr(category, "morphisms_from", None)):
        for m in category.morphisms_from(obj_name):
            neighbours.append(m.target)
        for m in category.morphisms_to(obj_name):
            neighbours.append(m.source)

    return neighbours


def _jaccard_similarity(s1: Set, s2: Set) -> float:
    if not s1 and not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def _get_property_fingerprint_from_cat(obj_name: str, category) -> Set[str]:
    fp: Set[str] = set()
    obj = None

    obj_attr = getattr(category, "objects", None)
    if isinstance(obj_attr, dict):
        obj = obj_attr.get(obj_name)
    elif callable(getattr(category, "get_object", None)):
        obj = category.get_object(obj_name)

    if obj:
        if hasattr(obj, "type_info"):
            for k, v in obj.type_info.items():
                fp.add(f"{k}:{v}")
        if hasattr(obj, "type_name"):
            fp.add(f"type:{obj.type_name}")
        if hasattr(obj, "metadata"):
            for k, v in obj.metadata.items():
                fp.add(f"{k}:{v}")

    return fp


# ─── Strategy classes (InferenceStrategy subclasses) ──────────────────────────

class SimplicialYonedaStrategy(InferenceStrategy):
    """Predict compatibility via Yoneda presheaf fingerprint similarity."""

    name = "simplicial_yoneda"

    def predict(self, source: str, target: str) -> List[Prediction]:
        predictions = []

        neighbors = self._find_compatible_neighbors(target)
        if not neighbors:
            return predictions

        best_similarity = 0.0
        best_neighbor   = ""

        for neighbor in neighbors:
            if neighbor == source:
                continue
            sim = self.yoneda_similarity(source, neighbor)
            if sim > best_similarity:
                best_similarity = sim
                best_neighbor   = neighbor

        if best_similarity > 0.4:
            predictions.append(Prediction(
                source=source,
                target=target,
                predicted_relation="compatible",
                prediction_type=PredictionType.YONEDA_DISTANCE,
                strategy_name=self.name,
                confidence=best_similarity,
                reasoning=(
                    f"Yoneda similarity {best_similarity:.4f} to "
                    f"known-compatible neighbour {best_neighbor}"
                ),
                evidence={
                    "neighbor":   best_neighbor,
                    "similarity": best_similarity,
                    "metric":     "Jaccard(YonedaFingerprint)",
                },
            ))

        return predictions

    def yoneda_fingerprint(self, obj_name: str) -> Set[Tuple[str, str]]:
        outgoing, incoming = self._build_morphism_index()
        fp: Set[Tuple[str, str]] = set()
        for m in incoming.get(obj_name, []):
            src = getattr(m, "source", getattr(m, "source_name", None))
            fp.add((src, m.name))
        for m in outgoing.get(obj_name, []):
            tgt = getattr(m, "target", getattr(m, "target_name", None))
            fp.add((tgt, m.name))
        return fp

    def yoneda_similarity(self, obj1: str, obj2: str) -> float:
        fp1, fp2 = self.yoneda_fingerprint(obj1), self.yoneda_fingerprint(obj2)
        if not fp1 and not fp2:
            return 0.0
        return len(fp1 & fp2) / len(fp1 | fp2)

    def _find_compatible_neighbors(self, target: str) -> List[str]:
        _, incoming = self._build_morphism_index()
        neighbours = []
        for m in incoming.get(target, []):
            if m.name in {"compatible", "viable", "stable", "indication"}:
                src = getattr(m, "source", getattr(m, "source_name", None))
                neighbours.append(src)
            elif m.confidence > 0.7:
                src = getattr(m, "source", getattr(m, "source_name", None))
                neighbours.append(src)
        return neighbours


class FibrationTransportStrategy(InferenceStrategy):
    """Predict compatibility by transporting along base category morphisms."""

    name = "fibration_transport"

    def predict(self, source: str, target: str) -> List[Prediction]:
        predictions = []

        outgoing, _ = self._build_morphism_index()
        source_compatible_with = []
        for m in outgoing.get(source, []):
            if m.name in {"compatible", "viable", "stable"} or m.confidence > 0.7:
                tgt = getattr(m, "target", getattr(m, "target_name", None))
                source_compatible_with.append(tgt)

        if not source_compatible_with:
            return predictions

        total_strength = 0.0
        contributors   = []

        for b_known in source_compatible_with:
            if b_known == target:
                continue
            strength = self.base_morphism_strength(b_known, target)
            if strength > 0.3:
                total_strength += strength
                contributors.append(b_known)

        if total_strength > 0:
            predictions.append(Prediction(
                source=source,
                target=target,
                predicted_relation="compatible",
                prediction_type=PredictionType.FIBRATION_LIFT,
                strategy_name=self.name,
                confidence=min(0.95, total_strength),
                reasoning=(
                    f"Fibration transport from {len(contributors)} "
                    "neighbours via base morphisms"
                ),
                evidence={"contributors": contributors, "total_strength": total_strength},
            ))

        return predictions

    def base_morphism_strength(self, obj1: str, obj2: str) -> float:
        fp1 = self._get_property_fingerprint(obj1)
        fp2 = self._get_property_fingerprint(obj2)
        if not fp1 or not fp2:
            return 0.0
        return len(fp1 & fp2) / len(fp1 | fp2)

    def _get_property_fingerprint(self, obj_name: str) -> Set[str]:
        obj_map = self._get_object_map()
        obj = obj_map.get(obj_name)
        if not obj:
            return set()
        fp: Set[str] = {f"type:{obj.type_name}"}
        for k, v in obj.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                fp.add(f"meta:{k}={v}")
            elif isinstance(v, list):
                for item in v:
                    fp.add(f"meta:{k}:{item}")
        return fp


class RezkEquivalenceStrategy(InferenceStrategy):
    """Propagate compatibility through Rezk-equivalent (isomorphic presheaf) materials."""

    name = "rezk_equivalence"

    def predict(self, source: str, target: str) -> List[Prediction]:
        predictions = []

        res = score_rezk_equivalence(source, target, "unknown")
        if res["confidence"] > 0.8:
            predictions.append(Prediction(
                source=source,
                target=target,
                predicted_relation="compatible",
                prediction_type=PredictionType.EQUIVALENCE_PROPAGATION,
                strategy_name=self.name,
                confidence=res["confidence"],
                reasoning=res["reason"],
                evidence=res["metadata"],
            ))

        return predictions
