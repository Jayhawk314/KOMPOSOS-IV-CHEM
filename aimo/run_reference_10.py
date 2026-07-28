# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Run 10 AIMO3 Reference Benchmark problems with answer checking."""
import sys, os, time, csv, json
sys.path.insert(0, '.')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from aimo.llm_engine import LLMConfig
from aimo.olympiad_solver import OlympiadSolver

# API key
api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    with open('.env') as f:
        for line in f:
            if line.startswith("OPENROUTER_API_KEY"):
                api_key = line.split('=', 1)[1].strip()

if not api_key:
    print("ERROR: No OPENROUTER_API_KEY found", flush=True)
    sys.exit(1)

# Load problems
problems = []
with open("aimo/data/aimo3_public/reference_test.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        problems.append((row["id"], row["problem"], int(row["answer"])))

print(f"AIMO3 Reference Benchmark: {len(problems)} problems", flush=True)
print(f"Model: openai/gpt-oss-120b via OpenRouter", flush=True)
print("-" * 60, flush=True)

# Create solver
config = LLMConfig(model_name="openai/gpt-oss-120b", backend="openrouter",
                   api_token=api_key, max_tokens=4096, temperature=0.7)
solver = OlympiadSolver(llm_config=config, beam_width=6, verbose=False)
print("Solver ready (TheoremKG will load on first problem)", flush=True)
print("-" * 60, flush=True)

# Solve each
results = {}
correct = 0
t_total = time.time()

for i, (pid, text, expected) in enumerate(problems):
    t0 = time.time()
    answer = solver.solve(text, problem_id=pid)
    dt = time.time() - t0
    is_correct = (answer == expected)
    if is_correct:
        correct += 1
    status = "CORRECT" if is_correct else "WRONG"
    results[pid] = {"answer": answer, "expected": expected, "correct": is_correct, "time": dt}
    print(f"[{i+1}/{len(problems)}] {pid}: {answer} (expected {expected}) [{status}] ({dt:.1f}s)", flush=True)

total_time = time.time() - t_total
print("-" * 60, flush=True)
print(f"Score: {correct}/{len(problems)} ({100*correct/len(problems):.0f}%)", flush=True)
print(f"Total time: {total_time:.1f}s ({total_time/len(problems):.1f}s avg)", flush=True)
print(flush=True)

# Summary
print("Results:", flush=True)
for pid, r in results.items():
    mark = "OK" if r["correct"] else "XX"
    print(f"  [{mark}] {pid}: got {r['answer']}, expected {r['expected']} ({r['time']:.1f}s)", flush=True)

# Save results
outpath = "aimo/results/reference_10_results.json"
os.makedirs(os.path.dirname(outpath), exist_ok=True)
with open(outpath, "w") as f:
    json.dump({"score": f"{correct}/{len(problems)}", "total_time": total_time, "results": results}, f, indent=2)
print(f"\nResults saved to {outpath}", flush=True)
