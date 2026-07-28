# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import json
import sys

def compute_auroc(scores, labels):
    """Compute AUROC manually."""
    pairs = sorted(zip(scores, labels), key=lambda x: x[0], reverse=True)
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos

    if n_pos == 0 or n_neg == 0:
        return 0.5

    tp = fp = 0
    prev_fpr = prev_tpr = 0.0
    auroc = 0.0

    for score, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1

        tpr = tp / n_pos
        fpr = fp / n_neg
        auroc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
        prev_fpr = fpr
        prev_tpr = tpr

    auroc += (1.0 - prev_fpr) * (1.0 + prev_tpr) / 2.0
    return auroc

def main():
    try:
        with open('audit/audit_report_2026-05-29.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    module_data = data.get('modules', {}).get('external_blind_compatibility', {})
    metadata = module_data.get('metadata', {})
    details = module_data.get('details', [])

    scores = []
    labels = []

    for item in details:
        if 'expected_compatible' in item:
            expected = item.get('expected_compatible')
            # The score we want is the ensemble score if it exists, otherwise the base score
            # Looking at the output, there is 'score', and 'decision' -> 'metadata' -> 'ensemble' -> 'score'
            # We'll just use 'score' which seems to be the ensemble or final score used for prediction
            score = item.get('score')
            if expected is not None and score is not None:
                labels.append(1 if expected else 0)
                scores.append(float(score))

    if not scores:
        print("No evaluated pairs found.")
        return

    auroc = compute_auroc(scores, labels)
    print("=" * 60)
    print("CHEMISTRY CORE SYSTEM AUROC TEST")
    print("=" * 60)
    dataset = metadata.get('version') or metadata.get('benchmark_period') or 'external_blind_compatibility'
    print(f"Dataset: {dataset}")
    print(f"Evaluated Pairs: {len(scores)}")
    print(f"Positive labels: {sum(labels)}")
    print(f"Negative labels: {len(labels) - sum(labels)}")
    print(f"AUROC: {auroc:.4f}")
    print("=" * 60)

if __name__ == "__main__":
    main()
