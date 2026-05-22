# KOMPOSOS-MOF Inverse Design UI Mockup

Based on your existing KOMPOSOS-III design, here's what the KOMPOSOS-MOF system should look like.

---

## **Main App Structure**

**File:** `pages/8_MOF_Designer.py`

**Page Config:**
```python
st.set_page_config(
    page_title="MOF Designer", 
    page_icon="🧬", 
    layout="wide"
)
st.title("MOF Linker Designer & Inverse Screening")
st.markdown("""
Generate novel 22-atom Metal-Organic Framework linkers optimized for your application.
Uses **generative models + KOMPOSOS categorical reasoning** to design molecules that 
satisfy all constraints (synthesizability, toxicity, stability, activity).
""")
```

---

## **Screen 1: Configuration & Generation**

### Layout: 3-Column Setup

```
┌─────────────────────────────────────────────────────────────────┐
│ MOF LINKER DESIGNER                                             │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   APPLICATION    │  │  GENERATION      │  │   CONSTRAINTS    │
│   CONTEXT        │  │   SETTINGS       │  │   & FILTERS      │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ Target App:      │  │ Num Candidates:  │  │ Keep only:       │
│ [Dropdown ▼]     │  │ [100  ←→ 1000]   │  │ ☑ AGREE all 5    │
│                  │  │                  │  │ ☐ Allow HOLLOW   │
│ • Breath VOC     │  │ Ranking:         │  │                  │
│ • Food Safety    │  │ [Morphism Integr▼] │ Filter Verdicts: │
│ • PFAS Detect    │  │                  │  │ ☑ Synthesizable  │
│ • Custom         │  │ Model:           │  │ ☑ Non-toxic      │
│                  │  │ [Pretrained GNN▼]  │ ☑ Stable         │
│                  │  │                  │  │ ☑ Active/Select  │
│                  │  │ Batch Size:      │  │ ☑ Conductive     │
│                  │  │ [32  ←→ 256]     │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
                               ↓
                      [GENERATE CANDIDATES]  (type="primary")
```

**Column 1: Application Context**
```python
target_app = st.selectbox(
    "Target Application",
    ["breath_voc_sensing", "food_safety", "pfas_detection", "custom"],
    format_func=lambda x: x.replace("_", " ").title()
)

if target_app == "custom":
    custom_desc = st.text_area("Describe your application:")
```

**Column 2: Generation Settings**
```python
n_candidates = st.slider("Number of candidates", 10, 1000, 100)
ranking = st.selectbox("Rank by", ["morphism_integrity", "verdicts_passed", "novel_chemistry"])
batch_size = st.slider("Batch size (for faster generation)", 32, 256, 64, step=32)
```

**Column 3: Filtering**
```python
st.markdown("**Filter Results By Verdicts**")
col_req, col_allow = st.columns(2)
with col_req:
    require_all_agree = st.checkbox("Require AGREE on all 5 verdicts", value=True)
with col_allow:
    allow_hollow = st.checkbox("Allow HOLLOW verdicts (exploratory)", value=False)

st.markdown("**Verdict Types**")
verdicts_to_keep = st.multiselect(
    "Keep candidates with these verdicts:",
    ["Synthesizability", "Toxicity", "Stability", "Activity", "Conductivity"],
    default=["Synthesizability", "Toxicity", "Stability", "Activity", "Conductivity"]
)
```

**Big Button:**
```python
if st.button("🚀 GENERATE CANDIDATES", type="primary", use_container_width=True):
    with st.spinner("Generating and screening linkers..."):
        # Call generation pipeline
        results = generate_and_screen(
            target_app=target_app,
            n_candidates=n_candidates,
            require_all_agree=require_all_agree,
            allow_hollow=allow_hollow,
            ranking=ranking
        )
    st.session_state.results = results
    st.rerun()
```

---

## **Screen 2: Results Overview (After Generation)**

