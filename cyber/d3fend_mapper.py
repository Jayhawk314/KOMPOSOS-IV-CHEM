# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>
"""
D3FEND-to-DetectionCapability Mapper

Maps MITRE D3FEND defensive techniques to our DetectionCapability enum,
enabling data-driven detection maps derived from the D3FEND ontology
instead of hand-coded mappings.

D3FEND API: https://d3fend.mitre.org/api-docs
Cache file: data/cyber/d3fend_cache.json
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from cyber.stealth_scoring import DetectionCapability


# =============================================================================
# D3FEND Category → DetectionCapability Mapping
# =============================================================================
# Maps D3FEND defensive technique parent categories and labels to our
# DetectionCapability enum. D3FEND organizes 267 defensive techniques
# under 7 tactics (Harden, Detect, Isolate, Deceive, Evict, Restore, Model).
# We map the Detect-tactic subcategories most precisely.

D3FEND_CATEGORY_MAP: Dict[str, Optional[DetectionCapability]] = {
    # === Detect tactic — most relevant for stealth scoring ===
    # Network-based detection
    "Network Traffic Analysis": DetectionCapability.NDR,
    "Protocol Metadata Anomaly Detection": DetectionCapability.NDR,
    "Client-server Payload Profiling": DetectionCapability.NDR,
    "Connection Attempt Analysis": DetectionCapability.NDR,
    "DNS Traffic Analysis": DetectionCapability.NDR,
    "File Carving": DetectionCapability.NDR,
    "Inbound Traffic Filtering": DetectionCapability.NDR,
    "IPC Traffic Analysis": DetectionCapability.NDR,
    "Per Host Download-Upload Ratio Analysis": DetectionCapability.NDR,
    "Remote Terminal Session Detection": DetectionCapability.NDR,
    "Relay Pattern Analysis": DetectionCapability.NDR,
    "Certificate Analysis": DetectionCapability.NDR,

    # Endpoint-based detection
    "File Analysis": DetectionCapability.EDR,
    "Process Analysis": DetectionCapability.EDR,
    "System Call Analysis": DetectionCapability.EDR,
    "Platform Monitoring": DetectionCapability.EDR,
    "File Integrity Monitoring": DetectionCapability.EDR,
    "Process Spawn Analysis": DetectionCapability.EDR,
    "Process Self-Modification Detection": DetectionCapability.EDR,
    "Script Execution Analysis": DetectionCapability.EDR,
    "File Content Rules": DetectionCapability.EDR,
    "Dynamic Analysis": DetectionCapability.EDR,
    "Emulated File Analysis": DetectionCapability.EDR,
    "File Hashing": DetectionCapability.EDR,
    "Homoglyph Detection": DetectionCapability.EDR,
    "Executable Allowlisting": DetectionCapability.EDR,
    "Executable Denylisting": DetectionCapability.EDR,
    "System Init Config Analysis": DetectionCapability.EDR,
    "Scheduled Job Analysis": DetectionCapability.EDR,
    "Service Binary Verification": DetectionCapability.EDR,
    "Firmware Verification": DetectionCapability.EDR,
    "Memory Boundary Tracking": DetectionCapability.EDR,
    "Shadow Stack Comparisons": DetectionCapability.EDR,
    "System Firmware Verification": DetectionCapability.EDR,
    "Software Update": DetectionCapability.EDR,
    "Database Query String Analysis": DetectionCapability.EDR,
    "Process Lineage Analysis": DetectionCapability.EDR,
    "Process Code Segment Verification": DetectionCapability.EDR,
    "Endpoint Health Beacon": DetectionCapability.EDR,
    "File Access Pattern Analysis": DetectionCapability.EDR,
    "Local File Permissions": DetectionCapability.EDR,

    # Log/SIEM-based detection
    "Log Analysis": DetectionCapability.SIEM,
    "Identifier Activity Analysis": DetectionCapability.SIEM,
    "Administrative Network Activity Analysis": DetectionCapability.SIEM,
    "Authentication Event Thresholding": DetectionCapability.SIEM,
    "Authorization Event Thresholding": DetectionCapability.SIEM,
    "Job Function Access Pattern Analysis": DetectionCapability.SIEM,
    "Resource Access Pattern Analysis": DetectionCapability.SIEM,
    "Session Duration Analysis": DetectionCapability.SIEM,
    "User Data Transfer Analysis": DetectionCapability.SIEM,
    "Web Session Activity Analysis": DetectionCapability.SIEM,
    "Domain Account Monitoring": DetectionCapability.SIEM,
    "Local Account Monitoring": DetectionCapability.SIEM,

    # Identity/Auth detection
    "User Session Analysis": DetectionCapability.IDENTITY,
    "Credential Analysis": DetectionCapability.IDENTITY,
    "Authentication Analysis": DetectionCapability.IDENTITY,
    "Authentication Cache Invalidation": DetectionCapability.IDENTITY,
    "Credential Compromise Scope Analysis": DetectionCapability.IDENTITY,
    "Credential Hardening": DetectionCapability.IDENTITY,
    "Multi-factor Authentication": DetectionCapability.IDENTITY,
    "One-time Password": DetectionCapability.IDENTITY,
    "Strong Password Policy": DetectionCapability.IDENTITY,
    "User Account Permissions": DetectionCapability.IDENTITY,
    "Account Locking": DetectionCapability.IDENTITY,
    "Biometric Authentication": DetectionCapability.IDENTITY,
    "Certificate-based Authentication": DetectionCapability.IDENTITY,

    # Email security
    "Message Analysis": DetectionCapability.EMAIL_SEC,
    "Email Analysis": DetectionCapability.EMAIL_SEC,
    "Sender MTA Reputation Analysis": DetectionCapability.EMAIL_SEC,
    "Sender Reputation Analysis": DetectionCapability.EMAIL_SEC,
    "URL Analysis": DetectionCapability.EMAIL_SEC,
    "Homoglyph Detection": DetectionCapability.EMAIL_SEC,

    # Cloud security
    "Cloud Configuration Analysis": DetectionCapability.CSPM,

    # Container security
    "Container Analysis": DetectionCapability.CONTAINER_SEC,

    # Deception
    "Decoy File": DetectionCapability.DECEPTION,
    "Decoy Network Resource": DetectionCapability.DECEPTION,
    "Decoy User Credential": DetectionCapability.DECEPTION,
    "Decoy Object": DetectionCapability.DECEPTION,
    "Decoy Session Token": DetectionCapability.DECEPTION,
    "Decoy Persona": DetectionCapability.DECEPTION,
    "Decoy Public Release": DetectionCapability.DECEPTION,
    "Decoy Environment": DetectionCapability.DECEPTION,
    "Connected Honeynet": DetectionCapability.DECEPTION,
    "Integrated Honeynet": DetectionCapability.DECEPTION,
    "Standalone Honeynet": DetectionCapability.DECEPTION,

    # Tactics that don't map to detection capabilities
    "Harden": None,
    "Isolate": None,
    "Evict": None,
    "Restore": None,
    "Model": None,
    "Restore File": None,
    "File Encryption": None,
    "File Eviction": None,
    "Disk Encryption": None,
    "Network Isolation": None,
    "Execution Isolation": None,
    "IO Port Restriction": None,
    "Inbound Session Volume Restriction": None,
    "Network Resource Access Control": None,
    "Outbound Traffic Filtering": None,
    "Forward Resolution Domain Denylisting": None,
    "Forward Resolution IP Denylisting": None,
    "Reverse Resolution IP Denylisting": None,
    "Hierarchical Domain Denylisting": None,
    "DNS Denylisting": None,
    "DNS Allowlisting": None,
    "Restore Email": None,
}


# =============================================================================
# D3FEND Cache
# =============================================================================

CACHE_DIR = Path(__file__).parent.parent / "data" / "cyber"
CACHE_FILE = CACHE_DIR / "d3fend_cache.json"


class D3FENDCache:
    """Manages local cache of D3FEND API responses."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or CACHE_FILE

    def load_cache(self) -> Optional[Dict]:
        """Load cached D3FEND data. Returns None if no cache exists."""
        if not self.cache_path.exists():
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def save_cache(self, data: Dict) -> None:
        """Save D3FEND data to cache file."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def is_stale(self, max_age_days: int = 30) -> bool:
        """Check if cache is older than max_age_days."""
        cache = self.load_cache()
        if cache is None:
            return True
        fetched_at = cache.get("fetched_at", 0)
        age_seconds = time.time() - fetched_at
        return age_seconds > (max_age_days * 86400)

    def fetch_technique(self, technique_id: str) -> Optional[Dict]:
        """
        Fetch D3FEND data for a single ATT&CK technique.

        Uses urllib (stdlib) to avoid adding dependencies.
        Returns parsed JSON response or None on failure.
        """
        import urllib.request
        import urllib.error

        # D3FEND API uses the technique ID directly
        url = f"https://d3fend.mitre.org/api/offensive-technique/attack/{technique_id}.json"

        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
                OSError, TimeoutError):
            return None

    def fetch_all_techniques(self, technique_ids: List[str],
                             progress_callback=None) -> Dict:
        """
        Fetch D3FEND data for all given technique IDs.

        Returns a cache dict ready for save_cache().
        """
        techniques = {}
        for i, tid in enumerate(technique_ids):
            if progress_callback:
                progress_callback(i + 1, len(technique_ids), tid)

            response = self.fetch_technique(tid)
            if response is not None:
                # Extract defensive technique bindings
                defensive = self._extract_defensive_techniques(response)
                if defensive:
                    techniques[tid] = {"defensive_techniques": defensive}

        return {
            "version": "d3fend-v1.3.0",
            "fetched_at": time.time(),
            "technique_count": len(techniques),
            "techniques": techniques,
        }

    @staticmethod
    def _extract_defensive_techniques(response: Dict) -> List[Dict]:
        """Extract defensive technique info from D3FEND API response."""
        result = []
        try:
            bindings = response.get("off_to_def", {}).get("results", {}).get("bindings", [])
            seen = set()
            for binding in bindings:
                def_tech = binding.get("def_tech_label", {}).get("value", "")
                def_tech_id = binding.get("def_tech", {}).get("value", "")
                parent = binding.get("def_tech_parent_label", {}).get("value", "")
                tactic = binding.get("def_tactic_label", {}).get("value", "")

                # Extract D3FEND ID from URI (e.g., d3f:FileAnalysis -> FileAnalysis)
                if "/" in def_tech_id:
                    def_tech_id = def_tech_id.rsplit("/", 1)[-1]
                if "#" in def_tech_id:
                    def_tech_id = def_tech_id.rsplit("#", 1)[-1]

                key = (def_tech_id, parent)
                if key not in seen and def_tech:
                    seen.add(key)
                    result.append({
                        "id": def_tech_id,
                        "name": def_tech,
                        "parent": parent,
                        "tactic": tactic,
                    })
        except (KeyError, TypeError, AttributeError):
            pass
        return result


# =============================================================================
# D3FEND Mapper
# =============================================================================

class D3FENDMapper:
    """
    Maps D3FEND defensive techniques to DetectionCapability enum values.

    Uses cached D3FEND data to build a detection map. Falls back to
    empty dict if no cache is available (caller should use hand-coded
    TECHNIQUE_DETECTION_MAP as fallback).
    """

    def __init__(self, cache: Optional[D3FENDCache] = None):
        self.cache = cache or D3FENDCache()

    def build_detection_map(self) -> Dict[str, List[DetectionCapability]]:
        """
        Build a technique → List[DetectionCapability] map from cached D3FEND data.

        Returns empty dict if no cache is available.
        """
        cache_data = self.cache.load_cache()
        if cache_data is None:
            return {}

        techniques = cache_data.get("techniques", {})
        detection_map: Dict[str, List[DetectionCapability]] = {}

        for tech_id, tech_data in techniques.items():
            caps = self._map_technique(tech_data)
            if caps is not None:  # None means "no data", [] means "undetectable"
                detection_map[tech_id] = caps

        return detection_map

    def _map_technique(self, tech_data: Dict) -> Optional[List[DetectionCapability]]:
        """Map a single technique's D3FEND defensive techniques to DetectionCapabilities."""
        defensive = tech_data.get("defensive_techniques", [])
        if not defensive:
            return None

        capabilities = set()
        for def_tech in defensive:
            # Try mapping by parent category first, then by name
            parent = def_tech.get("parent", "")
            name = def_tech.get("name", "")
            tactic = def_tech.get("tactic", "")

            cap = D3FEND_CATEGORY_MAP.get(parent)
            if cap is None:
                cap = D3FEND_CATEGORY_MAP.get(name)
            if cap is None:
                cap = D3FEND_CATEGORY_MAP.get(tactic)

            if cap is not None:
                capabilities.add(cap)

        return sorted(capabilities, key=lambda c: c.value)

    def get_detection_capabilities(self, technique_id: str) -> Optional[List[DetectionCapability]]:
        """Get detection capabilities for a single technique from cache."""
        cache_data = self.cache.load_cache()
        if cache_data is None:
            return None

        tech_data = cache_data.get("techniques", {}).get(technique_id)
        if tech_data is None:
            return None

        return self._map_technique(tech_data)
