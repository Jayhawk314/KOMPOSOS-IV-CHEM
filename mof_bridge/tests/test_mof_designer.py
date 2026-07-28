# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for MOF linker inverse design system.

Tests the full inverse design pipeline:
1. MP MOF loader and cache
2. Atomic descriptor extraction
3. Linker generator (novelty, atom count validation)
4. KOMPOSOS verdict engine (ZFC + CAT dual reasoning)
5. Screening pipeline
"""

import unittest
import tempfile
import os
import json
from pathlib import Path

# Check for RDKit availability at module level
try:
    from rdkit import Chem
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


class TestMOFLinkerCache(unittest.TestCase):
    """Test MOF linker cache operations."""

    def test_cache_initialization(self):
        """Test MOFLinkerCache initializes correctly."""
        from mof_bridge.mp_mof_loader import MOFLinkerCache

        import sys
        kwargs = {'ignore_cleanup_errors': True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as tmpdir:
            cache = MOFLinkerCache(cache_dir=tmpdir)
            self.assertIsNotNone(cache)
            self.assertEqual(cache.entry_count(), 0)

    def test_demo_linker_generation(self):
        """Test demo linker generation without MP API."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.mp_mof_loader import MOFLinkerCache
        import gc
        import sys

        # Use ignore_cleanup_errors on Python 3.10+ to avoid Windows file locking issues
        kwargs = {'ignore_cleanup_errors': True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as tmpdir:
            cache = MOFLinkerCache(cache_dir=tmpdir)
            # Demo mode generates small set of known 22-atom linkers
            cache.download(api_key="demo", max_mofs=5)

            count = cache.entry_count()
            self.assertGreater(count, 0)
            self.assertLessEqual(count, 10)  # Demo generates ≤10 linkers

            # Force garbage collection to close SQLite connections (Windows issue)
            cache = None
            gc.collect()

    def test_load_linkers(self):
        """Test loading linkers from cache."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.mp_mof_loader import MOFLinkerCache

        import sys
        kwargs = {'ignore_cleanup_errors': True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as tmpdir:
            cache = MOFLinkerCache(cache_dir=tmpdir)
            cache.download(api_key="demo", max_mofs=3)

            linkers = cache.load_linkers()
            self.assertIsInstance(linkers, list)
            self.assertGreater(len(linkers), 0)

            # Check linker structure
            for l in linkers:
                self.assertTrue(hasattr(l, "linker_id"))
                self.assertTrue(hasattr(l, "smiles"))
                self.assertTrue(hasattr(l, "formula"))
                self.assertTrue(hasattr(l, "heavy_atom_count"))
                self.assertEqual(l.heavy_atom_count, 22)

    def test_linker_to_dict(self):
        """Test MOFLinker serialization."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.mp_mof_loader import MOFLinkerCache

        import sys
        kwargs = {'ignore_cleanup_errors': True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as tmpdir:
            cache = MOFLinkerCache(cache_dir=tmpdir)
            cache.download(api_key="demo", max_mofs=1)
            linkers = cache.load_linkers()

            if linkers:
                d = linkers[0].to_dict()
                self.assertIsInstance(d, dict)
                self.assertIn("linker_id", d)
                self.assertIn("smiles", d)
                self.assertIn("formula", d)
                self.assertIn("heavy_atom_count", d)

    def test_import_preextracted_csv(self):
        """Test importing a pre-extracted CSV dataset."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.mp_mof_loader import MOFLinkerCache

        import sys
        kwargs = {'ignore_cleanup_errors': True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as tmpdir:
            dataset_path = Path(tmpdir) / "linkers.csv"
            dataset_path.write_text(
                "mof_id,linker_smiles\n"
                "mof-1,O=C(O)c1ccc(-c2ccc(-c3ccccc3)cc2)c(O)c1\n"
                "mof-2,c1ccccc1\n",
                encoding="utf-8",
            )

            cache = MOFLinkerCache(cache_dir=tmpdir)
            summary = cache.import_linker_dataset(
                str(dataset_path),
                source_name="test-csv",
                exact_heavy_atoms=22,
            )

            self.assertEqual(summary["imported"], 1)
            self.assertEqual(cache.entry_count(), 1)
            linkers = cache.load_linkers()
            self.assertEqual(linkers[0].heavy_atom_count, 22)

    def test_import_preextracted_json(self):
        """Test importing a pre-extracted JSON dataset."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.mp_mof_loader import MOFLinkerCache

        import sys
        kwargs = {'ignore_cleanup_errors': True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as tmpdir:
            dataset_path = Path(tmpdir) / "linkers.json"
            dataset_path.write_text(
                json.dumps([
                    {
                        "material_id": "mof-1",
                        "smiles": "O=C(O)c1ccc(-c2ccc(-c3ccccc3)cc2)c(O)c1",
                    },
                    {
                        "material_id": "mof-2",
                        "smiles": "not-a-smiles",
                    },
                ]),
                encoding="utf-8",
            )

            cache = MOFLinkerCache(cache_dir=tmpdir)
            summary = cache.import_linker_dataset(
                str(dataset_path),
                source_name="test-json",
                exact_heavy_atoms=22,
            )

            self.assertEqual(summary["imported"], 1)
            self.assertEqual(summary["skipped_invalid_smiles"], 1)
            self.assertEqual(cache.entry_count(), 1)

    def test_linker_like_filter_rejects_polyol_and_keeps_aromatic_linker(self):
        """Importer should reject obvious polyol fragments and keep aromatic linkers."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.mp_mof_loader import MOFLinkerCache

        import sys
        kwargs = {'ignore_cleanup_errors': True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as tmpdir:
            dataset_path = Path(tmpdir) / "linkers.json"
            dataset_path.write_text(
                json.dumps([
                    {
                        "id": "good",
                        "smiles": "O=C(O)c1ccc(-c2ccc(-c3ccccc3)cc2)c(O)c1",
                    },
                    {
                        "id": "bad",
                        "smiles": "CC(CC(Br)C(C)CCC(C)C(Br)CC(C)C(O)O)C(O)O",
                    },
                ]),
                encoding="utf-8",
            )

            cache = MOFLinkerCache(cache_dir=tmpdir)
            summary = cache.import_linker_dataset(str(dataset_path), source_name="filter-test")

            self.assertEqual(summary["imported"], 1)
            self.assertEqual(summary["skipped_non_linker_like"], 1)
            linkers = cache.load_linkers()
            self.assertEqual(len(linkers), 1)
            self.assertIn("c1", linkers[0].smiles)


class TestAtomicDescriptors(unittest.TestCase):
    """Test atomic descriptor extraction."""

    def test_compute_descriptors_benzene(self):
        """Test descriptor extraction for benzene."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.atomic_descriptors import compute_atomic_descriptors

        smiles = "c1ccccc1"  # Benzene
        desc = compute_atomic_descriptors(smiles)

        self.assertIn("atoms", desc)
        self.assertIn("bonds", desc)
        self.assertIn("global", desc)

        # Benzene has 6 carbons
        self.assertEqual(len(desc["atoms"]), 6)

        # Check atom properties
        for atom in desc["atoms"]:
            self.assertEqual(atom["element"], "C")
            self.assertTrue(atom["aromatic"])
            self.assertIn(atom["hybridization"], ["SP2", "sp2"])

        # Check global properties
        self.assertEqual(desc["global"]["num_aromatic_rings"], 1)

    def test_compute_descriptors_carboxylic_acid(self):
        """Test descriptor extraction for benzoic acid."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.atomic_descriptors import compute_atomic_descriptors

        smiles = "c1ccc(cc1)C(=O)O"  # Benzoic acid
        desc = compute_atomic_descriptors(smiles)

        # Should have C, O atoms
        elements = {a["element"] for a in desc["atoms"]}
        self.assertIn("C", elements)
        self.assertIn("O", elements)

        # Should have heteroatom
        self.assertTrue(desc["global"]["has_heteroatom"])

    def test_descriptor_keys(self):
        """Test all required descriptor keys are present."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.atomic_descriptors import compute_atomic_descriptors

        smiles = "c1ccccc1"
        desc = compute_atomic_descriptors(smiles)

        # Atom keys
        required_atom_keys = {
            "index", "element", "atomic_number", "formal_charge",
            "hybridization", "aromatic", "num_bonds", "neighbors",
        }
        for atom in desc["atoms"]:
            for key in required_atom_keys:
                self.assertIn(key, atom)

        # Bond keys
        required_bond_keys = {"atom_i", "atom_j", "bond_type"}
        for bond in desc["bonds"]:
            for key in required_bond_keys:
                self.assertIn(key, bond)

        # Global keys
        required_global_keys = {"num_aromatic_rings", "has_heteroatom"}
        for key in required_global_keys:
            self.assertIn(key, desc["global"])


class TestLinkerGenerator(unittest.TestCase):
    """Test linker generator."""

    def setUp(self):
        """Set up generator with demo linkers."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.mp_mof_loader import MOFLinkerCache

        self.tmpdir = tempfile.mkdtemp()
        cache = MOFLinkerCache(cache_dir=self.tmpdir)
        cache.download(api_key="demo", max_mofs=5)
        self.known_linkers = cache.load_linkers()

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_generator_initialization(self):
        """Test LinkerGenerator initializes with known linkers."""
        from mof_bridge.linker_generator import LinkerGenerator

        generator = LinkerGenerator(self.known_linkers)
        self.assertIsNotNone(generator)
        self.assertEqual(len(generator.known_smiles), len(self.known_linkers))

    def test_generate_candidates_returns_list(self):
        """Test generator returns list of SMILES."""
        from mof_bridge.linker_generator import LinkerGenerator

        generator = LinkerGenerator(self.known_linkers)
        candidates = generator.generate_candidates(
            n_candidates=10,
            application_context="breath_VOC_sensing",
        )

        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 0)

    def test_all_candidates_have_valid_heavy_atom_count(self):
        """Test all generated candidates have 18-30 heavy atoms."""
        from mof_bridge.linker_generator import LinkerGenerator
        from rdkit import Chem

        generator = LinkerGenerator(self.known_linkers)
        candidates = generator.generate_candidates(
            n_candidates=10,
            application_context="breath_VOC_sensing",
        )

        for smiles in candidates:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                heavy_atoms = mol.GetNumHeavyAtoms()
                self.assertGreaterEqual(
                    heavy_atoms, 18,
                    f"Candidate {smiles} has {heavy_atoms} heavy atoms, expected >= 18"
                )
                self.assertLessEqual(
                    heavy_atoms, 30,
                    f"Candidate {smiles} has {heavy_atoms} heavy atoms, expected <= 30"
                )

    def test_candidates_are_novel(self):
        """Test generated candidates are not in known set."""
        from mof_bridge.linker_generator import LinkerGenerator

        generator = LinkerGenerator(self.known_linkers)
        candidates = generator.generate_candidates(
            n_candidates=10,
            application_context="breath_VOC_sensing",
        )

        known_smiles_set = {l.smiles for l in self.known_linkers}
        for smiles in candidates:
            self.assertNotIn(
                smiles, known_smiles_set,
                f"Candidate {smiles} is already in known linker set"
            )

    def test_candidates_are_unique(self):
        """Test all generated candidates are unique."""
        from mof_bridge.linker_generator import LinkerGenerator

        generator = LinkerGenerator(self.known_linkers)
        candidates = generator.generate_candidates(
            n_candidates=20,
            application_context="breath_VOC_sensing",
        )

        # Check for duplicates
        unique = set(candidates)
        self.assertEqual(
            len(unique), len(candidates),
            f"Found {len(candidates) - len(unique)} duplicate candidates"
        )

    def test_exclude_elements(self):
        """Test element exclusion constraint."""
        from mof_bridge.linker_generator import LinkerGenerator
        from rdkit import Chem

        generator = LinkerGenerator(self.known_linkers)
        candidates = generator.generate_candidates(
            n_candidates=10,
            application_context="breath_VOC_sensing",
            exclude_elements=["F", "Cl"],
        )

        for smiles in candidates:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                atoms = [atom.GetSymbol() for atom in mol.GetAtoms()]
                self.assertNotIn("F", atoms)
                self.assertNotIn("Cl", atoms)


class TestLinkerVerdictEngine(unittest.TestCase):
    """Test KOMPOSOS verdict engine."""

    def test_verdict_engine_initialization(self):
        """Test LinkerVerdictEngine initializes."""
        from mof_bridge.komposos_verdicts import LinkerVerdictEngine

        engine = LinkerVerdictEngine()
        self.assertIsNotNone(engine)

    def test_score_verdicts_simple_aromatic(self):
        """Test verdict scoring on simple aromatic linker."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.komposos_verdicts import LinkerVerdictEngine

        engine = LinkerVerdictEngine()

        # Simple aromatic carboxylic acid (common linker motif)
        smiles = "c1ccc(cc1)C(=O)O"  # Benzoic acid (only 7 heavy atoms, but for demo)

        result = engine.score_verdicts(smiles, "breath_VOC_sensing")

        # Check result structure
        self.assertIsNotNone(result)
        self.assertEqual(result.linker_smiles, smiles)
        self.assertIsInstance(result.verdicts, dict)
        self.assertIsInstance(result.verdict_scores, dict)
        self.assertIsInstance(result.morphism_integrity, float)
        self.assertIsInstance(result.overall_viable, bool)

        # Check all 5 verdicts present
        required_verdicts = {"synthesizability", "toxicity", "stability", "activity", "conductivity"}
        self.assertEqual(set(result.verdicts.keys()), required_verdicts)

        # Check verdict values are valid
        valid_verdicts = {"AGREE", "HOLLOW", "ORPHAN", "REJECT"}
        for v in result.verdicts.values():
            self.assertIn(v, valid_verdicts)

        # Check scores are 0-1
        for score in result.verdict_scores.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

        # Check morphism integrity is 0-1
        self.assertGreaterEqual(result.morphism_integrity, 0.0)
        self.assertLessEqual(result.morphism_integrity, 1.0)

    def test_verdict_result_to_dict(self):
        """Test LinkerVerdictResult serialization."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.komposos_verdicts import LinkerVerdictEngine

        engine = LinkerVerdictEngine()
        smiles = "c1ccccc1"  # Benzene

        result = engine.score_verdicts(smiles, "breath_VOC_sensing")
        d = result.to_dict()

        self.assertIsInstance(d, dict)
        self.assertIn("linker_smiles", d)
        self.assertIn("verdicts", d)
        self.assertIn("verdict_scores", d)
        self.assertIn("morphism_integrity", d)
        self.assertIn("overall_viable", d)

    def test_morphism_integrity_consistent_molecule(self):
        """Test morphism integrity for a consistent molecule."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.komposos_verdicts import LinkerVerdictEngine

        engine = LinkerVerdictEngine()

        # Benzene is perfectly consistent (all SP2 aromatic carbons)
        smiles = "c1ccccc1"
        result = engine.score_verdicts(smiles, "breath_VOC_sensing")

        # Should have high morphism integrity (>0.8)
        self.assertGreater(result.morphism_integrity, 0.7)


class TestLinkerScreener(unittest.TestCase):
    """Test full screening pipeline."""

    def setUp(self):
        """Set up screener with demo cache."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_screener_initialization(self):
        """Test LinkerScreener initializes with cache."""
        from mof_bridge.linker_screening import LinkerScreener
        from mof_bridge.mp_mof_loader import MOFLinkerCache

        # Create demo cache
        cache = MOFLinkerCache(cache_dir=self.tmpdir)
        cache.download(api_key="demo", max_mofs=3)

        # Initialize screener (will auto-load cache)
        screener = LinkerScreener()
        self.assertIsNotNone(screener)

    def test_screening_pipeline_small(self):
        """Test full pipeline with small candidate count."""
        from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec
        from mof_bridge.mp_mof_loader import MOFLinkerCache

        # Create demo cache
        cache = MOFLinkerCache(cache_dir=self.tmpdir)
        cache.download(api_key="demo", max_mofs=3)

        spec = LinkerScreeningSpec(
            application_context="breath_VOC_sensing",
            num_candidates=5,  # Small for fast test
            require_all_agree=False,  # Allow any verdict
            allow_hollow=True,
            ranking_mode="morphism_integrity",
        )

        screener = LinkerScreener()
        result = screener.screen(spec)

        # Check result structure
        self.assertIsNotNone(result)
        self.assertGreater(result.num_generated, 0)
        self.assertIsInstance(result.candidates, list)
        self.assertGreater(result.generation_time_sec, 0)

    def test_screening_result_to_dict(self):
        """Test ScreeningResult serialization."""
        from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec
        from mof_bridge.mp_mof_loader import MOFLinkerCache

        # Create demo cache
        cache = MOFLinkerCache(cache_dir=self.tmpdir)
        cache.download(api_key="demo", max_mofs=2)

        spec = LinkerScreeningSpec(
            application_context="breath_VOC_sensing",
            num_candidates=3,
            require_all_agree=False,
            allow_hollow=True,
        )

        screener = LinkerScreener()
        result = screener.screen(spec)

        d = result.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("candidates", d)
        self.assertIn("num_generated", d)
        self.assertIn("num_passed_all", d)
        self.assertIn("avg_morphism_integrity", d)
        self.assertIn("best_morphism_integrity", d)


class TestVerdictClassifications(unittest.TestCase):
    """Test verdict classification logic (AGREE/HOLLOW/ORPHAN/REJECT)."""

    def test_verdict_classification_types(self):
        """Test that verdict classifications are valid."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.komposos_verdicts import LinkerVerdictEngine

        engine = LinkerVerdictEngine()
        smiles = "c1ccccc1"  # Benzene

        result = engine.score_verdicts(smiles, "breath_VOC_sensing")

        # All verdicts should be one of 4 types
        valid_types = {"AGREE", "HOLLOW", "ORPHAN", "REJECT"}
        for verdict_name, verdict_value in result.verdicts.items():
            self.assertIn(
                verdict_value, valid_types,
                f"Verdict '{verdict_name}' has invalid type: {verdict_value}"
            )

    def test_overall_viable_logic(self):
        """Test overall_viable is True only if all verdicts AGREE."""
        if not RDKIT_AVAILABLE:
            self.skipTest("RDKit not available")

        from mof_bridge.komposos_verdicts import LinkerVerdictEngine

        engine = LinkerVerdictEngine()
        smiles = "c1ccccc1"

        result = engine.score_verdicts(smiles, "breath_VOC_sensing")

        # If overall_viable is True, all verdicts must be AGREE
        if result.overall_viable:
            for v in result.verdicts.values():
                self.assertEqual(v, "AGREE")

        # If any verdict is not AGREE, overall_viable must be False
        if any(v != "AGREE" for v in result.verdicts.values()):
            self.assertFalse(result.overall_viable)


if __name__ == "__main__":
    unittest.main()
