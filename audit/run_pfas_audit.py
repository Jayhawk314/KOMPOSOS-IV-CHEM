# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""PFAS structural detector audit (honest edition).

Evaluates the active pfas_bridge OECD CF2/CF3 rule against:
  1. EPA PFASSTRUCT v4 (~10.7k structures)  -> CONCORDANCE, not independent
     validation: EPA's list is itself structure-derived with ~the same rule, so
     high agreement is expected by construction. We report it as concordance and
     analyze the DISAGREEMENTS (structures EPA calls PFAS that our rule misses).
  2. A curated hard-negative panel (fluorinated-but-NOT-PFAS + non-fluorinated)
     -> SPECIFICITY. This is the discriminating test: can the rule avoid flagging
     fluorine that isn't a fully-fluorinated carbon?

No "AUROC" is reported: a binary substructure rule has no ROC curve. We report
recall/concordance, specificity, and the disagreement set.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")
from rdkit import Chem
from pfas_bridge.pfas_registry import is_pfas

# Curated hard negatives: fluorinated but NOT PFAS by OECD (no CF2/CF3 lacking H),
# plus common non-fluorinated molecules. Labels checked by hand against OECD 2021.
HARD_NEGATIVES = [
    # fluorinated but not PFAS (isolated / aromatic / H-bearing fluorinated C)
    ("Fluorobenzene", "Fc1ccccc1"),
    ("4-Fluorotoluene", "Cc1ccc(F)cc1"),
    ("3-Fluoropyridine", "Fc1cccnc1"),
    ("4-Fluorobenzoic acid", "OC(=O)c1ccc(F)cc1"),
    ("5-Fluorouracil", "O=c1[nH]cc(F)c(=O)[nH]1"),
    ("Monofluoroacetic acid", "OC(=O)CF"),
    ("Difluoroacetic acid (CHF2, has H)", "OC(=O)C(F)F"),
    ("1-Fluorobutane", "CCCCF"),
    ("2-Fluoroethanol", "OCCF"),
    ("Difluoromethane (CH2F2)", "FCF"),
    ("1,1-Difluoroethane (CHF2)", "CC(F)F"),
    ("1,2-Difluoroethane", "FCCF"),
    ("Fluconazole (aromatic F2, no CF2/CF3)", "OC(Cn1cncn1)(Cn1cncn1)c1ccc(F)cc1F"),
    ("Haloperidol (single aryl F)", "OC1(CCN(CCCC(=O)c2ccc(F)cc2)CC1)c1ccc(Cl)cc1"),
    ("Ciprofloxacin (single aryl F)", "OC(=O)C1=CN(C2CC2)c2cc(N3CCNCC3)c(F)cc2C1=O"),
    # non-fluorinated commons
    ("Water", "O"),
    ("Benzene", "c1ccccc1"),
    ("Ethanol", "CCO"),
    ("Acetic acid", "CC(=O)O"),
    ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
    ("Toluene", "Cc1ccccc1"),
    ("Caffeine", "Cn1cnc2c1c(=O)n(C)c(=O)n2C"),
    ("Urea", "NC(=O)N"),
    ("Glucose", "OCC1OC(O)C(O)C(O)C1O"),
    ("Methanol", "CO"),
]

# Positive controls (known PFAS) — sanity that the rule fires.
POSITIVE_CONTROLS = [
    ("PFOA", "OC(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F"),
    ("PFOS", "OS(=O)(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F"),
    ("TFA (trifluoroacetic acid)", "OC(=O)C(F)(F)F"),
    ("GenX (HFPO-DA)", "OC(=O)C(F)(OC(F)(F)C(F)(F)F)C(F)(F)F"),
]


def main():
    print("=" * 60)
    print("PFAS STRUCTURAL DETECTOR AUDIT (honest edition)")
    print("=" * 60)

    # --- Specificity on the hard-negative panel ---
    fp = [name for name, smi in HARD_NEGATIVES if is_pfas(smi)]
    n_neg = len(HARD_NEGATIVES)
    specificity = (n_neg - len(fp)) / n_neg
    print(f"\nHard-negative panel: {n_neg} molecules (fluorinated-but-not-PFAS + commons)")
    print(f"  Specificity: {n_neg - len(fp)}/{n_neg} = {specificity:.3f}")
    if fp:
        print(f"  FALSE POSITIVES (rule wrongly flagged): {fp}")

    # --- Positive controls ---
    pc_hits = sum(1 for _, smi in POSITIVE_CONTROLS if is_pfas(smi))
    print(f"\nPositive controls: {pc_hits}/{len(POSITIVE_CONTROLS)} known PFAS flagged")

    # --- EPA concordance (NOT independent validation) ---
    epa_file = ROOT / "data" / "EPA_PFASSTRUCTV4.txt"
    if not epa_file.exists():
        print(f"\n[skip] EPA file not found at {epa_file}")
        return
    total = hits = parse_fail = 0
    misses = []
    with open(epa_file, "r", encoding="utf-8") as f:
        next(f)
        for line in f:
            parts = line.strip().split("\t")
            if not parts or not parts[0]:
                continue
            smi = parts[0]
            total += 1
            if Chem.MolFromSmiles(smi) is None:
                parse_fail += 1
            if is_pfas(smi):
                hits += 1
            elif len(misses) < 20:
                misses.append((parts[1] if len(parts) > 1 else "?", smi))
    concordance = hits / total if total else 0.0
    print("\nEPA PFASSTRUCT v4 concordance (consistency w/ EPA's own structural list):")
    print(f"  {hits}/{total} = {concordance:.4f}  ({parse_fail} unparseable SMILES)")
    print(f"  Disagreements (EPA=PFAS, rule=not): {total - hits}")
    print("  NOTE: concordance, not independent validation — EPA's list is")
    print("        structure-derived with ~the same OECD rule.")
    if misses:
        print("\n  Sample missed EPA structures (rule blind spots):")
        for dtxsid, smi in misses[:10]:
            print(f"    {dtxsid}: {smi}")

    print("\n" + "=" * 60)
    print("AUDIT COMPLETE — no AUROC reported (binary rule has no ROC curve).")
    print("=" * 60)


if __name__ == "__main__":
    main()
