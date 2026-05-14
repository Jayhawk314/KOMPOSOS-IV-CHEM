# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Crystal Structure Type Predictor

Predicts crystal structure type (layered, spinel, olivine, garnet, perovskite,
etc.) for a given chemical composition using three evidence sources fused via
Dempster-Shafer theory:

1. Rule-based: Deterministic composition-pattern rules (highest reliability)
2. Kan extension: Weighted vote over k-nearest known materials
3. Goldschmidt: Tolerance factor discriminator

This narrows the 3D structural search space for downstream DFT/experiment.
KOMPOSOS tells you WHAT structure family to expect; CuspAI/GNoME can then
generate the actual 3D atom positions within that family.

References:
- Goldschmidt, Naturwissenschaften 14, 477 (1926)
- Shannon, Acta Cryst. A32, 751 (1976) -- ionic radii
- Pauling, J. Am. Chem. Soc. 51, 1010 (1929) -- radius ratio rules
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .parser import (
    parse_formula, composition_vector, ELEMENT_TABLE, SHORTHAND_MAP,
)
from .formation_energy import KNOWN_EF, _goldschmidt_tolerance
from categorical.dempster_shafer import MassFunction, combine


# ═══════════════════════════════════════════════════════════════════════════
# STRUCTURE TYPES
# ═══════════════════════════════════════════════════════════════════════════

# All known structure types across the codebase
STRUCTURE_TYPES = [
    "layered",          # R-3m, LiMO2 (NMC, LCO, NCA)
    "spinel",           # Fd-3m (LiMn2O4, Li4Ti5O12, LNMO)
    "olivine",          # Pnma (LiFePO4, LiMnPO4, LiCoPO4)
    "garnet",           # Ia-3d (Li7La3Zr2O12)
    "perovskite",       # Pm-3m (BaTiO3, SrTiO3)
    "rock_salt",        # Fm-3m (NiO, CoO, MgO, CaO, BaO)
    "corundum",         # R-3c (Al2O3, Fe2O3)
    "rutile",           # P42/mnm (TiO2, MnO2)
    "fluorite",         # Fm-3m (ZrO2-cubic, CeO2)
    "zinc_blende",      # F-43m (GaAs, SiC, ZnS)
    "wurtzite",         # P63mc (GaN, ZnO)
    "diamond",          # Fd-3m (Si, C-diamond, Ge)
    "thio-LISICON",     # (Li10GeP2S12, LGPS)
    "NASICON",          # R-3c (LATP, LAGP)
    "thiophosphate",    # (Li3PS4, argyrodite)
    "antifluorite",     # Fm-3m (Li2O, Na2O)
    "bcc",              # Im-3m (Li, Fe, W, Cr)
    "fcc",              # Fm-3m (Cu, Al, Ni, Au)
    "hcp",              # P63/mmc (Ti, Zr, Mg)
    "quartz",           # P3121 (SiO2)
    "hexagonal",        # (La2O3, other rare earth oxides)
]

# Element ground-state crystal structures
ELEMENT_STRUCTURES = {
    "Li": "bcc", "Na": "bcc", "K": "bcc", "Fe": "bcc", "Cr": "bcc",
    "W": "bcc", "Mo": "bcc", "V": "bcc", "Nb": "bcc",
    "Cu": "fcc", "Al": "fcc", "Ni": "fcc", "Ca": "fcc", "Sr": "fcc",
    "Ti": "hcp", "Zr": "hcp", "Mg": "hcp", "Co": "hcp", "Zn": "hcp",
    "Si": "diamond", "Ge": "diamond", "C": "diamond",
}

# III-V compound structure assignment by electronegativity difference
# Larger EN diff + lighter elements -> wurtzite; smaller diff -> zinc_blende
IIIV_WURTZITE = {"GaN", "AlN", "InN", "ZnO", "ZnS", "CdS", "BeO"}
IIIV_ZINCBLENDE = {"GaAs", "GaP", "InP", "InAs", "InSb", "GaSb", "SiC",
                   "ZnSe", "ZnTe", "CdTe", "CdSe", "AlAs", "AlP"}


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT DATACLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class StructurePrediction:
    """Crystal structure type prediction with multi-source evidence."""
    predicted_type: str                 # Top prediction
    probabilities: Dict[str, float]     # type -> probability (top types)
    confidence: float                   # 0-1
    goldschmidt_t: Optional[float]      # Tolerance factor if applicable
    sources: Dict[str, str]             # source_name -> its prediction
    detail: str                         # Human-readable explanation

    def to_dict(self) -> Dict:
        return {
            "predicted_type": self.predicted_type,
            "probabilities": self.probabilities,
            "confidence": self.confidence,
            "goldschmidt_t": self.goldschmidt_t,
            "sources": self.sources,
            "detail": self.detail,
        }


