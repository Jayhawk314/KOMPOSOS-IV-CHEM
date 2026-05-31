"""
PFAS Replacement Scorer
========================

Scores PFAS-free replacement candidates for specific use cases.
Each replacement has literature-backed performance, processability,
cost, and availability scores.

Replacement data sourced from:
- Bresser et al., Energy Environ. Sci. 2018 (aqueous binders)
- Li et al., J. Electrochem. Soc. 2020 (PVDF alternatives)
- Dams & Heylen, "PFAS restrictions impact on industry", 2023
- OECD, "PFASs and alternatives in coatings, paints and varnishes", 2022
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from oracle.compatibility_service import (
    run_compatibility_workflow,
    CompatibilityWorkflowResult,
)


class UseCase(Enum):
    """Application context for PFAS replacement."""
    BATTERY_BINDER = "battery_binder"
    SEAL_GASKET = "seal_gasket"
    MEMBRANE = "membrane"
    WIRE_INSULATION = "wire_insulation"
    NON_STICK_COATING = "non_stick_coating"
    CHEMICAL_RESISTANT_LINER = "chemical_resistant_liner"
    GENERAL = "general"


@dataclass
class ReplacementCandidate:
    """A PFAS-free alternative for a specific use case."""
    name: str
    use_case: UseCase
    performance_match: float   # 0-1: how well it matches the PFAS performance
    processability: float      # 0-1: ease of switching processes
    cost_factor: float         # 0-1: 1=same cost, 0=10x more expensive
    availability: float        # 0-1: commercial availability
    advantages: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Weighted composite score (performance-heavy)."""
        return (
            0.40 * self.performance_match
            + 0.20 * self.processability
            + 0.20 * self.cost_factor
            + 0.20 * self.availability
        )

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "use_case": self.use_case.value,
            "performance_match": self.performance_match,
            "processability": self.processability,
            "cost_factor": self.cost_factor,
            "availability": self.availability,
            "overall_score": round(self.overall_score, 3),
            "advantages": self.advantages,
            "limitations": self.limitations,
        }


# ---------------------------------------------------------------------------
# Curated replacement map: (PFAS_name, UseCase) -> list of candidates
#
# Sources cited inline.  Scores reflect current (2026) state of art.
# ---------------------------------------------------------------------------

REPLACEMENT_MAP: Dict[Tuple[str, UseCase], List[ReplacementCandidate]] = {}

# ----- PVDF as battery binder -----

REPLACEMENT_MAP[("PVDF", UseCase.BATTERY_BINDER)] = [
    ReplacementCandidate(
        name="CMC+SBR",
        use_case=UseCase.BATTERY_BINDER,
        performance_match=0.75,
        processability=0.85,
        cost_factor=0.90,
        availability=0.95,
        advantages=[
            "Water-based processing (no NMP solvent)",
            "Lower cost and environmental impact",
            "Commercially proven for graphite anodes",
        ],
        limitations=[
            "Lower adhesion on high-voltage cathodes",
            "Moisture sensitivity during processing",
            "Not suitable for NMC811 cathodes without modification",
        ],
    ),
    ReplacementCandidate(
        name="PAN",
        use_case=UseCase.BATTERY_BINDER,
        performance_match=0.60,
        processability=0.50,
        cost_factor=0.80,
        availability=0.70,
        advantages=[
            "Good electrochemical stability",
            "Can form gel electrolyte membranes",
            "High thermal stability",
        ],
        limitations=[
            "Requires organic solvents (DMF, DMSO)",
            "Lower flexibility than PVDF",
            "Less commercially mature as binder",
        ],
    ),
    ReplacementCandidate(
        name="PAA",
        use_case=UseCase.BATTERY_BINDER,
        performance_match=0.70,
        processability=0.80,
        cost_factor=0.85,
        availability=0.80,
        advantages=[
            "Water-soluble (green processing)",
            "Strong adhesion to silicon anodes",
            "Good cycling stability with Si/C composites",
        ],
        limitations=[
            "Brittle without plasticizer",
            "pH-sensitive processing",
        ],
    ),
    ReplacementCandidate(
        name="Alginate",
        use_case=UseCase.BATTERY_BINDER,
        performance_match=0.55,
        processability=0.75,
        cost_factor=0.95,
        availability=0.70,
        advantages=[
            "Bio-derived and sustainable",
            "Water-soluble",
            "Good adhesion via carboxyl groups",
        ],
        limitations=[
            "Lower mechanical strength",
            "Batch-to-batch variability",
            "Limited cycling data for high-voltage cathodes",
        ],
    ),
]

