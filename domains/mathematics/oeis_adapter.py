# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
OEIS Adapter -- Online Encyclopedia of Integer Sequences

Loads sequences as objects and cross-references as morphisms.
393,842 sequences with cross-reference links forming a topology
of mathematical pattern relationships.

Source: oeis.org/stripped.gz (sequences), oeis.org/names.gz (names),
        github.com/oeis/oeisdata (full data under CC-BY-SA 4.0)
Format: Plain text (stripped format) + cross-reference lists
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.types import Object, Morphism
from core.category import Category
from domains.mathematics.schema import theorem_object, proof_morphism


class OEISAdapter:
    """
    Loads OEIS sequence data into a KOMPOSOS-IV Category.

    Sequences become Objects, cross-references become Morphisms.
    The cross-reference topology reveals deep pattern relationships.

    Usage:
        adapter = OEISAdapter("/path/to/oeis/data")
        result = adapter.load_into(category)
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path
        self._objects: List[Object] = []
        self._morphisms: List[Morphism] = []
        self._parsed = False

    def load_into(self, category: Category) -> Dict[str, int]:
        """Parse OEIS data and load into the given Category."""
        if not self._parsed:
            self._parse()
        return category.bulk_add(self._objects, self._morphisms)

    def _parse(self):
        """Parse OEIS files into Objects and Morphisms."""
        if self.data_path and os.path.isdir(self.data_path):
            self._parse_from_files()
        else:
            self._load_demo_data()
        self._parsed = True

    def _parse_from_files(self):
        """
        Parse actual OEIS data files.

        Expected files:
            stripped  (or stripped.gz): A-number, sequence values
            names     (or names.gz): A-number, description
            Cross-references parsed from oeisdata repo or b-files
        """
        # Parse names file
        names_path = os.path.join(self.data_path, "names")
        if os.path.exists(names_path):
            with open(names_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(" ", 1)
                    if len(parts) >= 2:
                        seq_id = parts[0]  # e.g., A000001
                        name = parts[1]
                        self._objects.append(
                            Object(
                                name=seq_id,
                                type_name="Sequence",
                                metadata={"description": name, "field": "sequences"},
                                provenance="oeis",
                            )
                        )

        # Parse cross-references from oeisdata repo structure
        # Each sequence directory has a file with xref lines
        if os.path.isdir(os.path.join(self.data_path, "seq")):
            self._parse_crossrefs_from_repo()

    def _parse_crossrefs_from_repo(self):
        """Parse cross-references from oeisdata GitHub repo structure."""
        seq_dir = os.path.join(self.data_path, "seq")
        for prefix_dir in os.listdir(seq_dir):
            full_dir = os.path.join(seq_dir, prefix_dir)
            if not os.path.isdir(full_dir):
                continue
            for fname in os.listdir(full_dir):
                if not fname.startswith("A") or not fname.endswith(".txt"):
                    continue
                seq_id = fname.replace(".txt", "")
                filepath = os.path.join(full_dir, fname)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("%Y"):
                                # Cross-reference line
                                refs = self._extract_a_numbers(line)
                                for ref in refs:
                                    if ref != seq_id:
                                        self._morphisms.append(
                                            proof_morphism(
                                                name=f"oeis:{seq_id}->{ref}",
                                                source_thm=seq_id,
                                                target_thm=ref,
                                                confidence=0.7,
                                                proof_type="cross_reference",
                                                source="oeis",
                                            )
                                        )
                except Exception:
                    continue

    @staticmethod
    def _extract_a_numbers(text: str) -> List[str]:
        """Extract OEIS A-numbers (e.g., A000001) from text."""
        import re
        return re.findall(r"A\d{6}", text)

    def _load_demo_data(self):
        """Load demo data for testing without real OEIS data."""
        demo_sequences = [
            ("A000001", "Number of groups of order n", "group_theory"),
            ("A000040", "The prime numbers", "number_theory"),
            ("A000045", "Fibonacci numbers", "combinatorics"),
            ("A000079", "Powers of 2", "number_theory"),
            ("A000108", "Catalan numbers", "combinatorics"),
            ("A000142", "Factorial numbers", "combinatorics"),
            ("A000217", "Triangular numbers", "number_theory"),
            ("A000290", "Square numbers", "number_theory"),
            ("A000396", "Perfect numbers", "number_theory"),
            ("A000583", "Fourth powers", "number_theory"),
        ]

        for seq_id, desc, field in demo_sequences:
            self._objects.append(
                Object(
                    name=seq_id,
                    type_name="Sequence",
                    metadata={"description": desc, "field": field},
                    provenance="oeis",
                )
            )

        demo_xrefs = [
            ("A000040", "A000045", 0.5),   # primes <-> Fibonacci
            ("A000045", "A000108", 0.6),   # Fibonacci <-> Catalan
            ("A000108", "A000142", 0.7),   # Catalan <-> factorial
            ("A000079", "A000290", 0.5),   # powers of 2 <-> squares
            ("A000217", "A000290", 0.8),   # triangular <-> squares
            ("A000396", "A000040", 0.6),   # perfect numbers <-> primes
            ("A000001", "A000040", 0.4),   # groups <-> primes
        ]

        for src, tgt, conf in demo_xrefs:
            self._morphisms.append(
                proof_morphism(name=f"oeis:{src}->{tgt}", source_thm=src, target_thm=tgt,
                               confidence=conf, proof_type="cross_reference", source="oeis")
            )

    def inspect(self, n: int = 10) -> Dict[str, Any]:
        """Print N sample objects and morphisms for data inspection."""
        if not self._parsed:
            self._parse()
        return {
            "total_objects": len(self._objects),
            "total_morphisms": len(self._morphisms),
            "sample_objects": [
                {"name": o.name, "type": o.type_name, "desc": o.metadata.get("description", "")}
                for o in self._objects[:n]
            ],
            "sample_morphisms": [
                {"source": m.source, "target": m.target, "confidence": m.confidence}
                for m in self._morphisms[:n]
            ],
        }
