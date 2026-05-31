# PFAS Compliance Clock — corrected & sourced (2026-05-31)

**Why this file exists:** the older audit docs state a hard
*"EU PFAS ban — August 25, 2026"* (see `docs/BOM_AUDIT_FORMATS_AND_PROCEDURES.md`
lines ~28, 720, 867; echoed in `docs/BOM_SCREENING_RUBRIC.md`). **That date is
wrong and will cost credibility with any compliance professional.** This file is
the corrected source of truth and is hard-coded into `bom_triage.py` so reports
never drift back to it.

> Not legal advice. Verify against primary sources before filing. Dates move.

---

## The near-term teeth are US state laws, not the EU

| Jurisdiction | Milestone | Timing |
|---|---|---|
| **US — Minnesota (Amara's Law)** | Manufacturer reporting of intentionally-added PFAS | **2026-09-15** (90-day extension possible → 2026-12-14). Several product-category bans already in force; broad ban 2032. |
| **US — New Mexico** | Product PFAS reports + mandatory labeling; phased product bans | Reports + labeling **2027-01-01**; phased bans **2027-01-01** and **2028-01-01**; default ban 2032. |
| **US — EPA TSCA §8(a)(7)** | Mandatory PFAS manufacturing/import reporting **(IN FLUX)** | As of April 2026 EPA adjusted it: reporting starts **60 days after a forthcoming final rule, or 2027-01-31, whichever is first** (was Oct 13, 2026 for most; small article-importers had been April 13, 2027). **State the flux — do not quote a dead hard date.** |
| Other US states | Reporting/restrictions live | Maine, California, Colorado, Washington, New York, Maryland. |
| **EU — REACH universal PFAS restriction** | The biggest one, but slow | RAC opinion adopted Mar 2 2026; SEAC draft opinion Mar 26 2026 (consultation to ~May 25 2026); **SEAC final opinion ~end-2026**; **Commission adoption unlikely before Q3-2027**; **restrictions would not apply before 2029.** Sector derogations (semiconductors, medical) under discussion. |

**Net:** the people *desperate now* are (a) meeting **2026–2027 US reporting/labeling**
(MN Sep 2026, NM Jan 2027, EPA late-2026/early-2027) and (b) **reformulating ahead
of 2027 state product bans and EU 2029.** The EU is a *planning* pressure, not a
2026 cliff.

---

## Corrections to apply to the older docs

- `docs/BOM_AUDIT_FORMATS_AND_PROCEDURES.md`: replace every **"EU ban Aug 2026 /
  August 25, 2026"** and **"US EPA Oct 2026"** with the table above. The
  regulatory-timeline section (§"Regulatory Requirements") and the PDF report
  template (§7 / "Regulatory Timeline") both carry the stale dates.
- `docs/BOM_SCREENING_RUBRIC.md`: the summary-email template references an
  "EU PFAS restriction takes effect [date]" — wire it to this clock; lead with
  the **state** deadlines, which are the real near-term drivers.
- Both docs also **predate the cell-aware replacement functions**
  (`find_replacements_for_cell`) — the replacement sections undercount current
  capability. The cell-bottleneck ranking is now the headline differentiator.

---

## Sources

- Hunton — *What to watch in 2026: PFAS product restrictions & reporting*:
  https://www.hunton.com/the-nickel-report/what-to-watch-for-in-2026-a-new-wave-of-pfas-product-restrictions-and-reporting-requirements-go-into-effect-with-many-more-expected-in-2027-and-beyond
- US EPA — TSCA §8(a)(7) PFAS reporting:
  https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping
- ECHA — PFAS restriction timeline:
  https://echa.europa.eu/-/echa-announces-timeline-for-pfas-restriction-evaluation
- Covington — *ECHA launches new consultation on universal PFAS ban* (Mar 2026):
  https://www.cov.com/en/news-and-insights/insights/2026/03/echa-launches-a-new-public-consultation-on-a-proposed-universal-ban-on-pfas-in-the-eu
- (Health framing, if ever needed) IARC — PFOA = Group 1 carcinogen, PFOS = 2B (Nov 2023):
  https://www.iarc.who.int/news-events/iarc-monographs-evaluate-the-carcinogenicity-of-perfluorooctanoic-acid-pfoa-and-perfluorooctanesulfonic-acid-pfos/

_Last verified: 2026-05-31._
