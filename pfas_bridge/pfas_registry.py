"""
PFAS Substance Registry
========================

Curated registry of ~35 PFAS substances with real CAS numbers, regulatory
data, and category classification.  Designed for compliance screening of
materials used in batteries, coatings, seals, and membranes.

Regulatory sources:
- EU REACH Regulation (EC) No 1907/2006 — Annex XVII
- EU PFHxA restriction: Commission Delegated Regulation (EU) 2023/xxxx
- US EPA PFAS Strategic Roadmap (2021)
- Stockholm Convention on POPs (PFOA/PFOS listings)
- ECHA SVHC candidate list

CAS numbers verified against PubChem and ECHA databases.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Set

try:
    from rdkit import Chem
    _RDKIT_AVAILABLE = True
    _CF3_PATTERN = Chem.MolFromSmarts('[#6X4;H0;!$(*~[Cl,Br,I])](F)(F)F')
    _CF2_PATTERN = Chem.MolFromSmarts('[#6X4;H0;!$(*~[Cl,Br,I])](F)(F)')
except ImportError:
    _RDKIT_AVAILABLE = False



# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PFASCategory(Enum):
    """Classification of PFAS substances."""
    PFCA = "perfluorocarboxylic_acid"
    PFSA = "perfluorosulfonic_acid"
    FLUOROPOLYMER = "fluoropolymer"
    FLUOROSURFACTANT = "fluorosurfactant"
    FLUOROTELOMER = "fluorotelor"
    SIDE_CHAIN_FLUORINATED = "side_chain_fluorinated"
    PFAS_PRECURSOR = "pfas_precursor"
    EPA_STRUCTURAL = "epa_structural_registry"



class RegulationStatus(Enum):
    """Current regulatory status of a substance."""
    BANNED = "banned"
    RESTRICTED = "restricted"
    PROPOSED_BAN = "proposed_ban"
    UNDER_REVIEW = "under_review"
    NOT_RESTRICTED = "not_restricted"
    EXEMPT = "exempt"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Regulation:
    """A single regulatory action on a PFAS substance."""
    jurisdiction: str          # "EU", "US", "Stockholm Convention", etc.
    status: RegulationStatus
    effective_date: Optional[date] = None
    description: str = ""
    source: str = ""


@dataclass
class PFASSubstance:
    """A PFAS substance with identity and regulatory information."""
    name: str
    abbreviation: str
    cas_number: str
    category: PFASCategory
    formula: str = ""
    molecular_weight: Optional[float] = None
    regulations: List[Regulation] = field(default_factory=list)
    common_uses: List[str] = field(default_factory=list)
    notes: str = ""

    def is_banned(self, jurisdiction: Optional[str] = None) -> bool:
        """Check if substance is banned (optionally in a specific jurisdiction)."""
        for reg in self.regulations:
            if reg.status == RegulationStatus.BANNED:
                if jurisdiction is None or reg.jurisdiction == jurisdiction:
                    return True
        return False

    def is_restricted(self, jurisdiction: Optional[str] = None) -> bool:
        """Check if substance is banned or restricted."""
        for reg in self.regulations:
            if reg.status in (RegulationStatus.BANNED, RegulationStatus.RESTRICTED):
                if jurisdiction is None or reg.jurisdiction == jurisdiction:
                    return True
        return False

    def restriction_date(self) -> Optional[date]:
        """Earliest restriction/ban effective date."""
        dates = [
            reg.effective_date
            for reg in self.regulations
            if reg.effective_date is not None
            and reg.status in (RegulationStatus.BANNED, RegulationStatus.RESTRICTED,
                               RegulationStatus.PROPOSED_BAN)
        ]
        return min(dates) if dates else None

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "abbreviation": self.abbreviation,
            "cas_number": self.cas_number,
            "category": self.category.value,
            "formula": self.formula,
            "molecular_weight": self.molecular_weight,
            "regulations": [
                {
                    "jurisdiction": r.jurisdiction,
                    "status": r.status.value,
                    "effective_date": r.effective_date.isoformat() if r.effective_date else None,
                    "description": r.description,
                }
                for r in self.regulations
            ],
            "common_uses": self.common_uses,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PFAS_REGISTRY: Dict[str, PFASSubstance] = {}

# ===== Legacy PFAS (banned/severely restricted) =====

PFAS_REGISTRY["PFOA"] = PFASSubstance(
    name="Perfluorooctanoic acid",
    abbreviation="PFOA",
    cas_number="335-67-1",
    category=PFASCategory.PFCA,
    formula="C8HF15O2",
    molecular_weight=414.07,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2020, 7, 4),
            description="REACH Annex XVII entry 68; <25 ppb threshold",
            source="Regulation (EU) 2019/1021",
        ),
        Regulation(
            jurisdiction="Stockholm Convention",
            status=RegulationStatus.BANNED,
            effective_date=date(2019, 12, 3),
            description="Listed under Annex A (elimination)",
            source="COP-9 Decision SC-9/12",
        ),
        Regulation(
            jurisdiction="US",
            status=RegulationStatus.RESTRICTED,
            effective_date=date(2020, 1, 1),
            description="EPA SNUR; no new uses without review",
            source="EPA 40 CFR 721",
        ),
    ],
    common_uses=["Surfactant", "PTFE processing aid", "Stain repellent"],
    notes="Legacy C8 PFAS; primary PTFE processing aid until phase-out",
)

PFAS_REGISTRY["PFOS"] = PFASSubstance(
    name="Perfluorooctane sulfonic acid",
    abbreviation="PFOS",
    cas_number="1763-23-1",
    category=PFASCategory.PFSA,
    formula="C8HF17O3S",
    molecular_weight=500.13,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2010, 6, 25),
            description="REACH Annex XVII; POPs Regulation",
            source="Regulation (EU) 2019/1021",
        ),
        Regulation(
            jurisdiction="Stockholm Convention",
            status=RegulationStatus.BANNED,
            effective_date=date(2009, 5, 22),
            description="Listed under Annex B (restriction)",
            source="COP-4 Decision SC-4/17",
        ),
        Regulation(
            jurisdiction="US",
            status=RegulationStatus.RESTRICTED,
            effective_date=date(2002, 1, 1),
            description="3M voluntary phase-out; EPA SNUR",
            source="EPA 40 CFR 721",
        ),
    ],
    common_uses=["Fire-fighting foam", "Metal plating", "Semiconductor etching"],
    notes="First PFAS banned internationally (Stockholm Convention 2009)",
)

PFAS_REGISTRY["PFHxS"] = PFASSubstance(
    name="Perfluorohexane sulfonic acid",
    abbreviation="PFHxS",
    cas_number="355-46-4",
    category=PFASCategory.PFSA,
    formula="C6HF13O3S",
    molecular_weight=400.12,
    regulations=[
        Regulation(
            jurisdiction="Stockholm Convention",
            status=RegulationStatus.BANNED,
            effective_date=date(2022, 6, 22),
            description="Listed under Annex A (elimination)",
            source="COP-10 Decision SC-10/13",
        ),
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2023, 12, 7),
            description="POPs Regulation amendment",
            source="Commission Delegated Regulation (EU) 2023/1608",
        ),
    ],
    common_uses=["Fire-fighting foam", "Textile treatment"],
    notes="C6 sulfonate; Stockholm Convention listed 2022",
)

PFAS_REGISTRY["PFHxA"] = PFASSubstance(
    name="Perfluorohexanoic acid",
    abbreviation="PFHxA",
    cas_number="307-24-4",
    category=PFASCategory.PFCA,
    formula="C6HF11O2",
    molecular_weight=314.05,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            effective_date=date(2026, 10, 1),
            description="EU-wide restriction on C6 PFCAs; 18-month transition for most uses",
            source="ECHA proposal RAC/SEAC opinions 2023",
        ),
    ],
    common_uses=["Textile treatment", "Food contact coatings", "Firefighting foam"],
    notes="Key driver for Phase 5: ban effective Oct 2026",
)

PFAS_REGISTRY["PFNA"] = PFASSubstance(
    name="Perfluorononanoic acid",
    abbreviation="PFNA",
    cas_number="375-95-1",
    category=PFASCategory.PFCA,
    formula="C9HF17O2",
    molecular_weight=464.08,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2023, 2, 25),
            description="REACH Annex XVII entry 68; restricted with PFOA-related substances",
            source="Regulation (EU) 2021/1297",
        ),
    ],
    common_uses=["Surfactant", "Processing aid"],
)

# ===== Replacement PFAS (GenX, ADONA) =====

PFAS_REGISTRY["GenX"] = PFASSubstance(
    name="Hexafluoropropylene oxide dimer acid",
    abbreviation="GenX",
    cas_number="13252-13-6",
    category=PFASCategory.PFCA,
    formula="C6HF11O3",
    molecular_weight=330.05,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.UNDER_REVIEW,
            description="SVHC candidate; universal PFAS restriction proposal covers GenX",
            source="ECHA SVHC identification 2019",
        ),
        Regulation(
            jurisdiction="US",
            status=RegulationStatus.RESTRICTED,
            effective_date=date(2024, 4, 10),
            description="EPA MCL of 10 ppt in drinking water",
            source="EPA NPDWR Final Rule 2024",
        ),
    ],
    common_uses=["PTFE/fluoropolymer processing aid (replacement for PFOA)"],
    notes="Chemours replacement for PFOA; itself under regulatory scrutiny",
)

PFAS_REGISTRY["ADONA"] = PFASSubstance(
    name="Ammonium 4,8-dioxa-3H-perfluorononanoate",
    abbreviation="ADONA",
    cas_number="958445-44-8",
    category=PFASCategory.PFCA,
    formula="C7H2F12NO4",
    molecular_weight=400.07,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.UNDER_REVIEW,
            description="Covered by universal PFAS restriction proposal",
            source="ECHA universal PFAS restriction 2023",
        ),
    ],
    common_uses=["Fluoropolymer processing aid (replacement for PFOA)"],
    notes="3M replacement processing aid for fluoropolymer production",
)

# ===== Fluoropolymers =====

PFAS_REGISTRY["PTFE"] = PFASSubstance(
    name="Polytetrafluoroethylene",
    abbreviation="PTFE",
    cas_number="9002-84-0",
    category=PFASCategory.FLUOROPOLYMER,
    formula="(C2F4)n",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Universal PFAS restriction includes fluoropolymers; "
                        "possible derogations for critical uses",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["Seals/gaskets", "Non-stick coatings", "Wire insulation",
                 "Battery binder", "Chemical-resistant lining"],
    notes="Most common fluoropolymer; PVDF-like PFAS status debated (polymer of low concern?)",
)

PFAS_REGISTRY["PVDF"] = PFASSubstance(
    name="Polyvinylidene fluoride",
    abbreviation="PVDF",
    cas_number="24937-79-9",
    category=PFASCategory.FLUOROPOLYMER,
    formula="(C2H2F2)n",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Universal PFAS restriction; battery sector seeking derogation",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["Battery binder", "Membrane (water treatment)", "Chemical-resistant piping",
                 "Piezoelectric sensors"],
    notes="Critical battery material; dominant cathode binder; PFAS status contentious",
)

PFAS_REGISTRY["FEP"] = PFASSubstance(
    name="Fluorinated ethylene propylene",
    abbreviation="FEP",
    cas_number="25067-11-2",
    category=PFASCategory.FLUOROPOLYMER,
    formula="(C2F4·C3F6)n",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Covered by universal PFAS restriction proposal",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["Wire insulation", "Chemical tubing", "Non-stick coatings"],
    notes="Melt-processable fluoropolymer; lower max temp than PTFE",
)

PFAS_REGISTRY["PFA"] = PFASSubstance(
    name="Perfluoroalkoxy alkane",
    abbreviation="PFA",
    cas_number="26655-00-5",
    category=PFASCategory.FLUOROPOLYMER,
    formula="(C2F4·C2F3·O·CnF2n+1)x",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Covered by universal PFAS restriction proposal",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["Semiconductor wafer carriers", "Chemical-resistant tubing",
                 "High-purity fluid handling"],
)

PFAS_REGISTRY["ETFE"] = PFASSubstance(
    name="Ethylene tetrafluoroethylene",
    abbreviation="ETFE",
    cas_number="25038-71-5",
    category=PFASCategory.FLUOROPOLYMER,
    formula="(C2H4·C2F4)n",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Covered by universal PFAS restriction proposal",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["Architectural film", "Wire insulation", "Chemical vessel lining"],
    notes="Partially fluorinated; better mechanical properties than PTFE",
)

PFAS_REGISTRY["PCTFE"] = PFASSubstance(
    name="Polychlorotrifluoroethylene",
    abbreviation="PCTFE",
    cas_number="9002-83-9",
    category=PFASCategory.FLUOROPOLYMER,
    formula="(C2ClF3)n",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Covered by universal PFAS restriction proposal",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["Pharmaceutical blister packs", "Cryogenic seals",
                 "Moisture barrier films"],
    notes="Excellent moisture barrier; niche applications",
)

PFAS_REGISTRY["Nafion"] = PFASSubstance(
    name="Nafion (perfluorosulfonic acid membrane)",
    abbreviation="Nafion",
    cas_number="31175-20-9",
    category=PFASCategory.FLUOROPOLYMER,
    formula="(C7HF13O5S·C2F4)n",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Universal PFAS restriction; seeking critical-use derogation for fuel cells",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["PEM fuel cell membrane", "Chlor-alkali electrolysis",
                 "Ion-selective electrode"],
    notes="Chemours/DuPont; critical for hydrogen economy; strong derogation case",
)

# ===== Short-chain PFAS =====

PFAS_REGISTRY["PFBS"] = PFASSubstance(
    name="Perfluorobutane sulfonic acid",
    abbreviation="PFBS",
    cas_number="375-73-5",
    category=PFASCategory.PFSA,
    formula="C4HF9O3S",
    molecular_weight=300.10,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.RESTRICTED,
            effective_date=date(2023, 8, 23),
            description="SVHC (equivalent level of concern — very persistent)",
            source="ECHA SVHC identification 2020",
        ),
    ],
    common_uses=["Textile treatment", "Paper coating"],
    notes="Short-chain C4 PFSA; proposed as PFOS replacement but itself restricted",
)

PFAS_REGISTRY["PFBA"] = PFASSubstance(
    name="Perfluorobutanoic acid",
    abbreviation="PFBA",
    cas_number="375-22-4",
    category=PFASCategory.PFCA,
    formula="C4HF7O2",
    molecular_weight=214.04,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.UNDER_REVIEW,
            description="Covered by universal PFAS restriction proposal",
            source="ECHA universal PFAS restriction 2023",
        ),
    ],
    common_uses=["Industrial surfactant"],
    notes="Shortest-chain PFCA of concern; very mobile in groundwater",
)

PFAS_REGISTRY["PFPeA"] = PFASSubstance(
    name="Perfluoropentanoic acid",
    abbreviation="PFPeA",
    cas_number="2706-90-3",
    category=PFASCategory.PFCA,
    formula="C5HF9O2",
    molecular_weight=264.04,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.UNDER_REVIEW,
            description="Covered by universal PFAS restriction proposal",
            source="ECHA universal PFAS restriction 2023",
        ),
    ],
    common_uses=["Processing aid", "Surfactant"],
)

# ===== Fluorotelomers =====

PFAS_REGISTRY["6:2 FTOH"] = PFASSubstance(
    name="6:2 Fluorotelomer alcohol",
    abbreviation="6:2 FTOH",
    cas_number="647-42-7",
    category=PFASCategory.FLUOROTELOMER,
    formula="C8H5F13O",
    molecular_weight=364.10,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            effective_date=date(2026, 10, 1),
            description="PFHxA restriction covers 6:2 fluorotelomer derivatives",
            source="ECHA PFHxA restriction proposal",
        ),
    ],
    common_uses=["Grease-proof paper coating", "Textile water repellent"],
    notes="Degrades to PFHxA in the environment; key precursor",
)

PFAS_REGISTRY["8:2 FTOH"] = PFASSubstance(
    name="8:2 Fluorotelomer alcohol",
    abbreviation="8:2 FTOH",
    cas_number="678-39-7",
    category=PFASCategory.FLUOROTELOMER,
    formula="C10H5F17O",
    molecular_weight=464.12,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2020, 7, 4),
            description="Restricted as PFOA-related substance",
            source="Regulation (EU) 2019/1021",
        ),
    ],
    common_uses=["Textile treatment", "Paper coating"],
    notes="Degrades to PFOA; banned with PFOA-related substances",
)

PFAS_REGISTRY["6:2 FTS"] = PFASSubstance(
    name="6:2 Fluorotelomer sulfonate",
    abbreviation="6:2 FTS",
    cas_number="27619-97-2",
    category=PFASCategory.FLUOROTELOMER,
    formula="C8H5F13O3S",
    molecular_weight=428.16,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Covered by universal PFAS restriction proposal",
            source="ECHA universal PFAS restriction 2023",
        ),
    ],
    common_uses=["AFFF firefighting foam component"],
    notes="Found in fluorine-free foam alternatives as contaminant",
)

# ===== Processing aids =====

PFAS_REGISTRY["APFO"] = PFASSubstance(
    name="Ammonium perfluorooctanoate",
    abbreviation="APFO",
    cas_number="3825-26-1",
    category=PFASCategory.PFAS_PRECURSOR,
    formula="C8H4F15NO2",
    molecular_weight=431.10,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2020, 7, 4),
            description="Banned as PFOA salt",
            source="Regulation (EU) 2019/1021",
        ),
    ],
    common_uses=["PTFE polymerization emulsifier", "Fluoropolymer processing aid"],
    notes="Ammonium salt of PFOA; was the primary PTFE production emulsifier",
)

PFAS_REGISTRY["PFDA"] = PFASSubstance(
    name="Perfluorodecanoic acid",
    abbreviation="PFDA",
    cas_number="335-76-2",
    category=PFASCategory.PFCA,
    formula="C10HF19O2",
    molecular_weight=514.09,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2023, 2, 25),
            description="Restricted as PFOA-related substance (C9-C14 PFCAs)",
            source="Regulation (EU) 2021/1297",
        ),
    ],
    common_uses=["Surfactant", "Processing aid"],
)

# ===== Industry-specific PFAS materials =====

PFAS_REGISTRY["PVDF-HFP"] = PFASSubstance(
    name="Polyvinylidene fluoride-hexafluoropropylene copolymer",
    abbreviation="PVDF-HFP",
    cas_number="9011-17-0",
    category=PFASCategory.FLUOROPOLYMER,
    formula="(C2H2F2·C3F6)n",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Covered by universal PFAS restriction as fluoropolymer",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["Gel polymer electrolyte", "Li-ion battery separator coating",
                 "Membrane (water treatment)"],
    notes="PVDF copolymer with improved electrolyte uptake; battery-critical",
)

PFAS_REGISTRY["Fluorosilicone"] = PFASSubstance(
    name="Fluorosilicone rubber",
    abbreviation="FVMQ",
    cas_number="63148-56-1",
    category=PFASCategory.SIDE_CHAIN_FLUORINATED,
    formula="Various",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.UNDER_REVIEW,
            description="May fall under universal PFAS restriction (side-chain fluorinated)",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["Aerospace seals", "Fuel system O-rings", "Automotive gaskets"],
    notes="Silicone backbone with fluorinated side groups; fuel/solvent resistant",
)

PFAS_REGISTRY["PFPE"] = PFASSubstance(
    name="Perfluoropolyether",
    abbreviation="PFPE",
    cas_number="69991-67-9",
    category=PFASCategory.FLUOROPOLYMER,
    formula="Various",
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            description="Covered by universal PFAS restriction as fluoropolymer",
            source="ECHA universal PFAS restriction proposal 2023",
        ),
    ],
    common_uses=["High-vacuum lubricant", "Aerospace lubricant",
                 "Hard disk drive lubricant"],
    notes="Liquid fluoropolymer used as specialty lubricant",
)

# ===== Additional substances to reach ~35 =====

PFAS_REGISTRY["PFUnDA"] = PFASSubstance(
    name="Perfluoroundecanoic acid",
    abbreviation="PFUnDA",
    cas_number="2058-94-8",
    category=PFASCategory.PFCA,
    formula="C11HF21O2",
    molecular_weight=564.09,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2023, 2, 25),
            description="Restricted as C9-C14 PFCA",
            source="Regulation (EU) 2021/1297",
        ),
    ],
    common_uses=["Industrial surfactant"],
)

PFAS_REGISTRY["PFDoDA"] = PFASSubstance(
    name="Perfluorododecanoic acid",
    abbreviation="PFDoDA",
    cas_number="307-55-1",
    category=PFASCategory.PFCA,
    formula="C12HF23O2",
    molecular_weight=614.10,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2023, 2, 25),
            description="Restricted as C9-C14 PFCA",
            source="Regulation (EU) 2021/1297",
        ),
    ],
    common_uses=["Industrial surfactant"],
)

PFAS_REGISTRY["PFTrDA"] = PFASSubstance(
    name="Perfluorotridecanoic acid",
    abbreviation="PFTrDA",
    cas_number="72629-94-8",
    category=PFASCategory.PFCA,
    formula="C13HF25O2",
    molecular_weight=664.11,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2023, 2, 25),
            description="Restricted as C9-C14 PFCA",
            source="Regulation (EU) 2021/1297",
        ),
    ],
    common_uses=["Industrial surfactant"],
)

PFAS_REGISTRY["PFTeDA"] = PFASSubstance(
    name="Perfluorotetradecanoic acid",
    abbreviation="PFTeDA",
    cas_number="376-06-7",
    category=PFASCategory.PFCA,
    formula="C14HF27O2",
    molecular_weight=714.12,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.BANNED,
            effective_date=date(2023, 2, 25),
            description="Restricted as C9-C14 PFCA",
            source="Regulation (EU) 2021/1297",
        ),
    ],
    common_uses=["Industrial surfactant"],
)

PFAS_REGISTRY["PFHpA"] = PFASSubstance(
    name="Perfluoroheptanoic acid",
    abbreviation="PFHpA",
    cas_number="375-85-9",
    category=PFASCategory.PFCA,
    formula="C7HF13O2",
    molecular_weight=364.06,
    regulations=[
        Regulation(
            jurisdiction="EU",
            status=RegulationStatus.PROPOSED_BAN,
            effective_date=date(2026, 10, 1),
            description="Covered by PFHxA restriction (C6 and related)",
            source="ECHA PFHxA restriction proposal",
        ),
    ],
    common_uses=["Surfactant"],
)


# ---------------------------------------------------------------------------
# Cross-reference: substances that exist in both PFAS registry and
# polymer_bridge/material_properties.py
# ---------------------------------------------------------------------------

POLYMER_BRIDGE_PFAS: Set[str] = {"PVDF", "PTFE"}


# ---------------------------------------------------------------------------
# Heuristic patterns for detecting potential PFAS not in registry
# ---------------------------------------------------------------------------

# NOTE: bare "fluoro" is intentionally NOT here — it matches mono/partially
# fluorinated non-PFAS (fluorobenzene, 5-fluorouracil, fluoxetine). Names with a
# generic "fluoro" fall through to the structural OECD path, which distinguishes
# them correctly. "perfluoro*" IS a reliable PFAS signal and is kept.
_PFAS_SUBSTRINGS = [
    # Chemical names / reliable PFAS prefixes and polymer abbreviations
    "perfluoro", "fluoropolymer", "ptfe", "pvdf", "fep", "pfa", "etfe", "pctfe",
    "nafion", "pfas", "pfoa", "pfos", "genx", "pfhxa", "pfbs",
    # Commercial brand names (all lowercase for matching)
    "teflon", "kynar", "viton", "dyneon", "solef", "hylar",
    "chemours", "fluorel", "tecnoflon", "kalrez", "fluorosilicone",
]

# Map commercial brands to base PFAS substance for replacement lookup
_BRAND_TO_BASE = {
    "kynar": "PVDF", "solef": "PVDF", "hylar": "PVDF",
    "teflon": "PTFE", "dyneon": "PTFE",
    "viton": "FKM", "fluorel": "FKM", "tecnoflon": "FKM", "kalrez": "FKM",
    "nafion": "Nafion",
}


def resolve_base_pfas(name: str) -> Optional[str]:
    """Try to resolve a commercial/heuristic name to a known PFAS base substance.

    Returns the registry key (e.g. 'PVDF') or None.
    """
    name_lower = name.lower()
    for brand, base in _BRAND_TO_BASE.items():
        if brand in name_lower:
            return base
    # Also check if any registry abbreviation is embedded
    for key, sub in PFAS_REGISTRY.items():
        if sub.abbreviation.lower() in name_lower:
            return key
    return None


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

def get_pfas(name: str) -> Optional[PFASSubstance]:
    """Look up a PFAS substance by name or abbreviation (case-insensitive)."""
    # Direct lookup
    if name in PFAS_REGISTRY:
        return PFAS_REGISTRY[name]
    # Case-insensitive search by abbreviation
    name_lower = name.lower()
    for key, sub in PFAS_REGISTRY.items():
        if key.lower() == name_lower or sub.abbreviation.lower() == name_lower:
            return sub
    # Search by full name
    for sub in PFAS_REGISTRY.values():
        if sub.name.lower() == name_lower:
            return sub
    return None


def smiles_is_pfas(smiles: str) -> bool:
    """Strict OECD 2021 structural test on a SMILES string.

    True if the molecule contains a fully fluorinated -CF2- or -CF3 carbon
    (no H, and not bonded to Cl/Br/I). Returns False for invalid/unparseable
    SMILES or when RDKit is unavailable.
    """
    if not _RDKIT_AVAILABLE:
        return False
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    return mol.HasSubstructMatch(_CF3_PATTERN) or mol.HasSubstructMatch(_CF2_PATTERN)


def matches_pfas_substring(name: str) -> bool:
    """Brand/keyword heuristic match (e.g. 'Kynar' -> PVDF)."""
    name_lower = name.lower()
    return any(pattern in name_lower for pattern in _PFAS_SUBSTRINGS)


def is_pfas(name: str) -> bool:
    """Check if a material name or SMILES is PFAS.

    Safe cascade: registry exact -> brand/keyword substring -> structural OECD
    rule on a valid SMILES. Registry/brand are checked first so a known material
    is never shadowed by a coincidental SMILES parse.
    """
    if get_pfas(name) is not None:
        return True
    if matches_pfas_substring(name):
        return True
    return smiles_is_pfas(name)

def get_pfas_by_category(category: PFASCategory) -> Dict[str, PFASSubstance]:
    """Get all PFAS substances of a given category."""
    return {
        k: v for k, v in PFAS_REGISTRY.items()
        if v.category == category
    }


def get_all_pfas_names() -> List[str]:
    """Get all registered PFAS substance names."""
    return sorted(PFAS_REGISTRY.keys())


def get_banned_pfas() -> Dict[str, PFASSubstance]:
    """Get all PFAS substances that are banned in any jurisdiction."""
    return {
        k: v for k, v in PFAS_REGISTRY.items()
        if v.is_banned()
    }


# ---------------------------------------------------------------------------
# Family Detection (SMARTS)
# ---------------------------------------------------------------------------

_FAMILY_PATTERNS = {}
if _RDKIT_AVAILABLE:
    _FAMILY_PATTERNS = {
        "Carboxylic Acid": Chem.MolFromSmarts("[CX3](=O)[OX2H1,OX1-0]"),
        "Sulfonic Acid": Chem.MolFromSmarts("S(=O)(=O)[OX2H1,OX1-0]"),
        "Sulfonamide": Chem.MolFromSmarts("S(=O)(=O)N"),
        "Ether": Chem.MolFromSmarts("[#6X4,c][OD2][#6X4,c]"),
        "Alcohol": Chem.MolFromSmarts("[OX2H1]"),
        "Amine": Chem.MolFromSmarts("[NX3;H2,H1,H0]"),
        "Amide": Chem.MolFromSmarts("[NX3][CX3](=[OX1])"),
        "Phosphonic Acid": Chem.MolFromSmarts("P(=O)(O)O"),
        "Ester": Chem.MolFromSmarts("[#6X3](=[OX1])O[#6X4]"),
    }

def get_pfas_family(smiles: str) -> str:
    """Identify chemical family from SMILES using functional group patterns."""
    if not _RDKIT_AVAILABLE or not smiles:
        return "Unknown"
    
    try:
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return "Invalid SMILES"
            
        for family, pattern in _FAMILY_PATTERNS.items():
            if mol.HasSubstructMatch(pattern):
                return family
                
        return "Other / Poly-fluorinated"
    except Exception:
        return "Error"


def get_restricted_pfas() -> Dict[str, PFASSubstance]:
    """Get all PFAS that are banned or restricted in any jurisdiction."""
    return {
        k: v for k, v in PFAS_REGISTRY.items()
        if v.is_restricted()
    }


def load_epa_registry(file_path: str = "data/EPA_PFASSTRUCTV4.txt") -> List[Dict]:
    """Load the massive EPA structural PFAS registry with families."""
    import os
    if not os.path.exists(file_path):
        return []
        
    results = []
    try:
        with open(file_path, "r") as f:
            # Skip header: Structure(SMILES) DTXSID FW
            header = f.readline()
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    smiles = parts[0]
                    # Parse FW, handle possible salt weight suffix like "434.9019 (427.9615+6.9405)"
                    fw_raw = parts[2] if len(parts) > 2 else None
                    fw = None
                    if fw_raw:
                        try:
                            fw = float(fw_raw.split()[0])
                        except (ValueError, IndexError):
                            pass
                            
                    results.append({
                        "smiles": smiles,
                        "id": parts[1],
                        "fw": fw,
                        "family": get_pfas_family(smiles)
                    })
    except Exception:
        pass
    return results

_EPA_REGISTRY_CACHE = None

def get_epa_registry() -> List[Dict]:
    """Get the EPA registry (cached)."""
    global _EPA_REGISTRY_CACHE
    if _EPA_REGISTRY_CACHE is None:
        _EPA_REGISTRY_CACHE = load_epa_registry()
    return _EPA_REGISTRY_CACHE


if __name__ == "__main__":
    print("=" * 70)
    print("PFAS Substance Registry")
    print("=" * 70)
    print(f"\nTotal substances: {len(PFAS_REGISTRY)}")
    for cat in PFASCategory:
        members = get_pfas_by_category(cat)
        if members:
            print(f"\n{cat.value} ({len(members)}):")
            for name, sub in members.items():
                status = "BANNED" if sub.is_banned() else (
                    "RESTRICTED" if sub.is_restricted() else sub.regulations[0].status.value if sub.regulations else "N/A"
                )
                print(f"  {name:12s}  CAS {sub.cas_number:15s}  [{status}]")
    print(f"\nPolymer bridge cross-reference: {POLYMER_BRIDGE_PFAS}")
