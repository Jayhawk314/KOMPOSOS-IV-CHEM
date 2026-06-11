# TODO: Surface stoichiometric validation

Done 2026-06-10 (session 1): `synthesis_planner/stoich_solver.py` (Z3), wired
into `SynthesisPlanner.score_route` (hard veto on UNBALANCED), API/SDK get
fields free (`stoichiometry`, `balanced_reaction`, `stoichiometry_notes`).
Audit: `python audit\run_stoich_audit.py` -> 17 balanced / 0 unbalanced / 7 skipped.

Done 2026-06-10 (session 2):
- [x] NEW page `streamlit_app/pages/11_Synthesis_Planner.py` — ranked routes,
      balanced-equation display, veto/skip badges, step tables, citations.
      Smoke-tested (imports clean); verify visually with `streamlit run streamlit_app/app.py`.
- [x] `validation_status.py` — added `synthesis_planner` feature note
      (Z3 check semantics, scope honesty, audit command).
- [x] `docs/AUDIT_CHANGE_LOG.md` — 2026-06-10 entry (internal-consistency,
      NOT blind; artifact `audit/stoich_balance_report.json`).
- [x] `docs/FEATURES.md` §7 — stoich validation + UI bullets.
- [x] `requirements.txt` + `requirements-deploy.txt` — added `z3-solver>=4.12.0`.
- [x] Checked Cell Designer / Discovery Workbench: neither renders per-route
      dicts directly (workbench only references synthesis in prose); fields
      flow through `to_dict()` automatically if they ever do.
- Tests: 111 pass in synthesis_planner.

## Still open (low priority)
1. Visual check of the new page in a browser; add it to any landing-page
   feature list in `streamlit_app/app.py` if one enumerates pages.
2. Showcase outputs (`showcase/synthesis_comparison.py`,
   `showcase/blog/synthesis_routes.md`) — regenerate/extend with the new fields.
3. `notebooks/demo_battery_cell.ipynb` + `QUICKSTART.md` — mention new fields.
4. `KOMPOSOS_COMPLETE_SYSTEM_GUIDE.md` — document the validation pass.
5. SACE phase 2: precursor-set search ("which <=4 non-toxic DB precursors
   reach target X") via `solve_balance` — turns validation into directed design.
6. Commit: new/changed files are untracked/modified — `synthesis_planner/stoich_solver.py`,
   `synthesis_planner/tests/test_stoich_solver.py`, `route_planner.py`,
   `audit/run_stoich_audit.py`, `audit/stoich_balance_report.json`,
   `streamlit_app/pages/11_Synthesis_Planner.py`, `validation_status.py`,
   docs + requirements. (Check bridge-dir gitignore footgun if any path is ignored.)
