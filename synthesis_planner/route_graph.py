# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Synthesis Route Graph
======================

Core dataclasses and curated synthesis routes for battery materials,
ceramics, and polymers. Each route is a chain of SynthesisStep morphisms
from precursors to final product.

Routes are curated from literature with citations. This is NOT ML-generated;
it is a knowledge base of real published recipes stored as morphism chains
in the categorical framework.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SynthesisConditions:
    """Processing conditions for a single synthesis step."""
    temperature_C: float
    time_hours: float
    atmosphere: str = "air"          # air, N2, Ar, vacuum, H2/Ar, O2
    pressure_atm: float = 1.0
    equipment: str = "furnace"       # furnace, ball_mill, mixer, spray_dryer, etc.


@dataclass
class SynthesisStep:
    """A single step in a synthesis route (a morphism in the category)."""
    operation: str                   # "mix", "calcine", "grind", "dry", "wash", "coat", etc.
    inputs: List[str]                # Input material names
    output: str                      # Output material name
    conditions: SynthesisConditions
    success_probability: float       # 0-1, from literature
    hazards: List[str] = field(default_factory=list)
    notes: str = ""
    citation: str = ""


@dataclass
class SynthesisRoute:
    """A complete synthesis route: ordered chain of steps from precursors to target."""
    name: str
    target: str                      # Target material formula/name
    steps: List[SynthesisStep]       # Ordered sequence
    precursors: List[str]            # Starting materials (auto-derived if empty)
    overall_confidence: float        # 0.75*min + 0.25*avg of step confidences
    total_time_hours: float          # Sum of step times
    max_temperature_C: float         # Max temp across all steps
    risk_level: str                  # "low", "medium", "high"
    citation: str = ""               # Primary publication DOI


def compute_route_confidence(steps: List[SynthesisStep]) -> float:
    """Compute route confidence: 0.75 * bottleneck + 0.25 * average."""
    if not steps:
        return 0.0
    probs = [s.success_probability for s in steps]
    return 0.75 * min(probs) + 0.25 * (sum(probs) / len(probs))


def compute_total_time(steps: List[SynthesisStep]) -> float:
    """Sum of all step durations."""
    return sum(s.conditions.time_hours for s in steps)


def compute_max_temp(steps: List[SynthesisStep]) -> float:
    """Maximum temperature across all steps."""
    if not steps:
        return 0.0
    return max(s.conditions.temperature_C for s in steps)


def derive_precursors(steps: List[SynthesisStep]) -> List[str]:
    """Derive precursors: inputs to step 1 that are not outputs of earlier steps."""
    all_outputs = set()
    precursors = []
    for step in steps:
        for inp in step.inputs:
            if inp not in all_outputs and inp not in precursors:
                precursors.append(inp)
        all_outputs.add(step.output)
    return precursors


def build_route(
    name: str,
    target: str,
    steps: List[SynthesisStep],
    citation: str = "",
) -> SynthesisRoute:
    """Build a SynthesisRoute with auto-computed fields."""
    confidence = compute_route_confidence(steps)
    total_time = compute_total_time(steps)
    max_temp = compute_max_temp(steps)
    precursors = derive_precursors(steps)

    # Risk level from hazard count and step complexity
    all_hazards = []
    for s in steps:
        all_hazards.extend(s.hazards)
    if any(h in all_hazards for h in ['toxic_gas', 'H2S_release', 'pyrophoric']):
        risk = "high"
    elif any(h in all_hazards for h in ['exothermic', 'moisture_sensitive', 'corrosive']):
        risk = "medium"
    else:
        risk = "low"

    return SynthesisRoute(
        name=name,
        target=target,
        steps=steps,
        precursors=precursors,
        overall_confidence=round(confidence, 4),
        total_time_hours=round(total_time, 2),
        max_temperature_C=max_temp,
        risk_level=risk,
        citation=citation,
    )


# ============================================================================
# Curated Synthesis Routes (~25)
# ============================================================================

# --- LFP: LiFePO4 (3 routes) ---

LFP_SOLID_STATE = build_route(
    name="LFP_solid_state",
    target="LFP",
    steps=[
        SynthesisStep(
            operation="mix",
            inputs=["Li2CO3", "Fe2O3", "NH4H2PO4"],
            output="LFP_precursor_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="ball_mill"),
            success_probability=0.95,
            notes="Stoichiometric ball milling of precursors",
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["LFP_precursor_mix"],
            output="LFP_calcined",
            conditions=SynthesisConditions(temperature_C=350, time_hours=5.0,
                                           atmosphere="N2", equipment="furnace"),
            success_probability=0.90,
            notes="Decomposition of carbonates and phosphates",
        ),
        SynthesisStep(
            operation="grind",
            inputs=["LFP_calcined"],
            output="LFP_ground",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="ball_mill"),
            success_probability=0.98,
            notes="Intermediate grinding to improve homogeneity",
        ),
        SynthesisStep(
            operation="sinter",
            inputs=["LFP_ground"],
            output="LFP",
            conditions=SynthesisConditions(temperature_C=700, time_hours=10.0,
                                           atmosphere="N2", equipment="furnace"),
            success_probability=0.85,
            hazards=["exothermic"],
            notes="Final sintering under N2 to maintain Fe2+ oxidation state",
            citation="10.1149/1.1393348",
        ),
    ],
    citation="10.1149/1.1393348",  # Padhi et al., J. Electrochem. Soc. 1997
)


