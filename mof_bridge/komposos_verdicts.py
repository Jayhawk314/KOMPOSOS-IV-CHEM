# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS Verdict Engine for MOF Linkers
=========================================

Scores linker candidates with 5 verdicts using ZFC + CAT dual-engine reasoning.

Verdicts:
1. Synthesizability — Can we make it?
2. Toxicity — Is it safe?
3. Stability — Will it survive operating conditions?
4. Activity/Selectivity — Does it work for the target application?
5. Electrical Conductivity — Does it conduct electrons?

Each verdict classified as:
- AGREE: Both ZFC (logic) and CAT (composition) confirm
- HOLLOW: CAT yes, ZFC no (structurally plausible but logically impossible)
- ORPHAN: ZFC yes, CAT no (logically forced but structurally unknown)
- REJECT: Both no

Pattern follows: oracle/material_zfc_constraints.py + zfc/bridge.py
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from mof_bridge.atomic_descriptors import compute_atomic_descriptors


@dataclass
class LinkerVerdictResult:
    """Result from scoring a linker candidate with all 5 verdicts."""
    linker_smiles: str
    verdicts: Dict[str, str]            # verdict_name → "AGREE"/"HOLLOW"/"ORPHAN"/"REJECT"
    verdict_scores: Dict[str, float]    # verdict_name → confidence (0-1)
    morphism_integrity: float           # CAT layer integrity score (0-1)
    zfc_constraints_passed: int         # Number of ZFC constraints satisfied
    reasoning_traces: Dict[str, str]    # verdict_name → explanation
    overall_viable: bool                # True if all verdicts == AGREE

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'linker_smiles': self.linker_smiles,
            'verdicts': self.verdicts,
            'verdict_scores': self.verdict_scores,
            'morphism_integrity': self.morphism_integrity,
            'zfc_constraints_passed': self.zfc_constraints_passed,
            'reasoning_traces': self.reasoning_traces,
            'overall_viable': self.overall_viable,
        }


