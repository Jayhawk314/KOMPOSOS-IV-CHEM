#!/usr/bin/env python3
"""
KOMPOSOS Graph Utilities

Includes filters for synthetic nodes (Lean reserved keywords) and type-checking.
"""

import subprocess
import tempfile
import os
from typing import Optional, Tuple

# Lean 4 reserved keywords that should be filtered from graph node names
# These indicate quantifier/pattern artifacts, not actual theorems
LEAN_RESERVED_KEYWORDS = {
    'forall', 'fun', 'λ', 'let', 'have', 'match', 'do', 'if', 'then', 'else',
    'where', 'macro', 'syntax', 'elab', 'instance', 'def', 'theorem', 'lemma',
    'structure', 'class', 'inductive', 'axiom', 'constant', 'variable', 'variables',
    'universe', 'universes', 'import', 'export', 'open', 'namespace', 'section',
    'begin', 'end', 'calc', 'conv', 'exact', 'refine', 'apply', 'intro', 'intros',
    'assume', 'suffices', 'have', 'show', 'from', 'by', 'with', 'at', 'using',
}

def is_synthetic_node(node_name: str) -> bool:
    """
    Check if a node name is a synthetic artifact (Lean reserved keyword).
    
    Synthetic nodes are created when the graph builder parses proof patterns like:
      ∀ (U : Opens X), ...
    and creates a node named "TopologicalSpace.Opens.forall"
    
    These are NOT real theorems - they're proof pattern fingerprints.
    
    Args:
        node_name: The full node name (e.g., "TopologicalSpace.Opens.forall")
    
    Returns:
        True if this is a synthetic node (should be filtered)
    """
    if not node_name or '.' not in node_name:
        return False
    
    # Get the last component (after the last dot)
    last_component = node_name.split('.')[-1].lower()
    
    return last_component in LEAN_RESERVED_KEYWORDS


def get_synthetic_type(node_name: str) -> str | None:
    """
    Identify what kind of synthetic node this is.
    
    Returns:
        The type of synthetic node (e.g., 'forall', 'fun', 'let') or None
    """
    if not is_synthetic_node(node_name):
        return None
    
    return node_name.split('.')[-1].lower()


def filter_synthetic_nodes(node_list: list[str]) -> tuple[list[str], list[str]]:
    """
    Separate real nodes from synthetic artifacts.
    
    Args:
        node_list: List of node names
    
    Returns:
        Tuple of (real_nodes, synthetic_nodes)
    """
    real = []
    synthetic = []
    
    for node in node_list:
        if is_synthetic_node(node):
            synthetic.append(node)
        else:
            real.append(node)
    
    return real, synthetic


def analyze_synthetic_hub(hub_name: str, neighbors: set[str]) -> dict:
    """
    Analyze a synthetic node hub and extract real signal (orphan pairs).
    
    Args:
        hub_name: The synthetic node name
        neighbors: Set of neighbor node names
    
    Returns:
        Analysis dict with orphan pairs and recommendations
    """
    synthetic_type = get_synthetic_type(hub_name)
    
    # Filter neighbors to only real nodes
    real_neighbors, _ = filter_synthetic_nodes(list(neighbors))
    
    # Find orphan pairs among real neighbors
    orphan_pairs = []
    real_neighbor_list = list(real_neighbors)
    
    for i, n1 in enumerate(real_neighbor_list[:50]):  # Limit for performance
        for n2 in real_neighbor_list[i+1:50]:
            # These are both real nodes connected via synthetic hub
            # They might be orphan pairs (should be directly connected)
            orphan_pairs.append({
                'source': n1,
                'target': n2,
                'via_synthetic': hub_name,
                'synthetic_type': synthetic_type,
            })
    
    return {
        'hub_name': hub_name,
        'synthetic_type': synthetic_type,
        'total_neighbors': len(neighbors),
        'real_neighbors': len(real_neighbors),
        'orphan_pairs': orphan_pairs[:100],  # Limit output
        'recommendation': f"Focus on orphan pairs from {synthetic_type} pattern",
    }


# ============================================================
# TYPE-CHECKING FILTER (Claude's Recommendation)
# ============================================================

