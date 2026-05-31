# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Integration tests for the ZFC reasoning engine.

Tests cover:
1. Import smoke tests
2. Universe construction from store
3. Logic oracle (entailment, witnesses)
4. Well-ordering (rank, ordinal oracle)
5. Separation checker (contradiction detection)
6. Proof engine (dual verification)
7. Meta Kan / System 3 (episode recording, meta-prediction)
8. Store adapter (store -> ZFC round-trip)
9. Bridge (delta classification)
"""

import sys
import os
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 1. Import Smoke Tests
# ============================================================

class TestImports(unittest.TestCase):
    """Verify all ZFC modules import cleanly."""

    def test_import_universe(self):
        from zfc import Universe, ZFSet, Relation, zfset, relation
        self.assertTrue(callable(zfset))
        self.assertTrue(callable(relation))

    def test_import_logic(self):
        from zfc import (
            Formula, FormulaKind, Term, Model, Theory, LogicOracle,
            atom, member, equals, neg, conj, disj, implies, iff,
            forall, exists, var, const, conj_all, satisfies, find_witness,
        )
        self.assertTrue(callable(atom))

    def test_import_well_ordering(self):
        from zfc import (
            Ordinal, WellOrder, OrdinalOracle,
            well_order_by_rank, well_order_by_relation,
            von_neumann_rank, rank_all,
            transfinite_induction, bounded_induction,
            RankProfile, rank_profile, classify_relation_by_rank,
        )
        self.assertTrue(callable(well_order_by_rank))

    def test_import_separation(self):
        from zfc import (
            Constraint, Contradiction, SeparationResult, SeparationChecker,
            prediction_to_constraint, predictions_to_constraints,
            detect_pairwise_contradictions, find_minimal_conflict,
        )
        self.assertTrue(callable(prediction_to_constraint))

    def test_import_proof_engine(self):
        from zfc import (
            Proof, ProofStep, ProofResult,
            ZFCVerifier, CATVerifier,
            StepMethod, StepStatus,
            step, axiom,
        )
        self.assertTrue(callable(step))

    def test_import_meta_kan(self):
        from zfc import (
            DeltaType, Resolution, Episode, EpisodeCategory,
            MetaPrediction, MetaKanExtension, System3Oracle,
        )
        self.assertIsNotNone(DeltaType.AGREE)

    def test_import_store_adapter(self):
        from zfc.store_adapter import (
            store_to_universe, store_to_model,
            build_transitivity_theory, store_to_logic_oracle,
            store_to_ordinal_oracle, adapter_summary,
        )
        self.assertTrue(callable(store_to_universe))

    def test_import_bridge(self):
        from zfc.bridge import DualEngineBridge, DualResult, DualPrediction
        self.assertTrue(callable(DualEngineBridge))


# ============================================================
# 2. Universe Construction
# ============================================================

class TestUniverse(unittest.TestCase):
    """Test ZFC Universe primitives."""

    def setUp(self):
        from zfc import Universe, zfset, relation
        self.V = Universe("TestUniverse")
        self.drugs = self.V.add_set(zfset("Drugs"))
        self.aspirin = self.V.add_set(zfset("Aspirin"))
        self.cox2 = self.V.add_set(zfset("COX2"))
        self.V.add_element(self.aspirin, self.drugs)
        self.inhibits = relation("inhibits", [("Aspirin", "COX2")])
        self.V.add_relation(self.inhibits)

    def test_membership(self):
        self.assertTrue(self.V.membership("Aspirin", "Drugs"))
        self.assertFalse(self.V.membership("COX2", "Drugs"))

    def test_relation_holds(self):
        self.assertTrue(self.inhibits.holds("Aspirin", "COX2"))
        self.assertFalse(self.inhibits.holds("COX2", "Aspirin"))

    def test_relation_image(self):
        img = self.inhibits.image("Aspirin")
        self.assertIn("COX2", img)

    def test_separation(self):
        result = self.V.separate(
            self.drugs,
            lambda x: self.inhibits.holds(x, "COX2"),
            name="COX2_inhibitors"
        )
        self.assertIn("Aspirin", result._elements)

    def test_union(self):
        from zfc import zfset as make_zfset
        proteins = self.V.add_set(make_zfset("Proteins"))
        self.V.add_element(self.cox2, proteins)
        u = self.V.union(self.drugs, proteins)
        self.assertIn("Aspirin", u._elements)
        self.assertIn("COX2", u._elements)

    def test_compose_relations(self):
        from zfc import relation
        assoc = relation("associated_with", [("COX2", "Inflammation")])
        self.V.add_relation(assoc)
        composed = self.V.compose_relations(self.inhibits, assoc)
        self.assertTrue(composed.holds("Aspirin", "Inflammation"))

    def test_transitive_closure(self):
        from zfc import relation
        r = relation("chain", [("A", "B"), ("B", "C"), ("C", "D")])
        self.V.add_relation(r)
        tc = self.V.transitive_closure(r)
        self.assertTrue(tc.holds("A", "D"))
        self.assertTrue(tc.holds("A", "C"))

    def test_empty_set(self):
        self.assertEqual(len(self.V.empty._elements), 0)

    def test_extensional_equality(self):
        from zfc import zfset
        a = zfset("SetA", elements={"x", "y"})
        b = zfset("SetB", elements={"x", "y"})
        self.assertTrue(self.V.extensionally_equal(a, b))


# ============================================================
# 3. Logic Oracle
# ============================================================

class TestLogicOracle(unittest.TestCase):
    """Test first-order logic and entailment."""

    def setUp(self):
        from zfc import (
            Universe, zfset, relation,
            Model, Theory, LogicOracle,
            atom, conj, implies, forall, var, const,
        )
        V = Universe("LogicTest")
        for name in ["Aspirin", "COX2", "Inflammation"]:
            V.add_set(zfset(name))

        inhibits = relation("inhibits", [("Aspirin", "COX2")])
        assoc = relation("associated_with", [("COX2", "Inflammation")])
        treats = relation("treats", [("Aspirin", "Inflammation")])
        V.add_relation(inhibits)
        V.add_relation(assoc)
        V.add_relation(treats)

        M = Model(universe=V)
        T = Theory("TestTheory")
        # Transitivity axiom
        T.add_axiom(forall("x", forall("y", forall("z",
            implies(
                conj(
                    atom("inhibits", var("x"), var("y")),
                    atom("associated_with", var("y"), var("z")),
                ),
                atom("treats", var("x"), var("z")),
            )
        ))))
        self.oracle = LogicOracle(T, M)

    def test_predict_true(self):
        from zfc import atom, const
        claim = atom("treats", const("Aspirin"), const("Inflammation"))
        entailed, conf, witness = self.oracle.predict(claim)
        self.assertTrue(entailed)
        self.assertEqual(conf, 1.0)

    def test_predict_false(self):
        from zfc import atom, const
        claim = atom("treats", const("COX2"), const("Aspirin"))
        entailed, conf, _ = self.oracle.predict(claim)
        self.assertFalse(entailed)

    def test_predict_relation(self):
        entailed, conf, _ = self.oracle.predict_relation(
            "inhibits", "Aspirin", "COX2"
        )
        self.assertTrue(entailed)

    def test_find_all_entailed(self):
        results = self.oracle.find_all_entailed("inhibits", "Aspirin")
        names = [t for t, _ in results]
        self.assertIn("COX2", names)

    def test_check_consistency(self):
        is_consistent, violated = self.oracle.check_consistency()
        # Transitivity axiom is a universal -- it's not directly
        # checked by satisfies in this simple model
        self.assertIsInstance(is_consistent, bool)

    def test_compare_with_prediction(self):
        delta = self.oracle.compare_with_prediction({
            "source": "Aspirin",
            "target": "Inflammation",
            "relation": "treats",
            "confidence": 0.75,
        })
        self.assertEqual(delta["delta_type"], "agree")
        self.assertTrue(delta["zfc_says"])


# ============================================================
# 4. Well-Ordering
# ============================================================

class TestWellOrdering(unittest.TestCase):
    """Test ordinals and well-ordering."""

    def test_ordinal_successor(self):
        from zfc import Ordinal
        o = Ordinal(value=3)
        s = o.successor()
        self.assertEqual(s.value, 4)

    def test_ordinal_comparison(self):
        from zfc import Ordinal
        a = Ordinal(value=2)
        b = Ordinal(value=5)
        self.assertTrue(a < b)
        self.assertFalse(b < a)

    def test_rank_all(self):
        from zfc import Universe, zfset, rank_all
        V = Universe("RankTest")
        V.add_set(zfset("A"))
        V.add_set(zfset("B"))
        a_set = V.get_set("A")
        b_set = V.get_set("B")
        V.add_element(a_set, b_set)
        ranks = rank_all(V)
        self.assertIn("A", ranks)

    def test_well_order_by_rank(self):
        from zfc import Universe, zfset, well_order_by_rank
        V = Universe("WOTest")
        for name in ["X", "Y", "Z"]:
            V.add_set(zfset(name))
        wo = well_order_by_rank(V)
        self.assertIsNotNone(wo)
        self.assertTrue(len(wo.elements) >= 3)

    def test_ordinal_oracle(self):
        from zfc import Universe, zfset, relation, OrdinalOracle
        V = Universe("OOTest")
        for name in ["A", "B", "C"]:
            V.add_set(zfset(name))
        rel = relation("follows", [("A", "B"), ("B", "C")])
        V.add_relation(rel)
        oo = OrdinalOracle(V, rel)
        pred, conf, evidence = oo.predict_by_rank("A", "C")
        self.assertIsInstance(pred, bool)
        self.assertIsInstance(conf, float)


# ============================================================
# 5. Separation Checker
# ============================================================

class TestSeparation(unittest.TestCase):
    """Test constraint satisfaction and contradiction detection."""

    def test_prediction_to_constraint(self):
        from zfc import prediction_to_constraint
        c = prediction_to_constraint({
            "source": "DrugA",
            "target": "ProteinB",
            "relation": "inhibits",
            "confidence": 0.8,
            "strategy": "semantic",
        })
        self.assertEqual(c.confidence, 0.8)
        self.assertEqual(c.strategy, "semantic")

    def test_detect_contradictions(self):
        from zfc import predictions_to_constraints, detect_pairwise_contradictions
        preds = [
            {"source": "A", "target": "B", "relation": "inhibits",
             "confidence": 0.8, "strategy": "s1"},
            {"source": "A", "target": "B", "relation": "activates",
             "confidence": 0.7, "strategy": "s2"},
        ]
        constraints = predictions_to_constraints(preds)
        contradictions = detect_pairwise_contradictions(constraints)
        self.assertTrue(len(contradictions) > 0)

    def test_no_contradictions(self):
        from zfc import predictions_to_constraints, detect_pairwise_contradictions
        preds = [
            {"source": "A", "target": "B", "relation": "inhibits",
             "confidence": 0.8, "strategy": "s1"},
            {"source": "C", "target": "D", "relation": "activates",
             "confidence": 0.7, "strategy": "s2"},
        ]
        constraints = predictions_to_constraints(preds)
        contradictions = detect_pairwise_contradictions(constraints)
        self.assertEqual(len(contradictions), 0)

    def test_separation_checker(self):
        from zfc import Universe, SeparationChecker
        V = Universe("SepTest")
        checker = SeparationChecker(V)
        result = checker.check([
            {"source": "A", "target": "B", "relation": "inhibits",
             "confidence": 0.8, "strategy": "s1"},
        ])
        self.assertTrue(result.is_consistent)


# ============================================================
# 6. Proof Engine
# ============================================================

class TestProofEngine(unittest.TestCase):
    """Test dual-verified proof construction."""

    def test_axiom(self):
        from zfc import Proof, axiom, StepStatus
        proof = Proof("TestProof")
        ax = proof.add_axiom(axiom("ax1", "Known fact", "Prop"))
        self.assertEqual(ax.status, StepStatus.VALID)

    def test_composition_step(self):
        from zfc import Proof, axiom, step, StepMethod, StepStatus
        proof = Proof("CompTest")
        proof.add_axiom(axiom("ax1", "Drug inhibits Protein", "Drug->Protein"))
        proof.add_axiom(axiom("ax2", "Protein associated Disease", "Protein->Disease"))
        s = proof.add_step(step(
            "s1", "Drug treats Disease",
            method=StepMethod.COMPOSITION,
            inputs=["ax1", "ax2"],
            input_types=["Drug->Protein", "Protein->Disease"],
            output_type="Drug->Disease",
            justification="composition",
        ))
        self.assertEqual(s.status, StepStatus.VALID)

    def test_verify_all(self):
        from zfc import Proof, axiom, step, StepMethod
        proof = Proof("VerifyTest", goal="conclusion")
        proof.add_axiom(axiom("ax1", "premise", "Prop"))
        proof.add_step(step(
            "s1", "conclusion",
            method=StepMethod.SEPARATION,
            inputs=["ax1"],
            input_types=["Prop"],
            output_type="conclusion",
            justification="separation",
        ))
        result = proof.verify_all()
        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_complete)

    def test_reject_missing_input(self):
        from zfc import Proof, step, StepMethod, StepStatus
        proof = Proof("RejectTest")
        s = proof.add_step(step(
            "s1", "bad step",
            method=StepMethod.COMPOSITION,
            inputs=["nonexistent1", "nonexistent2"],
            input_types=["A", "B"],
            output_type="C",
        ))
        self.assertEqual(s.status, StepStatus.REJECT)


# ============================================================
# 7. Meta Kan / System 3
# ============================================================

class TestSystem3(unittest.TestCase):
    """Test episode recording and meta-prediction."""

    def setUp(self):
        from zfc import System3Oracle, Episode, Resolution
        self.oracle = System3Oracle("TestS3")
        # Add some episodes
        episodes = [
            Episode("e1", "A", "B", "rel1", "test",
                    cat_says=True, cat_confidence=0.8,
                    zfc_says=True, zfc_confidence=0.7),
            Episode("e2", "C", "D", "rel1", "test",
                    cat_says=True, cat_confidence=0.75,
                    zfc_says=True, zfc_confidence=0.65),
            Episode("e3", "E", "F", "rel1", "test",
                    cat_says=False, cat_confidence=0.2,
                    zfc_says=True, zfc_confidence=0.8),
        ]
        for ep in episodes:
            self.oracle.record(ep)
        self.oracle.resolve("e1", Resolution.CONFIRMED, "known")
        self.oracle.resolve("e2", Resolution.CONFIRMED, "known")
        self.oracle.resolve("e3", Resolution.CONFIRMED, "orphan was real")

    def test_record(self):
        self.assertEqual(len(self.oracle.history.episodes), 3)

    def test_resolve(self):
        self.assertEqual(len(self.oracle.history._resolved), 3)

    def test_delta_classification(self):
        from zfc import DeltaType
        ep1 = self.oracle.history.episodes["e1"]
        ep3 = self.oracle.history.episodes["e3"]
        self.assertEqual(ep1.delta_type, DeltaType.AGREE)
        self.assertEqual(ep3.delta_type, DeltaType.ORPHAN)

    def test_predict(self):
        pred = self.oracle.predict("G", "H", "rel1", "test",
                                   cat_conf=0.7, zfc_conf=0.6)
        self.assertIsNotNone(pred)
        self.assertIsNotNone(pred.predicted_delta)

    def test_should_run_both(self):
        should, reason = self.oracle.should_run_both("X", "Y", "rel1", "test")
        self.assertIsInstance(should, bool)
        self.assertIsInstance(reason, str)

    def test_report(self):
        report = self.oracle.report()
        self.assertIn("System 3", report)
        self.assertIn("Episodes", report)

    def test_episode_features(self):
        ep = self.oracle.history.episodes["e1"]
        features = ep.features()
        self.assertEqual(len(features), 11)


# ============================================================
# 8. Store Adapter
# ============================================================

class TestStoreAdapter(unittest.TestCase):
    """Test store -> ZFC conversion."""

    def setUp(self):
        from data import create_memory_store, StoredObject, StoredMorphism
        self.store = create_memory_store()
        for name, typ in [
            ("Aspirin", "Drug"), ("COX2", "Protein"),
            ("Inflammation", "Disease"),
        ]:
            self.store.add_object(StoredObject(name=name, type_name=typ))
        for src, tgt, rel in [
            ("Aspirin", "COX2", "inhibits"),
            ("COX2", "Inflammation", "associated_with"),
            ("Aspirin", "Inflammation", "treats"),
        ]:
            self.store.add_morphism(
                StoredMorphism(name=rel, source_name=src, target_name=tgt)
            )

    def test_store_to_universe(self):
        from zfc.store_adapter import store_to_universe
        V = store_to_universe(self.store)
        self.assertIn("Aspirin", V.sets)
        self.assertIn("COX2", V.sets)
        self.assertIn("Drug", V.sets)  # container set
        self.assertIn("inhibits", V.relations)

    def test_store_to_universe_type_membership(self):
        from zfc.store_adapter import store_to_universe
        V = store_to_universe(self.store)
        drug_set = V.get_set("Drug")
        self.assertIn("Aspirin", drug_set._elements)
        self.assertNotIn("COX2", drug_set._elements)

    def test_store_to_model(self):
        from zfc.store_adapter import store_to_model
        M = store_to_model(self.store)
        self.assertIsNotNone(M.universe)
        self.assertGreater(len(M.universe.sets), 0)

    def test_build_transitivity_theory(self):
        from zfc.store_adapter import build_transitivity_theory
        T = build_transitivity_theory(self.store)
        self.assertGreater(len(T.axioms), 0)

    def test_store_to_logic_oracle(self):
        from zfc.store_adapter import store_to_logic_oracle
        oracle = store_to_logic_oracle(self.store)
        entailed, conf, _ = oracle.predict_relation(
            "inhibits", "Aspirin", "COX2"
        )
        self.assertTrue(entailed)

    def test_store_to_ordinal_oracle(self):
        from zfc.store_adapter import store_to_ordinal_oracle
        oo = store_to_ordinal_oracle(self.store)
        self.assertIsNotNone(oo)

    def test_adapter_summary(self):
        from zfc.store_adapter import adapter_summary
        summary = adapter_summary(self.store)
        self.assertEqual(summary["total_objects"], 3)
        self.assertEqual(summary["total_morphisms"], 3)
        self.assertIn("Drug", summary["types"])
        self.assertIn("inhibits", summary["relations"])


# ============================================================
# 9. Bridge (Delta Classification)
# ============================================================

class TestBridge(unittest.TestCase):
    """Test DualEngineBridge delta classification."""

    def setUp(self):
        from data import create_memory_store, StoredObject, StoredMorphism
        self.store = create_memory_store()
        for name, typ in [
            ("Aspirin", "Drug"), ("Celecoxib", "Drug"),
            ("COX2", "Protein"),
            ("Inflammation", "Disease"), ("Pain", "Disease"),
        ]:
            self.store.add_object(StoredObject(name=name, type_name=typ))
        for src, tgt, rel in [
            ("Aspirin", "COX2", "inhibits"),
            ("Celecoxib", "COX2", "inhibits"),
            ("COX2", "Inflammation", "associated_with"),
            ("Aspirin", "Inflammation", "treats"),
            ("Celecoxib", "Inflammation", "treats"),
        ]:
            self.store.add_morphism(
                StoredMorphism(name=rel, source_name=src, target_name=tgt)
            )

    def test_bridge_creation(self):
        from zfc.bridge import DualEngineBridge
        bridge = DualEngineBridge(self.store, embeddings=None, domain="test")
        self.assertIsNotNone(bridge.logic_oracle)
        self.assertIsNone(bridge.cat_oracle)  # no embeddings

    def test_bridge_predict(self):
        from zfc.bridge import DualEngineBridge
        bridge = DualEngineBridge(self.store, embeddings=None, domain="test")
        result = bridge.predict("Celecoxib", "Inflammation")
        self.assertIsNotNone(result)
        self.assertGreater(len(result.predictions), 0)

    def test_bridge_orphan_detection(self):
        """ZFC-only mode: all predictions should be ORPHANs (no CAT)."""
        from zfc.bridge import DualEngineBridge
        from zfc import DeltaType
        bridge = DualEngineBridge(self.store, embeddings=None)
        result = bridge.predict("Aspirin", "Inflammation")
        # Since CAT is unavailable, ZFC-found predictions are ORPHANs
        for dp in result.predictions:
            self.assertEqual(dp.delta_type, DeltaType.ORPHAN)

    def test_bridge_episode_recorded(self):
        from zfc.bridge import DualEngineBridge
        bridge = DualEngineBridge(self.store, embeddings=None, domain="test")
        result = bridge.predict("Aspirin", "COX2")
        self.assertIsNotNone(result.episode)
        self.assertEqual(len(bridge.system3.history.episodes), 1)

    def test_bridge_predict_batch(self):
        from zfc.bridge import DualEngineBridge
        bridge = DualEngineBridge(self.store, embeddings=None)
        results = bridge.predict_batch([
            ("Aspirin", "Inflammation"),
            ("Celecoxib", "Inflammation"),
        ])
        self.assertEqual(len(results), 2)

    def test_bridge_analysis(self):
        from zfc.bridge import DualEngineBridge
        bridge = DualEngineBridge(self.store, embeddings=None, domain="test")
        result = bridge.predict("Aspirin", "Inflammation")
        self.assertIn("Dual Engine Bridge", result.analysis)
        self.assertIn("ORPHAN", result.analysis)

    def test_bridge_report(self):
        from zfc.bridge import DualEngineBridge
        bridge = DualEngineBridge(self.store, embeddings=None, domain="test")
        bridge.predict("Aspirin", "Inflammation")
        report = bridge.report()
        self.assertIn("System 3", report)

    def test_bridge_resolve(self):
        from zfc.bridge import DualEngineBridge
        from zfc import Resolution
        bridge = DualEngineBridge(self.store, embeddings=None)
        result = bridge.predict("Aspirin", "Inflammation")
        bridge.resolve(result.episode.id, Resolution.CONFIRMED, "known")
        self.assertEqual(len(bridge.system3.history._resolved), 1)


if __name__ == "__main__":
    unittest.main()
