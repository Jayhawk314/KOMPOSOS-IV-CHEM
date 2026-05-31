# go_to_market/

Go-to-market material for KOMPOSOS-IV-CHEM. **Strategy and tooling, not audit
claims** — benchmark/audit truth lives in `audit/` and the registry. This folder
is about getting the validated work in front of the right first users honestly.

## pfas/ — PFAS compliance reformulation

The one domain with a hard, datable buyer pain: companies facing PFAS
restrictions who need replacements that **actually work in their product**.

| File | What it is |
|---|---|
| `COMPLIANCE_CLOCK_2026.md` | Corrected, sourced regulatory deadlines. **Supersedes the stale "EU ban Aug 2026" date** in `docs/BOM_AUDIT_FORMATS_AND_PROCEDURES.md` / `docs/BOM_SCREENING_RUBRIC.md`. |
| `GO_TO_MARKET.md` | How to land the first design partner: the differentiator (cell-aware replacement), honest positioning, who to approach, the free-BOM first move, and a fix-before-charging backlog. |
| `bom_triage.py` | **Working CLI** — the "send me your BOM, I'll run the triage" deliverable. Drives the live `pfas_bridge` (`PFASComplianceChecker` + `find_replacements_for_cell`). |
| `example_bom.csv` | A 13-line NMC battery BOM to demo with. |
| `out/` | Generated reports (`.md` + `.json`). |

### Run it

```powershell
# offline (no PubChem name->SMILES resolution) — fast, deterministic demo
python go_to_market\pfas\bom_triage.py --bom go_to_market\pfas\example_bom.csv --client "Acme Battery Co" --no-resolve

# full capability (resolves unknown names to catch NOVEL PFAS via OECD rule)
python go_to_market\pfas\bom_triage.py --bom go_to_market\pfas\example_bom.csv --client "Acme Battery Co"
```

Outputs a Markdown report + JSON artifact to `out/`. The report:
- screens every line for PFAS (exact / brand / CAS / OECD-structural),
- for each PFAS line, ranks replacements **against the clean materials that
  remain in the cell**, worst-interface-first, surfacing the **bottleneck**,
- separates "compatibility-evaluated" from "no interface data → manual review"
  so *no-data never outranks a real evaluation*,
- carries the corrected compliance clock and an honest disclaimer in-report.

### Relationship to existing docs

`docs/BOM_SCREENING_RUBRIC.md` and `docs/BOM_AUDIT_FORMATS_AND_PROCEDURES.md` are
the older delivery/format docs. They (1) predate the cell-aware replacement
functions and (2) carry stale deadlines. Treat **code as truth** and this folder
+ the clock file as the current layer; the PDF client-report path
(`reports/pfas_report.py`) remains the polished customer deliverable.
