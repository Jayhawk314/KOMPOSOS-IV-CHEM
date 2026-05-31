"""
PFAS BOM Triage CLI  (go-to-market / design-partner tool)
=========================================================

The "send me your bill of materials, I'll run the triage" deliverable.

Given a BOM as CSV, this:
  1. screens every line for PFAS (exact / brand / CAS / OECD-structural via the
     real `pfas_bridge.PFASComplianceChecker`),
  2. for each PFAS line, ranks PFAS-free replacements **against the rest of the
     BOM as the cell/stack** using `find_replacements_for_cell`, surfacing the
     weakest interface (the *bottleneck*) — i.e. "PFAS-free AND compatible with
     YOUR cell", not just "not PFAS",
  3. emits an auditable Markdown report + a machine-readable JSON artifact.

This is the CURRENT-code capability. The older docs
(`docs/BOM_AUDIT_FORMATS_AND_PROCEDURES.md`, `docs/BOM_SCREENING_RUBRIC.md`)
predate the cell-aware replacement functions and the corrected 2026/27 deadlines
— see `go_to_market/pfas/COMPLIANCE_CLOCK_2026.md`.

HONEST FRAMING (kept in the report header): this is a *triage accelerator and an
auditable screening aid* — NOT a compliance certification and NOT a substitute
for analytical lab testing (EPA 533/537.1, TOF/TOP) or bench qualification.

Usage:
    python go_to_market/pfas/bom_triage.py --bom go_to_market/pfas/example_bom.csv \
        --client "Acme Battery Co"

CSV columns (header row required; only `material_name` is mandatory):
    material_name      e.g. PVDF              (aliases accepted: material, name)
    function           e.g. cathode binder    (drives use-case scoring)
    cas_number         e.g. 24937-79-9        (optional, improves detection)
    quantity, unit     optional, carried into the report
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, List, Optional

# --- make the repo root importable regardless of where we're invoked from ----
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pfas_bridge.compliance_checker import PFASComplianceChecker  # noqa: E402
from pfas_bridge.replacement_scorer import (  # noqa: E402
    UseCase,
    find_replacements_for_cell,
)

# Quiet RDKit's SMILES-parse warnings (the checker probes plain names like
# "Carbon Black" against the structural rule; failures there are expected).
try:  # pragma: no cover
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")
except Exception:
    pass


# --- corrected compliance clock (source of truth: COMPLIANCE_CLOCK_2026.md) ---
# Hard-coded here so the report never silently drifts back to the stale
# "EU ban Aug 25 2026" claim that lives in the older audit docs.
COMPLIANCE_CLOCK: List[Dict[str, str]] = [
    {"jurisdiction": "US – Minnesota (Amara's Law)",
     "milestone": "Manufacturer reporting deadline",
     "date": "2026-09-15 (90-day ext. possible to 2026-12-14); category bans already live, broad ban 2032"},
    {"jurisdiction": "US – New Mexico",
     "milestone": "Product reports + labeling; phased bans",
     "date": "Reports/labeling 2027-01-01; phased bans 2027-01-01 & 2028-01-01"},
    {"jurisdiction": "US – EPA TSCA §8(a)(7)",
     "milestone": "PFAS manufacturing/import reporting (IN FLUX)",
     "date": "starts 60 days after a forthcoming final rule, or 2027-01-31, whichever is first"},
    {"jurisdiction": "EU – REACH universal restriction",
     "milestone": "SEAC final opinion → Commission → application",
     "date": "final opinion ~end-2026; Commission adoption unlikely before Q3-2027; would NOT apply before 2029"},
]

# function-keyword -> UseCase  (mirrors docs/BOM_SCREENING_RUBRIC.md §2.3)
_USE_CASE_KEYWORDS = [
    (("binder",), UseCase.BATTERY_BINDER),
    (("gasket", "seal", "o-ring", "oring"), UseCase.SEAL_GASKET),
    (("separator", "membrane"), UseCase.MEMBRANE),
    (("wire", "insulation", "cable", "jacket"), UseCase.WIRE_INSULATION),
    (("non-stick", "nonstick", "release coat"), UseCase.NON_STICK_COATING),
    (("liner", "tank", "container"), UseCase.CHEMICAL_RESISTANT_LINER),
]


def _use_case_for(function: str) -> UseCase:
    f = (function or "").strip().lower()
    for keywords, uc in _USE_CASE_KEYWORDS:
        if any(k in f for k in keywords):
            return uc
    return UseCase.GENERAL


def _pct(x: Optional[float]) -> str:
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else "n/a"


# --------------------------------------------------------------------------- #
# BOM loading
# --------------------------------------------------------------------------- #
def load_bom(path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row = { (k or "").strip().lower(): (v or "").strip() for k, v in raw.items() }
            name = row.get("material_name") or row.get("material") or row.get("name")
            if not name:
                continue
            rows.append({
                "material_name": name,
                "function": row.get("function", ""),
                "cas_number": row.get("cas_number", ""),
                "quantity": row.get("quantity", ""),
                "unit": row.get("unit", ""),
            })
    return rows


# --------------------------------------------------------------------------- #
# Core triage
# --------------------------------------------------------------------------- #
def run_triage(
    bom: List[Dict[str, str]],
    client: str,
    resolve_unknown: bool = True,
) -> Dict[str, Any]:
    checker = PFASComplianceChecker(resolve_unknown=resolve_unknown)

    # --- Pass 1: classify every line (PFAS or not) ---------------------------
    entries: List[Dict[str, Any]] = []
    for row in bom:
        name = row["material_name"]
        use_case = _use_case_for(row["function"])
        result = checker.check(name, use_case=use_case)
        entries.append({
            "row": row, "name": name, "use_case": use_case, "result": result,
        })

    # The "cell" a replacement must live in = the materials that will REMAIN,
    # i.e. the clean lines. Other detected-PFAS lines are themselves leaving, so
    # scoring against them would be misleading.
    clean_cell = [e["name"] for e in entries if not e["result"].is_pfas]

    materials_out: List[Dict[str, Any]] = []
    pfas_lines: List[Dict[str, Any]] = []

    for e in entries:
        name, use_case, result = e["name"], e["use_case"], e["result"]
        row = e["row"]
        record: Dict[str, Any] = {
            "material_name": name,
            "function": row["function"],
            "use_case": use_case.value,
            "quantity": row["quantity"],
            "unit": row["unit"],
            "is_pfas": result.is_pfas,
            "detection_tier": result.detection_tier,
            "pfas_category": result.pfas_category,
            "urgency": result.urgency,
            "regulations_violated": result.regulations_violated,
        }

        if result.is_pfas:
            key = None
            if result.pfas_substance is not None:
                key = result.pfas_substance.abbreviation
            elif result.resolved_base:
                key = result.resolved_base

            ranked: List[Dict[str, Any]] = []     # compatibility-evaluated
            no_data: List[Dict[str, Any]] = []    # no interface could be scored
            if key:
                for item in find_replacements_for_cell(key, clean_cell, use_case=use_case):
                    cand = item["candidate"]
                    entry = {
                        "name": cand.name,
                        "standalone_quality": round(cand.overall_score, 3),
                        "bottleneck_material": item["bottleneck_material"],
                        "bottleneck_calibrated": item["bottleneck_calibrated"],
                        "bottleneck_viable": item["bottleneck_viable"],
                        "interfaces_evaluated": item["n_evaluated"],
                        "combined_rank": item["combined_rank"],
                        "interfaces": {
                            m: {"calibrated": v["calibrated"], "viable": v["viable"],
                                "evaluated": v["evaluated"]}
                            for m, v in item["interfaces"].items()
                        },
                        "limitations": cand.limitations,
                    }
                    (ranked if item["n_evaluated"] > 0 else no_data).append(entry)

            # Honest ordering: evaluated candidates by worst-interface (bottleneck)
            # first — "no data" never outranks a real evaluation.
            ranked.sort(
                key=lambda r: (r["bottleneck_calibrated"] if r["bottleneck_calibrated"]
                               is not None else -1.0, r["standalone_quality"]),
                reverse=True,
            )
            no_data.sort(key=lambda r: r["standalone_quality"], reverse=True)

            record["replacement_key"] = key
            record["cell_clean"] = clean_cell
            record["replacements_ranked"] = ranked
            record["replacements_no_interface_data"] = no_data
            pfas_lines.append(record)

        materials_out.append(record)

    priority = {"critical": 4, "high": 3, "moderate": 2, "low": 1, "none": 0}
    max_urgency = max(
        (m["urgency"] for m in materials_out),
        key=lambda u: priority.get(u, 0),
        default="none",
    )

    return {
        "client": client,
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "screened": len(materials_out),
            "pfas_detected": len(pfas_lines),
            "clean": sum(1 for m in materials_out if not m["is_pfas"]),
            "max_urgency": max_urgency,
        },
        "compliance_clock": COMPLIANCE_CLOCK,
        "materials": materials_out,
        "disclaimer": (
            "Triage accelerator and auditable screening aid — NOT a compliance "
            "certification and NOT a substitute for analytical lab testing "
            "(EPA 533/537.1, TOF/TOP) or bench qualification. Compatibility values "
            "are calibrated probabilities (isotonic, out-of-sample ECE ~0.07); a "
            "70% means roughly 7 in 10 such pairs are compatible. Any replacement "
            "must be pilot-tested in your specific application before production."
        ),
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_markdown(report: Dict[str, Any]) -> str:
    s = report["summary"]
    L: List[str] = []
    L.append(f"# PFAS BOM Triage — {report['client']}")
    L.append("")
    L.append(f"_Generated {report['generated_at']} · KOMPOSOS-IV-CHEM `pfas_bridge`_")
    L.append("")
    L.append(f"> **{report['disclaimer']}**")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append(f"- Materials screened: **{s['screened']}**")
    L.append(f"- PFAS detected: **{s['pfas_detected']}**")
    L.append(f"- Clean: **{s['clean']}**")
    L.append(f"- Highest urgency: **{s['max_urgency'].upper()}**")
    L.append("")

    L.append("## Compliance clock (corrected, sourced)")
    L.append("")
    L.append("| Jurisdiction | Milestone | Timing |")
    L.append("|---|---|---|")
    for c in report["compliance_clock"]:
        L.append(f"| {c['jurisdiction']} | {c['milestone']} | {c['date']} |")
    L.append("")
    L.append("_No single \"EU ban Aug 2026\" date exists; see "
             "`go_to_market/pfas/COMPLIANCE_CLOCK_2026.md` for sources._")
    L.append("")

    pfas = [m for m in report["materials"] if m["is_pfas"]]
    if not pfas:
        L.append("## PFAS findings")
        L.append("")
        L.append("No PFAS detected in this BOM. ✅")
        return "\n".join(L)

    L.append("## PFAS findings & cell-compatible replacements")
    L.append("")
    for m in pfas:
        L.append(f"### {m['material_name']}  ·  urgency: **{m['urgency'].upper()}**")
        L.append("")
        meta = [f"detection: `{m['detection_tier']}`",
                f"category: {m['pfas_category']}",
                f"use-case: `{m['use_case']}`"]
        if m.get("function"):
            meta.append(f"function: {m['function']}")
        L.append("- " + " · ".join(meta))
        if m.get("regulations_violated"):
            for r in m["regulations_violated"]:
                L.append(f"  - ⚠️ {r.get('jurisdiction')}: {r.get('status')} "
                         f"({r.get('effective_date') or 'no date'}) — {r.get('description','')}")
        L.append("")

        ranked = m.get("replacements_ranked") or []
        no_data = m.get("replacements_no_interface_data") or []
        n_cell = len(m["cell_clean"])

        if not ranked and not no_data:
            L.append("- _No curated replacement set for this substance/use-case — "
                     "manual review (request SDS)._")
            L.append("")
            continue

        if ranked:
            L.append(f"Replacements scored against the **clean cell** "
                     f"({n_cell} materials that remain). **Bottleneck** = weakest "
                     f"interface; ranked worst-interface-first (a low bottleneck is "
                     f"disqualifying however good the standalone score).")
            L.append("")
            L.append("| Rank | Replacement | Standalone quality | Cell bottleneck | "
                     "Bottleneck compat | Interfaces scored |")
            L.append("|---|---|---|---|---|---|")
            for i, r in enumerate(ranked, 1):
                L.append(
                    f"| {i} | **{r['name']}** | {r['standalone_quality']:.2f} | "
                    f"{r['bottleneck_material'] or '—'} | "
                    f"{_pct(r['bottleneck_calibrated'])} | "
                    f"{r['interfaces_evaluated']}/{n_cell} |"
                )
            L.append("")

        if no_data:
            names = ", ".join(f"{r['name']} (q={r['standalone_quality']:.2f})"
                              for r in no_data)
            L.append(f"_Insufficient interface data — manual review (not in the "
                     f"compatibility registry, so no cell interface could be scored): "
                     f"{names}._")
            L.append("")

        if not ranked:
            continue
        # interface detail for the top compatibility-evaluated candidate
        top = ranked[0]
        scored = {mat: e for mat, e in top["interfaces"].items() if e["evaluated"]}
        if scored:
            L.append(f"<details><summary>Interface detail — top pick "
                     f"<b>{top['name']}</b></summary>")
            L.append("")
            L.append("| Adjoining material | Calibrated compatibility | Viable |")
            L.append("|---|---|---|")
            for mat, e in scored.items():
                L.append(f"| {mat} | {_pct(e['calibrated'])} | "
                         f"{'yes' if e['viable'] else 'no' if e['viable'] is not None else '—'} |")
            L.append("")
            L.append("</details>")
            L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="PFAS BOM triage (cell-aware replacements)")
    ap.add_argument("--bom", required=True, help="path to BOM CSV")
    ap.add_argument("--client", default="Design Partner", help="client/company name for the report")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "out"),
                    help="output directory")
    ap.add_argument("--no-resolve", action="store_true",
                    help="disable PubChem name->SMILES resolution (offline / faster)")
    args = ap.parse_args(argv)

    try:  # Windows consoles default to cp1252; the report uses unicode.
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    bom = load_bom(args.bom)
    if not bom:
        print(f"No materials found in {args.bom}", file=sys.stderr)
        return 1

    report = run_triage(bom, client=args.client, resolve_unknown=not args.no_resolve)
    md = render_markdown(report)

    os.makedirs(args.out, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.join(args.out, f"triage_{stamp}")
    with open(base + ".md", "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(md)
    print(f"\n[written] {base}.md\n[written] {base}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
