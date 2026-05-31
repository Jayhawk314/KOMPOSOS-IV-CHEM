import sys
import re

with open('pfas_bridge/pfas_registry.py', 'r', encoding='utf-8') as f:
    content = f.read()

rdkit_imports = '''
try:
    from rdkit import Chem
    _RDKIT_AVAILABLE = True
    _CF3_PATTERN = Chem.MolFromSmarts('[#6X4;H0;!$(*~[Cl,Br,I])](F)(F)F')
    _CF2_PATTERN = Chem.MolFromSmarts('[#6X4;H0;!$(*~[Cl,Br,I])](F)(F)')
except ImportError:
    _RDKIT_AVAILABLE = False

'''

new_is_pfas = '''def is_pfas(name: str) -> bool:
    """
    Check if a material name or SMILES is a known PFAS substance.

    Uses strict OECD 2021 structural matching if RDKit is available and
    the input is a valid SMILES. Falls back to registry and heuristics.
    """
    # 1. Structural OECD Verification (If input is a valid SMILES)
    if _RDKIT_AVAILABLE:
        mol = Chem.MolFromSmiles(name)
        if mol is not None:
            if mol.HasSubstructMatch(_CF3_PATTERN) or mol.HasSubstructMatch(_CF2_PATTERN):
                return True
            # If it's a valid SMILES but failed the SMARTS match, we trust the structural veto
            return False

    # 2. Registry Exact Match
    if get_pfas(name) is not None:
        return True
        
    # 3. Heuristic Substring Match (for brand names like 'Kynar')
    name_lower = name.lower()
    for pattern in _PFAS_SUBSTRINGS:
        if pattern in name_lower:
            return True
            
    return False
'''

# Add imports after the other imports
content = re.sub(r'(from typing import .*?\n)', r'\1' + rdkit_imports, content, count=1)

# Replace the old is_pfas
old_is_pfas_pattern = r'def is_pfas\(name: str\) -> bool:.*?(?=\ndef get_pfas_by_category)'
content = re.sub(old_is_pfas_pattern, new_is_pfas, content, flags=re.DOTALL)

with open('pfas_bridge/pfas_registry.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated pfas_registry.py with OECD structural logic.")