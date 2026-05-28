# Autonomous Discovery Workbench Pipelines

Currently, workbench_service.py implements a **Composition-First** discovery pipeline. As you noticed, it only integrates 4 of the 8 available KOMPOSOS-IV-CHEM features:
1. **Composition Engine** (Inverse Design)
2. **PFAS Compliance** (Safety Screening)
3. **Compatibility Oracle** (Interface Verification)
4. **Synthesis Planner** (Route generation)

To achieve a true "Autonomous Workbench," the system must support multiple pipeline paths depending on the material class you are designing. 

## Pipeline Path A: Solid-State Crystals (The Crystal Dreamer Path)
When you "dream a crystal", you need a pipeline that moves from pure stoichiometry into 3D space:
1. **Inverse Design** (CompositionDesigner): Find a candidate formula matching property targets (e.g., Li7La3Zr2O12).
2. **Crystal Dreamer** (CrystalGenerator): Take the 1D formula and generate stable 3D structures (lattices, spacegroups, .cif files).
3. **Property Verification** (ForwardPredictor): Score the 3D structure for stability and bandgap.
4. **Interface Compatibility** (Oracle): Check if the specific 3D crystal face matches the interface material (e.g., Li_metal).
5. **Synthesis Planning**: Determine the precursor heating steps required to yield that specific crystal phase.

## Pipeline Path B: MOF Design (The MOF Path)
Metal-Organic Frameworks cannot be designed using standard composition models because they are topological assemblies of nodes and linkers:
1. **MOF Designer** (MOFGenerator): Select a metal node (e.g., Zn4O) and an organic linker (e.g., BDC) to fit a target topology (e.g., pcu).
2. **Topology Verification** (AIMO3 / Math Solver): Use the reasoning engine to verify that the resulting pore size and topology mathematically satisfy the design constraints (e.g., gas storage volume).
3. **Safety Check** (PFAS Compliance): Ensure the chosen organic linkers do not contain fluorinated forever-chemicals.
4. **Synthesis Planning**: Plan the solvent-based synthesis route.

## Next Steps for the Workbench
The workbench_service.py should be refactored to support a pipeline_type argument in DiscoveryGoal (e.g., CRYSTAL, MOF, COMPOSITION). This would allow the orchestrator to dynamically swap out Stage 1 (Generation) and insert Stage 1.5 (3D Structure Generation) depending on the user's specific discovery goal.
