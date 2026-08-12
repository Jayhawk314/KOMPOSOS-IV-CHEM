# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Shared validation-status surface for the Streamlit UI.

Single source of truth for the product's per-domain accuracy + uncertainty
claims, so the feature pages cannot drift apart or over-claim.

Numbers here come ONLY from frozen audit artifacts and
``audit/dataset_registry.json`` — never from G-docs design notes (those are
Gemini analysis, not validated claims). When the audit state changes, update
this file and the pages follow automatically.

Standing rule: claims are per-domain and must show uncertainty. Never headline
one global accuracy number.

Last synced to audit state: 2026-08-12
"""

import streamlit as st

LAST_SYNCED = "2026-08-12"

# The compatibility score is now mapped to a calibrated probability via an
# isotonic calibrator fit on dev+spent diagnostics (audit/build_compatibility_
# calibration.py). Honest held-out (k-fold OOS) ECE ~0.07, down from ~0.19 raw.
CONFIDENCE_CAVEAT = (
    "Runtime pairwise probabilities use the deployed 98-row development/spent "
    "isotonic artifact (artifact OOS ECE 0.055, Brier 0.034). A broader "
    "post-squash five-fold study reports OOS ECE 0.070 and Brier 0.068; Q11 "
    "blind ECE was 0.177. These are different cohorts and procedures, not "
    "general or domain-specific validation. A displayed 0.70 is an estimated "
    "frequency on the calibration cohort, not a lab guarantee. Aggregate "
    "cell/workbench scores are not passed through this pairwise calibrator."
)

# Per-domain compatibility validation.
# Source: audit/dataset_registry.json (Q8/Q9 are spent_diagnostic) +
# HANDOFF_AND_STANDING_RULES_2026-05-29.md.
COMPATIBILITY_DOMAINS = [
    {
        "Domain": "All compatibility domains",
        "Accuracy": "Q11 blind: 63.9% of 36 evaluated; 4 no-verdicts",
        "Basis (uncertainty)": "Internally authored labels; no source identifiers",
        "State": "Q11 spent after remediation; Q12 current blind, unscored",
    },
    {
        "Domain": "Per-domain estimates",
        "Accuracy": "Not promoted to headline metrics",
        "Basis (uncertainty)": "Q8+Q9 contain 80 total pairs with uneven domain counts",
        "State": "Report pair counts with any domain slice",
    },
    {
        "Domain": "Glass (single-domain)",
        "Accuracy": "—",
        "Basis (uncertainty)": "Coverage gap: some glasses missing from DB",
        "State": "Incomplete",
    },
]

# Honest blind-claim posture from audit/dataset_registry.json v3.
BLIND_STATUS = (
    "**Q12 is the current frozen blind compatibility set and is unscored.** "
    "Q11's first run was 63.9% on 36 evaluated pairs with four no-verdicts "
    "(MCC 0.278, Brier 0.279, ECE 0.177). Its labels had no external source "
    "identifiers and were authored by the same AI assistant that worked on the "
    "code. Q11 was then used for remediation and is now spent; the post-fix "
    "69.7% is regression evidence only, with total correct unchanged at 23/40. "
    "Q10 remains sealed and unconsumed. Development 41/41 is tuned, not blind."
)

# Per-feature validation notes. Keep each one short and honest.
FEATURE_NOTES = {
    "compatibility": None,  # rendered as the full per-domain table below
    "cell_designer": (
        "The manual designer and optimizer use native cross-domain functors. The UI "
        "now reports requested-interface **coverage** and refuses a full-cell verdict "
        "when an adjacent interface has no scorer. The aggregate score is uncalibrated. "
        "The optimizer objective is theoretical cathode-active V×C under covered "
        "compatibility constraints; it does not model cycle life, safety, thermal "
        "runaway, or cost."
    ),
    "crystal_dreamer": (
        "Crystal Dreamer is an **idea generator, not a precise predictor.** A "
        "current strict leave-one-anchor-out development audit recovers 7/9 "
        "self-consistent target-property windows. This measures inverse-search "
        "coverage against the same forward predictor, not predictive accuracy or "
        "experimental recovery. In a matched spent ablation, the four-strategy "
        "union also scored 7/9, while known-material property retrieval reached "
        "8/9 within the top 25 and the compact stoichiometry grid matched 7/9 "
        "with more exact recoveries. **Added value from four-way generation is "
        "not established.** Charge-balance coverage and unassessable formulas "
        "are reported separately. The "
        "property *values* it reports are rough estimates with honest uncertainty "
        "bands — use it to **surface leads to investigate, then verify.** It does "
        "not reliably reinvent exact or unusual chemistries."
    ),
    "pfas": (
        "This flags PFAS by their **chemical structure** (the official OECD rule), "
        "so it catches even PFAS it has never seen by name. On a check it cleared "
        "**25/25 non-PFAS look-alikes** correctly and matched the **EPA's official "
        "list 99.5%** of the time; brand names and the registry are also matched. "
        "Suggested replacements are rough guides (see each evidence label), but if "
        "you list your cell's adjoining materials, each replacement is also scored "
        "for pairwise compatibility against them. A full-stack value is shown only "
        "when every requested contact is covered; otherwise coverage is explicit."
    ),
    "mof_designer": (
        "Atom-count and donor-atom constraints are **exactly enforced (100%)** — "
        "the generator never fabricates the count. Candidate quality is now scored "
        "by a **validated grounded funnel** (chemical sanity, ≥2 coordinating "
        "sites, SAscore, donor geometry, + novelty vs. known linkers): **~94% "
        "recall on held-out real synthesized linkers, AUROC ~0.88** vs. raw "
        "generator output (MOFSimplify + CoRE-MOF; see "
        "docs/MOF_LINKER_BENCHMARK_RESULTS.md). The older 5 self-graded verdicts "
        "are retained only as legacy/unvalidated. A high funnel score means "
        "'indistinguishable from real linkers on every computable axis' — **not a "
        "wet-lab synthesis guarantee.**"
    ),
    "workbench": (
        "This is a **composition-first prototype** that chains inverse design → "
        "formula-scoped PFAS screening → compatibility context → synthesis planning. "
        "The PFAS formula screen is tri-state: `ASSESSED PASS` when a valid formula "
        "cannot contain a PFAS because carbon and fluorine do not co-occur, `VETOED` "
        "for an exact registered PFAS identity, and `NOT ASSESSED` when connectivity "
        "or identity is still required. Outputs are triage candidates for screening, "
        "not lab-validated designs. " + CONFIDENCE_CAVEAT
    ),
    "advanced_workbench": (
        "A **mixed-fidelity** pipeline. The **triage phase** (inverse design) proposes "
        "candidate formulas — these are *suggestions* and can be hallucinations. A "
        "versioned local development diagnostic requested 30 Li-bearing candidates "
        "and returned 29 unique formulas in **10.860 seconds** after the PFAS-path "
        "repair. That is one local latency/functional run, not an accuracy result, "
        "service-level guarantee, or comparison with an external professional workflow. "
        "The **precision phase** adds two checks you can trust more:\n\n"
        "1. **Charge-balance veto** — a pymatgen oxidation-state feasibility check; "
        "unassessable formulas receive no verdict. This is not an independent ZFC proof.\n"
        "2. **Interface coverage check** — an uncalibrated aggregate of the native "
        "cross-domain functors that are actually available. Missing adjacent interfaces "
        "are shown and block a full-cell verdict.\n\n"
        "Formula-only PFAS status remains tri-state; C/F co-occurrence requires structure "
        "or verified identity before a PFAS-free conclusion. "
        "**Two honesty caveats on the interface check:** (a) it scores the candidate's "
        "**nearest known analog** (a proxy), *not* the novel formula itself — the further "
        "that analog sits in composition space, the weaker the signal, so the scorecard "
        "shows the **proxy distance** and flags far proxies; (b) the reference cell is "
        "**battery-only**, so non-battery candidates are not cell-scored. "
        "**Trust the vetoes more than the suggestions.**"
    ),
    "composition_predictor": (
        "Property values are **estimates by comparison to known materials**, not "
        "lab measurements or first-principles calculations. They are **rough** on "
        "unfamiliar chemistry. The current 179-material true leave-one-out audit is "
        "formation-energy MAE **0.416 eV/atom** (RMSE 0.552; median 0.340). After "
        "recalibration on 2026-07-17, deployed 50/80/95% intervals cover "
        "50/79/95% in-pool and 49/80/94% in 5-fold OOS calibration. These are "
        "model-development results, not an external blind benchmark."
    ),
    "mp_explorer": (
        "Two kinds of data on this page, kept distinct: **raw Materials Project "
        "entries are DFT-computed reference data** (real, traceable to MP IDs), "
        "while **derived crystal structures are Kan-extension estimates** "
        "interpolated from the nearest MP entries. Estimates carry a confidence "
        "and full provenance but are not themselves computed or measured structures."
    ),
    "mof_explorer": (
        "MOF property data (surface area, stability, pore size) is **literature-"
        "backed with DOIs** — verify against the cited sources. The 5-scorer "
        "suitability ranking is a **model triage signal**, not a validated "
        "prediction: use it to shortlist candidates, then check the literature."
    ),
    "synthesis_planner": (
        "Routes are **curated from published literature with citations**, not "
        "ML-generated. Scores (feasibility/cost/time/safety) are heuristic "
        "rankings. The **stoichiometric validation is a formal Z3 check**: "
        "BALANCED means an element-balanced equation exists (shown as a "
        "formal witness using allowed auxiliary species — not the cited route's "
        "mechanism, redox chemistry, or yield); UNBALANCED is a hard veto "
        "(score zeroed). Balance "
        "cannot check redox feasibility, kinetics, or phase purity. Audit: "
        "`python audit\\run_stoich_audit.py` — 24 curated routes total: 17 "
        "element-balanced, 0 unbalanced, and 7 composite/mixture routes skipped "
        "because a single-formula balance is undefined (reproduced 2026-07-17)."
    ),
}


def render_compatibility_status(expanded: bool = False) -> None:
    """Per-domain compatibility accuracy + uncertainty table."""
    import pandas as pd

    with st.expander("Accuracy & uncertainty (per domain)", expanded=expanded):
        st.dataframe(
            pd.DataFrame(COMPATIBILITY_DOMAINS),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(BLIND_STATUS)
        st.warning(CONFIDENCE_CAVEAT)
        st.caption(f"Validation state synced {LAST_SYNCED} from audit/dataset_registry.json.")


def render_feature_status(feature_key: str, expanded: bool = False) -> None:
    """Render the validation/uncertainty banner for a given feature page."""
    if feature_key == "compatibility":
        render_compatibility_status(expanded=expanded)
        return

    note = FEATURE_NOTES.get(feature_key)
    if not note:
        return
    with st.expander("Accuracy & uncertainty", expanded=expanded):
        st.markdown(note)
        st.caption(f"Validation state synced {LAST_SYNCED} from frozen audit artifacts.")


def render_global_status() -> None:
    """Landing-page per-domain validation summary (app.py)."""
    import pandas as pd

    st.subheader("Validation status (per domain, with uncertainty)")
    st.dataframe(
        pd.DataFrame(COMPATIBILITY_DOMAINS),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(BLIND_STATUS)
    st.warning(CONFIDENCE_CAVEAT)
    st.caption(
        f"Synced {LAST_SYNCED} from audit/dataset_registry.json. "
        "Other features (PFAS detection, MOF synthesizability, inverse-design "
        "candidates) are triage tools and are not yet blind-validated — each page "
        "states its own status."
    )
