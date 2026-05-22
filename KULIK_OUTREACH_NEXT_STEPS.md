# Heather Kulik Outreach - Ready to Send

## What We Built ✓

1. ✅ **CSV of 50 viable 22-atom ligands**
   - File: `kulik_22atom_linkers_100.csv` (7.3 KB)
   - All have exactly 22 heavy atoms
   - All 5 verdicts = AGREE
   - Ready to attach to email

2. ✅ **Email drafts**
   - File: `KULIK_EMAIL_DRAFT.md`
   - 3 versions (live demo / local install / short DM)
   - Includes follow-up strategy

3. ✅ **Docker deployment plan** (for later)
   - File: `DOCKER_DEPLOYMENT_PLAN.md`
   - Ready if she wants local deployment

---

## Next Action: Send the Email

### Step 1: Check if Your Render Demo is Live

Try visiting one of these URLs:
- https://komposos-chem.onrender.com
- https://komposos-ui.onrender.com

**If live:**
- Use **Email Version A** (with demo link)
- Test the demo first: go to MOF Designer → set 22 atoms → verify it works

**If not live:**
- Use **Email Version B** (local install instructions)
- OR quickly redeploy to Render (15 min):
  ```bash
  # Push latest code to GitHub
  git add .
  git commit -m "Add Kulik outreach materials"
  git push

  # Render will auto-deploy if connected
  # Or manually trigger deploy in Render dashboard
  ```

### Step 2: Find Her Email

**Best bet:**
- MIT ChemE faculty page: https://cheme.mit.edu/profile/heather-j-kulik/
- Email likely: `kulik@mit.edu`

**Backup:**
- Twitter DM: @HeatherJKulik (use Version C)
- LinkedIn: Search "Heather Kulik MIT"

### Step 3: Send

1. Open your email client
2. Copy text from `KULIK_EMAIL_DRAFT.md` (Version A or B)
3. Attach: `kulik_22atom_linkers_100.csv`
4. Update placeholders:
   - Your real contact info
   - Demo URL (if using Version A)
5. **SEND**

---

## Email Checklist

Before hitting send:

- [ ] CSV file attached (7.3 KB)
- [ ] Subject line: "Your 22-atom ligand challenge - solved (50 examples attached)"
- [ ] Demo URL tested (if using Version A)
- [ ] GitHub repo is public: https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem
- [ ] Your real email signature (replace "James Hawkins" with your info)
- [ ] Spell-check done
- [ ] No typos in formulas (C15H9N2O5, etc.)

---

## If She Replies Positively

**She likes the CSV and wants more:**
→ Offer to generate more (100, 500, any atom count)
→ Offer to filter by specific donor atoms (N-only, O-only, etc.)
→ Send her the GitHub repo for local use

**She wants to integrate with molSimplify:**
→ Share the API endpoint: `POST /api/v1/design-mof-linker`
→ Example Python code:
```python
import requests
response = requests.post("http://localhost:8000/api/v1/design-mof-linker",
    headers={"X-API-Key": "your-key"},
    json={"exact_atoms": 22, "num_candidates": 100})
```

**She wants to test with DFT:**
→ Offer to co-author a validation paper
→ "KOMPOSOS Compositional Reasoning vs. LLM Generation for MOF Ligands"
→ Validate synthesizability scores with DFT

**She wants you to present:**
→ Offer virtual talk to her group
→ Topic: "Why LLMs Fail at Exact Constraints (and How Category Theory Fixes It)"

---

## If She Doesn't Reply (1 week)

Send follow-up (see `KULIK_EMAIL_DRAFT.md` for text):

**Subject:** Quick question about linker #13 (6 N donors)

Ask specific chemistry question about one of the linkers. This:
1. Shows you care about real chemistry (not just spam)
2. Gives her an easy response (technical question vs. vague "thoughts?")
3. Positions you as learner, not salesperson

---

## Timeline

**Today (Day 0):**
- ✅ CSV generated
- ✅ Email drafted
- ⏳ Check Render status
- ⏳ Send email

**Day 1-7:**
- Wait for response
- Don't spam

**Day 7:**
- If no reply, send follow-up

**Day 14:**
- If still no reply, try Twitter DM

**Day 30:**
- Move on to other outreach (other MOF profs, materials companies)

---

## Success Definition

**Minimum success:** She opens the email and looks at the CSV
**Good success:** She replies with feedback (even if critical)
**Great success:** She tests one ligand with DFT
**Excellent success:** Co-author validation paper
**Unicorn success:** She integrates into molSimplify

---

## Alternative Outreach (if Heather doesn't respond)

**Other MOF researchers:**
- Prof. Omar Yaghi (UC Berkeley) - invented MOFs
- Prof. Jeffrey Long (UC Berkeley) - gas storage MOFs
- Prof. Mircea Dincă (MIT) - Heather's colleague
- Prof. Wenbin Lin (UChicago) - catalytic MOFs

**Companies:**
- NuMat Technologies (gas storage MOFs, $75M raised)
- Mosaic Materials (CO2 capture, $30M raised)
- MOF Technologies (UK, commercial MOFs)

**Method:** Same email template, different use cases:
- Yaghi: "novel topologies" instead of "22 atoms"
- Long: "H2 storage linkers" instead of "CO2 capture"
- Companies: "rapid screening for scale-up" instead of "DFT validation"

---

## Files You Need

All ready in your repo:

1. `kulik_22atom_linkers_100.csv` - attach to email
2. `KULIK_EMAIL_DRAFT.md` - copy text from here
3. `scripts/generate_kulik_linkers.py` - if she wants different atom counts
4. `Dockerfile.kulik` - if she wants local Docker deployment
5. This file - your action checklist

---

## Ready?

You have everything you need to send the email **right now**. Just:

1. Check Render status (5 min)
2. Choose email version (A or B)
3. Find her email (2 min)
4. Send (1 min)

**Total time: < 10 minutes**

Good luck! 🚀
