# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for streaming Kan extension module."""

import pytest
import time

from categorical.streaming_kan import (
    CommaObject, StreamingCommaCategory, StreamingKanExtension,
)


# ---------------------------------------------------------------------------
# CommaObject
# ---------------------------------------------------------------------------

class TestCommaObject:
    def test_create(self):
        obj = CommaObject(
            source_object="NMC811",
            morphism_to_target="NMC811->LFP",
            target="LFP",
            timestamp=time.time(),
            weight=0.8,
        )
        assert obj.source_object == "NMC811"
        assert obj.target == "LFP"
        assert obj.weight == 0.8


# ---------------------------------------------------------------------------
# StreamingCommaCategory
# ---------------------------------------------------------------------------

class TestStreamingCommaCategory:
    def test_add_observation(self):
        cat = StreamingCommaCategory(decay_rate=0.0)
        t = time.time()
        updated = cat.add_observation("A", t, [("B", 0.8), ("C", 0.6)])
        assert "B" in updated
        assert "C" in updated
        assert len(cat.objects) == 2

    def test_self_loop_skipped(self):
        cat = StreamingCommaCategory()
        t = time.time()
        cat.add_observation("A", t, [("A", 0.9), ("B", 0.5)])
        assert len(cat.objects) == 1  # Only B, not A

    def test_predictions_sorted(self):
        cat = StreamingCommaCategory(decay_rate=0.0)
        t = time.time()
        cat.add_observation("A", t, [("B", 0.8), ("C", 0.3)])
        preds = cat.get_predictions(top_k=5, current_time=t)
        assert preds[0][0] == "B"
        assert preds[0][1] > preds[1][1]

    def test_multiple_observations_accumulate(self):
        cat = StreamingCommaCategory(decay_rate=0.0)
        t = time.time()
        cat.add_observation("A", t, [("C", 0.5)])
        cat.add_observation("B", t, [("C", 0.3)])
        preds = cat.get_predictions(top_k=5, current_time=t)
        assert preds[0][0] == "C"
        assert preds[0][1] == pytest.approx(0.8)

    def test_confidence_increases_with_sources(self):
        cat = StreamingCommaCategory(decay_rate=0.0)
        t = time.time()
        cat.add_observation("A", t, [("D", 0.5)])
        conf1 = cat.get_confidence("D")
        cat.add_observation("B", t, [("D", 0.5)])
        conf2 = cat.get_confidence("D")
        cat.add_observation("C", t, [("D", 0.5)])
        conf3 = cat.get_confidence("D")
        assert conf1 < conf2 < conf3

    def test_confidence_zero_for_unknown(self):
        cat = StreamingCommaCategory()
        assert cat.get_confidence("unknown") == 0.0

    def test_contributor_count(self):
        cat = StreamingCommaCategory(decay_rate=0.0)
        t = time.time()
        cat.add_observation("A", t, [("D", 0.5)])
        cat.add_observation("B", t, [("D", 0.3)])
        assert cat.get_contributor_count("D") == 2

    def test_supporting_evidence(self):
        cat = StreamingCommaCategory(decay_rate=0.0)
        t = time.time()
        cat.add_observation("A", t, [("D", 0.5)])
        cat.add_observation("B", t, [("D", 0.3)])
        evidence = cat.get_supporting_evidence("D")
        assert evidence == ["A", "B"]

    def test_prune_old(self):
        cat = StreamingCommaCategory(decay_rate=0.0)
        old_time = time.time() - 7200  # 2 hours ago
        new_time = time.time()
        cat.add_observation("A", old_time, [("B", 0.5)])
        cat.add_observation("C", new_time, [("D", 0.8)])
        cat.prune_old(max_age_seconds=3600)
        assert len(cat.objects) == 1
        assert cat.objects[0].source_object == "C"

    def test_decay_reduces_old_scores(self):
        cat = StreamingCommaCategory(decay_rate=0.1)
        old_time = time.time() - 100
        new_time = time.time()
        cat.add_observation("A", old_time, [("B", 1.0)])
        # Force full recomputation by hitting 100 observations
        for i in range(99):
            cat.add_observation(f"filler_{i}", new_time, [("D", 0.0001)])
        cat.add_observation("C", new_time, [("D", 1.0)])
        # Now observation_count % 100 == 0 on next get_predictions -> full recompute
        # Increment once more to trigger recompute
        preds = cat.get_predictions(top_k=5, current_time=new_time)
        scores = {p[0]: p[1] for p in preds}
        # D (recent, accumulated) should score higher than B (old with heavy decay)
        assert scores.get("D", 0) > scores.get("B", 0)


