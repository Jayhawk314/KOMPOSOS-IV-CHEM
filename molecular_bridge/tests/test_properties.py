# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for molecular property tables.

Verifies that all molecule entries have valid, self-consistent data.
Follows the pattern of battery_bridge/tests/test_properties.py.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from molecular_bridge.molecule_properties import (
    ALL_MOLECULES,
    ELECTROLYTE_SOLVENTS,
    SALT_ANIONS,
    POLYMER_MONOMERS,
    REAGENTS,
    COATINGS,
    GAS_MOLECULES,
    MoleculeClass,
    Molecule,
    get_molecule,
    get_molecules_by_class,
    list_molecule_names,
)


class TestMoleculeProperties(unittest.TestCase):
    """Test molecule property tables for completeness and validity."""

    def test_all_molecules_populated(self):
        """At least 30 molecules defined."""
        self.assertGreaterEqual(len(ALL_MOLECULES), 30)

    def test_total_count(self):
        """Exactly 37 molecules in the database."""
        self.assertEqual(len(ALL_MOLECULES), 37)

    def test_electrolyte_solvents_exist(self):
        """Core electrolyte solvents are present."""
        self.assertIn('EC', ELECTROLYTE_SOLVENTS)
        self.assertIn('DMC', ELECTROLYTE_SOLVENTS)
        self.assertIn('DEC', ELECTROLYTE_SOLVENTS)
        self.assertIn('EMC', ELECTROLYTE_SOLVENTS)
        self.assertIn('PC', ELECTROLYTE_SOLVENTS)
        self.assertIn('FEC', ELECTROLYTE_SOLVENTS)
        self.assertIn('VC', ELECTROLYTE_SOLVENTS)
        self.assertEqual(len(ELECTROLYTE_SOLVENTS), 7)

    def test_salt_anions_exist(self):
        """Core salt anions are present."""
        self.assertIn('LiPF6', SALT_ANIONS)
        self.assertIn('LiTFSI', SALT_ANIONS)
        self.assertIn('LiBF4', SALT_ANIONS)
        self.assertIn('LiClO4', SALT_ANIONS)
        self.assertEqual(len(SALT_ANIONS), 4)

    def test_polymer_monomers_exist(self):
        """Core polymer monomers are present."""
        self.assertIn('ethylene_oxide', POLYMER_MONOMERS)
        self.assertIn('vinylidene_fluoride', POLYMER_MONOMERS)
        self.assertIn('acrylonitrile', POLYMER_MONOMERS)
        self.assertIn('styrene', POLYMER_MONOMERS)
        self.assertIn('methyl_methacrylate', POLYMER_MONOMERS)
        self.assertEqual(len(POLYMER_MONOMERS), 5)

    def test_reagents_exist(self):
        """Core reagents are present."""
        self.assertIn('LiOH', REAGENTS)
        self.assertIn('H3PO4', REAGENTS)
        self.assertIn('FeSO4', REAGENTS)
        self.assertIn('Li2CO3', REAGENTS)
        self.assertEqual(len(REAGENTS), 10)

    def test_coatings_exist(self):
        """Coating molecules are present."""
        self.assertIn('Al_isopropoxide', COATINGS)
        self.assertIn('Ti_isopropoxide', COATINGS)
        self.assertIn('citric_acid', COATINGS)
        self.assertIn('oxalic_acid', COATINGS)
        self.assertEqual(len(COATINGS), 5)

    def test_gas_molecules_exist(self):
        """Gas molecules are present."""
        self.assertIn('O2', GAS_MOLECULES)
        self.assertIn('N2', GAS_MOLECULES)
        self.assertIn('Ar', GAS_MOLECULES)
        self.assertIn('CO2', GAS_MOLECULES)
        self.assertIn('H2O', GAS_MOLECULES)
        self.assertIn('H2', GAS_MOLECULES)
        self.assertEqual(len(GAS_MOLECULES), 6)


