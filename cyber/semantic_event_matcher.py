# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>

"""
Semantic Event Matcher - SecureBERT 2.0 Integration

Maps security events to MITRE ATT&CK techniques using semantic embeddings.
Instead of exact string matching on observables, this uses vector similarity
to match event descriptions to technique descriptions.

Benefits over symbolic matching:
- Catches paraphrased/novel indicators
- Generalizes across naming conventions
- Handles zero-day variants with similar descriptions

Default model: all-mpnet-base-v2 (768d)
Configurable: SecureBERT when available for domain-specific embeddings
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import math

from cyber.mitre_integration import MITREDatabase, ATTACKTechnique


@dataclass
class SemanticMatch:
    """Result of semantically matching an event to a technique."""
    technique_id: str
    technique_name: str
    similarity: float
    matched_text: str


class SemanticEventMatcher:
    """
    Match security events to MITRE ATT&CK techniques using semantic embeddings.

    Pre-encodes all technique descriptions at init time for fast matching.
    Uses cosine similarity between event text and technique descriptions.
    """

    def __init__(self, model_name: str = "all-mpnet-base-v2", mitre_db: Optional[MITREDatabase] = None):
        """
        Initialize the semantic event matcher.

        Args:
            model_name: Sentence transformer model name
            mitre_db: MITRE database instance (creates default if None)
        """
        self.model_name = model_name
        self.mitre_db = mitre_db or MITREDatabase()
        self._engine = None
        self._technique_embeddings: Dict[str, object] = {}
        self._technique_texts: Dict[str, str] = {}
        self._initialized = False

        self._prepare_technique_texts()

    def _prepare_technique_texts(self):
        """Build text descriptions for all techniques."""
        for tech_id, tech in self.mitre_db.techniques.items():
            parts = [tech.name, tech.description]
            # Include observable keywords
            for obs_type, obs_list in tech.observables.items():
                parts.append(f"{obs_type}: {', '.join(obs_list)}")
            # Include tactics
            parts.append("Tactics: " + ", ".join(t.name for t in tech.tactics))
            self._technique_texts[tech_id] = " ".join(parts)

    def _ensure_initialized(self):
        """Lazy-initialize the embeddings engine and pre-encode techniques."""
        if self._initialized:
            return

        try:
            from data.embeddings import EmbeddingsEngine
            self._engine = EmbeddingsEngine(model_name=self.model_name)

            # Pre-encode all technique descriptions
            tech_ids = list(self._technique_texts.keys())
            tech_texts = [self._technique_texts[tid] for tid in tech_ids]

            embeddings = self._engine.embed_batch(tech_texts)
            for tid, emb in zip(tech_ids, embeddings):
                self._technique_embeddings[tid] = emb

            self._initialized = True
        except Exception:
            # Fallback: use simple keyword matching
            self._engine = None
            self._initialized = True

    def match_event(self, event_text: str, top_k: int = 5) -> List[SemanticMatch]:
        """
        Match an event description to MITRE ATT&CK techniques.

        Args:
            event_text: Free-text description of the security event
            top_k: Number of top matches to return

        Returns:
            List of SemanticMatch sorted by similarity (highest first)
        """
        self._ensure_initialized()

        if self._engine is not None and self._technique_embeddings:
            return self._semantic_match(event_text, top_k)
        else:
            return self._keyword_match(event_text, top_k)

    def _semantic_match(self, event_text: str, top_k: int) -> List[SemanticMatch]:
        """Match using embedding similarity."""
        import numpy as np

        event_vec = self._engine.embed(event_text)

        scores = []
        for tech_id, tech_vec in self._technique_embeddings.items():
            sim = self._cosine_similarity_np(event_vec, tech_vec)
            scores.append((tech_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)

        matches = []
        for tech_id, sim in scores[:top_k]:
            tech = self.mitre_db.get_technique(tech_id)
            matches.append(SemanticMatch(
                technique_id=tech_id,
                technique_name=tech.name if tech else tech_id,
                similarity=sim,
                matched_text=self._technique_texts.get(tech_id, "")
            ))

        return matches

    def _keyword_match(self, event_text: str, top_k: int) -> List[SemanticMatch]:
        """Fallback: match using keyword overlap."""
        event_words = set(event_text.lower().split())

        scores = []
        for tech_id, tech_text in self._technique_texts.items():
            tech_words = set(tech_text.lower().split())
            if not tech_words:
                continue
            overlap = len(event_words & tech_words)
            sim = overlap / (math.sqrt(len(event_words)) * math.sqrt(len(tech_words)) + 1e-9)
            scores.append((tech_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)

        matches = []
        for tech_id, sim in scores[:top_k]:
            tech = self.mitre_db.get_technique(tech_id)
            matches.append(SemanticMatch(
                technique_id=tech_id,
                technique_name=tech.name if tech else tech_id,
                similarity=sim,
                matched_text=self._technique_texts.get(tech_id, "")
            ))

        return matches

    def compute_semantic_match_score(
        self,
        observables: Dict[str, str],
        technique: ATTACKTechnique
    ) -> float:
        """
        Compute semantic match score between event observables and a technique.

        Drop-in replacement for AttackChainStrategy._compute_match_score().

        Args:
            observables: Event observables dict (e.g., {"process": "powershell.exe"})
            technique: ATTACKTechnique to match against

        Returns:
            Match score in [0.0, 1.0]
        """
        self._ensure_initialized()

        # Build event text from observables
        event_text = " ".join(f"{k}: {v}" for k, v in observables.items())

        if self._engine is not None and technique.technique_id in self._technique_embeddings:
            event_vec = self._engine.embed(event_text)
            tech_vec = self._technique_embeddings[technique.technique_id]
            sim = self._cosine_similarity_np(event_vec, tech_vec)
            # Normalize to [0, 1] range (cosine can be negative)
            return max(0.0, sim)
        else:
            # Keyword fallback
            tech_text = self._technique_texts.get(technique.technique_id, "")
            event_words = set(event_text.lower().split())
            tech_words = set(tech_text.lower().split())
            if not tech_words:
                return 0.0
            overlap = len(event_words & tech_words)
            return overlap / (math.sqrt(len(event_words)) * math.sqrt(len(tech_words)) + 1e-9)

    @staticmethod
    def _cosine_similarity_np(v1, v2) -> float:
        """Compute cosine similarity between numpy arrays."""
        import numpy as np
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 > 0 and norm2 > 0:
            return float(np.dot(v1, v2) / (norm1 * norm2))
        return 0.0
