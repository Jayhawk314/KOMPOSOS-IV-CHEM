# KOMPOSOS-IV Math Discovery System

## What This Is

A computational runtime that implements Emily Riehl's infinity-category theory
as an operational engine, then uses it to scan 180,000 formalized theorems
from Lean's mathlib, find structural gaps, and classify which gaps are
genuine novel conjectures.

The system doesn't generate text. It treats mathematical proof libraries as
**geometric objects** -- graphs with curvature, topology, and spectral
structure -- then uses categorical gradient descent to find where the
structure is incomplete.

---

## The Core Stack

```
                    WHAT IT DOES                           WHERE IT LIVES
                    ============                           ==============

    LeanDojo         180K theorems from mathlib4           domains/mathematics/leandojo_adapter.py
    MMLKG            Mizar Mathematical Library            domains/mathematics/mmlkg_adapter.py
    NaturalProofs    ProofWiki + Stacks Project            domains/mathematics/naturalproofs_adapter.py
        |
        v
    MathKernel       3 independent Category instances      domains/mathematics/kernel.py
        |            (one per source -- convergence IS
        |             the signal)
        v
    +---+---+--------+-----------+
    |       |        |           |
   COG   OPTIMUS  Cosmos    DualEngine
    |       |        |           |
    v       v        v           v
  verify  refine   higher    classify
  claims  graphs  structure  conjectures
    |       |        |           |
    +---+---+--------+-----------+
        |
        v
    MathDiscoveryBridge              bridges/math_discovery_bridge.py
        |
        v
    DiscoveryResult
      - COG-verified convergent signals
      - OPTIMUS-discovered intermediate objects
      - InfinityCosmos fibrations and 2-cells
      - DualEngine verdicts: AGREE / HOLLOW / ORPHAN / REJECT
```

---

## How Each Layer Works (Real, Tested, With Code)

### 1. Category Runtime (`core/category.py`)

Everything is a Category. Objects are mathematical entities. Morphisms are
relationships with confidence values (quantale-enriched). Persistence is
automatic (SQLite). Hooks fire on mutations.

```python
from core.category import Category

cat = Category(db_path=":memory:")
cat.add("BanachSpace", type_name="concept")
cat.add("HilbertSpace", type_name="concept")
cat.connect("HilbertSpace", "BanachSpace", "is_a", confidence=0.99)

paths = cat.find_paths("HilbertSpace", "BanachSpace")
```

This is the substrate everything else builds on. 190 tests pass.

### 2. MathKernel -- Triple-Source Convergence (`domains/mathematics/kernel.py`)

The MathKernel runs **three independent Category instances** loaded from
three independent mathematical databases:

- **LeanDojo**: 180,907 theorems, 645,355 dependency morphisms (from mathlib4)
- **MMLKG**: Mizar Mathematical Library Knowledge Graph
- **NaturalProofs**: ProofWiki + Stacks Project

The key insight: **convergence across independent graphs IS the signal.**
If all 3 sources show the same topological feature, it's triple-confirmed.
If only 1 shows it, it's likely a source artifact.

```python
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter

kernel = MathKernel(db_dir=":memory:")
adapter = LeanDojoAdapter("data_sources/leandojo/leandojo_benchmark_4")
kernel.load_source("leandojo", adapter)

# Run convergent analysis (topology + geometry + spectral on all 3)
report = kernel.convergent_analysis()
# report.convergent_holes -- H1 features in 2+ sources
# report.convergent_clusters -- spherical regions in 2+ sources
# report.convergent_bridges -- hyperbolic bridges in 2+ sources
```

The kernel runs:
- **Persistent homology** (`topology/persistent_homology.py`) -- finds H1 loops/holes
- **Ollivier-Ricci curvature** (`geometry/ricci.py`) -- classifies regions as spherical (clusters) or hyperbolic (bridges)
- **Spectral analysis** (`geometry/spectral.py`) -- algebraic connectivity, eigenvalues

### 3. COG Engine -- 5-Tier Verification (`cog/engine.py`)

Claims about mathematical relationships are verified through 5 tiers of
increasing computational cost:

