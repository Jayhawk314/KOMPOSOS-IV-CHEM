# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS-III AUROC & Precision-Recall Curve Analysis
====================================================

Calculates Area Under ROC and PR curves for the scientific audit.
Provides a threshold-independent measure of the engine's predictive power.
"""

import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_curve, auc
import matplotlib.pyplot as plt

def run_performance_analysis(report_path: str):
    print(f"Analyzing performance from: {report_path}")
    
    with open(report_path, "r") as f:
        data = json.load(f)
        
    results = data.get("modules", {}).get("scientific_accuracy", {}).get("details", [])
    if not results:
        results = data.get("results", [])
        
    if not results:
        print("No scientific accuracy results found in report.")
        return

    y_true = []
    y_scores = []
    
    for r in results:
        # Check multiple possible keys for ground truth and scores
        actual = r.get("expected_compatible")
        if actual is None:
            actual = r.get("expected")
            
        score = r.get("score")
        
        if actual is not None and score is not None:
            y_true.append(1 if actual else 0)
            y_scores.append(score)
        
    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    
    # AUROC
    auroc = roc_auc_score(y_true, y_scores)
    
    # Precision-Recall AUC
    precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
    pr_auc = auc(recall, precision)
    
    # Find Optimal Threshold (Youden's J statistic)
    fpr, tpr, thresholds_roc = roc_curve(y_true, y_scores)
    j_scores = tpr - fpr
    optimal_idx = np.argmax(j_scores)
    optimal_threshold = thresholds_roc[optimal_idx]
    
    print("\n" + "=" * 50)
    print("THRESHOLD-INDEPENDENT PERFORMANCE")
    print("=" * 50)
    print(f"AUROC (Receiver Operating Characteristic): {auroc:.4f}")
    print(f"AUPRC (Precision-Recall Curve):        {pr_auc:.4f}")
    print(f"Optimal Threshold (Youden's J):        {optimal_threshold:.3f}")
    print("-" * 50)
    
    if auroc > 0.90:
        print("✓ EXCELLENT: Engine shows superior discriminative power.")
    elif auroc > 0.80:
        print("✓ GOOD: Engine is a reliable classifier.")
    else:
        print("⚠ FAIR: Model may require better feature calibration.")
        
    # Generate Plots (optional, but good for docs)
    # plt.figure()
    # plt.plot(fpr, tpr, label=f'ROC (area = {auroc:.2f})')
    # ...
    
    return {
        "auroc": float(auroc),
        "pr_auc": float(pr_auc),
        "optimal_threshold": float(optimal_threshold)
    }

if __name__ == "__main__":
    # Find latest audit report
    audit_dir = Path("audit")
    reports = list(audit_dir.glob("audit_report_*.json"))
    if reports:
        latest_report = sorted(reports)[-1]
        run_performance_analysis(str(latest_report))
    else:
        print("No audit reports found in audit/ directory.")
