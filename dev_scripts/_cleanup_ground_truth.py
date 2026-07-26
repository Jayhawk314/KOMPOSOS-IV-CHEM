"""One-time script to clean up audit ground truth data.

1. De-duplicate battery.json (remove entries that duplicate blind_test_pairs.json
   or duplicate each other within the file).
2. Add 'doi' and 'used_for_tuning' fields to all ground truth JSON files.
3. Add 'used_for_tuning' field to blind_test_pairs.json.

Run once, then delete this script.
"""
import json
from pathlib import Path

AUDIT_DIR = Path(__file__).parent / "audit"
GT_DIR = AUDIT_DIR / "ground_truth"

# ── Known DOIs from citation strings ──────────────────────────────────────
CITATION_DOIS = {
    "Noh et al., J. Power Sources 2013": "10.1016/j.jpowsour.2013.01.137",
    "Noh et al., J. Power Sources 2013, 233, 121-130": "10.1016/j.jpowsour.2013.01.137",
    "Thackeray et al., J. Electrochem. Soc. 1992": "10.1149/1.2069200",
    "Thackeray et al., J. Electrochem. Soc. 1992, 139, 363": "10.1149/1.2069200",
    "Armand et al., Nat. Mater. 2009": "10.1038/nmat2297",
    "Armand et al., Nat. Mater. 2009, 8, 621-629": "10.1038/nmat2297",
    "Lin et al., Nat. Nanotechnol. 2017": "10.1038/nnano.2017.16",
    "Lin et al., Nat. Nanotechnol. 2017, 12, 194-206": "10.1038/nnano.2017.16",
    "Murugan et al., Angew. Chem. 2007": "10.1002/anie.200701144",
    "Murugan et al., Angew. Chem. 2007, 46, 7778": "10.1002/anie.200701144",
    "Murugan et al. 2007": "10.1002/anie.200701144",
    "Xu, Chem. Rev. 2004": "10.1021/cr030203g",
    "Xu, Chem. Rev. 2004, 104, 4303-4417": "10.1021/cr030203g",
    "Obrovac & Chevrier, Chem. Rev. 2014": "10.1021/cr500207g",
    "Obrovac & Chevrier, Chem. Rev. 2014, 114, 11444-11502": "10.1021/cr500207g",
    "Winter et al., Adv. Mater. 1998": "10.1002/(SICI)1521-4095(199807)10:10<725::AID-ADMA725>3.0.CO;2-Z",
    "Winter et al., Adv. Mater. 1998, 10, 725-763": "10.1002/(SICI)1521-4095(199807)10:10<725::AID-ADMA725>3.0.CO;2-Z",
    "Zhu et al., ACS Appl. Mater. Interfaces 2015": "10.1021/acsami.5b07517",
    "Zhu et al., ACS Appl. Mater. Interfaces 2015, 7, 23685": "10.1021/acsami.5b07517",
    "Li et al., J. Electrochem. Soc. 2017": "10.1149/2.1291714jes",
    "Li et al., J. Electrochem. Soc. 2017, 164, A3529": "10.1149/2.1291714jes",
    "Zhao et al., J. Power Sources 2015": "10.1016/j.jpowsour.2015.06.037",
    "Zhao et al., J. Power Sources 2015, 294, 169-178": "10.1016/j.jpowsour.2015.06.037",
    "Richards et al., Chem. Mater. 2016": "10.1021/acs.chemmater.5b04082",
    "Richards et al., Chem. Mater. 2016, 28, 266-273": "10.1021/acs.chemmater.5b04082",
    "Kato et al., Nat. Energy 2016": "10.1038/nenergy.2016.30",
    "Kato et al., Nat. Energy 2016, 1, 16030": "10.1038/nenergy.2016.30",
    "Hakari et al., Chem. Lett. 2015": "10.1246/cl.140996",
    "Hakari et al., Chem. Lett. 2015, 44, 307": "10.1246/cl.140996",
    "Liu et al., Nat. Energy 2019": "10.1038/s41560-019-0338-x",
    "Liu et al., Nat. Energy 2019, 4, 180-186": "10.1038/s41560-019-0338-x",
    "Bresser et al., Energy Environ. Sci. 2018": "10.1039/C8EE00640G",
    "Bresser et al., Energy Environ. Sci. 2018, 11, 3096": "10.1039/C8EE00640G",
    "Zhang et al., J. Power Sources 2011": "10.1016/j.jpowsour.2010.08.114",
    "Zhang et al., J. Power Sources 2011, 196, 1513": "10.1016/j.jpowsour.2010.08.114",
    "Li et al., Electrochem. Energy Rev. 2020": "10.1007/s41918-019-00053-3",
    "Li et al., Electrochem. Energy Rev. 2020, 3, 43-80": "10.1007/s41918-019-00053-3",
    "Armand & Tarascon, Nature 2008": "10.1038/451652a",
    "Armand & Tarascon, Nature 2008, 451, 652-657": "10.1038/451652a",
    "Armand et al., Nature 2008": "10.1038/451652a",
    "Janek & Zeier, Nat. Energy 2016": "10.1038/nenergy.2016.141",
    "Manthiram et al., Nat. Rev. Mater. 2017": "10.1038/natrevmats.2016.103",
    # Semiconductor DOIs (already present in some entries)
    "Vurgaftman et al., J. Appl. Phys. 2001": "10.1063/1.1368156",
    "People & Bean, Appl. Phys. Lett. 1985": "10.1063/1.96206",
    "Ambacher et al., J. Appl. Phys. 1998": "10.1063/1.369664",
    "Kroemer, J. Cryst. Growth 1987": "10.1016/0022-0248(87)90068-0",
    "Dingle et al., Appl. Phys. Lett. 1978": "10.1063/1.90457",
    "Ambacher et al., J. Phys.: Condens. Matter 2002": "10.1088/0953-8984/14/13/302",
    "Radisavljevic et al., Nat. Nanotechnol. 2011": "10.1038/nnano.2010.279",
    "Pearton et al., Appl. Phys. Rev. 2018": "10.1063/1.5006941",
    "Ozgur et al., J. Appl. Phys. 2005": "10.1063/1.1992666",
    "Taniyasu et al., Nature 2006": "10.1038/nature04760",
    "Gong et al., Nat. Mater. 2014": "10.1038/nmat4091",
    "Liebich et al., Appl. Phys. Lett. 2011": "10.1063/1.3586256",
    # Polymer DOIs
    "Bates, Science 1991": "10.1126/science.251.4996.898",
    "Hillmyer et al., J. Am. Chem. Soc. 1997": "10.1021/ja963622m",
    # Ceramic DOIs
    "Rangasamy et al., J. Am. Chem. Soc. 2012": "10.1021/ja305709z",
    "Kim et al., Biomaterials 2003": "10.1016/S0142-9612(03)00044-9",
    # Glass DOIs
    "Hench, J. Am. Ceram. Soc. 1998": "10.1111/j.1151-2916.1998.tb02540.x",
    # Metal DOIs
    "Kim & Kim, J. Am. Ceram. Soc. 2002, 85, 1628": "10.1111/j.1151-2916.2002.tb00325.x",
    "Paine & Narula, Chem. Rev. 1990, 90, 73-91": "10.1021/cr00099a004",
    "Wei & Becher, J. Am. Ceram. Soc. 1984, 67, 571": "10.1111/j.1151-2916.1984.tb19603.x",
    "Adachi, J. Appl. Phys. 1985, 58, R1": "10.1063/1.336070",
    "Lloyd, Int. Mater. Rev. 1994, 39, 1-23": "10.1179/imr.1994.39.1.1",
    "Butler, Mater. Sci. Technol. 1985, 1, 417-432": "10.1179/mst.1985.1.6.417",
}