class TestMoleculeDataIntegrity(unittest.TestCase):
    """Verify data integrity for every molecule."""

    def test_all_have_required_fields(self):
        """Every molecule has name, formula, CID, CAS, SMILES, MW."""
        for name, mol in ALL_MOLECULES.items():
            self.assertTrue(mol.name, f"{name} missing name")
            self.assertTrue(mol.formula, f"{name} missing formula")
            self.assertIsInstance(mol.pubchem_cid, int, f"{name} CID not int")
            self.assertGreater(mol.pubchem_cid, 0, f"{name} CID <= 0")
            self.assertTrue(mol.cas_number, f"{name} missing CAS")
            self.assertTrue(mol.smiles, f"{name} missing SMILES")
            self.assertGreater(mol.molecular_weight, 0, f"{name} MW <= 0")

    def test_all_have_molecule_class(self):
        """Every molecule has a valid MoleculeClass."""
        for name, mol in ALL_MOLECULES.items():
            self.assertIsInstance(mol.molecule_class, MoleculeClass,
                                 f"{name} has invalid molecule_class")
            self.assertNotEqual(mol.molecule_class, MoleculeClass.OTHER,
                                f"{name} has class OTHER (should be specific)")

    def test_molecular_weight_reasonable(self):
        """Molecular weights are in reasonable range (2-500 g/mol)."""
        for name, mol in ALL_MOLECULES.items():
            self.assertGreater(mol.molecular_weight, 1.0,
                               f"{name} MW too low: {mol.molecular_weight}")
            self.assertLess(mol.molecular_weight, 500.0,
                            f"{name} MW too high: {mol.molecular_weight}")

    def test_boiling_above_melting(self):
        """Where both are available, bp > mp (except subliming species like CO2)."""
        # CO2 sublimes at 1 atm: bp=-78.5 C (sublimation), mp=-56.6 C (at 5.18 atm)
        sublimes = {'CO2'}
        for name, mol in ALL_MOLECULES.items():
            if name in sublimes:
                continue
            if mol.boiling_point_C is not None and mol.melting_point_C is not None:
                self.assertGreater(mol.boiling_point_C, mol.melting_point_C,
                                   f"{name}: bp ({mol.boiling_point_C}) <= mp ({mol.melting_point_C})")

    def test_density_positive(self):
        """Where density is given, it must be positive."""
        for name, mol in ALL_MOLECULES.items():
            if mol.density_g_cm3 is not None:
                self.assertGreater(mol.density_g_cm3, 0,
                                   f"{name} has non-positive density")

    def test_hbond_counts_non_negative(self):
        """H-bond donor/acceptor counts must be >= 0."""
        for name, mol in ALL_MOLECULES.items():
            self.assertGreaterEqual(mol.hbond_donors, 0, f"{name} HBD < 0")
            self.assertGreaterEqual(mol.hbond_acceptors, 0, f"{name} HBA < 0")

    def test_all_have_sources(self):
        """Every molecule should have at least one source citation."""
        for name, mol in ALL_MOLECULES.items():
            self.assertGreater(len(mol.sources), 0,
                               f"{name} has no source citations")

    def test_pubchem_cids_unique(self):
        """All PubChem CIDs should be unique."""
        cids = [mol.pubchem_cid for mol in ALL_MOLECULES.values()]
        self.assertEqual(len(cids), len(set(cids)),
                         f"Duplicate CIDs found: {[c for c in cids if cids.count(c) > 1]}")

    def test_cas_numbers_unique(self):
        """All CAS numbers should be unique."""
        cas = [mol.cas_number for mol in ALL_MOLECULES.values()]
        self.assertEqual(len(cas), len(set(cas)),
                         f"Duplicate CAS numbers found")

    def test_ionization_energy_reasonable(self):
        """IE values should be in 5-20 eV (typical for small molecules)."""
        for name, mol in ALL_MOLECULES.items():
            if mol.ionization_energy_eV is not None:
                self.assertGreater(mol.ionization_energy_eV, 5.0,
                                   f"{name} IE too low: {mol.ionization_energy_eV}")
                self.assertLess(mol.ionization_energy_eV, 20.0,
                                f"{name} IE too high: {mol.ionization_energy_eV}")


