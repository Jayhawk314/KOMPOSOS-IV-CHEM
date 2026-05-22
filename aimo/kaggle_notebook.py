"""
Kaggle Notebook - AIMO3 Competition Submission.

Self-contained Kaggle submission script using KOMPOSOS Theorem KG + LLM.

Setup on Kaggle:
1. Create notebook with GPU accelerator (4x H100)
2. Add competition dataset (aimo-progress-prize-3)
3. Upload KOMPOSOS-IV as a dataset (named "komposos-iv")
4. Upload LeanDojo corpus as a dataset (named "leandojo-corpus", REQUIRED - 180K theorems)
5. Upload Qwen model weights as a dataset (named "qwen25-math-72b", REQUIRED - no internet)
6. Run this notebook

Architecture:
- Theorem KG: 7-stage categorical retrieval (spectral, composition, Yoneda, Kan, Oracle, Ricci)
- LLM: Qwen2.5-Math-72B via vLLM with tensor_parallel=4
- For each problem: classify -> KG 7-stage query -> theorem context -> LLM strategy beam -> majority vote
- Budget: ~120s per problem, 110 problems = ~3.7 hours (within 5-hour limit)
- Outputs submission.csv in required format (id, answer)
"""

import subprocess
import sys
import os
import time
import csv


# ---------------------------------------------------------------------------
# Step 0: Setup paths and dependencies
# ---------------------------------------------------------------------------

def setup_environment():
    """Configure runtime: paths, dependencies, hardware check."""
    on_kaggle = os.path.exists("/kaggle")

    if on_kaggle:
        # Add KOMPOSOS-IV code to Python path
        # Try common Kaggle dataset naming conventions
        code_paths = [
            "/kaggle/input/komposos-iv",
            "/kaggle/input/komposos-iv-code",
            "/kaggle/input/komposos4",
        ]
        for code_path in code_paths:
            if os.path.isdir(code_path):
                sys.path.insert(0, code_path)
                print(f"KOMPOSOS-IV code: {code_path}")
                break
        else:
            print("WARNING: KOMPOSOS-IV code dataset not found!")
            print("Upload the repo as a Kaggle dataset named 'komposos-iv'")
            print("Checked:", code_paths)

        os.chdir("/kaggle/working")

        # Install vLLM if not available
        try:
            import vllm  # noqa: F401
            print("vLLM: already installed")
        except ImportError:
            print("Installing vLLM...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "vllm", "--quiet", "--no-warn-conflicts"
            ])
            print("vLLM: installed")

        # Check hardware
        try:
            import torch
            n_gpus = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if n_gpus > 0 else "none"
            print(f"GPUs: {n_gpus}x {gpu_name}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB per GPU")
        except (ImportError, RuntimeError):
            print("WARNING: No GPU detected!")

    else:
        # Local development
        sys.path.insert(0, '.')

    return on_kaggle


# ---------------------------------------------------------------------------
# Step 1: Find model weights (local dataset, required for no-internet Kaggle)
# ---------------------------------------------------------------------------

def find_model_path():
    """Find local model weights. Kaggle has no internet, so model must be a dataset."""
    model_paths = [
        # Kaggle dataset paths (try common naming)
        "/kaggle/input/qwen25-math-72b",
        "/kaggle/input/qwen25-math-72b-instruct",
        "/kaggle/input/qwen-math-72b",
        "/kaggle/input/qwen2.5-math-72b-instruct",
        # Smaller model fallbacks
        "/kaggle/input/qwen25-math-7b",
        "/kaggle/input/qwen25-math-7b-instruct",
        "/kaggle/input/qwen-math-7b",
    ]

    for path in model_paths:
        if os.path.isdir(path):
            # Check it has model files (config.json or model index)
            if (os.path.exists(os.path.join(path, "config.json")) or
                    os.path.exists(os.path.join(path, "model.safetensors.index.json"))):
                print(f"Model found: {path}")
                return path

    # Not found - will try HuggingFace hub name (works if internet available)
    print("WARNING: No local model weights found. Will try HuggingFace hub.")
    print("For offline Kaggle: upload model weights as a dataset.")
    print("Checked:", model_paths[:4])
    return None