# ── Identify battery.json duplicates ──────────────────────────────────────

def pair_identity(pair):
    """Canonical identity for symmetric compatibility: (sorted materials, electrolyte)."""
    mats = tuple(sorted((pair["material_a"], pair["material_b"])))
    return (mats, pair.get("electrolyte"))


def deduplicate_battery(battery_data, blind_pairs):
    """Remove battery pairs that duplicate blind test pairs or each other."""
    # Build set of blind test identities (battery domain only)
    blind_ids = set()
    for p in blind_pairs:
        if p.get("domain", "battery") == "battery" or p.get("domain", "").startswith("battery"):
            blind_ids.add(pair_identity(p))

    seen = set()
    kept = []
    removed_ids = []

    for pair in battery_data["pairs"]:
        pid = pair_identity(pair)

        # Skip if this identity is in blind test pairs
        if pid in blind_ids:
            # But keep the original IDs 1-16, 25-27, 30 that ARE the blind test copies
            # Actually, these should be removed from battery.json since they're loaded
            # separately from blind_test_pairs.json
            removed_ids.append(pair["id"])
            continue

        # Skip if we've already seen this identity
        if pid in seen:
            removed_ids.append(pair["id"])
            continue

        seen.add(pid)
        kept.append(pair)

    print(f"  Battery: {len(battery_data['pairs'])} -> {len(kept)} pairs ({len(removed_ids)} removed)")
    print(f"  Removed IDs: {removed_ids}")

    battery_data["pairs"] = kept
    return battery_data