LFP_SOL_GEL = build_route(
    name="LFP_sol_gel",
    target="LFP",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["LiNO3", "Fe(NO3)3", "H3PO4", "citric_acid"],
            output="LFP_sol",
            conditions=SynthesisConditions(temperature_C=60, time_hours=3.0,
                                           equipment="stirrer"),
            success_probability=0.92,
            notes="Dissolve metal salts in citric acid solution (chelating agent)",
        ),
        SynthesisStep(
            operation="gel",
            inputs=["LFP_sol"],
            output="LFP_gel",
            conditions=SynthesisConditions(temperature_C=80, time_hours=12.0,
                                           equipment="oven"),
            success_probability=0.90,
            notes="Evaporate solvent to form gel",
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["LFP_gel"],
            output="LFP",
            conditions=SynthesisConditions(temperature_C=600, time_hours=8.0,
                                           atmosphere="Ar", equipment="furnace"),
            success_probability=0.82,
            notes="Calcine gel under inert atmosphere",
            citation="10.1016/j.jpowsour.2007.04.042",
        ),
    ],
    citation="10.1016/j.jpowsour.2007.04.042",
)


LFP_HYDROTHERMAL = build_route(
    name="LFP_hydrothermal",
    target="LFP",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["LiOH", "FeSO4", "H3PO4"],
            output="LFP_solution",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="stirrer"),
            success_probability=0.95,
            notes="Dissolve precursors in DI water at stoichiometric ratio",
        ),
        SynthesisStep(
            operation="hydrothermal",
            inputs=["LFP_solution"],
            output="LFP_crude",
            conditions=SynthesisConditions(temperature_C=180, time_hours=12.0,
                                           pressure_atm=10.0, equipment="autoclave"),
            success_probability=0.80,
            hazards=["high_pressure"],
            notes="Hydrothermal synthesis in autoclave at 180C/10atm",
            citation="10.1021/cm048764",
        ),
        SynthesisStep(
            operation="wash",
            inputs=["LFP_crude", "DI_water"],
            output="LFP_washed",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="filter"),
            success_probability=0.98,
        ),
        SynthesisStep(
            operation="dry",
            inputs=["LFP_washed"],
            output="LFP",
            conditions=SynthesisConditions(temperature_C=80, time_hours=12.0,
                                           atmosphere="vacuum", equipment="oven"),
            success_probability=0.97,
        ),
    ],
    citation="10.1021/cm048764",
)


# --- NMC811: LiNi0.8Mn0.1Co0.1O2 ---

NMC811_COPRECIPITATION = build_route(
    name="NMC811_coprecipitation",
    target="NMC811",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["NiSO4", "MnSO4", "CoSO4"],
            output="NMC_TM_solution",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="stirrer"),
            success_probability=0.95,
            notes="Dissolve transition metal sulfates in 2M ratio 8:1:1",
        ),
        SynthesisStep(
            operation="coprecipitate",
            inputs=["NMC_TM_solution", "NaOH", "NH4OH"],
            output="NMC_hydroxide_precursor",
            conditions=SynthesisConditions(temperature_C=50, time_hours=12.0,
                                           atmosphere="N2", equipment="reactor"),
            success_probability=0.85,
            notes="Coprecipitation at pH 11.5 under N2, NH4OH as chelating agent",
            citation="10.1021/acs.chemmater.7b03080",
        ),
        SynthesisStep(
            operation="wash",
            inputs=["NMC_hydroxide_precursor", "DI_water"],
            output="NMC_hydroxide_washed",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="filter"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="dry",
            inputs=["NMC_hydroxide_washed"],
            output="NMC_hydroxide_dried",
            conditions=SynthesisConditions(temperature_C=120, time_hours=12.0,
                                           equipment="oven"),
            success_probability=0.97,
        ),
        SynthesisStep(
            operation="mix",
            inputs=["NMC_hydroxide_dried", "LiOH"],
            output="NMC_Li_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="mortar"),
            success_probability=0.95,
            notes="Mix with 5% excess LiOH to compensate Li loss at high temp",
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["NMC_Li_mix"],
            output="NMC811",
            conditions=SynthesisConditions(temperature_C=800, time_hours=12.0,
                                           atmosphere="O2", equipment="furnace"),
            success_probability=0.80,
            hazards=["moisture_sensitive"],
            notes="High-temp calcination under O2 flow; NMC811 is moisture-sensitive",
            citation="10.1021/acs.chemmater.7b03080",
        ),
    ],
    citation="10.1021/acs.chemmater.7b03080",
)


