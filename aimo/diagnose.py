# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Minimal diagnostic - find exactly where the solver hangs."""
import sys, os, time
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

print("STEP 1: imports", flush=True)
from aimo.llm_engine import LLMConfig, LLMEngine

print("STEP 2: loading API key", flush=True)
api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    try:
        with open('.env') as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY"):
                    api_key = line.split('=', 1)[1].strip()
    except:
        pass
print(f"  key found: {bool(api_key)}", flush=True)

print("STEP 3: testing raw API call", flush=True)
t0 = time.time()
config = LLMConfig(model_name="openai/gpt-oss-120b", backend="openrouter",
                   api_token=api_key, max_tokens=50)
engine = LLMEngine(config)
result = engine.generate("What is 7*8?", n=1, temperature=0.3)
print(f"  API response: {len(result[0])} chars in {time.time()-t0:.1f}s", flush=True)

print("STEP 4: loading TheoremKG (this takes ~4 min)", flush=True)
t0 = time.time()
from aimo.math_context import MathContextBuilder
from aimo.problem_classifier import ProblemClassifier
builder = MathContextBuilder(verbose=False)
classifier = ProblemClassifier()
# Force KG load
kg = builder._get_kg()
n_obj = len(kg.category.objects())
print(f"  KG loaded: {n_obj} theorems in {time.time()-t0:.1f}s", flush=True)

print("STEP 5: building context for test problem", flush=True)
t0 = time.time()
problem = "Find the number of integers between 1 and 1000 that can be expressed as difference of squares"
features = classifier.classify(problem)
ctx = builder.build_context(problem, features)
print(f"  context: {len(ctx.context_text)} chars, hint={ctx.computation_hint}, {time.time()-t0:.1f}s", flush=True)

print("STEP 6: creating solver", flush=True)
t0 = time.time()
from aimo.olympiad_solver import OlympiadSolver
solver = OlympiadSolver(llm_config=config, beam_width=3, verbose=False)
print(f"  solver created in {time.time()-t0:.1f}s", flush=True)

print("STEP 7: solving problem", flush=True)
t0 = time.time()
answer = solver.solve(problem)
print(f"  ANSWER: {answer} in {time.time()-t0:.1f}s", flush=True)

print("DONE", flush=True)
