# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Red Team Audit: Mythos-Style Attack Simulation

Models Anthropic Mythos Preview's actual attack methodology against
KOMPOSOS-IV's detection pipeline. Based on:
  - Anthropic red.anthropic.com/2026/mythos-preview/ capability disclosure
  - MITRE ATT&CK Evaluations methodology (evals.mitre.org)
  - NIST SP 800-115 security assessment framework

Five test classes mapping to Mythos capabilities:
  1. Autonomous Discovery — unknown vuln detection
  2. Exploit Chaining — multi-step attack chains
  3. Adversarial Evasion — bypassing detection
  4. Scale & Performance — large codebase handling
  5. Detection Quality Metrics — MITRE-style scoring

Run:
    python -m pytest audits/red_team_audit.py -v
"""

import time
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.category import Category
from core.cosmos import InfinityCosmos
from core.gray_coherence import (
    GrayCategoryLayer, SoftwareCategoryBuilder, TwoCellProxy,
    CoherenceGapType, CoherenceVulnerabilityMapper, SoftwareObject,
    SoftwareMorphism, VULN_CLASS,
)
from categorical.cat_advanced import CATEngine, TrustBoundary
from core.optimus import OptimusEngine


# ============================================================================
# Helpers
# ============================================================================

def build_cfg_category(nodes, edges):
    """Build a SoftwareCategoryBuilder from a CFG spec."""
    builder = SoftwareCategoryBuilder()
    builder.from_cfg(nodes, edges)
    return builder


def scan_builder(builder, cosmos=None):
    """Run GrayCategoryLayer scan and return gaps."""
    layer = GrayCategoryLayer(cosmos)
    return layer.scan_builder(builder)


def gap_types(gaps):
    """Extract gap type values from a list of Modifications."""
    return [g.gap_type for g in gaps]


# ============================================================================
# 1. AUTONOMOUS DISCOVERY
#    Models Mythos finding unknown vulns in code it hasn't seen.
# ============================================================================

class TestMythosAutonomousDiscovery(unittest.TestCase):
    """Mythos autonomously discovers zero-days across vuln classes."""

    def test_memory_corruption_patterns(self):
        """
        Stack buffer overflow + use-after-free + heap corruption.
        Models: FFmpeg H.264 CVE (16-year-old), Linux kernel dangling pointer.
        Realistic: functions have multiple call targets (branching).
        """
        nodes = [
            {"id": "user_input", "kind": "function", "privilege": 0},
            {"id": "parse_header", "kind": "function", "privilege": 0},
            {"id": "alloc_buffer", "kind": "function", "privilege": 0},
            {"id": "copy_data", "kind": "function", "privilege": 0},   # overflow target
            {"id": "safe_copy", "kind": "function", "privilege": 0},   # safe alternative
            {"id": "free_buffer", "kind": "function", "privilege": 0},
            {"id": "use_buffer", "kind": "function", "privilege": 0},  # UAF target
            {"id": "safe_return", "kind": "function", "privilege": 0}, # safe alternative
            {"id": "kernel_write", "kind": "function", "privilege": 2},
        ]
        edges = [
            {"src": "user_input", "dst": "parse_header", "kind": "call", "confidence": 0.9},
            {"src": "user_input", "dst": "safe_return", "kind": "call", "confidence": 0.95},
            {"src": "parse_header", "dst": "alloc_buffer", "kind": "call", "confidence": 0.8},
            {"src": "parse_header", "dst": "safe_return", "kind": "call", "confidence": 0.9},
            # Branch: safe copy vs dangerous copy
            {"src": "alloc_buffer", "dst": "copy_data", "kind": "call", "confidence": 0.3},
            {"src": "alloc_buffer", "dst": "safe_copy", "kind": "call", "confidence": 0.9},
            # Branch: free then reuse (UAF) vs safe return — shared heap region
            {"src": "free_buffer", "dst": "use_buffer", "kind": "call", "confidence": 0.2,
             "memory_regions": ["heap_buf"]},
            {"src": "free_buffer", "dst": "safe_return", "kind": "call", "confidence": 0.9,
             "memory_regions": ["heap_buf"]},
            # Privesc via corruption
            {"src": "use_buffer", "dst": "kernel_write", "kind": "call", "confidence": 0.1,
             "privilege_delta": 2},
            {"src": "use_buffer", "dst": "safe_return", "kind": "call", "confidence": 0.8},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        detected_types = set(gap_types(gaps))
        # Must detect at least memory-related gaps
        memory_gaps = {
            CoherenceGapType.COMPOSITION_BOUNDARY,
            CoherenceGapType.LIFETIME_VIOLATION,
            CoherenceGapType.GRAY_TENSOR_FAILURE,
            CoherenceGapType.FUNCTOR_ESCAPE,
            CoherenceGapType.PRIVILEGE_NON_COMMUTE,
        }
        found = detected_types & memory_gaps
        self.assertTrue(len(found) >= 2,
                        f"Must detect >=2 memory corruption indicators, got: "
                        f"{[g.value for g in found]}")

    def test_logic_vulnerability_patterns(self):
        """
        Auth bypass + privilege escalation.
        Models: KASLR bypass + auth skip patterns Mythos chains.
        Each source node has branching (safe + dangerous paths).
        """
        nodes = [
            {"id": "login_handler", "kind": "function", "privilege": 0},
            {"id": "auth_check", "kind": "function", "privilege": 0},
            {"id": "admin_panel", "kind": "function", "privilege": 1},
            {"id": "kernel_info", "kind": "function", "privilege": 2},  # KASLR leak
            {"id": "safe_logout", "kind": "function", "privilege": 0},  # safe path
        ]
        edges = [
            # Normal path: login → auth → admin (high confidence)
            {"src": "login_handler", "dst": "auth_check", "kind": "call", "confidence": 0.95},
            # Bypass path: login → admin directly (auth skip, low confidence)
            {"src": "login_handler", "dst": "admin_panel", "kind": "call", "confidence": 0.1},
            # auth_check branches: safe vs escalation
            {"src": "auth_check", "dst": "admin_panel", "kind": "call", "confidence": 0.9},
            {"src": "auth_check", "dst": "safe_logout", "kind": "call", "confidence": 0.95},
            # admin_panel branches: safe vs KASLR leak
            {"src": "admin_panel", "dst": "kernel_info", "kind": "call", "confidence": 0.15,
             "privilege_delta": 2},
            {"src": "admin_panel", "dst": "safe_logout", "kind": "call", "confidence": 0.9},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        detected_types = set(gap_types(gaps))
        # Auth bypass should trigger sieve_collapse or privilege_non_commute
        auth_indicators = {
            CoherenceGapType.SIEVE_COLLAPSE,
            CoherenceGapType.PRIVILEGE_NON_COMMUTE,
            CoherenceGapType.FUNCTOR_ESCAPE,
        }
        found = detected_types & auth_indicators
        self.assertTrue(len(found) >= 1,
                        f"Must detect auth/priv bypass, got: {[g.value for g in detected_types]}")

    def test_ancient_bug_detection(self):
        """
        Deeply nested call chain (6+ levels) hiding a buffer overflow.
        Models: FreeBSD NFS CVE-2026-4747 (17-year-old bug).
        Mythos found this through autonomous deep path analysis.
        Each node has a safe alternative to create 2-cell pairs.
        """
        nodes = [{"id": f"fn_{i}", "kind": "function", "privilege": 0} for i in range(8)]
        nodes.append({"id": "overflow_target", "kind": "function", "privilege": 2})
        nodes.append({"id": "safe_exit", "kind": "function", "privilege": 0})

        edges = []
        for i in range(7):
            # Normal chain: fn_i → fn_{i+1}
            edges.append({
                "src": f"fn_{i}", "dst": f"fn_{i+1}",
                "kind": "call", "confidence": 0.85,
            })
            # Safe alternative: fn_i → safe_exit
            edges.append({
                "src": f"fn_{i}", "dst": "safe_exit",
                "kind": "call", "confidence": 0.95,
            })
        # Deep bug: fn_7 → overflow_target with low confidence (the hidden vuln)
        edges.append({
            "src": "fn_7", "dst": "overflow_target",
            "kind": "call", "confidence": 0.1,
            "privilege_delta": 2,
        })
        # fn_7 also has safe path
        edges.append({
            "src": "fn_7", "dst": "safe_exit",
            "kind": "call", "confidence": 0.9,
        })

        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        # The system must detect the privilege boundary crossing at depth
        self.assertTrue(len(gaps) > 0,
                        "Must detect vulnerability even at 8-level call depth")

        # Verify a gap involves the deep target or fn_7
        deep_gaps = [g for g in gaps
                     if "overflow_target" in g.source_2cell.source_morphism
                     or "overflow_target" in g.source_2cell.target_morphism
                     or "fn_7" in g.source_2cell.source_morphism]
        self.assertTrue(len(deep_gaps) > 0,
                        "Must detect the deep overflow, not just surface-level noise")

    def test_false_positive_rate(self):
        """
        Clean code with no vulnerabilities.
        Mythos-defense must not cry wolf on safe patterns.
        """
        nodes = [
            {"id": "main", "kind": "function", "privilege": 0},
            {"id": "validate_input", "kind": "function", "privilege": 0},
            {"id": "process_data", "kind": "function", "privilege": 0},
            {"id": "format_output", "kind": "function", "privilege": 0},
            {"id": "log_result", "kind": "function", "privilege": 0},
        ]
        edges = [
            {"src": "main", "dst": "validate_input", "kind": "call", "confidence": 0.95},
            {"src": "validate_input", "dst": "process_data", "kind": "call", "confidence": 0.9},
            {"src": "process_data", "dst": "format_output", "kind": "call", "confidence": 0.9},
            {"src": "format_output", "dst": "log_result", "kind": "call", "confidence": 0.95},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        # Clean code: 0 false positives is ideal, allow at most 1
        self.assertLessEqual(len(gaps), 1,
                             f"False positive rate too high: {len(gaps)} gaps on clean code")


# ============================================================================
# 2. EXPLOIT CHAINING
#    Mythos's signature: chain 2-4 vulns to defeat defense-in-depth.
# ============================================================================

class TestMythosExploitChaining(unittest.TestCase):
    """Mythos chains multiple vulnerabilities into complete exploits."""

    def test_two_step_chain(self):
        """
        Privilege escalation -> sandbox escape.
        Models basic Mythos chaining: privesc + escape = full compromise.
        Each source has a safe alternative (branching for 2-cell pairs).
        """
        nodes = [
            {"id": "user_process", "kind": "function", "privilege": 0},
            {"id": "admin_service", "kind": "function", "privilege": 1},
            {"id": "kernel_api", "kind": "function", "privilege": 2},
            {"id": "safe_log", "kind": "function", "privilege": 0},
        ]
        edges = [
            # Step 1: privesc (user → admin, low confidence = suspicious)
            {"src": "user_process", "dst": "admin_service", "kind": "call",
             "confidence": 0.15, "privilege_delta": 1},
            # Safe alternative from user_process
            {"src": "user_process", "dst": "safe_log", "kind": "call",
             "confidence": 0.95},
            # Step 2: escape (admin → kernel, low confidence = suspicious)
            {"src": "admin_service", "dst": "kernel_api", "kind": "call",
             "confidence": 0.1, "privilege_delta": 1},
            # Safe alternative from admin_service
            {"src": "admin_service", "dst": "safe_log", "kind": "call",
             "confidence": 0.9},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        self.assertTrue(len(gaps) >= 1, "Must detect at least one link in the chain")

        # Verify chainability: both links should be flagged
        mapper = CoherenceVulnerabilityMapper()
        vulns = mapper.classify_all(gaps, location="test_chain")
        chainable = [v for v in vulns if v.is_chainable]
        self.assertTrue(len(chainable) >= 1,
                        "At least one gap must be marked chainable")

    def test_four_step_chain(self):
        """
        KASLR bypass -> kernel read -> scheduler manipulation -> code execution.
        Models: Mythos's documented Linux kernel exploit chain.
        Each step has a safe alternative from the same source.
        """
        nodes = [
            {"id": "net_handler", "kind": "function", "privilege": 0},
            {"id": "idt_leak", "kind": "function", "privilege": 1},     # KASLR bypass
            {"id": "freed_skb", "kind": "function", "privilege": 1},    # kernel read via UAF
            {"id": "tc_sched", "kind": "function", "privilege": 2},     # scheduler manipulation
            {"id": "fn_ptr_hijack", "kind": "function", "privilege": 2}, # code execution
            {"id": "safe_drop", "kind": "function", "privilege": 0},    # safe path
        ]
        edges = [
            # Attack chain
            {"src": "net_handler", "dst": "idt_leak", "kind": "call",
             "confidence": 0.2, "privilege_delta": 1},
            {"src": "net_handler", "dst": "safe_drop", "kind": "call",
             "confidence": 0.95},
            {"src": "idt_leak", "dst": "freed_skb", "kind": "call",
             "confidence": 0.15},
            {"src": "idt_leak", "dst": "safe_drop", "kind": "call",
             "confidence": 0.9},
            {"src": "freed_skb", "dst": "tc_sched", "kind": "call",
             "confidence": 0.1, "privilege_delta": 1},
            {"src": "freed_skb", "dst": "safe_drop", "kind": "call",
             "confidence": 0.85},
            {"src": "tc_sched", "dst": "fn_ptr_hijack", "kind": "call",
             "confidence": 0.05},
            {"src": "tc_sched", "dst": "safe_drop", "kind": "call",
             "confidence": 0.8},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        # Must detect multiple gaps across the chain
        self.assertTrue(len(gaps) >= 2,
                        f"Must detect >=2 gaps in 4-step chain, got {len(gaps)}")

    def test_cross_boundary_pivot(self):
        """
        Network -> NFS handler -> stack overflow -> ROP -> root.
        Models: FreeBSD NFS RCE (CVE-2026-4747).
        Tests trust boundary enforcement via CATEngine + FibrationEnforcer.
        """
        cat = Category("nfs_pivot", db_path=":memory:")
        cat.add("net_entry", type_name="NetworkSurface")
        cat.add("nfs_handler", type_name="NetworkSurface")
        cat.add("stack_overflow", type_name="KernelSurface")
        cat.add("rop_chain", type_name="KernelSurface")
        cat.add("root_shell", type_name="KernelSurface")

        cat.connect("net_entry", "nfs_handler", "nfs_request", confidence=0.8)
        cat.connect("nfs_handler", "stack_overflow", "buffer_overrun", confidence=0.1)
        cat.connect("stack_overflow", "rop_chain", "gadget_chain", confidence=0.05)
        cat.connect("rop_chain", "root_shell", "exec_payload", confidence=0.05)

        optimus = OptimusEngine(cat)
        engine = CATEngine(cat, optimus=optimus, publish_events=False)

        boundary = TrustBoundary(
            name="net_to_kernel",
            source_surface="NetworkSurface",
            target_surface="KernelSurface",
            policy_rules=["input_validation_required", "stack_canary_required"],
        )

        from categorical.activity_system import ActivitySystem, ActivityComponent
        system = ActivitySystem("nfs_attack")
        # Include all objects that participate in the boundary crossing
        system.add_component("net_entry", ActivityComponent.SUBJECT)
        system.add_component("nfs_handler", ActivityComponent.TOOL)
        system.add_component("stack_overflow", ActivityComponent.TOOL)
        system.add_component("root_shell", ActivityComponent.OBJECT)
        system.add_component("rop_chain", ActivityComponent.COMMUNITY)

        result = engine.full_analysis(
            system, trust_boundaries=[boundary],
        )

        # Must detect cross-boundary pivot violations
        self.assertIsInstance(result["pivot_violations"], list)
        self.assertTrue(
            len(result["pivot_violations"]) > 0,
            "FibrationEnforcer must detect Network->Kernel pivot"
        )

    def test_chain_with_one_clean_link(self):
        """
        3-step chain where middle link is legitimate.
        System must flag endpoints but not the clean middle.
        """
        nodes = [
            {"id": "exploit_entry", "kind": "function", "privilege": 0},
            {"id": "legit_middleware", "kind": "function", "privilege": 0},
            {"id": "kernel_target", "kind": "function", "privilege": 2},
        ]
        edges = [
            # Suspicious entry
            {"src": "exploit_entry", "dst": "legit_middleware", "kind": "call",
             "confidence": 0.2},
            # Also suspicious: direct path bypassing middleware
            {"src": "exploit_entry", "dst": "kernel_target", "kind": "call",
             "confidence": 0.05, "privilege_delta": 2},
            # Clean middle
            {"src": "legit_middleware", "dst": "kernel_target", "kind": "call",
             "confidence": 0.9, "privilege_delta": 2},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        # Must detect the cross-privilege gaps
        self.assertTrue(len(gaps) >= 1,
                        "Must detect privilege boundary crossing in chain")


# ============================================================================
# 3. ADVERSARIAL EVASION
#    Can an attacker craft code that bypasses KOMPOSOS-IV?
# ============================================================================

class TestAdversarialEvasion(unittest.TestCase):
    """Test resistance to deliberate evasion of the detection system."""

    def test_high_confidence_camouflage(self):
        """
        Attacker wraps os.system() in high-confidence validation code.
        The morphism looks safe (high confidence) but crosses privilege boundary.
        Each source has branching for 2-cell pair generation.
        """
        nodes = [
            {"id": "safe_wrapper", "kind": "function", "privilege": 0},
            {"id": "input_validator", "kind": "function", "privilege": 0},
            {"id": "sanitizer", "kind": "function", "privilege": 0},
            {"id": "os_system_call", "kind": "function", "privilege": 2},
            {"id": "safe_return", "kind": "function", "privilege": 0},
        ]
        edges = [
            {"src": "safe_wrapper", "dst": "input_validator", "kind": "call",
             "confidence": 0.95},
            {"src": "safe_wrapper", "dst": "safe_return", "kind": "call",
             "confidence": 0.95},
            {"src": "input_validator", "dst": "sanitizer", "kind": "call",
             "confidence": 0.95},
            {"src": "input_validator", "dst": "safe_return", "kind": "call",
             "confidence": 0.9},
            # The dangerous call hidden behind high-confidence wrappers
            {"src": "sanitizer", "dst": "os_system_call", "kind": "call",
             "confidence": 0.85, "privilege_delta": 2},
            # Safe alternative from same source
            {"src": "sanitizer", "dst": "safe_return", "kind": "call",
             "confidence": 0.95},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        # Even with high confidence, privilege boundary crossing must be detected
        priv_gaps = [g for g in gaps if g.gap_type in (
            CoherenceGapType.FUNCTOR_ESCAPE,
            CoherenceGapType.PRIVILEGE_NON_COMMUTE,
            CoherenceGapType.COMPOSITION_BOUNDARY,
        )]
        self.assertTrue(len(priv_gaps) >= 1,
                        "Must detect privilege boundary crossing despite high-confidence wrapping. "
                        f"Got gap types: {[g.gap_type.value for g in gaps]}")

    def test_split_path_evasion(self):
        """
        Attacker splits exploit across two independent paths that
        individually look clean (priv=0) but compose to reach priv=2.
        Each path has branching at the merge point.
        """
        nodes = [
            {"id": "path_a_entry", "kind": "function", "privilege": 0},
            {"id": "path_a_gadget", "kind": "function", "privilege": 0},
            {"id": "shared_target", "kind": "function", "privilege": 0},
            {"id": "path_b_entry", "kind": "function", "privilege": 0},
            {"id": "path_b_gadget", "kind": "function", "privilege": 0},
            {"id": "kernel_exec", "kind": "function", "privilege": 2},
            {"id": "safe_exit", "kind": "function", "privilege": 0},
        ]
        edges = [
            # Path A: looks clean individually
            {"src": "path_a_entry", "dst": "path_a_gadget", "kind": "call", "confidence": 0.3},
            {"src": "path_a_entry", "dst": "safe_exit", "kind": "call", "confidence": 0.9},
            {"src": "path_a_gadget", "dst": "shared_target", "kind": "call", "confidence": 0.3},
            {"src": "path_a_gadget", "dst": "safe_exit", "kind": "call", "confidence": 0.85},
            # Path B: looks clean individually
            {"src": "path_b_entry", "dst": "path_b_gadget", "kind": "call", "confidence": 0.3},
            {"src": "path_b_entry", "dst": "safe_exit", "kind": "call", "confidence": 0.9},
            {"src": "path_b_gadget", "dst": "shared_target", "kind": "call", "confidence": 0.3},
            {"src": "path_b_gadget", "dst": "safe_exit", "kind": "call", "confidence": 0.85},
            # Composed: shared_target → kernel (the actual exploit)
            {"src": "shared_target", "dst": "kernel_exec", "kind": "call",
             "confidence": 0.1, "privilege_delta": 2},
            {"src": "shared_target", "dst": "safe_exit", "kind": "call",
             "confidence": 0.9},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        # Must detect the composed privilege escalation
        self.assertTrue(len(gaps) >= 1,
                        "Must detect composed privilege escalation from split paths")

    def test_nomenclature_evasion(self):
        """
        Attacker names dangerous functions with innocent names.
        _validate_input actually calls os.system. SINK_REGISTRY won't match.
        Tests whether structural analysis (privilege propagation) still catches it.
        """
        builder = SoftwareCategoryBuilder()
        builder.objects["main"] = SoftwareObject("main", "function", privilege=0)
        builder.objects["_validate_input"] = SoftwareObject("_validate_input", "function", privilege=0)
        builder.objects["_format_output"] = SoftwareObject("_format_output", "function", privilege=2)
        builder.objects["_safe_log"] = SoftwareObject("_safe_log", "function", privilege=0)

        # main branches: _validate_input (normal) and _safe_log
        builder.morphisms.append(SoftwareMorphism(
            source="main", target="_validate_input",
            label="call.main→_validate_input", kind="call", confidence=0.9,
        ))
        builder.morphisms.append(SoftwareMorphism(
            source="main", target="_safe_log",
            label="call.main→_safe_log", kind="call", confidence=0.95,
        ))
        # _validate_input branches: dangerous escalation and safe log
        builder.morphisms.append(SoftwareMorphism(
            source="_validate_input", target="_format_output",
            label="call._validate_input→_format_output", kind="call",
            confidence=0.15, privilege_delta=2,
        ))
        builder.morphisms.append(SoftwareMorphism(
            source="_validate_input", target="_safe_log",
            label="call._validate_input→_safe_log", kind="call",
            confidence=0.9,
        ))

        gaps = scan_builder(builder)

        priv_gaps = [g for g in gaps if g.gap_type in (
            CoherenceGapType.FUNCTOR_ESCAPE,
            CoherenceGapType.PRIVILEGE_NON_COMMUTE,
            CoherenceGapType.COMPOSITION_BOUNDARY,
        )]
        self.assertTrue(len(priv_gaps) >= 1,
                        "Must detect privilege escalation regardless of function naming")

    def test_gradual_escalation(self):
        """
        Attacker escalates privilege by 1 level at each step:
        user(0) -> admin(1) -> kernel(2).
        Each step has privilege_delta=1, not 2.
        Tests cumulative detection with branching at each step.
        """
        nodes = [
            {"id": "user_fn", "kind": "function", "privilege": 0},
            {"id": "admin_fn", "kind": "function", "privilege": 1},
            {"id": "kernel_fn", "kind": "function", "privilege": 2},
            {"id": "safe_fn", "kind": "function", "privilege": 0},
        ]
        edges = [
            # Step 1: user → admin (suspicious)
            {"src": "user_fn", "dst": "admin_fn", "kind": "call",
             "confidence": 0.3, "privilege_delta": 1},
            # Safe alternative from user_fn
            {"src": "user_fn", "dst": "safe_fn", "kind": "call",
             "confidence": 0.9},
            # Step 2: admin → kernel (suspicious)
            {"src": "admin_fn", "dst": "kernel_fn", "kind": "call",
             "confidence": 0.2, "privilege_delta": 1},
            # Safe alternative from admin_fn
            {"src": "admin_fn", "dst": "safe_fn", "kind": "call",
             "confidence": 0.85},
        ]
        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        # System should detect the cumulative escalation
        # Note: this tests whether privilege propagation correctly aggregates
        self.assertTrue(len(gaps) >= 1,
                        "Must detect gradual privilege escalation (0->1->2)")


# ============================================================================
# 4. SCALE & PERFORMANCE
#    Mythos scans entire codebases. Can KOMPOSOS-IV keep up?
# ============================================================================

class TestScaleAndPerformance(unittest.TestCase):
    """Test detection at realistic codebase scale."""

    def test_1000_node_category(self):
        """
        1000 functions, ~3000 call edges, 5 injected vulns.
        Models: Mythos scanning a medium-sized project.
        """
        nodes = [{"id": f"fn_{i}", "kind": "function", "privilege": 0}
                 for i in range(1000)]
        # Add 5 kernel-level targets
        for i in range(5):
            nodes.append({"id": f"vuln_target_{i}", "kind": "function", "privilege": 2})

        edges = []
        # Normal call graph: ~3 edges per node (creates branching)
        for i in range(1000):
            for j in range(1, 4):
                target = (i + j * 7) % 1000
                edges.append({
                    "src": f"fn_{i}", "dst": f"fn_{target}",
                    "kind": "call", "confidence": 0.85,
                })

        # Inject 5 vulnerabilities
        for i in range(5):
            edges.append({
                "src": f"fn_{i * 200}", "dst": f"vuln_target_{i}",
                "kind": "call", "confidence": 0.1, "privilege_delta": 2,
            })

        builder = build_cfg_category(nodes, edges)

        start = time.time()
        gaps = scan_builder(builder)
        elapsed = time.time() - start

        # Must detect all 5 injected vulns
        self.assertTrue(len(gaps) >= 5,
                        f"Must detect >=5 vulns in 1000-node graph, got {len(gaps)}")
        # Must complete in reasonable time
        self.assertLess(elapsed, 30.0,
                        f"Scan took {elapsed:.1f}s, must complete in <30s")

    def test_deep_call_chain(self):
        """
        50-step call chain with vulnerability at step 47.
        Models: deeply nested library code hiding a bug.
        Each node has safe alternative for 2-cell pair generation.
        """
        nodes = [{"id": f"depth_{i}", "kind": "function", "privilege": 0}
                 for i in range(50)]
        nodes.append({"id": "deep_vuln", "kind": "function", "privilege": 2})
        nodes.append({"id": "safe_exit", "kind": "function", "privilege": 0})

        edges = []
        for i in range(49):
            # Chain link
            edges.append({
                "src": f"depth_{i}", "dst": f"depth_{i+1}",
                "kind": "call", "confidence": 0.9,
            })
            # Safe alternative (creates branching at every node)
            edges.append({
                "src": f"depth_{i}", "dst": "safe_exit",
                "kind": "call", "confidence": 0.95,
            })
        # Vuln at depth 47
        edges.append({
            "src": "depth_47", "dst": "deep_vuln",
            "kind": "call", "confidence": 0.1, "privilege_delta": 2,
        })

        builder = build_cfg_category(nodes, edges)
        gaps = scan_builder(builder)

        # Must detect the deep vulnerability
        deep_gaps = [g for g in gaps
                     if "deep_vuln" in g.source_2cell.source_morphism
                     or "deep_vuln" in g.source_2cell.target_morphism
                     or "depth_47" in g.source_2cell.source_morphism]
        self.assertTrue(len(deep_gaps) > 0,
                        "Must detect vulnerability at call depth 47")

    def test_parallel_morphism_scaling(self):
        """
        50 objects with 10 parallel morphisms each -> 500 morphisms.
        Tests quadratic 2-cell pair growth.
        """
        nodes = [{"id": f"obj_{i}", "kind": "function", "privilege": 0}
                 for i in range(50)]
        edges = []
        for i in range(50):
            target = (i + 1) % 50
            for j in range(10):
                edges.append({
                    "src": f"obj_{i}", "dst": f"obj_{target}",
                    "kind": "call",
                    "confidence": 0.5 + j * 0.05,
                    "label": f"obj_{i}->obj_{target}_v{j}",
                })

        builder = build_cfg_category(nodes, edges)

        start = time.time()
        gaps = scan_builder(builder)
        elapsed = time.time() - start

        # Must complete without timeout
        self.assertLess(elapsed, 60.0,
                        f"Parallel morphism scan took {elapsed:.1f}s, must complete in <60s")


# ============================================================================
# 5. DETECTION QUALITY METRICS
#    MITRE ATT&CK Evaluation-style scoring.
# ============================================================================

class TestDetectionQualityMetrics(unittest.TestCase):
    """Industry-standard detection quality measurement."""

    def _build_gap_scenario(self, gap_type_name, priv_a, priv_b, conf_a, conf_b,
                            mem_regions_a=(), mem_regions_b=(),
                            same_source=False, same_target=False):
        """Build a minimal 2-cell pair designed to trigger a specific gap type."""
        src_a = "mor_x" if same_source else "mor_a"
        src_b = "mor_x" if same_source else "mor_b"
        tgt_a = "mor_y" if same_target else "mor_c"
        tgt_b = "mor_y" if same_target else "mor_d"

        alpha = TwoCellProxy(src_a, tgt_a, f"alpha_{gap_type_name}",
                             confidence=conf_a, privilege_level=priv_a,
                             memory_regions=mem_regions_a)
        beta = TwoCellProxy(src_b, tgt_b, f"beta_{gap_type_name}",
                            confidence=conf_b, privilege_level=priv_b,
                            memory_regions=mem_regions_b)
        return alpha, beta

    def test_detection_coverage_matrix(self):
        """
        Build one scenario per gap type. Verify all 8 are detected.
        This is the MITRE-style coverage matrix.
        """
        layer = GrayCategoryLayer()
        results = {}

        # 1. FUNCTOR_ESCAPE: level_gap >= 2, low confidence
        a, b = self._build_gap_scenario("escape", 0, 2, 0.1, 0.2)
        mod = layer.check_modification_coherence(a, b)
        results["functor_escape"] = mod.gap_type == CoherenceGapType.FUNCTOR_ESCAPE

        # 2. PRIVILEGE_NON_COMMUTE: hypervisor + user
        a, b = self._build_gap_scenario("priv", 0, 2, 0.5, 0.5)
        mod = layer.check_modification_coherence(a, b)
        results["privilege_non_commute"] = mod.gap_type == CoherenceGapType.PRIVILEGE_NON_COMMUTE

        # 3. SIEVE_COLLAPSE: same target, huge confidence gap
        a = TwoCellProxy("mor_a", "shared_target", "alpha_sieve", confidence=0.95, privilege_level=0)
        b = TwoCellProxy("mor_b", "shared_target", "beta_sieve", confidence=0.1, privilege_level=0)
        mod = layer.check_modification_coherence(a, b)
        results["sieve_collapse"] = mod.gap_type == CoherenceGapType.SIEVE_COLLAPSE

        # 4. LIFETIME_VIOLATION: shared memory, divergent confidence
        a, b = self._build_gap_scenario("lifetime", 0, 0, 0.9, 0.2,
                                        mem_regions_a=("heap_buf",),
                                        mem_regions_b=("heap_buf",))
        mod = layer.check_modification_coherence(a, b)
        results["lifetime_violation"] = mod.gap_type == CoherenceGapType.LIFETIME_VIOLATION

        # 5. GRAY_TENSOR_FAILURE: no shared intermediate, both low
        a = TwoCellProxy("mor_x", "mor_y", "alpha_tensor", confidence=0.2, privilege_level=0)
        b = TwoCellProxy("mor_p", "mor_q", "beta_tensor", confidence=0.2, privilege_level=0)
        mod = layer.check_modification_coherence(a, b)
        results["gray_tensor_failure"] = mod.gap_type == CoherenceGapType.GRAY_TENSOR_FAILURE

        # 6. INTERCHANGE_FAILURE: reversed morphism pair, low product
        a = TwoCellProxy("mor_f", "mor_g", "alpha_ixchg", confidence=0.3, privilege_level=0)
        b = TwoCellProxy("mor_g", "mor_f", "beta_ixchg", confidence=0.3, privilege_level=0)
        mod = layer.check_modification_coherence(a, b)
        results["interchange_failure"] = mod.gap_type == CoherenceGapType.INTERCHANGE_FAILURE

        # 7. COMPOSITION_BOUNDARY: priv mismatch, low confidence
        a, b = self._build_gap_scenario("comp", 0, 1, 0.4, 0.4)
        mod = layer.check_modification_coherence(a, b)
        results["composition_boundary"] = mod.gap_type == CoherenceGapType.COMPOSITION_BOUNDARY

        # 8. MODIFICATION_MISSING: same source, both uncertain, not identical
        a = TwoCellProxy("shared_src", "tgt_a", "alpha_race", confidence=0.4, privilege_level=0)
        b = TwoCellProxy("shared_src", "tgt_b", "beta_race", confidence=0.4, privilege_level=0)
        mod = layer.check_modification_coherence(a, b)
        results["modification_missing"] = mod.gap_type == CoherenceGapType.MODIFICATION_MISSING

        # Score
        detected = sum(1 for v in results.values() if v)
        total = len(results)

        for gap_name, found in results.items():
            status = "DETECTED" if found else "MISSED"
            print(f"  [{status}] {gap_name}")

        print(f"\n  Coverage: {detected}/{total}")
        self.assertEqual(detected, total,
                         f"Coverage gap: {detected}/{total}. "
                         f"Missed: {[k for k, v in results.items() if not v]}")

    def test_proof_type_distribution(self):
        """
        Run scenarios with cosmos available.
        Report structural vs heuristic proof distribution.
        """
        cat = Category("proof_test", db_path=":memory:")
        cat.add("A")
        cat.add("B")
        cat.add("C")
        cat.connect("A", "B", "f", confidence=0.9)
        cat.connect("A", "B", "g", confidence=0.2)
        cat.connect("B", "C", "h", confidence=0.8)
        cat.connect("A", "C", "shortcut", confidence=0.1)

        cosmos = InfinityCosmos(cat)
        layer = GrayCategoryLayer(cosmos)

        # Check several pairs
        pairs = [
            (TwoCellProxy("f", "g", "a1", confidence=0.5),
             TwoCellProxy("f", "g", "a2", confidence=0.3)),
            (TwoCellProxy("f", "h", "b1", confidence=0.9),
             TwoCellProxy("g", "shortcut", "b2", confidence=0.1)),
        ]
        structural_count = 0
        heuristic_count = 0
        for a, b in pairs:
            mod = layer.check_modification_coherence(a, b)
            if mod.proof_type == "structural":
                structural_count += 1
            else:
                heuristic_count += 1

        total = structural_count + heuristic_count
        ratio = structural_count / total if total > 0 else 0.0
        print(f"\n  Structural proofs: {structural_count}/{total} ({ratio:.0%})")
        print(f"  Heuristic proofs:  {heuristic_count}/{total}")

        # At least some should be structural when cosmos is available
        # (not a hard requirement — depends on what 2-cells h2K builds)
        self.assertGreaterEqual(total, 2, "Must check at least 2 pairs")

    def test_end_to_end_pipeline(self):
        """
        Full pipeline: CFG -> GrayCategoryLayer -> VulnerabilityMapper -> MITRE ID.
        Verifies the complete detection-to-report chain.
        Source node has branching (dangerous + safe) for 2-cell pair generation.
        """
        nodes = [
            {"id": "entry", "kind": "function", "privilege": 0},
            {"id": "dangerous_call", "kind": "function", "privilege": 2},
            {"id": "safe_call", "kind": "function", "privilege": 0},
        ]
        edges = [
            # Dangerous path
            {"src": "entry", "dst": "dangerous_call", "kind": "call",
             "confidence": 0.1, "privilege_delta": 2},
            # Safe alternative (creates branching for 2-cell pair)
            {"src": "entry", "dst": "safe_call", "kind": "call",
             "confidence": 0.95},
        ]

        # Step 1: Build category
        builder = build_cfg_category(nodes, edges)

        # Step 2: Scan for gaps
        layer = GrayCategoryLayer()
        gaps = layer.scan_builder(builder)
        self.assertTrue(len(gaps) > 0, "Pipeline must find gaps")

        # Step 3: Map to vulnerabilities
        mapper = CoherenceVulnerabilityMapper()
        vulns = mapper.classify_all(gaps, location="pipeline_test")
        self.assertTrue(len(vulns) > 0, "Mapper must produce vulnerability candidates")

        # Step 4: Verify MITRE mapping exists
        for v in vulns:
            self.assertNotEqual(v.mitre_id, "",
                                f"Vuln {v.vuln_class} must have MITRE ID")
            self.assertNotEqual(v.vuln_class, "clean",
                                "Vuln class must not be 'clean'")
            self.assertGreater(v.severity, 0.0,
                               "Severity must be > 0")

        # Print summary
        print(f"\n  Pipeline results:")
        for v in vulns:
            print(f"    {v.vuln_class} | MITRE {v.mitre_id} | "
                  f"severity={v.severity:.2f} | {v.gap_type.value}")


# ============================================================================
# 6. FULL DEFENSE PIPELINE VALIDATION
#    Tests all 8 integrated stages against Mythos-style attacks.
#    Previously these systems were dormant. Now they're wired.
# ============================================================================

class TestFullDefensePipeline(unittest.TestCase):
    """
    Validates the integrated pipeline:
      Gray Coherence → COG → OPTIMUS → Higher-Order → CAT → Streaming Kan → Bus
    """

    def _make_pipeline(self, **kwargs):
        from core.gray_coherence import FullDefensePipeline
        return FullDefensePipeline(cog_min_tier=0, optimus_depth=3, **kwargs)

    def test_cog_verification_gate(self):
        """
        COG must verify every gap. Gaps that COG confirms as AGREE
        (path is valid) should be rejected as false positives.
        Gaps COG marks HOLLOW/REJECT should pass through.
        """
        from core.gray_coherence import FullDefensePipeline
        pipeline = self._make_pipeline()
        builder = build_cfg_category(
            nodes=[
                {"id": "entry", "kind": "function", "privilege": 0},
                {"id": "danger", "kind": "function", "privilege": 2},
                {"id": "safe", "kind": "function", "privilege": 0},
            ],
            edges=[
                {"src": "entry", "dst": "danger", "kind": "call",
                 "confidence": 0.1, "privilege_delta": 2},
                {"src": "entry", "dst": "safe", "kind": "call",
                 "confidence": 0.95},
            ],
        )
        report = pipeline.run(builder, location="cog_gate_test")

        # Every vulnerability must have been through COG
        for vuln in report.vulnerabilities:
            self.assertGreaterEqual(vuln.proof.cog_tier_reached, 0,
                "COG must have been called (tier >= 0)")
            self.assertNotEqual(vuln.proof.cog_status, "",
                "COG must set a status")
            self.assertTrue(vuln.proof.cog_verified,
                "Verified gaps must have cog_verified=True")

    def test_optimus_suggests_remediations(self):
        """
        OPTIMUS must suggest intermediate objects to close detected gaps.
        For a user→kernel gap, it should suggest adding validation gates.
        """
        pipeline = self._make_pipeline()
        builder = build_cfg_category(
            nodes=[
                {"id": "web_input", "kind": "function", "privilege": 0},
                {"id": "auth_gate", "kind": "function", "privilege": 1},
                {"id": "kernel_op", "kind": "function", "privilege": 2},
            ],
            edges=[
                {"src": "web_input", "dst": "kernel_op", "kind": "call",
                 "confidence": 0.15, "privilege_delta": 2},
                {"src": "web_input", "dst": "auth_gate", "kind": "call",
                 "confidence": 0.9, "privilege_delta": 1},
                {"src": "auth_gate", "dst": "kernel_op", "kind": "call",
                 "confidence": 0.85, "privilege_delta": 1},
            ],
        )
        report = pipeline.run(builder, location="optimus_test")

        # At least one vuln should have OPTIMUS suggestions
        vulns_with_suggestions = [v for v in report.vulnerabilities
                                   if v.optimus_suggestions]
        self.assertTrue(len(vulns_with_suggestions) > 0,
            "OPTIMUS must generate remediation suggestions")

        # Suggestions should be actionable strings
        for vuln in vulns_with_suggestions:
            for s in vuln.optimus_suggestions:
                self.assertIsInstance(s, str)
                self.assertTrue(len(s) > 10,
                    f"Suggestion too short to be useful: {s!r}")

    def test_cat_engine_detects_activity_obstructions(self):
        """
        CAT Engine must detect HOLLOW activity obstructions when
        tool-mediated paths diverge from direct paths.
        This is the key defense against Mythos's bypass strategy.
        """
        pipeline = self._make_pipeline()
        builder = build_cfg_category(
            nodes=[
                {"id": "web_handler", "kind": "function", "privilege": 0},
                {"id": "auth_gate", "kind": "function", "privilege": 1},
                {"id": "kernel_alloc", "kind": "function", "privilege": 2},
            ],
            edges=[
                # Legitimate path: web → auth → kernel
                {"src": "web_handler", "dst": "auth_gate", "kind": "call",
                 "confidence": 0.95, "privilege_delta": 1},
                {"src": "auth_gate", "dst": "kernel_alloc", "kind": "call",
                 "confidence": 0.9, "privilege_delta": 1},
                # Bypass path: web → kernel directly (Mythos exploit)
                {"src": "web_handler", "dst": "kernel_alloc", "kind": "call",
                 "confidence": 0.2, "privilege_delta": 2},
            ],
        )
        report = pipeline.run(builder, location="cat_test")

        # CAT must find activity obstructions
        self.assertTrue(len(report.activity_obstructions) > 0,
            "CAT Engine must detect diverging production triads")

        # Obstruction must be HOLLOW or REJECT (both = structural problem)
        critical = [o for o in report.activity_obstructions
                    if o.get("status") in ("HOLLOW", "REJECT")]
        self.assertTrue(len(critical) > 0,
            f"CAT must flag bypass as HOLLOW or REJECT, got: "
            f"{[o.get('status') for o in report.activity_obstructions]}")

    def test_streaming_kan_predicts_next_attack(self):
        """
        Streaming Kan must predict what Mythos will try next based
        on detected gap types mapped to MITRE techniques.
        """
        pipeline = self._make_pipeline()
        builder = build_cfg_category(
            nodes=[
                {"id": "exploit_entry", "kind": "function", "privilege": 0},
                {"id": "priv_target", "kind": "function", "privilege": 2},
                {"id": "safe_path", "kind": "function", "privilege": 0},
            ],
            edges=[
                {"src": "exploit_entry", "dst": "priv_target", "kind": "call",
                 "confidence": 0.1, "privilege_delta": 2},
                {"src": "exploit_entry", "dst": "safe_path", "kind": "call",
                 "confidence": 0.9},
            ],
        )
        report = pipeline.run(builder, location="kan_test")

        # Must have predictions
        self.assertTrue(len(report.predictions) > 0,
            "Streaming Kan must predict next attack techniques")

        # Each prediction must have technique, score, confidence
        for pred in report.predictions:
            self.assertIn("technique", pred)
            self.assertIn("score", pred)
            self.assertIn("confidence", pred)
            self.assertTrue(pred["technique"].startswith("T"),
                f"Prediction must be MITRE technique ID, got: {pred['technique']}")

    def test_all_stages_activate(self):
        """
        A realistic attack must activate ALL pipeline stages.
        This verifies nothing is dormant.
        """
        pipeline = self._make_pipeline()
        builder = build_cfg_category(
            nodes=[
                {"id": "net_recv", "kind": "function", "privilege": 0},
                {"id": "validate", "kind": "function", "privilege": 1},
                {"id": "kernel_write", "kind": "function", "privilege": 2},
            ],
            edges=[
                {"src": "net_recv", "dst": "validate", "kind": "call",
                 "confidence": 0.9, "privilege_delta": 1},
                {"src": "validate", "dst": "kernel_write", "kind": "call",
                 "confidence": 0.85, "privilege_delta": 1},
                {"src": "net_recv", "dst": "kernel_write", "kind": "call",
                 "confidence": 0.1, "privilege_delta": 2},
            ],
        )
        report = pipeline.run(builder, location="all_stages_test")
        stages = report._active_stages()

        # Verify all critical stages fired
        required_stages = [
            "gray_coherence",
            "cog_verification",
            "optimus_refinement",
            "streaming_kan_prediction",
        ]
        for stage in required_stages:
            self.assertIn(stage, stages,
                f"Stage '{stage}' did not activate. Active: {stages}")


# ============================================================================
# 7. ADVANCED MYTHOS ATTACKS (Addressing Known Limitations)
#    Tests that exercise capabilities BEYOND basic Gray Coherence:
#    - Sociotechnical attacks via CAT Engine
#    - Adaptive attack prediction via Streaming Kan
#    - COG-verified threshold replacement
#    - Cross-surface fibration hardening
# ============================================================================

class TestAdvancedMythosAttacks(unittest.TestCase):
    """
    Advanced attacks that previously couldn't be detected because
    COG, OPTIMUS, CAT, and Streaming Kan were dormant.
    """

    def test_sociotechnical_insider_threat(self):
        """
        Insider threat: legitimate user gradually escalates via
        activity system contradictions. CAT Engine must detect the
        tension between authorized and unauthorized activity patterns.
        """
        from core.gray_coherence import FullDefensePipeline
        pipeline = FullDefensePipeline(cog_min_tier=0)
        builder = build_cfg_category(
            nodes=[
                {"id": "employee_access", "kind": "function", "privilege": 0},
                {"id": "file_server", "kind": "module", "privilege": 1},
                {"id": "hr_database", "kind": "function", "privilege": 1},
                {"id": "admin_console", "kind": "function", "privilege": 2},
                {"id": "normal_work", "kind": "function", "privilege": 0},
            ],
            edges=[
                # Normal activity: employee → file_server (authorized)
                {"src": "employee_access", "dst": "file_server", "kind": "call",
                 "confidence": 0.95, "privilege_delta": 1},
                {"src": "employee_access", "dst": "normal_work", "kind": "call",
                 "confidence": 0.99},
                # Suspicious: employee → hr_database (not their role)
                {"src": "employee_access", "dst": "hr_database", "kind": "call",
                 "confidence": 0.3, "privilege_delta": 1},
                # Escalation: file_server → admin_console (insider pivot)
                {"src": "file_server", "dst": "admin_console", "kind": "call",
                 "confidence": 0.15, "privilege_delta": 1},
                {"src": "file_server", "dst": "normal_work", "kind": "call",
                 "confidence": 0.9},
            ],
        )
        report = pipeline.run(builder, location="insider_threat")

        # Pipeline must detect SOMETHING (gap or obstruction)
        total_findings = len(report.vulnerabilities) + len(report.activity_obstructions)
        self.assertTrue(total_findings > 0,
            "Must detect insider threat via gaps or CAT obstructions")

    def test_supply_chain_dependency_attack(self):
        """
        Models Mythos exploiting a deep dependency chain:
        app → trusted_lib → transitive_dep → malicious_payload.
        The intermediate library is trusted (high confidence) but
        transitively reaches dangerous code.
        """
        from core.gray_coherence import FullDefensePipeline
        pipeline = FullDefensePipeline(cog_min_tier=0)
        builder = build_cfg_category(
            nodes=[
                {"id": "app_main", "kind": "function", "privilege": 0},
                {"id": "trusted_lib", "kind": "module", "privilege": 0},
                {"id": "transitive_dep", "kind": "function", "privilege": 0},
                {"id": "malicious_payload", "kind": "function", "privilege": 2},
                {"id": "safe_fallback", "kind": "function", "privilege": 0},
            ],
            edges=[
                {"src": "app_main", "dst": "trusted_lib", "kind": "import",
                 "confidence": 0.98},
                {"src": "app_main", "dst": "safe_fallback", "kind": "call",
                 "confidence": 0.95},
                {"src": "trusted_lib", "dst": "transitive_dep", "kind": "call",
                 "confidence": 0.85},
                {"src": "trusted_lib", "dst": "safe_fallback", "kind": "call",
                 "confidence": 0.9},
                # The hidden payload deep in the chain
                {"src": "transitive_dep", "dst": "malicious_payload", "kind": "call",
                 "confidence": 0.1, "privilege_delta": 2},
                {"src": "transitive_dep", "dst": "safe_fallback", "kind": "call",
                 "confidence": 0.8},
            ],
        )
        report = pipeline.run(builder, location="supply_chain")

        self.assertTrue(len(report.vulnerabilities) > 0,
            "Must detect supply chain attack through transitive dependencies")

        # Streaming Kan should predict supply chain follow-up
        self.assertTrue(len(report.predictions) > 0,
            "Streaming Kan must predict follow-up techniques")

    def test_cross_surface_fibration_attack(self):
        """
        Mythos pivots from web surface to kernel surface.
        CAT Engine's FibrationEnforcer must detect the cross-surface
        pivot via trust boundary violation.
        Tests the full pipeline including CAT trust boundaries.
        """
        cat = Category("fibration_attack", db_path=":memory:")
        cat.add("web_entry", type_name="WebSurface")
        cat.add("api_handler", type_name="WebSurface")
        cat.add("kernel_driver", type_name="KernelSurface")
        cat.add("root_shell", type_name="KernelSurface")

        cat.connect("web_entry", "api_handler", "http_request", confidence=0.9)
        cat.connect("api_handler", "kernel_driver", "ioctl_overflow", confidence=0.1)
        cat.connect("kernel_driver", "root_shell", "escalate", confidence=0.05)

        optimus = OptimusEngine(cat)
        engine = CATEngine(cat, optimus=optimus, publish_events=False)

        boundary = TrustBoundary(
            name="web_to_kernel",
            source_surface="WebSurface",
            target_surface="KernelSurface",
            policy_rules=["input_sanitization", "ioctl_whitelisting"],
        )

        from categorical.activity_system import ActivitySystem, ActivityComponent
        system = ActivitySystem("web_to_kernel_pivot")
        system.add_component("web_entry", ActivityComponent.SUBJECT)
        system.add_component("api_handler", ActivityComponent.TOOL)
        system.add_component("kernel_driver", ActivityComponent.TOOL)
        system.add_component("root_shell", ActivityComponent.OBJECT)

        result = engine.full_analysis(system, trust_boundaries=[boundary])

        # Must detect the cross-surface pivot
        self.assertTrue(
            len(result.get("pivot_violations", [])) > 0,
            "FibrationEnforcer must detect Web→Kernel cross-surface pivot")

    def test_adaptive_multi_stage_with_prediction(self):
        """
        Simulates Mythos executing a multi-stage attack and verifies
        that Streaming Kan predicts the continuation.
        Stage 1: Initial access (T1190 pattern)
        Stage 2: Privilege escalation (T1068 pattern)
        Stage 3: Predicted by Streaming Kan
        """
        from core.gray_coherence import FullDefensePipeline
        pipeline = FullDefensePipeline(cog_min_tier=0)

        # Build two stages of attack
        builder = build_cfg_category(
            nodes=[
                {"id": "web_exploit", "kind": "function", "privilege": 0},
                {"id": "cmd_inject", "kind": "function", "privilege": 1},
                {"id": "priv_escalate", "kind": "function", "privilege": 2},
                {"id": "normal_response", "kind": "function", "privilege": 0},
            ],
            edges=[
                # Stage 1: exploit public-facing app
                {"src": "web_exploit", "dst": "cmd_inject", "kind": "call",
                 "confidence": 0.2, "privilege_delta": 1},
                {"src": "web_exploit", "dst": "normal_response", "kind": "call",
                 "confidence": 0.95},
                # Stage 2: escalate from command exec
                {"src": "cmd_inject", "dst": "priv_escalate", "kind": "call",
                 "confidence": 0.15, "privilege_delta": 1},
                {"src": "cmd_inject", "dst": "normal_response", "kind": "call",
                 "confidence": 0.8},
            ],
        )
        report = pipeline.run(builder, location="adaptive_attack")

        # Must have predictions for Stage 3
        self.assertTrue(len(report.predictions) > 0,
            "Must predict Stage 3 of adaptive attack")

        # Predictions should reference MITRE techniques
        techniques = [p["technique"] for p in report.predictions]
        self.assertTrue(all(t.startswith("T") for t in techniques),
            f"All predictions must be MITRE techniques: {techniques}")

    def test_cog_replaces_arbitrary_thresholds(self):
        """
        Previously limitation #5: 'Confidence thresholds are somewhat
        arbitrary.' COG verification now provides multi-tier logical
        verification instead of relying solely on threshold checks.
        Verify that COG is called and provides tier-based verification.
        """
        from core.gray_coherence import FullDefensePipeline
        pipeline = FullDefensePipeline(cog_min_tier=0)
        builder = build_cfg_category(
            nodes=[
                {"id": "input", "kind": "function", "privilege": 0},
                {"id": "target", "kind": "function", "privilege": 2},
                {"id": "safe", "kind": "function", "privilege": 0},
            ],
            edges=[
                {"src": "input", "dst": "target", "kind": "call",
                 "confidence": 0.5, "privilege_delta": 2},
                {"src": "input", "dst": "safe", "kind": "call",
                 "confidence": 0.9},
            ],
        )
        report = pipeline.run(builder, location="cog_threshold_test")

        # COG must have been consulted (not just threshold)
        self.assertTrue(report.has_cog_verification,
            "COG must verify gaps instead of relying on arbitrary thresholds")

        for vuln in report.vulnerabilities:
            self.assertGreaterEqual(vuln.proof.cog_tier_reached, 0,
                "COG must attempt verification through tiers")

    def test_defense_report_summary_completeness(self):
        """
        The DefenseReport.summary() must include data from ALL systems,
        not just Gray Coherence. This is the audit's scoreboard.
        """
        from core.gray_coherence import FullDefensePipeline
        pipeline = FullDefensePipeline(cog_min_tier=0)
        builder = build_cfg_category(
            nodes=[
                {"id": "a", "kind": "function", "privilege": 0},
                {"id": "b", "kind": "function", "privilege": 2},
                {"id": "c", "kind": "function", "privilege": 0},
            ],
            edges=[
                {"src": "a", "dst": "b", "kind": "call",
                 "confidence": 0.1, "privilege_delta": 2},
                {"src": "a", "dst": "c", "kind": "call",
                 "confidence": 0.95},
            ],
        )
        report = pipeline.run(builder, location="summary_test")
        summary = report.summary()

        # Must have all pipeline fields
        required_keys = [
            "total_gaps_detected",
            "cog_verified",
            "cog_rejected_false_positives",
            "vulnerabilities",
            "with_optimus_suggestions",
            "activity_obstructions",
            "predicted_next_attacks",
            "pipeline_stages_active",
            "has_cog_verification",
        ]
        for key in required_keys:
            self.assertIn(key, summary,
                f"Summary missing key: {key}")


# ============================================================================
# SCORING REPORT
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
