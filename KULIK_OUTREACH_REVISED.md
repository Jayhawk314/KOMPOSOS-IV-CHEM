# Heather Kulik Outreach - Revised Low-Friction Strategy

## Problem with Original Plan

❌ **First email asks for 2-3GB Docker download** = too much friction
❌ She has to install, configure, troubleshoot before seeing value
❌ No immediate proof it solves her problem

## Revised 3-Step Strategy

### Step 1: First Contact (ZERO friction)

**Goal**: Solve her problem in the email itself, prove the tool works

**Deliverables:**
1. ✅ **CSV file attached** - 100 pre-generated 22-atom ligands (all verdicts AGREE)
2. ✅ **Live web demo link** - Click and try immediately (Render deployment or GitHub Codespaces)
3. ✅ **Screenshot/GIF** - Shows MOF Designer generating exact 22-atom ligands

**Email structure:**
```
Subject: Your 22-atom ligand challenge - solved (100 examples attached)

Hi Prof. Kulik,

I heard you mention: "I just ask it, please design me a ligand that has 22 atoms.
I can never get an answer that has 22 atoms."

I built a tool that does this using compositional reasoning (not LLMs).

**See for yourself:**
→ Attached: 100 pre-screened 22-atom ligands (CSV) with SMILES, formulas, donor atoms
→ Try live: [DEMO_LINK] (click "MOF Designer" → set 22 atoms → generate)
→ Screenshot: [shows exact atom count control UI]

All 100 ligands have:
- Exactly 22 heavy atoms (verified with RDKit)
- All 5 KOMPOSOS verdicts = AGREE (synthesizability, toxicity, stability, activity, conductivity)
- Donor atom counts (N, O, S) for MOF coordination

Would love to hear if these are useful for your molSimplify/DFT pipeline.

Best,
James Hawkins
```

**What she can do immediately:**
- Open CSV in Excel (30 seconds)
- Click demo link, generate her own ligands (2 minutes)
- Validate SMILES in her existing tools (immediate integration test)

---

### Step 2: Second Contact (If Interested)

**Trigger**: She replies with positive feedback or questions

**Goal**: Enable local deployment for her lab

**Deliverables:**
1. Docker image on DockerHub (`jayhawk314/komposos-chemistry`)
2. One-line install instructions
3. API integration example for molSimplify

**Email:**
```
Great to hear the ligands are useful!

For your lab/cluster, I've packaged it as a Docker image:

docker run -p 8501:8501 jayhawk314/komposos-chemistry

Or integrate via API:
[Python code snippet]

Let me know if you want to discuss integration with your 7-objective active learning workflow.
```

---

### Step 3: Third Contact (Partnership)

**Trigger**: She's using it regularly, wants to collaborate

**Goal**: Academic partnership, co-authorship, validation study

**Options:**
- Validate KOMPOSOS linkers with DFT (publication)
- Integrate into molSimplify as a pre-screening filter
- Joint NSF proposal (interpretable AI for materials)
- Guest lecture at MIT on compositional reasoning vs LLMs

---

## Immediate Action Items

### 1. Generate the CSV (High Priority)

**File**: `scripts/generate_kulik_linkers.py`
**Output**: `kulik_22atom_linkers_100.csv`
**Time**: ~5 minutes to generate

### 2. Get Live Demo URL (High Priority)

**Option A**: Render deployment (already exists?)
- Check if komposos-chemistry.onrender.com is live
- If not, redeploy with `render.yaml`

**Option B**: GitHub Codespaces (free, instant)
- Add `.devcontainer/devcontainer.json`
- Link: "Open in GitHub Codespaces" button in README

**Option C**: Hugging Face Spaces (free for demos)
- Create Space with Streamlit app
- Auto-deploys from git push

**Recommendation**: Check Render first (quickest if already deployed)

### 3. Create Screenshot/GIF (Medium Priority)

**Tool**: ScreenToGif or OBS
**Content**:
- MOF Designer page
- Set exact atom count = 22
- Click generate
- Results show "Heavy Atoms: 22" for all ligands
- Export to CSV

**Why**: Visual proof is instant credibility

### 4. Find Her Email (Medium Priority)

**Sources:**
- MIT ChemE faculty page (kulik@mit.edu likely)
- Twitter/X: @HeatherJKulik
- LinkedIn: Heather Kulik
- molSimplify GitHub repo contact info

**Backup**: DM on Twitter first, mention the interview quote

---

## Email Template (Final Version)

```
Subject: Your 22-atom ligand challenge - solved (100 examples attached)

Hi Prof. Kulik,

I recently heard your interview where you mentioned: "I just ask it, please design
me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

I built a tool that solves this using compositional reasoning (category theory +
ZFC set theory) instead of LLMs. It generates ligands with exact atom count control.

**Proof attached:**
→ 100 pre-screened 22-atom ligands (CSV with SMILES, formulas, donor atoms)
→ All 5 verdicts = AGREE (synthesizability, toxicity, stability, activity, conductivity)
→ Ready for molSimplify/DFT validation

**Try it yourself:**
→ Live demo: [DEMO_LINK]
→ Click "MOF Designer" → set 22 atoms → generate
→ Screenshot: [shows UI with exact atom count]

The tool filters by donor atoms (N, O, S) and scores with 5 compositional verdicts.
No training data - it reasons over chemical composition rules.

Would love to hear if these ligands are useful for your active learning pipeline.
Happy to discuss integration with molSimplify.

Best,
James Hawkins
GitHub: https://github.com/Jayhawk314/KOMPOSOS-CHEM
LinkedIn: [your profile]
```

**Attachment**: `kulik_22atom_linkers_100.csv` (small, ~50KB)

---

## Success Metrics

**First Contact (1 week):**
- [ ] Email opened (track with HubSpot or similar)
- [ ] CSV downloaded/opened
- [ ] Demo link clicked
- [ ] Reply received

**Second Contact (1 month):**
- [ ] Docker image pulled
- [ ] Local deployment successful
- [ ] API integration tested

**Third Contact (3 months):**
- [ ] DFT validation results shared
- [ ] Co-authorship discussion
- [ ] Presentation at MIT group meeting

---

## Why This Works

1. **Solves her exact problem** - "22 atoms" is quoted directly from her interview
2. **Zero friction** - CSV opens in Excel, demo is one click
3. **Immediate validation** - She can test with her existing tools right away
4. **Credibility** - 100 examples with full verdicts shows this isn't vaporware
5. **Low ask** - Not asking for money, time, or setup - just feedback
6. **Clear value prop** - Integrates with molSimplify (her tool)
7. **Academic framing** - Compositional reasoning vs LLMs (research angle)

---

## Next Steps

1. ✅ Generate `kulik_22atom_linkers_100.csv`
2. ✅ Check Render deployment status / get live demo URL
3. ✅ Create screenshot/GIF of MOF Designer
4. ✅ Find her email / Twitter DM
5. ✅ Send first contact email
6. ⏳ Wait 1 week
7. 📧 Follow up if no response (mention specific ligand from CSV, ask if it's synthesizable)

**Timeline**: First email sent within 24 hours
