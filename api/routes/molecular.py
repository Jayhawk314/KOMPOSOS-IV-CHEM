# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Molecular bridge API endpoints."""

from fastapi import APIRouter, HTTPException

from api.models import (
    MolecularCompatibilityRequest,
    MolecularCompatibilityResponse,
    MoleculeListResponse,
    MoleculeSearchRequest,
    MoleculeSearchResponse,
    MoleculeSearchResult,
)
from molecular_bridge.molecule_properties import (
    ALL_MOLECULES, MoleculeClass, get_molecules_by_class,
)
from molecular_bridge.interface_validator import validate_interface
from molecular_bridge.constraint_search import (
    search_by_constraints,
    get_heavy_atom_count,
)

router = APIRouter(prefix="/api/v1", tags=["molecular"])


@router.get("/molecules", response_model=MoleculeListResponse)
def list_molecules():
    """List all molecules grouped by class."""
    classes = {}
    for cls in MoleculeClass:
        mols = get_molecules_by_class(cls)
        if mols:
            classes[cls.value] = sorted(mols.keys())

    return MoleculeListResponse(
        total=len(ALL_MOLECULES),
        classes=classes,
    )


@router.post(
    "/molecular-compatibility",
    response_model=MolecularCompatibilityResponse,
)
def check_molecular_compatibility(req: MolecularCompatibilityRequest):
    """Check compatibility between two molecules.

    Uses all five molecular interaction scorers (electronic compatibility,
    thermodynamic stability, steric compatibility, solubility compatibility,
    reactivity risk) to produce a composite score.
    """
    try:
        result = validate_interface(req.molecule_a, req.molecule_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return MolecularCompatibilityResponse(
        molecule_a=req.molecule_a,
        molecule_b=req.molecule_b,
        scores=result.to_dict(),
        viable=result.viable,
    )


@router.post("/search-molecules", response_model=MoleculeSearchResponse)
def search_molecules(req: MoleculeSearchRequest):
    """Search molecules by exact structural constraints.

    Solves Prof. Kulik's (MIT) challenge: "Design me a ligand with exactly
    22 heavy atoms." Unlike LLMs, this endpoint NEVER hallucinates — it
    returns ONLY molecules from the curated database that match ALL
    constraints, or an empty list.

    All constraints are combined with AND logic.
    """
    # Parse molecule_class if provided
    mol_class = None
    if req.molecule_class:
        try:
            mol_class = MoleculeClass(req.molecule_class)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown molecule_class '{req.molecule_class}'. "
                       f"Valid: {[mc.value for mc in MoleculeClass]}",
            )

    # Convert list ranges to tuples
    atom_range = tuple(req.heavy_atom_range) if req.heavy_atom_range else None
    mw_range = tuple(req.molecular_weight_range) if req.molecular_weight_range else None

    results = search_by_constraints(
        heavy_atom_count=req.heavy_atom_count,
        heavy_atom_range=atom_range,
        functional_groups=req.functional_groups,
        molecular_weight_range=mw_range,
        exclude_elements=req.exclude_elements,
        include_elements=req.include_elements,
        molecule_class=mol_class,
    )

    # Build constraint list for transparency
    constraints = []
    if req.heavy_atom_count is not None:
        constraints.append(f"heavy_atom_count={req.heavy_atom_count}")
    if req.heavy_atom_range:
        constraints.append(f"heavy_atom_range={req.heavy_atom_range}")
    if req.functional_groups:
        constraints.append(f"functional_groups={req.functional_groups}")
    if req.molecular_weight_range:
        constraints.append(f"molecular_weight_range={req.molecular_weight_range}")
    if req.exclude_elements:
        constraints.append(f"exclude_elements={req.exclude_elements}")
    if req.include_elements:
        constraints.append(f"include_elements={req.include_elements}")
    if req.molecule_class:
        constraints.append(f"molecule_class={req.molecule_class}")

    return MoleculeSearchResponse(
        num_results=len(results),
        constraints_applied=constraints,
        results=[
            MoleculeSearchResult(
                name=mol.name,
                formula=mol.formula,
                molecular_weight=mol.molecular_weight,
                heavy_atom_count=get_heavy_atom_count(mol),
                molecule_class=mol.molecule_class.value,
                functional_groups=list(mol.functional_groups),
            )
            for mol in results
        ],
    )
