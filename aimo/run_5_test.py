"""Run 5 test problems. Simple, no framework."""
import sys, os, time, csv
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

# Load problems
problems = []
with open("aimo/data/aimo3_public/demo_test.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        problems.append((row["id"], row["problem"]))

print(f"Loaded {len(problems)} problems", flush=True)

# Create solver
config = LLMConfig(model_name="openai/gpt-oss-120b", backend="openrouter",
                   api_token=api_key, max_tokens=2048, temperature=0.7)
solver = OlympiadSolver(llm_config=config, beam_width=6, verbose=False)
print("Solver ready", flush=True)

# Solve each
results = {}
t_total = time.time()
for i, (pid, text) in enumerate(problems):
    t0 = time.time()
    answer = solver.solve(text, problem_id=pid)
    dt = time.time() - t0
    results[pid] = answer
    print(f"[{i+1}/{len(problems)}] {pid}: {answer} ({dt:.1f}s)", flush=True)

print(f"\nAll done in {time.time()-t_total:.1f}s", flush=True)
for pid, ans in results.items():
    print(f"  {pid} = {ans}", flush=True)
