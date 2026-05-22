# MOF Linker External Validation Plan

**Purpose**: Make the MOF/linker claim stronger by moving from internal scoring to independent build/DFT results.

## Packet

- Export script: `python scripts/export_mof_external_validation_packet.py --count 50`
- Packet: `audit/external_blind/mof_linker_validation_2026_q2.csv`
- Manifest: `audit/external_blind/mof_linker_validation_2026_q2.sha256`
- Current SHA256: `396677b1abedbeb50be0c53b796c8fcf2b0c696eb6fff8f9e884acd17abd315d`

The packet contains 50 top-ranked 22-heavy-atom KOMPOSOS candidates plus blank external-result columns. KOMPOSOS scores are recorded as predictions, not labels.

## External Workflow

1. Pick a fixed metal node/topology family before running results, for example UiO-style Zr6 nodes or Zn paddlewheel nodes.
2. Build candidate MOF structures with molSimplify or an equivalent external builder.
3. Relax structures with the external group's DFT workflow.
4. Fill the blank columns: build status, relaxation status, energy fields, max force, imaginary-frequency count, and external verdict.
5. Return the completed CSV without changing KOMPOSOS columns.
6. Compute success rate, build failure rate, relaxation failure rate, and energy/force distributions.

## Reporting Rules

- Report all 50 rows, including build failures.
- Do not remove failed candidates from the denominator.
- Do not tune the linker scorer against this file and still call it blind.
- If this packet is used for tuning, freeze a new dated packet before the next public result.

## Why This Matters

A 50-linker external molSimplify/DFT packet is more valuable than thousands of additional internally scored linkers. It tests whether KOMPOSOS candidates survive an independent structure-building and relaxation workflow.
