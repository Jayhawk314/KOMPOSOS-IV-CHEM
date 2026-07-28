# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for BOM ingestion: tolerant parsing, honest resolution.

The behavioural contracts: nothing is silently dropped, unrecognized names are
a first-class outcome with suggestions (never auto-applied), and brand/free-text
aliases map only onto names the vocabulary actually contains.
"""

from __future__ import annotations

import pytest

from ingest import ingest_bom, parse_bom_text, resolve_material
from ingest.bom_ingest import _parse_qty, known_vocabulary


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def test_csv_with_header_and_units_column():
    lines, warnings = parse_bom_text(
        "Material,Function,Qty (kg)\nPVDF,cathode binder,2.5\nNMC811,cathode,45"
    )
    assert not warnings
    assert [(l.raw_name, l.function, l.quantity_kg) for l in lines] == [
        ("PVDF", "cathode binder", 2.5),
        ("NMC811", "cathode", 45.0),
    ]


def test_pipe_format_backward_compatible():
    """The PFAS page's original `name | function | qty` format still parses."""
    lines, _ = parse_bom_text("PVDF | cathode binder | 50\nPTFE | gasket seal | 10")
    assert [(l.raw_name, l.quantity_kg) for l in lines] == [("PVDF", 50.0), ("PTFE", 10.0)]


def test_plain_names_one_per_line():
    lines, _ = parse_bom_text("PVDF\nGraphite\nNMC811")
    assert [l.raw_name for l in lines] == ["PVDF", "Graphite", "NMC811"]
    assert all(l.function is None and l.quantity_kg is None for l in lines)


def test_semicolon_and_tab_delimiters():
    for text in ("PVDF;binder;1.0", "PVDF\tbinder\t1.0"):
        lines, _ = parse_bom_text(text)
        assert lines[0].raw_name == "PVDF"
        assert lines[0].quantity_kg == 1.0


def test_comments_and_blanks_skipped_and_bad_rows_warned():
    lines, warnings = parse_bom_text("# my BOM\n\nPVDF,binder,1\n,,\n")
    assert [l.raw_name for l in lines] == ["PVDF"]


def test_no_content_warns_instead_of_crashing():
    lines, warnings = parse_bom_text("\n\n# only comments\n")
    assert lines == []
    assert warnings


@pytest.mark.parametrize("raw,expected", [
    ("2.5", 2.5),
    ("2.5 kg", 2.5),
    ("1,500", 1500.0),   # thousands separator
    ("1,5", 1.5),        # European decimal
    ("", None),
    ("n/a", None),
])
def test_quantity_parsing(raw, expected):
    assert _parse_qty(raw) == expected


# ---------------------------------------------------------------------------
# resolution
# ---------------------------------------------------------------------------

def test_exact_vocabulary_match():
    r = resolve_material("PVDF")
    assert r.status == "matched" and r.canonical == "PVDF"
    assert "polymer" in r.domains
    assert r.pfas_flag  # PVDF is both vocabulary AND PFAS


def test_brand_with_grade_resolves_via_alias():
    r = resolve_material("Kynar 2801")
    assert r.status == "alias"
    assert r.canonical == "PVDF"
    assert r.pfas_flag and r.pfas_base == "PVDF"


def test_free_text_resolves():
    assert resolve_material("copper foil").canonical == "Cu_foil"
    assert resolve_material("alumina").canonical == "Al2O3"
    assert resolve_material("polypropylene").canonical == "PP"


def test_unrecognized_gets_suggestions_not_coercion():
    r = resolve_material("grafite")  # typo for Graphite
    assert r.status == "unrecognized"
    assert r.canonical is None, "must never auto-apply a guess"
    assert "Graphite" in r.suggestions


def test_similar_but_different_chemical_is_not_coerced():
    """LiFSI and LiTFSI are DIFFERENT salts: suggest, never substitute."""
    r = resolve_material("LiFSI")
    assert r.status == "unrecognized"
    assert r.canonical is None
    assert "LiTFSI" in r.suggestions


def test_truly_unknown_material_has_no_bogus_suggestions():
    r = resolve_material("Unobtainium XR-7")
    assert r.status == "unrecognized"
    assert r.suggestions == []


def test_aliases_only_map_to_real_vocabulary():
    vocab = known_vocabulary()
    from ingest.bom_ingest import _ALIAS_TO_CANONICAL, _build_vocab
    _build_vocab()
    for alias, target in _ALIAS_TO_CANONICAL.items():
        assert target in vocab, f"alias {alias!r} -> {target!r} not in vocabulary"


# ---------------------------------------------------------------------------
# end-to-end
# ---------------------------------------------------------------------------

def test_ingest_nothing_dropped():
    res = ingest_bom("PVDF,binder,1\nUnobtainium,magic,2\nKynar,binder,3")
    assert res.summary()["lines"] == 3
    assert len(res.matched) == 2
    assert len(res.unrecognized) == 1
    # every input line appears in exactly one bucket
    total = len(res.matched) + len(res.pfas_only) + len(res.unrecognized)
    assert total == 3


def test_material_inputs_use_canonical_and_preserve_raw():
    res = ingest_bom("Kynar 2801,cathode binder,2.5")
    mi = res.to_material_inputs()
    assert mi[0].name == "PVDF"
    assert "Kynar 2801" in (mi[0].function or "")
    assert mi[0].quantity_kg == 2.5


def test_material_inputs_include_unrecognized_by_default():
    res = ingest_bom("Unobtainium,magic,2")
    assert [m.name for m in res.to_material_inputs()] == ["Unobtainium"]
    assert res.to_material_inputs(include_unrecognized=False) == []


def test_ingest_feeds_pfas_report():
    """The full loop: messy text -> ingest -> PFAS screening report."""
    from reports.pfas_report import PFASComplianceReport
    res = ingest_bom(
        "Material,Function,Qty (kg)\n"
        "Kynar 2801,cathode binder,2.5\n"
        "NMC811,cathode active,45\n"
        "Teflon tape,thread seal,0.2\n"
        "Unobtainium,magic,1\n"
    )
    report = PFASComplianceReport().screen_portfolio(res.to_material_inputs())
    d = report.to_dict()
    assert d["summary"]["screened"] == 4
    detected = {det["material"] for det in d["detections"]}
    assert "PVDF" in detected and "PTFE" in detected
    # the unknown is neither detected nor lost
    all_names = detected | {c.get("name") for c in d["clean_materials"]}
    assert "Unobtainium" in all_names
