"""Tests for MOF bridge KOMPOSOS integration."""

import unittest

from mof_bridge.material_properties import get_mof, ALL_MOFS
from mof_bridge.integration import (
    mof_to_stored_object,
    MOFMorphism,
    create_mof_morphism,
    build_mof_category,
)
from mof_bridge.interface_validator import MOFConditions


class TestMOFToStoredObject(unittest.TestCase):

    def test_conversion(self):
        mof = get_mof('ZIF-8')
        obj = mof_to_stored_object(mof)
        self.assertEqual(obj.name, 'ZIF-8')
        self.assertIn('mof', obj.metadata['domain'])
        self.assertEqual(obj.metadata['topology'], 'sod')

    def test_all_mofs_convert(self):
        for name, mof in ALL_MOFS.items():
            obj = mof_to_stored_object(mof)
            self.assertEqual(obj.name, mof.name)


class TestMOFMorphism(unittest.TestCase):

    def test_create_morphism(self):
        morphism = create_mof_morphism('UiO-66')
        self.assertIsInstance(morphism, MOFMorphism)
        self.assertEqual(morphism.mof.name, 'UiO-66')

    def test_create_morphism_with_conditions(self):
        conditions = MOFConditions(
            operating_temp_C=200.0,
            environment='humid',
        )
        morphism = create_mof_morphism('ZIF-8', conditions=conditions)
        self.assertTrue(morphism.interface_score.total > 0)

    def test_create_morphism_unknown_raises(self):
        with self.assertRaises(ValueError):
            create_mof_morphism('NONEXISTENT')

    def test_morphism_to_stored(self):
        morphism = create_mof_morphism('MOF-5')
        stored = morphism.to_stored_morphism()
        self.assertEqual(stored.source_name, 'MOF-5')
        self.assertIn('app', stored.target_name.lower())


class TestBuildCategory(unittest.TestCase):

    def test_build_category(self):
        cat = build_mof_category()
        if cat is not None:
            self.assertGreater(len(cat.objects), 0)

    def test_build_subset(self):
        cat = build_mof_category(mof_names=['ZIF-8', 'UiO-66', 'MOF-5'])
        if cat is not None:
            # At least the 3 MOFs as objects
            self.assertGreaterEqual(len(cat.objects), 3)


if __name__ == '__main__':
    unittest.main()
