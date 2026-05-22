"""MOF Linker Designer API Routes."""

from fastapi import APIRouter, HTTPException

from api.models import (
    MOFLinkerDesignRequest,
    MOFLinkerDesignResponse,
    MOFLinkerCandidateOutput,
)

router = APIRouter(prefix="/api/v1", tags=["mof-designer"])


@router.post("/design-mof-linker", response_model=MOFLinkerDesignResponse)
def design_mof_linker(req: MOFLinkerDesignRequest):
    """Generate novel 22-atom MOF linkers with KOMPOSOS verdicts.

    This endpoint:
    1. Generates novel 22-atom linker candidates
    2. Scores each with 5 KOMPOSOS verdicts (synthesizability, toxicity, stability, activity, conductivity)
    3. Uses ZFC + CAT dual-engine reasoning
    4. Filters by verdict criteria
    5. Ranks by morphism integrity or verdict count
    6. Returns top 50 candidates

    Args:
        req: MOFLinkerDesignRequest with generation parameters

    Returns:
        MOFLinkerDesignResponse with ranked candidates

    Raises:
        HTTPException 400: If invalid application context or parameters
        HTTPException 500: If generation fails
    """
    # Validate application context
    valid_apps = ["breath_VOC_sensing", "food_safety", "PFAS_detection", "custom"]
    if req.application_context not in valid_apps:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid application_context '{req.application_context}'. "
                   f"Must be one of: {', '.join(valid_apps)}"
        )

    # Validate ranking mode
    valid_ranking = ["morphism_integrity", "verdict_count"]
    if req.ranking_mode not in valid_ranking:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ranking_mode '{req.ranking_mode}'. "
                   f"Must be one of: {', '.join(valid_ranking)}"
        )

    # Import screening components
    try:
        from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"MOF bridge not available: {e}. "
                   "Install: pip install rdkit"
        )

    # Create screening spec
    spec = LinkerScreeningSpec(
        application_context=req.application_context,
        num_candidates=req.num_candidates,
        require_all_agree=req.require_all_agree,
        allow_hollow=req.allow_hollow,
        functional_groups=req.functional_groups,
        exclude_elements=req.exclude_elements,
        ranking_mode=req.ranking_mode,
    )

    # Run screening
    try:
        screener = LinkerScreener()
        result = screener.screen(spec)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"MOF linker cache not available. "
                   "Run: python scripts/download_mof_linkers.py --api-key YOUR_KEY"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Screening failed: {str(e)}"
        )

    # Convert candidates to output format
    candidates_output = []
    for candidate in result.candidates:
        # Get molecular properties (formula, MW) from SMILES if available
        formula = ""
        molecular_weight = 0.0

        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors
            mol = Chem.MolFromSmiles(candidate.linker_smiles)
            if mol:
                formula = Chem.rdMolDescriptors.CalcMolFormula(mol)
                molecular_weight = Descriptors.MolWt(mol)
        except Exception:
            # If RDKit not available or fails, leave blank
            pass

        candidates_output.append(
            MOFLinkerCandidateOutput(
                smiles=candidate.linker_smiles,
                formula=formula,
                molecular_weight=molecular_weight,
                verdicts=candidate.verdicts,
                verdict_scores=candidate.verdict_scores,
                morphism_integrity=candidate.morphism_integrity,
                reasoning_traces=candidate.reasoning_traces,
                overall_viable=candidate.overall_viable,
            )
        )

    return MOFLinkerDesignResponse(
        num_generated=result.num_generated,
        num_passed_all=result.num_passed_all,
        candidates=candidates_output,
        avg_morphism_integrity=result.avg_morphism_integrity,
        best_morphism_integrity=result.best_morphism_integrity,
        generation_time_sec=result.generation_time_sec,
    )
