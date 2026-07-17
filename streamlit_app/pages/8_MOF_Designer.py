"""MOF Linker Designer -- generate novel ligands with exact atom counts."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.validation_status import render_feature_status

st.set_page_config(page_title="MOF Linker Designer", page_icon="@", layout="wide")
st.title("MOF Linker Designer")
render_login_sidebar()

st.markdown(
    "Design novel organic ligands for Metal-Organic Frameworks. "
    "Specify an exact atom count and get back candidates with exact-count "
    "constraints enforced."
)
render_feature_status("mof_designer")

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
try:
    from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec
    from mof_bridge.mp_mof_loader import MOFLinkerCache
    _MOF_OK = True
except ImportError:
    _MOF_OK = False

try:
    from mof_bridge.benchmark.scorer import score_linker, is_available as _funnel_is_available
    _FUNNEL_OK = _funnel_is_available()
except Exception:
    _FUNNEL_OK = False

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
    _RDK = True
except ImportError:
    _RDK = False

if not _MOF_OK:
    st.error("MOF bridge not available. `pip install rdkit mp-api pymatgen`")
    st.stop()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _formula(smi):
    if not _RDK:
        return "?"
    m = Chem.MolFromSmiles(smi)
    return rdMolDescriptors.CalcMolFormula(m) if m else "?"

def _mw(smi):
    if not _RDK:
        return 0.0
    m = Chem.MolFromSmiles(smi)
    return round(Descriptors.MolWt(m), 1) if m else 0.0

def _heavy(smi):
    if not _RDK:
        return 0
    m = Chem.MolFromSmiles(smi)
    return m.GetNumHeavyAtoms() if m else 0

def _count_donor_atoms(smi, symbol):
    """Count atoms of a given element in a SMILES string."""
    if not _RDK:
        return 0
    m = Chem.MolFromSmiles(smi)
    if not m:
        return 0
    return sum(1 for a in m.GetAtoms() if a.GetSymbol() == symbol)

def _verdict_icon(v):
    return {"AGREE": "[OK]", "HOLLOW": "[??]", "ORPHAN": "[?]", "REJECT": "[X]"}.get(v, "?")

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

st.subheader("What do you want?")

col1, col2 = st.columns(2)

with col1:
    exact_atoms = st.number_input(
        "Exact heavy atom count",
        min_value=5, max_value=60, value=22, step=1,
        help="How many non-hydrogen atoms? Default: 22 (common for MOF linker design)."
    )
    n_candidates = st.slider(
        "Candidates to generate", 20, 500, 100, step=10,
        help="More candidates = more chances to find good ones, but slower."
    )

with col2:
    app_map = {
        "CO2 Capture": "breath_VOC_sensing",
        "Gas Storage / Separation": "food_safety",
        "Catalysis": "PFAS_detection",
        "Sensing (VOC, gas)": "breath_VOC_sensing",
        "General MOF Design": "custom",
    }
    app_label = st.selectbox("Application", list(app_map.keys()), index=0)
    application = app_map[app_label]

    donor_options = {"Nitrogen (N)": "N", "Oxygen (O)": "O", "Sulfur (S)": "S"}
    donor_labels = st.multiselect(
        "Required donor atoms (coordinating atoms)",
        list(donor_options.keys()),
        default=["Nitrogen (N)"],
        help="Filter results to only show ligands containing these elements."
    )
    required_donors = [donor_options[d] for d in donor_labels]

with st.expander("Advanced"):
    all_elements = ["H", "B", "C", "N", "O", "F", "Si", "P", "S", "Cl", "Br", "I"]
    exclude = st.multiselect(
        "Exclude elements", all_elements, default=[],
        help="Remove candidates containing these elements."
    )
    require_all_agree = st.checkbox(
        "Require all 5 legacy verdicts AGREE",
        value=False,
        help=(
            "Legacy categorical descriptors are unvalidated extras for novel linkers. "
            "The grounded funnel shown in results is the benchmarked screen."
        ),
    )
    allow_hollow = st.checkbox("Allow legacy HOLLOW verdicts (exploratory)", value=False)

with st.expander("Directed Generation Controls (steer the search)"):
    st.caption(
        "By default the generator explores randomly. These controls turn it from a "
        "'slot machine' into a 'microscope' — lock onto one molecule, bias the "
        "strategy mix, or force specific functional groups onto every candidate."
    )

    st.markdown("**Strategy mix** — how the generator builds each candidate.")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        w_sub = st.slider(
            "Functional-group substitution", 0.0, 1.0, 0.5, step=0.05,
            help="Swap groups (–OH, –NH2, –F, …) on an existing backbone. Keeps the skeleton, varies decoration."
        )
    with sc2:
        w_mod = st.slider(
            "Backbone modification", 0.0, 1.0, 0.3, step=0.05,
            help="Add/remove atoms from an existing linker to resize/reshape it."
        )
    with sc3:
        w_tmpl = st.slider(
            "Template (new backbones)", 0.0, 1.0, 0.2, step=0.05,
            help="Build from application-specific scaffolds. Best for entirely new topological ideas."
        )

    seed_smiles_in = st.text_input(
        "Seed molecule (SMILES) — pin generation to derivatives of this exact molecule",
        value="",
        help="Paste a SMILES (e.g. a top candidate from a previous run). The engine will "
             "only mutate THIS molecule. Disables the template strategy automatically.",
    )
    seed_valid = True
    if seed_smiles_in.strip():
        if _RDK and Chem.MolFromSmiles(seed_smiles_in.strip()) is None:
            seed_valid = False
            st.error("Seed SMILES is not valid — fix it or clear the field.")
        else:
            _seed_heavy = _heavy(seed_smiles_in.strip())
            st.caption(f"Pinned to {_formula(seed_smiles_in.strip())} "
                       f"({_seed_heavy} heavy atoms). "
                       "Template strategy is ignored while a seed is pinned.")
            if _seed_heavy != exact_atoms:
                st.warning(
                    f"Seed has {_seed_heavy} heavy atoms but the target is {exact_atoms}. "
                    "Only the **Backbone modification** strategy can resize it to the target — "
                    "give that slider weight, or set the target to "
                    f"{_seed_heavy} for substitution-only variations."
                )

    _GROUP_LABELS = {
        "Carboxyl (–COOH)": "carboxyl",
        "Hydroxyl (–OH)": "hydroxyl",
        "Amino (–NH2)": "amino",
        "Nitro (–NO2)": "nitro",
        "Cyano (–C≡N)": "cyano",
        "Fluoro (–F)": "fluoro",
        "Chloro (–Cl)": "chloro",
        "Sulfonic (–SO3H)": "sulfonic",
        "Pyridyl ring": "pyridyl",
    }
    required_group_labels = st.multiselect(
        "Required functional groups — every candidate MUST contain all of these",
        list(_GROUP_LABELS.keys()),
        default=[],
        help="Hard constraint. Requiring groups thins the yield, so the generator "
             "is given extra attempts and prefers seed linkers that already carry them.",
    )
    required_groups = [_GROUP_LABELS[g] for g in required_group_labels]

# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

st.divider()

if st.button("GENERATE LIGANDS", type="primary", use_container_width=True):
    if not require_access():
        st.stop()
    if not seed_valid:
        st.error("Cannot generate: the seed SMILES is invalid. Fix or clear it first.")
        st.stop()
    consume_use()

    # Directed-generation controls: only pass non-default values through.
    _seed = seed_smiles_in.strip() or None
    _weights = {"substitution": w_sub, "modification": w_mod, "template": w_tmpl}
    if (w_sub + w_mod + w_tmpl) <= 0:
        st.warning("All strategy weights are zero — falling back to the default mix.")
        _weights = None

    spec = LinkerScreeningSpec(
        application_context=application,
        num_candidates=n_candidates,
        require_all_agree=require_all_agree,
        allow_hollow=allow_hollow,
        exclude_elements=exclude if exclude else None,
        strategy_weights=_weights,
        seed_smiles=_seed,
        required_groups=required_groups if required_groups else None,
    )

    try:
        screener = LinkerScreener()
    except Exception as e:
        st.error(f"Screener init failed: {e}")
        st.stop()

    # Set exact atom count on generator
    screener.generator.min_atoms = exact_atoms
    screener.generator.max_atoms = exact_atoms

    with st.spinner(f"Generating {n_candidates} ligands with exactly {exact_atoms} heavy atoms..."):
        try:
            result = screener.screen(spec)
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.stop()

    st.session_state.mof_result = result
    st.session_state.mof_required_donors = required_donors
    st.session_state.mof_exact_atoms = exact_atoms
    st.session_state.mof_directed = {
        "strategy_weights": _weights,
        "seed_smiles": _seed,
        "required_groups": required_groups or [],
    }
    st.rerun()

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

if "mof_result" in st.session_state:
    res = st.session_state.mof_result
    required_donors = st.session_state.get("mof_required_donors", [])
    target_atoms = st.session_state.get("mof_exact_atoms", 22)

    st.divider()

    # Post-filter by donor atoms
    filtered = []
    for c in res.candidates:
        has_donors = all(_count_donor_atoms(c.linker_smiles, d) > 0 for d in required_donors)
        if has_donors:
            filtered.append(c)

    st.subheader(f"Results: {len(filtered)} ligands with {target_atoms} heavy atoms")

    # Validated grounded funnel: score every candidate (chemical sanity,
    # coordination, synthesizability, geometry) + novelty vs known linkers.
    scored = [(c, score_linker(c.linker_smiles) if _FUNNEL_OK else None) for c in filtered]
    if _FUNNEL_OK:
        scored.sort(key=lambda cf: cf[1]["score"], reverse=True)
    n_passed_gates = sum(1 for _, fr in scored if fr and fr["passed_all"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Generated", res.num_generated)
    m2.metric(
        "Passed grounded gates" if _FUNNEL_OK else "Passed All Verdicts",
        n_passed_gates if _FUNNEL_OK else res.num_passed_all,
    )
    m3.metric("After Donor Filter", len(filtered))

    if _FUNNEL_OK:
        st.caption(
            "Grounded funnel (validated): ~94% recall on held-out real synthesized "
            "linkers, AUROC ~0.88 vs. raw generator output "
            "(see docs/MOF_LINKER_BENCHMARK_RESULTS.md). Gates: chemical sanity, "
            ">=2 coordinating sites, SAscore, donor geometry. Novelty = 1 - similarity "
            "to nearest known linker. A high score is NOT a synthesis guarantee."
        )

    _GATE_LABEL = {
        None: "PASS",
        "G1_parse": "fail: invalid",
        "G1_pains_brenk": "flag: PAINS/Brenk",
        "G2_coordination": "fail: <2 donors",
        "G3_sascore": "fail: hard to synthesize",
        "G4_geometry": "fail: donor geometry",
    }

    if not filtered:
        st.warning(
            "No candidates matched. Try: more candidates, relaxing verdicts, "
            "or removing donor atom requirements."
        )
    else:
        import pandas as pd

        rows = []
        for c, fr in scored[:50]:
            row = {
                "Formula": _formula(c.linker_smiles),
                "Atoms": _heavy(c.linker_smiles),
                "MW": _mw(c.linker_smiles),
                "SMILES": c.linker_smiles,
            }
            if fr:
                row["Funnel"] = _GATE_LABEL.get(fr["died_at"], fr["died_at"] or "PASS")
                row["Coord"] = fr["n_coord"]
                row["SAscore"] = fr["sascore"] if fr["sascore"] is not None else "—"
                row["Novelty"] = round(1 - fr["max_tanimoto"], 2) if fr["max_tanimoto"] is not None else "—"
            for d in ["N", "O", "S"]:
                row[d] = _count_donor_atoms(c.linker_smiles, d)
            rows.append(row)

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Top candidate detail
        best, best_fr = scored[0]
        st.subheader("Top Candidate")
        st.code(best.linker_smiles, language="text")

        bc1, bc2 = st.columns(2)
        with bc1:
            st.markdown(f"**{_formula(best.linker_smiles)}** | "
                        f"{_heavy(best.linker_smiles)} atoms | "
                        f"MW {_mw(best.linker_smiles)}")
            donors_str = ", ".join(
                f"{d}: {_count_donor_atoms(best.linker_smiles, d)}"
                for d in ["N", "O", "S"]
                if _count_donor_atoms(best.linker_smiles, d) > 0
            )
            if donors_str:
                st.markdown(f"**Donor atoms:** {donors_str}")

        with bc2:
            if best_fr:
                st.markdown("**Grounded funnel**")
                if best_fr["passed_all"]:
                    st.success("PASS — clears every grounded gate")
                else:
                    st.warning(f"Stopped at {_GATE_LABEL.get(best_fr['died_at'], best_fr['died_at'])}")
                st.write(f"Coordinating sites: {best_fr['n_coord']}")
                if best_fr["sascore"] is not None:
                    st.write(f"SAscore (lower = easier to make): {best_fr['sascore']}")
                if best_fr["geometry_ok"] is not None:
                    st.write(f"Ditopic-capable geometry: {'yes' if best_fr['geometry_ok'] else 'no'}")
                if best_fr["max_tanimoto"] is not None:
                    st.write(f"Novelty (1 - nearest-known): {round(1 - best_fr['max_tanimoto'], 2)}")
                if best_fr["pains_brenk_flag"]:
                    st.caption("Trips PAINS/Brenk drug filters — common for real MOF linkers; informational only.")
            
            with st.expander("Dynamic Descriptor Verdicts (Unvalidated)"):
                for vn, vv in best.verdicts.items():
                    st.write(f"{_verdict_icon(vv)} {vn}: {best.verdict_scores.get(vn, 0):.2f}")

        if best.reasoning_traces:
            with st.expander("Reasoning traces"):
                for vn, trace in best.reasoning_traces.items():
                    st.markdown(f"**{vn}:**")
                    safe = trace.encode("ascii", "replace").decode()
                    st.caption(safe)

        # Export
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            csv_rows = []
            for c in filtered:
                csv_rows.append({
                    "SMILES": c.linker_smiles,
                    "formula": _formula(c.linker_smiles),
                    "heavy_atoms": _heavy(c.linker_smiles),
                    "MW": _mw(c.linker_smiles),
                    "N_count": _count_donor_atoms(c.linker_smiles, "N"),
                    "O_count": _count_donor_atoms(c.linker_smiles, "O"),
                    "S_count": _count_donor_atoms(c.linker_smiles, "S"),
                    "morphism_integrity": c.morphism_integrity,
                    "viable": c.overall_viable,
                    **{k: v for k, v in c.verdicts.items()},
                })
            st.download_button(
                "Download CSV", pd.DataFrame(csv_rows).to_csv(index=False),
                "ligands.csv", "text/csv", use_container_width=True,
            )
        with c2:
            import json
            import datetime
            
            bundle = {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "software_version": "KOMPOSOS-IV-CHEM (Triage-Grade Designer)",
                "design_constraints": {
                    "target_atoms": target_atoms,
                    "required_donors": list(required_donors),
                    "directed_generation": st.session_state.get("mof_directed", {}),
                },
                "candidates_audit": [
                    {
                        "candidate": c.to_dict(),
                        "funnel_audit": next((fr for _c, fr in scored if _c.linker_smiles == c.linker_smiles), None)
                    } for c in filtered
                ]
            }
            
            st.download_button(
                "📥 Download Reproducibility Bundle (JSON)",
                json.dumps(bundle, indent=2),
                "mof_designer_audit.json", "application/json", use_container_width=True,
                help="Download an auditable JSON bundle containing the generated linkers and their exact funnel screening history."
            )

        # Verdict stats
        with st.expander("Verdict breakdown"):
            if hasattr(res, "verdict_statistics") and res.verdict_statistics:
                stat_rows = []
                for vn in ["synthesizability", "toxicity", "stability", "activity", "conductivity"]:
                    if vn in res.verdict_statistics:
                        counts = res.verdict_statistics[vn]
                        stat_rows.append({
                            "Verdict": vn,
                            "AGREE": counts.get("AGREE", 0),
                            "HOLLOW": counts.get("HOLLOW", 0),
                            "ORPHAN": counts.get("ORPHAN", 0),
                            "REJECT": counts.get("REJECT", 0),
                        })
                if stat_rows:
                    st.dataframe(pd.DataFrame(stat_rows), use_container_width=True, hide_index=True)

        with st.expander("Raw data"):
            st.json(res.to_dict())

# ---------------------------------------------------------------------------
# Seed Database tab
# ---------------------------------------------------------------------------

st.divider()
with st.expander("Seed Linker Database"):
    try:
        cache = MOFLinkerCache()
        if cache.is_available():
            linkers = cache.load_linkers()
            st.caption(f"{len(linkers)} known linkers in database")
            if linkers:
                import pandas as pd
                atom_counts = [l.heavy_atom_count for l in linkers]
                st.caption(f"Atom range: {min(atom_counts)}-{max(atom_counts)}")
                rows = [{"SMILES": l.smiles[:60], "Atoms": l.heavy_atom_count,
                         "MW": l.molecular_weight, "Source": l.mp_source_id}
                        for l in linkers[:100]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No seed database. Run: `python scripts/download_mof_linkers.py`")
    except Exception as e:
        st.error(str(e))
