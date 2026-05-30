"""MOF linker generator validation benchmark.

See docs/MOF_LINKER_BENCHMARK_SPEC.md for the design. This package builds a
deduped corpus of real synthesized linkers (MOFSimplify + CoRE-MOF), freezes a
refcode-level seed/eval split, constructs decoys, runs the grounded funnel, and
reports recall / AUROC / the 22-atom claim.
"""
