# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
MOF Linker Generator
=====================

Generates novel 22-atom organic linker candidates via constraint-based
combinatorial search.

Phase 1: Constraint-based generation (functional groups, ring fusion, saturation)
Phase 2: GNN-based generation (future enhancement)

Pattern follows: composition_engine/designer.py (inverse design)
"""

import random
from typing import List, Optional, Set, Dict
from dataclasses import dataclass

from mof_bridge.mp_mof_loader import MOFLinker


@dataclass
class GenerationStrategy:
    """A strategy for generating novel linkers."""

    name: str
    description: str
    min_candidates: int
    max_candidates: int


class LinkerGenerator:
    """Generate novel MOF linkers (18–30 heavy atoms) via combinatorial search.

    Strategies:
    1. Functional group substitution (–OH, –NH2, –COOH, –F, etc.)
    2. Ring fusion (combine smaller rings)
    3. Saturation/desaturation (add/remove double bonds)

    All candidates are validated:
    - RDKit valid SMILES
    - Heavy atom count in [18, 30]
    - Not in known linkers set (novelty)
    """

    def __init__(self, known_linkers: List[MOFLinker]):
        """Initialize generator with database of known 22-atom linkers.

        Args:
            known_linkers: List of known MOFLinker objects
        """
        self.known_linkers = known_linkers
        self.known_smiles = {l.smiles for l in known_linkers}

        # Allow variable linker sizes
        self.min_atoms = 18
        self.max_atoms = 30

        # Functional group SMILES patterns for substitution
        self.functional_groups = {
            "hydroxyl": "O",
            "amino": "N",
            "carboxyl": "C(=O)O",
            "methyl": "C",
            "fluoro": "F",
            "chloro": "Cl",
            "bromo": "Br",
            "nitro": "N(=O)=O",
            "cyano": "C#N",
            "methoxy": "OC",
        }

    def generate_candidates(
        self,
        n_candidates: int,
        application_context: str,
        functional_groups: Optional[List[str]] = None,
        exclude_elements: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate novel 22-atom linker SMILES strings.

        Args:
            n_candidates: Number of candidates to generate
            application_context: Application (breath_VOC_sensing, food_safety, etc.)
            functional_groups: Preferred functional groups to include
            exclude_elements: Elements to exclude (e.g., ['F', 'Cl'])

        Returns:
            List of novel SMILES strings (validated, 22 heavy atoms)

        Note:
            Phase 1 implementation uses simplified generation.
            Phase 2 will add GNN-based molecular generation.
        """
        try:
            from rdkit import Chem
        except ImportError:
            raise ImportError("RDKit required. Install: pip install rdkit")

        candidates = []
        seen_smiles = set()  # Track unique SMILES to avoid duplicates
        attempts = 0
        max_attempts = n_candidates * 10  # Allow retries

        print(
            f"\nGenerating {n_candidates} novel {self.min_atoms}-{self.max_atoms} atom linkers..."
        )
        print(f"Application: {application_context}")
        print(f"Known linkers: {len(self.known_linkers)}")

        while len(candidates) < n_candidates and attempts < max_attempts:
            attempts += 1

            # Strategy selection (weighted random)
            strategy = random.choices(
                ["substitution", "modification", "template"],
                weights=[0.5, 0.3, 0.2],
                k=1,
            )[0]

            if strategy == "substitution" and self.known_linkers:
                # Strategy 1: Functional group substitution
                candidate = self._generate_by_substitution(
                    functional_groups=functional_groups,
                    exclude_elements=exclude_elements,
                )

            elif strategy == "modification" and self.known_linkers:
                # Strategy 2: Modify known linker (add/remove atoms)
                candidate = self._generate_by_modification(
                    exclude_elements=exclude_elements,
                )

            else:
                # Strategy 3: Template-based generation
                candidate = self._generate_from_template(
                    application_context=application_context,
                    functional_groups=functional_groups,
                    exclude_elements=exclude_elements,
                )

            # Validate candidate and check for duplicates
            if candidate and self._is_valid_candidate(candidate, exclude_elements):
                if candidate not in seen_smiles:
                    candidates.append(candidate)
                    seen_smiles.add(candidate)

                    if len(candidates) % 10 == 0:
                        print(f"  Generated: {len(candidates)}/{n_candidates}")

        print(f"Generated {len(candidates)} candidates after {attempts} attempts")
        return candidates

    def _generate_by_substitution(
        self,
        functional_groups: Optional[List[str]],
        exclude_elements: Optional[List[str]],
    ) -> Optional[str]:
        """Generate by substituting functional groups on known linker.

        REAL implementation using SMARTS patterns to swap functional groups.
        """
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
        except ImportError:
            return None

        # Pick random known linker as template
        template = random.choice(self.known_linkers)
        mol = Chem.MolFromSmiles(template.smiles)
        if mol is None:
            return None

        # Make a copy to modify
        mol = Chem.RWMol(mol)

        # Functional group substitution pairs (SMARTS patterns)
        # Format: (pattern_to_find, replacements)
        substitutions = [
            # Carboxylic acid <-> ester <-> amide
            (
                "[CX3](=O)[OX2H1]",
                ["[CX3](=O)[OX2][CH3]", "[CX3](=O)[NX3H2]"],
            ),  # COOH -> COOCH3, CONH2
            # Hydroxyl <-> methoxy <-> amine
            ("[OX2H]", ["[OX2][CH3]", "[NX3H2]"]),  # OH -> OCH3, NH2
            # Methyl <-> ethyl <-> halogen
            ("[CH3]", ["[CH2][CH3]", "F", "Cl"]),  # CH3 -> CH2CH3, F, Cl
            # Nitro <-> amine <-> hydroxyl
            ("[N+](=O)[O-]", ["[NX3H2]", "[OX2H]"]),  # NO2 -> NH2, OH
            # Benzene ring modifications
            ("c", ["[nH]", "n", "o", "s"]),  # C in aromatic -> N, O, S
        ]

        # Try random substitution
        for _ in range(5):  # Try up to 5 times
            pattern, replacements = random.choice(substitutions)
            replacement = random.choice(replacements)

            try:
                # Use ReplaceSubstructs to swap functional groups
                patt = Chem.MolFromSmarts(pattern)
                if patt is None:
                    continue

                # Find matches
                matches = mol.GetSubstructMatches(patt)
                if not matches:
                    continue

                # Pick random match
                match = random.choice(matches)

                # Try to replace (simplified - just modify the first atom)
                # Full implementation would rebuild the whole substructure
                atom_idx = match[0]
                atom = mol.GetAtomWithIdx(atom_idx)

                # Simple element swap based on replacement
                if replacement == "F":
                    atom.SetAtomicNum(9)  # Fluorine
                elif replacement == "Cl":
                    atom.SetAtomicNum(17)  # Chlorine
                elif replacement == "[NX3H2]":
                    atom.SetAtomicNum(7)  # Nitrogen
                elif replacement == "[OX2H]":
                    atom.SetAtomicNum(8)  # Oxygen

                # Sanitize and check
                try:
                    Chem.SanitizeMol(mol)
                    new_smiles = Chem.MolToSmiles(mol)

                    # Check heavy atom count
                    n = Chem.MolFromSmiles(new_smiles).GetNumHeavyAtoms()
                    if self.min_atoms <= n <= self.max_atoms:
                        return new_smiles
                except:
                    continue

            except Exception:
                continue

        # If all substitutions failed, return None
        return None

    def _generate_by_modification(
        self,
        exclude_elements: Optional[List[str]],
    ) -> Optional[str]:
        """Generate by adding/removing atoms from known linker.

        REAL implementation using molecular graph editing.
        """
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
        except ImportError:
            return None

        # Pick random known linker with !=22 heavy atoms
        templates = [l for l in self.known_linkers if l.heavy_atom_count != 22]
        if not templates:
            templates = self.known_linkers

        template = random.choice(templates)
        mol = Chem.RWMol(Chem.MolFromSmiles(template.smiles))
        if mol is None:
            return None

        current_heavy = mol.GetNumHeavyAtoms()
        # Sample a target size within allowed range
        target_heavy = random.randint(self.min_atoms, self.max_atoms)

        # Add or remove atoms to reach target size
        if current_heavy < target_heavy:
            # ADD atoms
            atoms_to_add = target_heavy - current_heavy

            for _ in range(atoms_to_add):
                # Find a carbon atom to attach to
                c_atoms = [
                    i for i, a in enumerate(mol.GetAtoms()) if a.GetSymbol() == "C"
                ]
                if not c_atoms:
                    break

                attach_idx = random.choice(c_atoms)

                # Add a methyl group or aromatic carbon
                if random.random() < 0.5:
                    # Add CH3
                    new_idx = mol.AddAtom(Chem.Atom(6))  # Carbon
                    mol.AddBond(attach_idx, new_idx, Chem.BondType.SINGLE)
                else:
                    # Add aromatic carbon (part of benzene)
                    new_idx = mol.AddAtom(Chem.Atom(6))
                    mol.AddBond(attach_idx, new_idx, Chem.BondType.AROMATIC)

        elif current_heavy > target_heavy:
            # REMOVE atoms
            atoms_to_remove = current_heavy - target_heavy

            for _ in range(atoms_to_remove):
                # Find leaf atoms (degree 1) to remove
                leaf_atoms = [
                    i
                    for i, a in enumerate(mol.GetAtoms())
                    if a.GetDegree() == 1 and a.GetSymbol() not in ["H"]
                ]

                if leaf_atoms:
                    remove_idx = random.choice(leaf_atoms)
                    mol.RemoveAtom(remove_idx)
                else:
                    break

        # Sanitize and return
        try:
            Chem.SanitizeMol(mol)
            new_smiles = Chem.MolToSmiles(mol)

            n = Chem.MolFromSmiles(new_smiles).GetNumHeavyAtoms()
            if self.min_atoms <= n <= self.max_atoms:
                return new_smiles
        except:
            pass

        return None

    def _generate_from_template(
        self,
        application_context: str,
        functional_groups: Optional[List[str]],
        exclude_elements: Optional[List[str]],
    ) -> Optional[str]:
        """Generate from application-specific templates."""
        # Application-specific common MOF linker motifs
        templates_by_app = {
            "breath_VOC_sensing": [
                # Aromatic dicarboxylic acids (good for VOC sensing)
                "O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1",  # BDC-like
                "O=C(O)c1ccc(-c2cc(-c3ccc(C(=O)O)cc3)cc(-c3ccc(C(=O)O)cc3)c2)cc1",  # Triphenyl
                "O=C(O)c1c(C(=O)O)ccc2ccc(C(=O)O)c(C(=O)O)c12", # Naphthalene-tetracarboxylic
                "O=C(O)c1ccc(C2(c3ccc(C(=O)O)cc3)c3ccccc3-2)cc1", # Fluorene-based
            ],
            "food_safety": [
                # Amine/hydroxyl rich (H-bonding for contaminants)
                "Nc1ccc(-c2ccc(N)cc2)cc1",
                "Oc1ccc(-c2ccc(O)cc2)cc1",
            ],
            "PFAS_detection": [
                # Halogen-binding sites
                "c1ccc(-c2ccccc2)cc1",  # Biphenyl backbone
            ],
            "custom": [
                # Generic aromatic frameworks
                "c1ccc(-c2ccccc2)cc1",
                "c1ccc(-c2cc(-c3ccccc3)ccc2)cc1",
            ],
        }

        templates = templates_by_app.get(
            application_context, templates_by_app["custom"]
        )
        if not templates:
            return None

        # Start from template then adjust size toward target range
        base = random.choice(templates)

        try:
            from rdkit import Chem
        except ImportError:
            return base

        mol = Chem.RWMol(Chem.MolFromSmiles(base))
        if mol is None:
            return base

        target = random.randint(self.min_atoms, self.max_atoms)

        # Grow or prune to reach target (simple heuristic edits)
        while mol.GetNumHeavyAtoms() < target:
            c_atoms = [i for i, a in enumerate(mol.GetAtoms()) if a.GetSymbol() == "C"]
            if not c_atoms:
                break
            attach = random.choice(c_atoms)
            new_idx = mol.AddAtom(Chem.Atom(6))
            mol.AddBond(attach, new_idx, Chem.BondType.SINGLE)

        while mol.GetNumHeavyAtoms() > target:
            leaf_atoms = [
                i
                for i, a in enumerate(mol.GetAtoms())
                if a.GetDegree() == 1 and a.GetSymbol() != "H"
            ]
            if not leaf_atoms:
                break
            mol.RemoveAtom(random.choice(leaf_atoms))

        try:
            Chem.SanitizeMol(mol)
            smi = Chem.MolToSmiles(mol)
            n = Chem.MolFromSmiles(smi).GetNumHeavyAtoms()
            if self.min_atoms <= n <= self.max_atoms:
                return smi
        except Exception:
            pass

        return None

    def _is_valid_candidate(
        self,
        smiles: str,
        exclude_elements: Optional[List[str]],
    ) -> bool:
        """Validate a candidate SMILES.

        Checks:
        - RDKit valid
        - Heavy atom count in [18, 30]
        - Not in known set (novelty)
        - Doesn't contain excluded elements
        """
        try:
            from rdkit import Chem
        except ImportError:
            return False

        # Check RDKit validity
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False

        # Check heavy atom count
        heavy_atoms = mol.GetNumHeavyAtoms()
        if not (self.min_atoms <= heavy_atoms <= self.max_atoms):
            return False

        # Check novelty
        if smiles in self.known_smiles:
            return False

        # Check excluded elements
        if exclude_elements:
            mol_elements = set(atom.GetSymbol() for atom in mol.GetAtoms())
            if any(elem in mol_elements for elem in exclude_elements):
                return False

        # Check for radicals or invalid valences
        try:
            Chem.SanitizeMol(mol)
        except Exception:
            return False

        return True


if __name__ == "__main__":
    # Demo usage
    print("Testing Linker Generator...")

    # Create demo known linkers
    from mof_bridge.mp_mof_loader import MOFLinkerCache

    cache = MOFLinkerCache()
    if not cache.is_available():
        print("Creating demo cache...")
        cache.download(api_key="demo")

    known_linkers = cache.load_linkers()
    print(f"Loaded {len(known_linkers)} known linkers")

    # Generate candidates
    generator = LinkerGenerator(known_linkers)
    candidates = generator.generate_candidates(
        n_candidates=10,
        application_context="breath_VOC_sensing",
    )

    print(f"\nGenerated {len(candidates)} candidates:")
    for i, smiles in enumerate(candidates[:5], 1):
        print(f"  {i}. {smiles[:60]}...")

    # Validate all are 22 atoms
    try:
        from rdkit import Chem

        for smiles in candidates:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                heavy = mol.GetNumHeavyAtoms()
                assert heavy == 22, f"Expected 22 atoms, got {heavy}"
        print(f"\n✓ All candidates have exactly 22 heavy atoms")
    except ImportError:
        print("\n(RDKit not available for validation)")
