"""Tests for MOF material properties database."""

import unittest

from mof_bridge.material_properties import (
    ALL_MOFS,
    MOF,
    MOFTopology,
    MOFApplication,
    get_mof,
    get_mofs_by_topology,
    get_mofs_by_application,
    list_water_stable_mofs,
    KNOWN_GOOD_APPLICATIONS,
    KNOWN_BAD_APPLICATIONS,
)


class TestMOFDatabase(unittest.TestCase):
    """Test the MOF database completeness and data quality."""

    def test_database_has_30_mofs(self):
        self.assertEqual(len(ALL_MOFS), 30)

    def test_all_mofs_are_mof_objects(self):
        for name, mof in ALL_MOFS.items():
            self.assertIsInstance(mof, MOF, f"{name} is not a MOF")

    def test_all_mofs_have_positive_bet(self):
        for name, mof in ALL_MOFS.items():
            self.assertGreater(
                mof.bet_surface_area_m2g, 0,
                f"{name} has non-positive BET surface area",
            )

    def test_all_mofs_have_positive_pore_volume(self):
        for name, mof in ALL_MOFS.items():
            self.assertGreater(
                mof.pore_volume_cm3g, 0,
                f"{name} has non-positive pore volume",
            )

    def test_all_mofs_have_positive_pore_diameter(self):
        for name, mof in ALL_MOFS.items():
            self.assertGreater(
                mof.pore_diameter_angstrom, 0,
                f"{name} has non-positive pore diameter",
            )

    def test_all_mofs_have_thermal_stability(self):
        for name, mof in ALL_MOFS.items():
            self.assertGreater(
                mof.thermal_stability_C, 0,
                f"{name} has non-positive thermal stability",
            )

    def test_all_mofs_have_doi(self):
        for name, mof in ALL_MOFS.items():
            self.assertTrue(
                len(mof.doi) > 0,
                f"{name} is missing DOI reference",
            )

    def test_all_mofs_have_valid_topology(self):
        for name, mof in ALL_MOFS.items():
            self.assertIsInstance(mof.topology, MOFTopology)

    def test_all_mofs_have_valid_application(self):
        for name, mof in ALL_MOFS.items():
            self.assertIsInstance(mof.primary_application, MOFApplication)

    def test_water_stability_values(self):
        valid = {'excellent', 'good', 'moderate', 'poor'}
        for name, mof in ALL_MOFS.items():
            self.assertIn(
                mof.water_stability, valid,
                f"{name} has invalid water_stability: {mof.water_stability}",
            )

    def test_all_mofs_have_sources(self):
        for name, mof in ALL_MOFS.items():
            self.assertGreater(
                len(mof.sources), 0,
                f"{name} has no source citations",
            )


class TestMOFLookups(unittest.TestCase):
    """Test convenience lookup functions."""

    def test_get_mof_exists(self):
        mof = get_mof('ZIF-8')
        self.assertIsNotNone(mof)
        self.assertEqual(mof.name, 'ZIF-8')

    def test_get_mof_nonexistent(self):
        mof = get_mof('NONEXISTENT-999')
        self.assertIsNone(mof)

    def test_get_mofs_by_topology(self):
        sod = get_mofs_by_topology(MOFTopology.SOD)
        self.assertIn('ZIF-8', sod)
        self.assertIn('ZIF-67', sod)
        for name, mof in sod.items():
            self.assertEqual(mof.topology, MOFTopology.SOD)

    def test_get_mofs_by_application(self):
        gas = get_mofs_by_application(MOFApplication.GAS_STORAGE)
        self.assertIn('MOF-5', gas)
        for name, mof in gas.items():
            self.assertEqual(mof.primary_application, MOFApplication.GAS_STORAGE)

    def test_water_stable_mofs(self):
        stable = list_water_stable_mofs()
        self.assertGreater(len(stable), 0)
        for name in stable:
            mof = get_mof(name)
            self.assertEqual(mof.water_stability, 'excellent')

    def test_to_dict(self):
        mof = get_mof('UiO-66')
        d = mof.to_dict()
        self.assertEqual(d['name'], 'UiO-66')
        self.assertIn('bet_surface_area_m2g', d)
        self.assertIn('topology', d)


class TestKnownPairings(unittest.TestCase):
    """Test known good/bad application pairings data."""

    def test_good_applications_exist(self):
        for entry in KNOWN_GOOD_APPLICATIONS:
            mof = get_mof(entry['mof'])
            self.assertIsNotNone(mof, f"MOF {entry['mof']} not in database")

    def test_bad_applications_exist(self):
        for entry in KNOWN_BAD_APPLICATIONS:
            mof = get_mof(entry['mof'])
            self.assertIsNotNone(mof, f"MOF {entry['mof']} not in database")

    def test_bad_applications_have_poor_water_stability(self):
        for entry in KNOWN_BAD_APPLICATIONS:
            if entry['expected_problem'] == 'water_stability':
                mof = get_mof(entry['mof'])
                self.assertIn(
                    mof.water_stability, ('poor', 'moderate'),
                    f"{entry['mof']} should have poor/moderate water stability",
                )


class TestSpecificMOFs(unittest.TestCase):
    """Spot-check specific well-known MOF values."""

    def test_zif8_properties(self):
        mof = get_mof('ZIF-8')
        self.assertEqual(mof.metal_node, 'Zn')
        self.assertEqual(mof.topology, MOFTopology.SOD)
        self.assertAlmostEqual(mof.pore_diameter_angstrom, 3.4)
        self.assertEqual(mof.water_stability, 'excellent')
        self.assertGreaterEqual(mof.thermal_stability_C, 500)

    def test_uio66_properties(self):
        mof = get_mof('UiO-66')
        self.assertIn('Zr', mof.metal_node)
        self.assertEqual(mof.topology, MOFTopology.FCU)
        self.assertEqual(mof.water_stability, 'excellent')
        self.assertGreaterEqual(mof.thermal_stability_C, 450)

    def test_mof5_properties(self):
        mof = get_mof('MOF-5')
        self.assertIn('Zn', mof.metal_node)
        self.assertEqual(mof.topology, MOFTopology.PCU)
        self.assertEqual(mof.water_stability, 'poor')
        self.assertGreaterEqual(mof.bet_surface_area_m2g, 3000)

    def test_mil101_high_bet(self):
        mof = get_mof('MIL-101(Cr)')
        self.assertGreaterEqual(mof.bet_surface_area_m2g, 4000)
        self.assertEqual(mof.water_stability, 'excellent')

    def test_dut49_highest_pore_volume(self):
        mof = get_mof('DUT-49')
        self.assertGreaterEqual(mof.pore_volume_cm3g, 2.5)

    def test_cof300_is_organic(self):
        mof = get_mof('COF-300')
        self.assertEqual(mof.metal_node, 'None (organic)')
        self.assertTrue(mof.metadata.get('is_cof', False))


if __name__ == '__main__':
    unittest.main()
