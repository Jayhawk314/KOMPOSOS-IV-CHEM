# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Gray Coherence Runtime — Lightweight Continuous Protection

Provides continuous Mythos defense WITHOUT Orion dependency.

Two modes:
  1. Periodic scanning: Run MythosShield on a schedule
  2. File-watching: Re-scan when critical code changes detected

This is the hot-load replacement that doesn't need Orion.

Usage:
    # Programmatic
    runtime = GrayCoherenceRuntime(scan_interval_seconds=3600)
    runtime.run_continuous(top_k=50)

    # Or as background task
    asyncio.create_task(runtime.run_continuous_async(top_k=50))

    # Or one-shot scan
    runtime.scan_now()
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from core.gray_coherence_bridge import MythosShield, ShieldReport

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result from one MythosShield scan."""
    timestamp: float
    gap_count: int
    critical_count: int
    chainable_count: int
    scan_time_ms: float
    files_changed: List[str] = field(default_factory=list)
    report: Optional["ShieldReport"] = None

    def __repr__(self) -> str:
        return (
            f"ScanResult(gaps={self.gap_count}, "
            f"critical={self.critical_count}, "
            f"time={self.scan_time_ms:.0f}ms)"
        )


class GrayCoherenceRuntime:
    """
    Lightweight continuous Mythos defense without Orion.

    Watches critical files and re-scans on changes.
    Also runs periodic full scans even without changes.

    This provides:
      - Hot-load equivalent: detects changes and re-scans
      - Continuous protection: periodic scans + change-triggered scans
      - No Orion dependency: uses only stdlib + existing modules
    """

    def __init__(
        self,
        shield: Optional["MythosShield"] = None,
        watch_dirs: Optional[List[str]] = None,
        scan_interval_seconds: float = 3600.0,
        top_k: int = 50,
    ):
        """
        Args:
            shield: MythosShield instance (created automatically if None)
            watch_dirs: Directories to watch for changes
            scan_interval_seconds: How often to run periodic scans
            top_k: Number of conjectures to evaluate per scan
        """
        from core.gray_coherence_bridge import build_shield

        self.shield = shield
        self.watch_dirs = [Path(d) for d in (watch_dirs or [])]
        self.scan_interval = scan_interval_seconds
        self.top_k = top_k
        self._file_hashes: Dict[str, str] = {}
        self._scan_history: List[ScanResult] = []
        self._running = False

        # Initialize shield if not provided
        if self.shield is None:
            try:
                from oracle import CategoricalOracle
                from core.category import Category
                from data.embeddings import EmbeddingsEngine

                cat = Category("mythos_defense")
                embeddings = EmbeddingsEngine()
                oracle = CategoricalOracle(cat, embeddings)
                self.shield = build_shield(oracle, category=cat)
            except Exception as e:
                logger.error(f"Failed to initialize MythosShield: {e}")
                from core.gray_coherence_bridge import MythosShield
                self.shield = MythosShield(oracle=None)

        # Default watch directories
        if not self.watch_dirs:
            for d in ["core", "cyber", "cog", "categorical", "oracle"]:
                p = Path(__file__).parent.parent / d
                if p.exists():
                    self.watch_dirs.append(p)

        # Initialize file hashes
        self._initialize_file_hashes()

    def scan_now(self, top_k: Optional[int] = None) -> ScanResult:
        """
        Run one immediate MythosShield scan.

        Args:
            top_k: Override default top_k for this scan

        Returns:
            ScanResult with gap findings
        """
        k = top_k or self.top_k
        start = time.time()

        report = self.shield.scan(top_k=k)

        # Check for file changes
        changed = self._check_for_changes()

        elapsed_ms = (time.time() - start) * 1000

        result = ScanResult(
            timestamp=time.time(),
            gap_count=report.gray_gap_count,
            critical_count=len(report.critical),
            chainable_count=len(report.chainable),
            scan_time_ms=elapsed_ms,
            files_changed=changed,
            report=report,
        )

        self._scan_history.append(result)
        logger.info(
            f"[GrayCoherence] Scan complete: "
            f"{result.gap_count} gaps, {result.critical_count} critical "
            f"in {elapsed_ms:.0f}ms"
        )

        return result

    def run_continuous(self, top_k: Optional[int] = None) -> None:
        """
        Run continuous scans in the foreground (blocking).

        Main loop: watch files, scan on change, periodic full scan.
        Emits findings to stdout and threat intelligence bus.

        Args:
            top_k: Override default top_k for all scans
        """
        from core.threat_intelligence_bus import (
            ThreatIntelligenceBus,
            EVENT_MYTHOS_SHIELD_SCAN,
        )

        k = top_k or self.top_k
        self._running = True

        logger.info(
            f"[GrayCoherence] Continuous scan started "
            f"(interval={self.scan_interval}s, top_k={k})"
        )

        try:
            bus = ThreatIntelligenceBus.get_instance()

            while self._running:
                changed = self._check_for_changes()

                # Always scan; print extra info if files changed
                result = self.scan_now(k)

                # Publish to threat intelligence bus
                bus.publish(
                    EVENT_MYTHOS_SHIELD_SCAN,
                    payload={
                        "gap_count": result.gap_count,
                        "critical_count": result.critical_count,
                        "chainable_count": result.chainable_count,
                        "scan_time_ms": result.scan_time_ms,
                        "files_changed": result.files_changed,
                    },
                    source="gray_coherence_runtime",
                )

                # Print summary
                if result.critical_count > 0:
                    logger.warning(
                        f"[GrayCoherence] CRITICAL: "
                        f"{result.critical_count} structural gaps found"
                    )
                elif result.gap_count > 0:
                    logger.info(
                        f"[GrayCoherence] WARNING: "
                        f"{result.gap_count} gaps found (Mythos risk)"
                    )
                else:
                    logger.debug("[GrayCoherence] Clean — no coherence gaps")

                # Wait for next scan interval
                time.sleep(self.scan_interval)

        except KeyboardInterrupt:
            logger.info("[GrayCoherence] Continuous scan stopped")
            self._running = False

    async def run_continuous_async(self, top_k: Optional[int] = None) -> None:
        """
        Run continuous scans in the background (async).

        Can be run with asyncio.create_task().

        Args:
            top_k: Override default top_k for all scans
        """
        from core.threat_intelligence_bus import (
            ThreatIntelligenceBus,
            EVENT_MYTHOS_SHIELD_SCAN,
        )

        k = top_k or self.top_k
        self._running = True

        logger.info(
            f"[GrayCoherence] Async continuous scan started "
            f"(interval={self.scan_interval}s, top_k={k})"
        )

        try:
            bus = ThreatIntelligenceBus.get_instance()

            while self._running:
                changed = self._check_for_changes()
                result = self.scan_now(k)

                # Publish to threat intelligence bus
                bus.publish(
                    EVENT_MYTHOS_SHIELD_SCAN,
                    payload={
                        "gap_count": result.gap_count,
                        "critical_count": result.critical_count,
                        "scan_time_ms": result.scan_time_ms,
                        "files_changed": result.files_changed,
                    },
                    source="gray_coherence_runtime",
                )

                if result.critical_count > 0:
                    logger.warning(
                        f"[GrayCoherence] CRITICAL: "
                        f"{result.critical_count} structural gaps found"
                    )

                # Wait for next scan interval
                await asyncio.sleep(self.scan_interval)

        except asyncio.CancelledError:
            logger.info("[GrayCoherence] Async scan cancelled")
            self._running = False
        except KeyboardInterrupt:
            logger.info("[GrayCoherence] Async scan stopped")
            self._running = False

    def stop(self) -> None:
        """Stop continuous scanning."""
        self._running = False

    def get_scan_history(self, limit: int = 100) -> List[ScanResult]:
        """Get recent scan results."""
        return self._scan_history[-limit:]

    def get_statistics(self) -> Dict:
        """Get scan statistics."""
        if not self._scan_history:
            return {"total_scans": 0}

        total = len(self._scan_history)
        total_gaps = sum(r.gap_count for r in self._scan_history)
        total_critical = sum(r.critical_count for r in self._scan_history)
        avg_time = sum(r.scan_time_ms for r in self._scan_history) / total

        return {
            "total_scans": total,
            "total_gaps_found": total_gaps,
            "total_critical_found": total_critical,
            "average_gaps_per_scan": total_gaps / total,
            "average_scan_time_ms": avg_time,
            "last_scan": self._scan_history[-1].timestamp,
        }

    # -------------------------------------------------------------------
    # File watching internals
    # -------------------------------------------------------------------

    def _initialize_file_hashes(self) -> None:
        """Hash all watched Python files."""
        for d in self.watch_dirs:
            for f in d.glob("**/*.py"):
                try:
                    content = f.read_bytes()
                    h = hashlib.sha256(content).hexdigest()
                    self._file_hashes[str(f)] = h
                except Exception:
                    pass

    def _check_for_changes(self) -> List[str]:
        """
        Check if watched files have changed since last scan.

        Returns:
            List of changed file paths
        """
        changed = []

        # Check existing files
        current_hashes: Dict[str, str] = {}
        for f in self.watch_dirs:
            for p in f.glob("**/*.py"):
                try:
                    content = p.read_bytes()
                    h = hashlib.sha256(content).hexdigest()
                    path_str = str(p)
                    current_hashes[path_str] = h

                    old_h = self._file_hashes.get(path_str)
                    if old_h != h:
                        changed.append(path_str)
                        logger.debug(f"[GrayCoherence] File changed: {p}")
                except Exception:
                    pass

        # Check for new files
        for path_str in current_hashes:
            if path_str not in self._file_hashes:
                changed.append(path_str)

        # Update stored hashes
        self._file_hashes = current_hashes

        return changed
