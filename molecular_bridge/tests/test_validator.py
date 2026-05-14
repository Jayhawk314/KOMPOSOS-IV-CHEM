"""
Tests for molecular interface validator.

Verifies that the MolecularInterfaceValidator correctly combines
all five scorers into a weighted composite score with viability check.
Follows the pattern of battery_bridge/tests/test_interface.py.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from molecular_bridge.molecule_properties import (
    get_molecule, ALL_MOLECULES, Molecule, MoleculeClass,
)
from molecular_bridge.interface_validator import (
    MolecularInterfaceValidator,
    MolecularInterfaceScore,
    MolecularWeights,
    validate_interface,
)


class TestMolecularWeights(unittest.TestCase):
    """Test weight configuration."""

    def test_default_weights_sum_to_one(self):
        """Default weights must sum to 1.0."""
        w = MolecularWeights.default()
        total = (w.electronic_compatibility + w.thermodynamic_stability +
                 w.steric_compatibility + w.solubility_compatibility +
                 w.reactivity_risk)
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_safety_focus_weights_sum_to_one(self):
        """Safety-focus weights must sum to 1.0."""
        w = MolecularWeights.safety_focus()
        total = (w.electronic_compatibility + w.thermodynamic_stability +
                 w.steric_compatibility + w.solubility_compatibility +
                 w.reactivity_risk)
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_solubility_focus_weights_sum_to_one(self):
        """Solubility-focus weights must sum to 1.0."""
        w = MolecularWeights.solubility_focus()
        total = (w.electronic_compatibility + w.thermodynamic_stability +
                 w.steric_compatibility + w.solubility_compatibility +
                 w.reactivity_risk)
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_safety_focus_emphasizes_reactivity(self):
        """Safety focus should weight reactivity highest."""
        w = MolecularWeights.safety_focus()
        self.assertEqual(
            max(w.electronic_compatibility, w.thermodynamic_stability,
                w.steric_compatibility, w.solubility_compatibility,
                w.reactivity_risk),
            w.reactivity_risk)

    def test_invalid_weights_rejected(self):
        """Weights not summing to 1.0 should raise ValueError."""
        w = MolecularWeights(
            electronic_compatibility=0.5,
            thermodynamic_stability=0.5,
            steric_compatibility=0.5,
            solubility_compatibility=0.5,
            reactivity_risk=0.5,
        )
        with self.assertRaises(ValueError):
            w.validate()


class TestValidatorBasic(unittest.TestCase):
    """Basic validator functionality."""

    def setUp(self):
        self.validator = MolecularInterfaceValidator()

    def test_validate_by_name(self):
        """Validate by molecule name returns MolecularInterfaceScore."""
        result = self.validator.validate('EC', 'DMC')
        self.assertIsInstance(result, MolecularInterfaceScore)
        self.assertGreaterEqual(result.total, 0.0)
        self.assertLessEqual(result.total, 1.0)

    def test_validate_unknown_molecule_raises(self):
        """Unknown molecule name raises ValueError."""
        with self.assertRaises(ValueError):
            self.validator.validate('NOT_A_MOLECULE', 'EC')
        with self.assertRaises(ValueError):
            self.validator.validate('EC', 'NOT_A_MOLECULE')

    def test_validate_returns_all_components(self):
        """Result has all five component scores."""
        result = self.validator.validate('EC', 'DMC')
        self.assertGreaterEqual(result.electronic_compatibility, 0.0)
        self.assertLessEqual(result.electronic_compatibility, 1.0)
        self.assertGreaterEqual(result.thermodynamic_stability, 0.0)
        self.assertLessEqual(result.thermodynamic_stability, 1.0)
        self.assertGreaterEqual(result.steric_compatibility, 0.0)
        self.assertLessEqual(result.steric_compatibility, 1.0)
        self.assertGreaterEqual(result.solubility_compatibility, 0.0)
        self.assertLessEqual(result.solubility_compatibility, 1.0)
        self.assertGreaterEqual(result.reactivity_risk, 0.0)
        self.assertLessEqual(result.reactivity_risk, 1.0)

    def test_total_is_weighted_sum(self):
        """Total score should be the weighted sum of components."""
        result = self.validator.validate('EC', 'DMC')
        w = self.validator.weights
        expected = (
            w.electronic_compatibility * result.electronic_compatibility +
            w.thermodynamic_stability * result.thermodynamic_stability +
            w.steric_compatibility * result.steric_compatibility +
            w.solubility_compatibility * result.solubility_compatibility +
            w.reactivity_risk * result.reactivity_risk
        )
        self.assertAlmostEqual(result.total, expected, places=4)

    def test_viable_flag_matches_threshold(self):
        """Viable flag should match total >= threshold."""
        validator = MolecularInterfaceValidator(viability_threshold=0.50)
        result = validator.validate('EC', 'DMC')
        self.assertEqual(result.viable, result.total >= 0.50)

    def test_custom_threshold(self):
        """Very high threshold should make most pairs non-viable."""
        validator = MolecularInterfaceValidator(viability_threshold=0.99)
        result = validator.validate('EC', 'DMC')
        # Very hard to reach 0.99, should be non-viable
        self.assertFalse(result.viable)

    def test_zero_threshold(self):
        """Zero threshold should make all pairs viable."""
        validator = MolecularInterfaceValidator(viability_threshold=0.0)
        result = validator.validate('O2', 'H2')  # Even dangerous pair
        self.assertTrue(result.viable)


class TestValidateMoleculeObjects(unittest.TestCase):
    """Test validate_molecules with Molecule objects directly."""

    def test_validate_molecules_direct(self):
        """validate_molecules works with Molecule objects."""
        validator = MolecularInterfaceValidator()
        ec = get_molecule('EC')
        dmc = get_molecule('DMC')
        result = validator.validate_molecules(ec, dmc)
        self.assertIsInstance(result, MolecularInterfaceScore)

    def test_same_molecule(self):
        """Same molecule should still produce valid scores."""
        validator = MolecularInterfaceValidator()
        ec = get_molecule('EC')
        result = validator.validate_molecules(ec, ec)
        self.assertGreaterEqual(result.total, 0.0)
        self.assertLessEqual(result.total, 1.0)


class TestValidateAllInterfaces(unittest.TestCase):
    """Test batch pairwise validation."""

    def test_validate_all_three_molecules(self):
        """Three molecules produce 3 pairwise results."""
        validator = MolecularInterfaceValidator()
        results = validator.validate_all_interfaces(['EC', 'DMC', 'DEC'])
        self.assertEqual(len(results), 3)
        for (a, b), score in results.items():
            self.assertIsInstance(score, MolecularInterfaceScore)

    def test_validate_all_skips_unknown(self):
        """Unknown molecules are silently skipped."""
        validator = MolecularInterfaceValidator()
        results = validator.validate_all_interfaces(['EC', 'NOT_REAL', 'DMC'])
        # Only EC-DMC should work
        self.assertEqual(len(results), 1)

    def test_validate_all_solvents(self):
        """All 7 solvents produce 21 pairwise results."""
        validator = MolecularInterfaceValidator()
        solvents = ['EC', 'DMC', 'DEC', 'EMC', 'PC', 'FEC', 'VC']
        results = validator.validate_all_interfaces(solvents)
        expected = 7 * 6 // 2  # C(7,2) = 21
        self.assertEqual(len(results), expected)


class TestConvenienceFunction(unittest.TestCase):
    """Test the validate_interface convenience function."""

    def test_convenience_function(self):
        """validate_interface() returns same type as validator."""
        result = validate_interface('EC', 'DMC')
        self.assertIsInstance(result, MolecularInterfaceScore)
        self.assertIsInstance(result.viable, bool)

    def test_convenience_function_raises_on_unknown(self):
        """validate_interface() raises ValueError for unknown molecule."""
        with self.assertRaises(ValueError):
            validate_interface('FAKE', 'DMC')


class TestToDict(unittest.TestCase):
    """Test serialization."""

    def test_to_dict_keys(self):
        """to_dict has all expected keys."""
        result = validate_interface('EC', 'DMC')
        d = result.to_dict()
        expected_keys = {
            'total', 'electronic_compatibility', 'thermodynamic_stability',
            'steric_compatibility', 'solubility_compatibility',
            'reactivity_risk', 'viable',
        }
        self.assertEqual(set(d.keys()), expected_keys)

    def test_to_dict_values_rounded(self):
        """Scores in to_dict should be rounded to 4 decimal places."""
        result = validate_interface('EC', 'DMC')
        d = result.to_dict()
        for key in ('total', 'electronic_compatibility', 'thermodynamic_stability',
                     'steric_compatibility', 'solubility_compatibility', 'reactivity_risk'):
            val = d[key]
            # Check it's a float with at most 4 decimal places
            self.assertEqual(val, round(val, 4), f"{key} not rounded to 4 dp")


class TestDetails(unittest.TestCase):
    """Test that details are populated."""

    def test_details_has_molecule_names(self):
        """Details should contain molecule_a and molecule_b."""
        validator = MolecularInterfaceValidator()
        result = validator.validate('EC', 'DMC')
        self.assertEqual(result.details['molecule_a'], 'EC')
        self.assertEqual(result.details['molecule_b'], 'DMC')

    def test_details_has_sub_details(self):
        """Details should contain sub-details for each scorer."""
        validator = MolecularInterfaceValidator()
        result = validator.validate('EC', 'DMC')
        self.assertIn('electronic_details', result.details)
        self.assertIn('thermodynamic_details', result.details)
        self.assertIn('steric_details', result.details)
        self.assertIn('solubility_details', result.details)
        self.assertIn('reactivity_details', result.details)


class TestWeightPresets(unittest.TestCase):
    """Test that weight presets affect scoring as expected."""

    def test_safety_focus_lowers_dangerous_score(self):
        """Safety focus should lower total for dangerous pairs more than default."""
        default_v = MolecularInterfaceValidator()
        safety_v = MolecularInterfaceValidator(weights=MolecularWeights.safety_focus())

        # O2+H2 is dangerous -- reactivity score is low
        default_r = default_v.validate('O2', 'H2')
        safety_r = safety_v.validate('O2', 'H2')

        # Safety focus weights reactivity at 0.45 vs default 0.25
        # So when reactivity is bad, safety focus should give lower total
        self.assertLessEqual(safety_r.total, default_r.total + 0.01,
                             "Safety focus should penalize dangerous pairs more")

    def test_solubility_focus_emphasizes_solubility(self):
        """Solubility focus weights should give solubility 0.35."""
        w = MolecularWeights.solubility_focus()
        self.assertEqual(w.solubility_compatibility, 0.35)


class TestExhaustivePairwise(unittest.TestCase):
    """Run validator on all molecule pairs to ensure no crashes."""

    def test_all_pairs_complete(self):
        """Every pair in the database validates without error."""
        validator = MolecularInterfaceValidator()
        names = list(ALL_MOLECULES.keys())
        for i, name_a in enumerate(names):
            for name_b in names[i + 1:]:
                try:
                    result = validator.validate(name_a, name_b)
                    self.assertIsInstance(result, MolecularInterfaceScore)
                    self.assertGreaterEqual(result.total, 0.0)
                    self.assertLessEqual(result.total, 1.0)
                except Exception as e:
                    self.fail(f"Validation failed for {name_a}-{name_b}: {e}")


if __name__ == '__main__':
    unittest.main()
