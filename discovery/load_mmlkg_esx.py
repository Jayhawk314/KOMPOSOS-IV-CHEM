#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Load MMLKG directly from ESX files using the adapter."""

import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Tuple

from core.types import Object, Morphism
from core.category import Category
from domains.mathematics.schema import theorem_object, definition_object, proof_morphism
from domains.mathematics.mmlkg_adapter import MMLKGAdapter

# Paths
ESX_DIR = 'data_sources/mmlkg/esx_files-main/esx_mml'
MML_LAR = 'data_sources/mmlkg/esx_files-main/mml.lar'

def parse_mml_lar(filepath: str) -> Dict[str, List[str]]:
    """Parse mml.lar for article dependencies."""
    article_deps: Dict[str, List[str]] = {}
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ':' in line:
                parts = line.split(':', 1)
                article = parts[0].strip()
                deps_str = parts[1].strip() if len(parts) > 1 else ''
                deps = [d.strip() for d in deps_str.split() if d.strip()]
                article_deps[article] = deps
    
    return article_deps

def mizar_id_to_field(mizar_id: str) -> str:
    """Map Mizar article ID to mathematical field."""
    article = mizar_id.split(':')[0] if ':' in mizar_id else mizar_id
    prefix = article.split('_')[0] if '_' in article else article
    
    field_map = {
        'TOPREAL': 'general_topology',
        'COMPTS': 'general_topology',
        'METRIC': 'general_topology',
        'ALGSTR': 'group_theory',
        'GROUP': 'group_theory',
        'RING': 'commutative_algebra',
        'VECTSP': 'linear_algebra',
        'RLVECT': 'linear_algebra',
        'MATRIX': 'linear_algebra',
        'NAT': 'number_theory',
        'REAL': 'real_analysis',
        'SEQ': 'real_analysis',
        'MEASURE': 'measure_theory',
        'FUNCT': 'logic_foundations',
        'ZFMISC': 'logic_foundations',
        'FINSET': 'combinatorics',
        'GRAPH': 'combinatorics',
    }
    
    return field_map.get(prefix.upper(), 'unknown')

def load_esx_files(esx_dir: str) -> Tuple[List[Object], Dict[str, str]]:
    """Load theorems/definitions from ESX files."""
    objects: List[Object] = []
    id_to_article: Dict[str, str] = {}
    
    theorem_count = 0
    def_count = 0
    file_count = 0
    
    for root, dirs, files in os.walk(esx_dir):
        for fname in files:
            if not fname.endswith('.esx'):
                continue
            
            filepath = os.path.join(root, fname)
            file_count += 1
            
            try:
                tree = ET.parse(filepath)
                root_elem = tree.getroot()
                
                # Extract article ID from filename or root element
                article_id = fname.replace('.esx', '')
                
                # Look for theorem/definition elements
                for elem in root_elem.iter():
                    tag = elem.tag.lower()
                    
                    # Check for various Mizar element types
                    if any(kw in tag for kw in ['theorem', 'lemma', 'proposition', 'statement', 'scheme']):
                        item_id = elem.get('id', elem.get('label', ''))
                        if not item_id:
                            continue
                        
                        # Build full ID
                        full_id = f"{article_id}:{item_id}"
                        
                        content = elem.text or ''
                        for child in elem:
                            if child.text:
                                content += ' ' + (child.text or '')
                        
                        field = mizar_id_to_field(full_id)
                        
                        obj = theorem_object(
                            name=full_id,
                            statement=content[:500] if content else '',
                            field=field,
                            source='mmlkg',
                            article=article_id,
                        )
                        objects.append(obj)
                        id_to_article[full_id] = article_id
                        theorem_count += 1
                        
                    elif any(kw in tag for kw in ['definition', 'def']):
                        item_id = elem.get('id', elem.get('label', ''))
                        if not item_id:
                            continue
                        
                        full_id = f"{article_id}:{item_id}"
                        
                        content = elem.text or ''
                        for child in elem:
                            if child.text:
                                content += ' ' + (child.text or '')
                        
                        field = mizar_id_to_field(full_id)
                        
                        obj = definition_object(
                            name=full_id,
                            statement=content[:500] if content else '',
                            field=field,
                            source='mmlkg',
                            article=article_id,
                        )
                        objects.append(obj)
                        id_to_article[full_id] = article_id
                        def_count += 1
                        
            except Exception as e:
                continue
    
    print(f"Processed {file_count} ESX files")
    print(f"Found {theorem_count} theorems, {def_count} definitions")
    
    return objects, id_to_article

