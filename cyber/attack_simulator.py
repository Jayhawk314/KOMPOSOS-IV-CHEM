# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Red Team Attack Simulator: Flip All 6 Categorical Constructions

Each categorical construction used for DEFENSE is inverted for OFFENSE:

  C1 Enriched Category  -> Plan stealthiest attack path (Dijkstra on quantale)
  C2 Streaming Kan Ext  -> Select next step defender LEAST expects
  C3 Natural Transform   -> Generate novel APT variants
  C4 Attack-Defense Adj  -> Find weakest defense points (counit epsilon)
  C5 Grothendieck Fib    -> Plan multi-surface campaigns
  C6 Presheaf Topos      -> Find detection blind spots (lowest truth value)

This implements a Breach and Attack Simulation (BAS) engine:
  Execute -> Observe -> Analyze -> Recommend -> Re-test

Industry context:
  - MITRE CALDERA architecture (adversary emulation)
  - Picus / AttackIQ BAS loop (detection validation)
  - Game-theoretic AI for attack guidance (arxiv:2601.05887)

Mathematical basis:
  - Stealth quantale ([0,1], x, 1) with DPERO log transform
  - Kan extensions as partial colimits (Perrone & Tholen 2022)
  - Natural transformations preserve compositional structure
  - Adjunction F -| G encodes attack-defense duality
  - Grothendieck fibration unifies attack surfaces
  - Presheaf topos gives multi-valued truth via subobject classifier
