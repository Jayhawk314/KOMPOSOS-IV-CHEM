# Testing KOMPOSOS on AIMO3 Public Problems

## Quick Start

### 1. Get the Public Problems

Download from Kaggle:
```bash
# Go to: https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/data
# Download test.csv (contains 50 public + 50 private problems)
# Place in: aimo/data/aimo3_public/test.csv
```

### 2. Set Up API Key

**Option A: Environment Variable**
```bash
export OPENROUTER_API_KEY="your_key_here"
```

**Option B: .env File**
Create `.env` in project root:
```
OPENROUTER_API_KEY=your_key_here
```

Get your OpenRouter key at: https://openrouter.ai/

### 3. Run Tests

**Full test (all 50 public problems):**
```bash
python aimo/test_public_50.py --backend openrouter
```

**Quick test (first 5 problems):**
```bash
python aimo/test_public_50.py --backend openrouter --limit 5
```

**Resume from problem 10:**
```bash
python aimo/test_public_50.py --backend openrouter --start 10
```

## Performance Goals

| Score | Accuracy | Status |
|-------|----------|--------|
| 44/50 | 88% | Current public leaderboard best |
| 47/50 | 94% | Competitive |
| 48/50 | 96% | Target (97% goal) |
| 50/50 | 100% | Perfect |

## Backend Options

### OpenRouter (GPT-OSS-120B) - RECOMMENDED
```bash
python aimo/test_public_50.py --backend openrouter
```
- **Model**: GPT-OSS-120B (best for olympiad math)
- **Cost**: ~$0.01 per problem (est. $0.50 for 50 problems)
- **Speed**: ~120s per problem
- **Total time**: ~2 hours for 50 problems

### HuggingFace API (Qwen2.5-Math-7B)
```bash
python aimo/test_public_50.py --backend hf_api
```
- **Model**: Qwen2.5-Math-7B-Instruct
- **Cost**: Free (with HF Pro) or pay-per-use
- **Speed**: ~60s per problem
- **Total time**: ~1 hour for 50 problems

### Mock (Pattern Matching Only)
```bash
python aimo/test_public_50.py --backend mock
```
- **Model**: None (pattern matching + calculator only)
- **Cost**: Free
- **Speed**: ~5s per problem
- **Expected**: 8-12/50 (direct-solvable problems only)

## Output Files

Results are saved to `aimo/results/`:

- **submission_TIMESTAMP.csv** - Kaggle submission format (id, answer)
- **results_TIMESTAMP.json** - Detailed results with timing and correctness
- **partial_submission_TIMESTAMP.csv** - Auto-saved every 10 problems

## Architecture

The solver uses:

1. **TheoremKG (180K theorems)** - 7-stage categorical retrieval:
   - Spectral clustering (GraphLaplacian)
   - Composition paths (category theory)
   - Yoneda similarity (Hom-set matching)
   - Kan extensions (gap-filling, 1.8x weight)
   - Oracle strategies (StructuralHole + Geometric, 2.0x weight)
   - Ricci curvature ranking (cached)
   - Persistent homology (multi-step detection)

2. **LLM Strategy Beam** - 6-8 strategies x 3 samples:
   - Self-consistency voting per strategy
   - Code verification (1.5x weight boost)
   - Majority vote across strategies

3. **Fallback Path** - Pattern matching + calculator:
   - 20+ computation patterns
   - Formula-based direct solve

## Debugging

**Enable verbose output:**
```python
# Edit test_public_50.py line 117:
solver = OlympiadSolver(..., verbose=True)
```

**Test single problem:**
```python
from aimo.olympiad_solver import OlympiadSolver
from aimo.llm_engine import LLMConfig

config = LLMConfig(
    model_name="openai/gpt-oss-120b",
    backend="openrouter",
    api_token="your_key"
)
solver = OlympiadSolver(llm_config=config, verbose=True)

answer = solver.solve("Your problem text here")
print(f"Answer: {answer}")
```

## Tips for 97% Accuracy

1. **Use GPT-OSS-120B** - Specifically trained for competition math
2. **Increase time budget** - Edit `time_budget_per_problem=180.0` → `300.0`
3. **More samples** - Edit `beam_width=8` → `12` (but slower)
4. **Check hard problems** - Problems that fail are usually:
   - Geometry (may need diagram reasoning)
   - Combinatorics (complex counting)
   - Number theory (advanced modular arithmetic)

## Competition Submission

To submit to Kaggle AIMO3:
1. Use `aimo/kaggle_notebook.py` (production version)
2. Upload KOMPOSOS-IV as Kaggle dataset
3. Upload LeanDojo corpus (180K theorems) as dataset
4. Upload model weights (Qwen2.5-Math-72B) as dataset
5. Run notebook on 4x H100 GPUs

Estimated: ~3.7 hours for 110 problems (within 5-hour limit)
