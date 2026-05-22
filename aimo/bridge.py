"""
MathProofBridge — Convert LLM proof steps into KOMPOSOS-IV Category objects.

This bridge transforms structured proof decompositions from LLMs into
categorical structures that KOMPOSOS-IV can reason about.
"""

import sys
from typing import Dict, List, Any, Optional

# Guard imports for Kaggle compatibility
try:
    from core import Bridge, Object, Morphism
    from data.embeddings import SentenceEmbedder
except ImportError as e:
    print(f"Warning: Could not import KOMPOSOS-IV core: {e}", file=sys.stderr)
    # Provide stubs for testing
    class Bridge:
        def __init__(self, *args, **kwargs):
            self.category = None
        def load(self):
            return self
    class Object:
        def __init__(self, name, type_name, metadata=None, provenance=None):
            self.name = name
            self.type_name = type_name
            self.metadata = metadata or {}
            self.provenance = provenance
    class Morphism:
        def __init__(self, name, source, target, confidence=1.0):
            self.name = name
            self.source = source
            self.target = target
            self.confidence = confidence
    class SentenceEmbedder:
        @staticmethod
        def instance():
            return SentenceEmbedder()
        def embed(self, text):
            # Fallback: hash-based pseudo-embedding
            return [hash(text) % 1000 / 1000.0] * 384


class MathProofBridge(Bridge):
    """
    Bridge that converts LLM proof decompositions into Category objects.
    
    Each proof step becomes an Object.
    Each dependency becomes a Morphism.
    Semantic embeddings enable similarity-based reasoning.
    """
    
    def __init__(self, problem_id: str, llm_output: Dict[str, Any]):
        """
        Initialize bridge with problem context and LLM output.
        
        Args:
            problem_id: Unique identifier (e.g., "problem_42")
            llm_output: Parsed JSON from LLM decomposition
        """
        self.problem_id = problem_id
        self.llm_output = llm_output
        self.domain = llm_output.get("domain", "mixed")
        self.steps = llm_output.get("steps", [])
        self.candidate_paths = llm_output.get("candidate_paths", [])
        
        # Initialize embedder
        try:
            self.embedder = SentenceEmbedder.instance()
        except Exception:
            self.embedder = SentenceEmbedder()
        
        # Call parent init
        super().__init__(
            name=f"bridge_{problem_id}"
        )
    
    def get_objects(self) -> List[Object]:
        """
        Convert each proof step into a Category Object.
        
        Returns:
            List of Object instances, one per step
        """
        objects = []
        
        for step in self.steps:
            step_id = step.get("id", f"step_{len(objects)}")
            step_type = step.get("type", "deduction")
            claim = step.get("claim", "")
            
            # Create object with embedding
            try:
                embedding = self.embedder.embed(claim)
            except Exception:
                # Fallback if embedding fails
                embedding = [0.0] * 384
            
            obj = Object(
                name=step_id,
                type_name=step_type,
                metadata={
                    "claim": claim,
                    "domain": self.domain,
                    "problem_id": self.problem_id,
                    "expression": step.get("expression"),
                    "embedding": embedding,
                },
                provenance=f"llm_{self.problem_id}"
            )
            
            objects.append(obj)
        
        return objects
    
    def get_morphisms(self) -> List[Morphism]:
        """
        Convert step dependencies into Category Morphisms.
        
        Returns:
            List of Morphism instances representing inference edges
        """
        morphisms = []
        
        for step in self.steps:
            step_id = step.get("id", "")
            depends_on = step.get("depends_on", [])
            
            for dep_id in depends_on:
                if dep_id and step_id:
                    mor = Morphism(
                        name="implies",
                        source=dep_id,
                        target=step_id,
                        confidence=0.9  # Default, updated by verifier
                    )
                    morphisms.append(mor)
        
        return morphisms
    
    def score_pair(self, source: str, target: str) -> Dict[str, float]:
        """
        Compute semantic similarity between two steps.
        
        Args:
            source: Source step ID
            target: Target step ID
            
        Returns:
            Dict with semantic_similarity score (0.0-1.0)
        """
        # Find the objects
        source_obj = None
        target_obj = None
        
        for obj in self.get_objects():
            if obj.name == source:
                source_obj = obj
            if obj.name == target:
                target_obj = obj
        
        if not source_obj or not target_obj:
            return {"semantic_similarity": 0.0}
        
        # Get embeddings
        source_emb = source_obj.metadata.get("embedding", [])
        target_emb = target_obj.metadata.get("embedding", [])
        
        if not source_emb or not target_emb:
            return {"semantic_similarity": 0.0}
        
        # Compute cosine similarity
        try:
            dot_product = sum(a * b for a, b in zip(source_emb, target_emb))
            norm_source = sum(a * a for a in source_emb) ** 0.5
            norm_target = sum(b * b for b in target_emb) ** 0.5
            
            if norm_source == 0 or norm_target == 0:
                return {"semantic_similarity": 0.0}
            
            similarity = dot_product / (norm_source * norm_target)
            
            # Clamp to [0, 1]
            similarity = max(0.0, min(1.0, similarity))
            
            return {"semantic_similarity": float(similarity)}
            
        except Exception:
            return {"semantic_similarity": 0.0}
    
    def get_step_claim(self, step_id: str) -> str:
        """Get the claim text for a step."""
        for step in self.steps:
            if step.get("id") == step_id:
                return step.get("claim", "")
        return ""
    
    def get_answer_step(self) -> Optional[str]:
        """Find the step that contains the final answer."""
        for step in self.steps:
            if step.get("type") == "answer":
                return step.get("id")
        
        # Fallback: look for "answer" in claim
        for step in reversed(self.steps):
            claim = step.get("claim", "").lower()
            if "answer" in claim or "=" in claim:
                return step.get("id")
        
        return None