# --- NMC622: LiNi0.6Mn0.2Co0.2O2 ---

NMC622_COPRECIPITATION = build_route(
    name="NMC622_coprecipitation",
    target="NMC622",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["NiSO4", "MnSO4", "CoSO4"],
            output="NMC622_TM_solution",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="stirrer"),
            success_probability=0.95,
            notes="6:2:2 molar ratio",
        ),
        SynthesisStep(
            operation="coprecipitate",
            inputs=["NMC622_TM_solution", "NaOH", "NH4OH"],
            output="NMC622_hydroxide",
            conditions=SynthesisConditions(temperature_C=50, time_hours=12.0,
                                           atmosphere="N2", equipment="reactor"),
            success_probability=0.88,
            notes="pH 11.0, N2 blanket",
        ),
        SynthesisStep(
            operation="mix",
            inputs=["NMC622_hydroxide", "LiOH"],
            output="NMC622_Li_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="mortar"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["NMC622_Li_mix"],
            output="NMC622",
            conditions=SynthesisConditions(temperature_C=850, time_hours=12.0,
                                           atmosphere="O2", equipment="furnace"),
            success_probability=0.85,
        ),
    ],
    citation="10.1016/j.jpowsour.2013.12.063",
)


# --- NMC111: LiNi1/3Mn1/3Co1/3O2 ---

NMC111_COPRECIPITATION = build_route(
    name="NMC111_coprecipitation",
    target="NMC111",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["NiSO4", "MnSO4", "CoSO4"],
            output="NMC111_TM_solution",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="stirrer"),
            success_probability=0.96,
            notes="1:1:1 molar ratio, easier to control than high-Ni",
        ),
        SynthesisStep(
            operation="coprecipitate",
            inputs=["NMC111_TM_solution", "NaOH", "NH4OH"],
            output="NMC111_hydroxide",
            conditions=SynthesisConditions(temperature_C=50, time_hours=10.0,
                                           atmosphere="N2", equipment="reactor"),
            success_probability=0.90,
        ),
        SynthesisStep(
            operation="mix",
            inputs=["NMC111_hydroxide", "Li2CO3"],
            output="NMC111_Li_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="mortar"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["NMC111_Li_mix"],
            output="NMC111",
            conditions=SynthesisConditions(temperature_C=900, time_hours=12.0,
                                           atmosphere="air", equipment="furnace"),
            success_probability=0.90,
        ),
    ],
    citation="10.1149/1.1391631",
)


# --- LCO: LiCoO2 ---

LCO_SOLID_STATE = build_route(
    name="LCO_solid_state",
    target="LCO",
    steps=[
        SynthesisStep(
            operation="mix",
            inputs=["Li2CO3", "Co3O4"],
            output="LCO_precursor_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="ball_mill"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["LCO_precursor_mix"],
            output="LCO_calcined",
            conditions=SynthesisConditions(temperature_C=600, time_hours=5.0,
                                           atmosphere="air", equipment="furnace"),
            success_probability=0.92,
        ),
        SynthesisStep(
            operation="sinter",
            inputs=["LCO_calcined"],
            output="LCO",
            conditions=SynthesisConditions(temperature_C=900, time_hours=12.0,
                                           atmosphere="air", equipment="furnace"),
            success_probability=0.88,
            notes="Standard high-temp sintering; original Li-ion cathode",
            citation="10.1016/0025-5408(80)90012-4",
        ),
    ],
    citation="10.1016/0025-5408(80)90012-4",  # Mizushima et al., 1980
)


# --- LMO: LiMn2O4 ---

LMO_SOLID_STATE = build_route(
    name="LMO_solid_state",
    target="LMO",
    steps=[
        SynthesisStep(
            operation="mix",
            inputs=["Li2CO3", "MnO2"],
            output="LMO_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="ball_mill"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["LMO_mix"],
            output="LMO",
            conditions=SynthesisConditions(temperature_C=800, time_hours=24.0,
                                           atmosphere="air", equipment="furnace"),
            success_probability=0.85,
            notes="Spinel LiMn2O4; long calcination for phase purity",
            citation="10.1016/0167-2738(94)90291-7",
        ),
    ],
    citation="10.1016/0167-2738(94)90291-7",
)


# --- Graphite Anode Coating ---

