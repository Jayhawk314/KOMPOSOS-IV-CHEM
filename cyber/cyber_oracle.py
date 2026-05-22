# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>

"""
KOMPOSOS-SEC: Cybersecurity Oracle

Main orchestrator that combines all KOMPOSOS-SEC components:
- Attack chain detection (compositional structure)
- Temporal sheaf coherence (event stream validation)
- Ricci flow compression (scale to enterprise networks)
- Kan filling prediction (predict next attack steps)

This is the production API for KOMPOSOS-SEC.

Example usage:
    oracle = CyberSecurityOracle()

    # Ingest security events
    oracle.add_events(security_events)

    # Detect attacks
    threats = oracle.detect_threats()

    # Predict next steps
    predictions = oracle.predict_next_attacks()

    # Get explanation
    explanation = oracle.explain_threat(threat_id)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
import json

from cyber.attack_chain_strategies import AttackChainStrategy, SecurityEvent, MITRECompositionStrategy
from cyber.temporal_sheaves import TemporalSheafChecker, EventStreamCoherence
from cyber.ricci_compression import RicciFlowCompressor, NetworkNode, NetworkEdge, NetworkSupernodes
from cyber.kan_filling import CubicalKanFiller, AttackPathPredictor
from cyber.mitre_integration import MITREDatabase
from cyber.supply_chain import SupplyChainStrategy
from cyber.crypto_analysis import (
    CryptoVulnerabilityScanner, RSAKey, ECDSASignature,
    RSAKeyAnalyzer, PostQuantumReadinessAnalyzer,
)

# Novel Category Theory Constructions (1-6)
from cyber.stealth_scoring import StealthScorer, StealthOptimalPathFinder
from cyber.realtime_predictor import RealTimeAttackPredictor
from categorical.natural_transformations import NaturalTransformationDetector
from cyber.attack_defense_adjunction import AttackDefenseAdjunction, DefenseOptimizer, Target
from cyber.multi_surface_detector import MultiSurfaceDetector
from cyber.topos_detector import ToposDetector

from data import create_store, StoredObject


@dataclass
class ThreatDetection:
    """A detected threat (attack chain)."""
    threat_id: str
    severity: str  # "critical", "high", "medium", "low"
    attack_chain: List[str]  # Technique IDs
    confidence: float
    start_time: float
    end_time: float
    affected_hosts: List[str]
    explanation: str
    evidence: Dict


class CyberSecurityOracle:
    """
    Main KOMPOSOS-SEC Oracle for threat detection and prediction.

    This integrates all components into a unified detection engine.
    """

    def __init__(self, database_path: str = "cybersec.db", environment=None):
        """Initialize the cybersecurity oracle."""
        self.store = create_store(database_path)
        self.environment = environment
        self.mitre_db = MITREDatabase(environment=environment)

        # Core components
        self.attack_chain_strategy = AttackChainStrategy(self.store)
        self.sheaf_checker = TemporalSheafChecker(window_size_seconds=300)
        self.event_coherence = EventStreamCoherence()
        self.predictor = AttackPathPredictor()

        # Supply chain analysis
        self.supply_chain_strategy = SupplyChainStrategy(self.store)

        # Network compression (optional, for large-scale analysis)
        self.network_compressor: Optional[RicciFlowCompressor] = None
        self.compressed_network: Optional[NetworkSupernodes] = None

        # === Novel Category Theory Constructions ===

        # Construction 1: Enriched Attack Category (stealth-weighted composition)
        self.enriched_cat = self.mitre_db.build_enriched_category()
        self.stealth_scorer = StealthScorer(environment=environment)
        self.stealth_optimizer = StealthOptimalPathFinder(self.enriched_cat)

        # Construction 2: Streaming Kan Extension (real-time prediction)
        self.realtime_predictor = RealTimeAttackPredictor(
            alert_threshold=0.7, decay_rate=0.001
        )

        # Construction 3: Natural Transformation Variant Detection
        self.variant_detector = NaturalTransformationDetector(self.mitre_db)

        # Construction 4: Attack-Defense Adjunction (game-theoretic defense)
        self.defense_adjunction = AttackDefenseAdjunction(self.enriched_cat, self.mitre_db)
        self.defense_optimizer = DefenseOptimizer(self.enriched_cat, self.mitre_db)

        # Construction 5: Grothendieck Multi-Surface Fibration (APT detection)
        self.multi_surface_detector = MultiSurfaceDetector()

        # Construction 6: Presheaf Topos Logic (multi-valued truth)
        self.topos_detector = ToposDetector.from_enriched_category(self.enriched_cat)

        # Crypto vulnerability scanner (Layer 2 bridge)
        self.crypto_scanner = CryptoVulnerabilityScanner()

        # Event buffer
        self.events: List[SecurityEvent] = []

        # Detected threats
        self.detected_threats: List[ThreatDetection] = []
        self.threat_counter = 0

        print("[KOMPOSOS-SEC] Initialized")
        print(f"  MITRE ATT&CK: {len(self.mitre_db.techniques)} techniques loaded")
        print(f"  Valid compositions: {len(self.mitre_db.valid_compositions)}")
        print(f"  Enriched category: {self.enriched_cat}")
        print(f"  Novel constructions: 6 active")

    def set_environment(self, environment):
        """
        Change the environment profile and rebuild dependent components.

        Rebuilds the enriched category, stealth scorer, stealth optimizer,
        and realtime predictor with the new environment.
        """
        self.environment = environment
        self.mitre_db.environment = environment
        # Invalidate successor cache so it rebuilds with new environment
        if hasattr(self.mitre_db, '_successor_cache'):
            del self.mitre_db._successor_cache

        self.enriched_cat = self.mitre_db.build_enriched_category()
        self.stealth_scorer = StealthScorer(environment=environment)
        self.stealth_optimizer = StealthOptimalPathFinder(self.enriched_cat)
        self.realtime_predictor = RealTimeAttackPredictor(
            alert_threshold=0.7, decay_rate=0.001
        )

    def add_events(self, events: List[SecurityEvent]):
        """Add security events for analysis."""
        self.events.extend(events)
        print(f"[KOMPOSOS-SEC] Added {len(events)} events (total: {len(self.events)})")

    def add_network_topology(self, nodes: List[NetworkNode], edges: List[NetworkEdge]):
        """
        Add network topology for compression and attack path analysis.

        For large networks (>10K nodes), this enables 100x compression.
        """
        print(f"[KOMPOSOS-SEC] Compressing network: {len(nodes)} nodes, {len(edges)} edges")

        self.network_compressor = RicciFlowCompressor(target_compression_ratio=100.0)
        self.compressed_network = self.network_compressor.compress(nodes, edges)

        print(f"[KOMPOSOS-SEC] Network compressed to {len(self.compressed_network.supernodes)} supernodes")

    def detect_threats(self, time_window_hours: Optional[float] = None) -> List[ThreatDetection]:
        """
        Detect threats from ingested events.

        Args:
            time_window_hours: Analyze only recent events (None = all events)

        Returns:
            List of detected threats
        """
        print("\n" + "=" * 80)
        print("KOMPOSOS-SEC: THREAT DETECTION")
        print("=" * 80)

        if not self.events:
            print("[Warning] No events to analyze")
            return []

        # Filter events by time window
        events_to_analyze = self.events
        if time_window_hours is not None:
            cutoff_time = time.time() - (time_window_hours * 3600)
            events_to_analyze = [e for e in self.events if e.timestamp >= cutoff_time]
            print(f"[1] Analyzing {len(events_to_analyze)} events in last {time_window_hours}h")
        else:
            print(f"[1] Analyzing all {len(events_to_analyze)} events")

        # Phase 1: Temporal coherence check
        print("\n[2] Checking temporal coherence...")
        coherence_result = self.event_coherence.check_event_stream(events_to_analyze)
        print(f"    Coherent: {coherence_result['coherent']}")
        print(f"    Violations: {len(coherence_result['violations'])}")
        print(f"    Multi-window attacks: {len(coherence_result['attack_chains'])}")

        # Phase 2: Attack chain detection
        print("\n[3] Detecting attack chains...")
        stored_events = StoredObject(
            name="event_stream",
            type_name="security_events",
            metadata={"events": events_to_analyze}
        )
        self.store.add_object(stored_events)

        predictions = self.attack_chain_strategy.predict(stored_events)
        print(f"    Detected {len(predictions)} potential attack chains")

        # Phase 3: Filter and rank threats
        print("\n[4] Ranking threats...")
        new_threats = self._create_threat_detections(predictions, coherence_result)

        # Add to threat database
        self.detected_threats.extend(new_threats)

        print(f"\n[RESULT] {len(new_threats)} threats detected")
        for i, threat in enumerate(new_threats[:5], 1):
            print(f"  {i}. {threat.severity.upper()}: {len(threat.attack_chain)}-step chain (conf: {threat.confidence:.2%})")

        print("=" * 80)

        return new_threats

    def _create_threat_detections(self,
                                  predictions: List,
                                  coherence_result: Dict) -> List[ThreatDetection]:
        """Convert predictions to threat detections."""
        threats = []

        for pred in predictions:
            if pred.confidence < 0.5:  # Filter low-confidence
                continue

            # Extract attack chain
            attack_chain = pred.evidence.get("chain", [])
            if not attack_chain:
                continue

            # Determine severity
            severity = self._compute_severity(pred, coherence_result)

            # Get affected hosts from events
            affected_hosts = list(set(
                e.source_host for e in self.events
                if any(tech in e.matched_techniques for tech in attack_chain)
            ))

            # Get time range
            matching_events = [
                e for e in self.events
                if any(tech in e.matched_techniques for tech in attack_chain)
            ]
            start_time = min(e.timestamp for e in matching_events) if matching_events else time.time()
            end_time = max(e.timestamp for e in matching_events) if matching_events else time.time()

            # Create threat
            self.threat_counter += 1
            threat = ThreatDetection(
                threat_id=f"THREAT_{self.threat_counter:04d}",
                severity=severity,
                attack_chain=attack_chain,
                confidence=pred.confidence,
                start_time=start_time,
                end_time=end_time,
                affected_hosts=affected_hosts,
                explanation=pred.evidence.get("explanation", ""),
                evidence=pred.evidence
            )

            threats.append(threat)

        # Sort by severity and confidence
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        threats.sort(key=lambda t: (severity_order[t.severity], -t.confidence))

        return threats

    def _compute_severity(self, prediction, coherence_result: Dict) -> str:
        """Compute threat severity."""
        chain = prediction.evidence.get("chain", [])

        # Critical if:
        # - Long chain (5+ steps)
        # - Contains exfiltration or impact
        # - Has coherence violations (evasion attempts)
        if len(chain) >= 5:
            return "critical"

        for tech_id in chain:
            tech = self.mitre_db.get_technique(tech_id)
            if tech:
                from cyber.mitre_integration import MITRETactic
                if MITRETactic.EXFILTRATION in tech.tactics or MITRETactic.IMPACT in tech.tactics:
                    return "critical"

        # High if:
        # - 3-4 steps
        # - Contains lateral movement or credential access
        if len(chain) >= 3:
            return "high"

        # Medium otherwise
        if len(chain) >= 2:
            return "medium"

        return "low"

    def predict_next_attacks(self, threat_id: Optional[str] = None, top_n: int = 5) -> List[Dict]:
        """
        Predict next likely attack steps.

        Args:
            threat_id: Predict for specific threat (None = most recent threat)
            top_n: Number of predictions to return

        Returns:
            List of predicted attack techniques
        """
        if not self.detected_threats:
            print("[Warning] No threats detected yet. Run detect_threats() first.")
            return []

        # Get threat to analyze
        threat = None
        if threat_id:
            threat = next((t for t in self.detected_threats if t.threat_id == threat_id), None)
        else:
            threat = self.detected_threats[0]  # Most recent / highest severity

        if not threat:
            print(f"[Warning] Threat {threat_id} not found")
            return []

        print(f"\n[KOMPOSOS-SEC] Predicting next steps for {threat.threat_id}...")
        print(f"  Current chain: {' -> '.join(threat.attack_chain)}")

        predictions = self.predictor.predict_next_attacks(threat.attack_chain, top_n=top_n)

        print(f"  Predicted {len(predictions)} possible next steps:")
        for i, pred in enumerate(predictions, 1):
            print(f"    {i}. {pred['technique_name']} ({pred['confidence']:.0%})")

        return predictions

    def explain_threat(self, threat_id: str) -> str:
        """Generate detailed explanation of a detected threat."""
        threat = next((t for t in self.detected_threats if t.threat_id == threat_id), None)

        if not threat:
            return f"Threat {threat_id} not found"

        explanation = "\n" + "=" * 80 + "\n"
        explanation += f"THREAT ANALYSIS: {threat.threat_id}\n"
        explanation += "=" * 80 + "\n\n"

        explanation += f"Severity: {threat.severity.upper()}\n"
        explanation += f"Confidence: {threat.confidence:.0%}\n"
        explanation += f"Time Range: {threat.start_time:.1f} - {threat.end_time:.1f}\n"
        explanation += f"Duration: {(threat.end_time - threat.start_time)/60:.1f} minutes\n"
        explanation += f"Affected Hosts: {', '.join(threat.affected_hosts[:5])}"
        if len(threat.affected_hosts) > 5:
            explanation += f" (+{len(threat.affected_hosts)-5} more)"
        explanation += "\n\n"

        explanation += "ATTACK CHAIN:\n"
        explanation += "-" * 80 + "\n"

        for i, tech_id in enumerate(threat.attack_chain, 1):
            tech = self.mitre_db.get_technique(tech_id)
            if tech:
                explanation += f"{i}. {tech.name} ({tech_id})\n"
                explanation += f"   Tactics: {', '.join(t.name for t in tech.tactics)}\n"
                explanation += f"   Platforms: {', '.join(tech.platforms)}\n"

                if tech.observables:
                    explanation += f"   Observables:\n"
                    for obs_type, obs_list in tech.observables.items():
                        explanation += f"     {obs_type}: {', '.join(obs_list)}\n"

                explanation += "\n"

        explanation += "-" * 80 + "\n\n"

        explanation += "COMPOSITIONAL PROOF:\n"
        explanation += threat.explanation

        explanation += "\n" + "=" * 80 + "\n"

        return explanation

    def export_threats_json(self, output_file: str = "threats.json"):
        """Export detected threats to JSON."""
        threats_data = []

        for threat in self.detected_threats:
            threats_data.append({
                "threat_id": threat.threat_id,
                "severity": threat.severity,
                "confidence": threat.confidence,
                "attack_chain": threat.attack_chain,
                "chain_length": len(threat.attack_chain),
                "start_time": threat.start_time,
                "end_time": threat.end_time,
                "duration_seconds": threat.end_time - threat.start_time,
                "affected_hosts": threat.affected_hosts,
                "evidence": threat.evidence
            })

        with open(output_file, 'w') as f:
            json.dump({
                "total_threats": len(threats_data),
                "threats": threats_data
            }, f, indent=2)

        print(f"\n[KOMPOSOS-SEC] Exported {len(threats_data)} threats to {output_file}")

    def get_statistics(self) -> Dict:
        """Get detection statistics."""
        if not self.detected_threats:
            return {
                "total_threats": 0,
                "by_severity": {},
                "avg_chain_length": 0,
                "avg_confidence": 0
            }

        severity_counts = {}
        for threat in self.detected_threats:
            severity_counts[threat.severity] = severity_counts.get(threat.severity, 0) + 1

        return {
            "total_threats": len(self.detected_threats),
            "by_severity": severity_counts,
            "avg_chain_length": sum(len(t.attack_chain) for t in self.detected_threats) / len(self.detected_threats),
            "avg_confidence": sum(t.confidence for t in self.detected_threats) / len(self.detected_threats),
            "total_events_analyzed": len(self.events),
            "affected_hosts": len(set(h for t in self.detected_threats for h in t.affected_hosts))
        }


    # === NEW API: Novel Category Theory Constructions ===

    def find_stealthiest_attack(self, start: str, end: str,
                                 top_k: int = 5) -> Dict:
        """
        Construction 1: Find the stealthiest attack path between techniques.

        Uses enriched category composition over ([0,1], x, 1) quantale
        with DPERO log transform for Dijkstra optimization.

        Args:
            start: Starting technique ID
            end: Target technique ID
            top_k: Number of alternative paths to return

        Returns:
            Dict with optimal path, stealth score, and alternatives
        """
        result = self.stealth_optimizer.find_stealthiest_path(start, end)
        alternatives = self.stealth_optimizer.find_top_k_paths(start, end, k=top_k)

        return {
            "optimal_path": result[0] if result else None,
            "optimal_stealth": result[1] if result else 0,
            "log_cost": result[2] if result else float('inf'),
            "alternatives": [
                {"path": p, "stealth": s} for p, s in alternatives
            ],
            "defense_suggestion": (
                self.stealth_optimizer.suggest_mitigations(top_n=3)
                if result else []
            )
        }

    def stream_predict(self, technique_id: str,
                       timestamp: float = None) -> Optional[Dict]:
        """
        Construction 2: Process real-time event via streaming Kan extension.

        Feeds event through comma category and returns alert if confidence
        exceeds threshold. O(1) per event via incremental colimit update.

        Args:
            technique_id: Observed MITRE technique ID
            timestamp: Event timestamp (defaults to now)

        Returns:
            Alert dict if threshold exceeded, else None
        """
        alert = self.realtime_predictor.ingest_event(technique_id, timestamp)
        if alert:
            return alert.to_dict()
        return None

    def get_streaming_forecast(self, horizon: int = 3) -> List[Dict]:
        """
        Construction 2: Multi-step forecast via iterated Kan extension.

        Returns:
            List of forecast steps with predictions
        """
        return self.realtime_predictor.get_attack_forecast(horizon)

    def detect_zero_day_variant(self, chain: List[str]) -> List[Dict]:
        """
        Construction 3: Detect if a chain is a variant of known APT campaigns.

        Uses natural transformation detection — same kill chain shape,
        different concrete techniques. Naturality square commuting ensures
        compositional structure is preserved across variants.

        Args:
            chain: Observed attack chain (list of technique IDs)

        Returns:
            List of matching campaigns with similarity scores
        """
        return self.variant_detector.detect_variant(chain)

    def optimize_defense(self, targets: List[Dict],
                          budget: float = 5.0) -> Dict:
        """
        Construction 4: Optimize defense allocation via adjunction.

        Uses attack-defense adjunction F -| G where:
          - F: Targets -> AttackChains (attacker optimization)
          - G: AttackChains -> Defenses (defender response)
          - Unit eta: optimal defense allocation
          - Counit epsilon: residual vulnerability

        Args:
            targets: List of dicts with 'name', 'value', 'techniques'
            budget: Total defense budget

        Returns:
            Dict with equilibrium, defense allocation, residual risk
        """
        target_objects = [
            Target(
                name=t["name"],
                asset_type=t.get("asset_type", "server"),
                value=t.get("value", 1.0),
            )
            for t in targets
        ]

        return self.defense_adjunction.compute_equilibrium(
            target_objects, budget=budget
        )

    def detect_cross_surface_attack(self, technique_sequence: List[str]) -> Dict:
        """
        Construction 5: Detect cross-surface APT attack via Grothendieck fibration.

        The Grothendieck construction unifies all attack surfaces (Network,
        Identity, Cloud, Endpoint, Container, Application) into a total
        category where cross-surface pivots are first-class morphisms.

        Args:
            technique_sequence: Ordered list of observed technique IDs

        Returns:
            Dict with pivot alerts, APT match, risk score, recommendations
        """
        return self.multi_surface_detector.analyze_events(technique_sequence)

    def classify_with_topos(self, observed_techniques: List[str],
                             top_k: int = 10) -> List[Dict]:
        """
        Construction 6: Multi-valued truth classification via presheaf topos.

        Instead of binary "attack/not attack", returns sieve-based truth values
        indicating from which perspectives each technique appears threatening.
        Uses subobject classifier Omega for intuitionistic logic.

        Args:
            observed_techniques: Currently observed technique IDs
            top_k: Number of top threats to return

        Returns:
            List of threat classifications with truth values and perspectives
        """
        results = self.topos_detector.assess_threat(observed_techniques, top_k)
        return [
            {
                "technique": r.technique_id,
                "truth_value": r.truth_value,
                "confidence_level": r.confidence_level,
                "perspectives": list(r.supporting_perspectives),
                "evidence_paths": r.evidence_paths,
                "note": r.intuitionistic_note
            }
            for r in results
        ]

    def full_analysis(self, technique_sequence: List[str]) -> Dict:
        """
        Run ALL 6 novel constructions on an observed attack chain.

        This is the comprehensive analysis endpoint that leverages every
        categorical construction for maximum insight.

        Args:
            technique_sequence: Ordered list of observed technique IDs

        Returns:
            Dict with results from all 6 constructions
        """
        results = {}

        # Construction 1: Stealth analysis
        if len(technique_sequence) >= 2:
            stealth = self.stealth_scorer.chain_stealth(technique_sequence)
            results["stealth_analysis"] = {
                "chain_stealth": stealth,
                "per_technique": {
                    t: self.stealth_scorer.get_stealth(t)
                    for t in technique_sequence
                }
            }

        # Construction 2: Stream each event and get predictions
        predictions = []
        for tech in technique_sequence:
            alert = self.stream_predict(tech)
            if alert:
                predictions.append(alert)
        results["streaming_predictions"] = predictions
        results["forecast"] = self.get_streaming_forecast(3)

        # Construction 3: Variant detection
        results["variant_matches"] = self.detect_zero_day_variant(technique_sequence)

        # Construction 4: Defense recommendation
        targets = [Target(
            name="observed_attack",
            asset_type="server",
            value=1.0,
        )]
        results["defense_optimization"] = self.defense_adjunction.compute_equilibrium(
            targets, budget=5.0
        )

        # Construction 5: Cross-surface analysis
        results["cross_surface"] = self.detect_cross_surface_attack(technique_sequence)

        # Construction 6: Topos classification
        results["topos_classification"] = self.classify_with_topos(technique_sequence)

        return results


    # === Crypto-Attack Detection Bridge Methods ===

    CRYPTO_VULN_TO_TECHNIQUE = {
        "rsa_small_factor": "TCRYPTO_001",
        "rsa_close_primes": "TCRYPTO_001",
        "rsa_smooth_p_minus_1": "TCRYPTO_001",
        "rsa_insufficient_key_size": "TCRYPTO_001",
        "rsa_weak_exponent": "TCRYPTO_001",
        "rsa_common_factor": "TCRYPTO_002",
        "ecdsa_nonce_reuse": "TCRYPTO_003",
        "ecdsa_nonce_bias": "TCRYPTO_003",
        "ecdsa_weak_curve": "TCRYPTO_004",
    }

    def _map_crypto_vulns_to_techniques(self, vulnerabilities) -> List[str]:
        """Map crypto vulnerability findings to TCRYPTO_* technique IDs."""
        technique_ids = set()
        for vuln in vulnerabilities:
            tech_id = self.CRYPTO_VULN_TO_TECHNIQUE.get(vuln.vuln_type)
            if tech_id:
                technique_ids.add(tech_id)
        return sorted(technique_ids)

    def scan_and_analyze_crypto(self, rsa_keys: List[RSAKey] = None,
                                 ecdsa_signatures: List[ECDSASignature] = None) -> Dict:
        """
        Bridge: Scan crypto vulnerabilities AND run full categorical analysis.

        Takes RSA keys and/or ECDSA signatures, runs CryptoVulnerabilityScanner,
        maps findings to TCRYPTO_* technique IDs, then feeds them into
        full_analysis() for all 6 categorical constructions.

        Returns unified result: crypto findings + categorical analysis.
        """
        crypto_results = {}
        all_vulns = []

        # Scan RSA keys
        if rsa_keys:
            rsa_result = self.crypto_scanner.scan_rsa_keys(rsa_keys)
            crypto_results["rsa_scan"] = {
                "total_keys_scanned": rsa_result["total_keys_scanned"],
                "vulnerabilities_found": rsa_result["vulnerabilities_found"],
                "by_severity": rsa_result["by_severity"],
            }
            all_vulns.extend(rsa_result["all_vulnerabilities"])

        # Scan ECDSA signatures
        if ecdsa_signatures:
            ecdsa_result = self.crypto_scanner.scan_ecdsa_signatures(ecdsa_signatures)
            crypto_results["ecdsa_scan"] = {
                "total_signatures_scanned": len(ecdsa_signatures),
                "vulnerabilities_found": ecdsa_result["vulnerabilities_found"],
                "by_severity": ecdsa_result["by_severity"],
            }
            all_vulns.extend(ecdsa_result["all_vulnerabilities"])

        # Map findings to TCRYPTO techniques
        mapped_techniques = self._map_crypto_vulns_to_techniques(all_vulns)
        crypto_results["mapped_techniques"] = mapped_techniques
        crypto_results["vulnerability_details"] = [
            {
                "type": v.vuln_type,
                "severity": v.severity,
                "description": v.description,
                "affected_key": v.affected_key,
            }
            for v in all_vulns
        ]

        # Run full categorical analysis if we found techniques
        categorical_analysis = {}
        if mapped_techniques:
            categorical_analysis = self.full_analysis(mapped_techniques)

        return {
            "crypto_findings": crypto_results,
            "categorical_analysis": categorical_analysis,
            "unified_risk": "HIGH" if any(
                v.severity == "critical" for v in all_vulns
            ) else "MEDIUM" if all_vulns else "LOW",
        }

    def assess_quantum_posture(self, algorithms: List[str]) -> Dict:
        """
        Assess quantum readiness of cryptographic algorithms.

        Maps vulnerable algorithms to TCRYPTO_006 (quantum harvest risk)
        and returns quantum assessment + defense optimization via adjunction.
        """
        pq_analyzer = PostQuantumReadinessAnalyzer()
        assessments = []
        vulnerable = []

        for algo in algorithms:
            assessment = pq_analyzer.assess_algorithm(algo)
            assessments.append({
                "algorithm": assessment.algorithm,
                "quantum_vulnerable": assessment.quantum_vulnerable,
                "estimated_qubits": assessment.estimated_qubits,
                "timeline": assessment.timeline,
                "severity": assessment.severity,
                "recommendation": assessment.recommendation,
            })
            if assessment.quantum_vulnerable:
                vulnerable.append(algo)

        # If any algorithms are quantum-vulnerable, run defense optimization
        # for TCRYPTO_006 (quantum harvest risk)
        defense_result = {}
        if vulnerable:
            target = Target(
                name="quantum_vulnerable_systems",
                asset_type="server",
                value=1.0,
            )
            defense_result = self.defense_optimizer.optimize_single_target(target)

        nist_result = pq_analyzer.check_nist_compliance(algorithms)

        return {
            "assessments": assessments,
            "vulnerable_algorithms": vulnerable,
            "safe_algorithms": [a for a in algorithms if a not in vulnerable],
            "nist_compliance": nist_result,
            "defense_recommendation": defense_result,
            "quantum_harvest_risk": "HIGH" if vulnerable else "LOW",
        }

    # === RED TEAM SIMULATION API ===

    def simulate_attack(self, start: str = "T1566", end: str = "T1041",
                        max_length: int = 7) -> 'SimulationReport':
        """
        Plan and execute a simulated attack using all 6 categorical constructions.

        Flips each construction from defense to offense to understand risk.
        Returns a SimulationReport with BAS metrics and categorical insights.
        """
        from cyber.attack_simulator import RedTeamSimulator
        sim = RedTeamSimulator(self)
        campaign = sim.plan_stealth_attack(start, end, max_length)
        return sim.execute_simulated_attack(campaign)

    def run_purple_team(self, base_campaign: str = "APT28_standard",
                        budget: float = 5.0) -> Dict:
        """
        Full purple team exercise: execute variant → observe → analyze → recommend.

        Generates a novel variant of a known APT campaign via natural
        transformations (C3), executes the simulated attack, measures
        detection gaps, and recommends defense improvements via adjunction (C4).
        """
        from cyber.attack_simulator import RedTeamSimulator
        sim = RedTeamSimulator(self)
        campaign = sim.generate_campaign_variant(base_campaign, mutation_rate=0.3)
        return sim.run_purple_team_exercise(campaign)

    def run_mythos_simulation(self, attack_name: Optional[str] = None,
                              run_all: bool = False) -> Dict:
        """
        Run Mythos-style attack simulations to test system resilience.

        Based on real Anthropic Mythos capabilities (April 2026):
          - 4+ step exploit chains composed in <10 hours
          - Autonomous sandbox escape without explicit instruction
          - Legacy bug excavation (27-year-old vulnerabilities)
          - AI safety policy bypass (>50 subcommands disables checks)
          - Vulnerability chaining (multiple flaws → single exploit)
          - Memory corruption in memory-safe VMMs
          - Browser renderer + OS sandbox escapes
          - AI agent command-parsing safety bypasses
          - Supply chain scanning + exploitation

        Args:
            attack_name: Specific attack pattern to run (None = all if run_all=True)
            run_all: If True, run all 12 Mythos attack patterns

        Returns:
            Dict with simulation results and risk profile

        Usage:
            # Run all simulations
            oracle.run_mythos_simulation(run_all=True)

            # Run specific attack
            oracle.run_mythos_simulation("sandbox_escape_chain")
        """
        from cyber.mythos_attack_simulations import (
            MythosAttackSimulationSuite,
            MYTHOS_ATTACK_CHAINS,
        )

        suite = MythosAttackSimulationSuite(self)

        if run_all:
            results = suite.run_all_simulations()
            profile = suite.get_mythos_risk_profile()
            suite.print_report()

            return {
                "status": "complete",
                "simulations_run": len(results),
                "risk_profile": profile,
                "results": [
                    {
                        "attack": r.attack_name,
                        "pattern": r.attack_pattern,
                        "detection_rate": r.detection_rate,
                        "coherence_gaps": r.coherence_gaps_found,
                        "critical_gaps": r.critical_gaps,
                        "mythos_risk": r.mythos_risk_score,
                        "remediation": r.remediation_actions,
                    }
                    for r in results
                ],
            }
        elif attack_name:
            result = suite.run_simulation(attack_name)
            return {
                "status": "complete",
                "simulation": result,
                "attack_name": attack_name,
                "detection_rate": result.detection_rate,
                "coherence_gaps_found": result.coherence_gaps_found,
                "mythos_risk_score": result.mythos_risk_score,
            }
        else:
            # Default: run all
            return self.run_mythos_simulation(run_all=True)


def demo():
    """Demo KOMPOSOS-SEC with simulated attack."""
    print("\n" + "=" * 80)
    print("KOMPOSOS-SEC DEMONSTRATION")
    print("=" * 80)

    oracle = CyberSecurityOracle()

    # Simulate a multi-stage attack
    print("\n[Simulating APT attack campaign...]")

    base_time = time.time() - 3600  # 1 hour ago

    events = [
        # Stage 1: Initial Access (phishing)
        SecurityEvent(
            timestamp=base_time,
            event_type="email",
            observables={"attachment": "invoice.docx", "sender": "finance@evil.com"},
            source_host="WORKSTATION_042",
            matched_techniques=["T1566"],
            confidence=0.85
        ),

        # Stage 2: Execution (PowerShell)
        SecurityEvent(
            timestamp=base_time + 60,
            event_type="process",
            observables={"process": "powershell.exe", "command": "encoded_command"},
            source_host="WORKSTATION_042",
            matched_techniques=["T1059"],
            confidence=0.90
        ),

        # Stage 3: Privilege Escalation
        SecurityEvent(
            timestamp=base_time + 180,
            event_type="process",
            observables={"process": "exploit.exe", "parent": "powershell.exe"},
            source_host="WORKSTATION_042",
            matched_techniques=["T1068"],
            confidence=0.80
        ),

        # Stage 4: Credential Dumping
        SecurityEvent(
            timestamp=base_time + 300,
            event_type="process",
            observables={"process": "mimikatz", "access": "lsass.exe"},
            source_host="WORKSTATION_042",
            matched_techniques=["T1003"],
            confidence=0.95
        ),

        # Stage 5: Lateral Movement
        SecurityEvent(
            timestamp=base_time + 600,
            event_type="network",
            observables={"protocol": "smb", "destination": "192.168.1.50"},
            source_host="WORKSTATION_042",
            destination_host="FILE_SERVER_01",
            matched_techniques=["T1021"],
            confidence=0.75
        ),

        # Stage 6: Collection
        SecurityEvent(
            timestamp=base_time + 900,
            event_type="file",
            observables={"action": "read", "path": "/sensitive_data/"},
            source_host="FILE_SERVER_01",
            matched_techniques=["T1005"],
            confidence=0.70
        ),

        # Stage 7: Exfiltration
        SecurityEvent(
            timestamp=base_time + 1200,
            event_type="network",
            observables={"destination": "evil-c2.com", "bytes": "50MB"},
            source_host="FILE_SERVER_01",
            matched_techniques=["T1041"],
            confidence=0.85
        )
    ]

    oracle.add_events(events)

    # Detect threats
    threats = oracle.detect_threats()

    if threats:
        # Explain top threat
        print("\n" + oracle.explain_threat(threats[0].threat_id))

        # Predict next steps
        predictions = oracle.predict_next_attacks(threats[0].threat_id, top_n=3)

        # Export
        oracle.export_threats_json("demo_threats.json")

        # Statistics
        stats = oracle.get_statistics()
        print("\nDETECTION STATISTICS:")
        print(f"  Total threats: {stats['total_threats']}")
        print(f"  Average chain length: {stats['avg_chain_length']:.1f}")
        print(f"  Average confidence: {stats['avg_confidence']:.0%}")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    demo()
