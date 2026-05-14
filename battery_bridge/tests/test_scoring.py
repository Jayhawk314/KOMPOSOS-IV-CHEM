"""
Tests for battery interaction scoring functions.

Verifies that each of the 5 scorers returns values in [0, 1]
and responds correctly to known good/bad material pairings.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from battery_bridge.material_properties import (
    get_material, CATHODE_MATERIALS, ANODE_MATERIALS,
    ELECTROLYTE_SOLVENTS, ELECTROLYTE_SALTS, SOLID_ELECTROLYTES,
)
from battery_bridge.interaction_scoring import (
    score_ion_transport,
    score_electrochemical_stability,
    score_interface_compatibility,
    score_mechanical_compatibility,
    score_degradation_penalty,
    score_all,
    ScorerResult,
)


class TestScorerRange(unittest.TestCase):
    """All scorers must return values in [0, 1]."""

    def _check_range(self, result: ScorerResult, label: str):
        self.assertGreaterEqual(result.score, 0.0, f"{label} score < 0")
        self.assertLessEqual(result.score, 1.0, f"{label} score > 1")

    def test_all_scorers_in_range(self):
        """Run every scorer on every material pair; all must be in [0, 1]."""
        # Pick a representative subset to keep test fast
        test_pairs = [
            ('LFP', 'EC'), ('NMC811', 'EC'), ('Graphite', 'EC'),
            ('Li_metal', 'LLZO'), ('LGPS', 'NMC811'), ('Si', 'DMC'),
            ('LFP', 'LiPF6'), ('LTO', 'LiTFSI'),
        ]
        for name_a, name_b in test_pairs:
            mat_a = get_material(name_a)
            mat_b = get_material(name_b)
            if mat_a is None or mat_b is None:
                continue

            self._check_range(score_ion_transport(mat_a, mat_b),
                              f"ion_transport({name_a},{name_b})")
            self._check_range(score_electrochemical_stability(mat_a, mat_b),
                              f"echem_stability({name_a},{name_b})")
            self._check_range(score_interface_compatibility(mat_a, mat_b),
                              f"interface_compat({name_a},{name_b})")
            self._check_range(score_mechanical_compatibility(mat_a, mat_b),
                              f"mech_compat({name_a},{name_b})")
            self._check_range(score_degradation_penalty(mat_a, mat_b),
                              f"degradation({name_a},{name_b})")


class TestIonTransport(unittest.TestCase):
    """Tests for ion transport scorer."""

    def test_solid_electrolyte_pair(self):
        """Two solid electrolytes with similar conductivity score well."""
        llzo = get_material('LLZO')
        li3ps4 = get_material('Li3PS4')
        result = score_ion_transport(llzo, li3ps4)
        self.assertGreater(result.score, 0.3)

    def test_molecular_solvent_good_transport(self):
        """Molecular solvents interface well with electrodes."""
        ec = get_material('EC')
        lfp = get_material('LFP')
        result = score_ion_transport(lfp, ec)
        self.assertGreater(result.score, 0.5)


class TestElectrochemicalStability(unittest.TestCase):
    """Tests for electrochemical stability scorer."""

    def test_lfp_ec_stable(self):
        """LFP at 3.4V is within EC's stability window (ox ~4.5V)."""
        lfp = get_material('LFP')
        ec = get_material('EC')
        result = score_electrochemical_stability(lfp, ec)
        self.assertGreater(result.score, 0.7,
                           "LFP + EC should be electrochemically stable")

    def test_lgps_nmc811_unstable(self):
        """LGPS decomposes at NMC811 voltage (3.8V >> 2.1V limit)."""
        nmc811 = get_material('NMC811')
        lgps = get_material('LGPS')
        result = score_electrochemical_stability(nmc811, lgps)
        self.assertLess(result.score, 0.5,
                        "LGPS + NMC811 should flag instability")

    def test_graphite_ec_sei_expected(self):
        """Graphite at 0.1V is below EC reduction potential -> SEI forms (expected)."""
        graphite = get_material('Graphite')
        ec = get_material('EC')
        result = score_electrochemical_stability(graphite, ec)
        # SEI formation is expected and manageable, shouldn't tank score
        self.assertGreater(result.score, 0.6,
                           "Graphite + EC: SEI is expected, should not fail hard")