# ----- PVDF as membrane -----

REPLACEMENT_MAP[("PVDF", UseCase.MEMBRANE)] = [
    ReplacementCandidate(
        name="PAN",
        use_case=UseCase.MEMBRANE,
        performance_match=0.70,
        processability=0.65,
        cost_factor=0.80,
        availability=0.75,
        advantages=[
            "Good chemical resistance",
            "Established membrane fabrication",
            "Hydrophilic (no pre-treatment needed)",
        ],
        limitations=[
            "Lower mechanical strength than PVDF",
            "Narrower pH tolerance",
        ],
    ),
    ReplacementCandidate(
        name="Cellulose Acetate",
        use_case=UseCase.MEMBRANE,
        performance_match=0.55,
        processability=0.70,
        cost_factor=0.90,
        availability=0.85,
        advantages=[
            "Bio-derived",
            "Low fouling propensity",
            "Low cost",
        ],
        limitations=[
            "Poor chlorine resistance",
            "Narrow pH range (4-8)",
            "Biodegradable (shorter lifetime)",
        ],
    ),
    ReplacementCandidate(
        name="PES",
        use_case=UseCase.MEMBRANE,
        performance_match=0.75,
        processability=0.70,
        cost_factor=0.70,
        availability=0.80,
        advantages=[
            "Excellent thermal stability",
            "Wide pH tolerance",
            "Good mechanical properties",
        ],
        limitations=[
            "Hydrophobic (needs surface modification)",
            "Higher cost than PVDF",
        ],
    ),
]

# ----- PTFE as seal/gasket -----

REPLACEMENT_MAP[("PTFE", UseCase.SEAL_GASKET)] = [
    ReplacementCandidate(
        name="EPDM",
        use_case=UseCase.SEAL_GASKET,
        performance_match=0.65,
        processability=0.80,
        cost_factor=0.85,
        availability=0.90,
        advantages=[
            "Excellent weather/ozone resistance",
            "Good temperature range (-50 to 150C)",
            "Low cost",
        ],
        limitations=[
            "Poor oil/fuel resistance",
            "Not suitable for hydrocarbon environments",
            "Lower max temperature than PTFE",
        ],
    ),
    ReplacementCandidate(
        name="PDMS",
        use_case=UseCase.SEAL_GASKET,
        performance_match=0.60,
        processability=0.75,
        cost_factor=0.80,
        availability=0.90,
        advantages=[
            "Wide temperature range (-60 to 230C)",
            "Food-grade options available",
            "Biocompatible",
        ],
        limitations=[
            "Low mechanical strength",
            "Poor abrasion resistance",
            "Swells in hydrocarbons",
        ],
    ),
    ReplacementCandidate(
        name="NBR",
        use_case=UseCase.SEAL_GASKET,
        performance_match=0.55,
        processability=0.80,
        cost_factor=0.90,
        availability=0.95,
        advantages=[
            "Excellent oil/fuel resistance",
            "Low cost",
            "Widely available",
        ],
        limitations=[
            "Poor ozone/weather resistance",
            "Limited temperature range",
            "Not suitable for polar solvents",
        ],
    ),
    ReplacementCandidate(
        name="PEEK",
        use_case=UseCase.SEAL_GASKET,
        performance_match=0.80,
        processability=0.40,
        cost_factor=0.30,
        availability=0.70,
        advantages=[
            "Exceptional chemical resistance",
            "High temperature (up to 260C continuous)",
            "Excellent mechanical properties",
        ],
        limitations=[
            "Very expensive",
            "Difficult to process (Tm=343C)",
            "Limited elasticity",
        ],
    ),
]

# ----- FEP as wire insulation -----

