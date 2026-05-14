#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
KOMPOSOS-IV-PHARM Streamlit Web Frontend.

Wraps the triage CLI into an interactive web app for drug repurposing demos.

Usage:
    pip install streamlit
    streamlit run app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validation.repurposing_benchmark import (
    DB_PATH,
    drug_disease_pairs,
    load_full_typed_view,
    make_strategies,
    score_pair,
)
from validation.trace_prediction import _build_provenance_index, trace_pair
from validation.triage import (
    _label_for_pair,
    _provenance_fraction,
    self_check,
    triage_disease,
    triage_drug,
)


# ── Cache heavy loads ────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading knowledge graph...")
def load_graph():
    category, _ = load_full_typed_view(DB_PATH)
    drugs, diseases, positives = drug_disease_pairs(category)
    strategies = make_strategies(category)
    provenance_index = _build_provenance_index(DB_PATH)
    n_objects = len(category.objects())
    n_morphisms = len(category.morphisms())
    check_recovered, check_total = self_check(
        category, drugs, diseases, positives
    )
    return {
        "category": category,
        "drugs": drugs,
        "diseases": diseases,
        "positives": positives,
        "strategies": strategies,
        "provenance_index": provenance_index,
        "n_objects": n_objects,
        "n_morphisms": n_morphisms,
        "n_positives": len(positives),
        "check_recovered": check_recovered,
        "check_total": check_total,
    }


# ── Page config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="KOMPOSOS-IV-PHARM",
    page_icon="\u2695",
    layout="wide",
)


# ── Sidebar ──────────────────────────────────────────────────────────

st.sidebar.title("KOMPOSOS-IV-PHARM")
st.sidebar.caption("Categorical Drug Repurposing")

mode = st.sidebar.radio(
    "Mode",
    ["Disease-first", "Drug-first", "Pair detail", "About"],
)

g = load_graph()

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**Graph**: {g['n_objects']} objects, {g['n_morphisms']} morphisms\n\n"
    f"**Positives**: {g['n_positives']} FDA-approved\n\n"
    f"**Self-check**: {g['check_recovered']}/{g['check_total']} recoverable"
)


# ── Helpers ──────────────────────────────────────────────────────────

