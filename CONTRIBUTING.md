# Contributing to KOMPOSOS-III-LAMBDA-max-3D-chem

**Compositional reasoning engine for chemistry and materials science.**

This project is open source (Apache 2.0) and welcomes contributors — materials scientists, chemists, developers, and curious humans of all backgrounds.

---

## Quick Links

- **Project Overview:** [README.md](README.md)
- **Commercialization Plan:** [COMMERCIALIZATION_PLAN.md](COMMERCIALIZATION_PLAN.md)
- **Target Customers:** [TARGET_CUSTOMERS.md](TARGET_CUSTOMERS.md)
- **Live Demo:** [chem.komposos.ai](https://chem.komposos.ai) (coming soon)
- **License:** Apache 2.0 (free for all use)

---

## Where Help Is Needed

### High Priority

| Area | What's Needed | Skills Required |
|------|---------------|-----------------|
| **Experimental Validation** | Test predictions in lab (Co-IP, DFT, etc.) | Lab skills, DFT, materials characterization |
| **Data Curation** | Add new materials with property data | Materials science, literature review |
| **PFAS Compliance** | Expand PFAS database, add regulations | Regulatory knowledge, chemistry |
| **Documentation** | User guides, tutorials, API docs | Technical writing |
| **Testing** | More unit tests, integration tests | Python, pytest |
| **Frontend** | Improve Streamlit/FastAPI UI | Streamlit, React, JavaScript |

### Medium Priority

| Area | What's Needed | Skills Required |
|------|---------------|-----------------|
| **New Domain Bridges** | Add bridges (polymer→battery, etc.) | Category theory, materials science |
| **ML Integration** | Better ML models for property prediction | PyTorch, scikit-learn, GNNs |
| **Performance** | Optimize for large-scale screening | Python optimization, multiprocessing |
| **DFT Integration** | Auto-validate predictions with DFT | DFT (VASP, Quantum ESPRESSO, etc.) |
| **Synthesis Planning** | Expand synthesis route database | Chemistry, literature review |

### Low Priority (But Welcome)

| Area | What's Needed | Skills Required |
|------|---------------|-----------------|
| **Examples** | More example notebooks | Any level |
| **Bug Reports** | File issues for bugs | GitHub issues |
| **Feature Requests** | Suggest new features | GitHub issues |
| **Translations** | Translate docs to other languages | Any language |
| **Outreach** | Share on social media, write blog posts | Communication |

---

## How to Contribute

### 1. **Fork and Pull Request**

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/KOMPOSOS-III-LAMBDA-max-3D-chem
cd KOMPOSOS-III-LAMBDA-max-3D-chem
git checkout -b your-feature-branch

# Make your changes
# Add tests for new code
# Update docs if needed

git commit -m "Add feature X (resolves #123)"
git push origin your-feature-branch
# Open Pull Request on GitHub
```

### 2. **Report a Bug**

Use [GitHub Issues](https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem/issues):

**Good bug report includes:**
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version, OS, dependencies
- Error messages (full traceback)

### 3. **Request a Feature**

Use [GitHub Issues](https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem/issues):

**Good feature request includes:**
- What problem you're trying to solve
- Why current features don't solve it
- How you'd use the new feature
- Any relevant examples/mockups

### 4. **Add Material Data**

New materials are welcome! Follow the pattern in `battery_bridge/material_properties.py`:

```python
# battery_bridge/material_properties.py

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Material:
    name: str
    formula: str
    domain: str  # "battery", "polymer", "metal", etc.
    properties: Dict[str, float]
    citations: List[str]

# Add your material:
NMC811 = Material(
    name="NMC811",
    formula="LiNi0.8Mn0.1Co0.1O2",
    domain="battery",
    properties={
        "voltage_max": 4.3,  # V vs. Li/Li+
        "capacity_theoretical": 200,  # mAh/g
        "thermal_stability_onset": 200,  # °C
        "ionic_conductivity": 1e-3,  # S/cm
    },
    citations=[
        "DOI:10.1038/s41560-019-0388-3",
        "DOI:10.1021/acs.chemmater.8b01111",
    ],
)
```

Add tests in `tests/battery_bridge/test_materials.py`.

### 5. **Add PFAS Substance**

PFAS compliance is critical for EU October 2026 ban. Follow the pattern in `pfas_bridge/pfas_substances.py`:

```python
# pfas_bridge/pfas_substances.py

from dataclasses import dataclass
from typing import List

@dataclass
class PFASSubstance:
    name: str
    cas_number: str
    category: str  # "PFCA", "PFSA", "fluoropolymer", etc.
    regulations: List[str]  # EU, US, Stockholm Convention
    urgency: str  # "critical", "high", "moderate", "low", "none"
    replacements: List[str]  # Suggested alternatives

# Add your substance:
PFHxA = PFASSubstance(
    name="Perfluorohexanoic acid",
    cas_number="307-24-4",
    category="PFCA",
    regulations=[
        "EU REACH Annex XVII (ban Oct 2026)",
        "US EPA PFAS Strategic Roadmap",
    ],
    urgency="critical",
    replacements=["C6-free DWR", "hydrocarbon-based treatments"],
)
```

---

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- SQLite (comes with Python)

### Install for Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/KOMPOSOS-III-LAMBDA-max-3D-chem
cd KOMPOSOS-III-LAMBDA-max-3D-chem

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install dev dependencies
pip install pytest pytest-asyncio httpx mypy
```

### Run Tests

```bash
# Run all tests (1,423 tests)
python -m pytest tests/ -v

# Run specific domain tests
python -m pytest battery_bridge/tests/ -v
python -m pytest pfas_bridge/tests/ -v

# Run with coverage
python -m pytest tests/ --cov=battery_bridge --cov-report=html
```

### Start the API

```bash
# Development mode
python -m api.main

# Or with uvicorn directly
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for Swagger UI.

### Start the Streamlit App

```bash
streamlit run streamlit_app/app.py
```

Visit `http://localhost:8501` for the web UI.

---

## Code Style

### Python Style

- **PEP 8** for general style
- **Type hints** on all function signatures
- **Docstrings** for all public functions/classes (Google style)
- **Max line length:** 100 characters

Example:

```python
from typing import Dict, List, Tuple
from battery_bridge.material_properties import Material

def check_compatibility(
    material_a: Material,
    material_b: Material,
    scorers: List[str] = None,
) -> Dict[str, float]:
    """
    Check compatibility between two materials.
    
    Args:
        material_a: First material
        material_b: Second material
        scorers: List of scorers to use (default: all 5)
        
    Returns:
        Dictionary of scorer names to compatibility scores [0, 1]
        
    Raises:
        ValueError: If materials are from incompatible domains
    """
    # Implementation here
    pass
```

### Testing Style

- **pytest** for all tests
- **Async tests** with `@pytest.mark.asyncio`
- **Descriptive test names:** `test_should_detect_thermal_mismatch`
- **Arrange-Act-Assert** pattern

Example:

```python
import pytest
from battery_bridge.interaction_scoring import ThermalScorer

def test_should_score_thermal_mismatch_low():
    """Materials with large CTE mismatch should score low."""
    # Arrange
    material_a = Material(
        name="TestA",
        formula="A",
        domain="battery",
        properties={"cte": 10e-6},  # 1/K
        citations=[],
    )
    material_b = Material(
        name="TestB",
        formula="B",
        domain="battery",
        properties={"cte": 50e-6},  # 1/K
        citations=[],
    )
    scorer = ThermalScorer()
    
    # Act
    score = scorer.score(material_a, material_b)
    
    # Assert
    assert score < 0.5  # Large mismatch = low score
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new PFAS substance database
fix: correct thermal compatibility calculation
docs: add tutorial for battery compatibility
test: add integration tests for PFAS compliance
refactor: extract synthesis planning into separate module
```

---

## Architecture Overview

```
Material Data (103K+ from Materials Project + 169 curated)
       │
  Domain Bridges (6 domains)
   ╱    │    │    │    │    ╲
Battery Polymer Metal Ceramic Semiconductor Glass
   ╲    │    │    │    │    ╱
    Cross-Bridge Functor (multi-domain composition)
       │
  5 Scorers per Domain
   ╱    │    │    │    ╲
Thermal Mechanical Chemical Structural Transport
       │
  Composite Score [0, 1]
       │
  ZFC Verification
       │
  AGREE / ORPHAN / HOLLOW / REJECT
```

### Key Modules

| Module | Purpose | Files | Tests |
|--------|---------|-------|-------|
| `battery_bridge/` | Battery materials | 8 | 58 |
| `polymer_bridge/` | Polymers | 8 | 98 |
| `metal_bridge/` | Metals | 8 | 101 |
| `ceramic_bridge/` | Ceramics | 8 | 102 |
| `semiconductor_bridge/` | Semiconductors | 8 | 113 |
| `glass_bridge/` | Glass | 8 | 179 |
| `cross_bridge/` | Multi-domain | 6 | 103 |
| `molecular_bridge/` | Molecules (37) | 8 | 90 |
| `pfas_bridge/` | PFAS compliance (35) | 8 | 81 |
| `composition_engine/` | Inverse design | 10 | 252 |
| `synthesis_planner/` | Synthesis routes (24) | 8 | 94 |
| `api/` | REST API (17 endpoints) | 4 | 45 |
| `tests/` | Test suite | 23 files | 1,423 total |

---

## Good First Issues

Look for issues tagged [`good first issue`](https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22):

- Add new material with property data
- Add new PFAS substance
- Documentation improvements
- Adding tests for existing code
- Minor bug fixes
- Frontend polish (Streamlit UI improvements)

---

## For Experimentalists

**Want to validate predictions in the lab?**

This project desperately needs experimental validation! If you have lab access:

1. **Pick a prediction** from the repo (e.g., NMC811 + LLZO compatibility)
2. **Test it** using your standard methods (EIS, XRD, SEM, etc.)
3. **Report results** in `experimental_validation/` folder:

```markdown
# experimental_validation/nmc811_llzo_validation.md

## Prediction
KOMPOSOS predicted: compatible (score 0.72)
- Thermal match: 0.85
- Voltage match: 0.90
- Chemical: 0.55 (Li exchange at interface — monitor)

## Experimental Method
- Synthesis: [your method]
- Characterization: [XRD, SEM, EIS, etc.]
- Conditions: [temperature, pressure, atmosphere]

## Results
- [Your results with data]

## Conclusion
✅ CONFIRMED / ❌ REFUTED / ⚠️ PARTIALLY CONFIRMED

## Notes
[Any additional observations]
```

**Funding available:** If you need materials/equipment funding, discuss in an issue. Grant opportunities can support this.

---

## For Computational Chemists

**Want to run DFT validation?**

DFT validation is highly valued! If you have compute access:

1. **Pick a prediction** from the repo
2. **Run DFT** (VASP, Quantum ESPRESSO, Gaussian, etc.)
3. **Report results** in `dft_validation/` folder:

```markdown
# dft_validation/nmc811_llzo_interface.md

## Prediction
KOMPOSOS predicted: compatible (score 0.72)

## DFT Method
- Code: [VASP 6.4, etc.]
- Functional: [PBE, HSE06, etc.]
- Basis set: [PAW, etc.]
- k-points: [grid]
- Convergence: [criteria]

## Results
- Formation energy: [value]
- Band structure: [metallic/semiconducting]
- Interface stability: [stable/unstable]

## Conclusion
✅ CONFIRMED / ❌ REFUTED

## Input Files
[Link to uploaded input files]
```

---

## Getting Help

**Stuck?** Reach out:

- **GitHub Issues:** Tag with `question`
- **Email:** jhawk314@gmail.com
- **Twitter:** [@yourhandle] (add if you want)
- **Discord:** [add if you create one]

**Office Hours:** (add if you want to offer live help)

---

## Recognition

Contributors will be acknowledged in:

- `CONTRIBUTORS.md` (list of all contributors)
- Release notes (for significant contributions)
- Papers/presentations (if your work is cited)

**Significant contributions** may also include:
- Co-authorship on papers (especially experimental/DFT validation)
- Speaking opportunities at conferences
- Revenue share (if commercial features you built are monetized)

---

## License

Apache 2.0 — free for commercial and non-commercial use.

**By contributing, you agree to license your contributions under Apache 2.0.**

If you want different terms (e.g., you're contributing on behalf of a company), discuss in an issue before submitting code.

---

## The Spirit of This Project

From the README:

> *"Not a neural network. KOMPOSOS doesn't train on data — it reasons compositionally over knowledge graphs."*

This project values:

✅ **Interpretable reasoning** — Every prediction has an explanation
✅ **Data provenance** — Every property traces to published data
✅ **Accessibility** — No PhD required to contribute
✅ **Openness** — Free for all, including commercial use
✅ **Pragmatism** — Ship working code, not just papers

If that resonates with you, you belong here.

---

## Start Here

New to the project?

1. **Read** [README.md](README.md) (10 min)
2. **Try the demo:** `python showcase/quickstart_demo.py` (2 min)
3. **Browse** architecture in [CLAUDE.md](CLAUDE.md) (if exists)
4. **Pick** a [`good first issue`](https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
5. **Fork** and start coding!

**Experimentalists:** Start with `experimental_validation/README.md`
**Computational chemists:** Start with `dft_validation/README.md`

Welcome aboard.

*tat hastu* — so be it.

---

*Last updated: March 13, 2026*