# ═══════════════════════════════════════════════════════════════════════════
# STRUCTURE TYPE PREDICTOR
# ═══════════════════════════════════════════════════════════════════════════

class StructureTypePredictor:
    """
    Predicts crystal structure type from chemical composition.

    Uses three evidence sources fused via Dempster-Shafer:
    1. Rule-based composition-pattern matching (high reliability)
    2. Kan extension: IDW vote over nearest known materials
    3. Goldschmidt tolerance factor (for perovskite/layered discrimination)

    Usage:
        stp = StructureTypePredictor()
        result = stp.predict("NMC811")
        print(result.predicted_type)  # "layered"
        print(result.confidence)      # ~0.92
    """

    def __init__(self, k: int = 5):
        self.k = k
        self.known = KNOWN_EF  # 37 materials with structure_type
        # Lazy-cached MP data for _mp_predict (avoids reloading 103K entries)
        self._mp_index = None
        self._mp_entries_cached = None
        self._mp_loaded = False

    def predict(self, formula: str) -> StructurePrediction:
        """Predict crystal structure type for a chemical formula."""
        resolved = SHORTHAND_MAP.get(formula, formula)
        comp = parse_formula(resolved)

        # Source 1: Rule-based (highest reliability)
        rule_type, rule_conf, rule_detail = self._rule_predict(comp)

        # Source 2: Kan extension (weighted vote over nearest known)
        kan_probs, kan_top, kan_conf = self._kan_predict(comp)

        # Source 3: Goldschmidt tolerance factor
        gold_type, gold_conf, gold_t = self._goldschmidt_classify(comp)

        # Source 4: MP structure vote (if available)
        mp_type, mp_conf = self._mp_predict(comp)

        # Collect sources
        sources = {}
        if rule_type:
            sources["rule"] = rule_type
        if kan_top:
            sources["kan_extension"] = kan_top
        if gold_type:
            sources["goldschmidt"] = gold_type
        if mp_type:
            sources["materials_project"] = mp_type

        # Fuse via Dempster-Shafer
        probabilities, fused_conf = self._fuse(
            rule_type, rule_conf,
            kan_probs, kan_conf,
            gold_type, gold_conf,
            mp_type=mp_type, mp_conf=mp_conf,
        )

        # Top prediction
        if probabilities:
            predicted_type = max(probabilities, key=probabilities.get)
        elif rule_type:
            predicted_type = rule_type
        elif kan_top:
            predicted_type = kan_top
        else:
            predicted_type = "unknown"

        # Build detail string
        detail = self._build_detail(predicted_type, sources, gold_t, fused_conf)

        # Filter probabilities to top 5
        sorted_probs = sorted(probabilities.items(), key=lambda x: -x[1])
        top_probs = {k: round(v, 4) for k, v in sorted_probs[:5] if v > 0.01}

        return StructurePrediction(
            predicted_type=predicted_type,
            probabilities=top_probs,
            confidence=round(fused_conf, 3),
            goldschmidt_t=round(gold_t, 4) if gold_t is not None else None,
            sources=sources,
            detail=detail,
        )

    # ── Source 1: Rule-based prediction ────────────────────────────────

    def _rule_predict(self, comp: Dict[str, float]
                      ) -> Tuple[Optional[str], float, str]:
        """
        Deterministic composition-pattern rules.
        Returns (type, confidence, detail) or (None, 0, "").
        """
        elements = set(comp.keys())
        has_li = "Li" in comp
        has_o = "O" in comp
        has_s = "S" in comp
        has_p = "P" in comp

        tm_elements = {"Ni", "Mn", "Co", "Fe", "Ti", "Cr", "V"}
        tms_present = elements & tm_elements
        tm_total = sum(comp.get(m, 0) for m in tm_elements)

        li_amt = comp.get("Li", 0)
        o_amt = comp.get("O", 0)
        p_amt = comp.get("P", 0)
        mn_amt = comp.get("Mn", 0)
        s_amt = comp.get("S", 0)

        # ── Pure element ──────────────────────────────────────────
        if len(elements) == 1:
            elem = list(elements)[0]
            struct = ELEMENT_STRUCTURES.get(elem)
            if struct:
                return struct, 0.95, f"Pure element {elem}: {struct}"
            return None, 0.0, ""

        # ── Graphite (C with stoich > 1) ──────────────────────────
        if elements == {"C"} or (len(elements) == 1 and "C" in elements):
            if comp.get("C", 0) > 1:
                return "diamond", 0.80, "Carbon allotrope (graphite/diamond)"

        # ── III-V / II-VI semiconductors ──────────────────────────
        if len(elements) == 2 and not has_li and not has_o:
            formula_str = "".join(sorted(elements))
            # Check known assignments
            for name in IIIV_WURTZITE:
                if set(parse_formula(name).keys()) == elements:
                    return "wurtzite", 0.90, f"Known wurtzite compound"
            for name in IIIV_ZINCBLENDE:
                if set(parse_formula(name).keys()) == elements:
                    return "zinc_blende", 0.90, f"Known zincblende compound"

        # ── Garnet: Li7La3Zr2O12-type ─────────────────────────────
        if has_li and "La" in comp and "Zr" in comp and has_o and li_amt >= 5:
            return "garnet", 0.95, "Li-La-Zr-O garnet (LLZO-type)"

        # ── Thio-LISICON: Li10GeP2S12-type ────────────────────────
        if has_li and has_s and has_p and li_amt >= 3:
            if "Ge" in comp or "Si" in comp or "Sn" in comp:
                return "thio-LISICON", 0.90, "Li-M-P-S thio-LISICON"
            return "thiophosphate", 0.85, "Li-P-S thiophosphate"

        # ── NASICON: Li-Al-Ti-P-O ─────────────────────────────────
        if has_li and "Al" in comp and "Ti" in comp and has_p and has_o:
            return "NASICON", 0.90, "Li-Al-Ti-P-O NASICON framework"

        # ── Olivine: LiMPO4 ──────────────────────────────────────
        if has_li and has_p and has_o and tms_present:
            # Check stoichiometry: P:O should be ~1:4
            if p_amt > 0 and abs(o_amt / p_amt - 4.0) < 1.0:
                return "olivine", 0.92, "Li-M-PO4 olivine phosphate"

        # ── Spinel: LiMn2O4-type (Mn > 1 per formula) ────────────
        if has_li and has_o and mn_amt > 1.0:
            return "spinel", 0.90, "Li-Mn-O spinel (Mn>1 per f.u.)"

        # ── Spinel: LiNi0.5Mn1.5O4 (high-voltage) ───────────────
        if has_li and has_o and mn_amt > 0.8 and "Ni" in comp:
            ni_amt = comp.get("Ni", 0)
            if mn_amt + ni_amt > 1.5:
                return "spinel", 0.88, "Li-Ni-Mn-O high-voltage spinel"

        # ── Layered: LiMO2 (TM_total ~ 1, O ~ 2) ────────────────
        if has_li and has_o and tms_present:
            if 0.5 <= tm_total <= 1.5 and 1.5 <= o_amt <= 2.5:
                return "layered", 0.92, "Li-TM-O2 layered oxide (R-3m)"

        # ── Antifluorite: Li2O, Na2O ──────────────────────────────
        if has_o and o_amt <= 1.5 and not tms_present and not has_p:
            alkali_total = sum(comp.get(a, 0) for a in ["Li", "Na", "K"])
            if alkali_total >= 1.5 and alkali_total / o_amt > 1.5:
                return "antifluorite", 0.85, "A2O antifluorite"

        # ── Perovskite: ABO3 ─────────────────────────────────────
        if has_o and o_amt >= 2.5 and not has_li:
            # Check for A-site (large: Ba, Sr, Ca, La) + B-site (Ti, Zr, etc.)
            a_site = {"Ba", "Sr", "Ca", "La", "K", "Na"}
            b_site = {"Ti", "Zr", "Nb", "Fe", "Mn", "Co", "Ni"}
            has_a = bool(elements & a_site)
            has_b = bool(elements & b_site)
            if has_a and has_b:
                a_total = sum(comp.get(e, 0) for e in a_site if e in comp)
                b_total = sum(comp.get(e, 0) for e in b_site if e in comp)
                if abs(a_total - b_total) < 0.5 and abs(o_amt - 3 * b_total) < 1.5:
                    return "perovskite", 0.88, "ABO3 perovskite"

        # ── Binary oxides ─────────────────────────────────────────
        if has_o and len(elements) == 2:
            cation = (elements - {"O"}).pop()
            cation_amt = comp.get(cation, 0)

            ratio = o_amt / cation_amt if cation_amt > 0 else 0

            # A2O3 -> corundum
            if abs(ratio - 1.5) < 0.2:
                return "corundum", 0.85, f"{cation}2O3 corundum structure"

            # AO2 -> rutile or fluorite
            if abs(ratio - 2.0) < 0.2:
                # Rutile for Ti, Mn, Sn; fluorite for Zr, Ce
                if cation in ("Zr", "Ce"):
                    return "fluorite", 0.82, f"{cation}O2 fluorite structure"
                return "rutile", 0.82, f"{cation}O2 rutile structure"

            # AO -> rock salt
            if abs(ratio - 1.0) < 0.2:
                return "rock_salt", 0.85, f"{cation}O rock salt structure"

        return None, 0.0, ""

    # ── Source 2: Kan extension vote ───────────────────────────────

    def _kan_predict(self, comp: Dict[str, float]
                     ) -> Tuple[Dict[str, float], Optional[str], float]:
        """
        Kan extension: IDW-weighted vote over nearest known materials.
        Returns (probabilities, top_type, confidence).
        """
        query_vec = composition_vector(comp)
        epsilon = 0.01

        distances = []
        for entry in self.known:
            # Skip reference elements
            if entry.name.endswith("_ref"):
                continue
            dist = float(np.linalg.norm(query_vec - entry.vector))
            distances.append((entry, dist))

        distances.sort(key=lambda x: x[1])
        neighbours = distances[:self.k]

        if not neighbours:
            return {}, None, 0.0

        # IDW weights
        weights = [1.0 / (d + epsilon) for _, d in neighbours]
        total_w = sum(weights)
        weights = [w / total_w for w in weights]

        # Vote for structure types
        votes: Dict[str, float] = {}
        for (entry, _), w in zip(neighbours, weights):
            st = entry.structure_type
            votes[st] = votes.get(st, 0.0) + w

        if not votes:
            return {}, None, 0.0

        top_type = max(votes, key=votes.get)

        # Confidence: how concentrated is the vote?
        top_weight = votes[top_type]
        confidence = top_weight  # Already normalized to [0,1]

        # Reduce confidence if nearest neighbour is far
        min_dist = neighbours[0][1]
        dist_factor = max(0.1, 1.0 - min_dist / 5.0)
        confidence *= dist_factor
        confidence = min(0.90, max(0.05, confidence))

        return votes, top_type, confidence

    # ── Source 3: Goldschmidt tolerance factor ─────────────────────

    def _goldschmidt_classify(self, comp: Dict[str, float]
                              ) -> Tuple[Optional[str], float, Optional[float]]:
        """
        Use Goldschmidt tolerance factor to discriminate structures.
        Returns (type, confidence, t_value).
        """
        t = _goldschmidt_tolerance(comp)
        if t is None:
            return None, 0.0, None

        # Check if this is an ABO3 perovskite candidate
        has_li = "Li" in comp
        a_site = {"Ba", "Sr", "Ca", "La", "K", "Na"}
        is_perovskite_candidate = bool(set(comp.keys()) & a_site) and not has_li

        if is_perovskite_candidate:
            if 0.85 <= t <= 1.05:
                return "perovskite", 0.80, t
            elif 0.75 <= t < 0.85:
                return "spinel", 0.50, t  # Distorted, possibly different
        else:
            # Li-TM-O system
            if 0.85 <= t <= 1.00:
                return "layered", 0.75, t
            elif 0.75 <= t < 0.85:
                return "spinel", 0.60, t
            elif t > 1.00:
                return "layered", 0.55, t  # Stretched tolerance

        return None, 0.3, t

    # ── Source 4: Materials Project vote ────────────────────────────

    def _mp_predict(self, comp: Dict[str, float]
                    ) -> Tuple[Optional[str], float]:
        """
        Vote for crystal system from nearest Materials Project entries.
        Returns (crystal_system_mapped_to_structure_type, confidence).
        """
        # Lazy-load and cache MP data + spatial index (once per instance)
        if not self._mp_loaded:
            self._mp_loaded = True
            try:
                from .mp_loader import MPCache
                from .spatial_index import CompositionIndex
                cache = MPCache()
                if cache.is_available():
                    entries = cache.load_entries_with_lattice()
                    if entries:
                        self._mp_entries_cached = entries
                        self._mp_index = CompositionIndex(entries)
            except Exception:
                pass

        if self._mp_index is None:
            return None, 0.0

        query_vec = composition_vector(comp)
        neighbours = self._mp_index.nearest_k(query_vec, k=self.k)

        if not neighbours:
            return None, 0.0

        # Map MP crystal system to our structure types
        CS_TO_STRUCT = {
            "trigonal": "layered",     # R-3m layered oxides
            "cubic": "rock_salt",      # Could be spinel, rock_salt, etc.
            "orthorhombic": "olivine", # Pnma olivine
            "hexagonal": "hexagonal",
            "tetragonal": "rutile",
            "monoclinic": "layered",
        }

        # Also map known space groups to structure types
        SG_TO_STRUCT = {
            "R-3m": "layered",
            "Fd-3m": "spinel",
            "Pnma": "olivine",
            "Ia-3d": "garnet",
            "Pm-3m": "perovskite",
            "Fm-3m": "rock_salt",
            "R-3c": "corundum",
            "P42/mnm": "rutile",
            "F-43m": "zinc_blende",
            "P63mc": "wurtzite",
            "Im-3m": "bcc",
            "P63/mmc": "hcp",
        }

        # IDW weighted vote
        epsilon = 0.01
        raw_weights = [1.0 / (d + epsilon) for _, d in neighbours]
        total_w = sum(raw_weights)
        weights = [w / total_w for w in raw_weights]

        votes: Dict[str, float] = {}
        for (entry, _), w in zip(neighbours, weights):
            # Try space group mapping first (more specific)
            sg = getattr(entry, 'space_group_symbol', '')
            cs = getattr(entry, 'crystal_system', '').lower()

            struct_type = SG_TO_STRUCT.get(sg) or CS_TO_STRUCT.get(cs, cs)
            if struct_type:
                votes[struct_type] = votes.get(struct_type, 0.0) + w

        if not votes:
            return None, 0.0

        winner = max(votes, key=votes.get)
        confidence = votes[winner]

        # Distance penalty
        min_dist = neighbours[0][1]
        dist_factor = max(0.1, 1.0 - min_dist / 5.0)
        confidence *= dist_factor
        confidence = min(0.85, max(0.05, confidence))

        return winner, confidence

    # ── Dempster-Shafer Fusion ─────────────────────────────────────

    def _fuse(self,
              rule_type: Optional[str], rule_conf: float,
              kan_probs: Dict[str, float], kan_conf: float,
              gold_type: Optional[str], gold_conf: float,
              mp_type: Optional[str] = None, mp_conf: float = 0.0,
              ) -> Tuple[Dict[str, float], float]:
        """
        Fuse three evidence sources via Dempster-Shafer.

        Strategy: Rules are near-deterministic for common structures.
        When rules fire with high confidence, they dominate.
        Kan extension serves as confirmation or fallback.
        Goldschmidt provides weak additional evidence.
        """
        # Start with Kan probabilities as base (already a distribution)
        probs: Dict[str, float] = dict(kan_probs)

        # If rules fired, boost the rule prediction heavily
        if rule_type and rule_conf > 0.5:
            # D-S fusion: rule source with high reliability
            frame = frozenset(["agree", "disagree"])
            agree = frozenset(["agree"])

            # Rule confidence
            m_rule = MassFunction(masses={
                agree: rule_conf,
                frame: 1.0 - rule_conf,
            })

            # Kan agreement with rule
            kan_agrees = kan_probs.get(rule_type, 0.0)
            kan_agree_conf = kan_conf * kan_agrees if kan_conf > 0 else 0.0
            m_kan = MassFunction(masses={
                agree: min(0.9, kan_agree_conf + 0.1),  # Base belief
                frame: 1.0 - min(0.9, kan_agree_conf + 0.1),
            })

            try:
                combined, conflict = combine(m_rule, m_kan)
                fused_belief = combined.belief(agree)
            except ValueError:
                fused_belief = rule_conf

            # Goldschmidt agreement
            if gold_type and gold_type == rule_type:
                fused_belief = min(0.98, fused_belief + gold_conf * 0.1)
            elif gold_type and gold_type != rule_type and gold_conf > 0.6:
                fused_belief *= 0.9  # Slight penalty for disagreement

            # MP agreement
            if mp_type and mp_type == rule_type:
                fused_belief = min(0.98, fused_belief + mp_conf * 0.08)
            elif mp_type and mp_type != rule_type and mp_conf > 0.6:
                fused_belief *= 0.95  # Small penalty for disagreement

            # Build probability distribution dominated by rule prediction
            probs = {}
            probs[rule_type] = fused_belief
            remaining = 1.0 - fused_belief

            # Distribute remaining probability among Kan votes
            for st, p in kan_probs.items():
                if st != rule_type:
                    probs[st] = remaining * p

            fused_conf = min(0.98, fused_belief)
            return probs, fused_conf

        # Rules didn't fire -- fall back to Kan + Goldschmidt + MP
        if kan_probs:
            if gold_type and gold_type in kan_probs:
                # Goldschmidt confirms a Kan prediction
                kan_probs[gold_type] = min(0.95,
                    kan_probs[gold_type] + gold_conf * 0.15)
            if mp_type and mp_type in kan_probs:
                # MP confirms a Kan prediction
                kan_probs[mp_type] = min(0.95,
                    kan_probs[mp_type] + mp_conf * 0.12)

            # Renormalize
            total = sum(kan_probs.values())
            if total > 0:
                kan_probs = {k: v / total for k, v in kan_probs.items()}

            fused_conf = kan_conf
            top_kan = max(kan_probs, key=kan_probs.get) if kan_probs else None
            if gold_type and top_kan == gold_type:
                fused_conf = min(0.90, fused_conf + 0.10)
            if mp_type and top_kan == mp_type:
                fused_conf = min(0.92, fused_conf + 0.08)

            return kan_probs, min(0.92, max(0.1, fused_conf))

        # Nothing available
        if gold_type:
            return {gold_type: gold_conf}, gold_conf

        return {"unknown": 1.0}, 0.05

    # ── Detail builder ─────────────────────────────────────────────

    def _build_detail(self, predicted: str, sources: Dict[str, str],
                      gold_t: Optional[float], confidence: float) -> str:
        """Build human-readable explanation."""
        parts = [f"Predicted: {predicted} (confidence={confidence:.2f})"]

        # Source agreement
        source_types = set(sources.values())
        if len(source_types) == 1 and len(sources) > 1:
            parts.append("All sources agree.")
        elif len(source_types) > 1:
            parts.append("Sources: " + ", ".join(
                f"{k}={v}" for k, v in sources.items()))

        if gold_t is not None:
            parts.append(f"Goldschmidt t={gold_t:.3f}")

        return " ".join(parts)