class TestConvenienceFunctions(unittest.TestCase):
    """Test lookup and convenience functions."""

    def test_get_molecule_valid(self):
        """get_molecule returns Molecule for known names."""
        mol = get_molecule('EC')
        self.assertIsNotNone(mol)
        self.assertEqual(mol.name, 'EC')
        self.assertEqual(mol.formula, 'C3H4O3')

    def test_get_molecule_invalid(self):
        """get_molecule returns None for unknown names."""
        mol = get_molecule('NOT_A_MOLECULE_XYZ')
        self.assertIsNone(mol)

    def test_get_molecules_by_class(self):
        """get_molecules_by_class returns correct subset."""
        solvents = get_molecules_by_class(MoleculeClass.ELECTROLYTE_SOLVENT)
        self.assertEqual(len(solvents), 7)
        self.assertIn('EC', solvents)
        self.assertIn('DMC', solvents)

    def test_list_molecule_names(self):
        """list_molecule_names returns sorted list."""
        names = list_molecule_names()
        self.assertEqual(len(names), 37)
        self.assertEqual(names, sorted(names))

    def test_to_dict_roundtrip(self):
        """Molecule.to_dict() produces a valid dict."""
        mol = get_molecule('EC')
        d = mol.to_dict()
        self.assertEqual(d['name'], 'EC')
        self.assertEqual(d['formula'], 'C3H4O3')
        self.assertEqual(d['pubchem_cid'], 7303)
        self.assertIsInstance(d['molecular_weight'], float)
        self.assertIn('molecule_class', d)

    def test_to_dict_optional_fields(self):
        """to_dict includes non-None optional float fields."""
        mol = get_molecule('EC')
        d = mol.to_dict()
        self.assertIn('boiling_point_C', d)
        self.assertIn('density_g_cm3', d)
        self.assertIn('dipole_moment_debye', d)

    def test_to_dict_skips_none(self):
        """to_dict omits None optional float fields."""
        mol = get_molecule('LiPF6')
        d = mol.to_dict()
        # LiPF6 has no boiling point (decomposes)
        self.assertNotIn('boiling_point_C', d)


class TestSpecificMoleculeData(unittest.TestCase):
    """Spot-check published values for key molecules."""

    def test_ec_molecular_weight(self):
        """EC MW should be ~88 g/mol."""
        mol = get_molecule('EC')
        self.assertAlmostEqual(mol.molecular_weight, 88.06, places=1)

    def test_ec_boiling_point(self):
        """EC bp ~248 C (PubChem)."""
        mol = get_molecule('EC')
        self.assertAlmostEqual(mol.boiling_point_C, 248.0, delta=5)

    def test_ec_dipole_moment(self):
        """EC dipole ~4.87 D (Xu 2004)."""
        mol = get_molecule('EC')
        self.assertAlmostEqual(mol.dipole_moment_debye, 4.87, delta=0.5)

    def test_lipf6_is_not_oxidizer(self):
        """LiPF6 is not classified as oxidizer."""
        mol = get_molecule('LiPF6')
        self.assertFalse(mol.is_oxidizing)

    def test_liclo4_is_oxidizer(self):
        """LiClO4 (perchlorate) IS classified as oxidizer."""
        mol = get_molecule('LiClO4')
        self.assertTrue(mol.is_oxidizing)

    def test_h2_is_reducing(self):
        """H2 is a reducing agent."""
        mol = get_molecule('H2')
        self.assertTrue(mol.is_reducing)
        self.assertFalse(mol.is_oxidizing)

    def test_o2_is_oxidizing(self):
        """O2 is an oxidizing agent."""
        mol = get_molecule('O2')
        self.assertTrue(mol.is_oxidizing)
        self.assertFalse(mol.is_reducing)

    def test_water_dipole(self):
        """H2O dipole should be ~1.85 D."""
        mol = get_molecule('H2O')
        self.assertAlmostEqual(mol.dipole_moment_debye, 1.85, delta=0.1)

    def test_h2_redox_potential(self):
        """H2 standard reduction potential is 0.0 V by definition."""
        mol = get_molecule('H2')
        self.assertAlmostEqual(mol.redox_potential_V, 0.0, places=2)

    def test_o2_redox_potential(self):
        """O2/H2O standard reduction potential is +1.23 V."""
        mol = get_molecule('O2')
        self.assertAlmostEqual(mol.redox_potential_V, 1.23, delta=0.1)


if __name__ == '__main__':
    unittest.main()