"""

from __future__ import annotations

import math
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from cyber.cyber_oracle import CyberSecurityOracle

from cyber.stealth_scoring import StealthScorer
from cyber.realtime_predictor import RealTimeAttackPredictor, FirstMoveDetector
from categorical.natural_transformations import (
    NaturalTransformationDetector, PatternFunctor,
)
from cyber.attack_defense_adjunction import (
    AttackDefenseAdjunction, DefenseOptimizer, Target, DEFENSE_CATALOG,
)
from cyber.multi_surface_detector import MultiSurfaceDetector
from cyber.topos_detector import ToposDetector
from cyber.mitre_integration import MITREDatabase, MITRETactic
from categorical.grothendieck import SURFACE_CLASSIFICATION


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AttackCampaign:
    """A planned or auto-generated attack campaign for simulation."""
    name: str
    technique_chain: List[str]
    surfaces: List[str]
    timing_delays: List[float]
    stealth_target: float
    variant_of: Optional[str] = None
    entry_point: str = ""
    objective: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class StepResult:
    """Result of executing one step of a simulated attack."""
    step_index: int
    technique_id: str
    surface: str
    timestamp: float
    detected: bool
    detection_source: Optional[str]
    stealth_score: float
    kan_alert: Optional[Dict]
    topos_truth: float
    blind_spot_perspectives: List[str]
    time_to_detect: Optional[float]


@dataclass
class SimulationReport:
    """Complete results of a simulated attack or purple team exercise."""
    campaign: AttackCampaign
    step_results: List[StepResult]

    # BAS metrics
    overall_detection_rate: float
    mean_time_to_detect: Optional[float]
    undetected_steps: List[int]

    # Categorical insights
    stealth_achieved: float
    variant_matches: List[Dict]
    defense_gaps: Dict
    cross_surface_pivots: List[Dict]
    blind_spots: Dict[str, float]

    # Overall assessment
    risk_score: float
    recommended_mitigations: List[Dict]


# =============================================================================
# HELPERS
# =============================================================================

_TECH_TO_SURFACE: Dict[str, str] = {}
for _surf, _techs in SURFACE_CLASSIFICATION.items():
    for _t in _techs:
        if _t not in _TECH_TO_SURFACE:
            _TECH_TO_SURFACE[_t] = _surf


def _classify_surface(technique_id: str) -> str:
    """Return the primary attack surface for a technique."""
    return _TECH_TO_SURFACE.get(technique_id, "Endpoint")


# =============================================================================
# RED TEAM SIMULATOR
# =============================================================================

class RedTeamSimulator:
    """
    Red team attack simulation engine using all 6 categorical constructions.

    Flips each construction from defense to offense:
      C1 (Enriched): Plan stealthiest path
      C2 (Kan):      Select optimal next step
      C3 (NatTrans): Generate novel APT variants
      C4 (Adjunction): Find weakest defense points
      C5 (Grothendieck): Plan cross-surface campaigns
      C6 (Topos):    Find detection blind spots
    """

    def __init__(self, oracle: 'CyberSecurityOracle'):
        self.oracle = oracle

    # -----------------------------------------------------------------
    # C1: Enriched Category -> Plan stealthiest attack
    # -----------------------------------------------------------------

    def plan_stealth_attack(self, start: str, end: str,
                            max_length: int = 7,
                            top_k: int = 5) -> AttackCampaign:
        """
        C1 FLIPPED: Use enriched category to PLAN the stealthiest attack path.

        Defense use: Find stealthiest path attacker MIGHT use.
        Offense use: Plan the attack path that minimizes detection probability.

        Uses StealthOptimalPathFinder.find_stealthiest_path() which runs
        Dijkstra on DPERO-transformed stealth quantale weights.
        """
        result = self.oracle.stealth_optimizer.find_stealthiest_path(
            start, end, max_length=max_length
        )

        if result is None:
            # Fallback: direct two-step chain
            chain = [start, end]
            stealth = self.oracle.stealth_scorer.chain_stealth(chain)
        else:
            chain, stealth, _log_cost = result

        # Build surfaces for each technique
        surfaces = [_classify_surface(t) for t in chain]

        # Timing: stealthier steps get longer delays (patient attacker)
        timing_delays = []
        scorer = self.oracle.stealth_scorer
        for t in chain:
            s = scorer.get_stealth(t)
            # High stealth = long dwell (1-10 minutes), low stealth = fast
            delay = 60.0 + s * 540.0  # 1 to 10 minutes
            timing_delays.append(delay)

        return AttackCampaign(
            name=f"stealth_attack_{start}_to_{end}",
            technique_chain=chain,
            surfaces=surfaces,
            timing_delays=timing_delays,
            stealth_target=stealth,
            entry_point=start,
            objective=f"reach {end} with maximum stealth",
        )

    # -----------------------------------------------------------------
    # C2: Streaming Kan Extension -> Select least-expected next step
    # -----------------------------------------------------------------

    def select_next_step(self, current_chain: List[str]) -> Dict:
        """
        C2 FLIPPED: Use streaming Kan extension to SELECT optimal next step.

        Defense use: Predict what attacker will do next.
        Offense use: Choose the step the defender LEAST expects.

        Creates a fresh RealTimeAttackPredictor, feeds the chain through,
        gets predictions, then INVERTS: selects the composable successor
        with the LOWEST prediction confidence.
        """
        # Fresh predictor to avoid contaminating oracle state
        predictor = RealTimeAttackPredictor(
            alert_threshold=0.7, decay_rate=0.001
        )

        base_time = time.time()
        for i, tech in enumerate(current_chain):
            predictor.ingest_event(tech, base_time + i * 60)

        # Get what the defender expects
        forecast = predictor.get_attack_forecast(horizon_steps=1)

        predicted_set = set()
        if forecast:
            for step_entry in forecast:
                # Each entry is {"step": N, "predictions": [...]}
                for p in step_entry.get("predictions", []):
                    predicted_set.add(p.get("technique", ""))

        # Get all composable successors of the last technique
        last_tech = current_chain[-1]
        successors = self.oracle.mitre_db.get_composable_successors(last_tech)

        if not successors:
            return {"technique": last_tech, "reason": "no successors available",
                    "surprise_factor": 0.0}

        scorer = self.oracle.stealth_scorer

        # Rank by: NOT in predicted set + high stealth
        best = None
        best_score = -1.0
        for tech_id, _weight in successors:
            surprise = 0.0 if tech_id in predicted_set else 1.0
            stealth = scorer.get_stealth(tech_id)
            score = 0.6 * surprise + 0.4 * stealth
            if score > best_score:
                best_score = score
                best = tech_id

        return {
            "technique": best,
            "stealth": scorer.get_stealth(best),
            "surprise_factor": best_score,
            "predicted_by_defender": best in predicted_set,
            "reason": "least expected by Kan extension prediction",
        }

    # -----------------------------------------------------------------
    # C3: Natural Transformation -> Generate APT variants
    # -----------------------------------------------------------------

    def generate_campaign_variant(self, base_campaign: str,
                                   mutation_rate: float = 0.3) -> AttackCampaign:
        """
        C3 FLIPPED: Use natural transformations to GENERATE novel APT variants.

        Defense use: Detect if chain matches known APT.
        Offense use: Generate chain that preserves kill chain shape but
                     substitutes stealthier techniques at each position.

        The naturality condition (commuting squares) ensures the variant
        maintains valid compositional structure.
        """
        detector = self.oracle.variant_detector
        if base_campaign not in detector.known_patterns:
            # Fallback to first available campaign
            if not detector.known_patterns:
                # No patterns registered, return empty campaign
                return AttackCampaign(
                    name=f"variant_campaign",
                    technique_chain=[],
                    surfaces=[],
                    timing_delays=[],
                    stealth_target=0.5,
                    variant_of=base_campaign,
                )
            base_campaign = next(iter(detector.known_patterns))

        base_functor = detector.known_patterns[base_campaign]
        original_chain = list(base_functor.instance)
        original_shape = list(base_functor.shape)

        scorer = self.oracle.stealth_scorer
        mitre_db = self.oracle.mitre_db
        new_chain = list(original_chain)

        # Determine which positions to mutate
        n = len(original_chain)
        positions_to_mutate = []
        for i in range(n):
            if random.random() < mutation_rate:
                positions_to_mutate.append(i)

        # For each position, find same-tactic alternative with higher stealth
        for pos in positions_to_mutate:
            original_tech = original_chain[pos]
            original_stealth = scorer.get_stealth(original_tech)

            # Get tactic for this position
            tech_obj = mitre_db.get_technique(original_tech)
            if tech_obj is None or not tech_obj.tactics:
                continue

            tactic = tech_obj.tactics[0]

            # Find alternatives in same tactic
            alternatives = mitre_db.get_techniques_by_tactic(tactic)
            candidates = []
            for alt in alternatives:
                if alt.technique_id == original_tech:
                    continue
                alt_stealth = scorer.get_stealth(alt.technique_id)
                # Must be composable with neighbors
                composable = True
                if pos > 0:
                    composable = composable and mitre_db.can_compose(
                        new_chain[pos - 1], alt.technique_id
                    )
                if pos < n - 1:
                    composable = composable and mitre_db.can_compose(
                        alt.technique_id, original_chain[pos + 1]
                    )
                if composable and alt_stealth >= original_stealth:
                    candidates.append((alt.technique_id, alt_stealth))

            if candidates:
                # Pick stealthiest candidate
                candidates.sort(key=lambda x: x[1], reverse=True)
                new_chain[pos] = candidates[0][0]

        # Validate naturality of the variant
        new_shape = []
        for tech_id in new_chain:
            tech_obj = mitre_db.get_technique(tech_id)
            if tech_obj and tech_obj.tactics:
                new_shape.append(tech_obj.tactics[0].name)
            else:
                new_shape.append(tech_id)

        variant_functor = PatternFunctor(
            name=f"variant_of_{base_campaign}",
            shape=new_shape,
            instance=new_chain,
        )
        nat_check = detector.check_naturality(base_functor, variant_functor)

        surfaces = [_classify_surface(t) for t in new_chain]
        stealth = scorer.chain_stealth(new_chain)

        timing_delays = []
        for t in new_chain:
            s = scorer.get_stealth(t)
            timing_delays.append(60.0 + s * 540.0)

        return AttackCampaign(
            name=f"variant_of_{base_campaign}",
            technique_chain=new_chain,
            surfaces=surfaces,
            timing_delays=timing_delays,
            stealth_target=stealth,
            variant_of=base_campaign,
            objective=f"variant attack based on {base_campaign}",
            metadata={
                "original_chain": original_chain,
                "mutations": len(positions_to_mutate),
                "naturality_score": nat_check["similarity_score"],
                "is_natural": nat_check["is_natural"],
            },
        )

    # -----------------------------------------------------------------
    # C4: Attack-Defense Adjunction -> Find defense gaps
    # -----------------------------------------------------------------

    def find_defense_gaps(self, targets: List[Dict],
                           budget: float = 5.0) -> Dict:
        """
        C4 FLIPPED: Use adjunction to find WEAKEST defense points.

        Defense use: Optimize defense allocation via unit eta.
        Offense use: Compute counit epsilon to find RESIDUAL VULNERABILITY.

        Ranks targets by highest residual risk = where to attack first.
        """
        adjunction = self.oracle.defense_adjunction
        target_objects = [
            Target(
                name=t.get("name", f"target_{i}"),
                asset_type=t.get("asset_type", "server"),
                value=t.get("value", 1.0),
            )
            for i, t in enumerate(targets)
        ]

        gap_analysis = []
        for target in target_objects:
            # F(target) = all viable attack chains
            chains = adjunction.F.apply(target)
            if not chains:
                continue

            worst_chain, worst_stealth = chains[0]

            # G(chain) = best defense
            defenses = adjunction.G.apply(worst_chain)

            # epsilon = residual vulnerability after defense
            residual = adjunction.counit(worst_chain, defenses)

            # Find undefended techniques
            defended_techs = {d.get("covers_technique") for d in defenses}
            undefended = [t for t in worst_chain if t not in defended_techs]

            gap_analysis.append({
                "target": target.name,
                "value": target.value,
                "worst_attack_chain": worst_chain,
                "worst_attack_stealth": worst_stealth,
                "residual_vulnerability": residual,
                "defense_cost": sum(d.get("cost", 0) for d in defenses),
                "undefended_techniques": undefended,
                "defense_effectiveness": 1.0 - residual,
                "attack_priority": target.value * residual,
            })

        # Rank by attack priority (highest = best target for attacker)
        gap_analysis.sort(key=lambda x: x["attack_priority"], reverse=True)

        return {
            "gaps": gap_analysis,
            "best_target": gap_analysis[0] if gap_analysis else None,
            "total_residual_risk": sum(g["residual_vulnerability"] for g in gap_analysis),
        }

    # -----------------------------------------------------------------
    # C5: Grothendieck Fibration -> Plan cross-surface campaigns
    # -----------------------------------------------------------------

    def plan_cross_surface_campaign(self, entry_surface: str,
                                     target_surface: str,
                                     max_pivots: int = 3) -> AttackCampaign:
        """
        C5 FLIPPED: Use Grothendieck fibration to PLAN multi-surface attack.

        Defense use: Detect cross-surface pivots.
        Offense use: Plan campaign that pivots across surfaces to reach target.
        """
        detector = self.oracle.multi_surface_detector
        chains = detector.hunt_cross_surface_chains(
            max_pivots=max_pivots, max_length=8
        )

        # Filter: starts at entry_surface and reaches target_surface
        matching = []
        for chain in chains:
            surfaces = chain.surfaces_crossed
            if (surfaces and surfaces[0] == entry_surface
                    and target_surface in surfaces):
                matching.append(chain)

        if not matching:
            # Fallback: any chain that touches target surface
            matching = [c for c in chains if target_surface in c.surfaces_crossed]

        if not matching:
            # No chains found, build minimal campaign
            return AttackCampaign(
                name=f"cross_surface_{entry_surface}_to_{target_surface}",
                technique_chain=["T1566", "T1059"],
                surfaces=[entry_surface, "Endpoint"],
                timing_delays=[300.0, 300.0],
                stealth_target=0.5,
                objective=f"pivot from {entry_surface} to {target_surface}",
            )

        # Pick stealthiest matching chain
        matching.sort(key=lambda c: c.total_stealth, reverse=True)
        best = matching[0]

        scorer = self.oracle.stealth_scorer
        timing_delays = []
        for t in best.techniques:
            s = scorer.get_stealth(t)
            timing_delays.append(60.0 + s * 540.0)

        return AttackCampaign(
            name=f"cross_surface_{entry_surface}_to_{target_surface}",
            technique_chain=best.techniques,
            surfaces=best.surfaces_crossed,
            timing_delays=timing_delays,
            stealth_target=best.total_stealth,
            objective=f"pivot from {entry_surface} to {target_surface}",
            metadata={
                "pivot_count": best.pivot_count,
                "matching_apt": best.matching_apt,
            },
        )

    # -----------------------------------------------------------------
    # C6: Presheaf Topos -> Find detection blind spots
    # -----------------------------------------------------------------

    def find_detection_blind_spots(self, technique_set: List[str]) -> Dict:
        """
        C6 FLIPPED: Use topos logic to find detection BLIND SPOTS.

        Defense use: Classify from which perspectives attack is visible.
        Offense use: Find perspectives with LOWEST truth value = blind spots.
        """
        assessments = self.oracle.topos_detector.assess_threat(
            technique_set, top_k=20
        )

        blind_spots = {}
        recommendations = []

        for assessment in assessments:
            tech_id = assessment.technique_id
            truth = assessment.truth_value
            perspectives = assessment.supporting_perspectives

            # Low truth value = blind spot (hard for defenders to see)
            if truth < 0.5:
                blind_spots[tech_id] = truth
                recommendations.append({
                    "technique": tech_id,
                    "visibility": truth,
                    "seen_by": sorted(perspectives),
                    "recommendation": "attack from this angle — low visibility",
                })

        # Sort by visibility ascending (least visible first = best for attacker)
        recommendations.sort(key=lambda x: x["visibility"])

        # Overall visibility profile
        all_truths = [a.truth_value for a in assessments]
        avg_visibility = sum(all_truths) / len(all_truths) if all_truths else 0.0

        return {
            "blind_spots": blind_spots,
            "recommendations": recommendations,
            "average_visibility": avg_visibility,
            "total_assessed": len(assessments),
            "below_threshold": len(blind_spots),
        }

    # -----------------------------------------------------------------
    # Execute Simulated Attack (orchestrates C1-C6)
    # -----------------------------------------------------------------

    def execute_simulated_attack(self, campaign: AttackCampaign) -> SimulationReport:
        """
        Execute a full simulated attack and measure detection coverage.

        For each step:
          1. Feed through C2 streaming Kan (alert?)
          2. Run C6 topos assessment (visible from which perspectives?)
          3. Check C1 stealth score (signatured?)
          4. Record detection result

        After all steps:
          5. Run C3 variant detection on full chain
          6. Run C5 cross-surface analysis
          7. Run C4 defense gap analysis
          8. Compute BAS metrics (MTTD, detection rate)
        """
        chain = campaign.technique_chain
        scorer = self.oracle.stealth_scorer

        # Fresh predictor for simulation — now with first-move detection
        sim_predictor = RealTimeAttackPredictor(
            alert_threshold=0.7, decay_rate=0.001
        )

        # Fix 2: Attach first-move detector (campaign matching on step 1)
        sim_predictor.set_first_move_detector(self.oracle.variant_detector)

        # Fix 3: Pre-seed structural priors from right Kan extension
        sim_predictor.seed_structural_priors(
            target_type="server", prior_weight=0.15
        )

        # Fix 2b: Standalone first-move detector for detection decisions
        first_move_det = FirstMoveDetector(self.oracle.variant_detector)

        step_results: List[StepResult] = []
        base_time = time.time()
        cumulative_delay = 0.0
        observed_so_far_list: List[str] = []

        for i, tech_id in enumerate(chain):
            step_time = base_time + cumulative_delay
            if i < len(campaign.timing_delays):
                cumulative_delay += campaign.timing_delays[i]

            surface = campaign.surfaces[i] if i < len(campaign.surfaces) else "Endpoint"
            observed_so_far_list.append(tech_id)

            # --- C2: Streaming Kan alert check (now with priors) ---
            kan_alert_raw = sim_predictor.ingest_event(tech_id, step_time)
            kan_alert = kan_alert_raw.to_dict() if kan_alert_raw else None
            kan_detected = kan_alert is not None

            # --- FIX 2: First-move campaign matching ---
            fm_matches = first_move_det.check_partial_chain(
                observed_so_far_list
            )
            first_move_detected = False
            if fm_matches:
                best_fm = fm_matches[0]
                # Alert if confidence > 0.1 (even 1 step of a 7-step
                # campaign gives 0.14 — enough for an early warning)
                if best_fm["confidence"] > 0.1:
                    first_move_detected = True

            # --- FIX 1: Right Kan structural score ---
            if sim_predictor.right_kan is not None:
                structural_score = sim_predictor.right_kan.get_structural_score(
                    tech_id
                )
                structural_detected = structural_score > 0.5
            else:
                structural_score = 0.0
                structural_detected = False

            # --- C6: Topos truth value check ---
            topos_assessments = self.oracle.topos_detector.assess_threat(
                observed_so_far_list, top_k=10
            )
            topos_truth = 0.0
            blind_perspectives = []
            for ta in topos_assessments:
                if ta.technique_id == tech_id:
                    topos_truth = ta.truth_value
                    all_perspectives = set()
                    for ta2 in topos_assessments:
                        all_perspectives.update(ta2.supporting_perspectives)
                    blind_perspectives = sorted(
                        all_perspectives - ta.supporting_perspectives
                    )
                    break
            topos_detected = topos_truth > 0.7

            # --- C1: Stealth signature check ---
            stealth = scorer.get_stealth(tech_id)
            signature_detected = stealth < 0.25

            # --- Detection decision (now includes first-move fixes) ---
            detected = (
                kan_detected
                or topos_detected
                or signature_detected
                or first_move_detected
                or structural_detected
            )
            detection_source = None
            if first_move_detected:
                detection_source = "first_move_campaign_match"
            elif structural_detected:
                detection_source = "right_kan_structural"
            elif kan_detected:
                detection_source = "C2_streaming_kan"
            elif topos_detected:
                detection_source = "C6_topos_truth"
            elif signature_detected:
                detection_source = "C1_signature_low_stealth"

            # Simulated detection latency
            ttd = None
            if detected:
                # Faster detection for low-stealth techniques
                ttd = 5.0 + stealth * 55.0  # 5-60 seconds

            step_results.append(StepResult(
                step_index=i,
                technique_id=tech_id,
                surface=surface,
                timestamp=step_time,
                detected=detected,
                detection_source=detection_source,
                stealth_score=stealth,
                kan_alert=kan_alert,
                topos_truth=topos_truth,
                blind_spot_perspectives=blind_perspectives,
                time_to_detect=ttd,
            ))

        # --- Post-execution analysis ---

        # C3: Variant detection on full chain
        variant_matches = self.oracle.variant_detector.detect_variant(chain)

        # C5: Cross-surface analysis
        cross_surface = self.oracle.multi_surface_detector.analyze_events(chain)
        pivot_alerts = cross_surface.get("pivots", [])

        # C4: Defense gap analysis
        defense_gaps = self.find_defense_gaps(
            [{"name": "simulated_target", "asset_type": "server", "value": 1.0}],
            budget=5.0,
        )

        # BAS metrics
        detected_steps = [r for r in step_results if r.detected]
        undetected_indices = [r.step_index for r in step_results if not r.detected]
        detection_rate = len(detected_steps) / len(step_results) if step_results else 0.0

        mttd = None
        if detected_steps:
            ttds = [r.time_to_detect for r in detected_steps if r.time_to_detect is not None]
            mttd = sum(ttds) / len(ttds) if ttds else None

        stealth_achieved = scorer.chain_stealth(chain)

        # Blind spots summary
        blind_spots_summary: Dict[str, float] = {}
        for r in step_results:
            if not r.detected:
                blind_spots_summary[r.technique_id] = r.topos_truth

        # Risk score: weighted combination
        pivot_count = len(pivot_alerts)
        risk = (
            0.30 * (1.0 - detection_rate)
            + 0.25 * stealth_achieved
            + 0.20 * min(1.0, pivot_count / 3.0)
            + 0.15 * min(1.0, len(chain) / 8.0)
            + 0.10 * (1.0 if variant_matches else 0.0)
        )

        # Recommended mitigations from C4
        recommended = []
        if defense_gaps.get("best_target"):
            best = defense_gaps["best_target"]
            for tech in best.get("undefended_techniques", []):
                defenses = DEFENSE_CATALOG.get(tech, [])
                if defenses:
                    recommended.append({
                        "technique": tech,
                        "defense": defenses[0]["name"],
                        "effectiveness": defenses[0]["effectiveness"],
                        "cost": defenses[0]["cost"],
                    })

        return SimulationReport(
            campaign=campaign,
            step_results=step_results,
            overall_detection_rate=detection_rate,
            mean_time_to_detect=mttd,
            undetected_steps=undetected_indices,
            stealth_achieved=stealth_achieved,
            variant_matches=variant_matches,
            defense_gaps=defense_gaps,
            cross_surface_pivots=[
                {"surface_from": getattr(p, "source_surface", ""),
                 "surface_to": getattr(p, "target_surface", ""),
                 "technique": getattr(p, "source_technique", "")}
                for p in pivot_alerts
            ] if isinstance(pivot_alerts, list) else [],
            blind_spots=blind_spots_summary,
            risk_score=round(risk, 4),
            recommended_mitigations=recommended,
        )

    # -----------------------------------------------------------------
    # Purple Team Exercise (full BAS loop)
    # -----------------------------------------------------------------

    def run_purple_team_exercise(self, campaign: AttackCampaign,
                                  defense_config: Optional[Dict] = None) -> Dict:
        """
        Full BAS (Breach and Attack Simulation) loop:
          1. EXECUTE: Run simulated attack
          2. OBSERVE: Collect detection results
          3. ANALYZE: Compute detection gaps and blind spots
          4. RECOMMEND: Use C4 adjunction for defense improvements
          5. RE-TEST: Generate C3 variant and measure improvement
        """
        # Step 1: Execute
        report = self.execute_simulated_attack(campaign)

        # Step 2: Observe
        observations = {
            "total_steps": len(report.step_results),
            "detected": sum(1 for r in report.step_results if r.detected),
            "missed": len(report.undetected_steps),
            "detection_rate": report.overall_detection_rate,
            "mttd": report.mean_time_to_detect,
        }

        # Step 3: Analyze -- why were steps missed?
        gap_analysis = []
        for idx in report.undetected_steps:
            step = report.step_results[idx]
            reason = "unknown"
            if step.stealth_score > 0.7:
                reason = "high stealth — no signature exists"
            elif step.topos_truth < 0.3:
                reason = "blind spot — insufficient perspective coverage"
            elif step.kan_alert is None:
                reason = "not predicted — Kan extension had no historical basis"
            gap_analysis.append({
                "step": idx,
                "technique": step.technique_id,
                "surface": step.surface,
                "stealth": step.stealth_score,
                "topos_truth": step.topos_truth,
                "reason_missed": reason,
            })

        # Step 4: Recommend -- defense improvements
        defense_recommendations = report.recommended_mitigations

        # Step 5: Re-test with variant
        retest_result = None
        if campaign.variant_of:
            # Already a variant, generate another
            variant = self.generate_campaign_variant(
                campaign.variant_of, mutation_rate=0.5
            )
        else:
            # Generate variant from first matching APT
            if report.variant_matches:
                base = report.variant_matches[0]["campaign"]
                variant = self.generate_campaign_variant(base, mutation_rate=0.4)
            else:
                variant = None

        if variant:
            retest_report = self.execute_simulated_attack(variant)
            retest_result = {
                "variant_name": variant.name,
                "variant_chain": variant.technique_chain,
                "detection_rate": retest_report.overall_detection_rate,
                "improvement": (
                    retest_report.overall_detection_rate - report.overall_detection_rate
                ),
            }

        return {
            "initial_attack": {
                "campaign": campaign.name,
                "chain": campaign.technique_chain,
                "stealth": campaign.stealth_target,
            },
            "observations": observations,
            "gap_analysis": gap_analysis,
            "defense_recommendations": defense_recommendations,
            "retest": retest_result,
            "report": report,
            "risk_score": report.risk_score,
        }

    # -----------------------------------------------------------------
    # CA Network Propagation Bridge
    # -----------------------------------------------------------------

    def simulate_network_propagation(self, campaign: AttackCampaign,
                                      network_size: int = 100) -> Dict:
        """
        Bridge categorical attack planning with CA network dynamics.

        Uses existing cellular automata models from attack_propagation_ca.py
        to simulate how the planned attack propagates through an enterprise.
        """
        from cyber.attack_propagation_ca import (
            create_enterprise_network, create_apt_ca,
        )

        # Create enterprise network
        grid, critical_nodes = create_enterprise_network(
            num_workstations=network_size,
            num_servers=max(3, network_size // 10),
            num_critical=max(1, network_size // 50),
        )

        # Create APT CA with stealth matching the campaign
        apt_ca = create_apt_ca(
            stealth_factor=campaign.stealth_target,
            detection_sensitivity=0.3,
        )

        # Initial compromise: first few workstations
        initial = {0}

        # Run simulation
        result = apt_ca.simulate_attack(grid, initial, steps=50)

        # Critical path analysis
        critical_path = apt_ca.critical_path_analysis(result['trajectory'])

        # Containment simulation (defend critical nodes)
        containment = apt_ca.containment_simulation(
            grid, initial, critical_nodes, steps=50
        )

        return {
            "campaign": campaign.name,
            "network_size": network_size,
            "simulation_steps": 50,
            "peak_compromise": result['metrics'].get('peak_metric', 0),
            "critical_path_nodes": critical_path,
            "containment_reduction": containment['reduction'],
            "trajectory_length": len(result['trajectory']),
        }

    # -----------------------------------------------------------------
    # Mythos Validation — Post-Simulation Gray Coherence Check
    # -----------------------------------------------------------------

    def validate_against_mythos(self, report: SimulationReport) -> Dict:
        """
        Validate attack simulation results against gray coherence.

        This separates TESTING (did simulation work correctly?) from
        ATTACK SIMULATION (did the system resist realistic attacks?).

        For each undetected attack step, checks if the step exploits a
        structural coherence gap (not just a detection blind spot).

        Returns:
            Dict with coherence gap findings mapped to attack steps,
            plus patchable remediation recommendations.
        """
        from core.gray_coherence_bridge import MythosShield
        from core.threat_intelligence_bus import (
            ThreatIntelligenceBus,
            EVENT_ATTACK_PATTERN_DETECTED,
            EVENT_MYTHOS_VALIDATION,
        )

        shield = MythosShield(self.oracle)
        bus = ThreatIntelligenceBus.get_instance()
        gaps_found = []
        step_to_gap: Dict[int, Dict] = {}

        # Build SoftwareCategoryBuilder from the attack chain techniques
        try:
            from core.gray_coherence import SoftwareCategoryBuilder
            builder = SoftwareCategoryBuilder()

            # Add attack chain techniques as morphisms
            chain = report.campaign.technique_chain
            for i, tech in enumerate(chain):
                obj_name = f"step_{i}_{tech}"
                builder.objects[obj_name] = type(
                    "SoftwareObject", (),
                    {"name": obj_name, "kind": "technique", "privilege": 0,
                     "metadata": {"technique_id": tech}}
                )()

                if i > 0:
                    prev = f"step_{i-1}_{chain[i-1]}"
                    curr = obj_name
                    builder.morphisms.append(type(
                        "SoftwareMorphism", (),
                        {"source": prev, "target": curr,
                         "label": f"{prev}→{curr}", "kind": "attack_step",
                         "privilege_delta": 0, "confidence": 1.0}
                    )())

            # Scan for coherence gaps in the attack chain
            gray_gaps = shield.gray_layer.scan_builder(builder)

        except Exception as e:
            gray_gaps = []

        # Run full MythosShield scan on undetected steps
        for idx in report.undetected_steps:
            step = report.step_results[idx]

            # Check if this step corresponds to a coherence gap
            shield_report = shield.scan(top_k=10, min_confidence=0.3)

            for finding in shield_report.findings:
                gap_info = {
                    "attack_step_index": idx,
                    "technique_id": step.technique_id,
                    "vuln_class": finding.vulnerability.vuln_class,
                    "gap_type": finding.vulnerability.gap_type.value,
                    "severity": finding.combined_severity,
                    "is_chainable": finding.is_chainable,
                    "mitre_id": finding.vulnerability.mitre_id,
                    "remediation": finding.vulnerability.remediation,
                }
                gaps_found.append(gap_info)
                step_to_gap[idx] = gap_info

                # Publish to threat intelligence bus
                bus.publish(
                    EVENT_MYTHOS_VALIDATION,
                    payload={
                        "attack_step": idx,
                        "technique": step.technique_id,
                        "vuln_class": finding.vulnerability.vuln_class,
                        "gap_type": finding.vulnerability.gap_type.value,
                        "severity": finding.combined_severity,
                        "remediation": finding.vulnerability.remediation,
                    },
                    source="attack_simulator",
                )

        # Publish overall attack pattern
        bus.publish(
            EVENT_ATTACK_PATTERN_DETECTED,
            payload={
                "campaign": report.campaign.name,
                "chain": report.campaign.technique_chain,
                "detection_rate": report.overall_detection_rate,
                "coherence_gaps": len(gaps_found),
                "chainable_gaps": sum(1 for g in gaps_found if g.get("is_chainable")),
            },
            source="attack_simulator",
        )

        # Build enriched mitigation recommendations
        gap_remediations = list(set(
            g["remediation"] for g in gaps_found if g.get("remediation")
        ))
        report.recommended_mitigations.extend(gap_remediations)

        return {
            "attack_campaign": report.campaign.name,
            "total_steps": len(report.step_results),
            "undetected_steps": len(report.undetected_steps),
            "coherence_gaps_found": len(gaps_found),
            "chainable_gaps": sum(1 for g in gaps_found if g.get("is_chainable")),
            "critical_gaps": sum(
                1 for g in gaps_found if g.get("severity", 0) >= 0.75
            ),
            "step_to_gap_mapping": step_to_gap,
            "gap_details": gaps_found,
            "remediation_actions": gap_remediations,
            "mythos_risk_score": (
                len(gaps_found) / max(1, len(report.undetected_steps))
                if report.undetected_steps else 0.0
            ),
        }