GRAPHITE_ANODE_COATING = build_route(
    name="graphite_anode_coating",
    target="Graphite_anode_electrode",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["PVDF_powder", "NMP"],
            output="PVDF_binder_solution",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="stirrer"),
            success_probability=0.97,
            hazards=["NMP_toxic"],
            notes="Dissolve 5wt% PVDF in NMP solvent",
        ),
        SynthesisStep(
            operation="mix",
            inputs=["graphite_powder", "carbon_black", "PVDF_binder_solution"],
            output="anode_slurry",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="mixer"),
            success_probability=0.95,
            notes="90:5:5 ratio graphite:carbon_black:PVDF, planetary mixing",
        ),
        SynthesisStep(
            operation="coat",
            inputs=["anode_slurry", "Cu_foil"],
            output="anode_wet_coating",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="doctor_blade"),
            success_probability=0.90,
            notes="Doctor blade coating, ~100um wet thickness",
        ),
        SynthesisStep(
            operation="dry",
            inputs=["anode_wet_coating"],
            output="anode_dried",
            conditions=SynthesisConditions(temperature_C=120, time_hours=2.0,
                                           atmosphere="vacuum", equipment="oven"),
            success_probability=0.95,
            notes="Vacuum dry to remove NMP",
        ),
        SynthesisStep(
            operation="calender",
            inputs=["anode_dried"],
            output="Graphite_anode_electrode",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.1,
                                           equipment="calender_rolls"),
            success_probability=0.93,
            notes="Calender to target density ~1.5 g/cc",
        ),
    ],
    citation="10.1016/j.jpowsour.2011.09.100",
)


# --- CMC/SBR Graphite Anode (water-based) ---

GRAPHITE_ANODE_WATER = build_route(
    name="graphite_anode_water_based",
    target="Graphite_anode_electrode_water",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["CMC_powder", "DI_water"],
            output="CMC_solution",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="stirrer"),
            success_probability=0.97,
        ),
        SynthesisStep(
            operation="mix",
            inputs=["graphite_powder", "carbon_black", "CMC_solution", "SBR_latex"],
            output="anode_slurry_water",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="mixer"),
            success_probability=0.95,
            notes="96:1:1.5:1.5 ratio, water-based (no NMP), greener process",
        ),
        SynthesisStep(
            operation="coat",
            inputs=["anode_slurry_water", "Cu_foil"],
            output="anode_wet_water",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="doctor_blade"),
            success_probability=0.90,
        ),
        SynthesisStep(
            operation="dry",
            inputs=["anode_wet_water"],
            output="Graphite_anode_electrode_water",
            conditions=SynthesisConditions(temperature_C=80, time_hours=1.0,
                                           equipment="oven"),
            success_probability=0.95,
            notes="Lower dry temp than NMP process",
        ),
    ],
    citation="10.1016/j.jpowsour.2014.07.033",
)


# --- LLZO: Li7La3Zr2O12 (solid electrolyte) ---

LLZO_SOLID_STATE = build_route(
    name="LLZO_solid_state",
    target="LLZO",
    steps=[
        SynthesisStep(
            operation="mix",
            inputs=["LiOH", "La2O3", "ZrO2"],
            output="LLZO_precursor_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=4.0,
                                           equipment="ball_mill"),
            success_probability=0.90,
            notes="10% excess LiOH to compensate Li loss at high temp",
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["LLZO_precursor_mix"],
            output="LLZO_calcined",
            conditions=SynthesisConditions(temperature_C=900, time_hours=6.0,
                                           atmosphere="air", equipment="furnace"),
            success_probability=0.80,
            notes="Form garnet phase; tetragonal initially",
        ),
        SynthesisStep(
            operation="grind",
            inputs=["LLZO_calcined"],
            output="LLZO_ground",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="ball_mill"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="pelletize",
            inputs=["LLZO_ground"],
            output="LLZO_pellet",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           pressure_atm=200, equipment="press"),
            success_probability=0.90,
        ),
        SynthesisStep(
            operation="sinter",
            inputs=["LLZO_pellet"],
            output="LLZO",
            conditions=SynthesisConditions(temperature_C=1100, time_hours=6.0,
                                           atmosphere="air", equipment="furnace"),
            success_probability=0.75,
            hazards=["moisture_sensitive"],
            notes="Sintering to cubic LLZO; must avoid Li2CO3 surface contamination",
            citation="10.1002/aenm.201501590",
        ),
    ],
    citation="10.1002/aenm.201501590",
)


# --- LGPS: Li10GeP2S12 ---