def add_fields_to_pairs(pairs, domain, tuning_ids=None):
    """Add doi and used_for_tuning to each pair dict."""
    if tuning_ids is None:
        tuning_ids = set()

    for pair in pairs:
        # Add DOI from citation lookup
        if "doi" not in pair or pair["doi"] is None:
            citation = pair.get("citation", "")
            pair["doi"] = CITATION_DOIS.get(citation)

        # Add used_for_tuning
        if "used_for_tuning" not in pair:
            pair["used_for_tuning"] = pair["id"] in tuning_ids


def main():
    # ── Load blind test pairs ─────────────────────────────────────────
    blind_path = AUDIT_DIR / "blind_test_pairs.json"
    with open(blind_path) as f:
        blind_data = json.load(f)

    # ── Process battery.json ──────────────────────────────────────────
    print("Processing battery.json...")
    bat_path = GT_DIR / "battery.json"
    with open(bat_path) as f:
        battery_data = json.load(f)

    battery_data = deduplicate_battery(battery_data, blind_data["pairs"])

    # All remaining battery pairs are 300-series expansion (used during Phase 11/13 tuning)
    battery_tuning_ids = {p["id"] for p in battery_data["pairs"]}  # all are tuning
    add_fields_to_pairs(battery_data["pairs"], "battery", battery_tuning_ids)

    battery_data["description"] = (
        "Literature-validated battery material compatibility pairs. "
        "De-duplicated 2026-05-19; pairs overlapping blind_test_pairs.json removed."
    )
    with open(bat_path, "w") as f:
        json.dump(battery_data, f, indent=2)
    print(f"  Wrote {bat_path}")

    # ── Process other ground truth files ──────────────────────────────
    # Tuning IDs by domain (pairs known to have been used during bridge calibration)
    domain_tuning = {
        "semiconductor": {210, 211},  # SiC_4H+GaN override, lattice veto tuning
        "polymer": set(),  # chi tuning used HDPE/PP/PVDF pairs but those are generic knowledge
        "metal": set(),  # galvanic veto uses MIL-STD table, not specific pair tuning
        "ceramic": set(),  # CTE veto is from ASM Handbook, not pair-specific
        "glass": set(),
    }
    # Conservative: mark all as false (not used for tuning) unless specifically identified
    for domain in ["semiconductor", "polymer", "metal", "ceramic", "glass"]:
        gt_path = GT_DIR / f"{domain}.json"
        if not gt_path.exists():
            continue

        print(f"Processing {domain}.json...")
        with open(gt_path) as f:
            data = json.load(f)

        tuning_ids = domain_tuning.get(domain, set())
        add_fields_to_pairs(data["pairs"], domain, tuning_ids)

        with open(gt_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Wrote {gt_path} ({len(data['pairs'])} pairs)")

    # ── Process blind_test_pairs.json ─────────────────────────────────
    print("Processing blind_test_pairs.json...")
    # All blind test pairs were known since project inception = tuning
    for pair in blind_data["pairs"]:
        pair["used_for_tuning"] = True
        citation = pair.get("citation", "")
        if "doi" not in pair or pair["doi"] is None:
            pair["doi"] = CITATION_DOIS.get(citation)

    blind_data["warning"] = (
        "All 30 pairs overlap with audit/ground_truth/*.json or were known during development. "
        "These are tuning pairs, not held-out validation."
    )

    with open(blind_path, "w") as f:
        json.dump(blind_data, f, indent=2)
    print(f"  Wrote {blind_path}")

    # ── Summary ───────────────────────────────────────────────────────
    print("\n=== Summary ===")
    total_gt = 0
    total_doi = 0
    for domain in ["battery", "semiconductor", "polymer", "metal", "ceramic", "glass"]:
        gt_path = GT_DIR / f"{domain}.json"
        if not gt_path.exists():
            continue
        with open(gt_path) as f:
            data = json.load(f)
        n = len(data["pairs"])
        n_doi = sum(1 for p in data["pairs"] if p.get("doi"))
        total_gt += n
        total_doi += n_doi
        print(f"  {domain:15s}: {n:3d} pairs, {n_doi:3d} with DOI ({100*n_doi/n:.0f}%)")

    n_blind = len(blind_data["pairs"])
    n_blind_doi = sum(1 for p in blind_data["pairs"] if p.get("doi"))
    print(f"  {'blind_test':15s}: {n_blind:3d} pairs, {n_blind_doi:3d} with DOI ({100*n_blind_doi/n_blind:.0f}%)")
    print(f"\n  Total GT pairs: {total_gt}")
    print(f"  Total with DOI: {total_doi} ({100*total_doi/total_gt:.0f}%)")
    print(f"  Total loaded by audit runner: {total_gt + n_blind}")


if __name__ == "__main__":
    main()