### Metrics Row

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Generated   │  │  Passed All  │  │  Top Score   │  │  Avg Morph   │
│     ███      │  │     ███      │  │     ███      │  │     ███      │
│   1,000      │  │    847       │  │    0.968     │  │    0.922     │
│  Candidates  │  │   AGREE      │  │  Integrity   │  │  Integrity   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

```python
if 'results' in st.session_state:
    res = st.session_state.results
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Generated", res['total_candidates'])
    col2.metric("Passed All Verdicts", res['passed_all_agree'])
    col3.metric("Top Morphism Score", f"{res['best_morphism']:.3f}")
    col4.metric("Avg Morphism", f"{res['avg_morphism']:.3f}")
```

### Results Table with Sorting & Filtering

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ RANKED CANDIDATES (Top 50 shown)                                            │
├───┬────────────┬──────────┬──────┬────────┬──────┬────────┬──────┬────────┤
│ # │   SMILES   │    MW    │Morph │ Synth  │ Tox  │ Stabil │ Act  │ Cond   │
├───┼────────────┼──────────┼──────┼────────┼──────┼────────┼──────┼────────┤
│ 1 │Cc1cc[nH].. │ 234.2    │ 0.94 │  ✓    │  ✓   │   ✓    │  ✓   │   ✓    │
│ 2 │Nc2cc[N]c.. │ 245.1    │ 0.91 │  ✓    │  ✓   │   ✓    │  ✓   │   ◇    │
│ 3 │Oc3cc[OH].. │ 256.3    │ 0.89 │  ✓    │  ✓   │   ✓    │  ✓   │   ✓    │
│ 4 │[N+]c4cc... │ 267.5    │ 0.87 │  ✓    │  ◇   │   ✓    │  ✓   │   ✓    │
│ 5 │Sc5cc[S]c.. │ 278.9    │ 0.85 │  ◇   │  ✓   │   ✓    │  ✓   │   ✗    │
│...│            │          │      │        │      │        │      │        │
│50 │Fc6cc[Br].. │ 312.1    │ 0.71 │  ✓    │  ✓   │   ✓    │  ◇   │   ✓    │
└───┴────────────┴──────────┴──────┴────────┴──────┴────────┴──────┴────────┘

Legend: ✓ = AGREE  |  ◇ = HOLLOW  |  ✗ = REJECT  |  ○ = ORPHAN
```

**Table Implementation:**
```python
import pandas as pd

df = pd.DataFrame([
    {
        "Rank": i+1,
        "SMILES": cand['smiles'][:20] + "...",  # Truncate for display
        "MW": f"{cand['molecular_weight']:.1f}",
        "Morphism": f"{cand['morphism_integrity']:.2f}",
        "Synth": verdict_icon(cand['verdicts']['synthesizability']),
        "Toxicity": verdict_icon(cand['verdicts']['toxicity']),
        "Stability": verdict_icon(cand['verdicts']['stability']),
        "Activity": verdict_icon(cand['verdicts']['activity']),
        "Conductivity": verdict_icon(cand['verdicts']['conductivity']),
        "full_smiles": cand['smiles']
    }
    for i, cand in enumerate(results['candidates'][:50])
])