LGPS_BALL_MILL = build_route(
    name="LGPS_ball_mill",
    target="LGPS",
    steps=[
        SynthesisStep(
            operation="mix",
            inputs=["Li2S", "GeS2", "P2S5"],
            output="LGPS_mixture",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           atmosphere="Ar", equipment="glovebox"),
            success_probability=0.90,
            hazards=["moisture_sensitive", "H2S_release"],
            notes="Must handle in Ar glovebox; sulfides are moisture-sensitive",
        ),
        SynthesisStep(
            operation="ball_mill",
            inputs=["LGPS_mixture"],
            output="LGPS_milled",
            conditions=SynthesisConditions(temperature_C=25, time_hours=20.0,
                                           atmosphere="Ar", equipment="ball_mill"),
            success_probability=0.80,
            hazards=["H2S_release"],
            notes="Mechanochemical synthesis in sealed jar under Ar",
            citation="10.1038/nmat3066",
        ),
        SynthesisStep(
            operation="anneal",
            inputs=["LGPS_milled"],
            output="LGPS",
            conditions=SynthesisConditions(temperature_C=550, time_hours=8.0,
                                           atmosphere="Ar", equipment="furnace"),
            success_probability=0.75,
            hazards=["H2S_release", "moisture_sensitive"],
            notes="Crystallization anneal; sealed quartz tube under Ar",
        ),
    ],
    citation="10.1038/nmat3066",  # Kamaya et al., Nature Materials 2011
)


# --- Li3PS4 ---

LI3PS4_BALL_MILL = build_route(
    name="Li3PS4_ball_mill",
    target="Li3PS4",
    steps=[
        SynthesisStep(
            operation="mix",
            inputs=["Li2S", "P2S5"],
            output="Li3PS4_mixture",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           atmosphere="Ar", equipment="glovebox"),
            success_probability=0.92,
            hazards=["moisture_sensitive", "H2S_release"],
        ),
        SynthesisStep(
            operation="ball_mill",
            inputs=["Li3PS4_mixture"],
            output="Li3PS4",
            conditions=SynthesisConditions(temperature_C=25, time_hours=10.0,
                                           atmosphere="Ar", equipment="ball_mill"),
            success_probability=0.85,
            hazards=["H2S_release"],
            notes="Direct mechanochemical synthesis, no heat treatment needed",
            citation="10.1016/j.ssi.2012.08.023",
        ),
    ],
    citation="10.1016/j.ssi.2012.08.023",
)


# --- NCA: LiNi0.8Co0.15Al0.05O2 ---

NCA_COPRECIPITATION = build_route(
    name="NCA_coprecipitation",
    target="NCA",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["NiSO4", "CoSO4", "Al2(SO4)3"],
            output="NCA_TM_solution",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="stirrer"),
            success_probability=0.95,
            notes="80:15:5 Ni:Co:Al molar ratio",
        ),
        SynthesisStep(
            operation="coprecipitate",
            inputs=["NCA_TM_solution", "NaOH", "NH4OH"],
            output="NCA_hydroxide",
            conditions=SynthesisConditions(temperature_C=50, time_hours=12.0,
                                           atmosphere="N2", equipment="reactor"),
            success_probability=0.85,
        ),
        SynthesisStep(
            operation="mix",
            inputs=["NCA_hydroxide", "LiOH"],
            output="NCA_Li_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="mortar"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["NCA_Li_mix"],
            output="NCA",
            conditions=SynthesisConditions(temperature_C=750, time_hours=15.0,
                                           atmosphere="O2", equipment="furnace"),
            success_probability=0.80,
            hazards=["moisture_sensitive"],
            notes="Lower calcination T than NMC811 to avoid Al segregation",
        ),
    ],
    citation="10.1016/S0378-7753(98)00227-4",
)


# --- Al2O3: Alumina (2 routes) ---

AL2O3_BAYER = build_route(
    name="Al2O3_Bayer_simplified",
    target="Al2O3",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["bauxite", "NaOH_solution"],
            output="sodium_aluminate_solution",
            conditions=SynthesisConditions(temperature_C=180, time_hours=4.0,
                                           pressure_atm=5.0, equipment="autoclave"),
            success_probability=0.90,
            hazards=["corrosive"],
            notes="Bayer process: dissolve Al(OH)3 from bauxite, leave Fe2O3 behind",
        ),
        SynthesisStep(
            operation="precipitate",
            inputs=["sodium_aluminate_solution"],
            output="Al(OH)3_precipitate",
            conditions=SynthesisConditions(temperature_C=60, time_hours=48.0,
                                           equipment="crystallizer"),
            success_probability=0.85,
            notes="Seed precipitation of gibbsite",
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["Al(OH)3_precipitate"],
            output="Al2O3",
            conditions=SynthesisConditions(temperature_C=1100, time_hours=4.0,
                                           atmosphere="air", equipment="rotary_kiln"),
            success_probability=0.92,
            notes="Calcination of gibbsite to alpha-alumina",
        ),
    ],
    citation="industrial_standard",
)


