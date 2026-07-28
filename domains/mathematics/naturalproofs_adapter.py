# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
NaturalProofs Adapter -- ProofWiki + Stacks Project

Loads theorem/proof data from the NaturalProofs corpus (wellecks/naturalproofs).
~25K examples with reference graphs linking theorems to their dependencies.

Source: github.com/wellecks/naturalproofs
Format: JSON with dataset.theorems array

Each theorem:
  {
    "id": 0,
    "type": "theorem",
    "label": "Closed Form for Triangular Numbers",
    "title": "Closed Form for Triangular Numbers",
    "categories": ["Triangular Numbers", "Sums of Sequences", ...],
    "contents": ["The [[Definition:...]]...", "..."],
    "refs": ["Definition:Closed-Form Expression", ...],
    "ref_ids": [20933, 20514],
    "proofs": [{"contents": [...], "ref_ids": [...]}]
  }

The reference graph IS the morphism graph: theorem -> ref_ids = dependencies.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Set

from core.types import Object, Morphism
from core.category import Category
from domains.mathematics.schema import (
    theorem_object,
    definition_object,
    proof_morphism,
)


class NaturalProofsAdapter:
    """
    Loads NaturalProofs data into a KOMPOSOS-IV Category.

    Usage:
        adapter = NaturalProofsAdapter("/path/to/naturalproofs")
        result = adapter.load_into(category)
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path
        self._objects: List[Object] = []
        self._morphisms: List[Morphism] = []
        self._parsed = False
        self._theorem_ids: Set[str] = set()

    def load_into(self, category: Category) -> Dict[str, int]:
        """Parse NaturalProofs data and load into the given Category."""
        if not self._parsed:
            self._parse()
        return category.bulk_add(self._objects, self._morphisms)

    def _parse(self):
        """Parse NaturalProofs files into Objects and Morphisms."""
        if self.data_path and os.path.isdir(self.data_path):
            self._parse_from_files()
        else:
            self._load_demo_data()
        self._parsed = True

    def _parse_from_files(self):
        """
        Parse actual NaturalProofs JSON files.

        Expected structure:
            data_path/
                naturalproofs_proofwiki.json
                naturalproofs_stacks.json
                naturalproofs_textbooks.json (optional)

        Each JSON contains:
            dataset: {
                theorems: [{id, label, title, categories, contents, refs, ref_ids, proofs}]
            }
        """
        for source_file in (
            "naturalproofs_proofwiki.json",
            "naturalproofs_stacks.json",
            "naturalproofs_textbooks.json",
        ):
            filepath = os.path.join(self.data_path, source_file)
            if not os.path.exists(filepath):
                continue

            source_tag = source_file.replace("naturalproofs_", "").replace(".json", "")
            print(f"NaturalProofs: Reading {source_file}...")

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                count = self._process_naturalproofs_json(data, source_tag)
                print(f"NaturalProofs ({source_tag}): Processed {count} theorems")
            except Exception as e:
                print(f"NaturalProofs: Error reading {source_file}: {e}")
                continue

    def _process_naturalproofs_json(self, data, source_tag: str) -> int:
        """Process a single NaturalProofs JSON file. Returns theorem count."""
        # Handle various formats:
        # 1. Direct list: [...]
        # 2. Dataset as list: {"dataset": [...]}
        # 3. Dataset as dict with theorems: {"dataset": {"theorems": [...]}}
        # 4. Direct theorems: {"theorems": [...]}
        theorems = []
        
        if isinstance(data, list):
            theorems = data
        elif isinstance(data, dict):
            # Try {"dataset": {"theorems": [...]}}
            dataset = data.get("dataset")
            if isinstance(dataset, dict):
                theorems = dataset.get("theorems", [])
            elif isinstance(dataset, list):
                theorems = dataset
            else:
                # Try {"theorems": [...]}
                theorems = data.get("theorems", [])

        count = 0
        # First pass: create all theorem objects
        for item in theorems:
            if not isinstance(item, dict):
                continue

            item_id = str(item.get("id", ""))
            if not item_id:
                continue

            unique_id = f"np:{source_tag}:{item_id}"
            if unique_id in self._theorem_ids:
                continue
            self._theorem_ids.add(unique_id)

            title = item.get("label", item.get("title", unique_id))
            contents_list = item.get("contents", [])
            # Contents is a list of strings (proof steps)
            contents = " ".join(contents_list) if isinstance(contents_list, list) else str(contents_list)

            categories = item.get("categories", [])
            field = self._extract_field(categories)

            obj = theorem_object(
                name=unique_id,
                statement=contents[:1000],  # Truncate long statements
                field=field,
                source=f"naturalproofs_{source_tag}",
                title=title,
                categories=categories,
            )
            self._objects.append(obj)
            count += 1

        # Build ID to unique_id mapping for morphism creation
        id_to_unique = {
            str(item.get("id", "")): f"np:{source_tag}:{item.get('id', '')}"
            for item in theorems
            if isinstance(item, dict) and "id" in item
        }

        # Second pass: create dependency morphisms from ref_ids
        morphism_count = 0
        for item in theorems:
            if not isinstance(item, dict):
                continue

            item_id = str(item.get("id", ""))
            if not item_id:
                continue

            src_name = f"np:{source_tag}:{item_id}"
            ref_ids = item.get("ref_ids", [])

            for ref_id in ref_ids:
                ref_id_str = str(ref_id)
                tgt_name = id_to_unique.get(ref_id_str, f"np:{source_tag}:{ref_id_str}")

                if src_name != tgt_name:
                    self._morphisms.append(
                        proof_morphism(
                            name=f"np:{src_name}->{tgt_name}",
                            source_thm=src_name,
                            target_thm=tgt_name,
                            confidence=0.95,
                            proof_type="reference",
                            source=f"naturalproofs_{source_tag}",
                        )
                    )
                    morphism_count += 1

        print(f"NaturalProofs ({source_tag}): Created {morphism_count} dependency morphisms")
        return count

    def _extract_field(self, categories: List[str]) -> str:
        """Extract mathematical field from category list."""
        if not categories:
            return "unknown"

        # Map common ProofWiki categories to fields
        field_keywords = {
            "topology": "general_topology",
            "analysis": "real_analysis",
            "algebra": "algebra",
            "group": "group_theory",
            "ring": "commutative_algebra",
            "field": "field_theory",
            "number": "number_theory",
            "prime": "number_theory",
            "sequence": "real_analysis",
            "series": "real_analysis",
            "calculus": "real_analysis",
            "derivative": "real_analysis",
            "integral": "measure_theory",
            "measure": "measure_theory",
            "probability": "probability",
            "statistics": "statistics",
            "geometry": "geometry",
            "differential": "differential_geometry",
            "manifold": "differential_geometry",
            "category": "category_theory",
            "functor": "category_theory",
            "logic": "logic_foundations",
            "set theory": "logic_foundations",
            "combinatorics": "combinatorics",
            "graph": "combinatorics",
            "matrix": "linear_algebra",
            "vector": "linear_algebra",
            "linear": "linear_algebra",
        }

        for cat in categories:
            cat_lower = cat.lower()
            for keyword, field in field_keywords.items():
                if keyword in cat_lower:
                    return field

        # Default to first category
        return categories[0].lower().replace(" ", "_")

    def _load_demo_data(self):
        """Load demo data for testing without real NaturalProofs data."""
        demo_theorems = [
            ("np:pw:1001", "Intermediate Value Theorem", "general_topology"),
            ("np:pw:1002", "Bolzano-Weierstrass Theorem", "real_analysis"),
            ("np:pw:1003", "Heine-Borel Theorem", "general_topology"),
            ("np:pw:1004", "Cauchy-Schwarz Inequality", "linear_algebra"),
            ("np:pw:1005", "Fundamental Theorem of Calculus", "real_analysis"),
            ("np:pw:1006", "Mean Value Theorem", "real_analysis"),
            ("np:pw:1007", "Lagrange's Theorem (Groups)", "group_theory"),
            ("np:pw:1008", "Sylow's Theorems", "group_theory"),
            ("np:pw:1009", "Stone-Weierstrass Theorem", "functional_analysis"),
            ("np:pw:1010", "Brouwer Fixed Point Theorem", "algebraic_topology"),
        ]

        for name, statement, field in demo_theorems:
            self._objects.append(
                theorem_object(name=name, statement=statement, field=field,
                               source="naturalproofs_proofwiki")
            )

        demo_deps = [
            ("np:pw:1001", "np:pw:1002", 0.9),   # IVT uses B-W
            ("np:pw:1003", "np:pw:1002", 0.85),   # Heine-Borel uses B-W
            ("np:pw:1005", "np:pw:1006", 0.9),    # FTC uses MVT
            ("np:pw:1006", "np:pw:1001", 0.8),    # MVT uses IVT
            ("np:pw:1008", "np:pw:1007", 0.95),   # Sylow uses Lagrange
            ("np:pw:1009", "np:pw:1003", 0.7),    # Stone-W uses Heine-Borel
            ("np:pw:1010", "np:pw:1001", 0.6),    # Brouwer uses IVT
        ]

        for src, tgt, conf in demo_deps:
            self._morphisms.append(
                proof_morphism(name=f"np:{src}->{tgt}", source_thm=src, target_thm=tgt,
                               confidence=conf, source="naturalproofs_proofwiki")
            )

    def inspect(self, n: int = 10) -> Dict[str, Any]:
        """Print N sample objects and morphisms for data inspection."""
        if not self._parsed:
            self._parse()
        return {
            "total_objects": len(self._objects),
            "total_morphisms": len(self._morphisms),
            "sample_objects": [
                {"name": o.name, "type": o.type_name, "field": o.metadata.get("field", "")}
                for o in self._objects[:n]
            ],
            "sample_morphisms": [
                {"name": m.name, "source": m.source, "target": m.target}
                for m in self._morphisms[:n]
            ],
        }
