# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
PubChem PUG REST Loader
========================

Fetches molecular properties from PubChem's public API and returns
Molecule objects compatible with the molecular_bridge.

No API key required. Rate limit: 5 requests/second (self-enforced).
Uses only stdlib (urllib, json) -- zero extra dependencies.

Usage:
    loader = PubChemLoader()
    mol = loader.fetch_by_name("ethylene carbonate")
    print(mol.molecular_weight, mol.smiles)

    mol2 = loader.fetch_by_cid(7303)  # EC
    print(mol2.formula)

PubChem PUG REST docs:
    https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
"""

from __future__ import annotations

import json
import os
import time
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional

from molecular_bridge.molecule_properties import Molecule, MoleculeClass


# Default cache directory (inside data/)
_DEFAULT_CACHE_DIR = Path(__file__).parent / "cache" / "pubchem"

# PUG REST base URL
_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Properties to request from PubChem in a single call
_PROPERTY_LIST = (
    "MolecularWeight,MolecularFormula,CanonicalSMILES,InChI,"
    "XLogP,HBondDonorCount,HBondAcceptorCount,"
    "Complexity,ExactMass,IUPACName"
)


class PubChemError(Exception):
    """Error communicating with PubChem API."""


class PubChemLoader:
    """
    Loads molecular properties from PubChem PUG REST API.

    Features:
    - Fetch by name, CID, or SMILES
    - Automatic rate limiting (5 req/s)
    - Optional disk cache (JSON files)
    - Returns Molecule dataclass instances

    Args:
        cache_dir: Directory for cached responses. None to disable caching.
        rate_limit: Minimum seconds between requests (default 0.2 = 5/s).
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = _DEFAULT_CACHE_DIR,
        rate_limit: float = 0.2,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.rate_limit = rate_limit
        self._last_request_time = 0.0

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _rate_wait(self):
        """Enforce rate limit between API calls."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request_time = time.time()

    def _cache_key(self, url: str) -> Path:
        """Generate a cache file path from a URL."""
        h = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{h}.json"

    def _fetch_url(self, url: str) -> dict:
        """Fetch a URL with caching and rate limiting."""
        # Check cache first
        if self.cache_dir:
            cache_file = self._cache_key(url)
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)

        # Rate limit
        self._rate_wait()

        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise PubChemError(f"Not found: {url}") from e
            raise PubChemError(f"HTTP {e.code}: {url}") from e
        except urllib.error.URLError as e:
            # Corporate/AV proxies often MITM TLS and break cert verification.
            # PubChem is a public read-only API, so retry once with an
            # unverified context rather than failing the whole lookup.
            import ssl
            if isinstance(getattr(e, "reason", None), ssl.SSLError):
                try:
                    ctx = ssl._create_unverified_context()
                    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                except Exception as e2:
                    raise PubChemError(f"Connection error (after TLS fallback): {e2}") from e2
            else:
                raise PubChemError(f"Connection error: {e.reason}") from e

        # Cache result
        if self.cache_dir:
            cache_file = self._cache_key(url)
            with open(cache_file, 'w') as f:
                json.dump(data, f)

        return data

    def _properties_url(self, identifier: str, id_type: str = "name") -> str:
        """Build PUG REST properties URL."""
        return f"{_BASE_URL}/compound/{id_type}/{identifier}/property/{_PROPERTY_LIST}/JSON"

    def _synonyms_url(self, cid: int) -> str:
        """Build PUG REST synonyms URL (for CAS numbers)."""
        return f"{_BASE_URL}/compound/cid/{cid}/synonyms/JSON"

    def _extract_cas(self, synonyms_data: dict) -> str:
        """Extract CAS number from synonyms response."""
        try:
            syns = synonyms_data["InformationList"]["Information"][0]["Synonym"]
        except (KeyError, IndexError):
            return ""

        import re
        cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
        for syn in syns:
            if cas_pattern.match(syn):
                return syn
        return ""

    def _props_to_molecule(
        self,
        props: dict,
        cas_number: str = "",
        name_override: str = "",
        molecule_class: MoleculeClass = MoleculeClass.OTHER,
    ) -> Molecule:
        """Convert PubChem property dict to Molecule."""
        cid = props.get("CID", 0)
        formula = props.get("MolecularFormula", "")
        mw = props.get("MolecularWeight", 0.0)
        if isinstance(mw, str):
            mw = float(mw)
        # PubChem's 2025 API renamed CanonicalSMILES -> SMILES/ConnectivitySMILES.
        smiles = (
            props.get("CanonicalSMILES")
            or props.get("SMILES")
            or props.get("ConnectivitySMILES")
            or ""
        )
        logp = props.get("XLogP", None)
        hbd = props.get("HBondDonorCount", 0)
        hba = props.get("HBondAcceptorCount", 0)
        iupac = props.get("IUPACName", "")

        name = name_override or iupac or formula

        return Molecule(
            name=name,
            formula=formula,
            pubchem_cid=cid,
            cas_number=cas_number,
            smiles=smiles,
            molecular_weight=mw,
            logP=logp,
            hbond_donors=hbd,
            hbond_acceptors=hba,
            molecule_class=molecule_class,
            sources={'pubchem': f'PubChem CID {cid}'},
        )

    def fetch_by_name(
        self,
        name: str,
        molecule_class: MoleculeClass = MoleculeClass.OTHER,
        fetch_cas: bool = True,
    ) -> Molecule:
        """
        Fetch molecule properties by common name.

        Args:
            name: Common name (e.g. "ethylene carbonate", "limonene").
            molecule_class: Classification for the returned Molecule.
            fetch_cas: If True, make an additional request for CAS number.

        Returns:
            Molecule with properties populated from PubChem.

        Raises:
            PubChemError: If compound not found or API error.
        """
        url = self._properties_url(urllib.request.quote(name), "name")
        data = self._fetch_url(url)

        try:
            props = data["PropertyTable"]["Properties"][0]
        except (KeyError, IndexError) as e:
            raise PubChemError(f"No properties returned for '{name}'") from e

        cas = ""
        if fetch_cas:
            cid = props.get("CID", 0)
            if cid:
                try:
                    syn_data = self._fetch_url(self._synonyms_url(cid))
                    cas = self._extract_cas(syn_data)
                except PubChemError:
                    pass

        return self._props_to_molecule(
            props, cas_number=cas, name_override=name,
            molecule_class=molecule_class,
        )

    def fetch_by_cid(
        self,
        cid: int,
        molecule_class: MoleculeClass = MoleculeClass.OTHER,
        fetch_cas: bool = True,
    ) -> Molecule:
        """
        Fetch molecule properties by PubChem Compound ID.

        Args:
            cid: PubChem CID (e.g. 7303 for EC).
            molecule_class: Classification for the returned Molecule.
            fetch_cas: If True, make an additional request for CAS number.

        Returns:
            Molecule with properties populated from PubChem.

        Raises:
            PubChemError: If CID not found or API error.
        """
        url = self._properties_url(str(cid), "cid")
        data = self._fetch_url(url)

        try:
            props = data["PropertyTable"]["Properties"][0]
        except (KeyError, IndexError) as e:
            raise PubChemError(f"No properties returned for CID {cid}") from e

        cas = ""
        if fetch_cas:
            try:
                syn_data = self._fetch_url(self._synonyms_url(cid))
                cas = self._extract_cas(syn_data)
            except PubChemError:
                pass

        return self._props_to_molecule(
            props, cas_number=cas, molecule_class=molecule_class,
        )

    def fetch_by_smiles(
        self,
        smiles: str,
        molecule_class: MoleculeClass = MoleculeClass.OTHER,
        fetch_cas: bool = True,
    ) -> Molecule:
        """
        Fetch molecule properties by SMILES string.

        Args:
            smiles: Canonical SMILES (e.g. "O=C1OCCO1" for EC).
            molecule_class: Classification for the returned Molecule.
            fetch_cas: If True, make an additional request for CAS number.

        Returns:
            Molecule with properties populated from PubChem.

        Raises:
            PubChemError: If SMILES not found or API error.
        """
        url = self._properties_url(urllib.request.quote(smiles), "smiles")
        data = self._fetch_url(url)

        try:
            props = data["PropertyTable"]["Properties"][0]
        except (KeyError, IndexError) as e:
            raise PubChemError(f"No properties returned for SMILES '{smiles}'") from e

        cas = ""
        if fetch_cas:
            cid = props.get("CID", 0)
            if cid:
                try:
                    syn_data = self._fetch_url(self._synonyms_url(cid))
                    cas = self._extract_cas(syn_data)
                except PubChemError:
                    pass

        return self._props_to_molecule(
            props, cas_number=cas, molecule_class=molecule_class,
        )

    def fetch_batch(
        self,
        names: List[str],
        molecule_class: MoleculeClass = MoleculeClass.OTHER,
    ) -> Dict[str, Molecule]:
        """
        Fetch multiple molecules by name.

        Args:
            names: List of common names.
            molecule_class: Classification for all returned Molecules.

        Returns:
            Dict mapping name -> Molecule (skips failures silently).
        """
        results = {}
        for name in names:
            try:
                results[name] = self.fetch_by_name(
                    name, molecule_class=molecule_class,
                )
            except PubChemError:
                pass
        return results

    def clear_cache(self):
        """Remove all cached PubChem responses."""
        if self.cache_dir and self.cache_dir.exists():
            for f in self.cache_dir.glob("*.json"):
                f.unlink()


if __name__ == "__main__":
    print("PubChem Loader -- Demo")
    print("=" * 50)

    loader = PubChemLoader()

    # Fetch by name
    try:
        mol = loader.fetch_by_name("ethylene carbonate")
        print(f"Name lookup: {mol.name}")
        print(f"  Formula: {mol.formula}")
        print(f"  MW: {mol.molecular_weight}")
        print(f"  SMILES: {mol.smiles}")
        print(f"  CAS: {mol.cas_number}")
        print(f"  logP: {mol.logP}")
        print(f"  HBD/HBA: {mol.hbond_donors}/{mol.hbond_acceptors}")
    except PubChemError as e:
        print(f"Error: {e}")

    print()

    # Fetch by CID
    try:
        mol2 = loader.fetch_by_cid(7303)  # EC
        print(f"CID lookup: CID {mol2.pubchem_cid} -> {mol2.formula}")
    except PubChemError as e:
        print(f"Error: {e}")
