import json
import sqlite3
import hashlib
import time
import sys
from pathlib import Path

# Add project root to path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
from mof_bridge.mp_mof_loader import MOFLinkerCache

def import_mofsimplify_to_cache():
    json_path = "data/cache/mofsimplify_stability.json"
    if not Path(json_path).exists():
        print(f"Error: {json_path} not found")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    cache = MOFLinkerCache()
    # Ensure DB is initialized
    cache._init_database()
    
    conn = sqlite3.connect(cache.db_path)
    cursor = conn.cursor()
    
    imported = 0
    skipped_size = 0
    skipped_invalid = 0
    
    print(f"Importing linkers from MOFSimplify (range 18-26)...")
    
    for mof in data:
        core_name = mof.get("CoRE_name", "unknown")
        linkers_dict = mof.get("linkers", {})
        
        for l_id, mol2_block in linkers_dict.items():
            mol = Chem.MolFromMol2Block(mol2_block)
            if not mol:
                skipped_invalid += 1
                continue
                
            heavy_count = mol.GetNumHeavyAtoms()
            if not (18 <= heavy_count <= 26):
                skipped_size += 1
                continue
                
            smiles = Chem.MolToSmiles(mol)
            linker_id = hashlib.md5(smiles.encode()).hexdigest()[:16]
            
            # Check if exists
            cursor.execute("SELECT 1 FROM linkers WHERE smiles = ?", (smiles,))
            if cursor.fetchone():
                continue
                
            try:
                # Basic properties
                mw = Descriptors.MolWt(mol)
                logp = Descriptors.MolLogP(mol)
                hbd = Descriptors.NumHDonors(mol)
                hba = Descriptors.NumHAcceptors(mol)
                rot = Descriptors.NumRotatableBonds(mol)
                arom = Descriptors.NumAromaticRings(mol)
                formula = rdMolDescriptors.CalcMolFormula(mol)
                
                cursor.execute("""
                    INSERT INTO linkers (
                        linker_id, smiles, formula, heavy_atom_count,
                        mp_source_id, molecular_weight, logp,
                        hbond_donors, hbond_acceptors, rotatable_bonds,
                        aromatic_rings, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    linker_id, smiles, formula, heavy_count,
                    f"mofsimplify:{core_name}", mw, logp,
                    hbd, hba, rot, arom, int(time.time())
                ))
                imported += 1
            except Exception as e:
                print(f"Error importing {smiles[:30]}: {e}")
                
    conn.commit()
    conn.close()
    
    print(f"DONE!")
    print(f"  Imported: {imported}")
    print(f"  Skipped (wrong size): {skipped_size}")
    print(f"  Skipped (invalid): {skipped_invalid}")
    print(f"  Total in cache: {cache.entry_count()}")

if __name__ == "__main__":
    import_mofsimplify_to_cache()