# ---------------------------------------------------------------------------
# StreamingKanExtension
# ---------------------------------------------------------------------------

class TestStreamingKanExtension:
    def test_observe_and_predict(self):
        kan = StreamingKanExtension(decay_rate=0.0)
        t = time.time()
        kan.observe("NMC811", t, [("LFP", 0.7), ("LCO", 0.5)])
        preds = kan.predict(top_k=3)
        assert len(preds) == 2
        assert preds[0]["target"] in ("LFP", "LCO")
        assert preds[0]["score"] > 0

    def test_event_count(self):
        kan = StreamingKanExtension()
        t = time.time()
        kan.observe("A", t, [("B", 0.5)])
        kan.observe("C", t, [("D", 0.3)])
        assert kan.get_event_count() == 2

    def test_comma_category_size(self):
        kan = StreamingKanExtension()
        t = time.time()
        kan.observe("A", t, [("B", 0.5), ("C", 0.3)])
        assert kan.get_comma_category_size() == 2

    def test_predict_includes_metadata(self):
        kan = StreamingKanExtension(decay_rate=0.0)
        t = time.time()
        kan.observe("A", t, [("B", 0.8)])
        preds = kan.predict()
        assert len(preds) == 1
        p = preds[0]
        assert "target" in p
        assert "score" in p
        assert "confidence" in p
        assert "n_contributors" in p
        assert "supporting_evidence" in p

    def test_multi_step_forecast_without_fn(self):
        kan = StreamingKanExtension(decay_rate=0.0)
        t = time.time()
        kan.observe("A", t, [("B", 0.8)])
        forecast = kan.multi_step_forecast(steps=3)
        # Without composable_fn, should only get step 1
        assert len(forecast) == 1
        assert forecast[0][0]["step"] == 1

    def test_multi_step_forecast_with_fn(self):
        kan = StreamingKanExtension(decay_rate=0.0)
        t = time.time()
        kan.observe("A", t, [("B", 0.8)])

        def composable_fn(source_id):
            graph = {
                "B": [("C", 0.7)],
                "C": [("D", 0.6)],
            }
            return graph.get(source_id, [])

        forecast = kan.multi_step_forecast(steps=3, composable_fn=composable_fn)
        assert len(forecast) >= 2

        # Confidence should decay at each step
        if len(forecast) >= 2 and forecast[0] and forecast[1]:
            assert forecast[1][0]["confidence"] <= forecast[0][0]["confidence"]

    def test_multi_step_rollback(self):
        """Hypothetical observations are rolled back after forecast."""
        kan = StreamingKanExtension(decay_rate=0.0)
        t = time.time()
        kan.observe("A", t, [("B", 0.8)])

        initial_size = kan.get_comma_category_size()

        def composable_fn(source_id):
            return [("X", 0.5)] if source_id == "B" else []

        kan.multi_step_forecast(steps=2, composable_fn=composable_fn)

        # After forecast, size should be back to initial
        assert kan.get_comma_category_size() == initial_size

    def test_prune(self):
        kan = StreamingKanExtension(decay_rate=0.0)
        old_time = time.time() - 7200
        new_time = time.time()
        kan.observe("A", old_time, [("B", 0.5)])
        kan.observe("C", new_time, [("D", 0.8)])
        kan.prune(max_age_seconds=3600)
        assert kan.get_event_count() == 1
        assert kan.get_comma_category_size() == 1


# ---------------------------------------------------------------------------
# Chemistry use case
# ---------------------------------------------------------------------------

class TestChemistryUseCases:
    def test_streaming_lab_results(self):
        """Simulate streaming lab results about material compatibility."""
        kan = StreamingKanExtension(decay_rate=0.0)
        t = time.time()

        # Lab result 1: NMC811 tested with EC -> good compatibility with LFP-type materials
        kan.observe("NMC811_EC_test", t, [
            ("NMC811_viable", 0.85),
            ("high_voltage_cathode_ok", 0.70),
        ])

        # Lab result 2: LLZO tested with Li_metal -> confirms solid-state viability
        kan.observe("LLZO_Li_test", t + 1, [
            ("solid_state_viable", 0.65),
            ("NMC811_viable", 0.40),  # indirect evidence
        ])

        preds = kan.predict(top_k=5)
        # NMC811_viable should have highest score (contributions from both)
        targets = {p["target"]: p["score"] for p in preds}
        assert "NMC811_viable" in targets
        assert targets["NMC811_viable"] > targets.get("solid_state_viable", 0)