class LinkerVerdictEngine:
    """Score MOF linker candidates with 5 KOMPOSOS verdicts.

    Each verdict uses dual-engine reasoning:
    - ZFC Layer: Logic rules on atomic descriptors
    - CAT Layer: Morphism integrity (structural composition)
    - Classification: AGREE/HOLLOW/ORPHAN/REJECT
    """

    def __init__(self):
        """Initialize verdict engine."""
        # Known toxic functional groups (SMARTS patterns)
        self.toxic_groups = [
            'isocyanate', 'diazo', 'azide', 'peroxide',
            'N(=O)=O',  # Nitro (some are toxic)
        ]

        # Known stable aromatic backbones (for CAT layer similarity)
        self.stable_backbones = [
            'benzene', 'biphenyl', 'naphthalene', 'anthracene',
            'pyridine', 'imidazole', 'triazole',
        ]

    def score_verdicts(
        self,
        linker_smiles: str,
        application_context: str,
    ) -> LinkerVerdictResult:
        """Run dual-engine reasoning on a linker candidate.

        Args:
            linker_smiles: Canonical SMILES string
            application_context: Target application (breath_VOC_sensing, etc.)

        Returns:
            LinkerVerdictResult with all 5 verdicts + reasoning traces

        Raises:
            ImportError: If RDKit not installed
            ValueError: If SMILES invalid
        """
        # Extract atomic descriptors
        try:
            descriptors = compute_atomic_descriptors(linker_smiles)
        except Exception as e:
            raise ValueError(f"Failed to compute descriptors: {e}")

        # Compute morphism integrity (CAT layer)
        morphism_integrity = self._compute_morphism_integrity(descriptors)

        # Score each verdict
        verdicts = {}
        verdict_scores = {}
        reasoning_traces = {}
        zfc_passed = 0

        # 1. Synthesizability
        synth_score, synth_zfc, synth_cat, synth_trace = self._score_synthesizability(descriptors)
        verdict, score = self._classify_verdict(synth_zfc, synth_cat, morphism_integrity)
        verdicts['synthesizability'] = verdict
        verdict_scores['synthesizability'] = score
        reasoning_traces['synthesizability'] = synth_trace
        if synth_zfc:
            zfc_passed += 1

        # 2. Toxicity
        tox_score, tox_zfc, tox_cat, tox_trace = self._score_toxicity(descriptors, linker_smiles)
        verdict, score = self._classify_verdict(tox_zfc, tox_cat, morphism_integrity)
        verdicts['toxicity'] = verdict
        verdict_scores['toxicity'] = score
        reasoning_traces['toxicity'] = tox_trace
        if tox_zfc:
            zfc_passed += 1

        # 3. Stability
        stab_score, stab_zfc, stab_cat, stab_trace = self._score_stability(descriptors)
        verdict, score = self._classify_verdict(stab_zfc, stab_cat, morphism_integrity)
        verdicts['stability'] = verdict
        verdict_scores['stability'] = score
        reasoning_traces['stability'] = stab_trace
        if stab_zfc:
            zfc_passed += 1

        # 4. Activity/Selectivity
        act_score, act_zfc, act_cat, act_trace = self._score_activity(descriptors, application_context)
        verdict, score = self._classify_verdict(act_zfc, act_cat, morphism_integrity)
        verdicts['activity'] = verdict
        verdict_scores['activity'] = score
        reasoning_traces['activity'] = act_trace
        if act_zfc:
            zfc_passed += 1

        # 5. Electrical Conductivity
        cond_score, cond_zfc, cond_cat, cond_trace = self._score_conductivity(descriptors)
        verdict, score = self._classify_verdict(cond_zfc, cond_cat, morphism_integrity)
        verdicts['conductivity'] = verdict
        verdict_scores['conductivity'] = score
        reasoning_traces['conductivity'] = cond_trace
        if cond_zfc:
            zfc_passed += 1

        # Overall viability: all verdicts must be AGREE
        overall_viable = all(v == 'AGREE' for v in verdicts.values())

        return LinkerVerdictResult(
            linker_smiles=linker_smiles,
            verdicts=verdicts,
            verdict_scores=verdict_scores,
            morphism_integrity=morphism_integrity,
            zfc_constraints_passed=zfc_passed,
            reasoning_traces=reasoning_traces,
            overall_viable=overall_viable,
        )

    def _score_synthesizability(self, descriptors: Dict) -> tuple:
        """Score synthesizability verdict.

        ZFC Rules:
        - All atoms have valid valence
        - No strained rings
        - Bond orders match hybridization

        CAT Check:
        - Retrosynthetic path exists (heuristic)

        Returns:
            (score, zfc_says, cat_says, trace)
        """
        atoms = descriptors['atoms']
        bonds = descriptors['bonds']
        global_props = descriptors['global']

        # ZFC: Check bond order / hybridization consistency
        inconsistencies = 0
        for bond in bonds:
            atom_i = atoms[bond['atom_i']]
            atom_j = atoms[bond['atom_j']]

            # SP2 atoms: SINGLE bonds are normal between aromatic rings
            # (biphenyl, terphenyl, etc.) and for exocyclic substituents.
            # Only flag SP-hybridized atoms with wrong bond types.
            if 'SP' == atom_i['hybridization'] and 'SP' == atom_j['hybridization']:
                if bond['bond_type'] not in ['TRIPLE', 'DOUBLE']:
                    inconsistencies += 1
            elif 'SP3' in atom_i['hybridization'] and 'SP3' in atom_j['hybridization']:
                if bond['bond_type'] not in ['SINGLE']:
                    inconsistencies += 1

        # ZFC: Check for strained rings (very small rings)
        has_strained_ring = global_props['max_ring_size'] < 5 and global_props['num_rings'] > 0

        # ZFC verdict
        zfc_says = (inconsistencies == 0) and (not has_strained_ring)
        zfc_score = 0.9 if zfc_says else 0.3

        # CAT: Check if linker resembles known synthesizable patterns
        # Heuristic: aromatic rings + carboxyl/amine groups are common
        has_aromatic = global_props['num_aromatic_rings'] > 0
        has_functional_groups = any(
            a['element'] in ('N', 'O') and a['num_bonds'] <= 3
            for a in atoms
        )

        cat_says = has_aromatic and has_functional_groups
        cat_score = 0.8 if cat_says else 0.4

        # Reasoning trace
        trace_parts = []
        if zfc_says:
            trace_parts.append("✓ All bonds valid, no strained rings")
        else:
            if inconsistencies > 0:
                trace_parts.append(f"✗ {inconsistencies} bond/hybridization mismatches")
            if has_strained_ring:
                trace_parts.append("✗ Strained ring detected")

        if cat_says:
            trace_parts.append("✓ Resembles known synthesizable patterns")
        else:
            trace_parts.append("◇ Unusual structure, synthesis pathway unclear")

        trace = "; ".join(trace_parts)

        return (zfc_score, zfc_says, cat_says, trace)

    def _score_toxicity(self, descriptors: Dict, smiles: str) -> tuple:
        """Score toxicity verdict.

        ZFC Rules:
        - No known toxic functional groups
        - No heavy metals
        - Electrophilicity < threshold

        CAT Check:
        - Structural similarity to known safe molecules

        Returns:
            (score, zfc_says, cat_says, trace)
        """
        atoms = descriptors['atoms']

        # ZFC: Check for toxic groups (simplified - real implementation would use SMARTS)
        has_toxic_group = any(g.lower() in smiles.lower() for g in self.toxic_groups)

        # ZFC: Check for heavy metals
        heavy_metals = {'Pb', 'Hg', 'Cd', 'As', 'Cr'}
        has_heavy_metal = any(a['element'] in heavy_metals for a in atoms)

        # ZFC: Check electrophilicity (high positive charges)
        max_positive_charge = max((a['partial_charge'] for a in atoms), default=0.0)
        high_electrophilicity = max_positive_charge > 0.5

        # ZFC verdict
        zfc_says = (not has_toxic_group) and (not has_heavy_metal) and (not high_electrophilicity)
        zfc_score = 0.9 if zfc_says else 0.2

        # CAT: Organic molecules with aromatic rings are generally safe
        is_organic = all(a['element'] in ('C', 'H', 'N', 'O', 'S', 'P') for a in atoms)
        has_stable_rings = descriptors['global']['num_aromatic_rings'] > 0

        cat_says = is_organic and has_stable_rings
        cat_score = 0.8 if cat_says else 0.5

        # Reasoning trace
        trace_parts = []
        if zfc_says:
            trace_parts.append("✓ No known toxic groups, no heavy metals")
        else:
            if has_toxic_group:
                trace_parts.append("✗ Contains known toxic functional group")
            if has_heavy_metal:
                trace_parts.append("✗ Contains heavy metal")
            if high_electrophilicity:
                trace_parts.append("✗ High electrophilicity (toxic risk)")

        if cat_says:
            trace_parts.append("✓ Organic aromatic structure (generally safe)")
        else:
            trace_parts.append("◇ Unusual composition, toxicity unclear")

        trace = "; ".join(trace_parts)

        return (zfc_score, zfc_says, cat_says, trace)

    def _score_stability(self, descriptors: Dict) -> tuple:
        """Score stability verdict.

        ZFC Rules:
        - Strong bonds (no weak bonds)
        - Aromatic systems present (stabilization)

        CAT Check:
        - Similar to known stable linkers

        Returns:
            (score, zfc_says, cat_says, trace)
        """
        bonds = descriptors['bonds']
        global_props = descriptors['global']

        # ZFC: All bonds should be strong (single, double, aromatic)
        weak_bonds = [b for b in bonds if b['bond_order'] < 1.0]
        has_weak_bonds = len(weak_bonds) > 0

        # ZFC: Aromatic systems provide stability
        has_aromatic = global_props['num_aromatic_rings'] > 0

        # ZFC verdict
        zfc_says = (not has_weak_bonds) and has_aromatic
        zfc_score = 0.85 if zfc_says else 0.4

        # CAT: Check for stable patterns (aromatic rings, conjugation)
        has_conjugation = global_props['conjugation_length'] > 6
        cat_says = has_aromatic and has_conjugation
        cat_score = 0.8 if cat_says else 0.5

        # Reasoning trace
        trace_parts = []
        if zfc_says:
            trace_parts.append("✓ Strong bonds, aromatic stabilization")
        else:
            if has_weak_bonds:
                trace_parts.append(f"✗ {len(weak_bonds)} weak bonds detected")
            if not has_aromatic:
                trace_parts.append("✗ No aromatic rings (reduced stability)")

        if cat_says:
            trace_parts.append("✓ Extended conjugation enhances stability")
        else:
            trace_parts.append("◇ Limited conjugation, stability uncertain")

        trace = "; ".join(trace_parts)

        return (zfc_score, zfc_says, cat_says, trace)

    def _score_activity(self, descriptors: Dict, application: str) -> tuple:
        """Score activity/selectivity verdict (application-dependent).

        Returns:
            (score, zfc_says, cat_says, trace)
        """
        atoms = descriptors['atoms']
        global_props = descriptors['global']

        # Application-specific rules
        if application == 'breath_VOC_sensing':
            # ZFC: Need polar groups + aromatic rings
            has_polar = any(a['element'] in ('O', 'N') for a in atoms)
            has_aromatic = global_props['num_aromatic_rings'] > 0

            zfc_says = has_polar and has_aromatic
            zfc_score = 0.85 if zfc_says else 0.3

            # CAT: Check for π-π interaction capability
            cat_says = has_aromatic and global_props['conjugation_length'] > 6
            cat_score = 0.8 if cat_says else 0.4

            trace = "VOC sensing: " + (
                "✓ Polar groups + aromatics (π-π interactions)" if zfc_says
                else "✗ Missing polar groups or aromatic rings"
            )

        elif application == 'food_safety':
            # ZFC: High H-bond donor/acceptor count
            h_donors = sum(1 for a in atoms if a['element'] in ('N', 'O') and a['num_h'] > 0)
            h_acceptors = sum(1 for a in atoms if a['element'] in ('N', 'O'))

            zfc_says = (h_donors + h_acceptors) >= 4
            zfc_score = 0.8 if zfc_says else 0.3

            # CAT: Resembles known food safety sensors
            cat_says = h_acceptors > h_donors  # More acceptors = better
            cat_score = 0.75 if cat_says else 0.5

            trace = "Food safety: " + (
                f"✓ {h_donors} H-donors, {h_acceptors} H-acceptors (good for contaminant binding)"
                if zfc_says else "✗ Insufficient H-bonding sites"
            )

        elif application == 'PFAS_detection':
            # ZFC: Halogen-binding sites (Lewis acidic)
            has_lewis_acid = any(
                a['element'] in ('B', 'Al', 'Zr') or (a['partial_charge'] > 0.3)
                for a in atoms
            )

            zfc_says = has_lewis_acid
            zfc_score = 0.8 if zfc_says else 0.3

            # CAT: Aromatic framework for PFAS π-stacking
            has_aromatic = global_props['num_aromatic_rings'] > 0
            cat_says = has_aromatic
            cat_score = 0.75 if cat_says else 0.4

            trace = "PFAS detection: " + (
                "✓ Lewis acidic sites + aromatic framework" if (zfc_says and cat_says)
                else "✗ Missing Lewis acidic sites or aromatic rings"
            )

        else:  # custom or unknown
            # Generic activity: aromatic + functional groups
            has_aromatic = global_props['num_aromatic_rings'] > 0
            has_heteroatom = global_props['has_heteroatom']

            zfc_says = has_aromatic and has_heteroatom
            zfc_score = 0.7 if zfc_says else 0.4

            cat_says = has_aromatic
            cat_score = 0.7 if cat_says else 0.4

            trace = "Generic: " + (
                "✓ Aromatic + heteroatoms (versatile linker)" if zfc_says
                else "◇ Activity depends on specific application"
            )

        return (zfc_score, zfc_says, cat_says, trace)

    def _score_conductivity(self, descriptors: Dict) -> tuple:
        """Score electrical conductivity verdict.

        ZFC Rules:
        - Conjugated π-system length > 6
        - Aromatic content > 50%
        - Heteroatom doping (N, S)

        CAT Check:
        - Orbital overlap composes into extended state

        Returns:
            (score, zfc_says, cat_says, trace)
        """
        atoms = descriptors['atoms']
        bonds = descriptors['bonds']
        global_props = descriptors['global']

        # ZFC: Extended conjugation
        conjugation_length = global_props['conjugation_length']
        has_extended_conjugation = conjugation_length > 6

        # ZFC: Aromatic content
        aromatic_count = sum(1 for a in atoms if a['aromatic'])
        aromatic_fraction = aromatic_count / len(atoms) if atoms else 0
        high_aromatic_content = aromatic_fraction > 0.5

        # ZFC: Heteroatom doping
        has_heteroatom_doping = any(a['element'] in ('N', 'S') and a['aromatic'] for a in atoms)

        # ZFC verdict
        zfc_says = has_extended_conjugation and (high_aromatic_content or has_heteroatom_doping)
        zfc_score = 0.8 if zfc_says else 0.3

        # CAT: Check if conjugated bonds form continuous pathway
        conjugated_bonds = [b for b in bonds if b['conjugated']]
        continuous_pathway = len(conjugated_bonds) > 8  # Simplified check

        cat_says = continuous_pathway
        cat_score = 0.75 if cat_says else 0.4

        # Reasoning trace
        trace_parts = []
        if zfc_says:
            trace_parts.append(f"✓ Extended conjugation ({conjugation_length} bonds), {aromatic_fraction:.0%} aromatic")
        else:
            trace_parts.append(f"✗ Limited conjugation ({conjugation_length} bonds)")

        if has_heteroatom_doping:
            trace_parts.append("✓ Heteroatom doping (N/S)")

        if cat_says:
            trace_parts.append("✓ Continuous conjugated pathway")
        else:
            trace_parts.append("◇ Conjugation interrupted, conductivity limited")

        trace = "; ".join(trace_parts)

        return (zfc_score, zfc_says, cat_says, trace)

    def _compute_morphism_integrity(self, descriptors: Dict) -> float:
        """Compute morphism integrity (CAT layer).

        Checks if atomic descriptors compose consistently.
        For each bond: expected bond type from hybridization vs actual bond type.

        Returns:
            Integrity score (0-1), 1.0 = perfect consistency
        """
        atoms = descriptors['atoms']
        bonds = descriptors['bonds']

        if not bonds:
            return 1.0

        contradictions = 0

        for bond in bonds:
            atom_i = atoms[bond['atom_i']]
            atom_j = atoms[bond['atom_j']]

            # Expected bond type from hybridization
            hyb_i = atom_i['hybridization']
            hyb_j = atom_j['hybridization']
            actual_bond = bond['bond_type']

            # SP3-SP3: expect SINGLE
            # SP2-SP2: expect DOUBLE or AROMATIC
            # SP-SP: expect TRIPLE

            expected = None
            if 'SP3' in hyb_i and 'SP3' in hyb_j:
                expected = 'SINGLE'
            elif 'SP2' in hyb_i or 'SP2' in hyb_j:
                expected = ['DOUBLE', 'AROMATIC', 'SINGLE']  # SP2 can be single too
            elif 'SP' in hyb_i or 'SP' in hyb_j:
                expected = ['TRIPLE', 'DOUBLE']

            if expected:
                if isinstance(expected, list):
                    if actual_bond not in expected:
                        contradictions += 1
                elif actual_bond != expected:
                    contradictions += 1

        integrity = 1.0 - (contradictions / len(bonds))
        return max(0.0, min(1.0, integrity))

    def _classify_verdict(
        self,
        zfc_says: bool,
        cat_says: bool,
        morphism_integrity: float,
    ) -> tuple:
        """Classify verdict based on ZFC + CAT results.

        Args:
            zfc_says: ZFC layer says yes
            cat_says: CAT layer says yes
            morphism_integrity: CAT integrity score (0-1)

        Returns:
            (verdict_type, confidence_score)
        """
        # Adjust CAT based on morphism integrity
        cat_adjusted = cat_says and (morphism_integrity > 0.7)

        if zfc_says and cat_adjusted:
            return ('AGREE', morphism_integrity * 0.95)
        elif not zfc_says and cat_adjusted:
            return ('HOLLOW', morphism_integrity * 0.6)
        elif zfc_says and not cat_adjusted:
            return ('ORPHAN', 0.5)
        else:
            return ('REJECT', 0.2)


if __name__ == "__main__":
    # Demo usage
    print("Testing KOMPOSOS Verdict Engine...")

    test_smiles = "c1ccc(-c2ccc(-c3ccccc3)cc2)cc1"  # Triphenyl (simplified 22-atom)

    engine = LinkerVerdictEngine()

    try:
        result = engine.score_verdicts(test_smiles, "breath_VOC_sensing")

        print(f"\nSMILES: {test_smiles}")
        print(f"Morphism Integrity: {result.morphism_integrity:.3f}")
        print(f"ZFC Constraints Passed: {result.zfc_constraints_passed}/5")
        print(f"Overall Viable: {result.overall_viable}")

        print("\nVerdicts:")
        for verdict_name, verdict_type in result.verdicts.items():
            score = result.verdict_scores[verdict_name]
            trace = result.reasoning_traces[verdict_name]
            icon = {'AGREE': '✓', 'HOLLOW': '◇', 'ORPHAN': '○', 'REJECT': '✗'}[verdict_type]
            print(f"  {icon} {verdict_name.title()}: {verdict_type} (score: {score:.2f})")
            print(f"     {trace}")

    except ImportError as e:
        print(f"Error: {e}")
        print("Install RDKit: pip install rdkit")