REPLACEMENT_MAP[("FEP", UseCase.WIRE_INSULATION)] = [
    ReplacementCandidate(
        name="PEEK",
        use_case=UseCase.WIRE_INSULATION,
        performance_match=0.70,
        processability=0.50,
        cost_factor=0.30,
        availability=0.65,
        advantages=[
            "High temperature rating (260C continuous)",
            "Excellent flame resistance",
            "Good dielectric properties",
        ],
        limitations=[
            "Very expensive",
            "Harder to extrude",
            "Less flexible",
        ],
    ),
    ReplacementCandidate(
        name="Silicone",
        use_case=UseCase.WIRE_INSULATION,
        performance_match=0.60,
        processability=0.75,
        cost_factor=0.70,
        availability=0.85,
        advantages=[
            "Wide temperature range (-60 to 200C)",
            "Very flexible",
            "Good dielectric strength",
        ],
        limitations=[
            "Lower abrasion resistance",
            "Larger diameter needed for same voltage rating",
            "Tear-prone",
        ],
    ),
    ReplacementCandidate(
        name="XLPE",
        use_case=UseCase.WIRE_INSULATION,
        performance_match=0.55,
        processability=0.85,
        cost_factor=0.90,
        availability=0.95,
        advantages=[
            "Low cost",
            "Established manufacturing",
            "Good moisture resistance",
        ],
        limitations=[
            "Lower max temperature (90C)",
            "Not suitable for high-temp environments",
        ],
    ),
]

# ----- PTFE as non-stick coating -----

REPLACEMENT_MAP[("PTFE", UseCase.NON_STICK_COATING)] = [
    ReplacementCandidate(
        name="Ceramic coating",
        use_case=UseCase.NON_STICK_COATING,
        performance_match=0.70,
        processability=0.65,
        cost_factor=0.75,
        availability=0.80,
        advantages=[
            "PFAS-free",
            "Higher temperature tolerance",
            "Scratch-resistant",
        ],
        limitations=[
            "Less non-stick than PTFE",
            "Durability degrades faster",
            "Requires careful thermal management",
        ],
    ),
    ReplacementCandidate(
        name="Cast iron (seasoned)",
        use_case=UseCase.NON_STICK_COATING,
        performance_match=0.45,
        processability=0.90,
        cost_factor=0.95,
        availability=1.00,
        advantages=[
            "Zero PFAS",
            "Extremely durable",
            "Improves with use",
        ],
        limitations=[
            "Heavy",
            "Requires seasoning maintenance",
            "Reactive with acidic foods",
        ],
    ),
]

# ----- PTFE as chemical-resistant liner -----

REPLACEMENT_MAP[("PTFE", UseCase.CHEMICAL_RESISTANT_LINER)] = [
    ReplacementCandidate(
        name="PP (polypropylene)",
        use_case=UseCase.CHEMICAL_RESISTANT_LINER,
        performance_match=0.55,
        processability=0.85,
        cost_factor=0.95,
        availability=0.95,
        advantages=[
            "Low cost",
            "Good acid/base resistance",
            "Easy to fabricate",
        ],
        limitations=[
            "Poor organic solvent resistance",
            "Lower max temperature (120C)",
            "Oxidizer sensitivity",
        ],
    ),
    ReplacementCandidate(
        name="PEEK",
        use_case=UseCase.CHEMICAL_RESISTANT_LINER,
        performance_match=0.80,
        processability=0.40,
        cost_factor=0.25,
        availability=0.65,
        advantages=[
            "Broad chemical resistance",
            "High temperature",
            "Excellent mechanical properties",
        ],
        limitations=[
            "Very expensive (5-10x PTFE)",
            "Difficult to fabricate as liner",
        ],
    ),
    ReplacementCandidate(
        name="HDPE",
        use_case=UseCase.CHEMICAL_RESISTANT_LINER,
        performance_match=0.50,
        processability=0.90,
        cost_factor=0.95,
        availability=1.00,
        advantages=[
            "Very low cost",
            "Good acid/base resistance",
            "Easy to weld/fabricate",
        ],
        limitations=[
            "Poor organic solvent resistance",
            "Low max temperature (80C)",
            "UV degradation",
        ],
    ),
]

# ----- Nafion as membrane -----

