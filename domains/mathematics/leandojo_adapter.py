# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
LeanDojo Adapter -- LeanDojo Benchmark 4 / Mathlib4

Loads theorem dependency data from LeanDojo extraction of Lean4/Mathlib.
122,517 theorems/proofs, 259,580 tactics, 167,779 premises.

Source: HuggingFace leanprover-community/mathlib4
Format: corpus.jsonl - JSONL with path, imports, premises per file

Each line in corpus.jsonl:
  {
    "path": "Mathlib/Topology/Basic.lean",
    "imports": ["Mathlib.Data.Set.Basic", ...],
    "premises": [
      {"full_name": "id", "code": "...", "kind": "commanddeclaration"},
      {"full_name": "Function.comp", "code": "...", "kind": "commanddeclaration"},
      ...
    ]
  }

Dependencies: file A imports file B → all premises in B are dependencies
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple

from core.types import Object, Morphism
from core.category import Category
from domains.mathematics.schema import (
    theorem_object,
    definition_object,
    proof_morphism,
)


class LeanDojoAdapter:
    """
    Loads LeanDojo/Mathlib4 data into a KOMPOSOS-IV Category.

    Usage:
        adapter = LeanDojoAdapter("/path/to/leandojo/data")
        result = adapter.load_into(category)
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path
        self._objects: List[Object] = []
        self._morphisms: List[Morphism] = []
        self._parsed = False
        # Track premises we've seen to avoid duplicates
        self._premise_names: Set[str] = set()

    def load_into(self, category: Category) -> Dict[str, int]:
        """Parse LeanDojo data and load into the given Category."""
        if not self._parsed:
            self._parse()
        return category.bulk_add(self._objects, self._morphisms)

    def _parse(self):
        """Parse LeanDojo files into Objects and Morphisms."""
        if self.data_path and os.path.isdir(self.data_path):
            self._parse_from_files()
        else:
            self._load_demo_data()
        self._parsed = True

    def _parse_from_files(self):
        """
        Parse actual LeanDojo corpus.jsonl file.

        Format: JSONL with one line per Lean file
        Each line: {"path": str, "imports": [str], "premises": [{full_name, code, kind}]}

        Dependencies are encoded as:
          - File-level: imports list (file A depends on file B)
          - Premise-level: each premise depends on premises from imported files
        """
        corpus_path = os.path.join(self.data_path, "corpus.jsonl")
        if not os.path.exists(corpus_path):
            # Try direct path
            if self.data_path.endswith(".jsonl"):
                corpus_path = self.data_path
            else:
                # Search for corpus.jsonl
                for root, dirs, files in os.walk(self.data_path):
                    if "corpus.jsonl" in files:
                        corpus_path = os.path.join(root, "corpus.jsonl")
                        break

        if not os.path.exists(corpus_path):
            raise FileNotFoundError(
                f"Could not find corpus.jsonl in {self.data_path}"
            )

        # First pass: collect all premises from all files
        file_premises: Dict[str, List[str]] = {}  # path -> list of premise names
        premise_to_file: Dict[str, str] = {}  # premise_name -> file path

        print(f"LeanDojo: Reading corpus from {corpus_path}")
        line_count = 0
        file_count = 0

        with open(corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line_count += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                file_path = data.get("path", "")
                if not file_path:
                    continue

                file_count += 1
                premises = data.get("premises", [])
                premise_names = []
                for p in premises:
                    if isinstance(p, dict):
                        pname = p.get("full_name", "")
                        if pname:
                            premise_names.append(pname)
                            premise_to_file[pname] = file_path

                file_premises[file_path] = premise_names

        print(f"LeanDojo: Processed {file_count} files, {line_count} lines")
        print(f"LeanDojo: Found {len(premise_to_file)} unique premises")

        # Second pass: create objects and morphisms
        self._create_objects_and_morphisms(file_premises, premise_to_file, corpus_path)

    def _create_objects_and_morphisms(
        self,
        file_premises: Dict[str, List[str]],
        premise_to_file: Dict[str, str],
        corpus_path: str,
    ):
        """Create theorem objects and dependency morphisms."""
        # Create objects for all premises
        for premise_name, file_path in premise_to_file.items():
            if premise_name in self._premise_names:
                continue  # Skip duplicates
            self._premise_names.add(premise_name)

            # Extract field from module path
            field = self._extract_field(premise_name)

            obj = theorem_object(
                name=premise_name,
                statement="",  # Code not stored, available in corpus
                field=field,
                source="leandojo",
                file_path=file_path,
            )
            self._objects.append(obj)

        # Create morphisms: file imports create dependencies
        # If file A imports file B, then premises in A depend on premises in B
        morphism_count = 0
        with open(corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                file_path = data.get("path", "")
                imports = data.get("imports", [])
                premises = data.get("premises", [])

                if not imports or not premises:
                    continue

                # Get premise names in this file
                src_premises = [
                    p.get("full_name", "")
                    for p in premises
                    if isinstance(p, dict) and p.get("full_name")
                ]

                # Get all premise names from imported files
                for imp_path in imports:
                    tgt_premises = file_premises.get(imp_path, [])
                    # Create dependency edges: src_premises → tgt_premises
                    for src in src_premises[:5]:  # Limit to avoid explosion
                        for tgt in tgt_premises[:10]:
                            if src != tgt:
                                self._morphisms.append(
                                    proof_morphism(
                                        name=f"lean:{src}->{tgt}",
                                        source_thm=src,
                                        target_thm=tgt,
                                        confidence=0.9,
                                        proof_type="import",
                                        source="leandojo",
                                    )
                                )
                                morphism_count += 1
                                if morphism_count % 100000 == 0:
                                    print(f"LeanDojo: Created {morphism_count} morphisms...")

        print(f"LeanDojo: Total morphisms: {len(self._morphisms)}")

    def _extract_field(self, premise_name: str) -> str:
        """Extract mathematical field from Lean4 qualified name."""
        parts = premise_name.split(".")
        if len(parts) < 2:
            return "unknown"

        # Mathlib.Topology.Order.IntermediateValue → topology
        # Mathlib.Data.Nat.Factors → data (or number_theory for Nat)
        if parts[0] == "Mathlib" and len(parts) >= 2:
            module = parts[1].lower()
            # Map common modules to fields
            field_map = {
                "topology": "general_topology",
                "analysis": "real_analysis",
                "grouptheory": "group_theory",
                "data": "logic_foundations",
                "categorytheory": "category_theory",
                "linearalgebra": "linear_algebra",
                "measuretheory": "measure_theory",
                "numbertheory": "number_theory",
                "algebra": "algebra",
                "order": "order_lattices",
                "settheory": "logic_foundations",
            }
            return field_map.get(module, module)

        return parts[0].lower()

    def _load_demo_data(self):
        """Load demo data for testing without real LeanDojo data."""
        demo_theorems = [
            ("Mathlib.Topology.Order.IntermediateValue", "topology", "Intermediate Value Theorem in Lean4"),
            ("Mathlib.Analysis.Calculus.MeanValue", "analysis", "Mean Value Theorem"),
            ("Mathlib.GroupTheory.Sylow", "grouptheory", "Sylow theorems"),
            ("Mathlib.GroupTheory.Coset", "grouptheory", "Lagrange's theorem"),
            ("Mathlib.Data.Nat.Factors", "data", "Fundamental theorem of arithmetic"),
            ("Mathlib.CategoryTheory.Yoneda", "categorytheory", "Yoneda lemma"),
            ("Mathlib.Topology.Sequences", "topology", "Bolzano-Weierstrass"),
            ("Mathlib.Analysis.InnerProductSpace.Basic", "analysis", "Cauchy-Schwarz"),
            ("Mathlib.LinearAlgebra.Dimension", "linearalgebra", "Rank-nullity"),
            ("Mathlib.MeasureTheory.Integral.Bochner", "measuretheory", "Dominated convergence"),
        ]

        for name, field, statement in demo_theorems:
            self._objects.append(
                theorem_object(name=name, statement=statement, field=field, source="leandojo")
            )

        demo_deps = [
            ("Mathlib.Topology.Order.IntermediateValue", "Mathlib.Topology.Sequences", 1.0),
            ("Mathlib.Analysis.Calculus.MeanValue", "Mathlib.Topology.Order.IntermediateValue", 1.0),
            ("Mathlib.GroupTheory.Sylow", "Mathlib.GroupTheory.Coset", 1.0),
            ("Mathlib.Analysis.InnerProductSpace.Basic", "Mathlib.LinearAlgebra.Dimension", 0.9),
            ("Mathlib.MeasureTheory.Integral.Bochner", "Mathlib.Analysis.InnerProductSpace.Basic", 0.85),
            ("Mathlib.CategoryTheory.Yoneda", "Mathlib.Data.Nat.Factors", 0.5),
        ]

        for src, tgt, conf in demo_deps:
            self._morphisms.append(
                proof_morphism(name=f"lean:{src}->{tgt}", source_thm=src, target_thm=tgt,
                               confidence=conf, source="leandojo")
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