| Tier | Method | Time | What It Checks |
|------|--------|------|----------------|
| 0 | Graph lookup | ~1ms | Direct morphism exists? |
| 1 | Composition + paths | ~10ms | Transitive path exists? |
| 2 | Sheaf + Kan | ~100ms | Coherent under sheaf conditions? |
| 3 | ZFC Dual Engine | ~1s | Logically entailed AND structurally sound? |
| 4 | Full topology + flow | ~10s | 2-cells, curvature, interchange law |

When a discovery pipeline finds a convergent signal, COG verifies it:

```python
from cog.session import CogSession
from cog.engine import CogEngine
from cog.schema import CogClaim

session = CogSession(category=kernel.leandojo)
cog = CogEngine(session)

claim = CogClaim(
    source="Nat.Prime.dvd_mul",
    target="Nat.Prime",
    relation="depends_on",
    confidence=0.9,
)
result = cog.check_claim(claim, depth=3)
# result.status, result.confidence, result.tier
```

### 4. OPTIMUS -- Categorical Gradient Descent (`core/optimus.py`)

OPTIMUS is the self-refinement monad. It operates by:

1. Snapshotting a Category into an OPTIMUS RuntimeCategory
2. For each morphism A->C, searching all factorizations A->B->C
3. Keeping the factorization that improves the quantale weight
4. Syncing discovered shortcuts back to the Category

```
Classical gradient:  x_{t+1} = x_t - eta * grad(L)
OPTIMUS gradient:    m_{t+1} = argmax_{f in factorizations(m_t)} w(f)
```

Instead of adjusting parameters, OPTIMUS discovers **intermediate objects** --
mathematical concepts that should exist between two known concepts.

```python
from core.optimus import OptimusEngine

optimus = OptimusEngine(kernel.leandojo, max_depth=3)
result = optimus.refine(max_steps=20, depth=2)
# result["synced_morphisms"] -- new shortcuts discovered

# Find structural gaps (A->B->C exists but no A->C)
gaps = optimus.find_structural_gaps()
# Each gap is a candidate conjecture

# Discover intermediate objects
intermediates = optimus.discover_intermediates("TopologicalSpace", "MetricSpace")
```

When OPTIMUS finds a gap in the math graph, that gap is a **candidate
conjecture** -- a theorem that should exist but hasn't been formalized yet.

### 5. InfinityCosmos -- Higher Categorical Structure (`core/cosmos.py`)

Based on Riehl & Verity, "Infinity category theory from scratch" (arXiv:1608.05314).

The InfinityCosmos wraps a Category and provides:
- **Homotopy 2-category (h2K)**: 2-cells between parallel morphisms
- **Isofibration detection**: Distinguished morphisms with lifting properties
- **Cartesian fibrations**: Fiber structures preserving cartesian lifts
- **Yoneda embedding**: Representable presheaves, faithfulness score
- **Pointwise Kan extensions**: Via comma category (co)limits

```python
from core.cosmos import InfinityCosmos

cosmos = InfinityCosmos(kernel.cross_source)
h2k = cosmos.homotopy_2_category()      # Build h2K
fibs = cosmos.cartesian_fibrations()     # Find fibration structures
yoneda = cosmos.yoneda_embedding()       # Yoneda: is it fully faithful?
```

When built on the cross-source layer (theorems confirmed in multiple
databases), the cosmos reveals the **higher-dimensional structure of
mathematics itself** -- which theorems are in the same fiber (same kind of
theorem in different contexts), which are connected by 2-cells (alternative
proof strategies), and where the Yoneda embedding breaks (structural holes
in the formalization).

### 6. Dual Engine -- ZFC + CAT Verification (`zfc/bridge.py`)

Every discovered conjecture gets classified by running it through two
independent verification engines:

- **ZFC**: Is this logically entailed from the axioms?
- **CAT**: Is this structurally sound in the category graph?

The delta classification:

| Delta | ZFC | CAT | Meaning |
|-------|-----|-----|---------|
| **AGREE** | yes | yes | Both confirm -- known result |
| **ORPHAN** | yes | no | Logically forced but geometrically unsound |
| **HOLLOW** | no | yes | **NOVEL DISCOVERY** -- structurally real, logically baseless |
| **REJECT** | no | no | Neither supports it |

**HOLLOW results are the prize.** They are conjectures where the categorical
structure strongly suggests a theorem should exist, but no logical proof has
been found. These are the 59K holes.

