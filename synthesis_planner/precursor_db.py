# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Precursor Database
===================

Inventory of common synthesis precursors with cost, purity, hazard class,
and availability. Used by the SynthesisPlanner to estimate costs and
flag missing materials.

Prices are approximate 2024 Sigma-Aldrich/Alfa-Aesar catalog prices for
research-grade quantities (100g-1kg). Industrial bulk prices are 10-100x lower.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Precursor:
    """A starting material for synthesis."""
    name: str
    formula: str
    cost_usd_per_kg: float
    purity_pct: float = 99.0
    supplier: str = "Sigma-Aldrich"
    hazard_class: str = "none"       # none, irritant, toxic, flammable, corrosive, oxidizer
    shelf_life_months: int = 24
    available: bool = True


# ============================================================================
# Precursor Inventory (~50 entries)
# ============================================================================

ALL_PRECURSORS: Dict[str, Precursor] = {}

def _add(p: Precursor) -> Precursor:
    ALL_PRECURSORS[p.name] = p
    return p


# --- Lithium sources ---
_add(Precursor("Li2CO3", "Li2CO3", cost_usd_per_kg=45.0, purity_pct=99.0, hazard_class="irritant"))
_add(Precursor("LiOH", "LiOH", cost_usd_per_kg=55.0, purity_pct=98.0, hazard_class="corrosive"))
_add(Precursor("LiNO3", "LiNO3", cost_usd_per_kg=60.0, purity_pct=99.0, hazard_class="oxidizer"))
_add(Precursor("LiTFSI", "LiN(SO2CF3)2", cost_usd_per_kg=350.0, purity_pct=99.9, hazard_class="irritant",
               supplier="Solvay"))
_add(Precursor("Li2S", "Li2S", cost_usd_per_kg=500.0, purity_pct=99.9, hazard_class="corrosive",
               shelf_life_months=12))

# --- Iron sources ---
_add(Precursor("Fe2O3", "Fe2O3", cost_usd_per_kg=15.0, purity_pct=99.5))
_add(Precursor("FePO4", "FePO4", cost_usd_per_kg=40.0, purity_pct=99.0))
_add(Precursor("FeSO4", "FeSO4", cost_usd_per_kg=10.0, purity_pct=99.0, hazard_class="irritant"))
_add(Precursor("Fe(NO3)3", "Fe(NO3)3*9H2O", cost_usd_per_kg=25.0, purity_pct=98.0, hazard_class="oxidizer"))

# --- Transition metal sulfates (for NMC/NCA) ---
_add(Precursor("NiSO4", "NiSO4*6H2O", cost_usd_per_kg=30.0, purity_pct=99.0, hazard_class="toxic",
               supplier="Alfa-Aesar"))
_add(Precursor("MnSO4", "MnSO4*H2O", cost_usd_per_kg=12.0, purity_pct=99.0, hazard_class="irritant"))
_add(Precursor("CoSO4", "CoSO4*7H2O", cost_usd_per_kg=80.0, purity_pct=99.0, hazard_class="toxic"))
_add(Precursor("Al2(SO4)3", "Al2(SO4)3*18H2O", cost_usd_per_kg=8.0, purity_pct=98.0))

# --- Cobalt and manganese oxides ---
_add(Precursor("Co3O4", "Co3O4", cost_usd_per_kg=120.0, purity_pct=99.5, hazard_class="toxic"))
_add(Precursor("MnO2", "MnO2", cost_usd_per_kg=20.0, purity_pct=99.0, hazard_class="oxidizer"))

# --- Rare earth / zirconium ---
_add(Precursor("La2O3", "La2O3", cost_usd_per_kg=35.0, purity_pct=99.9, hazard_class="irritant"))
_add(Precursor("ZrO2", "ZrO2", cost_usd_per_kg=25.0, purity_pct=99.0))

# --- Phosphorus sources ---
_add(Precursor("NH4H2PO4", "NH4H2PO4", cost_usd_per_kg=15.0, purity_pct=99.0))
_add(Precursor("H3PO4", "H3PO4", cost_usd_per_kg=10.0, purity_pct=85.0, hazard_class="corrosive"))
_add(Precursor("P2S5", "P2S5", cost_usd_per_kg=200.0, purity_pct=99.0, hazard_class="flammable",
               shelf_life_months=12))

# --- Sulfide precursors ---
_add(Precursor("GeS2", "GeS2", cost_usd_per_kg=800.0, purity_pct=99.99, hazard_class="irritant",
               supplier="Alfa-Aesar"))

# --- Bases ---
_add(Precursor("NaOH", "NaOH", cost_usd_per_kg=8.0, purity_pct=98.0, hazard_class="corrosive"))
_add(Precursor("NH4OH", "NH4OH", cost_usd_per_kg=12.0, purity_pct=28.0, hazard_class="corrosive"))
_add(Precursor("NaOH_solution", "NaOH(aq)", cost_usd_per_kg=5.0, purity_pct=50.0, hazard_class="corrosive"))

# --- Sodium sources ---
_add(Precursor("Na2CO3", "Na2CO3", cost_usd_per_kg=10.0, purity_pct=99.5))

# --- Solvents ---
_add(Precursor("NMP", "C5H9NO", cost_usd_per_kg=25.0, purity_pct=99.5, hazard_class="toxic",
               shelf_life_months=36))
