"""
Neural RAG Retriever — Embedding-based Semantic Search

Replaces keyword matching with sentence transformer embeddings
for retrieving relevant theorems from LeanDojo corpus.

Phase 1A of Hybrid Learning System
"""

import sys
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Lazy import sentence_transformers
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Using fallback.", file=sys.stderr)
    print("Install: pip install sentence-transformers scikit-learn", file=sys.stderr)


class NeuralRAGRetriever:
    """
    Embedding-based retriever for mathematical theorems.
    
    Uses sentence transformers to encode problems and theorems,
    then retrieves via cosine similarity.
    
    Advantages over keyword matching:
    - Semantic understanding (e.g., "triangle" ↔ "polygon with 3 sides")
    - Handles paraphrasing
    - Cross-domain connections (e.g., algebra ↔ geometry)
    """
    
    def __init__(
        self,
        corpus_path: str,
        model_name: str = 'all-MiniLM-L6-v2',
        verbose: bool = False
    ):
        """
        Initialize neural RAG retriever.
        
        Args:
            corpus_path: Path to LeanDojo corpus.jsonl
            model_name: SentenceTransformer model to use
            verbose: Print progress messages
        """
        self.corpus_path = corpus_path
        self.model_name = model_name
        self.verbose = verbose
        
        self.theorems = []
        self.embeddings = None
        self.model = None
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load sentence transformer model."""
        if self.verbose:
            print(f"Loading SentenceTransformer: {self.model_name}", file=sys.stderr)
        
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Warning: Could not load model: {e}", file=sys.stderr)
            print("Falling back to keyword retrieval", file=sys.stderr)
            self.model = None
    
    def load_corpus(self, max_theorems: int = 100000):
        """
        Load and embed LeanDojo corpus.
        
        Args:
            max_theorems: Maximum number of theorems to load
        """
        if self.verbose:
            print(f"Loading LeanDojo corpus from {self.corpus_path}...", file=sys.stderr)
        
        theorems_data = []
        
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            for line in f:
                if len(theorems_data) >= max_theorems:
                    break
                
                try:
                    data = json.loads(line)
                    file_path = data.get('path', '')
                    premises = data.get('premises', [])
                    
                    for p in premises:
                        if not isinstance(p, dict):
                            continue
                        
                        name = p.get('full_name', '')
                        code = p.get('code', '')
                        
                        # Filter for Mathlib
                        if 'Mathlib' not in file_path:
                            continue
                        
                        # Create searchable text
                        text = f"{name}: {code}"
                        field = self._extract_field(file_path)
                        
                        theorems_data.append({
                            'name': name,
                            'file': file_path,
                            'field': field,
                            'text': text,
                            'code': code,
                        })
                
                except (json.JSONDecodeError, KeyError):
                    continue
        
        self.theorems = theorems_data
        
        if self.verbose:
            print(f"Loaded {len(self.theorems)} theorems", file=sys.stderr)
        
        # Compute embeddings
        self._compute_embeddings()
    
    def _extract_field(self, file_path: str) -> str:
        """Extract mathematical field from file path."""
        path_lower = file_path.lower()
        
        if 'number' in path_lower or 'arith' in path_lower or 'nat' in path_lower:
            return 'number_theory'
        if 'algebra' in path_lower or 'group' in path_lower or 'ring' in path_lower:
            return 'algebra'
        if 'topology' in path_lower:
            return 'topology'
        if 'analysis' in path_lower:
            return 'analysis'
        if 'combinat' in path_lower or 'finset' in path_lower:
            return 'combinatorics'
        if 'probab' in path_lower:
            return 'probability'
        if 'geometry' in path_lower or 'metric' in path_lower:
            return 'geometry'
        
        return 'other'
    
    def _compute_embeddings(self):
        """Compute embeddings for all theorems."""
        if not self.model or not self.theorems:
            return
        
        if self.verbose:
            print(f"Computing embeddings for {len(self.theorems)} theorems...", file=sys.stderr)
        
        texts = [t['text'] for t in self.theorems]
        
        # Batch encode
        self.embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=self.verbose,
            convert_to_numpy=True
        )
        
        if self.verbose:
            print(f"Embeddings shape: {self.embeddings.shape}", file=sys.stderr)
    
    def retrieve(
        self,
        problem_text: str,
        top_k: int = 5,
        field_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve theorems most similar to problem.
        
        Args:
            problem_text: The problem statement
            top_k: Number of theorems to retrieve
            field_filter: Optional field to filter by
            
        Returns:
            List of theorems with similarity scores
        """
        if not self.model or self.embeddings is None:
            # Fallback to keyword retrieval
            return self._keyword_retrieve(problem_text, top_k)
        
        # Encode problem
        problem_emb = self.model.encode([problem_text], convert_to_numpy=True)[0]
        
        # Compute similarities
        similarities = cosine_similarity([problem_emb], self.embeddings)[0]
        
        # Apply field filter if specified
        if field_filter:
            for i, thm in enumerate(self.theorems):
                if thm['field'] != field_filter:
                    similarities[i] = -1  # Exclude
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Build results
        results = []
        for idx in top_indices:
            if similarities[idx] < 0:
                continue
            
            result = self.theorems[idx].copy()
            result['similarity'] = float(similarities[idx])
            results.append(result)
        
        return results
    
    def _keyword_retrieve(
        self,
        problem_text: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Fallback keyword-based retrieval."""
        problem_lower = problem_text.lower()
        words = set(problem_lower.split())
        
        scored = []
        for thm in self.theorems:
            score = 0
            thm_text_lower = thm['text'].lower()
            
            # Count word overlaps
            for word in words:
                if len(word) > 3 and word in thm_text_lower:
                    score += 1
            
            scored.append((thm, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [
            {**thm, 'similarity': score / max(1, len(words))}
            for thm, score in scored[:top_k]
        ]
    
    def retrieve_with_chaining(
        self,
        problem_text: str,
        top_k: int = 5,
        chain_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Retrieve theorems with chaining support.
        
        Finds theorems that are semantically connected,
        not just individually similar.
        
        Args:
            problem_text: The problem statement
            top_k: Number of theorems to return
            chain_depth: How many hops to consider
            
        Returns:
            Chain of connected theorems
        """
        # First, get candidate theorems
        candidates = self.retrieve(problem_text, top_k=top_k * 2)
        
        if len(candidates) <= 1:
            return candidates
        
        # Build local similarity graph
        n = len(candidates)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                # Compute embedding similarity between theorems
                if self.model and self.embeddings is not None:
                    idx_i = self.theorems.index(candidates[i])
                    idx_j = self.theorems.index(candidates[j])
                    sim = cosine_similarity(
                        [self.embeddings[idx_i]],
                        [self.embeddings[idx_j]]
                    )[0][0]
                    similarity_matrix[i, j] = sim
                    similarity_matrix[j, i] = sim
        
        # Greedy chain: start with most similar, add connected
        chain = [candidates[0]]
        used = {0}
        
        while len(chain) < top_k and len(used) < n:
            best_next = None
            best_score = -1
            
            for i in range(n):
                if i in used:
                    continue
                
                # Score by connection to current chain
                score = 0
                for used_idx, used_thm in enumerate(chain):
                    if used_idx < n:
                        score += similarity_matrix[used_idx, i]
                    # Bonus for same field
                    if candidates[i]['field'] == used_thm['field']:
                        score += 0.5
                
                if score > best_score:
                    best_score = score
                    best_next = i
            
            if best_next is not None:
                chain.append(candidates[best_next])
                used.add(best_next)
            else:
                break
        
        if self.verbose and len(chain) > 1:
            print(f"  🔗 Neural chain: {len(chain)} theorems", file=sys.stderr)
        
        return chain
    
    def save_embeddings(self, output_path: str):
        """Save embeddings to disk for faster loading."""
        if self.embeddings is None:
            raise ValueError("No embeddings to save. Load corpus first.")
        
        np.save(output_path, self.embeddings)
        
        # Save metadata
        metadata = {
            'theorems': self.theorems,
            'model_name': self.model_name,
        }
        
        with open(output_path.replace('.npy', '.json'), 'w') as f:
            json.dump(metadata, f)
        
        if self.verbose:
            print(f"Saved embeddings to {output_path}", file=sys.stderr)
    
    def load_embeddings(self, embeddings_path: str):
        """Load pre-computed embeddings from disk."""
        self.embeddings = np.load(embeddings_path)
        
        metadata_path = embeddings_path.replace('.npy', '.json')
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.theorems = metadata['theorems']
        self.model_name = metadata.get('model_name', self.model_name)
        
        if self.verbose:
            print(f"Loaded embeddings from {embeddings_path}", file=sys.stderr)
            print(f"Shape: {self.embeddings.shape}", file=sys.stderr)


# Convenience function
def create_neural_retriever(
    corpus_path: str,
    embeddings_cache: Optional[str] = None,
    verbose: bool = False
) -> NeuralRAGRetriever:
    """
    Create neural retriever with optional embedding cache.
    
    Args:
        corpus_path: Path to LeanDojo corpus
        embeddings_cache: Optional path to save/load embeddings
        verbose: Print progress
        
    Returns:
        NeuralRAGRetriever instance
    """
    retriever = NeuralRAGRetriever(corpus_path, verbose=verbose)
    
    if embeddings_cache and Path(embeddings_cache).exists():
        retriever.load_embeddings(embeddings_cache)
    else:
        retriever.load_corpus()
        
        if embeddings_cache:
            retriever.save_embeddings(embeddings_cache)
    
    return retriever


if __name__ == "__main__":
    # Test neural RAG retriever
    print("\n" + "="*80)
    print("  NEURAL RAG RETRIEVER TEST")
    print("="*80)
    
    corpus_path = "data_sources/leandojo/leandojo_benchmark_4/corpus.jsonl"
    
    if not Path(corpus_path).exists():
        print(f"Corpus not found: {corpus_path}")
        print("Skipping test. Run: dir data_sources\\leandojo\\leandojo_benchmark_4\\corpus.jsonl")
        sys.exit(0)
    
    retriever = create_neural_retriever(
        corpus_path,
        embeddings_cache="aimo/neural_rag_cache.npy",
        verbose=True
    )
    
    # Test queries
    test_queries = [
        "Find the number of integers between 1 and 1000 that can be expressed as difference of squares",
        "Find the remainder when n squared is divided by 1000",
        "Find the area of a triangle with base 12 and height 8",
    ]
    
    print("\n" + "="*80)
    print("  RETRIEVAL TESTS")
    print("="*80)
    
    for query in test_queries:
        print(f"\nQuery: {query[:60]}...")
        
        results = retriever.retrieve(query, top_k=3)
        
        print(f"Top {len(results)} results:")
        for i, thm in enumerate(results[:3], 1):
            print(f"  {i}. {thm['name']} (similarity: {thm['similarity']:.3f}, field: {thm['field']})")
    
    print("\n" + "="*80 + "\n")
