"""Merge a sealed hidden-label file into a scorable benchmark file.

This is the *authorized scoring event* for a sealed blind holdout. It refuses to
run unless the recorded SHA256 seals still match, so a label file that was edited
after freezing cannot be silently merged and scored.

Usage:
    python audit/merge_sealed_labels.py --period 2026_q11
    python audit/merge_sealed_labels.py --period 2026_q11 --check-only

Writes audit/external_blind/compatibility_<period>.json (the scorable file),
which is what `run_audit.py --module external --external-path ...` consumes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_DIR = Path(__file__).parent / "external_blind"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_seal(path: Path, expected: str, label: str) -> bool:
    actual = _sha256(path)
    ok = actual == expected
    status = "OK" if ok else "SEAL BROKEN"
    print(f"  {label}: {status}")
    if not ok:
        print(f"    expected {expected}")
        print(f"    actual   {actual}")
    return ok


def merge(period: str, check_only: bool = False) -> int:
    pairs_path = _DIR / f"compatibility_{period}_pairs_unlabeled.json"
    labels_path = _DIR / f"compatibility_{period}_labels_hidden.json"
    out_path = _DIR / f"compatibility_{period}.json"

    for p in (pairs_path, labels_path):
        if not p.exists():
            print(f"ERROR: missing {p}")
            return 2

    labels_doc = json.loads(labels_path.read_text(encoding="utf-8"))
    pairs_doc = json.loads(pairs_path.read_text(encoding="utf-8"))

    print(f"Verifying seals for {period}:")
    recorded_pairs_sha = labels_doc.get("pairs_file_sha256")
    if not recorded_pairs_sha:
        print("  ERROR: labels file records no pairs_file_sha256; cannot verify seal")
        return 2
    ok = _verify_seal(pairs_path, recorded_pairs_sha, "pairs file")

    sidecar = _DIR / f"{labels_path.name}.sha256"
    if sidecar.exists():
        recorded_labels_sha = sidecar.read_text(encoding="utf-8").split()[0]
        ok = _verify_seal(labels_path, recorded_labels_sha, "labels file") and ok
    else:
        print("  WARNING: no labels sidecar hash found; labels integrity unverified")

    if not ok:
        print("\nABORT: seal verification failed. Do not score this dataset.")
        return 1

    labels = labels_doc.get("labels", {})
    merged, missing = [], []
    for pair in pairs_doc.get("pairs", []):
        pid = str(pair.get("id"))
        if pid not in labels:
            missing.append(pid)
            continue
        rec = dict(pair)
        entry = labels[pid]
        rec["expected_compatible"] = bool(entry["expected_compatible"])
        rec["borderline"] = bool(entry.get("borderline", False))
        rec["label_basis"] = entry.get("basis")
        rec["used_for_tuning"] = False
        merged.append(rec)

    if missing:
        print(f"ERROR: {len(missing)} pairs have no sealed label: {missing[:10]}")
        return 2

    n_true = sum(1 for r in merged if r["expected_compatible"])
    print(f"\nMerged {len(merged)} pairs ({n_true} compatible / {len(merged) - n_true} incompatible)")

    if check_only:
        print("--check-only: no file written")
        return 0

    out_doc = {
        "version": pairs_doc.get("version", "").replace(".pairs_unlabeled", ""),
        "created_at": pairs_doc.get("created_at"),
        "merged_at_scoring_event": True,
        "benchmark_period": pairs_doc.get("benchmark_period", period),
        "frozen": True,
        "source_pairs_file": pairs_path.name,
        "source_pairs_sha256": recorded_pairs_sha,
        "source_labels_file": labels_path.name,
        "source_labels_sha256": _sha256(labels_path),
        "description": pairs_doc.get("description"),
        "selection_policy": pairs_doc.get("selection_policy"),
        "holdout_policy": pairs_doc.get("holdout_policy"),
        "known_limitations": pairs_doc.get("known_limitations"),
        "pair_count": len(merged),
        "pairs": merged,
    }
    out_path.write_text(json.dumps(out_doc, indent=2) + "\n", encoding="utf-8")
    out_sha = _sha256(out_path)
    (out_path.with_suffix(".sha256")).write_text(f"{out_sha}  {out_path.name}\n", encoding="utf-8")
    print(f"Wrote {out_path.name}  sha256={out_sha}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--period", required=True, help="benchmark period, e.g. 2026_q11")
    ap.add_argument("--check-only", action="store_true", help="verify seals without writing")
    args = ap.parse_args()
    return merge(args.period, args.check_only)


if __name__ == "__main__":
    sys.exit(main())
