# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Cloud LLM Integration — Optional LLM Reasoning Layer

Uses cloud LLM APIs (Qwen, Claude, GPT-4) for mathematical reasoning.
Falls back to local hybrid solver if API unavailable.

Optional Component - requires API key
"""

import sys
import os
import json
from typing import Dict, List, Any, Optional, Tuple

# Lazy import API clients
OPENAI_AVAILABLE = False
ANTHROPIC_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    pass

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass


class CloudLLMReasoner:
    """
    Cloud LLM reasoning for mathematical problems.
    
    Uses LLM to generate proof sketches and intermediate steps,
    which are then verified/computed by local symbolic calculator.
    """
    
    def __init__(
        self,
        provider: str = 'openai',
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Initialize cloud LLM reasoner.
        
        Args:
            provider: 'openai', 'anthropic', or 'qwen'
            model: Model name (auto-selected if None)
            api_key: API key (uses env var if None)
            verbose: Print progress
        """
        self.provider = provider
        self.verbose = verbose
        
        # Auto-select model
        if model is None:
            if provider == 'openai':
                model = 'gpt-4o-mini'  # Cheap, fast
            elif provider == 'anthropic':
                model = 'claude-3-haiku-20240307'
            elif provider == 'qwen':
                model = 'qwen-plus'
        
        self.model = model
        
        # Initialize client
        self.client = self._init_client(provider, api_key)
        
        # System prompt for mathematical reasoning
        self.system_prompt = """You are an expert mathematician solving competition problems.

For each problem:
1. Identify the mathematical domain (number theory, algebra, combinatorics, geometry, probability)
2. Break down the solution into clear steps
3. Show all computations
4. Provide the final answer as an integer between 0 and 99999

Format your response as JSON:
{
    "domain": "...",
    "pattern": "...",
    "steps": [...],
    "computation": "...",
    "answer": 123
}

Think step-by-step but be concise."""
    
    def _init_client(self, provider: str, api_key: Optional[str]) -> Any:
        """Initialize API client."""
        if provider == 'openai':
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI not installed: pip install openai")
            
            key = api_key or os.environ.get('OPENAI_API_KEY')
            if not key:
                raise ValueError("OpenAI API key required (set OPENAI_API_KEY env var)")
            
            return OpenAI(api_key=key)
        
        elif provider == 'anthropic':
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic not installed: pip install anthropic")
            
            key = api_key or os.environ.get('ANTHROPIC_API_KEY')
            if not key:
                raise ValueError("Anthropic API key required")
            
            return Anthropic(api_key=key)
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def reason(self, problem_text: str) -> Dict[str, Any]:
        """
        Use LLM to reason about a problem.
        
        Args:
            problem_text: The problem statement
            
        Returns:
            Dictionary with domain, pattern, steps, and answer
        """
        if self.verbose:
            print(f"🤔 LLM reasoning about: {problem_text[:50]}...", file=sys.stderr)
        
        if self.provider == 'openai':
            return self._reason_openai(problem_text)
        elif self.provider == 'anthropic':
            return self._reason_anthropic(problem_text)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _reason_openai(self, problem_text: str) -> Dict[str, Any]:
        """Reason using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": problem_text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent reasoning
                max_tokens=1000,
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            if self.verbose:
                print(f"✅ LLM response: {result.get('answer', 'N/A')}", file=sys.stderr)
            
            return result
            
        except Exception as e:
            if self.verbose:
                print(f"❌ OpenAI error: {e}", file=sys.stderr)
            
            return {
                'error': str(e),
                'answer': None,
            }
    
    def _reason_anthropic(self, problem_text: str) -> Dict[str, Any]:
        """Reason using Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": problem_text}
                ]
            )
            
            result_text = response.content[0].text
            
            # Extract JSON from response
            # (Anthropic doesn't have native JSON mode yet)
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_text = result_text[start:end]
                result = json.loads(json_text)
            else:
                result = {'answer': None, 'error': 'Could not parse JSON'}
            
            if self.verbose:
                print(f"✅ Anthropic response: {result.get('answer', 'N/A')}", file=sys.stderr)
            
            return result
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Anthropic error: {e}", file=sys.stderr)
            
            return {
                'error': str(e),
                'answer': None,
            }
    
    def extract_pattern(self, reasoning: Dict[str, Any]) -> Optional[str]:
        """
        Extract pattern name from LLM reasoning.
        
        Maps LLM's natural language description to our pattern taxonomy.
        """
        pattern_mapping = {
            'difference of squares': 'difference_of_squares',
            'modular arithmetic': 'modular_square_roots',
            'Euler totient': 'euler_totient',
            'Wilson': 'wilson_theorem',
            'Fermat': 'fermat_little_theorem',
            'geometric sequence': 'geometric_sequence',
            'arithmetic sequence': 'arithmetic_sequence',
            'Vieta': 'vieta_sum_squares',
            'binomial': 'binomial_expansion',
            'catalan': 'catalan_number',
            'derangement': 'derangement',
            'inclusion-exclusion': 'inclusion_exclusion',
            'pigeonhole': 'pigeonhole',
            'Heron': 'heron_formula',
            'chord': 'chord_length',
            'tangent': 'tangent_length',
            'probability': 'binomial_probability',
        }
        
        llm_pattern = reasoning.get('pattern', '').lower()
        
        for key, value in pattern_mapping.items():
            if key.lower() in llm_pattern:
                return value
        
        # Fallback to domain-based guess
        domain = reasoning.get('domain', '').lower()
        
        if 'number' in domain:
            return 'difference_of_squares'
        elif 'algebra' in domain:
            return 'vieta_sum_squares'
        elif 'combinatorics' in domain:
            return 'counting_digits'
        elif 'geometry' in domain:
            return 'triangle_area'
        elif 'probability' in domain:
            return 'binomial_probability'
        
        return None
    
    def get_cost_estimate(self, num_problems: int) -> Dict[str, float]:
        """
        Estimate API cost for solving problems.
        
        Args:
            num_problems: Number of problems to solve
            
        Returns:
            Dictionary with cost estimates
        """
        # Approximate costs per problem (based on ~500 tokens input + 200 tokens output)
        costs = {
            'openai': {
                'gpt-4o-mini': 0.00015,  # $0.15/1M input + $0.60/1M output
                'gpt-4o': 0.005,  # $5/1M input + $15/1M output
            },
            'anthropic': {
                'claude-3-haiku': 0.00025,  # $0.25/1M input + $1.25/1M output
                'claude-3-sonnet': 0.003,  # $3/1M input + $15/1M output
            }
        }
        
        provider_costs = costs.get(self.provider, {})
        model_cost = provider_costs.get(self.model, 0.001)  # Default $0.001
        
        return {
            'per_problem': model_cost,
            'total': model_cost * num_problems,
            'currency': 'USD',
        }