AL2O3_PVD = build_route(
    name="Al2O3_PVD_coating",
    target="Al2O3_coating",
    steps=[
        SynthesisStep(
            operation="clean",
            inputs=["substrate_metal"],
            output="clean_substrate",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="ultrasonic_bath"),
            success_probability=0.98,
            notes="Ultrasonic clean in acetone + isopropanol",
        ),
        SynthesisStep(
            operation="deposit",
            inputs=["clean_substrate", "Al_target", "O2_gas"],
            output="Al2O3_coating",
            conditions=SynthesisConditions(temperature_C=300, time_hours=2.0,
                                           pressure_atm=0.001, equipment="PVD_chamber"),
            success_probability=0.85,
            notes="Reactive RF magnetron sputtering; Al target in O2/Ar plasma",
        ),
    ],
    citation="10.1016/j.tsf.2004.07.037",
)


# --- TiN: Titanium Nitride (PVD) ---

TIN_PVD = build_route(
    name="TiN_PVD_coating",
    target="TiN_coating",
    steps=[
        SynthesisStep(
            operation="clean",
            inputs=["substrate_metal"],
            output="clean_substrate_tin",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="ultrasonic_bath"),
            success_probability=0.98,
        ),
        SynthesisStep(
            operation="etch",
            inputs=["clean_substrate_tin"],
            output="etched_substrate",
            conditions=SynthesisConditions(temperature_C=300, time_hours=0.25,
                                           pressure_atm=0.01, equipment="PVD_chamber"),
            success_probability=0.95,
            notes="Ar ion bombardment to improve adhesion",
        ),
        SynthesisStep(
            operation="deposit",
            inputs=["etched_substrate", "Ti_target", "N2_gas"],
            output="TiN_coating",
            conditions=SynthesisConditions(temperature_C=400, time_hours=1.5,
                                           pressure_atm=0.001, equipment="PVD_chamber"),
            success_probability=0.88,
            notes="Reactive DC magnetron sputtering; Ti target in N2/Ar",
        ),
    ],
    citation="10.1016/S0257-8972(03)00989-2",
)


# --- SiC: Silicon Carbide (Acheson process) ---

SIC_ACHESON = build_route(
    name="SiC_Acheson",
    target="SiC",
    steps=[
        SynthesisStep(
            operation="mix",
            inputs=["SiO2", "petroleum_coke"],
            output="SiC_charge_mix",
            conditions=SynthesisConditions(temperature_C=25, time_hours=1.0,
                                           equipment="mixer"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="carbothermal_reduction",
            inputs=["SiC_charge_mix"],
            output="SiC_raw",
            conditions=SynthesisConditions(temperature_C=2500, time_hours=36.0,
                                           equipment="Acheson_furnace"),
            success_probability=0.80,
            hazards=["exothermic", "CO_gas"],
            notes="SiO2 + 3C -> SiC + 2CO at ~2500C; Acheson resistance furnace",
        ),
        SynthesisStep(
            operation="crush_and_grade",
            inputs=["SiC_raw"],
            output="SiC",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="crusher"),
            success_probability=0.92,
        ),
    ],
    citation="industrial_standard",
)


# --- PVDF Film (solution casting) ---

PVDF_FILM = build_route(
    name="PVDF_film_casting",
    target="PVDF_film",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["PVDF_powder", "NMP"],
            output="PVDF_solution",
            conditions=SynthesisConditions(temperature_C=60, time_hours=4.0,
                                           equipment="stirrer"),
            success_probability=0.95,
            hazards=["NMP_toxic"],
            notes="10-15wt% PVDF in NMP",
        ),
        SynthesisStep(
            operation="cast",
            inputs=["PVDF_solution"],
            output="PVDF_wet_film",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.1,
                                           equipment="doctor_blade"),
            success_probability=0.92,
            notes="Cast on glass plate, ~200um wet thickness",
        ),
        SynthesisStep(
            operation="dry",
            inputs=["PVDF_wet_film"],
            output="PVDF_film",
            conditions=SynthesisConditions(temperature_C=80, time_hours=12.0,
                                           atmosphere="vacuum", equipment="oven"),
            success_probability=0.95,
        ),
    ],
    citation="10.1016/j.memsci.2005.10.040",
)


# --- PEO Electrolyte Membrane ---

