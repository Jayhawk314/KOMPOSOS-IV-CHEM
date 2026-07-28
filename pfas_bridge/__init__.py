# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
PFAS Compliance Module
=======================

Identifies PFAS substances, checks regulatory compliance, and scores
PFAS-free replacement candidates.

Main classes:
    PFASRegistry - curated registry of ~35 PFAS substances
    ReplacementScorer - use-case-specific replacement scoring
    PFASComplianceChecker - combined compliance engine
"""

from pfas_bridge.pfas_registry import (
    PFASCategory,
    PFASSubstance,
    Regulation,
    RegulationStatus,
    get_all_pfas_names,
    get_pfas,
    get_pfas_by_category,
    is_pfas,
    get_epa_registry,
    load_epa_registry,
    POLYMER_BRIDGE_PFAS,
    PFAS_REGISTRY,
)
from pfas_bridge.replacement_scorer import (
    ReplacementCandidate,
    UseCase,
    find_replacements,
    score_replacement,
)
from pfas_bridge.compliance_checker import (
    ComplianceResult,
    BatchComplianceResult,
    PFASComplianceChecker,
)
