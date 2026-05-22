
#!/usr/bin/env python3
"""
Domain Plugin Interface

Any domain can implement this interface to match against the math kernel.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class StructureMatch:
    """Result of matching a domain against mathematical structure."""
    def __init__(self, 
                 math_structure: str,
                 domain_analog: str,
                 match_confidence: float,
                 predictions: List[str] = None,
                 gaps: List[str] = None):
        self.math_structure = math_structure    # Which theorem/region in math
        self.domain_analog = domain_analog       # What it corresponds to in domain
        self.match_confidence = match_confidence # D-S score [0, 1]
        self.predictions = predictions or []     # What math predicts should exist
        self.gaps = gaps or []                   # What's in math but missing in domain

class DomainPlugin(ABC):
    """
    Implement this to plug a domain into the Math Kernel.
    
    The kernel will find which mathematical structures govern your domain.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Return domain name (e.g., 'physics', 'climate', 'finance')."""
        pass
    
    @abstractmethod
    def get_objects(self) -> List[Dict[str, Any]]:
        """
        Return domain objects.
        
        Each object should have:
        - id: unique identifier
        - type: object type
        - properties: dict of attributes
        """
        pass
    
    @abstractmethod
    def get_morphisms(self) -> List[Dict[str, str]]:
        """
        Return domain relationships.
        
        Each morphism should have:
        - source: source object ID
        - target: target object ID  
        - type: relationship type
        """
        pass
    
    def match_against_kernel(self, kernel) -> List[StructureMatch]:
        """
        Find mathematical structures that match this domain.
        
        Default implementation uses topological signature matching.
        Override for custom matching logic.
        """
        from domains.mathematics.structure_match import StructureMatcher
        matcher = StructureMatcher(kernel)
        return matcher.find_matches(self, top_k=5)

# Example: Physics Plugin
class PhysicsPlugin(DomainPlugin):
    """Example: Physics domain plugin."""
    
    def __init__(self, physics_data_path: str):
        self.data_path = physics_data_path
        self._objects = []
        self._morphisms = []
        # Load physics laws, equations, experimental data...
    
    def get_name(self) -> str:
        return "physics"
    
    def get_objects(self):
        return self._objects
    
    def get_morphisms(self):
        return self._morphisms

# Example: Climate Plugin  
class ClimatePlugin(DomainPlugin):
    """Example: Climate domain plugin."""
    
    def __init__(self, climate_data_path: str):
        self.data_path = climate_data_path
        self._objects = []  # temperature records, pressure systems, etc.
        self._morphisms = []  # causal relationships, correlations
    
    def get_name(self) -> str:
        return "climate"
    
    def get_objects(self):
        return self._objects
    
    def get_morphisms(self):
        return self._morphisms

# Usage:
# kernel = MathKernel()
# physics = PhysicsPlugin("data/physics")
# matches = physics.match_against_kernel(kernel)
# 
# for match in matches:
#     print(f"Physics {match.domain_analog} matches {match.math_structure}")
#     print(f"  Confidence: {match.match_confidence}")
#     print(f"  Predictions: {match.predictions}")