```python
from zfc.store_adapter import StoreAdapter
from zfc.bridge import DualEngineBridge

adapter = StoreAdapter(kernel.leandojo)
dual = DualEngineBridge(adapter, category=kernel.leandojo)

result = dual.query("CompactSpace", "HausdorffSpace", "implies")
print(result.delta_type)  # AGREE, ORPHAN, HOLLOW, or REJECT
```

### 7. Formal Yoneda Proof (`core/formal_yoneda.py`)

The Yoneda distance metric is formally proven:
- d(y(A), y(B)) = |y(A) delta y(B)| / |y(A) union y(B)|
- d = 0 if and only if A is isomorphic to B
- Provably-correct absorb threshold replaces arbitrary 0.8

This means when OPTIMUS decides to merge or transfer knowledge between
objects, the threshold is mathematically derived, not heuristic.

### 8. Higher-Order OPTIMUS (`core/higher_order_optimus.py`)

Extends factorization to all categorical levels:
- Level 1: 1-morphism factorization (standard OPTIMUS)
- Level 2: 2-morphism factorization (vertical and horizontal composition)
- Level 3: Fibration factorization (intermediate total categories)
- Level 4: Functor factorization (C -> E -> D through intermediate category)

### 9. Extended Categorical Modules (`categorical/`)

12 modules providing the mathematical vocabulary:

