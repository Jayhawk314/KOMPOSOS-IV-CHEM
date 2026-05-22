"""
AnswerExtractor — Extract integer answers from verified proof chains.

Uses sympy to parse mathematical expressions and resolve to integers
in the range [0, 99999] as required by AIMO3.
"""

import sys
import re
from typing import Optional, Any, Dict, List

# Guard imports
try:
    import sympy as sp
    from sympy.parsing.latex import parse_latex
except ImportError:
    print("Warning: sympy not available, using fallback parsing", file=sys.stderr)
    sp = None
    parse_latex = None


class AnswerExtractor:
    """
    Extractor that resolves verified proofs to integer answers.
    
    Tries multiple strategies in order:
    1. Find "answer" type node
    2. Parse LaTeX with sympy
    3. Search for "= N" patterns
    4. Extract any integer
    5. Fallback to 0
    """
    
    def extract(
        self,
        cat: Any,  # Category
        verified_chain: Dict[str, Any],
        problem_text: str
    ) -> Optional[int]:
        """
        Extract integer answer from a verified proof chain.
        
        Args:
            cat: Category containing the proof
            verified_chain: Output from DualVerifier.verify_chain()
            problem_text: Original problem statement
            
        Returns:
            Integer in [0, 99999] or None if extraction fails
        """
        # Strategy 1: Find the "answer" type node
        answer_node = self._find_answer_node(cat)
        
        if answer_node:
            claim = answer_node.metadata.get("claim", "")
            result = self._parse_claim(claim)
            if result is not None:
                return self._clamp(result)
        
        # Strategy 2: Search all nodes in verified chain
        step_verdicts = verified_chain.get("step_verdicts", [])
        
        for step_info in reversed(step_verdicts):
            step_id = step_info.get("step", "")
            
            for obj in cat.objects():
                if obj.name == step_id:
                    claim = obj.metadata.get("claim", "")
                    result = self._parse_claim(claim)
                    if result is not None:
                        return self._clamp(result)
        
        # Strategy 3: Search problem text for modular arithmetic
        result = self._resolve_modular(problem_text)
        if result is not None:
            return self._clamp(result)
        
        # Strategy 4: Fallback regex
        result = self.fallback_parse(problem_text)
        if result is not None:
            return self._clamp(result)
        
        return None
    
    def _find_answer_node(self, cat: Any) -> Optional[Any]:
        """Find the node marked as 'answer' type."""
        for obj in cat.objects():
            if obj.type_name == "answer":
                return obj
        
        # Fallback: look for "answer" in claim
        for obj in cat.objects():
            claim = obj.metadata.get("claim", "").lower()
            if "answer" in claim:
                return obj
        
        return None
    
    def _parse_claim(self, claim: str) -> Optional[int]:
        """
        Parse a claim to extract an integer.
        
        Tries:
        1. LaTeX parsing with sympy
        2. Pattern matching for "= N"
        3. Direct integer extraction
        """
        if not claim:
            return None
        
        # Try LaTeX parsing
        if sp and parse_latex:
            try:
                # Look for LaTeX expressions
                latex_matches = re.findall(r'\$([^$]+)\$', claim)
                for latex in latex_matches:
                    try:
                        expr = parse_latex(latex)
                        result = sp.N(expr)
                        if result.is_number and result.is_integer:
                            return int(result)
                    except Exception:
                        pass
            except Exception:
                pass
        
        # Try pattern matching
        patterns = [
            r'answer\s*(?:is|=)\s*(\d+)',
            r'=\s*(\d+)',
            r'≡\s*(\d+)',
            r'(\d+)\s*\(\s*mod\s*\d+\s*\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, claim, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        
        # Try sympy evaluation of any expression
        if sp:
            try:
                # Look for mathematical expressions
                expr_match = re.search(r'([^=]+)=\s*(\d+)', claim)
                if expr_match:
                    expr_str = expr_match.group(1).strip()
                    try:
                        expr = sp.sympify(expr_str)
                        result = sp.N(expr)
                        if result.is_number:
                            return int(result)
                    except Exception:
                        pass
            except Exception:
                pass
        
        return None
    
    def _clamp(self, value: int) -> int:
        """Clamp value to [0, 99999] range."""
        return value % 100000
    
    def resolve_modular(self, expr: str, modulus: int = 1000) -> Optional[int]:
        """
        Parse and evaluate modular expressions.
        
        Example: "Find X mod 1000" → evaluates X, returns X % 1000
        """
        if not sp:
            return None
        
        # Look for "mod" expressions
        mod_match = re.search(r'(\d+)\s*mod\s*(\d+)', expr, re.IGNORECASE)
        if mod_match:
            try:
                value = int(mod_match.group(1))
                mod = int(mod_match.group(2))
                return value % mod
            except ValueError:
                pass
        
        # Look for "≡" (congruence)
        cong_match = re.search(r'(\d+)\s*≡\s*(\d+)\s*\(mod\s*(\d+)\)', expr)
        if cong_match:
            try:
                a = int(cong_match.group(1))
                b = int(cong_match.group(2))
                m = int(cong_match.group(3))
                # Return the canonical representative
                return a % m
            except ValueError:
                pass
        
        return None
    
    def fallback_parse(self, text: str) -> Optional[int]:
        """
        Last resort: regex scan for any integer.
        
        Returns the last integer found in the text.
        """
        # Look for all integers up to 5 digits
        matches = re.findall(r'\b(\d{1,5})\b', text)
        
        if matches:
            try:
                # Return the last integer found
                val = int(matches[-1])
                return val % 100000
            except ValueError:
                pass
        
        return None
