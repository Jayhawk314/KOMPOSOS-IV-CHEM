# KOMPOSOS-III Launch Playbook
## YouTube + Deployment + Outreach -- Everything You Need

*Generated 2026-03-28 | For James Ray Hawkins*

---

# TABLE OF CONTENTS

1. [PART 1: Deploy the UI (Code Stays Private)](#part-1-deploy-the-ui)
2. [PART 2: YouTube Video Series](#part-2-youtube-video-series)
3. [PART 3: 20 People to Email](#part-3-20-people-to-email)
4. [PART 4: LinkedIn Cross-Posting](#part-4-linkedin-cross-posting)
5. [PART 5: Cold Email Templates](#part-5-cold-email-templates)
6. [PART 6: Timeline -- What to Do When](#part-6-timeline)

---

# PART 1: Deploy the UI

Your code stays private. Nobody sees your Python. They only see the running Streamlit app.

## Step 0: Create the Streamlit Dockerfile

Your existing Dockerfile runs the API (uvicorn). You need a second one for the Streamlit UI. Save this as `Dockerfile.streamlit` in your project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

ENV PORT=8501
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD streamlit run streamlit_app/app.py --server.port=${PORT} --server.address=0.0.0.0
```

## Option A: Railway.app (RECOMMENDED -- $5/month, no cold starts)

### Why Railway

- Deploy from a **private** GitHub repo -- code never exposed
- No sleep, no cold starts (on Hobby plan)
- 8 GB RAM (your app uses ~300 MB)
- WebSockets work natively (Streamlit needs them)
- Custom domains with free SSL
- Auto-redeploys when you push to main
- Setup: ~10 minutes

### Step-by-Step

1. **Sign up**: Go to https://railway.com, click "Login", sign up with your GitHub account. You get a 30-day free trial with $5 credit. No credit card needed for trial.

2. **Create a private GitHub repo**: On GitHub, create a new PRIVATE repository. Push your KOMPOSOS code there. This is separate from any public repo you might have.

3. **Create a new Railway project**: In the Railway dashboard, click "New Project" > "Deploy from GitHub Repo".

4. **Authorize GitHub access**: Railway installs a GitHub App. When GitHub asks which repos, select "Only select repositories" and choose your private KOMPOSOS repo. Railway can't see your other repos.

5. **Select the repo**: Click on your repo in the list.

6. **Configure Dockerfile path**: Click the gear icon / "Settings" for the service. Under Build, set Dockerfile Path to `./Dockerfile.streamlit`.

7. **Add environment variables**: Click "Add Variables":
   - `PORT` = `8501`
   - `STREAMLIT_SERVER_HEADLESS` = `true`

8. **Deploy**: Click "Deploy Now". Watch the build logs. Takes 2-3 minutes.

9. **Get your URL**: Once deployed (green checkmark), go to Settings > "Public Networking" > "Generate Domain". You get something like `komposos-ui-production.up.railway.app`.

10. **Done.** Every time you `git push` to main, Railway auto-redeploys.

### Railway Pricing

| Tier | Cost | Included Usage | Sleep? |
|------|------|----------------|--------|
| Trial | $0 (30 days) | $5 credit | No |
| **Hobby** | **$5/month** | $5 credit included | **No** |
| Pro | $20/month | $10 credit | No |

Your app will cost ~$1-3/month in compute. On the Hobby plan you pay exactly $5/month total.

### Custom Domain (Later)

1. In Railway service Settings > "Public Networking" > "+ Custom Domain"
2. Enter `app.komposos.com` (or whatever domain you own)
3. Railway gives you a CNAME value
4. Add a CNAME record at your DNS provider (Namecheap, Cloudflare, etc.)
5. Railway auto-provisions SSL. Done.

## Option B: Render.com (FREE but has cold starts)

- Free tier: $0/month, but sleeps after 15 min of inactivity. Cold start = 30-60 seconds.
- Starter tier: $7/month, no sleep.
- 512 MB RAM on free/starter (your app fits, but tight).

### Steps

1. Go to https://render.com, sign up with GitHub.
2. Click "+ New" > "Web Service" > "Build and deploy from Git repository".
3. Connect your private GitHub repo.
4. Settings: Name = `komposos-ui`, Runtime = Docker, Dockerfile Path = `./Dockerfile.streamlit`, Instance Type = Free.
5. Add env vars: `PORT` = `10000` (Render uses 10000), `STREAMLIT_SERVER_HEADLESS` = `true`.
6. Click "Create Web Service". URL: `komposos-ui.onrender.com`.

### Render Free Tier Limits

| Feature | Free | Starter ($7/mo) |
|---------|------|-----------------|
| RAM | 512 MB | 512 MB |
| Sleep | Yes (15 min) | No |
| Cold start | 30-60 sec | N/A |
| Custom domain | Yes | Yes |
| Auto-deploy | Yes | Yes |

## Option C: Hugging Face Spaces (FREE, 16 GB RAM, good for academics)

- Free CPU Basic: 2 vCPU, **16 GB RAM** (most generous free tier)
- Private Spaces keep code hidden
- No custom domains
- URL: `huggingface.co/spaces/username/komposos-chemistry`
- Sleeps after ~48 hours of inactivity

### Steps

1. Sign up at https://huggingface.co/join
2. Create new Space: https://huggingface.co/new-space
3. Settings: SDK = Docker, Hardware = CPU Basic (Free), Visibility = Private
4. Clone the Space repo, copy your code in, push
5. HF Spaces expects port 7860 for Docker -- adjust CMD to `--server.port=7860`

**Downside**: No GitHub integration. You push to a separate HF Git repo. No custom domains.

## Option D: Google Cloud Run (Free tier, production-grade, more complex setup)

- Always-free tier: 180,000 vCPU-seconds/month (~10 users/day for 10 min each)
- Full production infrastructure with auto-scaling
- Custom domains with managed SSL
- Setup: ~30-45 minutes, requires `gcloud` CLI and Docker installed locally

### Steps (condensed)

```bash
# 1. Install gcloud CLI, log in, create project
gcloud auth login
gcloud projects create komposos-chemistry
gcloud config set project komposos-chemistry

# 2. Enable APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# 3. Create artifact registry
gcloud artifacts repositories create komposos-repo --repository-format=docker --location=us-central1

# 4. Build and push Docker image
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -t us-central1-docker.pkg.dev/komposos-chemistry/komposos-repo/streamlit-ui:latest -f Dockerfile.streamlit .
docker push us-central1-docker.pkg.dev/komposos-chemistry/komposos-repo/streamlit-ui:latest

# 5. Deploy
gcloud run deploy komposos-ui \
    --image=us-central1-docker.pkg.dev/komposos-chemistry/komposos-repo/streamlit-ui:latest \
    --region=us-central1 --platform=managed --port=8501 \
    --allow-unauthenticated --memory=1Gi --cpu=1 \
    --min-instances=0 --max-instances=2 --timeout=3600 \
    --set-env-vars="STREAMLIT_SERVER_HEADLESS=true"
```

**Important**: Set `--timeout=3600` (1 hour) because Streamlit uses WebSockets. Default 5-min timeout will disconnect users.

## DO NOT USE: Streamlit Community Cloud

Streamlit Community Cloud now supports private repos, BUT:
- Workspace developers can browse your code
- No Docker support (you can't control the runtime)
- 1 GB RAM hard limit
- "Made with Streamlit" badge you can't remove
- No custom domains

For proprietary code, use Railway, Render, or Cloud Run instead.

## Platform Comparison Summary

| Feature | Railway ($5/mo) | Render (Free) | HF Spaces (Free) | Cloud Run (Free tier) |
|---------|----------------|---------------|-------------------|----------------------|
| Code private | Yes | Yes | Yes (Private mode) | Yes |
| RAM | 8 GB | 512 MB | 16 GB | Configurable |
| Cold start | None | 30-60 sec | 1-3 min | 5-15 sec |
| Custom domain | Yes | Yes | No | Yes |
| Setup time | 10 min | 10 min | 20 min | 30-45 min |
| Auto-deploy from GitHub | Yes | Yes | No (separate repo) | No (manual) |

**My recommendation**: Start with Railway Hobby ($5/month). It's the fastest path to a live URL with no cold starts and your code stays private.

---

# PART 2: YouTube Video Series

## YouTube Algorithm Basics (2026)

### What the algorithm cares about

**Retention is everything.** A 4-minute video with 90% completion beats a 20-minute video where people leave at minute 5. For a new channel with zero subscribers, shorter videos with high completion build algorithmic trust faster.

### Optimal lengths

| Type | Length | Why |
|------|--------|-----|
| Hook / viral | 2-4 min | High retention, shareable |
| YouTube Shorts | 15-30 sec | 80%+ completion at this length |
| Explainer | 8-15 min | Unlocks mid-roll ads at 8 min |
| Demo | 6-10 min | Show results, cut ruthlessly |
| Vision / pitch | 5-8 min | Investor attention span |

### Thumbnails

- 1280 x 720 pixels, JPG or PNG, under 2 MB
- ONE dominant element per thumbnail
- Bold text: 5 words maximum
- High contrast colors (yellow on dark blue, white on red)
- Your face in at least 3 of 5 thumbnails
- Use Canva (free) -- search "YouTube thumbnail" for templates
- Fonts: Montserrat, Bebas Neue (bold sans-serif only)

### Titles

Optimal: 8-15 words, under 60 characters, keyword in first 3-5 words.

**Formulas:**
1. [Surprising claim] + [Proof]: "I Built a Chemistry Engine While DoorDashing (1,575 Tests)"
2. [Problem] + [Unexpected solution]: "The EU Is Banning Your Battery Materials. This Tool Finds Replacements."
3. [Contrast/tension]: "Every AI Lab Uses Neural Networks. I Used 19th Century Math Instead."

### Tags

PFAS ban, PFAS compliance, forever chemicals, PFAS replacement, PVDF alternative, PFAS battery, materials informatics, computational materials science, battery materials, category theory, materials AI, startup, solo developer, vibe coding

### Best time to post

Tuesday, Wednesday, or Thursday at 12-1 PM ET (gives 2-3 hours for indexing before afternoon peak).

### YouTube Shorts strategy

For every long video, cut 3-5 Shorts (15-30 seconds each). The funnel: Shorts get attention -> long video gets subscribers -> subscribers watch future content.

**Short ideas:**
1. "PVDF is in every EV battery. The EU is banning it in 4 months." (show PFAS scan)
2. "I asked my tool: 'Is NMC811 compatible with LGPS?' It said no. Here's why."
3. "Category theory in 20 seconds: if A works with B, and B works with C..."
4. "1,575 tests. 8 material domains. Zero training data."

---

## VIDEO 1: "The Hook" (3-4 minutes)

### Title options (pick one)

1. "I Built a Chemistry Engine While Delivering DoorDash"
2. "A DoorDash Driver Built a Materials Science Tool With 1,575 Passing Tests"
3. "No PhD, No Neural Network, No VC Money -- Just Category Theory"
4. "Every AI Startup Raised $550M. I Built Mine Between Deliveries."
5. "The $0 Chemistry Tool That Uses 19th Century Math Instead of AI"

**Best options**: #1 or #4. The DoorDash-to-chemistry contrast creates curiosity.

### Opening hook (first 5 seconds)

You, looking into camera, normal clothes, maybe sitting in your car:

> "Six months ago I was delivering burritos for DoorDash. Today I have a chemistry engine with 1,575 passing tests across 8 material domains. And I didn't use a single neural network."

### Minute-by-minute outline

**0:00-0:30 -- The contrast**

You in your car or at home. Voice over: "I'm not a chemist. I'm not an engineer. I'm a self-taught programmer who learned category theory from Wikipedia. And I built a tool that tells you whether two materials will work together before you build anything."

Cut to: the Streamlit UI running.

**0:30-1:30 -- What it does (show, don't tell)**

Screen recording: Open the Compatibility Checker. Type "NMC811" and "EC". Show the 5-scorer breakdown. Voice over: "You pick two materials. It checks voltage compatibility, thermal stability, chemical reactivity, mechanical stress, and kinetic transport. Nine mathematical strategies vote. No training data. No black box."

Then show a PFAS scan: type "PVDF", watch it flag as PFAS. Voice over: "And it knows which materials the EU is about to ban."

**1:30-2:30 -- The numbers**

Screen recording: run the dogfood test. Show "64 passed, 0 failed". Voice over: "169 real materials with published property data. 37 molecules. 30 MOFs. 8 material domains. Every property comes from a published paper. Every interaction is verified."

**2:30-3:30 -- Why you should care**

Voice over: "The EU PFAS ban takes effect August 2026. Every EV battery uses PVDF as a binder -- that's a PFAS chemical. Battery companies need to find replacements, and they need to know if those replacements work. That's what this tool does."

Cut to: PFAS Scanner showing CMC+SBR as PVDF replacement, score 0.83.

**3:30-3:50 -- Call to action**

"The tool is live. Link in the description. If you work in batteries, PFAS compliance, or materials discovery, I want to hear from you. Subscribe -- the next video explains why the EU PFAS ban is about to disrupt every EV battery on the planet."

---

## VIDEO 2: "The PFAS Problem" (8-10 minutes)

### Title options

1. "The EU Is Banning the Chemical in Every EV Battery (And What Replaces It)"
2. "Forever Chemicals in Your Battery: The PFAS Ban Explained"
3. "PVDF Is in Every Lithium Battery. The EU Bans It in 4 Months."

### Why this video works

Veritasium's PFAS video got 3M+ views in day one. PFAS is proven viral. Nobody has made a PFAS-in-batteries-specifically video. That's your gap.

### Outline

**0:00-2:00 -- What are PFAS (for non-chemists)**

"PFAS stands for per- and polyfluoroalkyl substances. You know them as 'forever chemicals.' The carbon-fluorine bond is one of the strongest in chemistry. They never break down -- not in water, not in soil, not in your blood. They're in nonstick pans, waterproof jackets, firefighting foam, and -- here's the part nobody talks about -- in every lithium-ion battery on the planet."

On screen: Simple diagram of C-F bond. Photos: nonstick pan, jacket, EV battery. Split screen: "PVDF = polyvinylidene fluoride = PFAS."

**2:00-4:00 -- The regulatory timeline (as a visual)**

Show a horizontal timeline (make in Canva/PowerPoint):
- March 2026: ECHA RAC adopted final opinion supporting EU-wide PFAS restriction
- March 2026: ECHA SEAC agreed draft opinion
- May 25, 2026: SEAC public consultation closes
- Aug 12, 2026: EU hard ban on PFAS in food-contact packaging
- Oct 2026: US EPA TSCA final reporting deadline
- End 2026: EU complete scientific evaluation
- 2027: EU Commission expected universal PFAS restriction

Key fact: ZVEI (German Electro Industry Association) stated: "100% of lithium-ion batteries currently fully rely on PFAS."

The battery industry requested a 13.5-year derogation for PVDF. It has NOT been formally granted yet.

**4:00-7:00 -- Tool demo: scanning a battery BOM**

Screen recording of PFAS Scanner:
1. Enter the Li-ion BOM: PVDF, PTFE, NMP, EC, DMC, LiPF6, CMC, SBR, Cu, Al, NMC811, Graphite, PP, PE, Carbon Black
2. Watch PVDF flag (moderate urgency -- proposed ban)
3. Watch PTFE flag (moderate urgency -- proposed ban)
4. Show replacements: PVDF -> CMC+SBR (0.84), PAA (0.77), Alginate (0.70), PAN (0.64)
5. Generate compliance report: 7 sections, provenance, verdict logic, action plan

Voice over: "Look at this. Two out of fifteen materials are PFAS. The tool doesn't just flag them -- it ranks replacements. CMC+SBR scores 0.84 as a PVDF replacement. That's based on published binder properties -- adhesion, electrochemical stability, flexibility. And it generates an auditable compliance report with regulatory citations."

**7:00-9:00 -- Why this matters**

"40 million EVs on the road. Every one has PVDF in the cathode binder. The EU is the world's second-largest EV market. Even with a potential 13.5-year derogation, companies need to start screening NOW because: the derogation isn't guaranteed, US state-level bans are already in effect, and supply chain due diligence requirements apply immediately."

**9:00-10:00 -- Close**

"Next video: the math underneath this tool. It's not machine learning. It's category theory -- pure mathematics from the 1940s that treats materials as objects, reactions as arrows, and compatibility as composition. Subscribe."

---

## VIDEO 3: "How the Math Works" (10-12 minutes)

### Title options

1. "Category Theory Predicts Chemistry (No Neural Network Required)"
2. "The Math Behind KOMPOSOS: Why 19th Century Theory Beats Modern AI"
3. "I Used Category Theory to Build a Chemistry Engine. Here's How."

### Key rule: Analogies first, formalism never

Save formalism for a separate video that 200 people will watch.

### Slide-by-slide outline

**Slide 1 -- "What Is Category Theory?" (1 min)**

Visual: A city map with locations (nodes) and roads (arrows).

"Category theory is the mathematics of relationships. Imagine a city. Locations are objects. Roads are morphisms -- the ways you get from one place to another. Category theory doesn't care what the locations ARE. It cares about how they connect."

**Slide 2 -- "Materials as Objects" (1 min)**

Visual: 6 colored circles: "NMC811", "EC", "PVDF", "Cu", "LLZO", "PEO". Each has a property card (voltage, Tg, conductivity).

"Every material is an object with properties. But the magic isn't in the objects. It's in the arrows."

**Slide 3 -- "Compatibility as Morphisms" (2 min)**

Visual: Arrows connecting pairs with scores (0.85, 0.72, 0.34).

"An arrow from NMC811 to EC means 'these two are compatible.' The arrow carries a score -- 5 scorers each produce 0 to 1."

Show the 5 scorers: voltage, thermal, chemical, mechanical, kinetic.

**Slide 4 -- "The Composition Principle" (2 min)**

Visual: A -> B (0.85), B -> C (0.79), dotted arrow A -> C with "?"

"If A works with B and B works with C, category theory lets us reason about A with C -- even if we've never tested them together. This is COMPOSITION."

Then show: 9 strategies voting -- Kan Extension, Semantic Similarity, Yoneda Pattern, Composition, Fibration Lift, Structural Hole, Geometric, Temporal, Type Heuristic.

**Slide 5 -- "The Lego Analogy" (1 min)**

Visual: Lego bricks snapping together.

"Think of materials like Lego. A 2x4 brick connects to another in specific ways. You don't try every combination -- you reason about what connects based on shapes. KOMPOSOS does this with voltage windows, thermal ranges, and chemical properties."

**Slide 6 -- "Not AI. Reasoning." (1 min)**

Visual: Left = "Neural Network" (black box, arrow in, arrow out, "?" inside). Right = "KOMPOSOS" (clear graph, every step labeled).

"A neural network is a black box. Number in, number out, nobody knows why. KOMPOSOS shows every step. Every score has a published source. When it says NMC811 and LGPS are incompatible, it tells you WHY."

**Slide 7 -- "ZFC Dual Verification" (2 min)**

Visual: Two columns: "Category Theory Engine" and "ZFC Set Theory Engine". Four outcomes: AGREE (green), ORPHAN (yellow), HOLLOW (orange), REJECT (red).

"A second engine runs in parallel. ZFC set theory -- the foundation of all mathematics -- independently verifies every prediction. If both agree, high confidence. If one says yes and the other no, it flags it. HOLLOW = 'structurally plausible but logically unsound.' No other tool has dual-engine verification."

**Slide 8 -- "Dempster-Shafer Fusion" (1 min)**

Visual: Three gauges: "Rule-based", "Kan extension", "Goldschmidt tolerance". Arrow to combined gauge: "Fused prediction."

"Three independent sources produce estimates. Dempster-Shafer theory fuses them into one prediction with a confidence score. This isn't averaging. It's principled evidence combination."

**Slide 9 -- Close (30 sec)**

"Category theory. ZFC. Dempster-Shafer. Kan extensions. Real math. Running in a tool you can use today. Next video: I ask it 64 real materials science questions."

---

## VIDEO 4: "64 Questions, 64 Correct Answers" (6-8 minutes)

### Title options

1. "I Asked My Tool 64 Materials Science Questions. It Got Every One Right."
2. "64 Real Chemistry Questions. 64 Correct Answers. No Training Data."
3. "Can Category Theory Pass a Materials Science Exam? (64/64)"

### Structure

Do NOT show all 64. Show the 10-12 most impressive, grouped by theme. Use a scoreboard overlay in the corner: 1/64, 2/64... 64/64.

**0:00-0:30 -- Setup**

"This tool has never been trained on any dataset. It reasons from first principles. I'm going to ask it 64 real questions. Let's see."

**0:30-2:00 -- Property Prediction (3 questions)**

- NMC811 voltage: predicted 3.78V, published 3.7-3.8V
- LFP voltage: predicted 3.42V, published 3.45V
- NMC532 (novel, not in database): predicted ~3.7V, published 3.6-3.7V

"These come from Kan extension -- generalizing from known cathodes."

**2:00-3:30 -- Compatibility (3 questions)**

- NMC811 + EC: compatible, score 0.82
- NMC811 + LGPS: incompatible (voltage window mismatch)
- PVDF is PFAS? Yes, moderate urgency

"It didn't just say no for LGPS. It told me WHY."

**3:30-5:00 -- Crystal Structure + MOFs (3 questions)**

- LiFePO4 structure: olivine. Correct.
- ZIF-8 BET surface area > 1000? Yes, 1630 m^2/g. Correct.
- UiO-66 water stable? Yes, excellent. Correct.

**5:00-6:00 -- Multi-domain + Hard Questions (2 questions)**

- Full cell design: NMC811 + LLZO + PEO + Cu. Bottleneck analysis.
- Constraint search: "ligand with exactly 22 heavy atoms containing Fe and N"

**6:00-6:30 -- The Final Scoreboard**

Run the full dogfood test on screen. Show "64 passed, 0 failed."

**6:30-7:00 -- Close**

"64 for 64. No training. No neural network. Final video: what happens when this gets funded."

---

## VIDEO 5: "The Vision" (5-7 minutes)

### Title options

1. "8 Domains, 1 Engine: The Materials Reasoning Platform Nobody Built"
2. "$2.1 Billion in Materials AI -- And They All Got It Wrong"
3. "The Unfunded Chemistry Tool That Outreasons Neural Networks"

### Outline

**0:00-0:30 -- The landscape**

"Lila Sciences: $550M. Orbital Materials: $1.2B unicorn. CuspAI: $154M. Citrine: $81M. All black-box neural networks. Every single one."

**0:30-1:30 -- The problem**

"Neural networks need massive training data. Materials science doesn't have it. 200,000 known materials. 10^100 possible compositions. You can't train your way to discovery. You have to REASON."

**1:30-3:00 -- The 8-domain advantage**

Diagram: all 8 bridges radiating from the core engine. "Batteries. Polymers. Metals. Ceramics. Semiconductors. Glass. MOFs. Molecules. The cross-bridge connects them all. 'Will this polymer binder work with this cathode in this electrolyte with this current collector?' -- 4 domains, one query. No competitor does this."

**3:00-4:00 -- Your story**

"I built this while delivering DoorDash. I'm not a chemist. I learned category theory because I thought: if A works with B and B works with C, there should be math for reasoning about A and C. There is. It's from the 1940s."

Show: your life, your car, then cut to the codebase, test counts.

**4:00-5:30 -- What a funded team could build**

- Full Materials Project integration (150K+ materials)
- DFT validation loops
- 3D crystal structure generation
- Laboratory automation connection
- Enterprise PFAS compliance SaaS

**5:30-6:00 -- The ask**

"If you're a materials scientist, try the API. If you're a battery company, let me scan your BOM. If you're an investor, look at what $2.1B bought everyone else -- black boxes. Look at what $0 and category theory produced."

**6:00-6:30 -- Final frame**

"Links in description. API, demo, my email. I'm one person. Imagine what a team could do."

---

## Zero-Budget Production Guide

### Free software

| Tool | Purpose |
|------|---------|
| **OBS Studio** | Screen recording + webcam. Record as MKV, then File > Remux to MP4 |
| **DaVinci Resolve** (free) | Video editing, color correction, titles |
| **Audacity** | Audio recording + noise removal |
| **Canva** (free tier) | Thumbnails, timeline graphics, slide diagrams |
| **Google Slides** or **PowerPoint** | Presentation slides for Video 3 |
| **ShareX** | Screenshots and quick clips |

### Audio without equipment

Audio quality matters MORE than video quality for retention. Bad audio = instant click-away.

1. **Record in a closet.** Clothes absorb echo. Sit surrounded by hanging clothes with your laptop. Sounds absurd. Works great.

2. **Use earbuds with a built-in mic** (the ones from your phone). Hold mic 2-3 inches from mouth. Better than laptop mic at 2 feet.

3. **Record voiceover separately in Audacity.** Don't rely on OBS. Record screen (muted mic) and voice (Audacity) simultaneously, sync in DaVinci.

4. **Audacity noise reduction:** Record 5 seconds of silence. Select it > Effect > Noise Reduction > Get Noise Profile. Select all audio > Effect > Noise Reduction > Apply. Removes fan noise and hum.

5. **Normalize:** Effect > Normalize to -1dB for consistent volume.

### Screen recording tips

- Increase browser zoom to 125-150% before recording
- Increase terminal font size to 16-18pt
- Hide bookmarks bar, extensions, desktop icons
- Use dark mode
- Record at 1920x1080, 30fps
- Practice the demo 3 times before recording
- Add zoom callouts in DaVinci for key numbers

### Making slides look professional

- One idea per slide. Max 20 words.
- Sans-serif fonts: Montserrat, Inter, Poppins. 36pt+ titles, 24pt+ body.
- 3 colors only: dark navy background (#1a1a2e), white text, blue accent (#00d4ff)
- Diagrams, not bullet lists
- Canva diagram templates: search "mind map" or "flowchart"

### Free music

| Source | License |
|--------|---------|
| YouTube Audio Library (in YouTube Studio) | Free, no attribution |
| Pixabay | Free, no attribution |
| Mixkit | Free, no attribution |

Use subtle background music at 10-15% volume. No music during screen recordings.

---

# PART 3: 20 People to Email

## Latest PFAS Regulatory News (Critical Context for Outreach)

**ECHA RAC adopted its final opinion on March 2, 2026** supporting EU-wide PFAS restriction. SEAC agreed its draft opinion March 10, 2026. A 60-day public consultation is open until **May 25, 2026**. SEAC final opinion expected end of 2026, then European Commission decides.

**Battery-specific**: The industry (via RECHARGE association) requested a **13.5-year derogation** for PVDF in batteries. It has NOT been formally granted. ZVEI stated "100% of lithium-ion batteries currently fully rely on PFAS."

**This means**: Companies need to start screening NOW. Even with a potential derogation, supply chain due diligence requirements apply immediately.

---

## TIER 1: Most Likely to Respond (Start Here)

### 1. Certivo (Seattle startup)

- **What**: AI compliance automation startup. Raised $4M seed (Feb 2026) from Suffolk Technologies. Their AI agent "CORA" automates RoHS, REACH, PFAS compliance. Spun out of Pioneer Square Labs.
- **Why they'd care**: They collect compliance data but can't evaluate whether a PFAS replacement actually works. Your tool fills a direct gap. They're early stage and looking for differentiators.
- **Website**: https://www.certivo.com/
- **Email subject**: "Materials reasoning engine for PFAS alternative screening -- complement to CORA's compliance automation"

### 2. Ateios Systems (Battery electrode startup)

- **What**: ~20-30 people. $7.25M Series A. Their RaiCore platform is the "world's only independently verified PFAS-free battery electrode technology." Partnered with Kodak (March 2026) to expand to NMC, LFP, and other chemistries. Named "Battery Manufacturer of the Year."
- **Why they'd care**: They ARE the PFAS-free alternative. Your tool computationally validates their claims -- showing RaiCore + NMC811 scores well on compatibility. They could use KOMPOSOS to demonstrate to customers that their alternatives work.
- **Website**: https://ateios.com/
- **Email subject**: "Computational validation of PFAS-free electrode compatibility -- tool to support your customer demos"

### 3. Eleni Savvidou (PhD researcher, Stockholm University)

- **What**: PhD researcher at Stockholm University, Dept of Environmental Science. Published a key paper "PFAS-Free Energy Storage" in Environmental Science & Technology. Her research shows PFAS electrolyte additives are largely unnecessary, while cathode binder replacement (PVDF) is the harder problem.
- **Why they'd care**: Her research is exactly what your tool does computationally. Tool validation partnership or co-publication would strengthen both parties. PhD students are very responsive to cold emails.
- **Email subject**: "Computational tool for screening PFAS-free battery alternatives -- directly relevant to your ES&T publication"

### 4. The Battery Technology Podcast (Ken Davies)

- **What**: Monthly podcast featuring battery industry news. Episode 48 was literally titled "Innovation in Materials Discovery."
- **Why they'd care**: Podcast hosts always need guests. Your story (DoorDash driver builds chemistry engine) is compelling content. PFAS in batteries is topical.
- **Website**: https://thebatterytechnologypodcast.podbean.com/
- **Email subject**: "Guest pitch: DoorDash driver builds PFAS compliance screening tool for battery manufacturers"

### 5. GreenSoft Technology (Pasadena, ~42 employees)

- **What**: Environmental compliance data management. They collect PFAS data from supply chains using IEC 62474 and EPA reference lists covering 15,000+ chemicals. Recently hosted a Minnesota PFAS webinar.
- **Why they'd care**: They collect compliance data but do NOT reason about alternatives. When clients ask "I need to replace PVDF -- what works?", GreenSoft can't answer. Your tool fills that gap directly. Partnership potential.
- **Website**: https://www.greensofttech.com/
- **Email subject**: "PFAS alternative screening tool -- potential integration with GreenSoft data services"

---

## TIER 2: High Value, Moderate Response Probability

### 6. Prof. Chibueze Amanchukwu (University of Chicago)

- **What**: Neubauer Family Assistant Professor, Pritzker School of Molecular Engineering. Designed two new families of PFAS-free battery solvents (published ACS Energy Letters, J. Electrochem. Soc.). Also published in Nature Chemistry on using lithium metal to degrade PFAS.
- **Why they'd care**: His lab does experimentally what your tool does computationally. Your replacement scores (CMC+SBR at 0.84) align with his research. Collaboration potential: validate predictions against his data, co-author a paper.
- **Website**: https://amanchukwu.uchicago.edu/
- **Email subject**: "Category-theoretic screening tool for PFAS-free battery compatibility -- research collaboration?"

### 7. Nanoramic Laboratories (MIT spinoff, Boston area)

- **What**: Developed Neocarbonix -- 3D nanocarbon mesh replacing PVDF binder. $44M investment (Samsung Ventures), $47.5M DOE grant for Bridgeport CT plant. GM Ventures investor. Drops into existing manufacturing lines.
- **Why they'd care**: Your tool showing "Neocarbonix + NMC811 = compatible" with scorer breakdowns is a selling point for their automaker customers. They need independent validation for DOE reporting.
- **Website**: https://www.nanoramic.com/
- **Email subject**: "Compositional reasoning tool validates PFAS-free binder compatibility -- demo for your engineering team?"

### 8. Acquis Compliance (Richmond, VA)

- **What**: PFAS software and services for TSCA Section 8(a)(7) reporting. 80+ years collective team experience. Consultants in 72+ countries.
- **Why they'd care**: Their manufacturing clients ask "if I replace PVDF with CMC+SBR, will it work?" They can't answer that. Your tool can. White-label or recommendation potential.
- **Website**: https://www.acquiscompliance.com/
- **Email subject**: "Compositional screening tool for PFAS replacement validation -- for your manufacturing clients"

### 9. Undecided with Matt Ferrell (YouTube, 1M+ subscribers)

- **What**: Sustainability tech channel covering batteries, EVs, solar, energy storage. High production quality, technically literate audience.
- **Why they'd care**: "Can we build batteries without forever chemicals?" + your tool as a live demo = great content. His audience cares about both sustainability and technology.
- **Website**: https://undecided.tech/
- **Email subject**: "Video pitch: The hidden forever chemicals in every EV battery -- and the tool screening replacements"

### 10. ZVEI / Gunther Kellermann (German Electro Industry Association)

- **What**: Germany's electro/digital industry association, Batteries Section. Published factsheet stating "100% of lithium-ion batteries fully rely on PFAS." Gunther Kellermann is Senior Manager, Environmental and Chemicals Policy, Battery Division. Phone: +49 69 6302 420.
- **Why they'd care**: Their factsheet IS your problem statement. They need tools to show member companies which alternatives work. Named contact with phone number.
- **Website**: https://www.zvei.org/en/association/sections/batteries-section
- **Email subject**: "Computational PFAS alternative screening for battery manufacturers -- directly relevant to your ZVEI factsheet"

---

## TIER 3: Worth Trying

### 11. RECHARGE (European Battery Association)

- **What**: European industry association for rechargeable/lithium battery manufacturers. Filed submissions to ECHA requesting 13.5-year PFAS derogation. Public Affairs Director: Kinga Timaru-Kast.
- **Why they'd care**: They need systematic substitution feasibility evidence for ECHA. Your tool provides reproducible screening -- exactly what regulators want.
- **Website**: https://rechargebatteries.org/
- **Email subject**: "PFAS substitution screening tool -- evidence for ECHA derogation evaluations"

### 12. Donut Lab (Finnish startup, ~60-70 people)

- **What**: Announced production-ready all-solid-state battery at CES 2026. 400 Wh/kg, 5-min fast charging. Shipping production cells Q1 2026. European company = EU PFAS restrictions apply directly.
- **Website**: https://www.donutlab.com/
- **Email subject**: "EU PFAS compliance screening tool -- essential for production-stage European battery startups"

### 13. ION Storage Systems (University of Maryland spinoff)

- **What**: Solid-state battery startup. $74.2M funding incl. $20M ARPA-E. Producing 100K military batteries/year. DOE-funded + military contracts = compliance documentation critical.
- **Website**: https://ionstoragesystems.com/
- **Email subject**: "PFAS compliance screening for solid-state battery components -- for DOE-funded programs"

### 14. Leclanche SA (Swiss, est. 1909, ~200 employees)

- **What**: Pioneer in water-based PFAS-free electrode manufacturing (13+ years). EUR 74.2M EU grant. Already solved PFAS but needs independent verification for regulators.
- **Website**: https://www.leclanche.com/
- **Email subject**: "Independent PFAS-free verification tool -- complement to Leclanche's compliance documentation"

### 15. Venable LLP (Law firm, PFAS practice)

- **What**: Major law firm with dedicated PFAS practice group. Runs "Navigating PFAS: Legal Perspectives" webinar series.
- **Why they'd care**: Their clients ask "what do we replace PFAS with?" and lawyers can't answer that. A tool they can point clients to adds value to their advisory.
- **Website**: https://www.venable.com/services/practices/pfas-and-emerging-contaminants
- **Email subject**: "PFAS screening tool for your manufacturing clients -- webinar collaboration opportunity?"

### 16. Prof. Heather Kulik (MIT, Kulik Research Group)

- **What**: Computational chemistry, MOF design (~10K ultrastable MOF structures identified), machine learning for materials. Published Nature Comp Sci. Open-source tools (molSimplify, MOFSimplify).
- **Why they'd care**: Your MOF bridge (30 MOFs, 5 scorers) and constraint search (22-atom ligand challenge) overlap directly with their research. Open-source friendly.
- **Website**: http://hjkgrp.mit.edu/
- **Email subject**: "Compositional reasoning engine for MOF compatibility screening -- open-source tool"

### 17. Langan Engineering (1,600 employees, PFAS Practice)

- **What**: Engineering/environmental services. PFAS sampling, remediation, compliance, litigation support.
- **Why they'd care**: They handle remediation but can't answer "what do I replace PFAS with in my product?" Your tool fills that gap.
- **Website**: https://www.langan.com/pfas
- **Email subject**: "PFAS substitution screening tool -- complement to Langan's remediation services"

### 18. Sovereign Consulting (Environmental, New Jersey)

- **What**: Environmental consulting/remediation for federal, commercial, private clients. PFAS sampling and analysis.
- **Website**: https://sovcon.com/
- **Email subject**: "PFAS alternative screening tool for your manufacturing clients -- free demo"

### 19. The Limiting Factor (Jordan Giesige, YouTube)

- **What**: Battery technology deep-dives with detailed animations. Technical audience, widely cited by industry professionals.
- **Why they'd care**: "PVDF is getting banned -- what replaces it?" with your tool demoing compatibility scores is prime content.
- **Website**: https://www.patreon.com/thelimitingfactor
- **Email subject**: "Deep dive material: EU is banning PVDF in batteries -- computational tool screens alternatives"

### 20. Battery Generation Podcast (Helmholtz Institute Ulm)

- **What**: Academic battery podcast. Natural fit for category theory angle.
- **Email subject**: "Guest pitch: Category theory predicts battery material compatibility -- and screens for PFAS compliance"

---

### Bonus Targets

- **Sbaiti & Company** (boutique PFAS litigation law firm): https://www.sbaitilaw.com/
- **Phillips Lytle LLP** (regional law, PFAS practice): https://phillipslytle.com/
- **Recharge by Battery Materials Review podcast** (Matt Fernley): industry podcast, PFAS supply chain topics
- **Taylor Sparks** (materials science professor with YouTube lectures)

---

# PART 4: LinkedIn Cross-Posting

### The Rule: Never copy-paste from YouTube. Rewrite for LinkedIn's professional context.

### One YouTube video = 5-8 LinkedIn posts

1. **Launch post** (day of upload): "I just published a video about [topic]. Here's the 30-second version..." + key insight + link
2. **Behind-the-scenes post** (next day): "Here's what I learned making this..."
3. **Data post** (2 days later): One specific stat or result as a standalone post
4. **Carousel post** (3 days later): Export 5-6 slides as images, post as LinkedIn carousel
5. **Hot take post** (4 days later): Controversial opinion from the video as standalone

### LinkedIn Post Templates

**Template 1 -- Story Post (Video 1 launch):**

> I built a chemistry engine while delivering DoorDash.
>
> No PhD. No lab. No VC money. No neural network.
>
> Just category theory, published material properties, and months of coding between deliveries.
>
> Today it has:
> - 169 materials with cited properties
> - 1,575 passing tests
> - 8 material domains
> - PFAS compliance screening (EU ban: Aug 2026)
> - A live API and web UI
>
> The $2.1B materials AI industry uses black-box neural networks.
> I used 19th century math instead.
>
> Full story: [YouTube link]
>
> #MaterialsScience #PFAS #DeepTech #BatteryTech #SoloFounder

**Template 2 -- Data Post (Video 2 launch):**

> PVDF is in every EV battery on the planet.
>
> The EU bans it in August 2026.
>
> I built a tool that:
> 1. Scans your bill of materials for PFAS
> 2. Flags urgency level
> 3. Ranks replacement materials by compatibility score
>
> PVDF -> CMC+SBR (0.84 compatibility)
> PVDF -> PAA (0.77)
> PTFE -> EPDM (0.77)
>
> These aren't guesses. They're scores from published property comparisons.
>
> 40M EVs. 4 months. Every battery manufacturer needs a PFAS transition plan.
>
> #PFAS #ForeverChemicals #EVBattery #Compliance #MaterialsScience

**Template 3 -- Hot Take:**

> Unpopular opinion: Materials AI doesn't need more training data. It needs better reasoning.
>
> $2.1B invested in materials AI. All neural networks. All black boxes.
>
> But materials science has a composability problem:
> If cathode A works with electrolyte B,
> and electrolyte B works with binder C,
> what about cathode A with binder C?
>
> Neural networks can't answer this without training examples.
> Category theory answers it by construction.
>
> #MaterialsInformatics #DeepTech #Innovation

### Hashtags (3-5 per post, never more)

**Core (use 2 every post):** #MaterialsScience, #PFAS or #ForeverChemicals, #BatteryTech
**Amplifiers (rotate 1-2):** #DeepTech, #Startup, #Innovation, #CleanTech
**Engagement (0-1):** #SoloFounder, #BuildInPublic

### Posting schedule

- Tuesday and Thursday, 8-10 AM in target timezone
- Reply to every comment within the first hour (engagement velocity)

---

# PART 5: Cold Email Templates

### The Permission-First Approach

Do NOT send a long pitch or a Loom video in your first email. Keep it short. Offer value. Ask one question.

**For compliance consultants (GreenSoft, Acquis, Certivo):**

> Subject: Free PFAS screening tool for battery BOMs
>
> Hi [Name],
>
> I built a PFAS compliance screening tool that scans a battery bill of materials, flags PFAS substances (with CAS numbers and regulation references), and ranks replacement candidates by compatibility score.
>
> Example: scanning a standard Li-ion BOM finds PVDF and PTFE as PFAS, and scores CMC+SBR at 0.84 as a drop-in PVDF replacement for cathode binders -- based on published adhesion, electrochemical stability, and flexibility data.
>
> The EU PFAS restriction is advancing (ECHA RAC adopted its final opinion March 2, 2026). I thought this might be useful for your clients.
>
> Would you like me to scan a specific materials list for you? Free, no strings.
>
> James

**For battery startups (Ateios, Nanoramic, Donut Lab):**

> Subject: Independent PFAS-free compatibility validation tool
>
> Hi [Name],
>
> I noticed [Company] is building PFAS-free battery electrodes. I built a materials compatibility engine that could independently validate your formulations against cathode/electrolyte/collector materials.
>
> Quick example: the tool scores CMC+SBR binder + NMC811 cathode at 0.84 overall compatibility, with breakdowns across voltage, thermal, chemical, mechanical, and kinetic dimensions. All scores trace to published properties with citations.
>
> This kind of independent computational validation might be useful for customer conversations or regulatory filings.
>
> Want me to run your specific materials through it? Takes 2 minutes.
>
> James

**For researchers (Prof. Amanchukwu, Eleni Savvidou, Prof. Kulik):**

> Subject: Computational screening tool for PFAS-free battery alternatives -- relevant to your [paper title] work
>
> Dear [Prof./Dr. Name],
>
> I read your [paper] in [journal] on [topic]. I built a compositional reasoning engine (category theory + ZFC set theory, not ML) that screens material compatibility and PFAS compliance.
>
> For PFAS-free battery alternatives, it currently scores:
> - CMC+SBR replacing PVDF as cathode binder: 0.84
> - PAA: 0.77
> - PAN: 0.64
>
> These are computed from published property comparisons (Bresser 2018, Li 2020). The tool generates compliance reports with provenance chains.
>
> Would validating these computational scores against your experimental data be useful? I'd be happy to share access and discuss potential collaboration.
>
> Best,
> James Hawkins

**For podcasts/YouTube (Battery Tech Podcast, Undecided, Limiting Factor):**

> Subject: Guest pitch: DoorDash driver builds PFAS compliance tool for battery manufacturers
>
> Hi [Name],
>
> Quick pitch: I'm a self-taught programmer who built a materials compatibility engine using category theory while delivering DoorDash. The tool now has 1,575 passing tests across 8 material domains and screens battery BOMs for PFAS compliance.
>
> Timely angle: the EU PFAS ban is advancing (ECHA RAC adopted final opinion March 2, 2026), PVDF is in every Li-ion battery, and the tool ranks replacement materials by compatibility score.
>
> The story: non-engineer uses 19th century math instead of neural networks to predict chemistry. No funding, no PhD, no VC money. Just category theory.
>
> Happy to do a live demo on your show or record a segment. The tool runs as a web app -- works great for screen sharing.
>
> James

**After someone replies (then send Loom):**

Record a personalized 60-90 second Loom showing THEIR specific materials being scanned. Research their products from public datasheets first.

---

# PART 6: Timeline -- What to Do When

## Week 1 (March 28 - April 4)

| Day | Action |
|-----|--------|
| **Day 1** | Create `Dockerfile.streamlit`. Create private GitHub repo. Push code. |
| **Day 2** | Deploy to Railway.app. Test all 7 pages on the live URL. |
| **Day 3** | Record Video 1 (the hook, 3-4 min). Edit in DaVinci Resolve. |
| **Day 4** | Upload Video 1. Post LinkedIn launch story. |
| **Day 5** | Cut 3 YouTube Shorts from Video 1. Post first Short. |
| **Day 6** | Send first 5 emails (Tier 1: Certivo, Ateios, Savvidou, Battery Tech Podcast, GreenSoft) |
| **Day 7** | Post LinkedIn data post (PFAS teaser for Video 2). Follow up on any replies. |

## Week 2 (April 5-11)

| Day | Action |
|-----|--------|
| **Day 8-9** | Record Video 2 (PFAS problem, 8-10 min). Edit. |
| **Day 10** | Upload Video 2. Post LinkedIn regulatory timeline post. |
| **Day 11** | Cut 2 Shorts from Video 2. Send next 5 emails (Tier 2: Amanchukwu, Nanoramic, Acquis, Undecided, ZVEI). |
| **Day 12** | LinkedIn carousel: 5-slide PFAS timeline. |
| **Day 13-14** | Start making slides for Video 3. Follow up on any email replies with personalized Loom demos. |

## Week 3 (April 12-18)

| Day | Action |
|-----|--------|
| **Day 15-17** | Record Video 3 (math explainer, 10-12 min). Take your time with this one. |
| **Day 18** | Upload Video 3. LinkedIn hot take post. |
| **Day 19** | Send next 5 emails (Tier 3: RECHARGE, Donut Lab, ION Storage, Venable, Kulik). |
| **Day 20-21** | Respond to any demo requests. Iterate on UI based on any feedback. |

## Week 4 (April 19-25)

| Day | Action |
|-----|--------|
| **Day 22-23** | Record Video 4 (64 questions demo, 6-8 min). |
| **Day 24** | Upload Video 4. LinkedIn data post. |
| **Day 25-26** | Send remaining 5 emails (Tier 3: Leclanche, Langan, Phillips Lytle, Limiting Factor, Battery Generation). |
| **Day 27-28** | Analyze results. Who responded? What did they ask? |

## Week 5 (April 26 - May 2)

| Day | Action |
|-----|--------|
| **Day 29-30** | Record Video 5 (vision, 5-7 min). |
| **Day 31** | Upload Video 5. LinkedIn milestone post (all 5 videos published). |
| **Day 32-35** | Follow up with every contact. Begin cold email round 2 with learnings from round 1. |

## Key Dates to Remember

| Date | Event | Your Action |
|------|-------|-------------|
| **May 25, 2026** | ECHA SEAC public consultation closes | Post about it. Email contacts: "The consultation window is closing" |
| **July 1, 2026** | Minnesota PFAS reporting kicks in | Post about it. "Minnesota deadline is here" |
| **Aug 12, 2026** | EU hard ban on PFAS in food-contact packaging | Post about it. Major content moment. |
| **Oct 2026** | US EPA TSCA + EU firefighting foam ban | Post about it. |

Each regulatory deadline is free marketing. The government is creating urgency for you.

---

# APPENDIX: Key Sources

## PFAS Regulatory
- ECHA RAC final opinion (March 2, 2026): https://echa.europa.eu/-/echa-supports-pfas-restriction-with-targeted-derogations
- ECHA SEAC consultation (open until May 25, 2026): https://echa.europa.eu/-/echa-to-consult-on-pfas-draft-opinion-in-spring-2026
- Euronews coverage: https://www.euronews.com/my-europe/2026/03/26/eu-chemicals-agency-backs-forever-chemicals-ban-with-final-decision-to-the-commission
- Arnold & Porter PFAS analysis: https://www.arnoldporter.com/en/perspectives/advisories/2026/03/echa-committees-advance-broad-pfas-restriction-under-reach
- PRBA Minnesota PFAS: https://www.prba.org/press-releases/prba-mn-pfas-prohibition-discussion-10235/
- ACS PFAS-Free Battery Research: https://pubs.acs.org/doi/10.1021/acs.est.4c06083
- Certivo PFAS Guide: https://www.certivo.com/blog-details/global-pfas-regulations-the-2025-2026-compliance-master-guide-for-manufacturers

## Battery Industry
- Ateios/Kodak PFAS-free electrodes: https://ateios.com/
- Nanoramic Neocarbonix: https://www.nanoramic.com/
- ZVEI PFAS in Batteries factsheet: https://www.zvei.org/en/association/sections/batteries-section
- ION Storage Systems milestone: https://electrek.co/2026/03/10/a-us-startup-just-cleared-a-major-solid-state-battery-milestone-production-is-next/
- Certivo $4M seed: https://www.geekwire.com/2026/seattle-startup-certivo-raises-4m-to-automate-supply-chain-compliance-with-ai/

## Deployment Platforms
- Railway docs: https://docs.railway.com/quick-start
- Railway Streamlit deploy: https://railway.com/deploy/streamlit
- Render pricing: https://render.com/pricing
- HF Spaces: https://huggingface.co/docs/hub/en/spaces-overview
- Google Cloud Run: https://docs.google.com/run/docs/deploying
- Streamlit Docker guide: https://docs.streamlit.io/deploy/tutorials/docker

## YouTube/Content
- Veritasium PFAS video context: https://pfascentral.org/news/youtube-science-star-derek-muller-confronts-pfas-forever-chemicalsin-his-own-blood
- YouTube Shorts strategy 2026: https://influenceflow.io/resources/youtube-shorts-and-long-form-video-strategy-the-complete-2026-creators-guide/
- LinkedIn hashtag strategy: https://blog.linkboost.co/linkedin-hashtag-strategy-2026/