def render_results_table(results):
    """Show ranked results as a streamlit table."""
    rows = []
    for r in results:
        rows.append({
            "Rank": r["rank"],
            "Drug": r["drug"],
            "Disease": r["disease"],
            "Score": round(r["score"], 3),
            "Label": r["label"],
            "Mech. Paths": r["n_chains"],
            "Cited Edges": f"{r['cited_edges']}/{r['total_edges']}"
            if r["total_edges"] > 0 else "-",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_detail(entry):
    """Show detailed evidence for one candidate."""
    label_color = "green" if entry["label"] == "APPROVED" else "orange"
    st.markdown(
        f"### {entry['drug']} \u2192 {entry['disease']}  "
        f"&nbsp; :{label_color}[{entry['label']}]"
    )
    st.metric("Score", f"{entry['score']:.3f}")

    if entry["votes"]:
        st.markdown("**Strategy Votes**")
        vote_cols = st.columns(min(len(entry["votes"]), 4))
        for i, (name, conf) in enumerate(entry["votes"]):
            vote_cols[i % len(vote_cols)].metric(name, f"{conf:.2f}")

    if entry["chains"]:
        st.markdown("**Mechanistic Evidence Chains**")
        for i, chain in enumerate(entry["chains"], 1):
            parts = [chain["edges"][0]["source"]]
            for edge in chain["edges"]:
                parts.append(f"\u2192 {edge['target']}")
            path_str = " ".join(parts)

            with st.expander(f"Path {i}: {path_str}"):
                for edge in chain["edges"]:
                    prov = edge.get("provenance", "unknown")
                    prov_display = prov if prov != "unknown" else "uncited"
                    st.markdown(
                        f"- **{edge['source']}** -{edge['relation']}-> "
                        f"**{edge['target']}** "
                        f"(conf: {edge['confidence']:.2f}, {prov_display})"
                    )

    cited = entry["cited_edges"]
    total = entry["total_edges"]
    if total > 0:
        st.progress(cited / total, text=f"Provenance: {cited}/{total} edges cited")


# ── Disease-first ────────────────────────────────────────────────────

if mode == "Disease-first":
    st.title("Rank drugs for a disease")
    disease = st.selectbox("Select disease", g["diseases"])
    top_n = st.slider("Top N", 5, len(g["drugs"]), 20)

    if st.button("Run triage", type="primary"):
        with st.spinner("Scoring all drugs..."):
            results = triage_disease(
                g["category"], g["strategies"], disease, g["positives"],
                g["provenance_index"], top_n=top_n,
            )
        render_results_table(results)

        st.markdown("---")
        st.subheader("Candidate Details")
        not_approved = [r for r in results if r["label"] == "NOT_APPROVED"]
        for entry in not_approved[:5]:
            render_detail(entry)
            st.markdown("---")


# ── Drug-first ───────────────────────────────────────────────────────

elif mode == "Drug-first":
    st.title("Rank diseases for a drug")
    drug = st.selectbox("Select drug", g["drugs"])

    if st.button("Run triage", type="primary"):
        with st.spinner("Scoring all diseases..."):
            results = triage_drug(
                g["category"], g["strategies"], drug, g["positives"],
                g["provenance_index"], top_n=len(g["diseases"]), show_all=True,
            )
        render_results_table(results)

        st.markdown("---")
        st.subheader("Top Predictions")
        for entry in results[:5]:
            render_detail(entry)
            st.markdown("---")


# ── Pair detail ──────────────────────────────────────────────────────

elif mode == "Pair detail":
    st.title("Inspect a specific drug-disease pair")
    col1, col2 = st.columns(2)
    drug = col1.selectbox("Drug", g["drugs"])
    disease = col2.selectbox("Disease", g["diseases"])

    if st.button("Analyze pair", type="primary"):
        with st.spinner("Analyzing..."):
            score, votes = score_pair(g["strategies"], drug, disease)
            trace = trace_pair(
                g["category"], drug, disease,
                g["strategies"], g["provenance_index"],
            )
            label = _label_for_pair((drug, disease), g["positives"])
            cited, total_edges = _provenance_fraction(trace["chains"])
            entry = {
                "rank": 1,
                "drug": drug,
                "disease": disease,
                "score": score,
                "label": label,
                "votes": votes,
                "n_chains": trace["n_chains"],
                "chains": trace["chains"],
                "cited_edges": cited,
                "total_edges": total_edges,
            }
        render_detail(entry)


# ── About ────────────────────────────────────────────────────────────

elif mode == "About":
    st.title("About KOMPOSOS-IV-PHARM")

    st.markdown("""
KOMPOSOS-IV-PHARM is a **categorical AI runtime** for drug repurposing. It uses
category theory (Kan extensions, Yoneda lemma, topos logic, fibrations) to
predict which existing drugs might treat diseases they weren't originally
approved for.

### How It Works

1. **Knowledge Graph**: 78 drugs, 366 proteins, 20 diseases, 1260 edges --
   all with literature citations (PMIDs + ChEMBL IDs)
2. **7 Inference Strategies**: Each uses a different mathematical lens
   (composition, Kan extensions, Yoneda patterns, topos logic, structural holes,
   fibration lifts, type heuristics)
3. **Scoring**: Average strategy confidences + path bonus for mechanistic
   Drug->Protein->Disease chains
4. **Evidence**: Every prediction comes with traceable mechanistic paths and
   literature citations

### Validation

| Metric | Value |
|--------|-------|
| LOOCV AUROC | 0.974 [95% CI: 0.965-0.983] |
| Positives | 44 FDA-approved oncology indications |
| Strongest baseline | shortest_path 0.931 (margin: +0.043) |
| Provenance | 1260/1260 morphisms cited (100%) |
| ClinicalTrials.gov cross-check | 63% IN_TRIALS, 30% PRECLINICAL, 7% NOVEL |

### Limitations

- **Research prototype**: Not a clinical decision support system
- **Oncology only**: 20 cancer types currently
- **Small graph**: 1143 objects vs 47k+ in published systems like Rephetio
- **Open-world negatives**: Unlabeled pairs are unknowns, not confirmed negatives
- **Modest margin**: +0.043 AUROC over shortest-path baseline

### Citation

Hawkins, J.R. (2026). KOMPOSOS-IV-PHARM: Categorical Drug Repurposing.
Apache 2.0 / Commercial dual license.
""")
