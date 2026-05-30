"""Shared validation-status surface for the Streamlit UI.

Single source of truth for the product's per-domain accuracy + uncertainty
claims, so the feature pages cannot drift apart or over-claim.

Numbers here come ONLY from frozen audit artifacts and
``audit/dataset_registry.json`` — never from G-docs design notes (those are
Gemini analysis, not validated claims). When the audit state changes, update
this file and the pages follow automatically.

Standing rule: claims are per-domain and must show uncertainty. Never headline
one global accuracy number.

Last synced to audit state: 2026-05-29
"""

import streamlit as st

LAST_SYNCED = "2026-05-29"

# Confidence scores are ranking signals, not probabilities. ECE ~0.15 on the
# compatibility engine even after the polymer fix (handoff 2026-05-29).
CONFIDENCE_CAVEAT = (
    "Confidence/score values are **ranking signals for triage, not calibrated "
    "probabilities** (compatibility ECE ~0.15). Do not read a 0.80 score as an "
    "80% chance of success."
)

# Per-domain compatibility validation.
# Source: audit/dataset_registry.json (Q8/Q9 are spent_diagnostic) +
# HANDOFF_AND_STANDING_RULES_2026-05-29.md.
COMPATIBILITY_DOMAINS = [
    {
        "Domain": "Metals / ceramics / semiconductors / cross-domain",
        "Accuracy": "77–100%",
        "Basis (uncertainty)": "Q8+Q9 spent diagnostics, ~115 pairs",
        "State": "Useful triage today",
    },
    {
        "Domain": "Polymer blends",
        "Accuracy": "87.5%",
        "Basis (uncertainty)": "Q9 spent diagnostic (35/40); ECE 0.15, Brier 0.099, AUROC 0.92",
        "State": "Repaired this cycle (Flory–Huggins χc)",
    },
    {
        "Domain": "Glass (single-domain)",
        "Accuracy": "—",
        "Basis (uncertainty)": "Coverage gap: some glasses missing from DB",
        "State": "Incomplete",
    },
]

# Honest blind-claim posture (audit/dataset_registry.json: current_blind_version is null).
BLIND_STATUS = (
    "**No dataset is currently blind.** Q2–Q9 are spent diagnostics (used for "
    "error analysis / calibration), not fresh blind claims. Q10 is the sealed "
    "final exam — its labels are hashed and held out, and it has **not been "
    "scored** yet. The development set is 41/41 (Brier 0.095) but it is *tuned*, "
    "so it is not a blind result."
)

# Per-feature validation notes. Keep each one short and honest.
FEATURE_NOTES = {
    "compatibility": None,  # rendered as the full per-domain table below
    "cell_designer": (
        "Interface scores come from the **cross-domain compatibility engine** "
        "(77–100% on Q8+Q9 spent diagnostics). The bottleneck and overall score "
        "are triage signals for the weakest interface. " + CONFIDENCE_CAVEAT
    ),
    "crystal_dreamer": (
        "Inverse design is an **unvalidated screening / triage tool**: candidates "
        "are ranked by predicted-property fit, not experimentally validated. "
        "Property predictions carry the Composition Predictor's uncertainty tiers; "
        "treat low-evidence tiers as discovery leads, not answers. " + CONFIDENCE_CAVEAT
    ),
    "pfas": (
        "PFAS detection uses a curated registry plus brand/keyword heuristics. "
        "**Registry hits are authoritative; heuristic and unknown hits require "
        "manual review.** Detection accuracy on a blind bill-of-materials has not "
        "yet been validated, and replacement scores are triage signals (see "
        "evidence tiers per row)."
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
        "PFAS screening → compatibility context → synthesis planning. Crystal- and "
        "MOF-specific pipeline modes are planned next. Outputs are triage "
        "candidates for screening, not lab-validated designs. " + CONFIDENCE_CAVEAT
    ),
    "composition_predictor": (
        "Property predictions are **interpolations over known materials** (Kan "
        "extension + Dempster–Shafer fusion), not first-principles calculations. "
        "Each property carries an **evidence tier** and, for formation energy, a "
        "**calibrated uncertainty interval**. Use the **Leave-One-Out test** below "
        "to see honest blind error on materials the engine is forced to forget. "
        "Treat low-evidence tiers as discovery leads."
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
