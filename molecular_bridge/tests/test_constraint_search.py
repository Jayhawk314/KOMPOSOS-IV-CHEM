"""Tests for constraint-based molecular search."""

import unittest

from molecular_bridge.constraint_search import (
    search_by_constraints,
    count_heavy_atoms_from_formula,
    get_heavy_atom_count,
    get_atom_count_distribution,
)
from molecular_bridge.molecule_properties import (
    ALL_MOLECULES,
    MoleculeClass,
    get_molecule,
)


class TestHeavyAtomCounting(unittest.TestCase):
    """Test heavy atom counting from chemical formulas."""

    def test_ec_formula(self):
        """EC (C3H4O3) has 6 heavy atoms: 3C + 3O."""
        self.assertEqual(count_heavy_atoms_from_formula("C3H4O3"), 6)

    def test_lipf6(self):
        """LiPF6 has 8 heavy atoms: 1Li + 1P + 6F."""
        self.assertEqual(count_heavy_atoms_from_formula("LiPF6"), 8)

    def test_styrene(self):
        """Styrene (C8H8) has 8 heavy atoms."""
        self.assertEqual(count_heavy_atoms_from_formula("C8H8"), 8)

    def test_simple_water(self):
        """H2O has 1 heavy atom."""
        self.assertEqual(count_heavy_atoms_from_formula("H2O"), 1)

    def test_parenthesized_formula(self):
        """Al(NO3)3 has 1Al + 3N + 9O = 13 heavy atoms."""
        self.assertEqual(count_heavy_atoms_from_formula("Al(NO3)3"), 13)

    def test_co2(self):
        """CO2 has 3 heavy atoms."""
        self.assertEqual(count_heavy_atoms_from_formula("CO2"), 3)

    def test_no_hydrogen_all_heavy(self):
        """NaCl has 2 heavy atoms."""
        self.assertEqual(count_heavy_atoms_from_formula("NaCl"), 2)

    def test_get_heavy_atom_count_molecule(self):
        """get_heavy_atom_count works on Molecule objects."""
        ec = get_molecule("EC")
        self.assertIsNotNone(ec)
        self.assertEqual(get_heavy_atom_count(ec), 6)


class TestSearchExactAtomCount(unittest.TestCase):
    """Test exact heavy atom count searches."""

    def test_search_returns_only_matching_count(self):
        """All returned molecules must have the exact requested count."""
        for target_count in [3, 6, 8]:
            results = search_by_constraints(heavy_atom_count=target_count)
            for mol in results:
                actual = get_heavy_atom_count(mol)
                self.assertEqual(
                    actual, target_count,
                    f"{mol.name} has {actual} atoms, expected {target_count}",
                )

    def test_impossible_count_returns_empty(self):
        """Search for 1000 atoms returns empty list, not hallucination."""
        results = search_by_constraints(heavy_atom_count=1000)
        self.assertEqual(len(results), 0)

    def test_zero_returns_h2_only(self):
        """Zero heavy atoms should match only H2 (pure hydrogen)."""
        results = search_by_constraints(heavy_atom_count=0)
        names = {m.name for m in results}
        # H2 has formula 'H2' — 0 heavy atoms
        self.assertTrue(all(m.formula == "H2" for m in results))


class TestSearchRange(unittest.TestCase):
    """Test heavy atom range searches."""

    def test_range_inclusive(self):
        """Range (5, 10) includes both 5 and 10."""
        results = search_by_constraints(heavy_atom_range=(5, 10))
        for mol in results:
            count = get_heavy_atom_count(mol)
            self.assertGreaterEqual(count, 5)
            self.assertLessEqual(count, 10)

    def test_range_finds_most_molecules(self):
        """Range (0, 100) should find all 37 molecules (including H2 with 0)."""
        results = search_by_constraints(heavy_atom_range=(0, 100))
        self.assertEqual(len(results), len(ALL_MOLECULES))

    def test_narrow_range_subset(self):
        """Narrow range returns a subset."""
        all_results = search_by_constraints(heavy_atom_range=(1, 100))
        narrow = search_by_constraints(heavy_atom_range=(3, 5))
        self.assertLessEqual(len(narrow), len(all_results))


class TestSearchFunctionalGroups(unittest.TestCase):

    def test_carbonate_filter(self):
        """Searching for 'carbonate' should find EC, DMC, DEC, etc."""
        results = search_by_constraints(functional_groups=["carbonate"])
        names = {m.name for m in results}
        self.assertIn("EC", names)
        self.assertIn("DMC", names)

    def test_combined_functional_groups(self):
        """Multiple groups use AND logic."""
        results = search_by_constraints(
            functional_groups=["carbonate", "cyclic_ester"]
        )
        for mol in results:
            self.assertIn("carbonate", mol.functional_groups)
            self.assertIn("cyclic_ester", mol.functional_groups)


