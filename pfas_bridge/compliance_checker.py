"""
PFAS Compliance Checker
========================

Main compliance engine combining the PFAS registry and replacement scorer.
Provides single-material checks, batch BOM screening, and alternative
suggestions with deadline-aware urgency levels.

Urgency levels:
    critical  — substance is BANNED
    high      — ban/restriction effective within 12 months
    moderate  — RESTRICTED or PROPOSED_BAN (>12 months out)
    low       — UNDER_REVIEW
    none      — not PFAS or not restricted
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from pfas_bridge.pfas_registry import (
    PFASSubstance,
    RegulationStatus,
    get_pfas,
    is_pfas,
    matches_pfas_substring,
    resolve_base_pfas,
    smiles_is_pfas,
)
from pfas_bridge.replacement_scorer import (
    ReplacementCandidate,
    UseCase,
    find_replacements,
)


@dataclass
class ComplianceResult:
    """Result of a single-material PFAS compliance check."""
    material_name: str
    is_pfas: bool
    pfas_substance: Optional[PFASSubstance] = None
    pfas_category: Optional[str] = None
    regulations_violated: List[Dict] = field(default_factory=list)
    urgency: str = "none"    # critical / high / moderate / low / none
    replacements: List[ReplacementCandidate] = field(default_factory=list)
    heuristic_match: bool = False   # True if detected by substring, not registry
    detection_tier: str = "unknown"  # exact / heuristic / structural / structural_resolved / unknown
    resolved_base: Optional[str] = None  # Base substance for heuristic matches
    resolved_smiles: Optional[str] = None  # SMILES used for a structural match

    def to_dict(self) -> Dict:
        result = {
            "material_name": self.material_name,
            "is_pfas": self.is_pfas,
            "pfas_category": self.pfas_category,
            "urgency": self.urgency,
            "heuristic_match": self.heuristic_match,
            "detection_tier": self.detection_tier,
            "regulations_violated": self.regulations_violated,
            "replacements": [r.to_dict() for r in self.replacements],
        }
        if self.pfas_substance:
            result["pfas_name"] = self.pfas_substance.name
            result["cas_number"] = self.pfas_substance.cas_number
        if self.resolved_base:
            result["resolved_base"] = self.resolved_base
        if self.resolved_smiles:
            result["resolved_smiles"] = self.resolved_smiles
        return result


@dataclass
class BatchComplianceResult:
    """Result of checking a product's bill of materials."""
    materials: List[ComplianceResult]

    @property
    def has_pfas(self) -> bool:
        return any(r.is_pfas for r in self.materials)

    @property
    def max_urgency(self) -> str:
        """Highest urgency across all materials."""
        priority = {"critical": 4, "high": 3, "moderate": 2, "low": 1, "none": 0}
        best = max(self.materials, key=lambda r: priority.get(r.urgency, 0))
        return best.urgency

    @property
    def pfas_count(self) -> int:
        return sum(1 for r in self.materials if r.is_pfas)

    def to_dict(self) -> Dict:
        return {
            "has_pfas": self.has_pfas,
            "pfas_count": self.pfas_count,
            "max_urgency": self.max_urgency,
            "materials": [r.to_dict() for r in self.materials],
        }