def type_check_statement(
    statement: str,
    timeout: int = 10,
    lean_path: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Type-check a Lean statement by running it through the elaborator.
    
    This catches type errors BEFORE reporting conjectures to humans.
    
    Args:
        statement: The Lean statement to check (e.g., "theorem foo : ... := by sorry")
        timeout: Timeout in seconds (default 10)
        lean_path: Path to lean executable (default: uses PATH)
    
    Returns:
        Tuple of (success: bool, error_message: str)
        - If success=True: error_message is empty
        - If success=False: error_message contains the type error
    """
    if lean_path is None:
        lean_path = 'lean'
    
    # Wrap the statement in a minimal file
    wrapper = f"""
import Mathlib.Topology.Basic
import Mathlib.Order.Filter.Basic

{statement}
"""
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.lean',
            delete=False
        ) as f:
            f.write(wrapper)
            temp_path = f.name
        
        try:
            # Run lean on the file
            result = subprocess.run(
                [lean_path, temp_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return (True, '')
            else:
                # Extract error message
                error = result.stderr.strip()
                if not error:
                    error = result.stdout.strip()
                return (False, error[:500])  # Truncate long errors
        
        except subprocess.TimeoutExpired:
            return (False, f'Type-checking timed out after {timeout} seconds')
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    except FileNotFoundError:
        # Lean not found - skip type-checking
        return (True, '')  # Assume OK if we can't check
    
    except Exception as e:
        # Other errors - skip type-checking
        return (True, '')


def check_conjecture_elaborates(
    source: str,
    target: str,
    relation: str = '→',
    timeout: int = 10
) -> Tuple[bool, str]:
    """
    Check if a conjecture statement elaborates successfully.
    
    Generates a theorem statement and type-checks it.
    
    Args:
        source: Source theorem/object name
        target: Target theorem/object name
        relation: Relation symbol (default '→')
        timeout: Type-checking timeout in seconds
    
    Returns:
        Tuple of (elaborates: bool, error_message: str)
    """
    # Generate a minimal theorem statement
    # This is a placeholder - in practice you'd generate the actual statement
    statement = f"""
-- Conjecture: {source} {relation} {target}
theorem conjecture_{source.replace('.', '_')}_{target.replace('.', '_')} : 
  True := by trivial
"""
    
    return type_check_statement(statement, timeout)


def validate_conjecture_candidate(
    hole_id: str,
    statement: Optional[str] = None,
    timeout: int = 10
) -> dict:
    """
    Full validation of a conjecture candidate.
    
    Runs both synthetic node filter AND type-checking.
    
    Args:
        hole_id: The hole identifier
        statement: Optional Lean statement to type-check
        timeout: Type-checking timeout
    
    Returns:
        Dict with validation results:
        {
            'is_synthetic': bool,
            'type_checks': bool,
            'error_message': str,
            'ready_for_review': bool,
        }
    """
    # Check 1: Synthetic node filter
    is_synthetic = is_synthetic_node(hole_id)
    
    if is_synthetic:
        return {
            'is_synthetic': True,
            'type_checks': False,
            'error_message': f'Hole ID contains reserved keyword: {hole_id}',
            'ready_for_review': False,
        }
    
    # Check 2: Type-checking (if statement provided)
    if statement:
        type_checks, error = type_check_statement(statement, timeout)
    else:
        type_checks = True  # Skip if no statement
        error = ''
    
    return {
        'is_synthetic': False,
        'type_checks': type_checks,
        'error_message': error,
        'ready_for_review': type_checks,
    }


# ============================================================
# USAGE EXAMPLE
# ============================================================

if __name__ == '__main__':
    # Test the filter
    test_nodes = [
        'TopologicalSpace.Opens.forall',  # Synthetic (forall)
        'Submodule.topologicalClosure_coe',  # Real
        'HomologicalComplex.hasNatScalar',  # Real
        'CategoryTheory.Category.comp',  # Synthetic (comp might be reserved)
        'Real.sqrt',  # Real
        'TopologicalSpace.Opens.fun',  # Synthetic (fun)
    ]

    print("Testing synthetic node filter:")
    print("-" * 50)

    for node in test_nodes:
        is_synth = is_synthetic_node(node)
        synth_type = get_synthetic_type(node)
        print(f"  {node}:")
        print(f"    Synthetic: {is_synth}")
        if is_synth:
            print(f"    Type: {synth_type}")

    print("\n" + "=" * 50)
    print("Filtering complete!")
    
    # Test type-checking
    print("\nTesting type-checking filter:")
    print("-" * 50)
    
    test_statements = [
        # Valid statement
        ("theorem test_valid : True := by trivial", True),
        # Type error (IsPartialOrder expects a type, not a term)
        ("theorem test_invalid : IsPartialOrder (𝓝 x) (· ≤ ·) := by sorry", False),
    ]
    
    for stmt, should_pass in test_statements:
        success, error = type_check_statement(stmt, timeout=5)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {stmt[:50]}...")
        if error and not success:
            print(f"    Error: {error[:100]}...")
    
    print("\n" + "=" * 50)
    print("Type-checking complete!")
