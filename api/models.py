"""Pydantic request/response models for the KOMPOSOS-III Chemistry API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Compatibility
# ---------------------------------------------------------------------------

class CompatibilityRequest(BaseModel):
    """Two-material compatibility check."""
    material_a: str = Field(..., description="First material name (e.g. 'NMC811')")
    material_b: str = Field(..., description="Second material name (e.g. 'LLZO')")
    role: Optional[str] = Field(None, description="Application role for the interface")
    electrolyte: Optional[str] = Field(None, description="Electrolyte context, when applicable")
    voltage_context: Optional[str] = Field(None, description="Voltage context such as high_voltage_cathode")
    coating: Optional[str] = Field(None, description="Protective coating or interlayer")
    processing_route: Optional[str] = Field(None, description="Processing route for the interface")
    compatibilizer: Optional[str] = Field(None, description="Polymer blend compatibilizer, if any")
    interface_type: Optional[str] = Field(None, description="Interface type or assembly mode")
    environment: Optional[str] = Field(None, description="Operating environment")
    temperature_C: Optional[float] = Field(None, description="Operating temperature in Celsius")
    md_verify: bool = Field(False, description="Trigger Molecular Dynamics verification for high-stakes validation")
    md_conditions: Optional[Dict[str, Any]] = Field(None, description="Operating conditions for MD simulation")


class CompatibilityResponse(BaseModel):
    """Result of a two-material compatibility check."""
    material_a: str
    material_b: str
    domain: str
    scores: Dict[str, Any]
    viable: bool
    md_results: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Multi-domain
# ---------------------------------------------------------------------------

class ComponentInput(BaseModel):
    """A single component in a multi-domain query."""
    name: str = Field(..., description="Material name")
    role: str = Field("", description="Role (e.g. 'cathode', 'collector')")


class MultiDomainRequest(BaseModel):
    """Multi-domain material combination analysis."""
    name: str = Field(..., description="Query name")
    components: List[ComponentInput] = Field(
        ..., min_length=2, description="Components to analyze"
    )
    electrolyte: Optional[str] = Field(
        None, description="Electrolyte for battery-metal functor"
    )
    viability_threshold: float = Field(
        0.50, ge=0.0, le=1.0, description="Minimum viable score"
    )


class MultiDomainResponse(BaseModel):
    """Result of multi-domain analysis."""
    query_name: str
    components: List[Dict[str, str]]
    domains_involved: List[str]
    overall_score: float
    viable: bool
    bottleneck: Optional[str]
    cross_domain_scores: Dict[str, Any]
    warnings: List[str]


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

class SynthesisRequest(BaseModel):
    """Synthesis planning request."""
    target: str = Field(..., description="Target material (e.g. 'LFP')")
    budget_usd: Optional[float] = Field(
        None, ge=0, description="Budget in USD"
    )
    available_equipment: List[str] = Field(
        default_factory=list, description="Available equipment"
    )


class SynthesisResponse(BaseModel):
    """Result of synthesis planning."""
    target: str
    num_routes: int
    best_route: Optional[Dict[str, Any]]
    precursor_cost_usd: float
    total_time_hours: float
    equipment_needed: List[str]
    warnings: List[str]
    all_routes: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Materials listing
# ---------------------------------------------------------------------------

class MaterialInfo(BaseModel):
    """Summary info for a single material."""
    name: str
    domain: str
    material_class: str


class MaterialsListResponse(BaseModel):
    """All materials grouped by domain."""
    total: int
    domains: Dict[str, List[str]]


class DomainMaterialsResponse(BaseModel):
    """Materials for a single domain with property details."""
    domain: str
    count: int
    materials: Dict[str, Dict[str, Any]]


# ---------------------------------------------------------------------------
# ZFC Verification
# ---------------------------------------------------------------------------

class ZFCVerifyRequest(BaseModel):
    """ZFC constraint verification for a material pair."""
    material_a: str = Field(..., description="First material name")
    material_b: str = Field(..., description="Second material name")


class ZFCVerifyResponse(BaseModel):
    """ZFC verification result."""
    material_a: str
    material_b: str
    available: bool
    num_constraints: int
    constraints: List[Dict[str, Any]]
    has_vetoes: bool
    interface_viable: Optional[bool] = None


# ---------------------------------------------------------------------------
# Molecular
# ---------------------------------------------------------------------------

class MolecularCompatibilityRequest(BaseModel):
    """Two-molecule compatibility check."""
    molecule_a: str = Field(..., description="First molecule name")
    molecule_b: str = Field(..., description="Second molecule name")


class MolecularCompatibilityResponse(BaseModel):
    """Result of a two-molecule compatibility check."""
    molecule_a: str
    molecule_b: str
    scores: Dict[str, Any]
    viable: bool


class MoleculeListResponse(BaseModel):
    """All molecules grouped by class."""
    total: int
    classes: Dict[str, List[str]]


# ---------------------------------------------------------------------------
# PFAS
# ---------------------------------------------------------------------------

class PFASCheckRequest(BaseModel):
    """PFAS compliance check request."""
    material_name: str = Field(
        ..., description="Material or substance name to check"
    )


class PFASCheckResponse(BaseModel):
    """PFAS compliance check result."""
    material_name: str
    is_pfas: bool
    pfas_category: Optional[str] = None
    restricted_eu: bool = False
    restricted_us: bool = False
    restriction_date: Optional[str] = None
    alternatives: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PFASSubstanceListResponse(BaseModel):
    """List of PFAS substances."""
    total: int
    categories: Dict[str, List[str]]


class PFASAlternativesRequest(BaseModel):
    """Request for PFAS replacement alternatives."""
    material_name: str = Field(
        ..., description="PFAS substance name (e.g. 'PVDF')"
    )
    use_case: Optional[str] = Field(
        None,
        description="Application context: battery_binder, seal_gasket, membrane, "
                    "wire_insulation, non_stick_coating, chemical_resistant_liner, general",
    )


class PFASAlternativesResponse(BaseModel):
    """PFAS replacement alternatives result."""
    material_name: str
    use_case: str
    num_alternatives: int
    alternatives: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Composition Designer (Inverse Design)
# ---------------------------------------------------------------------------

class PropertyTargetInput(BaseModel):
    """A single target property for inverse design."""
    name: str = Field(..., description="Property name (e.g. 'voltage', 'thermal_stability')")
    min_value: Optional[float] = Field(None, description="Minimum acceptable value")
    max_value: Optional[float] = Field(None, description="Maximum acceptable value")
    weight: float = Field(1.0, ge=0.0, le=1.0, description="Importance weight")


class ElementConstraintInput(BaseModel):
    """Constraints on which elements may appear."""
    required_elements: List[str] = Field(
        default_factory=list, description="Elements that must be present"
    )
    excluded_elements: List[str] = Field(
        default_factory=list, description="Elements that must not be present"
    )
    max_elements: Optional[int] = Field(
        None, ge=1, description="Maximum number of distinct elements"
    )


class DesignRequest(BaseModel):
    """Inverse composition design request."""
    targets: List[PropertyTargetInput] = Field(
        ..., min_length=1, description="Target properties with acceptable ranges"
    )
    element_constraints: Optional[ElementConstraintInput] = Field(
        None, description="Element inclusion/exclusion constraints"
    )
    min_synthesizability: float = Field(
        0.0, ge=0.0, le=1.0, description="Minimum synthesizability score"
    )
    require_stable: bool = Field(
        False, description="Require negative formation energy"
    )
    pfas_free: bool = Field(
        False, description="Exclude PFAS-containing compositions"
    )
    domain: Optional[str] = Field(
        None, description="Restrict search to a domain (battery, ceramic, semiconductor)"
    )
    max_candidates: int = Field(
        500, ge=10, le=5000, description="Maximum candidates to evaluate"
    )


class DesignCandidateOutput(BaseModel):
    """A single design candidate."""
    formula: str
    composition: Dict[str, float]
    overall_score: float
    target_scores: Dict[str, float]
    targets_met: List[str]
    targets_missed: List[str]
    predicted_properties: Dict[str, float]
    strategy: str
    anchor: Optional[str] = None
    synthesizability: float = 0.0
    formation_energy: Optional[float] = None
    structure_type: Optional[str] = None
    confidence: float = 0.0


class DesignResponse(BaseModel):
    """Inverse design search result."""
    num_candidates: int
    num_evaluated: int
    elapsed_seconds: float
    strategies_used: List[str]
    candidates: List[DesignCandidateOutput]


# ---------------------------------------------------------------------------
# PFAS Compliance Report
# ---------------------------------------------------------------------------

class PFASReportMaterialInput(BaseModel):
    """A single material for PFAS portfolio screening."""
    name: str = Field(..., description="Material name (e.g. 'PVDF')")
    cas_number: Optional[str] = Field(None, description="CAS registry number")
    function: Optional[str] = Field(None, description="Function in product (e.g. 'cathode binder')")
    quantity_kg: Optional[float] = Field(None, ge=0, description="Quantity in kg")


class PFASReportRequest(BaseModel):
    """Request for full PFAS compliance report."""
    materials: List[PFASReportMaterialInput] = Field(
        ..., min_length=1, description="Materials to screen"
    )
    use_demo_bom: bool = Field(
        False, description="Ignore materials list and use built-in Li-Ion demo BOM"
    )


class PFASReportResponse(BaseModel):
    """Structured PFAS compliance report."""
    report_id: str
    summary: Dict[str, Any]
    detections: List[Dict[str, Any]]
    clean_materials: List[Dict[str, Any]]
    regulatory_timeline: List[Dict[str, Any]]
    action_plan: List[Dict[str, Any]]
    methodology: Dict[str, Any]
    audit_certificate: Dict[str, Any]


# ---------------------------------------------------------------------------
# Molecule Constraint Search
# ---------------------------------------------------------------------------

class MoleculeSearchRequest(BaseModel):
    """Constraint-based molecule search (Kulik 22-atom challenge)."""
    heavy_atom_count: Optional[int] = Field(
        None, ge=0, description="Exact number of non-hydrogen atoms"
    )
    heavy_atom_range: Optional[List[int]] = Field(
        None, min_length=2, max_length=2,
        description="Inclusive [min, max] range of heavy atom count"
    )
    functional_groups: Optional[List[str]] = Field(
        None, description="Must contain ALL listed functional groups (AND logic)"
    )
    molecular_weight_range: Optional[List[float]] = Field(
        None, min_length=2, max_length=2,
        description="Inclusive [min, max] molecular weight range in g/mol"
    )
    exclude_elements: Optional[List[str]] = Field(
        None, description="Exclude molecules containing any of these elements"
    )
    include_elements: Optional[List[str]] = Field(
        None, description="Molecules must contain ALL of these elements"
    )
    molecule_class: Optional[str] = Field(
        None, description="Filter by class: electrolyte_solvent, salt_anion, polymer_monomer, reagent, coating, gas"
    )


class MoleculeSearchResult(BaseModel):
    """A molecule matching the search constraints."""
    name: str
    formula: str
    molecular_weight: float
    heavy_atom_count: int
    molecule_class: str
    functional_groups: List[str]


class MoleculeSearchResponse(BaseModel):
    """Result of constraint-based molecule search."""
    num_results: int
    constraints_applied: List[str]
    results: List[MoleculeSearchResult]


# ---------------------------------------------------------------------------
# MOF Linker Designer (Inverse Design)
# ---------------------------------------------------------------------------

class MOFLinkerDesignRequest(BaseModel):
    """Novel 22-atom MOF linker generation request."""
    application_context: str = Field(
        ...,
        description="Target application: breath_VOC_sensing, food_safety, PFAS_detection, custom"
    )
    num_candidates: int = Field(
        100, ge=10, le=1000,
        description="Number of candidates to generate"
    )
    require_all_agree: bool = Field(
        True,
        description="Only return candidates with all 5 verdicts == AGREE"
    )
    allow_hollow: bool = Field(
        False,
        description="Include HOLLOW verdicts (exploratory mode)"
    )
    functional_groups: Optional[List[str]] = Field(
        None,
        description="Preferred functional groups to include"
    )
    exclude_elements: Optional[List[str]] = Field(
        None,
        description="Elements to exclude (e.g. ['F', 'Cl'])"
    )
    ranking_mode: str = Field(
        "morphism_integrity",
        pattern="^(morphism_integrity|verdict_count)$",
        description="Ranking method: morphism_integrity or verdict_count"
    )


class MOFLinkerCandidateOutput(BaseModel):
    """A single MOF linker candidate with verdicts."""
    smiles: str
    formula: str = ""
    molecular_weight: float = 0.0
    verdicts: Dict[str, str]           # verdict_name → AGREE/HOLLOW/ORPHAN/REJECT
    verdict_scores: Dict[str, float]   # verdict_name → confidence (0-1)
    morphism_integrity: float
    reasoning_traces: Dict[str, str]
    overall_viable: bool


class MOFLinkerDesignResponse(BaseModel):
    """Result of MOF linker inverse design."""
    num_generated: int
    num_passed_all: int                # All verdicts == AGREE
    candidates: List[MOFLinkerCandidateOutput]
    avg_morphism_integrity: float
    best_morphism_integrity: float
    generation_time_sec: float
