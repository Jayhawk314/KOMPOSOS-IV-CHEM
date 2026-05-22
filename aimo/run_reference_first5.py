"""Run first 5 AIMO3 Reference Problems with DeepSeek R1."""
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

# Load first 5 problems only
problems = []
with open("aimo/data/aimo3_public/reference_test.csv", encoding="utf-8") as f:
    for i, row in enumerate(csv.DictReader(f)):
        if i >= 5:
            break
        problems.append((row["id"], row["problem"], int(row["answer"])))

print(f"AIMO3 Reference (First 5): {len(problems)} problems", flush=True)
print(f"Model: deepseek/deepseek-r1 via OpenRouter", flush=True)
print("-" * 60, flush=True)

config = LLMConfig(model_name="deepseek/deepseek-r1", backend="openrouter",
                   api_token=api_key, max_tokens=8192, temperature=0.7)
solver = OlympiadSolver(llm_config=config, beam_width=3, verbose=False)
print("Solver ready", flush=True)
print("-" * 60, flush=True)

results = {}
correct = 0
t_total = time.time()

for i, (pid, text, expected) in enumerate(problems):
    t0 = time.time()
    try:
        answer = solver.solve(text, problem_id=pid)
    except Exception as e:
        print(f"  ERROR on {pid}: {e}", flush=True)
        answer = 0
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

print("\nResults:", flush=True)
for pid, r in results.items():
    mark = "OK" if r["correct"] else "XX"
    print(f"  [{mark}] {pid}: got {r['answer']}, expected {r['expected']} ({r['time']:.1f}s)", flush=True)
