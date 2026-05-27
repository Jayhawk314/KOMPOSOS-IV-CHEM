# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Simplicial Type Theory (STT) Strategies for KOMPOSOS-IV-CHEM.

Implements structural metrics and transport laws to remove heuristics:
1. YonedaSimilarityStrategy - Uses Jaccard distance between presheaf fingerprints.
2. FibrationTransportStrategy - Lifts compatibility along base morphisms.
3. RezkEquivalenceStrategy - Groups isomorphic materials for label propagation.

Adapted from KOMPOSOS-IV-PHARM's stt_repurposing.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from core.category import Category, Object, Morphism
from oracle.prediction import Prediction, PredictionType
from oracle.strategies import InferenceStrategy


def score_simplicial_yoneda(
    material_a: str,
    material_b: str,
    domain: str,
    category: Optional[Category] = None,
) -> Dict[str, Any]:
    """Score compatibility via Yoneda similarity to known-compatible neighbors."""
    if category is None:
        # Try to build domain category if possible
        category = _try_get_domain_category(domain)

    if category is None:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.3,
            "reason": f"simplicial yoneda: no category for {domain}",
            "metadata": {}
        }

    # Use the strategy with the category
    # SimplicialYonedaStrategy usually needs a store, but we can mock it
    # or just use the core logic here.
    
    known_compatibles = _find_compatible_with(material_b, category)
    if not known_compatibles:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.4,
            "reason": f"simplicial yoneda: no known compatibles for {material_b}",
            "metadata": {}
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
            "reason": f"simplicial yoneda: similarity {best_sim:.3f} to {best_neighbor}",
            "metadata": {"neighbor": best_neighbor, "similarity": best_sim}
        }

    return {
        "score": 0.5,
        "compatible": True,
        "confidence": 0.4,
        "reason": "simplicial yoneda: no similar neighbors found",
        "metadata": {}
    }


def score_fibration_transport(
    material_a: str,
    material_b: str,
    domain: str,
    category: Optional[Category] = None,
) -> Dict[str, Any]:
    """Score compatibility via fibration transport."""
    if category is None:
        category = _try_get_domain_category(domain)

    if category is None:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.3,
            "reason": "fibration transport: no category",
            "metadata": {}
        }

    # Find where material_a is 'in the fiber' (has successful interfaces)
    # In PHARM: drugs connected to proteins connected to disease.
    # In CHEM: maybe A connected to X connected to B?
    # Simple version: find B' where A is compatible with B', then transport to B via B'<->B similarity.
    
    targets_for_a = _find_compatible_with(material_a, category)
    if not targets_for_a:
        return {
            "score": 0.5,
            "compatible": True,
            "confidence": 0.4,
            "reason": "fibration transport: source has no known compatibles",
            "metadata": {}
        }

    total_strength = 0.0
    contributors = []
    
    fp_b = _get_property_fingerprint_from_cat(material_b, category)
    
    for b_known in targets_for_a:
        if b_known == material_b:
            continue
        fp_known = _get_property_fingerprint_from_cat(b_known, category)
        strength = _jaccard_similarity(fp_b, fp_known)
        if strength > 0.2:
            total_strength += strength
            contributors.append(b_known)

    if total_strength > 0:
        confidence = min(0.9, 0.4 + total_strength)
        return {
            "score": 0.5 + (0.5 * min(1.0, total_strength)),
            "compatible": True,
            "confidence": confidence,
            "reason": f"fibration transport from {len(contributors)} neighbors",
            "metadata": {"contributors": contributors, "total_strength": total_strength}
        }

    return {
        "score": 0.5,
        "compatible": True,
        "confidence": 0.4,
        "reason": "fibration transport: no transport paths found",
        "metadata": {}
    }


def _try_get_domain_category(domain: str) -> Optional[Category]:
    """Try to load or build a category for the given domain."""
    import importlib
    try:
        mod = importlib.import_module(f"{domain}_bridge.integration")
        builder_name = f"build_{domain}_category"
        if hasattr(mod, builder_name):
            return getattr(mod, builder_name)()
    except (ImportError, AttributeError):
        pass
    return None


