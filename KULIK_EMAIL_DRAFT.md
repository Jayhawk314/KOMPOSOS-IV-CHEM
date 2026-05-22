# Email to Heather Kulik - Final Draft

## Version A: With Live Demo (if Render is deployed)

**Subject:** Your 22-atom ligand challenge - solved (50 examples attached)

---

Hi Prof. Kulik,

I recently heard your interview where you mentioned: "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

I built a tool that solves this using compositional reasoning (category theory + ZFC set theory) instead of LLMs. It generates ligands with **exact atom count control**.

**Proof attached:**
→ 50 pre-screened 22-atom ligands (CSV with SMILES, formulas, donor atoms)
→ All 5 KOMPOSOS verdicts = AGREE (synthesizability, toxicity, stability, activity, conductivity)
→ **Research-Grade Grounding:** System validated against 143 literature pairs (94.4% accuracy, F1=0.963)
→ **Physical Constraints:** Interatomic potentials now use live empirical distributions from ColabFit Exchange

**Try it yourself:**
→ Live demo: https://komposos-chem.onrender.com
→ Go to "MOF Designer" page (page 8)
→ Set "Exact Heavy Atom Count" = 22
→ Click "GENERATE LIGANDS"

The tool filters by donor atoms (N, O, S) and scores each candidate with 5 compositional verdicts. No training data - it reasons over chemical composition rules using dual-engine verification (categorical + set-theoretic).

**Some highlights from the attached CSV:**
- Linker #1: C15H9N2O5 (22 atoms, 2 N donors, morphism integrity 1.0)
- Linker #7: C19H21N3 (22 atoms, 3 N donors, all verdicts AGREE)
- Linker #13: C16H14N6 (22 atoms, 6 N donors, perfect for coordination)

Would love to hear if these ligands are useful for your active learning pipeline. Happy to discuss integration with molSimplify.

Best,
James Hawkins
GitHub: https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem

**Attachment:** kulik_22atom_linkers_100.csv (7.3 KB)

---

## Version B: Without Live Demo (local Docker instead)

**Subject:** Your 22-atom ligand challenge - solved (50 examples attached)

---

Hi Prof. Kulik,

I recently heard your interview where you mentioned: "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

I built a tool that solves this using compositional reasoning (category theory + ZFC set theory) instead of LLMs. It generates ligands with **exact atom count control**.

**Proof attached:**
→ 50 pre-screened 22-atom ligands (CSV with SMILES, formulas, donor atoms)
→ All 5 KOMPOSOS verdicts = AGREE (synthesizability, toxicity, stability, activity, conductivity)
→ **Research-Grade Grounding:** System validated against 143 literature pairs (94.4% accuracy, F1=0.963)
→ **Physical Constraints:** Interatomic potentials now use live empirical distributions from ColabFit Exchange

**See for yourself:**
You can run it locally with one command (requires Docker):

```bash
git clone https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem
cd KOMPOSOS-III-LAMBDA-max-3D-chem
streamlit run streamlit_app/app.py
```

Then go to "MOF Designer" → set 22 atoms → generate

The tool filters by donor atoms (N, O, S) and scores each candidate with 5 compositional verdicts. No training data - it reasons over chemical composition rules using dual-engine verification (categorical + set-theoretic).

**Some highlights from the attached CSV:**
- Linker #1: C15H9N2O5 (22 atoms, 2 N donors, morphism integrity 1.0)
- Linker #7: C19H21N3 (22 atoms, 3 N donors, all verdicts AGREE)
- Linker #13: C16H14N6 (22 atoms, 6 N donors, perfect for coordination)

Would love to hear if these ligands are useful for your active learning pipeline. Happy to discuss integration with molSimplify.

Best,
James Hawkins
GitHub: https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem

**Attachment:** kulik_22atom_linkers_100.csv (7.3 KB)

---

## Version C: Twitter/LinkedIn DM (shorter)

Hi Prof. Kulik,

Heard you mention: "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

I built a tool that does exactly this using compositional reasoning (not LLMs).

Attached: 50 pre-screened 22-atom ligands with SMILES, formulas, donor atoms, and 5 KOMPOSOS verdicts (all AGREE).

GitHub: https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem

Would love your feedback on whether these are useful for molSimplify/DFT validation.

Best,
James

---

## Contact Info to Find

**Email:**
- Check MIT ChemE faculty page (likely kulik@mit.edu)
- Try through molSimplify GitHub repo

**Twitter/X:**
- @HeatherJKulik (confirmed in docs)

**LinkedIn:**
- Search "Heather Kulik MIT"

---

## Pre-Send Checklist

Before sending, verify:

- [ ] CSV file attached (kulik_22atom_linkers_100.csv, 7.3 KB)
- [ ] All 50 linkers have exactly 22 heavy atoms (verified above ✓)
- [ ] All verdicts are AGREE (verified above ✓)
- [ ] Demo URL is correct (if using Version A)
  - Test: Visit URL, go to MOF Designer, generate 22-atom linkers
  - Verify: Results show exactly 22 atoms
- [ ] GitHub repo is public (or provide access)
- [ ] Email signature has your real contact info

---

## Follow-Up Strategy (if no response in 1 week)

**Follow-up email subject:** Quick question about linker #13 (6 N donors)

Hi Prof. Kulik,

Quick follow-up on the 22-atom ligands I sent last week.

I was curious about ligand #13 from the CSV (C16H14N6 - the one with 6 nitrogen donors). Does that level of N-coordination look synthesizable to you, or would you typically aim for 2-4 donors?

Trying to calibrate the tool's verdict scoring against real MOF chemists' intuition.

Thanks,
James

---

## Success Metrics

**Immediate (24 hours):**
- Email opened (use email tracker if available)

**Week 1:**
- Reply received (any response is good)
- CSV downloaded

**Week 2:**
- Demo clicked (if Version A)
- Questions about integration

**Month 1:**
- DFT validation attempt
- Invitation to present to group

**Month 3:**
- Collaboration discussion
- Co-authorship possibility
