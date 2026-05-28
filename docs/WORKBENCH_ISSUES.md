# Autonomous Discovery Workbench Issues

## Overview
The Autonomous Discovery Workbench is a central feature in KOMPOSOS-IV-CHEM designed to unify the 8 primary material discovery capabilities into a single pipeline. It orchestrates the process from inverse design and candidate generation through screening, verification, and synthesis planning.

## Resolved Issues
1. **AttributeError: 'CompositionDesigner' object has no attribute 'search'**
   - **File:** discovery/workbench_service.py
   - **Root Cause:** The CompositionDesigner class (in composition_engine/designer.py) defines its main entry point as design(spec), but workbench_service.py was trying to call an older or incorrect method name search(spec).
   - **Fix:** Renamed self._designer.search(spec) to self._designer.design(spec).

2. **TypeError: 'DesignResult' object is not iterable**
   - **File:** discovery/workbench_service.py
   - **Root Cause:** CompositionDesigner.design() returns a DesignResult dataclass object. The workbench service was trying to iterate directly over this object (or dr in design_results:), rather than its candidates list attribute.
   - **Fix:** Changed the iteration to or dr in design_results.candidates:.

## Open/Pending Issues
- If you find any further issues in the pipeline execution (e.g., related to screening, stability checks, or aimo3 solver integration), please log them here. The pipeline integrates multiple distinct services, and schema mismatches between what the pipeline expects and what the underlying components return are the most likely source of integration bugs.