class TestSearchExcludeElements(unittest.TestCase):

    def test_exclude_fluorine(self):
        """Excluding F should remove LiPF6, FEC, etc. but keep FeSO4."""
        from molecular_bridge.constraint_search import _get_elements_in_formula
        results = search_by_constraints(exclude_elements=["F"])
        for mol in results:
            elements = _get_elements_in_formula(mol.formula)
            self.assertNotIn("F", elements,
                             f"{mol.name} ({mol.formula}) should not contain element F")
        # FeSO4 should still be present (Fe != F)
        names = {m.name for m in results}
        self.assertIn("FeSO4", names)

    def test_exclude_nonexistent_element(self):
        """Excluding an element not in any molecule changes nothing."""
        all_mols = search_by_constraints()
        filtered = search_by_constraints(exclude_elements=["Xe"])
        self.assertEqual(len(all_mols), len(filtered))


class TestSearchIncludeElements(unittest.TestCase):

    def test_include_lithium(self):
        """Require Li — should find LiPF6, LiOH, Li2CO3, etc."""
        results = search_by_constraints(include_elements=["Li"])
        for mol in results:
            self.assertIn("Li", mol.formula,
                          f"{mol.name} ({mol.formula}) should contain Li")
        self.assertGreater(len(results), 0)


class TestSearchMoleculeClass(unittest.TestCase):

    def test_filter_by_electrolyte_solvent(self):
        """Filter by ELECTROLYTE_SOLVENT class."""
        results = search_by_constraints(molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT)
        for mol in results:
            self.assertEqual(mol.molecule_class, MoleculeClass.ELECTROLYTE_SOLVENT)

    def test_filter_by_salt_anion(self):
        results = search_by_constraints(molecule_class=MoleculeClass.SALT_ANION)
        names = {m.name for m in results}
        self.assertIn("LiPF6", names)


class TestSearchMolecularWeight(unittest.TestCase):

    def test_mw_range(self):
        """Filter by MW range."""
        results = search_by_constraints(molecular_weight_range=(50.0, 100.0))
        for mol in results:
            self.assertGreaterEqual(mol.molecular_weight, 50.0)
            self.assertLessEqual(mol.molecular_weight, 100.0)


class TestCombinedConstraints(unittest.TestCase):

    def test_combined_class_and_atom_range(self):
        """Combined constraints use AND logic."""
        results = search_by_constraints(
            molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT,
            heavy_atom_range=(5, 8),
        )
        for mol in results:
            self.assertEqual(mol.molecule_class, MoleculeClass.ELECTROLYTE_SOLVENT)
            count = get_heavy_atom_count(mol)
            self.assertGreaterEqual(count, 5)
            self.assertLessEqual(count, 8)

    def test_impossible_combination_empty(self):
        """Conflicting constraints return empty list."""
        results = search_by_constraints(
            heavy_atom_count=3,
            molecular_weight_range=(500.0, 1000.0),
        )
        self.assertEqual(len(results), 0)


class TestAtomCountDistribution(unittest.TestCase):

    def test_distribution_covers_all_molecules(self):
        """Distribution should account for all 37 molecules."""
        dist = get_atom_count_distribution()
        total = sum(len(names) for names in dist.values())
        self.assertEqual(total, len(ALL_MOLECULES))


class TestKulik22AtomChallenge(unittest.TestCase):
    """The famous Kulik challenge: find a ligand with exactly 22 atoms."""

    def test_22_atoms_returns_only_22(self):
        """If any results, they must have exactly 22 heavy atoms."""
        results = search_by_constraints(heavy_atom_count=22)
        for mol in results:
            self.assertEqual(get_heavy_atom_count(mol), 22)

    def test_never_hallucinates(self):
        """Result is either correct matches or empty — never wrong count."""
        for count in [1, 5, 10, 15, 20, 22, 25, 30, 50, 100]:
            results = search_by_constraints(heavy_atom_count=count)
            for mol in results:
                self.assertEqual(
                    get_heavy_atom_count(mol), count,
                    f"Hallucination: {mol.name} has {get_heavy_atom_count(mol)} "
                    f"atoms, claimed {count}",
                )


if __name__ == "__main__":
    unittest.main()
