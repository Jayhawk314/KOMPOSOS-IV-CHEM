# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS-III Literature Ground Truth Loader
============================================

Loads curated material compatibility pairs from published literature.
Each pair includes material names, expected compatibility, and citations.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class GroundTruthPair:
    id: int
    material_a: str
    material_b: str
    domain: str
    expected_compatible: bool
    citation: str
    doi: Optional[str] = None
    isbn: Optional[str] = None
    standard_id: Optional[str] = None
    url: Optional[str] = None
    manual_source: Optional[str] = None
    source_type: Optional[str] = None
    evidence_basis: Optional[str] = None
    notes: Optional[str] = None
    electrolyte: Optional[str] = None
    role: Optional[str] = None
    voltage_context: Optional[str] = None
    coating: Optional[str] = None
    processing_route: Optional[str] = None
    compatibilizer: Optional[str] = None
    interface_type: Optional[str] = None
    environment: Optional[str] = None
    temperature_C: Optional[float] = None
    used_for_tuning: Optional[bool] = None

class LiteratureGroundTruth:
    def __init__(self, ground_truth_dir: Optional[Path] = None):
        if ground_truth_dir is None:
            self.ground_truth_dir = Path(__file__).parent / "ground_truth"
        else:
            self.ground_truth_dir = ground_truth_dir
            
    def load_domain(self, domain: str) -> List[GroundTruthPair]:
        """Load all pairs for a specific domain."""
        file_path = self.ground_truth_dir / f"{domain}.json"
        if not file_path.exists():
            return []
            
        with open(file_path, "r") as f:
            data = json.load(f)
            
        pairs = []
        for p in data.get("pairs", []):
            pairs.append(GroundTruthPair(
                id=p.get("id"),
                material_a=p["material_a"],
                material_b=p["material_b"],
                domain=domain,
                expected_compatible=p["expected_compatible"],
                citation=p["citation"],
                doi=p.get("doi"),
                isbn=p.get("isbn"),
                standard_id=p.get("standard_id"),
                url=p.get("url"),
                manual_source=p.get("manual_source"),
                source_type=p.get("source_type"),
                evidence_basis=p.get("evidence_basis"),
                notes=p.get("notes"),
                electrolyte=p.get("electrolyte"),
                role=p.get("role"),
                voltage_context=p.get("voltage_context"),
                coating=p.get("coating") or p.get("metal_coating"),
                processing_route=p.get("processing_route"),
                compatibilizer=p.get("compatibilizer"),
                interface_type=p.get("interface_type"),
                environment=p.get("environment"),
                temperature_C=p.get("temperature_C"),
                used_for_tuning=p.get("used_for_tuning"),
            ))
        return pairs

    def load_all(self) -> Dict[str, List[GroundTruthPair]]:
        """Load all pairs across all domains."""
        results = {}
        if not self.ground_truth_dir.exists():
            return results
            
        for file in self.ground_truth_dir.glob("*.json"):
            domain = file.stem
            results[domain] = self.load_domain(domain)
        return results

if __name__ == "__main__":
    loader = LiteratureGroundTruth()
    all_data = loader.load_all()
    for domain, pairs in all_data.items():
        print(f"Domain: {domain}, Pairs: {len(pairs)}")