class PFASComplianceChecker:
    """
    Main compliance checker combining registry lookup, urgency
    assessment, and replacement suggestions.
    """

    def __init__(self, reference_date: Optional[date] = None, resolve_unknown: bool = True):
        """
        Args:
            reference_date: Date to use for deadline calculations.
                          Defaults to today.
            resolve_unknown: If True, unknown names are resolved to a SMILES via
                          PubChem (cached, best-effort) so the OECD structural
                          rule can catch novel PFAS not in the registry.
        """
        self.reference_date = reference_date or date.today()
        self.resolve_unknown = resolve_unknown
        self._pubchem = None  # lazy PubChemLoader

    def _resolve_to_smiles(self, name: str) -> Optional[str]:
        """Best-effort name -> SMILES via PubChem (cached). None on any failure."""
        if not self.resolve_unknown:
            return None
        try:
            from data.pubchem_loader import PubChemLoader
            if self._pubchem is None:
                self._pubchem = PubChemLoader()
            mol = self._pubchem.fetch_by_name(name, fetch_cas=False)
            return mol.smiles or None
        except Exception:
            return None  # no network / not found / loader unavailable

    def _structural_result(self, material_name: str, smiles: str, tier: str) -> "ComplianceResult":
        """Build a result for a structurally-detected PFAS (not in the registry)."""
        return ComplianceResult(
            material_name=material_name,
            is_pfas=True,
            pfas_substance=None,
            pfas_category="unknown_fluorinated (OECD structural match)",
            regulations_violated=[],
            urgency="moderate",
            replacements=[],
            heuristic_match=False,
            detection_tier=tier,
            resolved_smiles=smiles,
        )

    def check(
        self,
        material_name: str,
        use_case: UseCase = UseCase.GENERAL,
    ) -> ComplianceResult:
        """
        Check a single material for PFAS compliance.

        Args:
            material_name: Material or substance name to check.
            use_case: Application context for replacement scoring.

        Returns:
            ComplianceResult with PFAS status, urgency, and replacements.
        """
        substance = get_pfas(material_name)

        if substance is not None:
            # Known PFAS substance -- exact match
            regulations_violated = self._get_violations(substance)
            urgency = self._compute_urgency(substance)
            replacements = find_replacements(substance.abbreviation, use_case)

            return ComplianceResult(
                material_name=material_name,
                is_pfas=True,
                pfas_substance=substance,
                pfas_category=substance.category.value,
                regulations_violated=regulations_violated,
                urgency=urgency,
                replacements=replacements,
                heuristic_match=False,
                detection_tier="exact",
            )

        # Check heuristic detection (brand names, substrings)
        if matches_pfas_substring(material_name):
            # Try to resolve to a known base substance for replacements
            base_name = resolve_base_pfas(material_name)
            base_substance = get_pfas(base_name) if base_name else None
            replacements = []
            category = "unknown_fluorinated"
            urgency = "moderate"
            regulations_violated = []

            if base_substance is not None:
                category = base_substance.category.value
                urgency = self._compute_urgency(base_substance)
                regulations_violated = self._get_violations(base_substance)
                replacements = find_replacements(
                    base_substance.abbreviation, use_case
                )

            return ComplianceResult(
                material_name=material_name,
                is_pfas=True,
                pfas_substance=base_substance,
                pfas_category=category,
                regulations_violated=regulations_violated,
                urgency=urgency,
                replacements=replacements,
                heuristic_match=True,
                detection_tier="heuristic",
                resolved_base=base_name,
            )

        # Structural OECD rule on direct SMILES input
        if smiles_is_pfas(material_name):
            return self._structural_result(material_name, material_name, "structural")

        # Resolve an unknown name to a SMILES (PubChem) and apply the OECD rule.
        # This is what lets the scanner catch a NOVEL PFAS not in the registry.
        resolved = self._resolve_to_smiles(material_name)
        if resolved and smiles_is_pfas(resolved):
            return self._structural_result(material_name, resolved, "structural_resolved")

        # Not PFAS (or unresolvable -> manual review)
        return ComplianceResult(
            material_name=material_name,
            is_pfas=False,
            urgency="none",
            detection_tier="unknown",
            resolved_smiles=resolved,
        )

    def check_batch(
        self,
        material_names: List[str],
        use_case: UseCase = UseCase.GENERAL,
    ) -> BatchComplianceResult:
        """
        Check a list of materials (product BOM) for PFAS compliance.

        Args:
            material_names: List of material names to check.
            use_case: Application context for replacement scoring.

        Returns:
            BatchComplianceResult with per-material results.
        """
        results = [self.check(name, use_case) for name in material_names]
        return BatchComplianceResult(materials=results)

    def suggest_alternatives(
        self,
        material_name: str,
        use_case: UseCase = UseCase.GENERAL,
    ) -> List[ReplacementCandidate]:
        """
        Get replacement candidates for a PFAS material.

        Args:
            material_name: PFAS substance name.
            use_case: Application context.

        Returns:
            Sorted list of ReplacementCandidate objects.
        """
        substance = get_pfas(material_name)
        if substance is None:
            return []
        return find_replacements(substance.abbreviation, use_case)

    def _get_violations(self, substance: PFASSubstance) -> List[Dict]:
        """Extract active regulation violations."""
        violations = []
        for reg in substance.regulations:
            if reg.status in (
                RegulationStatus.BANNED,
                RegulationStatus.RESTRICTED,
                RegulationStatus.PROPOSED_BAN,
            ):
                violations.append({
                    "jurisdiction": reg.jurisdiction,
                    "status": reg.status.value,
                    "effective_date": (
                        reg.effective_date.isoformat() if reg.effective_date else None
                    ),
                    "description": reg.description,
                })
        return violations

    def _compute_urgency(self, substance: PFASSubstance) -> str:
        """
        Compute urgency level based on regulatory status and deadlines.

        Logic:
            BANNED -> critical
            Ban/restriction effective within 12 months -> high
            RESTRICTED or PROPOSED_BAN (>12 months) -> moderate
            UNDER_REVIEW -> low
            Otherwise -> none
        """
        has_banned = False
        has_restricted = False
        has_proposed = False
        has_review = False
        nearest_deadline = None

        for reg in substance.regulations:
            if reg.status == RegulationStatus.BANNED:
                has_banned = True
            elif reg.status == RegulationStatus.RESTRICTED:
                has_restricted = True
            elif reg.status == RegulationStatus.PROPOSED_BAN:
                has_proposed = True
                if reg.effective_date is not None:
                    if nearest_deadline is None or reg.effective_date < nearest_deadline:
                        nearest_deadline = reg.effective_date
            elif reg.status == RegulationStatus.UNDER_REVIEW:
                has_review = True

        if has_banned:
            return "critical"

        # Check if a proposed ban is imminent (within 12 months)
        if nearest_deadline is not None:
            days_until = (nearest_deadline - self.reference_date).days
            if days_until <= 365:
                return "high"

        if has_restricted or has_proposed:
            return "moderate"

        if has_review:
            return "low"

        return "none"


if __name__ == "__main__":
    checker = PFASComplianceChecker()

    print("=" * 70)
    print("PFAS Compliance Checker Demo")
    print("=" * 70)

    test_materials = ["PVDF", "PTFE", "PFOA", "HDPE", "PFHxA", "CMC", "Fluorosilicone"]
    for mat in test_materials:
        result = checker.check(mat, UseCase.BATTERY_BINDER)
        print(f"\n{mat}:")
        print(f"  PFAS: {result.is_pfas}")
        print(f"  Urgency: {result.urgency}")
        if result.regulations_violated:
            print(f"  Violations: {len(result.regulations_violated)}")
        if result.replacements:
            print(f"  Replacements: {len(result.replacements)}")
            for r in result.replacements[:3]:
                print(f"    {r.name}: score={r.overall_score:.3f}")
