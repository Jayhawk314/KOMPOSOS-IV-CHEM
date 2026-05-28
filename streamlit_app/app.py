"""KOMPOSOS-IV-CHEM Streamlit Web UI.

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
    page_title="KOMPOSOS-IV-CHEM",
    page_icon="chem",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load material count + MP status
from composition_engine.known_compositions import get_db

_db = get_db()
_mat_count = _db.size
_has_mp = _db.has_mp_data

st.title("KOMPOSOS-IV-CHEM")

st.markdown(f"""
**Categorical discovery workbench for materials chemistry.**
KOMPOSOS-IV-CHEM combines compatibility reasoning, inverse composition design,
PFAS screening, synthesis planning, and audit trails so researchers can move
from target properties to candidate materials before expensive lab or simulation work.

---

### What can you do here?

| Page | What it does |
|------|-------------|
| **Compatibility Checker** | Check two-material compatibility with shared API/UI reasoning and audit metadata |
| **PFAS Scanner** | Screen materials for PFAS compliance and find replacements |
| **Composition Predictor** | Predict properties from a chemical formula |
| **Cell Designer** | Design a multi-domain battery cell and find bottlenecks |
| **Crystal Dreamer** | Inverse design: describe target properties and find candidate compositions |
| **MP Explorer** | Browse optional Materials Project data and derive crystal structures |
| **MOF Explorer** | Screen 30 Metal-Organic Frameworks against operating conditions with a 5-scorer breakdown |
| **MOF Designer** | Generate novel MOF linkers with exact atom count control, donor atom filtering, and 5 KOMPOSOS verdicts |
| **Discovery Workbench** | Run the current composition-first pipeline: inverse design, element constraints, PFAS screening, compatibility context, and synthesis planning |

---

### How it works

KOMPOSOS uses **category theory** to reason about material compatibility.
Materials are *objects*, interactions are *morphisms*, and compatibility is
checked through structured composition, typed morphisms, calibration, and
dual-engine constraints.

- **7 curated material bridges** spanning battery, polymer, metal, ceramic,
  semiconductor, glass, and MOF workflows
- **{_mat_count:,} composition records loaded locally**; optional Materials Project cache expands discovery and structure lookup when available
- **Physics-embedded search**: composition vectors combine stoichiometry with periodic-table features for chemically aware neighbor selection
- **Active verification**: compatibility checks can run GROMACS when a real `.gro`/`.top` input bundle is supplied; missing inputs return an explicit no-verdict readiness state
- **Validation grounding**: development compatibility is currently reported as 41/41 on the tuned development set; Q8 is frozen as the next 40-pair blind holdout and is not a completed validation claim
- **Materials Project integration**: optional 103K+ DFT-computed structure cache with lattice parameters, formation energies, and convex hull distances when installed
- **Empirical bond constraints**: local bond distributions with optional ColabFit cache/API support; not a live dynamic potential service in this build

---

## Current Workbench Status

The Discovery Workbench is a working **composition-first prototype**. It currently chains:

1. **Target property bounds** with optional min/max controls.
2. **Element constraints** with searchable element selectors.
3. **Compatibility context** with searchable material and interface-role selectors.
4. **Synthesis planning** through the current route planner.

CRYSTAL-specific and MOF-specific pipeline modes are planned next; the current
page should be used as a screening and triage tool, not as a final lab validation system.

- **5 independent scorers** per bridge where available
- **Dempster-Shafer fusion** for multi-source evidence combination
- **ZFC dual-engine** for independent logical verification

No GPUs required for the core reasoning path.
""")

if _has_mp:
    st.sidebar.success(f"{_mat_count:,} composition records loaded (MP cached)")
else:
    st.sidebar.info(f"{_mat_count:,} composition records loaded (run download_mp_data.py for 103K+ MP cache)")
st.sidebar.markdown("Select a page above to get started.")
