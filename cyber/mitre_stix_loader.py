# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
MITRE ATT&CK STIX 2.1 Loader

Downloads and parses the official MITRE ATT&CK Enterprise dataset from the
MITRE CTI GitHub repository. Caches locally and refreshes weekly.

Uses only Python stdlib (urllib, json) — zero dependencies.
"""

import json
import logging
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger("komposos.mitre_stix")

STIX_URL = (
    "https://raw.githubusercontent.com/mitre/cti/master/"
    "enterprise-attack/enterprise-attack.json"
)

CACHE_DIR = Path(__file__).parent.parent / "data" / "cyber" / "mitre"
CACHE_FILE = CACHE_DIR / "enterprise-attack.json"

# Map MITRE tactic x-mitre-shortname to our MITRETactic enum names
_TACTIC_SHORTNAME_MAP = {
    "reconnaissance": "RECONNAISSANCE",
    "resource-development": "RESOURCE_DEVELOPMENT",
    "initial-access": "INITIAL_ACCESS",
    "execution": "EXECUTION",
    "persistence": "PERSISTENCE",
    "privilege-escalation": "PRIVILEGE_ESCALATION",
    "defense-evasion": "DEFENSE_EVASION",
    "credential-access": "CREDENTIAL_ACCESS",
    "discovery": "DISCOVERY",
    "lateral-movement": "LATERAL_MOVEMENT",
    "collection": "COLLECTION",
    "command-and-control": "COMMAND_AND_CONTROL",
    "exfiltration": "EXFILTRATION",
    "impact": "IMPACT",
}


@dataclass
class STIXTechnique:
    """Parsed MITRE ATT&CK technique from STIX data."""
    technique_id: str
    name: str
    description: str
    tactics: List[str]  # MITRETactic enum names
    platforms: List[str]
    data_sources: List[str]
    is_subtechnique: bool = False


class MITRESTIXLoader:
    """Loads MITRE ATT&CK techniques from official STIX 2.1 JSON."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_file = self.cache_dir / "enterprise-attack.json"

    def is_cache_fresh(self, max_age_days: int = 7) -> bool:
        """Check if the local cache exists and is younger than max_age_days."""
        if not self.cache_file.exists():
            return False
        age = time.time() - self.cache_file.stat().st_mtime
        return age < (max_age_days * 86400)

    def fetch_and_cache(self, force: bool = False) -> bool:
        """
        Download STIX data from GitHub and save to local cache.

        Returns True if fresh data was downloaded, False on failure.
        Skips download if cache is fresh unless force=True.
        """
        if not force and self.is_cache_fresh():
            logger.info("STIX cache is fresh, skipping download")
            return True

        logger.info(f"Downloading MITRE ATT&CK STIX data from {STIX_URL}")
        try:
            req = urllib.request.Request(
                STIX_URL,
                headers={"Accept": "application/json", "User-Agent": "KOMPOSOS-III/1.0"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()

            # Validate it's valid JSON before saving
            json.loads(data)

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_bytes(data)
            logger.info(f"STIX data cached at {self.cache_file} ({len(data)} bytes)")
            return True

        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
            logger.warning(f"Failed to download STIX data: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.warning(f"Downloaded STIX data is not valid JSON: {e}")
            return False

    def load_techniques(self) -> List[STIXTechnique]:
        """
        Parse STIX JSON and return list of ATT&CK techniques.

        Tries cache first; downloads if no cache exists.
        Returns empty list on failure.
        """
        if not self.cache_file.exists():
            if not self.fetch_and_cache():
                return []

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                bundle = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read STIX cache: {e}")
            return []

        objects = bundle.get("objects", [])

        # Build tactic ID -> shortname map from STIX x-mitre-tactic objects
        tactic_id_map: Dict[str, str] = {}
        for obj in objects:
            if obj.get("type") == "x-mitre-tactic":
                shortname = obj.get("x_mitre_shortname", "")
                # x-mitre-tactic objects have external_references with tactic IDs
                for ref in obj.get("external_references", []):
                    if ref.get("source_name") == "mitre-attack":
                        tactic_id_map[ref["external_id"]] = shortname

        techniques: List[STIXTechnique] = []
        for obj in objects:
            if obj.get("type") != "attack-pattern":
                continue
            # Skip revoked/deprecated
            if obj.get("revoked", False) or obj.get("x_mitre_deprecated", False):
                continue

            # Extract technique ID from external_references
            technique_id = ""
            for ref in obj.get("external_references", []):
                if ref.get("source_name") == "mitre-attack":
                    technique_id = ref.get("external_id", "")
                    break

            if not technique_id:
                continue

            # Extract tactics from kill_chain_phases
            tactics = []
            for phase in obj.get("kill_chain_phases", []):
                if phase.get("kill_chain_name") == "mitre-attack":
                    phase_name = phase.get("phase_name", "")
                    tactic_enum = _TACTIC_SHORTNAME_MAP.get(phase_name)
                    if tactic_enum:
                        tactics.append(tactic_enum)

            # Extract platforms
            platforms = obj.get("x_mitre_platforms", [])

            # Extract data sources
            data_sources = []
            for ds in obj.get("x_mitre_data_sources", []):
                data_sources.append(ds.split(":")[0].strip())
            data_sources = list(set(data_sources))

            # Check if sub-technique
            is_sub = obj.get("x_mitre_is_subtechnique", False)

            techniques.append(STIXTechnique(
                technique_id=technique_id,
                name=obj.get("name", ""),
                description=(obj.get("description", "") or "")[:500],
                tactics=tactics,
                platforms=platforms,
                data_sources=data_sources,
                is_subtechnique=is_sub,
            ))

        logger.info(f"Loaded {len(techniques)} techniques from STIX data")
        return techniques
