"""
AIMO3 EXPANDED TEST - Olympiad Level Problems

Tests the solver on harder problems (difficulty 6-10) beyond the baseline 8.
"""

import sys
sys.path.insert(0, '.')

from aimo.aimo3_solver import AIMO3RAGSolver

# Expanded test problems - MIX OF DIFFICULTY LEVELS
# Format: (name, problem_text, expected_answer, difficulty)
EXPANDED_TESTS = [
    # =====================================================================
    # BASELINE TESTS (difficulty 1-5) - Should pass
    # =====================================================================
    ("baseline_diff_squares", 
     "Find the number of integers between 1 and 1000 that can be expressed as difference of squares", 
     750, 3),
    
    ("baseline_vieta", 
     "The quadratic x² - 5x + 6 = 0 has roots. Find sum of their squares", 
     13, 2),
    
    ("baseline_geometric", 
     "Geometric sequence: 3rd term is 12, 5th term is 48. Find 7th term", 
     192, 3),
    
    # =====================================================================
    # INTERMEDIATE TESTS (difficulty 4-6) - New
    # =====================================================================
    ("intermediate_euler_totient", 
     "Find φ(100), the number of positive integers less than 100 that are coprime to 100", 
     40, 5),
    
    ("intermediate_fibonacci_mod", 
     "Find the remainder when F_100 is divided by 1000", 
     500, 6),  # F_100 mod 1000
    
    ("intermediate_crt", 
     "Find the smallest positive integer x such that x ≡ 2 (mod 3), x ≡ 3 (mod 5), x ≡ 2 (mod 7)", 
     23, 5),
    
    ("intermediate_catalan", 
     "Find the 5th Catalan number C_5", 
     42, 5),
    
    ("intermediate_derangement", 
     "Find the number of derangements of 5 objects (!5)", 
     44, 5),
    
    # =====================================================================
    # ADVANCED TESTS (difficulty 6-8) - Olympiad Level
    # =====================================================================
    ("advanced_fermat", 
     "Find 3^16 mod 17 using Fermat's Little Theorem", 
     1, 7),
    
    ("advanced_wilson", 
     "Find 16! mod 17 using Wilson's Theorem", 
     16, 7),
    
    ("advanced_legendre", 
     "Find the Legendre symbol (2/17)", 
     1, 7),
    
    ("advanced_divisor_sum", 
     "Find the sum of all positive divisors of 100", 
     217, 6),
    
    ("advanced_partition", 
     "Find the number of integer partitions of 10", 
     42, 7),
    
    ("advanced_stirling", 
     "Find S(5,3), the Stirling number of the second kind", 
     25, 7),
    
    # =====================================================================
    # EXPERT TESTS (difficulty 8-10) - IMO Level
    # =====================================================================
    ("expert_heron", 
     "Find the area of a triangle with sides 13, 14, and 15", 
     84, 8),
    
    ("expert_circumcircle", 
     "Find the circumradius of a triangle with sides 5, 12, and 13", 
     6, 8),
    
    ("expert_tangent", 
     "From a point 13 units from the center of a circle with radius 5, find the length of the tangent", 
     12, 8),
    
    ("expert_binomial", 
     "Find the coefficient of x³ in the expansion of (1+x)^10", 
     120, 7),
    
    ("expert_dice", 
     "Two fair dice are rolled. Find the number of ways to get a sum of 7", 
     1, 6),  # 6/36 = 1/6, numerator = 1
]


def run_expanded_test():
    print("\n" + "="*80)
    print("  AIMO3 EXPANDED TEST - Olympiad Level")
    print("  Testing on 20 problems across difficulty levels")
    print("="*80)
    
    solver = AIMO3RAGSolver(verbose=False)
    
    # Group by difficulty
    results_by_difficulty = {
        (1, 3): {"correct": 0, "total": 0},
        (4, 6): {"correct": 0, "total": 0},
        (7, 9): {"correct": 0, "total": 0},
        (10, 12): {"correct": 0, "total": 0},
    }
    
    detailed_results = []
    
    for name, problem, expected, difficulty in EXPANDED_TESTS:
        answer, trace = solver.solve(problem)
        correct = answer == expected
        
        # Determine difficulty bucket
        bucket = None
        for (low, high), data in results_by_difficulty.items():
            if low <= difficulty <= high:
                bucket = data
                break
        
        if bucket:
            bucket["total"] += 1
            if correct:
                bucket["correct"] += 1
        
        detailed_results.append({
            "name": name,
            "difficulty": difficulty,
            "correct": correct,
            "answer": answer,
            "expected": expected,
            "trace": trace
        })
        
        status = "✅" if correct else "❌"
        print(f"[D{difficulty}] {name}: {answer} (expected {expected}) {status}")
    
    # Summary by difficulty
    print("\n" + "="*80)
    print("  RESULTS BY DIFFICULTY")
    print("="*80)
    
    total_correct = 0
    total_all = 0
    
    for (low, high), data in results_by_difficulty.items():
        if data["total"] > 0:
            pct = 100 * data["correct"] / data["total"]
            print(f"  Difficulty {low}-{high}: {data['correct']}/{data['total']} ({pct:.1f}%)")
            total_correct += data["correct"]
            total_all += data["total"]
    
    overall_pct = 100 * total_correct / total_all if total_all > 0 else 0
    print(f"\n  OVERALL: {total_correct}/{total_all} ({overall_pct:.1f}%)")
    
    # Analysis
    print("\n" + "="*80)
    print("  ANALYSIS")
    print("="*80)
    
    # Check for systematic errors
    error_patterns = {}
    for r in detailed_results:
        if not r["correct"]:
            diff = r["difficulty"]
            error_patterns[diff] = error_patterns.get(diff, 0) + 1
    
    if error_patterns:
        print("\n  Errors by difficulty:")
        for diff, count in sorted(error_patterns.items()):
            print(f"    Difficulty {diff}: {count} errors")
    else:
        print("\n  ✅ No errors!")
    
    # Failed tests detail
    failed = [r for r in detailed_results if not r["correct"]]
    if failed:
        print(f"\n  Failed tests ({len(failed)}):")
        for r in failed[:5]:  # Show first 5
            print(f"    - {r['name']}: got {r['answer']}, expected {r['expected']}")
    
    print("\n" + "="*80 + "\n")
    
    return overall_pct


if __name__ == "__main__":
    run_expanded_test()