if __name__ == "__main__":
    stp = StructureTypePredictor()

    print("=" * 70)
    print("Crystal Structure Type Predictor -- Demo")
    print("=" * 70)

    test_formulas = [
        ("NMC811", "layered"),
        ("NMC622", "layered"),
        ("NMC111", "layered"),
        ("NMC721", "layered"),
        ("LFP", "olivine"),
        ("LMO", "spinel"),
        ("LNMO", "spinel"),
        ("LLZO", "garnet"),
        ("LGPS", "thio-LISICON"),
        ("LATP", "NASICON"),
        ("LCO", "layered"),
        ("NCA", "layered"),
        ("BaTiO3", "perovskite"),
        ("Al2O3", "corundum"),
        ("TiO2", "rutile"),
        ("ZrO2", "fluorite"),
        ("NiO", "rock_salt"),
        ("MgO", "rock_salt"),
        ("GaAs", "zinc_blende"),
        ("GaN", "wurtzite"),
        ("Si", "diamond"),
        ("Li", "bcc"),
        ("Cu", "fcc"),
    ]

    n_correct = 0
    for formula, expected in test_formulas:
        result = stp.predict(formula)
        match = "OK" if result.predicted_type == expected else "MISS"
        if match == "OK":
            n_correct += 1
        print(f"  {formula:12s} -> {result.predicted_type:15s} "
              f"(expected: {expected:15s}) [{match}] "
              f"conf={result.confidence:.2f}  t={result.goldschmidt_t}")

    print(f"\nAccuracy: {n_correct}/{len(test_formulas)} "
          f"({100*n_correct/len(test_formulas):.0f}%)")
