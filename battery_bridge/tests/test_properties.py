# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for battery material property tables.

Verifies that all material entries have valid, self-consistent data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from battery_bridge.material_properties import (
    ALL_MATERIALS,
    CATHODE_MATERIALS,
    ANODE_MATERIALS,
    ELECTROLYTE_SOLVENTS,
    ELECTROLYTE_SALTS,
    SOLID_ELECTROLYTES,
    IONS,
    MaterialClass,
    CrystalStructure,
    FailureMode,
    get_material,
    get_materials_by_class,
    list_cathodes,
    list_anodes,
    list_electrolytes,
    KNOWN_GOOD_CELLS,
    KNOWN_BAD_PAIRINGS,
)


class TestMaterialProperties(unittest.TestCase):
    """Test material property tables for completeness and validity."""

    def test_all_materials_populated(self):
        """At least 15 materials defined."""
        self.assertGreaterEqual(len(ALL_MATERIALS), 15)

    def test_cathodes_exist(self):
        """Cathode materials exist."""
        self.assertIn('LCO', CATHODE_MATERIALS)
        self.assertIn('LFP', CATHODE_MATERIALS)
        self.assertIn('NMC811', CATHODE_MATERIALS)
        self.assertIn('LMO', CATHODE_MATERIALS)
        self.assertGreaterEqual(len(CATHODE_MATERIALS), 4)

    def test_anodes_exist(self):
        """Anode materials exist."""
        self.assertIn('Graphite', ANODE_MATERIALS)
        self.assertIn('Li_metal', ANODE_MATERIALS)
        self.assertIn('Si', ANODE_MATERIALS)
        self.assertIn('LTO', ANODE_MATERIALS)

    def test_electrolytes_exist(self):
        """Electrolyte components exist."""
        self.assertIn('EC', ELECTROLYTE_SOLVENTS)
        self.assertIn('DMC', ELECTROLYTE_SOLVENTS)
        self.assertIn('LiPF6', ELECTROLYTE_SALTS)
        self.assertIn('LLZO', SOLID_ELECTROLYTES)
        self.assertIn('LGPS', SOLID_ELECTROLYTES)

    def test_ions_exist(self):
        """Carrier ions exist."""
        self.assertIn('Li+', IONS)
        self.assertIn('Na+', IONS)
        self.assertIn('Mg2+', IONS)

    def test_cathode_voltage_windows(self):
        """All cathodes have valid voltage windows."""
        for name, mat in CATHODE_MATERIALS.items():
            self.assertIsNotNone(mat.voltage_window, f"{name} missing voltage_window")
            self.assertGreater(mat.voltage_window.upper, mat.voltage_window.lower,
                               f"{name} upper < lower voltage")
            self.assertGreater(mat.voltage_window.nominal, 0,
                               f"{name} nominal voltage <= 0")
            # Cathodes should operate at 1.5-5.0V vs Li/Li+ (includes Li-S at ~2.1V)
            self.assertGreaterEqual(mat.voltage_window.nominal, 1.5,
                                    f"{name} cathode voltage too low")
            self.assertLessEqual(mat.voltage_window.upper, 5.5,
                                 f"{name} cathode voltage too high")

    def test_anode_voltage_windows(self):
        """Anodes have voltage windows below cathode range."""
        for name, mat in ANODE_MATERIALS.items():
            self.assertIsNotNone(mat.voltage_window, f"{name} missing voltage_window")
            # Anodes should be < 3V vs Li/Li+
            self.assertLessEqual(mat.voltage_window.nominal, 3.0,
                                 f"{name} anode voltage too high")

    def test_theoretical_capacities(self):
        """Capacities are positive and physically reasonable."""
        for name, mat in {**CATHODE_MATERIALS, **ANODE_MATERIALS}.items():
            if mat.theoretical_capacity is not None:
                self.assertGreater(mat.theoretical_capacity, 0,
                                   f"{name} capacity <= 0")
                # No material exceeds Li metal's 3860 mAh/g by much
                self.assertLessEqual(mat.theoretical_capacity, 5000,
                                     f"{name} capacity unreasonably high")

    def test_material_classes_correct(self):
        """Materials have correct MaterialClass assignments."""
        for name, mat in CATHODE_MATERIALS.items():
            self.assertEqual(mat.material_class, MaterialClass.CATHODE, name)
        for name, mat in ANODE_MATERIALS.items():
            self.assertEqual(mat.material_class, MaterialClass.ANODE, name)
        for name, mat in ELECTROLYTE_SOLVENTS.items():
            self.assertEqual(mat.material_class, MaterialClass.ELECTROLYTE_SOLVENT, name)
        for name, mat in ELECTROLYTE_SALTS.items():
            self.assertEqual(mat.material_class, MaterialClass.ELECTROLYTE_SALT, name)
        for name, mat in SOLID_ELECTROLYTES.items():
            self.assertEqual(mat.material_class, MaterialClass.SOLID_ELECTROLYTE, name)

    def test_failure_modes_are_valid_enums(self):
        """All failure modes are valid FailureMode enum values."""
        for name, mat in ALL_MATERIALS.items():
            for fm in mat.failure_modes:
                self.assertIsInstance(fm, FailureMode,
                                     f"{name} has invalid failure mode: {fm}")

    def test_sources_populated(self):
        """Key materials have source citations."""
        for name in ['LCO', 'LFP', 'NMC811', 'Graphite', 'Li_metal', 'Si', 'LLZO', 'LGPS']:
            mat = get_material(name)
            self.assertIsNotNone(mat, f"{name} not found")
            self.assertGreater(len(mat.sources), 0,
                               f"{name} has no source citations")

    def test_get_material_lookup(self):
        """get_material() returns correct material or None."""
        self.assertIsNotNone(get_material('LFP'))
        self.assertEqual(get_material('LFP').formula, 'LiFePO4')
        self.assertIsNone(get_material('NonexistentMaterial'))

    def test_get_materials_by_class(self):
        """get_materials_by_class() filters correctly."""
        cathodes = get_materials_by_class(MaterialClass.CATHODE)
        self.assertGreater(len(cathodes), 0)
        for name, mat in cathodes.items():
            self.assertEqual(mat.material_class, MaterialClass.CATHODE)

    def test_list_functions(self):
        """list_cathodes/anodes/electrolytes return non-empty lists."""
        self.assertGreater(len(list_cathodes()), 0)
        self.assertGreater(len(list_anodes()), 0)
        self.assertGreater(len(list_electrolytes()), 0)

    def test_known_good_cells_reference_valid_materials(self):
        """KNOWN_GOOD_CELLS reference materials that exist."""
        for cell in KNOWN_GOOD_CELLS:
            self.assertIsNotNone(get_material(cell['cathode']),
                                 f"Unknown cathode: {cell['cathode']}")
            self.assertIsNotNone(get_material(cell['anode']),
                                 f"Unknown anode: {cell['anode']}")

    def test_known_bad_pairings_reference_valid_materials(self):
        """KNOWN_BAD_PAIRINGS reference materials that exist."""
        for pair in KNOWN_BAD_PAIRINGS:
            self.assertIsNotNone(get_material(pair['material_a']),
                                 f"Unknown material: {pair['material_a']}")
            self.assertIsNotNone(get_material(pair['material_b']),
                                 f"Unknown material: {pair['material_b']}")

    def test_to_dict_serialization(self):
        """BatteryMaterial.to_dict() returns valid dict."""
        lfp = get_material('LFP')
        d = lfp.to_dict()
        self.assertIn('name', d)
        self.assertIn('formula', d)
        self.assertIn('material_class', d)
        self.assertEqual(d['name'], 'LFP')

    def test_si_anode_extreme_expansion(self):
        """Si anode has ~300% volume expansion (known value)."""
        si = get_material('Si')
        self.assertIsNotNone(si.volume_expansion)
        self.assertGreaterEqual(si.volume_expansion, 2.5)  # At least 250%

    def test_lto_zero_strain(self):
        """LTO is a 'zero-strain' material (< 1% expansion)."""
        lto = get_material('LTO')
        self.assertIsNotNone(lto.volume_expansion)
        self.assertLess(lto.volume_expansion, 0.01)

    def test_lgps_narrow_stability_window(self):
        """LGPS has a narrow electrochemical stability window."""
        lgps = get_material('LGPS')
        self.assertIsNotNone(lgps.oxidation_potential)
        self.assertIsNotNone(lgps.reduction_potential)
        window = lgps.oxidation_potential - lgps.reduction_potential
        # LGPS window is ~0.4V (1.7-2.1V), very narrow
        self.assertLess(window, 1.0)

    def test_li_metal_highest_capacity(self):
        """Li metal has the highest theoretical capacity."""
        li = get_material('Li_metal')
        self.assertIsNotNone(li.theoretical_capacity)
        # Li metal: 3860 mAh/g (highest of any anode)
        self.assertGreater(li.theoretical_capacity, 3000)


if __name__ == '__main__':
    unittest.main()