st.dataframe(
    df.style.background_gradient(subset=["Morphism"], cmap="RdYlGn", vmin=0.7, vmax=1.0),
    use_container_width=True,
    hide_index=True,
    column_config={
        "SMILES": st.column_config.TextColumn("SMILES", width=120),
        "Morphism": st.column_config.ProgressColumn("Morphism", min_value=0, max_value=1),
    }
)
```

---

## **Screen 3: Detailed View (Click on Rank)**

### When User Clicks on a Row: Expandable Detail View

```
┌──────────────────────────────────────────────────────────────────┐
│ CANDIDATE #1 — DETAILED ANALYSIS                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  SMILES: Cc1ccccc1NC(=O)c2ccccc2C                                │
│  IUPAC: N-(2-methylphenyl)benzamide                              │
│  Molecular Weight: 234.2 g/mol                                   │
│                                                                   │
│  ┌────────────────────┐  ┌────────────────────┐                 │
│  │ MORPHISM INTEGRITY │  │ VERDICT SUMMARY    │                 │
│  ├────────────────────┤  ├────────────────────┤                 │
│  │ Score: 0.943       │  │ Synthesizability:  │                 │
│  │ █████████░  94.3%  │  │ ✓ AGREE            │                 │
│  │                    │  │                    │                 │
│  │ Interpretation:    │  │ Toxicity:          │                 │
│  │ "Atomic envs very  │  │ ✓ AGREE            │                 │
│  │  consistent; 1 of  │  │                    │                 │
│  │  16 bonds has local│  │ Stability:         │                 │
│  │  ionic character"  │  │ ✓ AGREE            │                 │
│  │                    │  │                    │                 │
│  │ Quality: HIGH      │  │ Activity (VOC):    │                 │
│  │                    │  │ ✓ AGREE            │                 │
│  │                    │  │                    │                 │
│  │                    │  │ Conductivity:      │                 │
│  │                    │  │ ◇ HOLLOW           │                 │
│  └────────────────────┘  └────────────────────┘                 │
│                                                                   │
│ ─────────────────────────────────────────────────────────────── │
│                                                                   │
│ REASONING TRACES (Expandable)                                   │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ ▼ Synthesizability                                         │ │
│ │   ✓ All bonds valid (single, double, aromatic)            │ │
│ │   ✓ No strained ring systems detected                      │ │
│ │   ✓ Connectivity matches known N-aryl amide syntheses      │ │
│ │   → Prediction: Synthetically accessible (>90% confidence) │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ ▼ Toxicity                                                 │ │
│ │   ✓ No known toxic functional groups (isocyanates, etc)   │ │
│ │   ✓ Partial charges: moderate (<0.3e per atom)            │ │
│ │   ✓ Aromatic ring system (stable, low reactivity)         │ │
│ │   → Prediction: Non-toxic (low electrophilicity)           │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ ▼ Stability                                                │ │
│ │   ✓ All bond strengths > 2 kcal/mol (strong)              │ │
│ │   ✓ No strained rings (ring strain < 2 kcal/mol)          │ │
│ │   ✓ Aromatic C-H bonds resistant to oxidation             │ │
│ │   → Prediction: Thermally stable to >300°C                │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ ▼ Activity (Breath VOC Sensing)                            │ │
│ │   ✓ Aromatic rings: 2 benzene units (π-π interactions)    │ │
│ │   ✓ Polar functional group: N-H (H-bonding to VOCs)       │ │
│ │   ✓ Amide linker: known for VOC uptake                    │ │
│ │   → Prediction: Good selectivity for polar VOCs (ethanol, │ │
│ │     acetone, etc)                                          │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ ▼ Electrical Conductivity                                  │ │
│ │   ◇ Conjugation: Partial (aromatic, but N breaks π-system)│ │
│ │   ◇ Orbital overlap: Moderate (not fully delocalized)     │ │
│ │   ◇ Prediction ambiguous: Local ionic character around    │ │
│ │       nitrogen affects band structure unpredictably        │ │
│ │   → Recommendation: Run DFT for accurate bandgap estimate  │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ ─────────────────────────────────────────────────────────────── │
│                                                                   │
│ MOLECULAR PROPERTIES                                             │
│ • H-bond donors: 1 (N-H)                                         │
│ • H-bond acceptors: 2 (C=O, aromatic N)                          │
│ • Rotatable bonds: 2                                             │
│ • Aromatic rings: 2                                              │
│ • Heavy atom count: 22 ✓                                         │
│ • LogP: 2.8 (lipophilic)                                         │
│ • Topological PSA: 29.1 Å²                                       │
│                                                                   │
│ ─────────────────────────────────────────────────────────────── │
│                                                                   │
│ ACTIONS:                                                         │
│ [View Structure (2D/3D)] [Compare with #2] [Export Data]        │
│ [Run DFT Check] [Add to Shortlist]                              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Implementation:**
```python
selected_rank = st.selectbox("View details for candidate:", [f"#{i+1}" for i in range(50)])
rank_idx = int(selected_rank.strip("#")) - 1
candidate = results['candidates'][rank_idx]

with st.expander(f"Candidate #{rank_idx+1} — {candidate['smiles'][:40]}...", expanded=True):
    # Morphism score
    col_morph, col_verdict = st.columns(2)
    with col_morph:
        st.markdown("### Morphism Integrity")
        morphism = candidate['morphism_integrity']
        st.metric("Score", f"{morphism:.3f}")
        st.progress(morphism, text=f"{morphism*100:.1f}%")
        
        with st.expander("Interpretation"):
            st.write(candidate['reasoning_trace']['morphism_notes'])
    
    with col_verdict:
        st.markdown("### Verdicts Summary")
        for verdict_type, verdict in candidate['verdicts'].items():
            icon = verdict_icon(verdict)
            st.write(f"{icon} **{verdict_type.title()}**: {verdict}")
    
    # Detailed reasoning traces
    st.markdown("---")
    st.markdown("### Reasoning Traces")
    
    for verdict_type, trace in candidate['reasoning_trace'].items():
        if verdict_type != 'morphism_notes':
            with st.expander(f"▶ {verdict_type.title()}"):
                st.write(trace)
    
    # Molecular properties
    st.markdown("---")
    st.markdown("### Molecular Properties")
    props_cols = st.columns(4)
    props = candidate['properties']
    prop_list = [
        ("H-donors", props.get('h_donors')),
        ("H-acceptors", props.get('h_acceptors')),
        ("Rotatable", props.get('rotatable_bonds')),
        ("LogP", props.get('logp')),
        ("MW", props.get('molecular_weight')),
        ("PSA", props.get('topological_psa')),
        ("Aromatic Rings", props.get('aromatic_rings')),
        ("Heavy Atoms", props.get('heavy_atom_count')),
    ]
    for idx, (label, value) in enumerate(prop_list):
        with props_cols[idx % 4]:
            st.write(f"**{label}**: {value}")
    
    # Actions
    st.markdown("---")
    col_actions = st.columns(4)
    with col_actions[0]:
        if st.button("View 2D Structure", key=f"2d_{rank_idx}"):
            st.write("(Display 2D molecular structure here)")
    with col_actions[1]:
        if st.button("Compare with #2", key=f"cmp_{rank_idx}"):
            st.write("(Comparison view)")
    with col_actions[2]:
        if st.button("Export Data", key=f"exp_{rank_idx}"):
            st.download_button("Download JSON", json.dumps(candidate), f"candidate_{rank_idx+1}.json")
    with col_actions[3]:
        if st.button("⭐ Shortlist", key=f"short_{rank_idx}"):
            st.success(f"Added to shortlist!")
```

---

## **Screen 4: Batch Export & Reporting**

### Bottom Section: Export Options

```
┌──────────────────────────────────────────────────────────────────┐
│ EXPORT & REPORTING                                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ [Download CSV (all 50)]  [Download JSON]  [Generate PDF Report]  │
│                                                                   │
│ PDF Report includes:                                             │
│ • Title page (application + generation parameters)               │
│ • Top 10 candidates with full verdicts                           │
│ • Morphism integrity distribution chart                          │
│ • Verdict pass rate statistics                                   │
│ • Literature references (DOI for each reasoning rule)            │
│ • Next steps (DFT screening, synthesis planning)                 │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Implementation:**
```python
st.divider()
st.markdown("## Export & Reporting")

col_csv, col_json, col_pdf = st.columns(3)

with col_csv:
    csv_data = df.to_csv(index=False)
    st.download_button(
        label="📊 Download CSV",
        data=csv_data,
        file_name=f"mof_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

with col_json:
    json_data = json.dumps(results['candidates'], indent=2)
    st.download_button(
        label="📋 Download JSON",
        data=json_data,
        file_name=f"mof_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

with col_pdf:
    if st.button("📄 Generate PDF Report"):
        pdf_bytes = generate_pdf_report(results, target_app)
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=f"mof_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )

# Statistics
st.markdown("### Results Statistics")
stat_cols = st.columns(5)
stat_cols[0].metric("Total Candidates", len(results['candidates']))
stat_cols[1].metric("Morphism Range", f"{results['min_morphism']:.2f}-{results['max_morphism']:.2f}")
stat_cols[2].metric("Avg Verdicts Passed", f"{results['avg_verdicts_passed']}/5")
stat_cols[3].metric("Most Common Verdict", results['most_common_verdict'])
stat_cols[4].metric("Generation Time", f"{results['generation_time_sec']:.1f}s")

# Visualization: Verdict distribution
st.markdown("### Verdict Distribution")
verdict_counts = results['verdict_statistics']
fig = px.bar(
    x=list(verdict_counts.keys()),
    y=list(verdict_counts.values()),
    labels={"x": "Verdict Type", "y": "Count"},
    color=list(verdict_counts.keys()),
)
st.plotly_chart(fig, use_container_width=True)
```

---

## **Visual Design Consistency**

Matching your existing KOMPOSOS UI style:

**Color Scheme:**
- ✓ AGREE: Green (#2ecc71)
- ◇ HOLLOW: Yellow (#f39c12)
- ✗ REJECT: Red (#e74c3c)
- ○ ORPHAN: Gray (#95a5a6)
- Morphism bars: RdYlGn gradient (0.7→1.0)

**Typography:**
- Headers: Bold, clean (Streamlit default)
- SMILES display: Monospace (code font)
- Metrics: Large, high-contrast numbers

**Icons:**
- ✓ = checkmark (emoji or Unicode)
- ◇ = diamond (ambiguous)
- ✗ = X (failed)
- ○ = circle (unknown)
- 🧬 = DNA helix (app icon)
- 🚀 = rocket (generate button)
- 📊, 📋, 📄 = data export

---

## **Complete Page Flow (Summary)**

```
Entry Point (Home Page)
       ↓
"8_MOF_Designer.py" link
       ↓
Configuration Screen (Application + Generation Settings)
       ↓
[GENERATE CANDIDATES] button
       ↓
Results Overview (Metrics + Table)
       ↓
Click on Row → Detail View (Verdicts + Reasoning Traces)
       ↓
Compare / Export / Shortlist Actions
       ↓
Batch Export (CSV/JSON/PDF)
```

---

## **Key Features (What Makes This UI Powerful)**

1. **One-Click Generation**: Input application → Get 50 ranked candidates in seconds
2. **Full Transparency**: Every verdict has a reasoning trace
3. **Morphism Integrity Visualization**: See where the reasoning is solid vs. ambiguous
4. **Batch Export**: CSV for analysis, JSON for downstream processing, PDF for sharing
5. **Comparison**: Click any candidate to see detailed chemistry explanation
6. **Shortlist**: Build a list of favorites for experimental validation
7. **Fast Iteration**: Change application context, hit generate again in <30 seconds

---

## **Mobile Responsiveness**

- Main metrics: Stack on mobile (single column instead of 4)
- Table: Horizontal scroll on mobile, compact display
- Detail view: Full width, accordion-style expanding sections
- Export buttons: Stack vertically on mobile

---

**This UI tells the story:** 
1. What are you trying to make? (Application)
2. Generate candidates that fit. (Generation)
3. Here's what KOMPOSOS thinks. (Results + Verdicts)
4. Here's WHY it thinks that. (Reasoning Traces)
5. Take these candidates and run with them. (Export)
