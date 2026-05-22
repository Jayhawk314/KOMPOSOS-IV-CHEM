# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2024-2026 James Ray Hawkins

"""
KOMPOSOS-III Data Layer
========================

Comprehensive data management for categorical structures with temporal evolution tracking.

This module provides:
- SQLite-based storage for objects, morphisms, paths, and equivalences
- Sentence Transformer embeddings for semantic similarity
- Bulk data ingestion from multiple sources (OpenAlex, PDFs, Wikidata, etc.)
- Temporal indexing for evolution tracking

Key Classes:
- KomposOSStore: SQLite store for categorical structures
- EmbeddingsEngine: Semantic embeddings using Sentence Transformers
- CorpusLoader: Unified loader for multiple data sources

The data layer enables KOMPOSOS-III's core use case:
"Phylogenetics of concepts" - tracing how ideas evolve over time
and when different evolutionary paths are structurally equivalent.

Usage:
    from data import create_store, EmbeddingsEngine, CorpusLoader

    # Create a store
    store = create_store("my_corpus.db")

    # Load data from corpus
    loader = CorpusLoader("path/to/corpus")
    loader.load_all(store)

    # Add embeddings
    engine = EmbeddingsEngine()
    embedder = StoreEmbedder(store, engine)
    embedder.embed_all_objects()

    # Query the store
    paths = store.find_paths("Newton", "Schrödinger")
"""

from .store import (
    # Data classes
    StoredObject,
    StoredMorphism,
    StoredPath,
    EquivalenceClass,
    HigherMorphism,
    # Store class
    KomposOSStore,
    # Factory functions
    create_store,
    create_memory_store,
)

from .embeddings import (
    # Data classes
    EmbeddingResult,
    # Engine classes
    EmbeddingsEngine,
    StoreEmbedder,
    # Factory functions
    create_engine,
    load_engine,
    # Constants
    DEFAULT_MODEL,
)

from .sources import (
    # Parsed data classes
    ParsedWork,
    ParsedConcept,
    ParsedEntity,
    # Loaders
    OpenAlexLoader,
    PDFLoader,
    WikidataLoader,
    CustomDataLoader,
    BibTeXLoader,
    CorpusLoader,
)

from .config import (
    KomposOSConfig,
    get_config,
    init_corpus,
    verify_corpus,
    load_from_env,
    CORPUS_STRUCTURE,
)

__all__ = [
    # Store
    "StoredObject",
    "StoredMorphism",
    "StoredPath",
    "EquivalenceClass",
    "HigherMorphism",
    "KomposOSStore",
    "create_store",
    "create_memory_store",
    # Embeddings
    "EmbeddingResult",
    "EmbeddingsEngine",
    "StoreEmbedder",
    "create_engine",
    "load_engine",
    "DEFAULT_MODEL",
    # Sources
    "ParsedWork",
    "ParsedConcept",
    "ParsedEntity",
    "OpenAlexLoader",
    "PDFLoader",
    "WikidataLoader",
    "CustomDataLoader",
    "BibTeXLoader",
    "CorpusLoader",
    # Config
    "KomposOSConfig",
    "get_config",
    "init_corpus",
    "verify_corpus",
    "load_from_env",
    "CORPUS_STRUCTURE",
]
