# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Biological Protein Embeddings using ESM-2.

Uses Facebook's ESM-2 (Evolutionary Scale Modeling) protein language model
to generate biologically meaningful embeddings from amino acid sequences.

Unlike text embeddings (trained on papers), ESM-2 is trained on 250M protein
sequences and captures:
- Sequence homology (similar sequences = similar function)
- Structural compatibility (binding domains)
- Functional conservation (kinases cluster together)

Model: esm2_t33_650M_UR50D (650M parameters, 1280 dimensions)
Input: Amino acid sequence (string like "MEEPQSDPSV...")
Output: 1280-dimensional embedding vector

Compatible with existing EmbeddingsEngine interface.
"""
from __future__ import annotations

import sqlite3
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import json


# ESM-2 650M model (best quality, but slower than 35M/150M variants)
DEFAULT_MODEL = 'esm2_t33_650M_UR50D'
CACHE_DIR = Path.home() / ".komposos3"


class BiologicalEmbeddingsEngine:
    """
    ESM-2 protein language model embeddings.

    Compatible with EmbeddingsEngine interface for drop-in replacement
    in CategoricalOracle pipeline.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = 'cpu',
        cache_path: Optional[Path] = None
    ):
        """
        Initialize ESM-2 embeddings engine.

        Args:
            model_name: ESM model name (default: esm2_t33_650M_UR50D)
            device: 'cpu' or 'cuda'
            cache_path: Path to SQLite cache file
        """
        self.model_name = model_name
        self.device = device
        self.cache_path = cache_path or (CACHE_DIR / "bio_embeddings_cache.db")

        self._model = None
        self._alphabet = None
        self._batch_converter = None
        self._dimension = 1280  # ESM-2 650M output dimension

        self._sequences: Dict[str, str] = {}  # gene_name -> sequence
        self._memory_cache: Dict[str, np.ndarray] = {}
        self._db_initialized = False

        # Initialize
        self._init_model()
        self._load_sequences()
        self._init_cache_db()

    def _init_model(self):
        """Load ESM-2 model from fair-esm library."""
        try:
            import esm

            print(f"[BiologicalEmbeddings] Loading {self.model_name}...")
            print(f"  Device: {self.device}")
            print(f"  This may take 30-60 seconds for first load...")

            # Load model and alphabet
            self._model, self._alphabet = esm.pretrained.load_model_and_alphabet(
                self.model_name
            )
            self._model = self._model.to(self.device)
            self._model.eval()  # Inference mode

            # Batch converter for tokenization
            self._batch_converter = self._alphabet.get_batch_converter()

            # Get actual dimension from model
            self._dimension = self._model.embed_dim

            print(f"[BiologicalEmbeddings] Loaded: {self.model_name} ({self._dimension}d)")

        except ImportError:
            print("[BiologicalEmbeddings] ERROR: fair-esm not installed")
            print("  Install with: pip install fair-esm")
            self._model = None

        except Exception as e:
            print(f"[BiologicalEmbeddings] ERROR loading model: {e}")
            self._model = None

    def _load_sequences(self):
        """Load protein sequences from downloaded data."""
        # Try AML sequences first, then fall back to cancer proteins
        sequences_dir = Path("data/proteins/sequences_aml")
        if not sequences_dir.exists() or not (sequences_dir / "metadata.json").exists():
            sequences_dir = Path("data/proteins/sequences")

        metadata_file = sequences_dir / "metadata.json"

        if not metadata_file.exists():
            print(f"[BiologicalEmbeddings] WARNING: No sequences found at {metadata_file}")
            print("  Run scripts/download_uniprot_aml_sequences.py or scripts/download_uniprot_sequences.py first")
            return

        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            for protein in metadata["proteins"]:
                gene_name = protein["gene_name"]
                sequence = protein["sequence"]
                self._sequences[gene_name] = sequence

            print(f"[BiologicalEmbeddings] Loaded {len(self._sequences)} protein sequences")

        except Exception as e:
            print(f"[BiologicalEmbeddings] ERROR loading sequences: {e}")

    def _init_cache_db(self):
        """Initialize SQLite cache database."""
        if self._db_initialized:
            return

        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(str(self.cache_path))
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bio_embeddings (
                    gene_name TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model TEXT NOT NULL,
                    sequence TEXT NOT NULL,
                    sequence_length INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uniprot_id TEXT
                )
            """)

            conn.commit()
            conn.close()

            self._db_initialized = True

        except Exception as e:
            print(f"[BiologicalEmbeddings] WARNING: Could not initialize cache: {e}")

    def _get_cached(self, gene_name: str) -> Optional[np.ndarray]:
        """Retrieve embedding from SQLite cache."""
        if not self._db_initialized:
            return None

        try:
            conn = sqlite3.connect(str(self.cache_path))
            cursor = conn.cursor()

            cursor.execute(
                "SELECT embedding, model FROM bio_embeddings WHERE gene_name = ?",
                (gene_name,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                embedding_bytes, model = row
                # Only use cache if same model
                if model == self.model_name:
                    return np.frombuffer(embedding_bytes, dtype=np.float32)

        except Exception as e:
            print(f"[BiologicalEmbeddings] Cache read error: {e}")

        return None

    def _set_cached(self, gene_name: str, embedding: np.ndarray, sequence: str):
        """Store embedding in SQLite cache."""
        if not self._db_initialized:
            return

        try:
            conn = sqlite3.connect(str(self.cache_path))
            cursor = conn.cursor()

            embedding_bytes = embedding.astype(np.float32).tobytes()

            cursor.execute("""
                INSERT OR REPLACE INTO bio_embeddings
                (gene_name, embedding, model, sequence, sequence_length)
                VALUES (?, ?, ?, ?, ?)
            """, (
                gene_name,
                embedding_bytes,
                self.model_name,
                sequence,
                len(sequence)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"[BiologicalEmbeddings] Cache write error: {e}")

    def embed(self, gene_name: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate ESM-2 embedding for a protein.

        Args:
            gene_name: Gene symbol (e.g., "TP53")
            use_cache: Whether to use cache

        Returns:
            1280-dimensional embedding vector
        """
        # Check memory cache
        if use_cache and gene_name in self._memory_cache:
            return self._memory_cache[gene_name]

        # Check SQLite cache
        if use_cache:
            cached = self._get_cached(gene_name)
            if cached is not None:
                self._memory_cache[gene_name] = cached
                return cached

        # Get sequence
        if gene_name not in self._sequences:
            raise ValueError(f"No sequence found for {gene_name}")

        sequence = self._sequences[gene_name]

        # Generate embedding
        if self._model is None:
            raise RuntimeError("ESM-2 model not loaded")

        try:
            # Prepare batch (single sequence)
            data = [(gene_name, sequence)]
            _, _, batch_tokens = self._batch_converter(data)
            batch_tokens = batch_tokens.to(self.device)

            # Forward pass
            with torch.no_grad():
                results = self._model(
                    batch_tokens,
                    repr_layers=[self._model.num_layers]  # Get final layer
                )

            # Extract embeddings
            # Shape: (batch, seq_len, embed_dim)
            token_embeddings = results["representations"][self._model.num_layers]

            # Mean pooling (exclude special tokens: BOS at index 0, EOS at end)
            # This is standard practice for ESM embeddings
            embedding = token_embeddings[0, 1:-1, :].mean(dim=0)  # (embed_dim,)

            # Convert to numpy
            embedding = embedding.cpu().numpy().astype(np.float32)

            # Cache
            self._memory_cache[gene_name] = embedding
            if use_cache:
                self._set_cached(gene_name, embedding, sequence)

            return embedding

        except Exception as e:
            print(f"[BiologicalEmbeddings] Error embedding {gene_name}: {e}")
            raise

    def similarity(self, gene1: str, gene2: str) -> float:
        """
        Cosine similarity between two proteins.

        Args:
            gene1: First gene symbol
            gene2: Second gene symbol

        Returns:
            Similarity score (0-1, higher is more similar)
        """
        # Check if both are proteins (have sequences)
        if gene1 not in self._sequences or gene2 not in self._sequences:
            # Not a protein - return neutral similarity
            # (This happens when coherence checker compares relations like "activates")
            return 0.5

        v1 = self.embed(gene1)
        v2 = self.embed(gene2)

        # Cosine similarity
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 > 0 and norm2 > 0:
            return float(dot_product / (norm1 * norm2))
        return 0.0

    def embed_batch(self, gene_names: List[str], use_cache: bool = True) -> List[np.ndarray]:
        """
        Embed multiple proteins (uses caching, not true batching yet).

        Args:
            gene_names: List of gene symbols
            use_cache: Whether to use cache

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for gene_name in gene_names:
            embeddings.append(self.embed(gene_name, use_cache=use_cache))
        return embeddings

    @property
    def dimension(self) -> int:
        """Embedding dimension (1280 for ESM-2 650M)."""
        return self._dimension

    @property
    def is_available(self) -> bool:
        """Whether model is loaded and ready."""
        return self._model is not None and len(self._sequences) > 0

    @property
    def model(self):
        """Access to underlying ESM model (for advanced use)."""
        return self._model

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        stats = {
            "memory_cache": len(self._memory_cache),
            "sqlite_cache": 0
        }

        if self._db_initialized:
            try:
                conn = sqlite3.connect(str(self.cache_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM bio_embeddings")
                stats["sqlite_cache"] = cursor.fetchone()[0]
                conn.close()
            except:
                pass

        return stats

    def clear_memory_cache(self):
        """Clear in-memory cache."""
        self._memory_cache.clear()

    def clear_all_cache(self):
        """Clear both memory and SQLite cache."""
        self.clear_memory_cache()

        if self.cache_path.exists():
            self.cache_path.unlink()
            self._db_initialized = False
            self._init_cache_db()


# Factory function for compatibility
def create_biological_engine(model_name: str = DEFAULT_MODEL, device: str = 'cpu') -> BiologicalEmbeddingsEngine:
    """
    Create a biological embeddings engine.

    Args:
        model_name: ESM model name
        device: 'cpu' or 'cuda'

    Returns:
        BiologicalEmbeddingsEngine instance
    """
    return BiologicalEmbeddingsEngine(model_name=model_name, device=device)


if __name__ == "__main__":
    # Test code
    print("Testing BiologicalEmbeddingsEngine...")
    print()

    engine = BiologicalEmbeddingsEngine(device='cpu')

    if not engine.is_available:
        print("ERROR: Engine not available")
        print("Make sure:")
        print("  1. fair-esm is installed: pip install fair-esm")
        print("  2. Sequences downloaded: python scripts/download_uniprot_sequences.py")
        exit(1)

    print("Engine initialized successfully!")
    print()

    # Test single embedding
    print("Testing single protein (TP53)...")
    emb = engine.embed("TP53")
    print(f"  Embedding shape: {emb.shape}")
    print(f"  First 5 values: {emb[:5]}")
    print()

    # Test similarity (RAS family should be similar)
    print("Testing similarity (RAS family)...")
    sim_ras = engine.similarity("KRAS", "NRAS")
    sim_unrelated = engine.similarity("TP53", "KRAS")
    print(f"  KRAS vs NRAS (RAS family): {sim_ras:.3f}")
    print(f"  TP53 vs KRAS (unrelated):  {sim_unrelated:.3f}")
    print()

    if sim_ras > sim_unrelated:
        print("SUCCESS: RAS family members are more similar (as expected)")
    else:
        print("WARNING: Unexpected similarity scores")

    # Cache stats
    print()
    stats = engine.get_cache_stats()
    print(f"Cache stats: {stats}")