class TestInterfaceCompatibility(unittest.TestCase):
    """Tests for interface compatibility scorer."""

    def test_graphite_ec_good_sei(self):
        """Graphite + EC forms excellent SEI (well-known good pairing)."""
        graphite = get_material('Graphite')
        ec = get_material('EC')
        result = score_interface_compatibility(graphite, ec)
        self.assertGreater(result.score, 0.8,
                           "Graphite + EC is the gold standard SEI interface")

    def test_li_metal_ec_poor_sei(self):
        """Li metal + liquid EC has unstable SEI (dendrites)."""
        li = get_material('Li_metal')
        ec = get_material('EC')
        result = score_interface_compatibility(li, ec)
        self.assertLess(result.score, 0.5,
                        "Li metal + EC should flag dendrite/SEI instability")

    def test_si_ec_poor_sei(self):
        """Si + EC: SEI cracks due to 300% expansion."""
        si = get_material('Si')
        ec = get_material('EC')
        result = score_interface_compatibility(si, ec)
        self.assertLess(result.score, 0.5,
                        "Si + EC: SEI instability from volume expansion")


class TestMechanicalCompatibility(unittest.TestCase):
    """Tests for mechanical compatibility scorer."""

    def test_si_extreme_expansion(self):
        """Si anode should tank mechanical score due to 300% expansion."""
        si = get_material('Si')
        ec = get_material('EC')
        result = score_mechanical_compatibility(si, ec)
        self.assertLess(result.score, 0.3,
                        "Si 300% expansion should severely penalize mechanical score")

    def test_lto_zero_strain(self):
        """LTO (zero-strain) should have good mechanical score."""
        lto = get_material('LTO')
        ec = get_material('EC')
        result = score_mechanical_compatibility(lto, ec)
        self.assertGreater(result.score, 0.7,
                           "LTO zero-strain should have good mechanical compatibility")

    def test_graphite_moderate_expansion(self):
        """Graphite has ~10% expansion -- moderate, manageable."""
        graphite = get_material('Graphite')
        ec = get_material('EC')
        result = score_mechanical_compatibility(graphite, ec)
        self.assertGreater(result.score, 0.4,
                           "Graphite 10% expansion should be moderate")


class TestDegradationPenalty(unittest.TestCase):
    """Tests for degradation penalty scorer."""

    def test_li_metal_ec_dendrite_penalty(self):
        """Li metal + EC should trigger dendrite penalty."""
        li = get_material('Li_metal')
        ec = get_material('EC')
        result = score_degradation_penalty(li, ec)
        self.assertLess(result.score, 0.5,
                        "Li metal + EC: known dendrite risk")
        self.assertTrue(any('dendrite' in r.lower() or 'Dendrite' in r
                           for r in result.details.get('reasons', [])),
                        "Should mention dendrite in reasons")

    def test_lgps_nmc811_decomposition_penalty(self):
        """LGPS + NMC811 should trigger decomposition penalty."""
        lgps = get_material('LGPS')
        nmc = get_material('NMC811')
        result = score_degradation_penalty(lgps, nmc)
        self.assertLess(result.score, 0.5,
                        "LGPS + NMC811: known decomposition")

    def test_lfp_ec_no_penalty(self):
        """LFP + EC is a known good pairing with no degradation penalty."""
        lfp = get_material('LFP')
        ec = get_material('EC')
        result = score_degradation_penalty(lfp, ec)
        self.assertGreater(result.score, 0.7,
                           "LFP + EC: no known degradation issues")


class TestScoreAll(unittest.TestCase):
    """Tests for the composite score_all function."""

    def test_returns_five_scores(self):
        """score_all returns exactly 5 results."""
        lfp = get_material('LFP')
        ec = get_material('EC')
        results = score_all(lfp, ec)
        self.assertEqual(len(results), 5)
        expected_keys = {
            'ion_transport', 'electrochemical_stability',
            'interface_compatibility', 'mechanical_compatibility',
            'degradation_penalty',
        }
        self.assertEqual(set(results.keys()), expected_keys)

    def test_all_results_are_scorer_results(self):
        """All values in score_all output are ScorerResult instances."""
        lfp = get_material('LFP')
        ec = get_material('EC')
        results = score_all(lfp, ec)
        for name, result in results.items():
            self.assertIsInstance(result, ScorerResult, name)


if __name__ == '__main__':
    unittest.main()
