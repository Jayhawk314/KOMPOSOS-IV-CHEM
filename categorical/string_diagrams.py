# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
String Diagrams: Graphical Calculus for Monoidal Categories

String diagrams provide a planar graphical representation of morphisms
in monoidal categories. Wires represent objects, boxes represent morphisms.
Composition is horizontal juxtaposition, tensor is vertical stacking.

This module provides:
- Diagram: planar string diagram representation
- from_morphisms: build diagram from category morphisms
- evaluate: interpret diagram numerically
- to_ascii: ASCII art rendering
- simplify: equational rewriting on diagrams

Reference: Selinger, "A survey of graphical languages for monoidal categories" (2010)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.category import Category
from core.types import Object, Morphism


@dataclass
class Wire:
    """A wire in a string diagram (represents an object/type)."""
    name: str
    label: str = ""


@dataclass
class Box:
    """
    A box in a string diagram (represents a morphism).

    inputs: wires entering from the left
    outputs: wires exiting to the right
    """
    name: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    morphism_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Diagram:
    """
    A planar string diagram.

    Boxes are ordered left-to-right (composition order).
    Wires connect output of one box to input of the next.
    """
    name: str
    boxes: List[Box] = field(default_factory=list)
    wires: List[Wire] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)  # external input wires
    outputs: List[str] = field(default_factory=list)  # external output wires

    @property
    def width(self) -> int:
        """Number of boxes (composition depth)."""
        return len(self.boxes)

    @property
    def height(self) -> int:
        """Maximum number of parallel wires."""
        max_h = len(self.inputs)
        for box in self.boxes:
            max_h = max(max_h, len(box.inputs), len(box.outputs))
        return max(max_h, len(self.outputs))


def from_morphisms(
    category: Category,
    morphism_ids: List[str],
) -> Diagram:
    """
    Build a string diagram from a sequence of composed morphisms.

    Each morphism becomes a box. Wires connect consecutive boxes.
    """
    diagram = Diagram(name=f"diagram({len(morphism_ids)} boxes)")

    for i, mor_id in enumerate(morphism_ids):
        mor = category.get_morphism(mor_id)
        if mor is None:
            continue

        # Create wires for source/target
        src_wire = Wire(name=f"w_{mor.source}_{i}", label=mor.source)
        tgt_wire = Wire(name=f"w_{mor.target}_{i}", label=mor.target)

        if src_wire.name not in [w.name for w in diagram.wires]:
            diagram.wires.append(src_wire)
        if tgt_wire.name not in [w.name for w in diagram.wires]:
            diagram.wires.append(tgt_wire)

        box = Box(
            name=mor.name,
            inputs=[src_wire.name],
            outputs=[tgt_wire.name],
            morphism_id=mor_id,
        )
        diagram.boxes.append(box)

        if i == 0:
            diagram.inputs = [src_wire.name]
        if i == len(morphism_ids) - 1:
            diagram.outputs = [tgt_wire.name]

    return diagram


def from_tensor(
    category: Category,
    parallel_morphism_ids: List[str],
) -> Diagram:
    """
    Build a string diagram from parallel (tensored) morphisms.

    Each morphism becomes a box stacked vertically.
    """
    diagram = Diagram(name=f"tensor({len(parallel_morphism_ids)} boxes)")

    for i, mor_id in enumerate(parallel_morphism_ids):
        mor = category.get_morphism(mor_id)
        if mor is None:
            continue

        src_wire = Wire(name=f"w_{mor.source}_{i}", label=mor.source)
        tgt_wire = Wire(name=f"w_{mor.target}_{i}", label=mor.target)
        diagram.wires.append(src_wire)
        diagram.wires.append(tgt_wire)

        box = Box(
            name=mor.name,
            inputs=[src_wire.name],
            outputs=[tgt_wire.name],
            morphism_id=mor_id,
        )
        diagram.boxes.append(box)
        diagram.inputs.append(src_wire.name)
        diagram.outputs.append(tgt_wire.name)

    return diagram


def evaluate(
    diagram: Diagram,
    category: Category,
    input_values: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Evaluate a string diagram by applying each box's morphism.

    Returns the values on output wires.
    """
    wire_values: Dict[str, Any] = {}
    if input_values:
        wire_values.update(input_values)

    for box in diagram.boxes:
        if box.morphism_id is None:
            continue

        mor = category.get_morphism(box.morphism_id)
        if mor is None or not mor.is_callable:
            # Pass through
            for inp, out in zip(box.inputs, box.outputs):
                wire_values[out] = wire_values.get(inp)
            continue

        # Collect input values
        args = [wire_values.get(w) for w in box.inputs]
        args = [a for a in args if a is not None]

        if args:
            result = mor(*args)
            if len(box.outputs) == 1:
                wire_values[box.outputs[0]] = result
            elif isinstance(result, tuple):
                for out, val in zip(box.outputs, result):
                    wire_values[out] = val

    return {w: wire_values.get(w) for w in diagram.outputs}


def to_ascii(diagram: Diagram) -> str:
    """
    Render a string diagram as ASCII art.

    Each box is drawn with input/output wires.
    """
    if not diagram.boxes:
        return "(empty diagram)"

    lines = []
    max_label = max(
        (len(b.name) for b in diagram.boxes), default=3
    )
    box_width = max(max_label + 4, 8)

    # Draw each box
    for i, box in enumerate(diagram.boxes):
        # Input wires
        input_labels = ", ".join(
            w.split("_")[1] if "_" in w else w for w in box.inputs
        )
        output_labels = ", ".join(
            w.split("_")[1] if "_" in w else w for w in box.outputs
        )

        label = box.name.center(box_width - 2)
        top = "+" + "-" * (box_width - 2) + "+"
        mid = "|" + label + "|"
        bot = "+" + "-" * (box_width - 2) + "+"

        wire_in = f"  {input_labels} -->"
        wire_out = f"--> {output_labels}"

        if i == 0:
            lines.append(wire_in)
        lines.append(top)
        lines.append(mid)
        lines.append(bot)
        if i < len(diagram.boxes) - 1:
            lines.append("      |")
            lines.append("      v")
        else:
            lines.append(wire_out)

    return "\n".join(lines)


def simplify(
    diagram: Diagram,
    rules: Dict[str, str] = None,
) -> Diagram:
    """
    Simplify a string diagram using equational rewriting.

    Rules map box-name patterns to simplified forms.
    Default rules:
    - Remove identity boxes
    - Merge consecutive same-named boxes
    """
    if rules is None:
        rules = {}

    simplified_boxes = []
    for box in diagram.boxes:
        # Skip identity morphisms
        if box.name in ("id", "identity"):
            continue
        # Apply custom rules
        if box.name in rules:
            new_name = rules[box.name]
            if new_name == "":
                continue  # Remove the box
            box = Box(
                name=new_name,
                inputs=box.inputs,
                outputs=box.outputs,
                morphism_id=box.morphism_id,
            )
        simplified_boxes.append(box)

    return Diagram(
        name=f"simplified({diagram.name})",
        boxes=simplified_boxes,
        wires=diagram.wires,
        inputs=diagram.inputs,
        outputs=diagram.outputs,
    )