# ---------------------------------------------------------------------------
# Step 2: Build Theorem Knowledge Graph
# ---------------------------------------------------------------------------

def build_theorem_kg():
    """Build the theorem knowledge graph from LeanDojo corpus."""
    from aimo.theorem_kg import get_global_kg
    from domains.mathematics.leandojo_adapter import LeanDojoAdapter

    kg = get_global_kg()

    # Find LeanDojo corpus
    corpus_paths = [
        "/kaggle/input/leandojo-corpus/corpus.jsonl",
        "/kaggle/input/leandojo-corpus/leandojo_benchmark_4/corpus.jsonl",
        "/kaggle/input/leandojo/corpus.jsonl",
        "/kaggle/input/leandojo-benchmark-4/corpus.jsonl",
        "data_sources/leandojo/leandojo_benchmark_4/corpus.jsonl",
        "data_sources/leandojo/corpus.jsonl",
    ]

    adapter = None
    for path in corpus_paths:
        if os.path.exists(path):
            corpus_dir = os.path.dirname(path)
            print(f"Loading LeanDojo corpus from {corpus_dir}...")
            adapter = LeanDojoAdapter(data_path=corpus_dir)
            break

    if adapter is None:
        print("ERROR: LeanDojo corpus not found! Checked:")
        for p in corpus_paths:
            print(f"  - {p}")
        print("Upload leandojo_benchmark_4 as a Kaggle dataset named 'leandojo-corpus'.")
        raise FileNotFoundError("LeanDojo corpus required but not found")

    result = kg.ingest_corpus(adapter)
    n_obj = result.get('objects', 0)
    n_mor = result.get('morphisms', 0)
    print(f"Loaded {n_obj} theorems, {n_mor} dependencies")

    # Analyze structure (spectral clustering, Ricci curvature)
    print("Analyzing theorem graph structure...")
    kg.analyze_structure()
    n_clusters = len(kg._clusters) if kg._clusters else 0
    print(f"KG ready: {n_clusters} clusters")

    return kg


# ---------------------------------------------------------------------------
# Step 3: Load competition problems
# ---------------------------------------------------------------------------

def load_problems(input_path: str = "/kaggle/input/aimo-progress-prize-3"):
    """Load competition problems from CSV."""
    problems = {}

    csv_path = os.path.join(input_path, "test.csv")
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                problems[row['id']] = row['problem']
        print(f"Loaded {len(problems)} problems from {csv_path}")
    else:
        print(f"No competition data at {csv_path} - using demo problems")
        problems = {
            "demo_1": "Find the number of integers between 1 and 1000 "
                       "that can be expressed as difference of squares",
            "demo_2": "The quadratic x^2 - 5x + 6 = 0 has roots. "
                       "Find sum of their squares",
            "demo_3": "Smallest perfect cube divisible by 12",
            "demo_4": "How many 3-digit numbers have all distinct digits",
        }

    return problems


# ---------------------------------------------------------------------------
# Step 4: Create solver with correct backend
# ---------------------------------------------------------------------------

def create_solver(model_path: str = None):
    """Create the solver with Theorem KG + LLM strategy beam."""
    from aimo.llm_engine import LLMConfig
    from aimo.olympiad_solver import OlympiadSolver

    # Determine model name: local path (preferred) or HuggingFace hub name
    model_72b = model_path or "Qwen/Qwen2.5-Math-72B-Instruct"
    model_7b = "Qwen/Qwen2.5-Math-7B-Instruct"

    # Detect best backend
    config = None

    # Try vLLM first (best for H100)
    try:
        import vllm  # noqa: F401
        import torch
        n_gpus = torch.cuda.device_count()
        tp = min(n_gpus, 4)  # tensor parallel across available GPUs
        config = LLMConfig(
            model_name=model_72b,
            backend="vllm",
            tensor_parallel_size=tp,
            max_tokens=2048,
            temperature=0.7,
        )
        print(f"Backend: vLLM | Model: {model_72b} | TP={tp}")
    except ImportError:
        pass

    # Try transformers (local GPU without vLLM)
    if config is None:
        try:
            import torch
            if torch.cuda.is_available():
                config = LLMConfig(
                    model_name=model_7b,
                    backend="transformers",
                    max_tokens=1024,
                    temperature=0.7,
                )
                print(f"Backend: transformers | Model: {model_7b}")
        except ImportError:
            pass

    # Last resort: HF API (requires internet + credits)
    if config is None:
        hf_token = os.environ.get("HF_TOKEN", "")
        config = LLMConfig(
            model_name=model_7b,
            backend="hf_api",
            api_token=hf_token,
            max_tokens=1024,
            temperature=0.7,
        )
        print(f"Backend: HF API | Model: {model_7b}")

    # Create solver - legacy path with full TheoremKG categorical retrieval
    solver = OlympiadSolver(
        llm_config=config,
        beam_width=6,
        max_candidates=12,
        time_budget_per_problem=150.0,
        verbose=True,
    )
    # TIR is already disabled in olympiad_solver.py
    # Double-ensure it's off (legacy path has TheoremKG, TIR does not)
    solver._tir_solver = None

    return solver