PEO_MEMBRANE = build_route(
    name="PEO_electrolyte_membrane",
    target="PEO_electrolyte",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["PEO_powder", "LiTFSI", "acetonitrile"],
            output="PEO_casting_solution",
            conditions=SynthesisConditions(temperature_C=25, time_hours=12.0,
                                           atmosphere="Ar", equipment="glovebox"),
            success_probability=0.90,
            hazards=["moisture_sensitive"],
            notes="EO:Li = 20:1 molar ratio; handle in glovebox",
        ),
        SynthesisStep(
            operation="cast",
            inputs=["PEO_casting_solution"],
            output="PEO_wet_membrane",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.1,
                                           atmosphere="Ar", equipment="doctor_blade"),
            success_probability=0.90,
        ),
        SynthesisStep(
            operation="dry",
            inputs=["PEO_wet_membrane"],
            output="PEO_dried_membrane",
            conditions=SynthesisConditions(temperature_C=50, time_hours=24.0,
                                           atmosphere="Ar", equipment="glovebox"),
            success_probability=0.92,
        ),
        SynthesisStep(
            operation="hot_press",
            inputs=["PEO_dried_membrane"],
            output="PEO_electrolyte",
            conditions=SynthesisConditions(temperature_C=80, time_hours=0.5,
                                           pressure_atm=5.0, equipment="hot_press"),
            success_probability=0.88,
            notes="Hot press to improve ionic conductivity and reduce porosity",
        ),
    ],
    citation="10.1038/nmat4369",
)


# --- YSZ Thermal Barrier Coating ---

YSZ_PLASMA_SPRAY = build_route(
    name="YSZ_thermal_barrier",
    target="YSZ_coating",
    steps=[
        SynthesisStep(
            operation="clean",
            inputs=["Inconel_substrate"],
            output="clean_Inconel",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="grit_blaster"),
            success_probability=0.97,
            notes="Grit blast to roughen surface for adhesion",
        ),
        SynthesisStep(
            operation="bond_coat",
            inputs=["clean_Inconel", "MCrAlY_powder"],
            output="bond_coated_substrate",
            conditions=SynthesisConditions(temperature_C=200, time_hours=0.5,
                                           equipment="plasma_spray"),
            success_probability=0.90,
            notes="NiCoCrAlY bond coat, 100-150um thick",
        ),
        SynthesisStep(
            operation="deposit",
            inputs=["bond_coated_substrate", "YSZ_powder"],
            output="YSZ_coating",
            conditions=SynthesisConditions(temperature_C=250, time_hours=1.0,
                                           equipment="plasma_spray"),
            success_probability=0.85,
            notes="Air plasma spray YSZ top coat, 200-400um thick",
        ),
    ],
    citation="10.1007/s11666-004-0075-6",
)


# --- LFP Cathode Coating (electrode fabrication) ---

LFP_CATHODE_COATING = build_route(
    name="LFP_cathode_coating",
    target="LFP_cathode_electrode",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["PVDF_powder", "NMP"],
            output="PVDF_cathode_binder",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="stirrer"),
            success_probability=0.97,
            hazards=["NMP_toxic"],
        ),
        SynthesisStep(
            operation="mix",
            inputs=["LFP_powder", "carbon_black", "PVDF_cathode_binder"],
            output="cathode_slurry",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="mixer"),
            success_probability=0.92,
            notes="80:10:10 LFP:CB:PVDF mass ratio",
        ),
        SynthesisStep(
            operation="coat",
            inputs=["cathode_slurry", "Al_foil"],
            output="cathode_wet",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="doctor_blade"),
            success_probability=0.90,
        ),
        SynthesisStep(
            operation="dry",
            inputs=["cathode_wet"],
            output="cathode_dried",
            conditions=SynthesisConditions(temperature_C=120, time_hours=4.0,
                                           atmosphere="vacuum", equipment="oven"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="calender",
            inputs=["cathode_dried"],
            output="LFP_cathode_electrode",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.1,
                                           equipment="calender_rolls"),
            success_probability=0.93,
        ),
    ],
    citation="10.1016/j.jpowsour.2011.09.100",
)


# --- NMC811 Cathode Coating ---

NMC811_CATHODE_COATING = build_route(
    name="NMC811_cathode_coating",
    target="NMC811_cathode_electrode",
    steps=[
        SynthesisStep(
            operation="dissolve",
            inputs=["PVDF_powder", "NMP"],
            output="PVDF_NMC_binder",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="stirrer"),
            success_probability=0.97,
            hazards=["NMP_toxic"],
        ),
        SynthesisStep(
            operation="mix",
            inputs=["NMC811_powder", "carbon_black", "PVDF_NMC_binder"],
            output="NMC_cathode_slurry",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           atmosphere="dry_room", equipment="mixer"),
            success_probability=0.90,
            hazards=["moisture_sensitive"],
            notes="90:5:5 NMC:CB:PVDF; must process in dry room (dew point < -40C)",
        ),
        SynthesisStep(
            operation="coat",
            inputs=["NMC_cathode_slurry", "Al_foil"],
            output="NMC_cathode_wet",
            conditions=SynthesisConditions(temperature_C=25, time_hours=0.5,
                                           equipment="doctor_blade"),
            success_probability=0.88,
        ),
        SynthesisStep(
            operation="dry",
            inputs=["NMC_cathode_wet"],
            output="NMC811_cathode_electrode",
            conditions=SynthesisConditions(temperature_C=120, time_hours=12.0,
                                           atmosphere="vacuum", equipment="oven"),
            success_probability=0.93,
            hazards=["moisture_sensitive"],
        ),
    ],
    citation="10.1021/acs.chemmater.7b03080",
)