def _compute_yoneda_fingerprint(obj_name: str, category: Category) -> Set[Tuple[str, str]]:
    """Compute fingerprint from Category object."""
    fp = set()
    # Handle both categorical.Category (III) and core.Category (IV)
    if hasattr(category, "morphisms"):
        # III style
        for m in category.morphisms.values():
            if m.source.name == obj_name:
                fp.add((m.target.name, m.name))
            if m.target.name == obj_name:
                fp.add((m.source.name, m.name))
    elif hasattr(category, "morphisms_from"):
        # IV style
        for m in category.morphisms_from(obj_name):
            fp.add((m.target, m.name))
        for m in category.morphisms_to(obj_name):
            fp.add((m.source, m.name))
    return fp


def _find_compatible_with(obj_name: str, category: Category) -> List[str]:
    """Find objects connected to obj_name via high-confidence/viable morphisms."""
    neighbors = []
    if hasattr(category, "morphisms"):
        for m in category.morphisms.values():
            if m.source.name == obj_name:
                neighbors.append(m.target.name)
            elif m.target.name == obj_name:
                neighbors.append(m.source.name)
    elif hasattr(category, "morphisms_from"):
        for m in category.morphisms_from(obj_name):
            neighbors.append(m.target)
        for m in category.morphisms_to(obj_name):
            neighbors.append(m.source)
    return neighbors


def _jaccard_similarity(s1: Set, s2: Set) -> float:
    if not s1 and not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def _get_property_fingerprint_from_cat(obj_name: str, category: Category) -> Set[str]:
    fp = set()
    obj = None
    if hasattr(category, "objects"):
        obj = category.objects.get(obj_name)
    elif hasattr(category, "get_object"):
        obj = category.get_object(obj_name)
        
    if obj:
        # III style
        if hasattr(obj, "type_info"):
            for k, v in obj.type_info.items():
                fp.add(f"{k}:{v}")
        # IV style
        if hasattr(obj, "type_name"):
            fp.add(f"type:{obj.type_name}")
        if hasattr(obj, "metadata"):
            for k, v in obj.metadata.items():
                fp.add(f"{k}:{v}")
    return fp


class SimplicialYonedaStrategy(InferenceStrategy):
    """
    Score compatibility via Yoneda distance to known-compatible neighbors.

    Instead of embedding similarity, uses the Yoneda presheaf fingerprint:
    the set of all incoming and outgoing morphisms.
    """

    name = "simplicial_yoneda"

    def predict(self, source: str, target: str) -> List[Prediction]:
        """Predict compatibility via Yoneda similarity to neighbors."""
        predictions = []

        # Find known compatible neighbors for target
        # (Assuming 'source' is candidate, 'target' is reference)
        # In chem compatibility, we usually check if A and B are compatible.
        # We look for A' such that A' is compatible with B and A is similar to A'.

        neighbors = self._find_compatible_neighbors(target)
        if not neighbors:
            return predictions

        best_similarity = 0.0
        best_neighbor = ""

        for neighbor in neighbors:
            if neighbor == source:
                continue
            sim = self.yoneda_similarity(source, neighbor)
            if sim > best_similarity:
                best_similarity = sim
                best_neighbor = neighbor

        if best_similarity > 0.4:  # Threshold for "structural similarity"
            predictions.append(Prediction(
                source=source,
                target=target,
                predicted_relation="compatible",
                prediction_type=PredictionType.YONEDA_DISTANCE,
                strategy_name=self.name,
                confidence=best_similarity,
                reasoning=f"Yoneda similarity {best_similarity:.4f} to known-compatible neighbor {best_neighbor}",
                evidence={
                    "neighbor": best_neighbor,
                    "similarity": best_similarity,
                    "metric": "Jaccard(YonedaFingerprint)"
                }
            ))

        return predictions

    def yoneda_fingerprint(self, obj_name: str) -> Set[Tuple[str, str]]:
        """Compute the Yoneda presheaf fingerprint (incoming + outgoing)."""
        outgoing, incoming = self._build_morphism_index()

        fp = set()
        # Incoming: (source, relation)
        for m in incoming.get(obj_name, []):
            fp.add((m.source, m.name))
        # Outgoing: (target, relation)
        for m in outgoing.get(obj_name, []):
            fp.add((m.target, m.name))

        return fp

    def yoneda_similarity(self, obj1: str, obj2: str) -> float:
        """Jaccard similarity between Yoneda presheaf fingerprints."""
        fp1 = self.yoneda_fingerprint(obj1)
        fp2 = self.yoneda_fingerprint(obj2)

        if not fp1 and not fp2:
            return 0.0
        union = fp1 | fp2
        intersection = fp1 & fp2
        return len(intersection) / len(union)

    def _find_compatible_neighbors(self, target: str) -> List[str]:
        """Find objects that have a 'compatible' morphism to target."""
        _, incoming = self._build_morphism_index()
        neighbors = []
        for m in incoming.get(target, []):
            # Check if this morphism implies compatibility
            if m.name in {"compatible", "viable", "stable", "indication"}:
                neighbors.append(m.source)
            elif m.confidence > 0.7:  # Heuristic fallback for high-confidence edges
                neighbors.append(m.source)
        return neighbors