# ---------------------------------------------------------------------------
# Step 5: Solve all problems
# ---------------------------------------------------------------------------

def solve_all(solver, problems: dict) -> dict:
    """Solve all problems with timing and progress."""
    results = {}
    total = len(problems)

    print(f"\nSolving {total} problems...")
    print(f"Estimated time: {total * 150 / 3600:.1f} hours max")
    print("-" * 60)

    global_start = time.time()

    for i, (pid, text) in enumerate(problems.items()):
        start = time.time()

        answer = solver.solve(text, problem_id=pid)
        results[pid] = answer

        elapsed = time.time() - start
        total_elapsed = time.time() - global_start
        avg_time = total_elapsed / (i + 1)
        eta = avg_time * (total - i - 1)

        print(f"  [{i+1}/{total}] {pid}: {answer} "
              f"({elapsed:.1f}s, ETA: {eta/60:.1f}min)")

    total_time = time.time() - global_start
    print(f"\nCompleted {total} problems in {total_time/60:.1f} minutes")
    print(f"Average: {total_time/total:.1f}s per problem")

    return results


# ---------------------------------------------------------------------------
# Step 6: Write submission
# ---------------------------------------------------------------------------

def write_submission(results: dict, output_path: str = "submission.csv"):
    """Write Kaggle submission CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'answer'])
        for pid, answer in sorted(results.items()):
            writer.writerow([pid, answer])

    print(f"Submission written: {output_path} ({len(results)} answers)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main entry point."""
    print("=" * 60)
    print("  AIMO3 - KOMPOSOS Theorem KG + LLM Solver")
    print("  7-Stage Categorical Retrieval + Strategy Beam")
    print("=" * 60)

    # Step 0: Setup
    on_kaggle = setup_environment()

    # Step 1: Find model
    print("\n" + "=" * 60)
    print("Step 1: Finding Model Weights...")
    print("=" * 60)
    model_path = find_model_path()

    # Step 2: Build theorem KG
    print("\n" + "=" * 60)
    print("Step 2: Building Theorem Knowledge Graph (180K theorems)...")
    print("=" * 60)
    kg = build_theorem_kg()

    # Step 3: Load problems
    print("\n" + "=" * 60)
    print("Step 3: Loading Competition Problems...")
    print("=" * 60)
    if on_kaggle:
        problems = load_problems()
    else:
        problems = load_problems(".")
        if not problems:
            problems = load_problems("/nonexistent")

    # Step 4: Create solver
    print("\n" + "=" * 60)
    print("Step 4: Creating Solver (legacy path + TheoremKG)...")
    print("=" * 60)
    solver = create_solver(model_path=model_path)

    # Step 5: Solve
    print("\n" + "=" * 60)
    print("Step 5: Solving Problems...")
    print("=" * 60)
    results = solve_all(solver, problems)

    # Step 6: Write submission
    output = "/kaggle/working/submission.csv" if on_kaggle else "submission.csv"
    write_submission(results, output)

    print("\n" + "=" * 60)
    print("Done! Submission ready.")
    print("=" * 60)


if __name__ == "__main__":
    main()