REPLACEMENT_MAP[("Nafion", UseCase.MEMBRANE)] = [
    ReplacementCandidate(
        name="SPEEK",
        use_case=UseCase.MEMBRANE,
        performance_match=0.65,
        processability=0.60,
        cost_factor=0.70,
        availability=0.55,
        advantages=[
            "PFAS-free",
            "Good proton conductivity (tunable with sulfonation degree)",
            "Lower methanol permeability",
        ],
        limitations=[
            "Lower conductivity than Nafion",
            "Mechanical stability decreases at high sulfonation",
            "Less commercially mature",
        ],
    ),
    ReplacementCandidate(
        name="PBI",
        use_case=UseCase.MEMBRANE,
        performance_match=0.60,
        processability=0.50,
        cost_factor=0.60,
        availability=0.50,
        advantages=[
            "Excellent high-temperature operation (120-200C)",
            "No humidification needed with phosphoric acid doping",
            "PFAS-free",
        ],
        limitations=[
            "Requires acid doping",
            "Lower conductivity at low temperature",
            "Acid leaching over time",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

def find_replacements(
    pfas_name: str,
    use_case: UseCase = UseCase.GENERAL,
) -> List[ReplacementCandidate]:
    """
    Find PFAS-free replacement candidates for a given PFAS substance
    and use case.

    Returns candidates sorted by overall_score (best first).
    Falls back to all use cases for that substance if specific
    use case has no entries.
    """
    # Direct lookup
    key = (pfas_name, use_case)
    if key in REPLACEMENT_MAP:
        candidates = list(REPLACEMENT_MAP[key])
        candidates.sort(key=lambda c: c.overall_score, reverse=True)
        return candidates

    # Try GENERAL use case
    general_key = (pfas_name, UseCase.GENERAL)
    if general_key in REPLACEMENT_MAP:
        candidates = list(REPLACEMENT_MAP[general_key])
        candidates.sort(key=lambda c: c.overall_score, reverse=True)
        return candidates

    # Collect all use cases for this substance
    all_candidates = []
    for (name, _), cands in REPLACEMENT_MAP.items():
        if name == pfas_name:
            all_candidates.extend(cands)

    if all_candidates:
        # Deduplicate by name, keeping highest-scoring version
        seen = {}
        for c in all_candidates:
            if c.name not in seen or c.overall_score > seen[c.name].overall_score:
                seen[c.name] = c
        result = list(seen.values())
        result.sort(key=lambda c: c.overall_score, reverse=True)
        return result

    return []


def find_compatible_replacements(
    pfas_name: str,
    adjoining_material: str,
    use_case: UseCase = UseCase.GENERAL,
    domain: Optional[str] = None,
) -> List[Tuple[ReplacementCandidate, Optional[CompatibilityWorkflowResult]]]:
    """
    Find PFAS-free replacements and score their compatibility with an
    adjoining material (e.g., electrolyte for a binder).

    Returns list of (ReplacementCandidate, CompatibilityWorkflowResult)
    sorted by a combined (overall_score + compatibility_score) metric.
    """
    candidates = find_replacements(pfas_name, use_case)
    results = []

    for candidate in candidates:
        comp_res = None
        # Normalize name for compatibility engine if needed
        # e.g. "CMC+SBR" -> "CMC"
        bridge_name = candidate.name.split("+")[0] if "+" in candidate.name else candidate.name
        
        try:
            comp_res = run_compatibility_workflow(
                bridge_name,
                adjoining_material,
                domain=domain
            )
        except Exception:
            # Material might not be in the compatibility registry
            pass
        
        results.append((candidate, comp_res))

    # Rank by a composite of replacement quality and compatibility
    def _rank_key(item):
        cand, res = item
        comp_score = res.scores.get("total", 0.0) if res else 0.5
        # Weighted: 60% replacement quality, 40% compatibility
        return 0.6 * cand.overall_score + 0.4 * comp_score

    results.sort(key=_rank_key, reverse=True)
    return results


def find_replacements_for_cell(
    pfas_name: str,
    adjoining_materials: List[str],
    use_case: UseCase = UseCase.GENERAL,
    domain: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Score PFAS-free replacements against EVERY adjoining material in a cell/stack.

    A replacement is only as good for *your cell* as its weakest interface, so we
    report the per-interface calibrated compatibility probability AND the
    bottleneck (the worst one). This turns "not PFAS" into
    "PFAS-clean AND compatible with your cell".

    Returns a list of dicts (one per replacement), each:
        {
          "candidate": ReplacementCandidate,
          "interfaces": {adjoining_material: {score, calibrated, viable, domain, evaluated}},
          "bottleneck_material": str | None,   # weakest interface
          "bottleneck_calibrated": float | None,
          "bottleneck_viable": bool | None,
          "n_evaluated": int,                  # interfaces the engine could score
          "combined_rank": float,              # 0.6*quality + 0.4*bottleneck
        }
    sorted by combined_rank (best first).
    """
    adjoining = [m.strip() for m in adjoining_materials if m and m.strip()]
    candidates = find_replacements(pfas_name, use_case)
    out: List[Dict[str, Any]] = []

    for candidate in candidates:
        bridge_name = candidate.name.split("+")[0] if "+" in candidate.name else candidate.name
        interfaces: Dict[str, Dict[str, Any]] = {}

        for mat in adjoining:
            entry: Dict[str, Any] = {
                "score": None, "calibrated": None, "viable": None,
                "domain": None, "evaluated": False,
            }
            try:
                res = run_compatibility_workflow(bridge_name, mat, domain=domain)
                entry.update(
                    score=res.scores.get("total"),
                    calibrated=res.calibrated_probability,
                    viable=res.viable,
                    domain=res.domain,
                    evaluated=True,
                )
            except Exception:
                # Material pair not in the compatibility registry — leave unevaluated.
                pass
            interfaces[mat] = entry

        evaluated = [e for e in interfaces.values() if e["evaluated"]]
        # Bottleneck = weakest evaluated interface, by calibrated probability.
        scored = [e for e in evaluated if e["calibrated"] is not None]
        if scored:
            worst = min(scored, key=lambda e: e["calibrated"])
            bottleneck_cal = worst["calibrated"]
            bottleneck_mat = next(m for m, e in interfaces.items() if e is worst)
            bottleneck_viable = all(e["viable"] for e in evaluated if e["viable"] is not None)
        else:
            bottleneck_cal = None
            bottleneck_mat = None
            bottleneck_viable = None

        # Rank: replacement quality, tempered by the worst-interface compatibility.
        cell_term = bottleneck_cal if bottleneck_cal is not None else 0.5
        combined = 0.6 * candidate.overall_score + 0.4 * cell_term

        out.append({
            "candidate": candidate,
            "interfaces": interfaces,
            "bottleneck_material": bottleneck_mat,
            "bottleneck_calibrated": bottleneck_cal,
            "bottleneck_viable": bottleneck_viable,
            "n_evaluated": len(evaluated),
            "combined_rank": round(combined, 4),
        })

    out.sort(key=lambda d: d["combined_rank"], reverse=True)
    return out


def score_replacement(
    pfas_name: str,
    replacement_name: str,
    use_case: UseCase = UseCase.GENERAL,
) -> Optional[ReplacementCandidate]:
    """
    Score a specific replacement candidate for a PFAS substance.

    Returns the ReplacementCandidate if found, None otherwise.
    """
    candidates = find_replacements(pfas_name, use_case)
    for c in candidates:
        if c.name == replacement_name:
            return c
    return None


def get_all_replaceable_pfas() -> List[str]:
    """Get list of PFAS substances that have replacement candidates."""
    return sorted({name for (name, _) in REPLACEMENT_MAP.keys()})


def get_use_cases_for_pfas(pfas_name: str) -> List[UseCase]:
    """Get all use cases that have replacement data for a given PFAS."""
    return sorted(
        {uc for (name, uc) in REPLACEMENT_MAP.keys() if name == pfas_name},
        key=lambda x: x.value,
    )


if __name__ == "__main__":
    print("=" * 70)
    print("PFAS Replacement Scorer")
    print("=" * 70)
    for pfas_name in get_all_replaceable_pfas():
        use_cases = get_use_cases_for_pfas(pfas_name)
        print(f"\n{pfas_name}:")
        for uc in use_cases:
            candidates = find_replacements(pfas_name, uc)
            print(f"  [{uc.value}]")
            for c in candidates:
                print(f"    {c.name:20s}  score={c.overall_score:.3f}  "
                      f"perf={c.performance_match:.2f}  cost={c.cost_factor:.2f}")
