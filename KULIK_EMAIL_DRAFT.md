# Draft note to Heather Kulik

Status: technically audited 2026-07-17; verify the recipient address and any URL
immediately before sending.

**Subject:** A constrained 22-heavy-atom linker generator inspired by your LLM example

Hi Prof. Kulik,

Your comment about asking an LLM for a 22-atom ligand stuck with me as a clean
example of where unconstrained language generation loses chemical bookkeeping.

I built a small deterministic linker generator that enforces an exact heavy-atom
count and coordinating-site requirements with RDKit rather than asking an LLM to
count. I then pass candidates through a structural screening funnel: molecule
sanity, at least two recognized coordinating sites, synthetic-accessibility
score, donor geometry, and similarity to a known-linker seed corpus.

On the repository's frozen linker benchmark, that funnel gives 94.3% pass-all
recall on 423 held-out real linkers and AUROC 0.884 against raw generator output.
For the exact-22 subset (n=20), recall is 95% and AUROC is 0.901. I understand that
this validates a screening rule against known linker structure; it does not show
that a generated candidate will synthesize, coordinate as intended, or form a
useful MOF.

The code and benchmark are free and open. If this is of interest, I would value a
quick chemist's gut check on a small packet of the exact-22 candidates that pass
the grounded funnel. I am not selling anything or asking for collaboration.

Best,

James Hawkins

GitHub: [verify the public URL before sending]

## Pre-send audit

- [ ] Verify the interview wording from the original source; do not quote from
  memory if the wording is uncertain.
- [ ] Verify the public repository URL and that the benchmark artifact is present.
- [ ] Generate a fresh candidate packet from the current grounded-funnel path.
- [ ] Include exact heavy-atom count, recognized coordinating-site count, SAscore,
  geometry status, novelty coordinate, and pipeline/version hash.
- [ ] Do not attach `kulik_22atom_linkers_100.csv`. It is a legacy 50-row packet
  whose identical generic toxicity/activity/conductivity/etc. verdicts are not
  validated for novel linkers.
- [ ] Do not call the anecdote a challenge, claim it was solved, call a candidate
  perfect for coordination, or use the unrelated compatibility benchmark.
