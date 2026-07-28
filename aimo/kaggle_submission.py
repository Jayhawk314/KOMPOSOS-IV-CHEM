# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Kaggle AIMO3 Submission Notebook

This is the complete Kaggle submission for AIMO3 Progress Prize 3.
Run this notebook on Kaggle with T4 GPU.

Requirements:
- sentence-transformers
- sympy
- torch (pre-installed on Kaggle)
"""

import sys
import os
import json

# Add KOMPOSOS-IV to path
sys.path.insert(0, '/kaggle/input/komposos-iv')

print("="*70)
print("  AIMO3 SOLVER — KAGGLE SUBMISSION")
print("="*70)

# Test imports
try:
    from aimo import AIMOSolver
    print("✅ AIMO solver imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Initialize solver
print("\nInitializing solver...")
solver = AIMOSolver(
    llm_model="qwen2.5-math",  # Available on Kaggle
    use_fast_ricci=True,
    max_paths=5,
    llm_budget_per_problem=8,
    verbose=True,
)
print("✅ Solver initialized")

# Test on sample problems
print("\n" + "="*70)
print("  TESTING ON SAMPLE PROBLEMS")
print("="*70)

TEST_PROBLEMS = [
    {
        "id": "sample_1",
        "problem": "Find the number of positive integers n ≤ 1000 such that n² ≡ 1 (mod 1000).",
        "expected": 4,
    },
    {
        "id": "sample_2",
        "problem": "How many integers between 1 and 1000 can be written as a² - b² for nonnegative integers a, b?",
        "expected": 750,
    },
    {
        "id": "sample_3",
        "problem": "What is 2 + 2?",
        "expected": 4,
    },
]

results = []

for prob in TEST_PROBLEMS:
    print(f"\n{'='*70}")
    print(f"Problem: {prob['id']}")
    print(f"Problem: {prob['problem'][:80]}...")
    print(f"Expected: {prob['expected']}")
    print(f"{'='*70}")
    
    # Solve
    answer = solver.solve(prob['id'], prob['problem'])
    
    print(f"\nAnswer: {answer}")
    
    correct = (answer == prob['expected'])
    status = "✅ CORRECT" if correct else "❌ WRONG"
    print(f"Status: {status}")
    
    results.append({
        "id": prob['id'],
        "expected": prob['expected'],
        "predicted": answer,
        "correct": correct,
    })

# Summary
print(f"\n{'='*70}")
print("  TEST SUMMARY")
print("="*70)

correct_count = sum(1 for r in results if r['correct'])
total = len(results)

print(f"\nCorrect: {correct_count}/{total} ({100*correct_count/total:.1f}%)")
print("\nDetailed results:")
for r in results:
    status = "✅" if r['correct'] else "❌"
    print(f"  {status} {r['id']}: predicted={r['predicted']}, expected={r['expected']}")

print(f"\n{'='*70}")
print("  KAGGLE SUBMISSION READY")
print("="*70)

# Now run on actual Kaggle competition data
print("\n\nConnecting to Kaggle AIMO API...")

try:
    import aimo_competition
    print("✅ AIMO competition API available")
    
    # Submit to competition
    submission_rows = []
    
    print("\nSolving competition problems...")
    for problem_id, problem_text in aimo_competition.problems():
        print(f"  Solving {problem_id}...")
        answer = solver.solve(problem_id, problem_text)
        submission_rows.append({"id": problem_id, "answer": answer})
        print(f"    Answer: {answer}")
    
    # Save submission
    import pandas as pd
    submission_df = pd.DataFrame(submission_rows)
    submission_df.to_csv("submission.csv", index=False)
    
    print(f"\n✅ Submission saved to submission.csv")
    print(f"   Total problems: {len(submission_rows)}")
    
except ImportError:
    print("⚠️  AIMO API not available (not running on Kaggle)")
    print("\nTo submit on Kaggle:")
    print("1. Upload KOMPOSOS-IV as dataset")
    print("2. Create notebook with this code")
    print("3. Run notebook")
    print("4. Download submission.csv")

print("\n" + "="*70)
print("  COMPLETE")
print("="*70)
