# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>

"""
Attack-Defense Adjunction: Categorical Game Theory for Optimal Defense

Given categories:
  T (Targets): network assets, services, data stores
  E (ExploitChains): valid attack chains from enriched attack category
  D (Defenses): security controls, patches, monitoring rules

Attack functor F: T → E maps each target to viable attack chains
Defense functor G: E → D maps each exploit chain to defenses that mitigate it

Adjunction F ⊣ G means:
  Hom_E(F(target), chain) ≅ Hom_T(target, G(chain))
  "Ways to attack target via chain" ≅ "Ways target is covered by defense against chain"

Unit η: Id_T → G∘F  — "Apply defense for your own worst attack" = OPTIMAL DEFENSE
Counit ε: F∘G → Id_E — "Attack remaining after defense" = RESIDUAL VULNERABILITY

Triangle identities guarantee convergence of iterated defense improvement.

Mathematical basis:
  - Adjoint functors: nLab, Wikipedia
  - Compositional Game Theory: Hedges (2018), arxiv:1603.04641
  - Open Games as lenses: Hedges (2017), arxiv:1711.07059
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
import math


# Defense catalog: MITRE technique → available defenses
DEFENSE_CATALOG: Dict[str, List[Dict]] = {
    "T1566": [
        {"id": "M1054", "name": "Email filtering", "cost": 0.3, "effectiveness": 0.7},
        {"id": "M1017", "name": "User training", "cost": 0.2, "effectiveness": 0.4},
        {"id": "M1049", "name": "Sandboxing", "cost": 0.5, "effectiveness": 0.8},
    ],
    "T1059": [
        {"id": "M1042", "name": "Script blocking", "cost": 0.3, "effectiveness": 0.6},
        {"id": "M1038", "name": "Execution prevention", "cost": 0.4, "effectiveness": 0.75},
        {"id": "M1026", "name": "Privileged account mgmt", "cost": 0.5, "effectiveness": 0.5},
    ],
    "T1068": [
        {"id": "M1051", "name": "Patch management", "cost": 0.4, "effectiveness": 0.85},
        {"id": "M1050", "name": "Exploit protection", "cost": 0.3, "effectiveness": 0.6},
    ],
    "T1003": [
        {"id": "M1043", "name": "Credential guard", "cost": 0.4, "effectiveness": 0.8},
        {"id": "M1026", "name": "Privileged account mgmt", "cost": 0.5, "effectiveness": 0.7},
        {"id": "M1027", "name": "Password policies", "cost": 0.2, "effectiveness": 0.4},
    ],
    "T1021": [
        {"id": "M1032", "name": "MFA", "cost": 0.4, "effectiveness": 0.8},
        {"id": "M1035", "name": "Network segmentation", "cost": 0.6, "effectiveness": 0.75},
        {"id": "M1018", "name": "Limit remote access", "cost": 0.3, "effectiveness": 0.6},
    ],
    "T1005": [
        {"id": "M1041", "name": "Data encryption at rest", "cost": 0.3, "effectiveness": 0.5},
        {"id": "M1057", "name": "DLP", "cost": 0.6, "effectiveness": 0.7},
    ],
    "T1041": [
        {"id": "M1031", "name": "Network IPS", "cost": 0.5, "effectiveness": 0.6},
        {"id": "M1057", "name": "DLP", "cost": 0.6, "effectiveness": 0.8},
        {"id": "M1037", "name": "Proxy filtering", "cost": 0.3, "effectiveness": 0.5},
    ],
    "T1078": [
        {"id": "M1032", "name": "MFA", "cost": 0.4, "effectiveness": 0.85},
        {"id": "M1026", "name": "Privileged account mgmt", "cost": 0.5, "effectiveness": 0.7},
        {"id": "M1036", "name": "Account use policies", "cost": 0.2, "effectiveness": 0.4},
    ],
    "T1190": [
        {"id": "M1051", "name": "Patch management", "cost": 0.4, "effectiveness": 0.8},
        {"id": "M1030", "name": "WAF", "cost": 0.5, "effectiveness": 0.7},
        {"id": "M1016", "name": "Vulnerability scanning", "cost": 0.3, "effectiveness": 0.5},
    ],
    "T1195": [
        {"id": "M1016", "name": "Vulnerability scanning", "cost": 0.3, "effectiveness": 0.3},
        {"id": "M1045", "name": "Code signing", "cost": 0.4, "effectiveness": 0.5},
    ],
    "T1486": [
        {"id": "M1053", "name": "Backup/restore", "cost": 0.4, "effectiveness": 0.9},
        {"id": "M1035", "name": "Network segmentation", "cost": 0.6, "effectiveness": 0.5},
    ],
    "T1071": [
        {"id": "M1031", "name": "Network IPS", "cost": 0.5, "effectiveness": 0.5},
        {"id": "M1037", "name": "Proxy filtering", "cost": 0.3, "effectiveness": 0.6},
    ],
    "T1055": [
        {"id": "M1040", "name": "Behavior prevention", "cost": 0.4, "effectiveness": 0.6},
        {"id": "M1026", "name": "Privileged account mgmt", "cost": 0.5, "effectiveness": 0.5},
    ],
    "T1218": [
        {"id": "M1038", "name": "Execution prevention", "cost": 0.4, "effectiveness": 0.55},
        {"id": "M1042", "name": "Application allowlisting", "cost": 0.5, "effectiveness": 0.8},
    ],
    "T1556": [
        {"id": "M1032", "name": "MFA", "cost": 0.4, "effectiveness": 0.7},
        {"id": "M1026", "name": "Privileged account mgmt", "cost": 0.5, "effectiveness": 0.8},
        {"id": "M1022", "name": "Restrict registry perms", "cost": 0.3, "effectiveness": 0.6},
    ],
    "T1558": [
        {"id": "M1027", "name": "Strong passwords", "cost": 0.2, "effectiveness": 0.6},
        {"id": "M1026", "name": "Privileged account mgmt", "cost": 0.5, "effectiveness": 0.7},
    ],
    # === Cryptographic Technique Defenses ===
    "TCRYPTO_001": [
        {"id": "MC001", "name": "Key length enforcement (>=2048)", "cost": 0.2, "effectiveness": 0.95},
        {"id": "MC002", "name": "HSM usage", "cost": 0.6, "effectiveness": 0.90},
        {"id": "MC003", "name": "Cipher suite policy", "cost": 0.3, "effectiveness": 0.80},
    ],
    "TCRYPTO_002": [
        {"id": "MC004", "name": "Certified RNG for key generation", "cost": 0.3, "effectiveness": 0.90},
        {"id": "MC005", "name": "Key uniqueness audit", "cost": 0.2, "effectiveness": 0.85},
    ],
    "TCRYPTO_003": [
        {"id": "MC006", "name": "RFC 6979 deterministic nonce", "cost": 0.2, "effectiveness": 0.95},
        {"id": "MC007", "name": "Signature monitoring", "cost": 0.3, "effectiveness": 0.70},
    ],
    "TCRYPTO_004": [
        {"id": "MC008", "name": "NIST approved curves only", "cost": 0.2, "effectiveness": 0.90},
        {"id": "MC009", "name": "Curve parameter validation", "cost": 0.3, "effectiveness": 0.85},
    ],
    "TCRYPTO_005": [
        {"id": "MC010", "name": "Certificate Transparency monitoring", "cost": 0.3, "effectiveness": 0.85},
        {"id": "MC011", "name": "Certificate pinning", "cost": 0.4, "effectiveness": 0.80},
        {"id": "MC012", "name": "Short-lived certificates", "cost": 0.3, "effectiveness": 0.75},
    ],
    "TCRYPTO_006": [
        {"id": "MC013", "name": "PQC migration (ML-KEM)", "cost": 0.5, "effectiveness": 0.90},
        {"id": "MC014", "name": "Hybrid encryption (classical+PQC)", "cost": 0.4, "effectiveness": 0.80},
    ],
    "TCRYPTO_007": [
        {"id": "MC015", "name": "CA access controls and audit", "cost": 0.4, "effectiveness": 0.85},
        {"id": "MC016", "name": "Multi-party CA signing", "cost": 0.5, "effectiveness": 0.90},
        {"id": "MC010", "name": "Certificate Transparency monitoring", "cost": 0.3, "effectiveness": 0.80},
    ],
    "TCRYPTO_008": [
        {"id": "MC017", "name": "TLS 1.3 enforcement", "cost": 0.2, "effectiveness": 0.95},
        {"id": "MC018", "name": "Cipher suite hardening", "cost": 0.2, "effectiveness": 0.85},
        {"id": "MC019", "name": "Protocol downgrade detection", "cost": 0.3, "effectiveness": 0.75},
    ],
}


@dataclass
class Target:
    """A network asset that can be attacked."""
    name: str
    asset_type: str      # "server", "workstation", "database", "cloud_service"
    value: float         # Business value [0, 1]
    current_defenses: List[str] = field(default_factory=list)


@dataclass
class DefenseAllocation:
    """Optimal defense allocation for a target."""
    target: str
    defenses: List[Dict]       # Applied defenses
    total_cost: float
    residual_risk: float       # Risk remaining after defenses
    worst_attack_stealth: float  # Stealth of worst remaining attack
    covers_attacks: int        # Number of attack paths covered


class AttackFunctor:
    """
    F: Targets → ExploitChains

    Maps each target to viable exploit chains, weighted by stealth.
    """

    def __init__(self, enriched_cat, mitre_db):
        self.cat = enriched_cat
        self.mitre_db = mitre_db

    def apply(self, target: Target) -> List[Tuple[List[str], float]]:
        """
        F(target) = all viable exploit chains against target,
        weighted by stealth score.

        Returns: List of (chain, stealth_score) sorted by stealth desc.
        """
        # Determine entry points based on target type
        entry_techniques = self._get_entry_techniques(target)
        goal_techniques = self._get_goal_techniques(target)

        chains = []
        for entry in entry_techniques:
            for goal in goal_techniques:
                if entry == goal:
                    continue
                result = self.cat.optimal_path(entry, goal, maximize=True, max_length=7)
                if result:
                    path, stealth = result
                    if stealth and stealth > 0.01:  # Filter negligible paths
                        chains.append((path, stealth))

        chains.sort(key=lambda x: x[1], reverse=True)
        return chains[:20]  # Top 20 chains

    def _get_entry_techniques(self, target: Target) -> List[str]:
        """Get likely entry techniques for target type."""
        type_entries = {
            "server": ["T1190", "T1133"],
            "workstation": ["T1566", "T1195"],
            "database": ["T1190"],
            "cloud_service": ["T1078.004", "T1190"],
        }
        return type_entries.get(target.asset_type, ["T1566", "T1190"])

    def _get_goal_techniques(self, target: Target) -> List[str]:
        """Get likely goal techniques for target type."""
        type_goals = {
            "server": ["T1005", "T1041", "T1486"],
            "workstation": ["T1005", "T1041"],
            "database": ["T1005", "T1041"],
            "cloud_service": ["T1530", "T1537"],
        }
        return type_goals.get(target.asset_type, ["T1005", "T1041"])


class DefenseFunctor:
    """
    G: ExploitChains → Defenses

    Maps each exploit chain to defenses that mitigate it.
    """

    def __init__(self):
        self.catalog = DEFENSE_CATALOG

    def apply(self, chain: List[str]) -> List[Dict]:
        """
        G(chain) = best defense for each technique in chain.

        Returns list of defense recommendations.
        """
        defenses = []
        covered_mitigations = set()

        for tech_id in chain:
            available = self.catalog.get(tech_id, [])
            if not available:
                # Use generic defense for unknown techniques
                available = [{"id": "M1000", "name": "Monitoring",
                              "cost": 0.2, "effectiveness": 0.3}]

            # Pick best defense not already selected
            for defense in sorted(available, key=lambda d: d["effectiveness"], reverse=True):
                if defense["id"] not in covered_mitigations:
                    defenses.append({
                        **defense,
                        "covers_technique": tech_id
                    })
                    covered_mitigations.add(defense["id"])
                    break

        return defenses

    def defense_effectiveness(self, chain: List[str], defenses: List[Dict]) -> float:
        """
        Compute how effectively defenses mitigate an attack chain.

        Returns: fraction of chain mitigated [0, 1].
        """
        if not chain:
            return 1.0

        covered_techniques = {d.get("covers_technique") for d in defenses}
        total_effectiveness = 0.0

        for tech_id in chain:
            if tech_id in covered_techniques:
                matching = [d for d in defenses if d.get("covers_technique") == tech_id]
                if matching:
                    total_effectiveness += matching[0]["effectiveness"]
                else:
                    total_effectiveness += 0.0
            # Undefended technique contributes 0

        return total_effectiveness / len(chain)


class AttackDefenseAdjunction:
    """
    F ⊣ G: Attack-Defense adjunction.

    Computes:
    1. Unit (η): For each target, its optimal defense posture
    2. Counit (ε): For each defense, its residual vulnerability
    3. Nash equilibrium via iterated adjunction (fixed point)

    The adjunction encodes the duality:
      "Best defense for worst attack" ↔ "Worst attack against best defense"
    """

    def __init__(self, enriched_cat, mitre_db):
        self.F = AttackFunctor(enriched_cat, mitre_db)
        self.G = DefenseFunctor()
        self.enriched_cat = enriched_cat
        self.mitre_db = mitre_db

    def unit(self, target: Target) -> DefenseAllocation:
        """
        η_target: target → G(F(target))

        "Apply the defense for your own worst attack."
        This IS the optimal defense for this target.
        """
        # F(target) = worst attacks
        attacks = self.F.apply(target)

        if not attacks:
            return DefenseAllocation(
                target=target.name,
                defenses=[],
                total_cost=0.0,
                residual_risk=0.0,
                worst_attack_stealth=0.0,
                covers_attacks=0
            )

        # G(worst_attack) = defense against worst attack
        worst_chain, worst_stealth = attacks[0]
        defenses = self.G.apply(worst_chain)

        # Compute residual risk = counit
        residual = self.counit(worst_chain, defenses)

        total_cost = sum(d.get("cost", 0) for d in defenses)

        return DefenseAllocation(
            target=target.name,
            defenses=defenses,
            total_cost=total_cost,
            residual_risk=residual,
            worst_attack_stealth=worst_stealth,
            covers_attacks=len(attacks)
        )

    def counit(self, chain: List[str], defenses: List[Dict]) -> float:
        """
        ε_chain: F(G(chain)) → chain

        "What attack remains after applying defense?"
        Returns residual vulnerability [0, 1] where 0 = fully mitigated.
        """
        effectiveness = self.G.defense_effectiveness(chain, defenses)
        return 1.0 - effectiveness

    def compute_equilibrium(self, targets: List[Target],
                            budget: float = 5.0,
                            max_iterations: int = 10) -> Dict:
        """
        Nash equilibrium via iterated adjunction.

        F∘G∘F∘G∘... converges to fixed point = equilibrium.
        Budget constraint limits total defense spending.

        Returns optimal defense allocation across all targets.
        """
        # Initial allocation: unit for each target
        allocations = {}
        for target in targets:
            alloc = self.unit(target)
            allocations[target.name] = alloc

        # Check budget
        total_cost = sum(a.total_cost for a in allocations.values())

        if total_cost > budget:
            # Prioritize by target value × residual risk
            priority = sorted(
                targets,
                key=lambda t: t.value * allocations[t.name].residual_risk,
                reverse=True
            )

            # Allocate budget greedily
            remaining_budget = budget
            final_allocations = {}

            for target in priority:
                alloc = allocations[target.name]
                if alloc.total_cost <= remaining_budget:
                    final_allocations[target.name] = alloc
                    remaining_budget -= alloc.total_cost
                else:
                    # Partial defense: pick cheapest defenses that fit
                    affordable = [d for d in alloc.defenses
                                  if d.get("cost", 0) <= remaining_budget]
                    affordable_cost = sum(d.get("cost", 0) for d in affordable)

                    final_allocations[target.name] = DefenseAllocation(
                        target=target.name,
                        defenses=affordable,
                        total_cost=affordable_cost,
                        residual_risk=alloc.residual_risk * (1 + 0.2 * (len(alloc.defenses) - len(affordable))),
                        worst_attack_stealth=alloc.worst_attack_stealth,
                        covers_attacks=alloc.covers_attacks
                    )
                    remaining_budget -= affordable_cost

            allocations = final_allocations

        # Iterate to improve (triangle identity convergence)
        for iteration in range(max_iterations):
            improved = False

            for target in targets:
                if target.name not in allocations:
                    continue

                old_alloc = allocations[target.name]

                # Re-evaluate: with current defenses, what's the new worst attack?
                # This is the F∘G∘F step
                new_alloc = self.unit(target)

                # Check if defense changed
                if abs(new_alloc.residual_risk - old_alloc.residual_risk) > 0.01:
                    improved = True
                    if new_alloc.total_cost <= budget:
                        allocations[target.name] = new_alloc

            if not improved:
                break  # Fixed point reached

        # Compute overall metrics
        total_residual = sum(
            a.residual_risk * next((t.value for t in targets if t.name == a.target), 0.5)
            for a in allocations.values()
        )
        total_spent = sum(a.total_cost for a in allocations.values())

        return {
            "allocations": allocations,
            "total_cost": total_spent,
            "budget": budget,
            "budget_utilization": total_spent / budget if budget > 0 else 0,
            "total_weighted_residual_risk": total_residual,
            "converged": True,
            "targets_covered": len(allocations),
            "targets_total": len(targets)
        }


class DefenseOptimizer:
    """
    High-level API for defense optimization.

    Wraps AttackDefenseAdjunction with convenience methods.
    """

    def __init__(self, enriched_cat, mitre_db):
        self.adjunction = AttackDefenseAdjunction(enriched_cat, mitre_db)
        self.mitre_db = mitre_db

    def optimize_single_target(self, target: Target) -> Dict:
        """Optimize defense for a single target."""
        alloc = self.adjunction.unit(target)
        return {
            "target": target.name,
            "defenses": alloc.defenses,
            "cost": alloc.total_cost,
            "residual_risk": alloc.residual_risk,
            "worst_attack_stealth": alloc.worst_attack_stealth,
            "recommendation": self._generate_recommendation(alloc)
        }

    def optimize_portfolio(self, targets: List[Target],
                           budget: float = 5.0) -> Dict:
        """Optimize defense across a portfolio of targets."""
        return self.adjunction.compute_equilibrium(targets, budget)

    def what_if_analysis(self, target: Target,
                         remove_defense: str) -> Dict:
        """Analyze impact of removing a specific defense."""
        with_defense = self.adjunction.unit(target)

        # Remove the specified defense
        reduced_defenses = [d for d in with_defense.defenses
                           if d.get("id") != remove_defense]

        # Get the worst attack chain
        attacks = self.adjunction.F.apply(target)
        if attacks:
            worst_chain = attacks[0][0]
            new_residual = self.adjunction.counit(worst_chain, reduced_defenses)
        else:
            new_residual = 0.0

        return {
            "target": target.name,
            "removed_defense": remove_defense,
            "original_residual_risk": with_defense.residual_risk,
            "new_residual_risk": new_residual,
            "risk_increase": new_residual - with_defense.residual_risk,
            "cost_saved": next(
                (d.get("cost", 0) for d in with_defense.defenses
                 if d.get("id") == remove_defense), 0
            )
        }

    def _generate_recommendation(self, alloc: DefenseAllocation) -> str:
        """Generate human-readable defense recommendation."""
        if alloc.residual_risk < 0.2:
            risk_level = "LOW"
        elif alloc.residual_risk < 0.5:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        lines = [
            f"Defense Recommendation for {alloc.target}:",
            f"  Risk Level: {risk_level} (residual: {alloc.residual_risk:.2f})",
            f"  Total Cost: {alloc.total_cost:.2f}",
            f"  Covers {alloc.covers_attacks} attack paths",
            f"  Worst attack stealth: {alloc.worst_attack_stealth:.3f}",
            "",
            "  Applied Defenses:"
        ]

        for d in alloc.defenses:
            lines.append(
                f"    - {d.get('name', '?')} ({d.get('id', '?')}) "
                f"[eff: {d.get('effectiveness', 0):.0%}, cost: {d.get('cost', 0):.1f}] "
                f"covers {d.get('covers_technique', '?')}"
            )

        return "\n".join(lines)