_add(Precursor("acetonitrile", "CH3CN", cost_usd_per_kg=20.0, purity_pct=99.9, hazard_class="flammable"))
_add(Precursor("acetone", "CH3COCH3", cost_usd_per_kg=8.0, purity_pct=99.5, hazard_class="flammable"))
_add(Precursor("ethanol", "C2H5OH", cost_usd_per_kg=10.0, purity_pct=99.5, hazard_class="flammable"))
_add(Precursor("DI_water", "H2O", cost_usd_per_kg=0.5, purity_pct=99.99))

# --- Polymer precursors ---
_add(Precursor("PVDF_powder", "-(CH2CF2)n-", cost_usd_per_kg=40.0, purity_pct=99.0, supplier="Arkema"))
_add(Precursor("PEO_powder", "-(CH2CH2O)n-", cost_usd_per_kg=30.0, purity_pct=99.0))
_add(Precursor("CMC_powder", "CMC-Na", cost_usd_per_kg=15.0, purity_pct=99.0))
_add(Precursor("SBR_latex", "SBR", cost_usd_per_kg=12.0, purity_pct=48.0,
               supplier="JSR", shelf_life_months=6))

# --- Carbon additives ---
_add(Precursor("carbon_black", "C", cost_usd_per_kg=15.0, purity_pct=99.0, supplier="Timcal"))
_add(Precursor("graphite_powder", "C", cost_usd_per_kg=10.0, purity_pct=99.5))

# --- Metal foils / substrates ---
_add(Precursor("Cu_foil", "Cu", cost_usd_per_kg=30.0, purity_pct=99.9))
_add(Precursor("Al_foil", "Al", cost_usd_per_kg=15.0, purity_pct=99.0))

# --- Ceramic/PVD targets ---
_add(Precursor("Al_target", "Al", cost_usd_per_kg=80.0, purity_pct=99.99, supplier="Kurt-Lesker"))
_add(Precursor("Ti_target", "Ti", cost_usd_per_kg=120.0, purity_pct=99.99, supplier="Kurt-Lesker"))

# --- Gases ---
_add(Precursor("O2_gas", "O2", cost_usd_per_kg=2.0, purity_pct=99.999))
_add(Precursor("N2_gas", "N2", cost_usd_per_kg=1.5, purity_pct=99.999))
_add(Precursor("Ar_gas", "Ar", cost_usd_per_kg=3.0, purity_pct=99.999))

# --- Chelating agents ---
_add(Precursor("citric_acid", "C6H8O7", cost_usd_per_kg=8.0, purity_pct=99.0))

# --- Industrial ---
_add(Precursor("bauxite", "Al2O3*nH2O", cost_usd_per_kg=0.05, purity_pct=50.0,
               supplier="industrial"))
_add(Precursor("petroleum_coke", "C", cost_usd_per_kg=0.30, purity_pct=95.0,
               supplier="industrial"))
_add(Precursor("SiO2", "SiO2", cost_usd_per_kg=5.0, purity_pct=99.5))

# --- Thermal barrier / bond coat ---
_add(Precursor("MCrAlY_powder", "NiCoCrAlY", cost_usd_per_kg=250.0, purity_pct=99.0,
               supplier="Oerlikon-Metco"))
_add(Precursor("YSZ_powder", "ZrO2-8Y2O3", cost_usd_per_kg=60.0, purity_pct=99.0,
               supplier="Oerlikon-Metco"))
_add(Precursor("Inconel_substrate", "Inconel718", cost_usd_per_kg=50.0, purity_pct=99.0))
_add(Precursor("substrate_metal", "various", cost_usd_per_kg=20.0, purity_pct=99.0))

# --- Electrode powders (synthesized separately, used in coating routes) ---
_add(Precursor("LFP_powder", "LiFePO4", cost_usd_per_kg=15.0, purity_pct=99.0,
               supplier="BTR-New-Energy"))
_add(Precursor("NMC811_powder", "LiNi0.8Mn0.1Co0.1O2", cost_usd_per_kg=35.0, purity_pct=99.0,
               supplier="Umicore"))


# ============================================================================
# Lookup Functions
# ============================================================================

def get_precursor(name: str) -> Optional[Precursor]:
    """Look up a precursor by name."""
    return ALL_PRECURSORS.get(name)


def list_precursors() -> List[str]:
    """List all available precursor names."""
    return sorted(ALL_PRECURSORS.keys())


def estimate_route_cost(precursor_names: List[str], quantity_kg: float = 0.001) -> float:
    """
    Estimate total precursor cost for a synthesis route.

    Args:
        precursor_names: List of precursor names needed
        quantity_kg: Quantity of each precursor in kg (default 1g = 0.001 kg)

    Returns:
        Total estimated cost in USD
    """
    total = 0.0
    for name in precursor_names:
        p = get_precursor(name)
        if p is not None:
            total += p.cost_usd_per_kg * quantity_kg
        else:
            total += 100.0 * quantity_kg  # Default cost for unknown precursors
    return round(total, 2)


def check_availability(precursor_names: List[str]) -> Dict[str, bool]:
    """Check which precursors are available."""
    result = {}
    for name in precursor_names:
        p = get_precursor(name)
        result[name] = p.available if p is not None else False
    return result


def find_missing_precursors(precursor_names: List[str]) -> List[str]:
    """Return precursors that are not in the database."""
    return [n for n in precursor_names if n not in ALL_PRECURSORS]


def find_hazardous_precursors(precursor_names: List[str]) -> Dict[str, str]:
    """Return precursors with hazard classifications."""
    result = {}
    for name in precursor_names:
        p = get_precursor(name)
        if p is not None and p.hazard_class != "none":
            result[name] = p.hazard_class
    return result
