"""KOMPOSOS-III Chemistry — Streamlit Web UI.

Run with:
    streamlit run streamlit_app/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from streamlit_app.access_control import render_login_sidebar  # no-op

st.set_page_config(
    page_title="KOMPOSOS-III Chemistry",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load material count + MP status
from composition_engine.known_compositions import get_db
_db = get_db()
_mat_count = _db.size
_has_mp = _db.has_mp_data

st.title("KOMPOSOS-III Chemistry Engine")

st.markdown(f"""
**Compositional reasoning for materials science.**
Predict whether combinations of materials, molecules, or chemical species
will work together — before anything is physically built or simulated.

---

### What can you do here?

| Page | What it does |
|------|-------------|
| **Compatibility Checker** | Check if two materials are compatible (any of 6 domains) |
| **PFAS Scanner** | Screen materials for PFAS compliance and find replacements |
| **Composition Predictor** | Predict properties from any chemical formula |
| **Cell Designer** | Design a multi-domain battery cell and find bottlenecks |
| **Crystal Dreamer** | Inverse design: describe target properties, find candidate compositions |
| **MP Explorer** | Browse Materials Project data, derive crystal structures |
| **MOF Explorer** | Screen 30 Metal-Organic Frameworks against operating conditions with 5-scorer breakdown |
| **MOF Designer** | Generate novel MOF linkers with exact atom count control, donor atom filtering, and 5 KOMPOSOS verdicts |

---

### How it works

KOMPOSOS uses **category theory** — not neural networks — to reason about
material compatibility. Materials are *objects*, interactions are *morphisms*,
and compatibility is *composition*.

- **7 material bridges** spanning batteries, polymers, metals, ceramics,
  semiconductors, and glass
- **{_mat_count:,} materials** with real published property data (including 112+ battery-relevant species)
- **Physics-Embedded Search**: 120D composition vectors (stoichiometry + periodic table Group/Period) ensure chemically aware neighbor selection.
- **Active Verification**: Compatibility checks can run GROMACS when a real `.gro`/`.top` input bundle is supplied; otherwise the UI reports an explicit no-verdict readiness state, not a simulated stability result.
- **Validation Grounding** — current audit evaluates 215 curated literature pairs plus calibrated formation-energy intervals; compatibility results are an internal benchmark, not independent blind generalization.
- **Materials Project integration** — 103K+ DFT-computed structures with
  lattice parameters, formation energies, and convex hull distances
- **Empirical Bond Constraints** — local bond distributions with optional ColabFit cache/API support; not a live dynamic potential service in this build

---

## 🔬 Research-Grade Roadmap

To move from a high-fidelity screening tool to a more reliable research support tool, we are currently implementing:

1.  **Phase 16: Statistical Calibration**: Formation-energy intervals are calibrated against a frozen 5,000-entry external MP-style validation set and reported as 50/80/95% bands.
2.  **Organic Scaling**: Expanding our 199-material core with an automated **PubChem Bridge** to include 500+ lab reagents, catalysts, and monomers.
3.  **UI Provenance (🎓 Citation Badges)**: Every predicted property will soon feature a clickable citation badge linking directly to the DOI, Table, and Page of the source literature.

*Current Status: Phase 16 formation-energy calibration is active; broader physics still depends on source coverage and domain-specific validation.*
- **5 independent scorers** per bridge (ion transport, electrochemical stability,
  interface compatibility, mechanical compatibility, degradation)
- **Dempster-Shafer fusion** for multi-source evidence combination
- **ZFC dual-engine** for independent logical verification

No training data. No GPUs. Pure compositional reasoning.
""")

if _has_mp:
    st.sidebar.success(f"{_mat_count:,} materials loaded (MP cached)")
else:
    st.sidebar.info(f"{_mat_count:,} materials loaded (run download_mp_data.py for 103K+)")
st.sidebar.markdown("Select a page above to get started.")