| Module | What It Models |
|--------|---------------|
| `markov.py` | Stochastic kernels, probability morphisms |
| `optics.py` | Lenses, prisms, adapters (bidirectional data access) |
| `deep_learning.py` | Neural nets as Para + Optics |
| `poly.py` | Polynomial functors (Spivak's wiring diagrams) |
| `double_categories.py` | Tight/loose morphisms (2 kinds of arrow) |
| `dagger.py` | Dagger categories, compact closed (quantum) |
| `rewriting.py` | Term rewriting systems |
| `traced.py` | Traced monoidal categories (feedback loops) |
| `string_diagrams.py` | Diagrammatic reasoning |
| `linear.py` | Linear categories (linear algebra as morphisms) |
| `para.py` | Parametric families (learnable morphisms) |
| `kan_learning.py` | Kan extensions as learning algorithms |

Plus the original 19 modules: enriched categories, fibrations, Grothendieck
constructions, presheaf toposes, topos logic, operads, prime theory,
2-categories, natural transformations, Kan extensions, streaming Kan,
quantales, cellular automata, Dempster-Shafer, boundary profunctors,
activity systems, crypto categories.

### 10. TheoremKG -- AIMO Competition Solver (`aimo/theorem_kg.py`)

A full-corpus theorem knowledge graph using 7 retrieval stages:

1. **Keyword search** -> seed theorems
2. **Spectral clustering** (GraphLaplacian) -> cluster neighbors
3. **Composition paths** -> theorem chains
4. **Yoneda similarity** -> structurally analogous theorems
5. **Kan prediction** -> missing theorems via colimit
6. **Oracle strategies** -> 13+ categorical inference methods
7. **Ricci curvature** -> bridge vs hub importance

The `EnhancedTheoremKG` subclass adds COG verification of chains, OPTIMUS
discovery of intermediate theorems, and Cosmos fibration-based retrieval.

### 11. Lean 4 Proofs (`lean_proofs/`)

698+ theorems formalized in Lean 4 (v4.28.0, Mathlib v4.28.0). Includes
Ruliad conjectures, topology theorems, and gap-filling proofs.

---

## The Integrated Pipeline

### MathDiscoveryBridge (`bridges/math_discovery_bridge.py`)

This is the master wiring module. One call runs everything:

```python
from bridges.math_discovery_bridge import MathDiscoveryBridge
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter

# 1. Load the math kernel with real data
kernel = MathKernel()
kernel.load_source("leandojo", LeanDojoAdapter("data_sources/leandojo/leandojo_benchmark_4"))

# 2. Create bridge (wires to COG + OPTIMUS + Cosmos + DualEngine)
bridge = MathDiscoveryBridge(kernel)

# 3. Run the full pipeline
result = bridge.full_discovery()

# What you get:
result.convergence              # ConvergenceReport from 3 sources
result.cog_verified             # Signals that passed COG verification
result.cog_rejected             # Signals COG rejected (false positives)
result.optimus_intermediates    # New objects OPTIMUS discovered
result.optimus_gaps             # Structural holes (candidate conjectures)
result.cosmos_fibrations        # Higher-dimensional structure
result.cosmos_yoneda            # Yoneda embedding faithfulness
result.conjecture_verdicts      # DualEngine: AGREE / HOLLOW / ORPHAN / REJECT
result.cross_source_edges       # Cross-source links built

# The money shot:
hollows = [v for v in result.conjecture_verdicts if v["delta_type"] == "HOLLOW"]
# These are NOVEL DISCOVERIES -- structurally real but logically unproven
```

### IntegratedDiscoveryPipeline (`discovery/pipeline.py`)

For running raw discovery script output through verification:

```python
from discovery.pipeline import IntegratedDiscoveryPipeline

pipeline = IntegratedDiscoveryPipeline(category=kernel.leandojo)

# Feed in holes from the 59K pipeline
result = pipeline.run(
    holes=holes_from_filter_59k,
    conjectures=conjectures_from_treasure_hunt,
    cluster_objects=cluster_from_hole_navigation,
)

# result.holes_cog_verified -- how many holes survived COG
# result.conjectures_hollow -- how many conjectures are novel
# result.verdicts -- full DualEngine classification for each
```

---

## Using This System With an LLM

The system is designed to work with an LLM (Claude, etc.) as the reasoning
layer. The LLM doesn't do the math -- the categorical infrastructure does.
The LLM's role is:

1. **Interpret** -- Read a HOLLOW verdict and explain what the conjecture means
2. **Strategize** -- Given OPTIMUS gaps, decide which to investigate first
3. **Formalize** -- Take a conjecture and write the Lean 4 proof
4. **Navigate** -- Use TheoremKG to find relevant theorems for a problem

### Example: LLM-Assisted Discovery Session

```
Human: Run the discovery pipeline on the topology section.
       Show me HOLLOW results near Millennium Prize problems.

LLM:   [Calls bridge.full_discovery()]
       Found 3 HOLLOW conjectures near Yang-Mills anchor:
       1. SubmoduleClosure: CAT sees a closure property linking
          TopologicalVectorSpace -> BanachSpace that ZFC can't prove.
          Proximity to Yang-Mills: 0.73
       2. OpenSubgroupBridges: Topological feature in LeanDojo AND MMLKG
          (convergent). COG Tier 2 verified. DualEngine: HOLLOW.
       3. LinearPMapClosable: OPTIMUS found intermediate factorization
          through DenseSubmodule. Not in any source. HOLLOW.

Human: Formalize conjecture #3 (LinearPMapClosable) in Lean 4.

LLM:   [Uses TheoremKG to find related theorems]
       [Reads existing conjectures/LinearPMap_IsClosable.lean]
       [Writes Lean 4 proof using mathlib API]
       Here is the formalization:
       ```lean
       theorem linear_pmap_closable_via_dense_submodule
         {E F : Type*} [NormedAddCommGroup E] [NormedAddCommGroup F]
         [NormedSpace R E] [NormedSpace R F]
         (f : E ->L[R] F) (S : Submodule R E) [S.IsDense] :
         f.toPMap S |>.IsClosable := by
         ...
       ```

Human: Verify this through the DualEngine.

LLM:   [Calls bridge.verify_conjecture(...)]
       DualEngine verdict: AGREE
       ZFC confirms (confidence 0.87): logical chain through
       NormedSpace.IsDense -> Submodule.closure -> IsClosable
       CAT confirms (confidence 0.91): structural path exists in LeanDojo
```

---

## What This Means for Emily Riehl's Actual Work

Based on her current research priorities (2025-2026), this system addresses
five specific needs she has articulated:

### 1. The infinity-Cosmos Project in Lean

Riehl co-leads the infinity-cosmos project (with Carneiro and Verity) to
formalize (infinity,1)-category theory in Lean's mathlib. Their approach:
use the infinity-cosmos axiom as the starting point, work in the homotopy
2-category, and defer proving quasi-categories form an infinity-cosmos
(posted as a community "bounty").

**What KOMPOSOS provides:** The `InfinityCosmos` class (`core/cosmos.py`)
is a computational implementation of exactly this axiom. It builds h2K,
detects isofibrations, computes cartesian fibrations, Yoneda embedding,
and pointwise Kan extensions. When loaded with LeanDojo's 180K mathlib
theorems, it can identify where the homotopy 2-category structure is
incomplete -- directly feeding the infinity-cosmos project's formalization
roadmap.

The `categorical/fibrations.py`, `categorical/grothendieck.py`, and
`categorical/presheaf_topos.py` modules implement the exact categorical
constructions their project needs formalized.

### 2. "Formalizing Invisible Mathematics"

Her 2025 seminar and ICM 2026 invited talk ("Synthetic perspectives on
spaces and categories", arXiv:2510.15795) focus on making explicit the
implicit higher-dimensional coherences that "live between the lines" of
classical proofs. She calls this "invisible mathematics" -- the coherence
data that working mathematicians use intuitively but never write down.

**What KOMPOSOS provides:** This is precisely what the Gray coherence
layer does. The `core/gray_coherence.py` module checks for 3-cell
coherence -- modifications between 2-cells. When a 3-cell (Gamma: alpha => beta)
does NOT exist, that's a coherence gap. The system finds these gaps
automatically by scanning the categorical structure. These are literally
the "invisible" coherences that Riehl wants to make explicit.

The MathDiscoveryBridge runs this analysis on the LeanDojo corpus:
structural gaps where mathlib's formalization lacks the coherence witnesses
that should exist. Each gap is an instance of "invisible mathematics"
that needs formalizing.

### 3. Colimits in Cat and Mathlib Infrastructure Gaps

Riehl and Carneiro's recent paper (arXiv:2503.20704) formalized colimits
in Cat within mathlib, but identified remaining gaps:
- Limited support for general colimit constructions in specialized contexts
- Need for developed theory of reflective subcategories
- Gaps in simplicial category theory machinery
- Limited tools for free constructions on categorical structures

**What KOMPOSOS provides:** The OPTIMUS engine's `find_structural_gaps()`
method, when pointed at the category theory section of mathlib via LeanDojo,
identifies exactly these missing constructions. The `categorical/kan_extensions.py`
module computes Left and Right Kan extensions (colimits are left Kan extensions
along the unique functor to the terminal category). Running OPTIMUS on
the colimit-related subgraph of mathlib would find the specific missing
factorizations their project needs next.

### 4. Model Independence

Her foundational insight (arXiv:1608.05314): theorems proven in the
infinity-cosmos framework work for ALL models of (infinity,1)-categories
(quasi-categories, complete Segal spaces, Segal categories, etc.).
You prove it once, it works everywhere.

**What KOMPOSOS provides:** The system embodies this principle. The
`InfinityCosmos` class doesn't commit to a specific model -- it works
with the abstract categorical structure. When it finds a HOLLOW
conjecture (structurally real, logically novel), that conjecture is
model-independent by construction. This means discoveries made by
KOMPOSOS apply to every model simultaneously.

### 5. Mathlib Strategic Advisory Board

Riehl serves on mathlib's Strategic Advisory Board. She helps decide
where formalization effort should be directed. Showing her a prioritized
list of structural gaps in mathlib -- filtered by COG verification,
ranked by OPTIMUS structural importance, classified by DualEngine as
AGREE/HOLLOW -- gives her directly actionable data for steering the
project.

**What KOMPOSOS provides:** The 59K holes pipeline, filtered through
COG and classified by DualEngine, produces exactly this: a prioritized
gap manifesto for mathlib. The 21 keystone gaps (`gap_data/keystone_gaps/`)
are the highest-priority ones, already formalized in Lean 4.

### 6. The Rzk Proof Assistant Connection

Riehl helped develop the Rzk proof assistant (rzk-lang.github.io) for
simplicial HoTT, which formalizes synthetic infinity-category theory.
The sHoTT library includes the first formalization of the infinity-categorical
Yoneda lemma.

**What KOMPOSOS provides:** The `core/formal_yoneda.py` module implements
a computational Yoneda distance metric with formal proofs (d=0 iff isomorphic).
The `hott/` modules provide HoTT identity types and path induction. The
`cubical/` modules handle cubical interpolation. These are computational
counterparts to what Rzk proves synthetically -- and running KOMPOSOS
on Rzk's sHoTT library (via adapter) could identify where the synthetic
formalization has structural gaps that the computational approach reveals.

---

## Concrete Discovery Results Already Obtained

| Discovery | Source | DualEngine | Status |
|-----------|--------|------------|--------|
| SubmoduleClosure theorem | LeanDojo topology | HOLLOW | Formalized in Lean 4 |
| OpenSubgroup bridges | LeanDojo + MMLKG convergent | HOLLOW | Formalized in Lean 4 |
| LinearPMap closability | OPTIMUS factorization | HOLLOW | Formalized in Lean 4 |
| 3 new topology theorems | Treasure hunt | HOLLOW | `ThreeNewTopologyTheorems.lean` |
| 5 gauge theory conjectures | Deep dive analysis | HOLLOW | `conjecture_1-5.lean` |
| 21 keystone gaps | Priority filter | Various | `gap_data/keystone_gaps/` |
| 59K total holes | Full pipeline | Various | `gap_data/59k_gaps/` |

---

## Quick Start

```bash
# Set PYTHONPATH
cd KOMPOSOS-IV
export PYTHONPATH=$(pwd)

# Verify core tests pass
pytest tests/ -q --ignore=tests/test_mythos_adversarial.py \n                 --ignore=tests/test_mythos_adversarial_lightweight.py \n                 --ignore=tests/test_mythos_comprehensive.py
# 190 passed

# Test the wiring
python -c "
from bridges.math_discovery_bridge import MathDiscoveryBridge
from domains.mathematics.kernel import MathKernel
kernel = MathKernel(db_dir=":memory:")
bridge = MathDiscoveryBridge(kernel)
result = bridge.full_discovery()
print(result.summary())
"

# Test Oracle strategy
python -c "
from oracle.math_discovery_strategy import MathDiscoveryStrategy
from core.category import Category
strategy = MathDiscoveryStrategy(Category(db_path=":memory:"))
print(strategy.name)  # math_discovery
"

# Test EnhancedTheoremKG
python -c "
from aimo.theorem_kg import EnhancedTheoremKG
kg = EnhancedTheoremKG()
print(type(kg).__name__)  # EnhancedTheoremKG
"
```

---

## File Map

### Wiring (new)
| File | What It Wires |
|------|---------------|
| `bridges/math_discovery_bridge.py` | MathKernel -> COG + OPTIMUS + Cosmos + DualEngine |
| `oracle/math_discovery_strategy.py` | MathKernel -> Oracle strategy #13 |
| `discovery/pipeline.py` | Discovery scripts -> COG + OPTIMUS + DualEngine |
| `aimo/theorem_kg.py` (EnhancedTheoremKG) | TheoremKG -> COG + OPTIMUS + Cosmos |

### Core infrastructure
| File | What It Is |
|------|------------|
| `core/category.py` | The Category runtime (enriched, persistent) |
| `core/cosmos.py` | InfinityCosmos (Riehl-Verity) |
| `core/optimus.py` | OPTIMUS categorical gradient descent |
| `core/formal_yoneda.py` | Formal Yoneda distance proof |
| `core/higher_order_optimus.py` | Multi-level factorization |
| `cog/engine.py` | COG 5-tier verification |
| `zfc/bridge.py` | ZFC+CAT DualEngine |
| `oracle/__init__.py` | 13-strategy Categorical Oracle |

### Math data
| File | What It Contains |
|------|------------------|
| `domains/mathematics/kernel.py` | MathKernel (3-source convergence) |
| `domains/mathematics/leandojo_adapter.py` | LeanDojo 180K theorem loader |
| `aimo/theorem_kg.py` | TheoremKG (7-stage retrieval) |
| `conjectures/*.lean` | 15 Lean 4 formalized conjectures |
| `gap_data/` | 59K holes + 21 keystone gaps |
| `lean_proofs/` | 698+ Lean 4 theorems |
| `data_sources/` | 6.9 GB raw data (not in git) |

### 31 categorical modules
| Directory | Count | Coverage |
|-----------|-------|----------|
| `categorical/` | 31 | Enriched, fibrations, Grothendieck, presheaf, topos, operads, 2-cat, Kan, streaming Kan, quantales, Markov, optics, Para, poly, double, dagger, traced, string diagrams, linear, rewriting, kan_learning, deep_learning, prime, activity, boundary, cellular, crypto, Dempster-Shafer |

Author: James Ray Hawkins
License: Apache 2.0 / Commercial dual license