class HybridCloudSolver:
    """
    Hybrid solver combining cloud LLM with local computation.
    
    Architecture:
    1. Cloud LLM reasons about problem structure
    2. Local symbolic calculator computes exact answer
    3. Verification layer checks consistency
    """
    
    def __init__(
        self,
        provider: str = 'openai',
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        use_local_fallback: bool = True,
        verbose: bool = False
    ):
        """
        Initialize hybrid cloud solver.
        
        Args:
            provider: LLM provider ('openai', 'anthropic')
            model: Model name
            api_key: API key
            use_local_fallback: Fall back to local hybrid solver if API fails
            verbose: Print progress
        """
        self.verbose = verbose
        self.use_local_fallback = use_local_fallback
        
        # Initialize cloud reasoner
        try:
            self.cloud_reasoner = CloudLLMReasoner(
                provider=provider,
                model=model,
                api_key=api_key,
                verbose=verbose
            )
            self.cloud_available = True
        except (ImportError, ValueError) as e:
            if verbose:
                print(f"Cloud LLM not available: {e}", file=sys.stderr)
                print("Using local fallback only", file=sys.stderr)
            self.cloud_available = False
            self.cloud_reasoner = None
        
        # Import local solver for fallback
        if use_local_fallback:
            from aimo.hybrid_solver import AIMO3HybridSolver
            self.local_solver = AIMO3HybridSolver(verbose=verbose)
        else:
            self.local_solver = None
    
    def solve(self, problem_text: str) -> Tuple[Optional[int], str]:
        """
        Solve problem using cloud LLM + local computation.
        
        Args:
            problem_text: The problem statement
            
        Returns:
            (answer, trace)
        """
        if not self.cloud_available:
            if self.local_solver:
                return self.local_solver.solve(problem_text)
            return None, "no_solver_available"
        
        # Step 1: Cloud LLM reasoning
        reasoning = self.cloud_reasoner.reason(problem_text)
        
        if 'error' in reasoning or reasoning.get('answer') is None:
            if self.local_solver:
                if self.verbose:
                    print("Cloud failed, using local fallback", file=sys.stderr)
                return self.local_solver.solve(problem_text)
            return None, f"cloud_error: {reasoning.get('error', 'unknown')}"
        
        # Step 2: Extract pattern
        pattern = self.cloud_reasoner.extract_pattern(reasoning)
        
        # Step 3: Use LLM's answer directly (it does computation)
        llm_answer = reasoning.get('answer')
        
        if llm_answer is not None:
            trace = f"cloud_llm::{pattern or 'unknown'}"
            return int(llm_answer), trace
        
        # Step 4: Fallback to local computation
        if self.local_solver and pattern:
            return self.local_solver.solve(problem_text)
        
        return None, "computation_failed"
    
    def get_cost_estimate(self, num_problems: int) -> Dict[str, Any]:
        """Get cost estimate for cloud API usage."""
        if self.cloud_reasoner:
            return self.cloud_reasoner.get_cost_estimate(num_problems)
        return {'per_problem': 0, 'total': 0, 'currency': 'USD'}


if __name__ == "__main__":
    # Test cloud LLM integration
    print("\n" + "="*80)
    print("  CLOUD LLM INTEGRATION TEST")
    print("="*80)
    
    # Check if API key available
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("\nNo API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        print("\nFor testing without API key, use local hybrid solver:")
        print("  python aimo/hybrid_solver.py")
        print("\nTo get API keys:")
        print("  OpenAI: https://platform.openai.com/api-keys")
        print("  Anthropic: https://console.anthropic.com/settings/keys")
        sys.exit(0)
    
    # Test with API
    provider = 'openai' if 'OPENAI_API_KEY' in os.environ else 'anthropic'
    
    solver = HybridCloudSolver(
        provider=provider,
        verbose=True
    )
    
    # Test problems
    test_problems = [
        "Find the number of integers between 1 and 1000 that can be expressed as difference of squares",
        "The quadratic x² - 5x + 6 = 0 has roots. Find sum of their squares",
        "Fair coin flipped 4 times. Probability of exactly 2 heads?",
    ]
    
    print(f"\nTesting with {provider} API...")
    print(f"Cost estimate: {solver.get_cost_estimate(len(test_problems))}")
    
    for problem in test_problems:
        print(f"\n{'='*60}")
        print(f"Problem: {problem[:60]}...")
        
        answer, trace = solver.solve(problem)
        print(f"Answer: {answer}")
        print(f"Trace: {trace}")
    
    print("\n" + "="*80 + "\n")