# --- NASICON: Na3Zr2Si2PO12 (sodium solid electrolyte) ---

NASICON_SOLID_STATE = build_route(
    name="NASICON_solid_state",
    target="NASICON",
    steps=[
        SynthesisStep(
            operation="mix",
            inputs=["Na2CO3", "ZrO2", "SiO2", "NH4H2PO4"],
            output="NASICON_precursor",
            conditions=SynthesisConditions(temperature_C=25, time_hours=4.0,
                                           equipment="ball_mill"),
            success_probability=0.90,
        ),
        SynthesisStep(
            operation="calcine",
            inputs=["NASICON_precursor"],
            output="NASICON_calcined",
            conditions=SynthesisConditions(temperature_C=900, time_hours=8.0,
                                           atmosphere="air", equipment="furnace"),
            success_probability=0.82,
        ),
        SynthesisStep(
            operation="grind",
            inputs=["NASICON_calcined"],
            output="NASICON_ground",
            conditions=SynthesisConditions(temperature_C=25, time_hours=2.0,
                                           equipment="ball_mill"),
            success_probability=0.95,
        ),
        SynthesisStep(
            operation="sinter",
            inputs=["NASICON_ground"],
            output="NASICON",
            conditions=SynthesisConditions(temperature_C=1200, time_hours=10.0,
                                           atmosphere="air", equipment="furnace"),
            success_probability=0.78,
            notes="High-temp sintering for dense NASICON pellet",
        ),
    ],
    citation="10.1016/j.ssi.2004.07.070",
)


# ============================================================================
# Route Registry
# ============================================================================

ALL_ROUTES: Dict[str, List[SynthesisRoute]] = {}
"""Routes indexed by target material name."""

_ROUTE_LIST: List[SynthesisRoute] = [
    LFP_SOLID_STATE,
    LFP_SOL_GEL,
    LFP_HYDROTHERMAL,
    NMC811_COPRECIPITATION,
    NMC622_COPRECIPITATION,
    NMC111_COPRECIPITATION,
    LCO_SOLID_STATE,
    LMO_SOLID_STATE,
    GRAPHITE_ANODE_COATING,
    GRAPHITE_ANODE_WATER,
    LLZO_SOLID_STATE,
    LGPS_BALL_MILL,
    LI3PS4_BALL_MILL,
    NCA_COPRECIPITATION,
    AL2O3_BAYER,
    AL2O3_PVD,
    TIN_PVD,
    SIC_ACHESON,
    PVDF_FILM,
    PEO_MEMBRANE,
    YSZ_PLASMA_SPRAY,
    LFP_CATHODE_COATING,
    NMC811_CATHODE_COATING,
    NASICON_SOLID_STATE,
]

for _route in _ROUTE_LIST:
    ALL_ROUTES.setdefault(_route.target, []).append(_route)

# Also index by common aliases
_ALIASES = {
    'LiFePO4': 'LFP',
    'LiNi0.8Mn0.1Co0.1O2': 'NMC811',
    'LiNi0.6Mn0.2Co0.2O2': 'NMC622',
    'LiNi1/3Mn1/3Co1/3O2': 'NMC111',
    'LiCoO2': 'LCO',
    'LiMn2O4': 'LMO',
    'Li7La3Zr2O12': 'LLZO',
    'Li10GeP2S12': 'LGPS',
    'LiNi0.8Co0.15Al0.05O2': 'NCA',
    'Na3Zr2Si2PO12': 'NASICON',
}


def get_routes(target: str) -> List[SynthesisRoute]:
    """Get all synthesis routes for a target material."""
    # Direct lookup
    routes = ALL_ROUTES.get(target, [])
    if routes:
        return routes
    # Alias lookup
    canonical = _ALIASES.get(target)
    if canonical:
        return ALL_ROUTES.get(canonical, [])
    return []


def get_route_by_name(name: str) -> Optional[SynthesisRoute]:
    """Get a specific route by its unique name."""
    for routes in ALL_ROUTES.values():
        for route in routes:
            if route.name == name:
                return route
    return None


def list_all_targets() -> List[str]:
    """List all target materials with at least one synthesis route."""
    return sorted(ALL_ROUTES.keys())


def list_all_routes() -> List[SynthesisRoute]:
    """List all curated synthesis routes."""
    return list(_ROUTE_LIST)
