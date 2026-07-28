# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
SemanticKanBridge — Semantic similarity for cross-field proof inference.

Replaces keyword matching with embedding-based similarity for
predicting missing proof steps and transferring proof structures.
"""

import sys
from typing import Dict, List, Any, Optional, Tuple

# Guard imports
try:
    from core import Category, Object
    from categorical.kan_extensions import LeftKanExtension, RightKanExtension, Functor
    from data.embeddings import SentenceEmbedder
except ImportError as e:
    print(f"Warning: Could not import dependencies: {e}", file=sys.stderr)
    # Stubs for testing
    class Category:
        def __init__(self, *args, **kwargs):
            self._objects = {}
            self._morphisms = []
        def add(self, name, **kwargs):
            obj = Object(name, kwargs.get('type_name', 'step'))
            self._objects[name] = obj
            return obj
        def connect(self, source, target, **kwargs):
            pass
        def objects(self):
            return self._objects.values()
        def morphisms(self):
            return self._morphisms
    class Object:
        def __init__(self, name, type_name="step", metadata=None):
            self.name = name
            self.type_name = type_name
            self.metadata = metadata or {}
    class SentenceEmbedder:
        @staticmethod
        def instance():
            return SentenceEmbedder()
        def embed(self, text):
            return [hash(text) % 1000 / 1000.0] * 384
    class LeftKanExtension:
        def __init__(self, *args, **kwargs):
            pass
    class RightKanExtension:
        def __init__(self, *args, **kwargs):
            pass
    class Functor:
        def __init__(self, *args, **kwargs):
            pass


# Domain-specific proof templates
MATH_TEMPLATES = {
    "number_theory": [
        "Apply modular arithmetic reduction",
        "Use Chinese Remainder Theorem",
        "Factor via prime decomposition",
        "Apply Euler totient function",
        "Use Fermat's little theorem",
        "Reduce to Diophantine equation",
        "Apply quadratic reciprocity",
        "Use lifting the exponent lemma",
        "Apply Vieta jumping",
        "Use infinite descent",
    ],
    "combinatorics": [
        "Count via bijection",
        "Apply inclusion-exclusion principle",
        "Use generating functions",
        "Solve recurrence relation",
        "Apply pigeonhole principle",
        "Count with symmetry reduction",
        "Use double counting",
        "Apply stars and bars",
        "Use combinatorial identity",
        "Apply Burnside's lemma",
    ],
    "algebra": [
        "Apply Vieta's formulas to polynomial roots",
        "Use AM-GM inequality",
        "Apply Cauchy-Schwarz inequality",
        "Solve functional equation",
        "Sum geometric/arithmetic series",
        "Apply Holder's inequality",
        "Use substitution to simplify",
        "Factor polynomial",
        "Apply quadratic formula",
        "Use complex numbers",
    ],
    "geometry": [
        "Apply law of cosines",
        "Use similar triangles",
        "Apply power of a point",
        "Use coordinate geometry",
        "Apply trigonometric identity",
        "Use circle theorems",
        "Apply Pythagorean theorem",
        "Use angle chasing",
        "Apply Menelaus theorem",
        "Use inversion",
    ],
    "probability": [
        "Compute conditional probability",
        "Calculate expected value",
        "Apply linearity of expectation",
        "Use complementary counting",
        "Apply Bayes' theorem",
        "Use indicator variables",
        "Apply Markov chain",
        "Use symmetry argument",
    ],
}


class SemanticKanBridge:
    """
    Bridge that uses semantic similarity for Kan extension predictions.
    
    Replaces keyword matching with embedding-based similarity,
    enabling cross-field proof structure transfer.
    """
    
    def __init__(self, embedder: Optional[SentenceEmbedder] = None, threshold: float = 0.65):
        """
        Initialize semantic Kan bridge.
        
        Args:
            embedder: Sentence embedding model
            threshold: Cosine similarity threshold for matches (default 0.65)
        """
        try:
            self.embedder = embedder or SentenceEmbedder.instance()
        except Exception:
            self.embedder = SentenceEmbedder()
        
        self.threshold = threshold
        
        # Pre-compute template embeddings
        self._template_embeddings = {}
        self._compute_template_embeddings()
    
    def _compute_template_embeddings(self):
        """Pre-compute embeddings for all domain templates."""
        for domain, templates in MATH_TEMPLATES.items():
            self._template_embeddings[domain] = []
            for template in templates:
                try:
                    emb = self.embedder.embed(template)
                    self._template_embeddings[domain].append({
                        "claim": template,
                        "embedding": emb,
                        "domain": domain,
                    })
                except Exception:
                    pass
    
    def _cosine_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        if not emb1 or not emb2:
            return 0.0
        
        try:
            dot_product = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = sum(a * a for a in emb1) ** 0.5
            norm2 = sum(b * b for b in emb2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0
    
    def predict_missing_steps(
        self,
        cat: Category,
        known_steps: List[str],
        domain: str
    ) -> List[Dict[str, Any]]:
        """
        Predict missing proof steps using semantic similarity.
        
        Args:
            cat: Category with existing proof steps
            known_steps: List of known step IDs
            domain: Problem domain (number_theory, combinatorics, etc.)
            
        Returns:
            List of predicted steps with confidence scores
        """
        predictions = []
        
        # Get embeddings for known steps
        known_embeddings = []
        for obj in cat.objects():
            if obj.name in known_steps:
                emb = obj.metadata.get("embedding", [])
                if emb:
                    known_embeddings.append(emb)
        
        if not known_embeddings:
            return predictions
        
        # Get templates for this domain
        templates = self._template_embeddings.get(domain, [])
        
        # Find templates similar to known steps
        for template in templates:
            template_emb = template.get("embedding", [])
            
            max_similarity = 0.0
            for known_emb in known_embeddings:
                sim = self._cosine_similarity(template_emb, known_emb)
                max_similarity = max(max_similarity, sim)
            
            # If similar to existing steps, suggest as missing
            if max_similarity > self.threshold:
                predictions.append({
                    "claim": template["claim"],
                    "confidence": float(max_similarity),
                    "suggested_type": "deduction",
                    "domain": template["domain"],
                })
        
        # Sort by confidence
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Return top 5
        return predictions[:5]
    
    def domain_transfer(
        self,
        source_cat: Category,
        target_domain: str
    ) -> List[Tuple[str, str, float]]:
        """
        Transfer proof structure from source to target domain.
        
        Uses Right Kan extension: given target domain, what do we need?
        
        Args:
            source_cat: Category with source proof structure
            target_domain: Target domain name
            
        Returns:
            List of (source_step, target_step, confidence) tuples
        """
        transfers = []
        
        # Get source step embeddings
        source_steps = []
        for obj in source_cat.objects():
            emb = obj.metadata.get("embedding", [])
            claim = obj.metadata.get("claim", "")
            if emb and claim:
                source_steps.append({
                    "id": obj.name,
                    "claim": claim,
                    "embedding": emb,
                })
        
        # Get target domain templates
        target_templates = self._template_embeddings.get(target_domain, [])
        
        # Find semantic matches
        for source in source_steps:
            for template in target_templates:
                sim = self._cosine_similarity(
                    source["embedding"],
                    template["embedding"]
                )
                
                if sim > self.threshold:
                    transfers.append((
                        source["claim"],
                        template["claim"],
                        float(sim),
                    ))
        
        # Sort by confidence
        transfers.sort(key=lambda x: x[2], reverse=True)
        
        return transfers[:10]
    
    def find_analogous_steps(
        self,
        step_claim: str,
        domain: str
    ) -> List[Dict[str, Any]]:
        """
        Find steps in a domain that are analogous to a given claim.
        
        Args:
            step_claim: The claim to find analogues for
            domain: Domain to search in
            
        Returns:
            List of analogous steps with similarity scores
        """
        try:
            claim_emb = self.embedder.embed(step_claim)
        except Exception:
            return []
        
        analogous = []
        templates = self._template_embeddings.get(domain, [])
        
        for template in templates:
            sim = self._cosine_similarity(claim_emb, template["embedding"])
            if sim > self.threshold:
                analogous.append({
                    "claim": template["claim"],
                    "similarity": float(sim),
                    "domain": domain,
                })
        
        analogous.sort(key=lambda x: x["similarity"], reverse=True)
        return analogous[:5]