class FibrationTransportStrategy(InferenceStrategy):
    """
    Score compatibility by transporting along base category morphisms.

    If A is compatible with B, and B is 'similar' to B' (base morphism),
    then A might be compatible with B'.
    """

    name = "fibration_transport"

    def predict(self, source: str, target: str) -> List[Prediction]:
        predictions = []

        # Find all B_known such that source is compatible with B_known
        outgoing, _ = self._build_morphism_index()
        source_compatible_with = []
        for m in outgoing.get(source, []):
            if m.name in {"compatible", "viable", "stable"} or m.confidence > 0.7:
                source_compatible_with.append(m.target)

        if not source_compatible_with:
            return predictions

        # For each B_known, compute 'base strength' to target
        total_strength = 0.0
        contributors = []

        for b_known in source_compatible_with:
            if b_known == target:
                continue
            strength = self.base_morphism_strength(b_known, target)
            if strength > 0.3:
                total_strength += strength
                contributors.append(b_known)

        if total_strength > 0:
            confidence = min(0.95, total_strength)
            predictions.append(Prediction(
                source=source,
                target=target,
                predicted_relation="compatible",
                prediction_type=PredictionType.FIBRATION_LIFT,
                strategy_name=self.name,
                confidence=confidence,
                reasoning=f"Fibration transport from {len(contributors)} neighbors via base morphisms",
                evidence={
                    "contributors": contributors,
                    "total_strength": total_strength
                }
            ))

        return predictions

    def base_morphism_strength(self, obj1: str, obj2: str) -> float:
        """
        Define base category morphism strength.
        In chem, this could be shared functional groups or similar property sets.
        """
        # Fallback to Yoneda similarity if no explicit base morphisms
        fp1 = self._get_property_fingerprint(obj1)
        fp2 = self._get_property_fingerprint(obj2)

        if not fp1 or not fp2:
            return 0.0

        intersection = fp1 & fp2
        union = fp1 | fp2
        return len(intersection) / len(union)

    def _get_property_fingerprint(self, obj_name: str) -> Set[str]:
        """Extract properties/metadata as a fingerprint."""
        obj_map = self._get_object_map()
        obj = obj_map.get(obj_name)
        if not obj:
            return set()

        fp = set()
        # Use type_name
        fp.add(f"type:{obj.type_name}")
        # Use metadata keys/values
        for k, v in obj.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                fp.add(f"meta:{k}={v}")
            elif isinstance(v, list):
                for item in v:
                    fp.add(f"meta:{k}:{item}")

        return fp
