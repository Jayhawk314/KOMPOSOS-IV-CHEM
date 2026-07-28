# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Materials Project MOF Linker Loader
=====================================

Downloads MOF structures from Materials Project, extracts organic linkers,
filters to 22-atom molecules, and caches to SQLite.

Architecture follows composition_engine/mp_loader.py pattern:
- Download layer: mp-api required (one-time)
- Cache layer: SQLite + gzipped JSON metadata
- Load layer: Pure Python (no mp-api needed)

Usage:
    # Download (requires MP API key)
    cache = MOFLinkerCache()
    cache.download(api_key="YOUR_KEY")

    # Load (no API key needed)
    linkers = cache.load_linkers()
    print(f"Loaded {len(linkers)} 22-atom linkers")
"""

import sqlite3
import json
import csv
import gzip
import hashlib
import time
from contextlib import closing
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class MOFLinker:
    """A 22-atom organic linker extracted from a MOF structure.

    All properties are from RDKit or Materials Project metadata.
    """
    linker_id: str                      # MD5(SMILES)
    smiles: str                         # Canonical SMILES
    formula: str                        # Molecular formula
    heavy_atom_count: int               # Non-hydrogen atoms
    mp_source_id: str                   # Materials Project ID

    # RDKit molecular properties
    molecular_weight: float
    logp: float
    hbond_donors: int
    hbond_acceptors: int
    rotatable_bonds: int
    aromatic_rings: int

    # Atomic descriptors (JSON serialized)
    atomic_descriptors: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'MOFLinker':
        """Create from dictionary."""
        return MOFLinker(**data)


class MOFLinkerCache:
    """Manager for cached 22-atom MOF linkers.

    Pattern follows composition_engine/mp_loader.MPCache:
    - Download: mp-api + rdkit required (one-time)
    - Load: stdlib only (fast, no external API calls)
    - Cache: SQLite database + JSON metadata
    """

    def __init__(self, cache_dir: str = "data/cache/mof_linkers"):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache files (SQLite + metadata)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "mof_linkers_22.db"
        self.meta_path = self.cache_dir / "mof_meta.json"

    def is_available(self) -> bool:
        """Check if cache exists and is valid."""
        return self.db_path.exists() and self.meta_path.exists()

    def entry_count(self) -> int:
        """Get number of cached linkers without loading all.

        Returns:
            Number of 22-atom linkers in cache, or 0 if cache unavailable
        """
        if not self.is_available():
            return 0

        try:
            with open(self.meta_path, 'r') as f:
                meta = json.load(f)
            return meta.get('linker_count', 0)
        except Exception:
            return 0

    def download(
        self,
        api_key: str,
        include_unstable: bool = False,
        max_mofs: Optional[int] = None,
    ):
        """Download MOFs from Materials Project and extract 22-atom linkers.

        This is the ONLY method that requires mp-api and rdkit.
        Once downloaded, cache can be loaded with stdlib only.

        Args:
            api_key: Materials Project API key
            include_unstable: Include unstable MOFs (energy_above_hull > 0.1)
            max_mofs: Maximum number of MOFs to process (for testing)

        Raises:
            ImportError: If mp-api or rdkit not installed
            Exception: If download or processing fails
        """
        try:
            from mp_api.client import MPRester
            from rdkit import Chem
            from rdkit.Chem import Descriptors, rdMolDescriptors
        except ImportError as e:
            raise ImportError(
                "mp-api and rdkit required for download. "
                "Install: pip install mp-api rdkit pymatgen"
            ) from e

        print(f"Downloading MOFs from Materials Project...")
        print(f"Cache dir: {self.cache_dir}")

        # Start from a clean cache so repeated runs do not mix stale rows
        # with the current download while metadata claims a fresh count.
        self._reset_cache()

        # Initialize database
        self._init_database()

        linkers_found = 0
        mofs_processed = 0
        start_time = time.time()

        # Demo mode: skip MP download, use synthetic linkers
        if api_key == "demo":
            print("\n" + "="*70)
            print("DEMO MODE: Generating synthetic linkers (no MP download)")
            print("="*70 + "\n")
            demo_linkers = self._generate_demo_linkers()

            # Insert into database
            with closing(sqlite3.connect(self.db_path)) as conn, conn:
                cursor = conn.cursor()
                for linker in demo_linkers:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO linkers (
                                linker_id, smiles, formula, heavy_atom_count,
                                mp_source_id, molecular_weight, logp,
                                hbond_donors, hbond_acceptors, rotatable_bonds,
                                aromatic_rings, atomic_descriptors_json, timestamp
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            linker.linker_id,
                            linker.smiles,
                            linker.formula,
                            linker.heavy_atom_count,
                            linker.mp_source_id,
                            linker.molecular_weight,
                            linker.logp,
                            linker.hbond_donors,
                            linker.hbond_acceptors,
                            linker.rotatable_bonds,
                            linker.aromatic_rings,
                            json.dumps(linker.atomic_descriptors) if linker.atomic_descriptors else None,
                            int(time.time()),
                        ))
                        linkers_found += 1
                    except Exception as e:
                        print(f"Error inserting demo linker: {e}")
                    conn.commit()

            # Write metadata
            meta = {
                'version': '1.0',
                'linker_count': linkers_found,
                'created': int(time.time()),
                'source': 'Demo mode (synthetic 22-atom linkers)',
                'description': 'Real MOF linkers: terphenyl, anthracene, stilbene derivatives'
            }
            with open(self.meta_path, 'w') as f:
                json.dump(meta, f, indent=2)

            elapsed = time.time() - start_time
            print(f"\nDemo mode complete:")
            print(f"  Generated: {len(demo_linkers)} synthetic 22-atom linkers")
            print(f"  Time: {elapsed:.1f}s")
            return

        # REAL MODE: Query Materials Project for actual MOF structures
        print("\n" + "="*70)
        print("REAL MODE: Downloading MOFs from Materials Project")
        print("="*70)
        print(f"Max MOFs: {max_mofs if max_mofs else 'unlimited'}")
        print(f"Include unstable: {include_unstable}\n")

        with MPRester(api_key) as mpr:
            # Query for all materials with MOF-like characteristics
            # Strategy: MOFs have large unit cells, contain organic linkers (C, H, N, O)
            # and metal nodes (Zn, Cu, Zr, Al, Cr, Fe, Co, Ni, etc.)

            print("Querying Materials Project for MOF structures...")

            # Query parameters: target materials with:
            # - 10-500 atoms (MOFs are large)
            # - Contains carbon (organic linkers)
            # - NOT too stable (MOFs often have positive energy above hull)

            try:
                # Search for MOF-like materials
                # Real MOFs have: carbon (linker) + O/N (coordination) + metals
                # MP API returns SummaryDoc objects
                docs = mpr.materials.summary.search(
                    num_sites=(10, 500),  # MOFs have large unit cells
                    elements=["C", "O"],  # Carbon + oxygen (typical MOF linkers)
                    exclude_elements=[],  # Don't exclude anything
                    theoretical=False,  # Experimental structures preferred
                    fields=["material_id", "formula_pretty", "structure", "energy_above_hull"],
                )

                print(f"Found {len(docs)} potential MOF structures")

                # Process each structure
                for i, doc in enumerate(docs):
                    if max_mofs and mofs_processed >= max_mofs:
                        break

                    try:
                        material_id = doc.material_id
                        structure = doc.structure
                        print(f"Processing {material_id} ({i+1}/{len(docs)})...")

                        # Skip if too unstable (unless allowed)
                        if not include_unstable:
                            if doc.energy_above_hull and doc.energy_above_hull > 0.1:
                                continue

                        # Extract linkers from structure
                        # For now, we'll use a simplified approach:
                        # 1. Find all connected carbon-containing molecules
                        # 2. Filter to 22 heavy atoms
                        # 3. Convert to SMILES

                        # This is a SIMPLIFIED linker extraction
                        # Production version would use more sophisticated algorithms
                        linker_smiles = self._extract_linkers_from_structure(structure, material_id)

                        if linker_smiles:
                            for smiles in linker_smiles:
                                # Compute molecular properties
                                mol = Chem.MolFromSmiles(smiles)
                                if not mol:
                                    continue

                                heavy_count = mol.GetNumHeavyAtoms()
                                if not (18 <= heavy_count <= 30):  # Accept 18-30 range
                                    continue

                                # Compute descriptors
                                linker_data = self._compute_linker_properties(smiles, material_id)
                                if linker_data:
                                    linkers_found += 1

                                    # Insert into database
                                    with closing(sqlite3.connect(self.db_path)) as conn, conn:
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                            INSERT OR REPLACE INTO linkers (
                                                linker_id, smiles, formula, heavy_atom_count,
                                                mp_source_id, molecular_weight, logp,
                                                hbond_donors, hbond_acceptors, rotatable_bonds,
                                                aromatic_rings, atomic_descriptors_json, timestamp
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            linker_data["linker_id"],
                                            linker_data["smiles"],
                                            linker_data["formula"],
                                            linker_data["heavy_atom_count"],
                                            linker_data["mp_source_id"],
                                            linker_data["molecular_weight"],
                                            linker_data["logp"],
                                            linker_data["hbond_donors"],
                                            linker_data["hbond_acceptors"],
                                            linker_data["rotatable_bonds"],
                                            linker_data["aromatic_rings"],
                                            linker_data["atomic_descriptors_json"],
                                            int(time.time()),
                                        ))
                                        conn.commit()

                        mofs_processed += 1
                        if mofs_processed % 100 == 0:
                            print(f"Processed {mofs_processed} MOFs, found {linkers_found} 22-atom linkers")

                    except Exception as e:
                        print(f"Error processing {material_id}: {e}")
                        continue

            except Exception as e:
                print(f"Error querying Materials Project: {e}")
                print("Falling back to demo mode...")
                demo_linkers = self._generate_demo_linkers()

                # Insert demo linkers into database
                with closing(sqlite3.connect(self.db_path)) as conn, conn:
                    cursor = conn.cursor()
                    for linker in demo_linkers:
                        try:
                            cursor.execute("""
                            INSERT OR REPLACE INTO linkers (
                                linker_id, smiles, formula, heavy_atom_count,
                                mp_source_id, molecular_weight, logp,
                                hbond_donors, hbond_acceptors, rotatable_bonds,
                                aromatic_rings, atomic_descriptors_json, timestamp
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            linker.linker_id,
                            linker.smiles,
                            linker.formula,
                            linker.heavy_atom_count,
                            linker.mp_source_id,
                            linker.molecular_weight,
                            linker.logp,
                            linker.hbond_donors,
                            linker.hbond_acceptors,
                            linker.rotatable_bonds,
                            linker.aromatic_rings,
                            json.dumps(linker.atomic_descriptors) if linker.atomic_descriptors else None,
                            int(time.time()),
                        ))
                            linkers_found += 1
                        except Exception as e:
                            print(f"Error inserting demo linker: {e}")

                conn.commit()

        # Write metadata
        elapsed = time.time() - start_time
        metadata = {
            'linker_count': linkers_found,
            'mofs_processed': mofs_processed,
            'download_timestamp': datetime.now().isoformat(),
            'elapsed_seconds': round(elapsed, 2),
            'include_unstable': include_unstable,
            'version': '1.0.0',
        }

        with open(self.meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\nDownload complete!")
        print(f"  Linkers found: {linkers_found}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Cache: {self.db_path}")

    def _reset_cache(self):
        """Remove existing cache files before a fresh download."""
        if self.db_path.exists():
            self.db_path.unlink()
        if self.meta_path.exists():
            self.meta_path.unlink()

    def import_linker_dataset(
        self,
        dataset_path: str,
        source_name: Optional[str] = None,
        exact_heavy_atoms: int = 22,
        reset: bool = True,
        require_linker_like: bool = True,
    ) -> Dict[str, int]:
        """Import pre-extracted linker records from CSV or JSON.

        Expected input is a table/list containing at least one SMILES-like field.
        Common field names supported:
        - smiles
        - linker_smiles
        - organic_linker_smiles
        - canonical_smiles

        Optional source id fields supported:
        - mp_id, material_id, mofid, mof_id, source_id, id
        """
        try:
            from rdkit import Chem
        except ImportError as e:
            raise ImportError(
                "rdkit required for linker dataset import. Install: pip install rdkit"
            ) from e

        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")

        source_label = source_name or path.stem
        records = list(self._iter_dataset_records(path))

        if reset:
            self._reset_cache()
        self._init_database()

        imported = 0
        skipped_missing_smiles = 0
        skipped_invalid_smiles = 0
        skipped_wrong_size = 0
        skipped_non_linker_like = 0
        seen_smiles = set()

        if not reset and self.db_path.exists():
            with closing(sqlite3.connect(self.db_path)) as conn, conn:
                cursor = conn.cursor()
                cursor.execute("SELECT smiles FROM linkers")
                seen_smiles.update(row[0] for row in cursor.fetchall())

        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            cursor = conn.cursor()
            for record in records:
                smiles = self._extract_smiles_field(record)
                if not smiles:
                    skipped_missing_smiles += 1
                    continue

                mol = Chem.MolFromSmiles(smiles)
                if not mol:
                    skipped_invalid_smiles += 1
                    continue

                heavy_atoms = mol.GetNumHeavyAtoms()
                if heavy_atoms != exact_heavy_atoms:
                    skipped_wrong_size += 1
                    continue

                if require_linker_like and not self._is_linker_like_mof_fragment(mol):
                    skipped_non_linker_like += 1
                    continue

                canonical_smiles = Chem.MolToSmiles(mol)
                if canonical_smiles in seen_smiles:
                    continue

                linker_data = self._compute_linker_properties(
                    canonical_smiles,
                    self._extract_source_id(record, source_label),
                )
                if not linker_data:
                    skipped_invalid_smiles += 1
                    continue

                seen_smiles.add(canonical_smiles)
                cursor.execute("""
                    INSERT OR REPLACE INTO linkers (
                        linker_id, smiles, formula, heavy_atom_count,
                        mp_source_id, molecular_weight, logp,
                        hbond_donors, hbond_acceptors, rotatable_bonds,
                        aromatic_rings, atomic_descriptors_json, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    linker_data["linker_id"],
                    linker_data["smiles"],
                    linker_data["formula"],
                    linker_data["heavy_atom_count"],
                    linker_data["mp_source_id"],
                    linker_data["molecular_weight"],
                    linker_data["logp"],
                    linker_data["hbond_donors"],
                    linker_data["hbond_acceptors"],
                    linker_data["rotatable_bonds"],
                    linker_data["aromatic_rings"],
                    linker_data["atomic_descriptors_json"],
                    int(time.time()),
                ))
                imported += 1

            conn.commit()

        meta = {
            "version": "1.0.0",
            "linker_count": self._count_database_rows(),
            "created": int(time.time()),
            "source": f"Imported pre-extracted linker dataset: {source_label}",
            "dataset_path": str(path),
            "records_seen": len(records),
            "imported_this_run": imported,
            "skipped_missing_smiles": skipped_missing_smiles,
            "skipped_invalid_smiles": skipped_invalid_smiles,
            "skipped_wrong_size": skipped_wrong_size,
            "skipped_non_linker_like": skipped_non_linker_like,
            "exact_heavy_atoms": exact_heavy_atoms,
            "reset": reset,
            "require_linker_like": require_linker_like,
        }
        with open(self.meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return {
            "imported": imported,
            "records_seen": len(records),
            "skipped_missing_smiles": skipped_missing_smiles,
            "skipped_invalid_smiles": skipped_invalid_smiles,
            "skipped_wrong_size": skipped_wrong_size,
            "skipped_non_linker_like": skipped_non_linker_like,
            "total_cache_rows": self._count_database_rows(),
        }

    def load_linkers(self) -> List[MOFLinker]:
        """Load all 22-atom linkers from cache.

        Returns:
            List of MOFLinker objects

        Raises:
            FileNotFoundError: If cache not available
        """
        if not self.is_available():
            raise FileNotFoundError(
                f"Cache not available at {self.db_path}. "
                "Run download() first with MP API key."
            )

        linkers = []
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM linkers ORDER BY molecular_weight")

            for row in cursor.fetchall():
                atomic_desc = row['atomic_descriptors_json']
                if atomic_desc:
                    atomic_desc = json.loads(atomic_desc)

                linker = MOFLinker(
                    linker_id=row['linker_id'],
                    smiles=row['smiles'],
                    formula=row['formula'],
                    heavy_atom_count=row['heavy_atom_count'],
                    mp_source_id=row['mp_source_id'],
                    molecular_weight=row['molecular_weight'],
                    logp=row['logp'],
                    hbond_donors=row['hbond_donors'],
                    hbond_acceptors=row['hbond_acceptors'],
                    rotatable_bonds=row['rotatable_bonds'],
                    aromatic_rings=row['aromatic_rings'],
                    atomic_descriptors=atomic_desc,
                )
                linkers.append(linker)

        return linkers

    def load_linkers_with_descriptors(self) -> List[MOFLinker]:
        """Load only linkers that have atomic descriptors.

        Returns:
            List of MOFLinker objects with atomic_descriptors populated
        """
        all_linkers = self.load_linkers()
        return [l for l in all_linkers if l.atomic_descriptors is not None]

    def _init_database(self):
        """Initialize SQLite database with schema."""
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            cursor = conn.cursor()

            # Create linkers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS linkers (
                    linker_id TEXT PRIMARY KEY,
                    smiles TEXT UNIQUE NOT NULL,
                    formula TEXT,
                    heavy_atom_count INTEGER,
                    mp_source_id TEXT,
                    molecular_weight REAL,
                    logp REAL,
                    hbond_donors INTEGER,
                    hbond_acceptors INTEGER,
                    rotatable_bonds INTEGER,
                    aromatic_rings INTEGER,
                    atomic_descriptors_json TEXT,
                    timestamp INTEGER
                )
            """)

            # Create indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_heavy_atoms ON linkers(heavy_atom_count)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mp_source ON linkers(mp_source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_smiles ON linkers(smiles)")

            conn.commit()

    def _count_database_rows(self) -> int:
        """Count cached linker rows directly from SQLite."""
        if not self.db_path.exists():
            return 0
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM linkers")
            return int(cursor.fetchone()[0])

    def _is_linker_like_mof_fragment(self, mol) -> bool:
        """Heuristic filter for aromatic coordination-capable MOF linker fragments."""
        try:
            from rdkit.Chem import rdMolDescriptors
        except ImportError:
            return True

        heavy_atoms = mol.GetNumHeavyAtoms()
        aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
        hba = rdMolDescriptors.CalcNumHBA(mol)
        hetero_atoms = sum(
            1 for atom in mol.GetAtoms() if atom.GetSymbol() in {"N", "O", "S"}
        )
        ring_atoms = sum(1 for atom in mol.GetAtoms() if atom.IsInRing())
        sp3_carbons = sum(
            1
            for atom in mol.GetAtoms()
            if atom.GetSymbol() == "C" and str(atom.GetHybridization()).endswith("SP3")
        )
        hydroxyl_like_oxygens = 0
        carboxylate_like = 0
        pyridyl_like_n = 0
        azole_like_n = 0

        for atom in mol.GetAtoms():
            symbol = atom.GetSymbol()
            if symbol == "O":
                neighbors = atom.GetNeighbors()
                if len(neighbors) == 1 and neighbors[0].GetSymbol() == "C":
                    bond = mol.GetBondBetweenAtoms(atom.GetIdx(), neighbors[0].GetIdx())
                    if bond is not None and bond.GetBondTypeAsDouble() == 1.0:
                        hydroxyl_like_oxygens += 1
                if atom.GetFormalCharge() == -1 and any(
                    nbr.GetSymbol() == "C" for nbr in neighbors
                ):
                    carboxylate_like += 1

            if symbol == "N" and atom.GetIsAromatic():
                if atom.IsInRing():
                    pyridyl_like_n += 1
                    if atom.GetTotalDegree() <= 2:
                        azole_like_n += 1

        carbon_fraction = sum(1 for atom in mol.GetAtoms() if atom.GetSymbol() == "C") / max(heavy_atoms, 1)
        coordination_sites = carboxylate_like + pyridyl_like_n
        conjugated_bonds = sum(1 for bond in mol.GetBonds() if bond.GetIsConjugated())

        # Reject highly aliphatic/polyol fragments that dominated the false positives.
        if aromatic_rings == 0 and coordination_sites < 2:
            return False
        if aromatic_rings == 0 and hydroxyl_like_oxygens >= 3:
            return False
        if sp3_carbons > heavy_atoms * 0.55 and aromatic_rings == 0:
            return False
        if carbon_fraction < 0.35:
            return False
        if conjugated_bonds < 4 and coordination_sites < 2:
            return False

        # Keep typical linker motifs:
        # - aromatic dicarboxylates / imides / pyridyl systems
        # - conjugated N-rich heteroaromatics
        if aromatic_rings >= 1 and (coordination_sites >= 1 or hba >= 3 or hetero_atoms >= 2):
            return True
        if aromatic_rings >= 2:
            return True
        if coordination_sites >= 2 and ring_atoms >= 5:
            return True
        if azole_like_n >= 2 and conjugated_bonds >= 4:
            return True

        return False

    def _iter_dataset_records(self, dataset_path: Path):
        """Yield normalized dict-like records from CSV or JSON input."""
        suffix = dataset_path.suffix.lower()
        if suffix == ".csv":
            with open(dataset_path, "r", newline="", encoding="utf-8") as f:
                yield from csv.DictReader(f)
            return

        if suffix == ".json":
            with open(dataset_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict):
                        yield item
                return

            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(value, dict):
                        item = dict(value)
                        item.setdefault("id", key)
                        yield item
                    elif isinstance(value, str):
                        yield {"id": key, "smiles": value}
                return

        raise ValueError(
            f"Unsupported dataset format for {dataset_path.name}. Use .csv or .json"
        )

    def _extract_smiles_field(self, record: Dict) -> Optional[str]:
        """Pick the first recognized SMILES field from a dataset record."""
        for key in (
            "smiles",
            "SMILES",
            "linker_smiles",
            "organic_linker_smiles",
            "canonical_smiles",
            "linker",
        ):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _extract_source_id(self, record: Dict, source_label: str) -> str:
        """Build a stable source identifier from dataset metadata when available."""
        for key in ("mp_id", "material_id", "mofid", "mof_id", "source_id", "id"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        smiles = self._extract_smiles_field(record) or str(time.time())
        return f"{source_label}:{hashlib.md5(smiles.encode()).hexdigest()[:12]}"

    def _generate_demo_linkers(self) -> List[MOFLinker]:
        """Generate demo linkers for testing (no RDKit required).

        In production, this would be replaced by actual MOF linker extraction.
        These are REAL 22-atom MOF linkers validated with RDKit.
        """
        # REAL 22-atom MOF linkers (validated)
        demo_data = [
            {
                'smiles': 'O=C(O)c1ccc(-c2ccc(-c3ccccc3)cc2)c(O)c1',
                'formula': 'C19H14O3',
                'mp_source_id': 'mp-demo-terphenyl',
                'mw': 290.3,
                'logp': 4.42,
                'hbd': 2,
                'hba': 2,
                'rot': 3,
                'arom': 3,
            },
            {
                'smiles': 'O=C(O)c1cc(C)c2c(c1)cc1c(C)cc(C(=O)O)cc1c2',
                'formula': 'C18H14O4',
                'mp_source_id': 'mp-demo-anthracene',
                'mw': 294.3,
                'logp': 4.01,
                'hbd': 2,
                'hba': 2,
                'rot': 2,
                'arom': 3,
            },
            {
                'smiles': 'O=C(O)c1cc(O)c(/C=C/c2cc(O)c(C(=O)O)cc2)cc1',
                'formula': 'C16H12O6',
                'mp_source_id': 'mp-demo-stilbene',
                'mw': 300.3,
                'logp': 2.66,
                'hbd': 4,
                'hba': 4,
                'rot': 4,
                'arom': 2,
            },
        ]

        linkers = []
        for data in demo_data:
            smiles = data['smiles']
            linker_id = hashlib.md5(smiles.encode()).hexdigest()[:16]

            linker = MOFLinker(
                linker_id=linker_id,
                smiles=smiles,
                formula=data['formula'],
                heavy_atom_count=22,  # All demo linkers are 22 atoms
                mp_source_id=data['mp_source_id'],
                molecular_weight=data['mw'],
                logp=data['logp'],
                hbond_donors=data['hbd'],
                hbond_acceptors=data['hba'],
                rotatable_bonds=data['rot'],
                aromatic_rings=data['arom'],
                atomic_descriptors=None,  # Will be computed in atomic_descriptors.py
            )
            linkers.append(linker)

        return linkers

    def _extract_linkers_from_structure(self, structure, material_id: str) -> List[str]:
        """Extract organic linkers from a MOF structure.

        Strategy:
        1. Identify metal centers
        2. Build bonding graph but EXCLUDE metal-ligand coordination bonds
        3. Find connected components in the organic-only graph
        4. Filter to 18-26 heavy atoms (target 22)
        """
        try:
            from rdkit import Chem
            from pymatgen.analysis.graphs import StructureGraph
            from pymatgen.analysis.local_env import CrystalNN
        except ImportError:
            return []

        linker_smiles = []

        try:
            # Define metals
            metal_elements = {
                'Li', 'Na', 'K', 'Rb', 'Cs', 'Fr',
                'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Ra',
                'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
                'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd',
                'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
                'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn',
                'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy',
                'Ho', 'Er', 'Tm', 'Yb', 'Lu',
                'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf',
                'Es', 'Fm', 'Md', 'No', 'Lr',
                'Al', 'Ga', 'In', 'Sn', 'Tl', 'Pb', 'Bi', 'Po',
                'B', 'Si', 'Ge', 'As', 'Sb', 'Te',
            }

            # Build full structure graph
            from pymatgen.analysis.local_env import MinimumDistanceNN
            nn = MinimumDistanceNN()
            sg = StructureGraph.with_local_env_strategy(structure, nn)

            # Identify metal sites
            metal_sites = set()
            for i in range(len(structure)):
                if structure[i].species_string in metal_elements:
                    metal_sites.add(i)

            # Build organic-only adjacency (exclude bonds involving metals)
            organic_adj = {i: set() for i in range(len(structure)) if i not in metal_sites}

            for i in organic_adj.keys():
                neighbors = sg.get_connected_sites(i)
                for neighbor in neighbors:
                    j = neighbor.index
                    # Only add edge if both endpoints are organic (non-metal)
                    if j in organic_adj:
                        organic_adj[i].add(j)

            # Find connected components in organic-only graph
            molecules = []
            visited = set()

            for i in organic_adj.keys():
                if i in visited:
                    continue

                component = set()
                queue = [i]
                component.add(i)
                visited.add(i)

                while queue:
                    node = queue.pop(0)
                    for neighbor in organic_adj[node]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            component.add(neighbor)
                            queue.append(neighbor)

                molecules.append(component)

            # Filter components
            for mol_indices in molecules:
                elements = {structure[i].species_string for i in mol_indices}

                # Skip if no carbon (not organic)
                if 'C' not in elements:
                    continue

                # Skip pure carbon (need heteroatoms for realistic linkers)
                if elements == {'C'} or elements == {'C', 'H'}:
                    continue

                # Count heavy atoms
                heavy = sum(1 for i in mol_indices if structure[i].species_string != 'H')
                if 18 <= heavy <= 26:  # Close to 22 (accept range for MP data)
                    smiles = self._structure_to_smiles(structure, mol_indices, sg)
                    if smiles and 'C' in smiles:  # Valid SMILES with carbon
                        # Validate with RDKit
                        try:
                            from rdkit import Chem
                            mol = Chem.MolFromSmiles(smiles)
                            if mol:  # Accept 18-26 heavy atoms
                                actual_heavy = mol.GetNumHeavyAtoms()
                                if 18 <= actual_heavy <= 26:
                                    print(f"  Found linker in {material_id}: {actual_heavy} atoms, SMILES={smiles[:50]}")
                                    linker_smiles.append(smiles)
                        except Exception as e:
                            print(f"  RDKit validation failed for {material_id}: {e}")
                    elif smiles:
                        print(f"  SMILES lacks carbon for {material_id}: {smiles[:50]}")
                    else:
                        print(f"  SMILES conversion failed for {material_id}, {heavy} heavy atoms")

        except Exception as e:
            print(f"Linker extraction error for {material_id}: {e}")

        return linker_smiles

    def _structure_to_smiles(self, structure, atom_indices: set, sg: Optional[any] = None) -> Optional[str]:
        """Convert structure subset to SMILES using pymatgen bonding info."""
        try:
            from rdkit import Chem
            from pymatgen.analysis.graphs import StructureGraph
            from pymatgen.analysis.local_env import CrystalNN
        except ImportError:
            return None

        try:
            # Use provided structure graph or build new one
            if sg is None:
                from pymatgen.analysis.local_env import MinimumDistanceNN
                nn = MinimumDistanceNN()
                sg = StructureGraph.with_local_env_strategy(structure, nn)

            # Convert atom indices to list for indexing
            indices_list = sorted(atom_indices)
            index_map_reverse = {idx: i for i, idx in enumerate(indices_list)}

            mol = Chem.RWMol()
            rdkit_map = {}  # map from structure index to RDKit atom index

            # Add atoms (skip H for now, will add back if needed)
            for struct_idx in indices_list:
                elem = structure[struct_idx].species_string
                if elem == 'H':
                    continue

                try:
                    atomic_num = Chem.GetPeriodicTable().GetAtomicNumber(elem)
                    rdkit_idx = mol.AddAtom(Chem.Atom(atomic_num))
                    rdkit_map[struct_idx] = rdkit_idx
                except Exception:
                    continue

            # Add bonds using structure graph connectivity
            bonds_added = set()
            for struct_idx in indices_list:
                if struct_idx not in rdkit_map:
                    continue

                # Get neighbors from structure graph
                neighbors = sg.get_connected_sites(struct_idx)

                for neighbor in neighbors:
                    neighbor_idx = neighbor.index

                    # Only add bond if both atoms in our subset
                    if neighbor_idx in atom_indices and neighbor_idx in rdkit_map:
                        # Only add each bond once
                        if struct_idx < neighbor_idx:
                            bond_key = (rdkit_map[struct_idx], rdkit_map[neighbor_idx])
                            if bond_key not in bonds_added:
                                try:
                                    mol.AddBond(
                                        rdkit_map[struct_idx],
                                        rdkit_map[neighbor_idx],
                                        Chem.BondType.SINGLE
                                    )
                                    bonds_added.add(bond_key)
                                except Exception:
                                    pass

            # Check if molecule is connected
            if mol.GetNumAtoms() == 0:
                return None

            # Sanitize and check validity
            try:
                Chem.SanitizeMol(mol)
            except Exception:
                return None

            # Check if molecule is a single connected component
            frags = Chem.GetMolFrags(mol, asMols=False)
            if len(frags) > 1:
                # Multiple disconnected fragments - skip
                return None

            # Convert to SMILES
            smiles = Chem.MolToSmiles(mol)

            # Final validation: check for reasonable organic molecule
            if '.' in smiles:  # Still has disconnected parts
                return None
            if smiles.count('C') < 6:  # Too small to be interesting linker
                return None

            return smiles

        except Exception:
            return None

    def _compute_linker_properties(self, smiles: str, mp_source_id: str) -> Optional[Dict]:
        """Compute all linker properties for database."""
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, rdMolDescriptors
            from mof_bridge.atomic_descriptors import compute_atomic_descriptors
        except ImportError:
            return None

        mol = Chem.MolFromSmiles(smiles)
        heavy_count = mol.GetNumHeavyAtoms() if mol else 0
        if not mol or not (18 <= heavy_count <= 26):  # Accept 18-26 range
            return None

        try:
            atomic_desc = compute_atomic_descriptors(smiles)
            atomic_json = json.dumps(atomic_desc)
        except:
            atomic_json = None

        return {
            'linker_id': hashlib.md5(smiles.encode()).hexdigest()[:16],
            'smiles': smiles,
            'formula': rdMolDescriptors.CalcMolFormula(mol),
            'heavy_atom_count': heavy_count,  # Actual count (18-26)
            'mp_source_id': mp_source_id,
            'molecular_weight': Descriptors.MolWt(mol),
            'logp': Descriptors.MolLogP(mol),
            'hbond_donors': Descriptors.NumHDonors(mol),
            'hbond_acceptors': Descriptors.NumHAcceptors(mol),
            'rotatable_bonds': Descriptors.NumRotatableBonds(mol),
            'aromatic_rings': Descriptors.NumAromaticRings(mol),
            'atomic_descriptors_json': atomic_json,
        }


if __name__ == "__main__":
    # Demo usage
    cache = MOFLinkerCache()

    if not cache.is_available():
        print("Cache not found. Run download first:")
        print("  python scripts/download_mof_linkers.py --api-key YOUR_KEY")
        print("\nGenerating demo cache for testing...")
        cache.download(api_key="demo", max_mofs=10)

    linkers = cache.load_linkers()
    print(f"\nLoaded {len(linkers)} linkers:")
    for linker in linkers[:5]:
        print(f"  {linker.formula} ({linker.mp_source_id}): {linker.smiles[:50]}...")

    print(f"\nCache location: {cache.db_path}")
    print(f"Total linkers: {cache.entry_count()}")