def create_morphisms(objects: List[Object], id_to_article: Dict[str, str], 
                     article_deps: Dict[str, List[str]]) -> List[Morphism]:
    """Create dependency morphisms from article dependencies."""
    morphisms: List[Morphism] = []
    
    # Build article -> theorems mapping
    article_theorems: Dict[str, List[str]] = {}
    for obj in objects:
        article = id_to_article.get(obj.name, '')
        if article:
            if article not in article_theorems:
                article_theorems[article] = []
            article_theorems[article].append(obj.name)
    
    morphism_count = 0
    for article, deps in article_deps.items():
        src_theorems = article_theorems.get(article, [])[:20]  # Limit per article
        
        for dep_article in deps[:10]:  # Limit dependencies
            tgt_theorems = article_theorems.get(dep_article, [])[:5]
            
            for src in src_theorems[:5]:
                for tgt in tgt_theorems:
                    if src != tgt:
                        morphisms.append(
                            proof_morphism(
                                name=f"mmlkg:{src}->{tgt}",
                                source_thm=src,
                                target_thm=tgt,
                                confidence=0.85,
                                proof_type='article_dependency',
                                source='mmlkg',
                            )
                        )
                        morphism_count += 1
    
    print(f"Created {morphism_count} dependency morphisms")
    return morphisms

def main():
    print("=" * 60)
    print("Loading MMLKG from ESX files")
    print("=" * 60)
    
    print(f"ESX directory: {ESX_DIR}")
    print(f"mml.lar: {MML_LAR}")
    
    if not os.path.exists(ESX_DIR):
        print(f"ERROR: ESX directory not found: {ESX_DIR}")
        return
    
    if not os.path.exists(MML_LAR):
        print(f"ERROR: mml.lar not found: {MML_LAR}")
        return
    
    # Parse article dependencies
    print("\nParsing mml.lar...")
    article_deps = parse_mml_lar(MML_LAR)
    print(f"Found {len(article_deps)} article dependencies")
    
    # Load ESX files
    print("\nLoading ESX files...")
    objects, id_to_article = load_esx_files(ESX_DIR)
    
    if not objects:
        print("No objects found in ESX files, using demo data")
        adapter = MMLKGAdapter(None)
        adapter._parse()
        objects = adapter._objects
        article_deps = {}
    
    # Create morphisms
    print("\nCreating dependency morphisms...")
    morphisms = create_morphisms(objects, id_to_article, article_deps)
    
    # Load into category
    print("\nLoading into Category...")
    cat = Category(name='mmlkg', db_path=':memory:')
    
    result = cat.bulk_add(objects, morphisms)
    print(f"\nLoaded: {result}")
    
    # Statistics
    print(f"\nCategory statistics:")
    print(f"  Objects: {len(list(cat.objects()))}")
    print(f"  Edges: {len(cat.as_edges())}")
    
    # Sample
    print("\nSample objects:")
    for i, obj in enumerate(cat.objects()):
        if i >= 5:
            break
        print(f"  - {obj.name} ({obj.type_name}, {obj.metadata.get('field', 'unknown')})")
    
    print("\nSample edges:")
    for i, (s, t, w) in enumerate(cat.as_edges()):
        if i >= 5:
            break
        print(f"  - {s} -> {t} (weight={w})")

if __name__ == '__main__':
    main()
