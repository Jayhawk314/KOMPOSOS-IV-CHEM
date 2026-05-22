# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Polynomial Functors: Interfaces and Dynamical Systems

A polynomial functor p = sum_{i in I} y^{B_i} represents an interface:
- Positions I: the possible "states" or "outputs"
- Directions B_i: the possible "inputs" at each position

Coalgebras of polynomial functors are dynamical systems:
state-machines with typed I/O specified by the polynomial.

Products of polynomials model composition of dynamical systems.

Reference: Spivak, "Poly: An abundant categorical setting" (2021)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.category import Category


@dataclass
class PolynomialFunctor:
    """
    A polynomial functor p = sum_{i in positions} y^{directions[i]}.

    Fields:
        name: Identifier.
        positions: The set of positions (output states).
        directions: Map from position to set of directions (inputs).
    """
    name: str
    positions: Set[str] = field(default_factory=set)
    directions: Dict[str, Set[str]] = field(default_factory=dict)

    @property
    def degree(self) -> int:
        """Total number of directions across all positions."""
        return sum(len(d) for d in self.directions.values())

    def add_position(self, pos: str, dirs: Set[str] = None):
        """Add a position with its directions."""
        self.positions.add(pos)
        self.directions[pos] = dirs or set()


@dataclass
class DynamicalSystem:
    """
    A coalgebra of a polynomial functor: a state machine.

    Fields:
        name: Identifier.
        interface: The polynomial functor specifying I/O.
        state_set: Set of internal states.
        readout: state -> position (what the system outputs).
        update: (state, direction) -> state (how the system transitions).
    """
    name: str
    interface: PolynomialFunctor
    state_set: Set[str] = field(default_factory=set)
    readout: Optional[Callable[[str], str]] = None
    update: Optional[Callable[[str, str], str]] = None

    def output(self, state: str) -> str:
        """Get the output (position) for a given state."""
        if self.readout is None:
            return state
        return self.readout(state)

    def step(self, state: str, input_val: str) -> str:
        """Apply one transition: (state, input) -> new_state."""
        if self.update is None:
            return state
        return self.update(state, input_val)


def run(
    system: DynamicalSystem,
    initial_state: str,
    inputs: List[str],
) -> List[Tuple[str, str]]:
    """
    Execute a dynamical system for a sequence of inputs.

    Returns:
        List of (state, output) pairs at each step.
    """
    state = initial_state
    trace = [(state, system.output(state))]

    for inp in inputs:
        state = system.step(state, inp)
        trace.append((state, system.output(state)))

    return trace


def sequential(p: PolynomialFunctor, q: PolynomialFunctor) -> PolynomialFunctor:
    """
    Composition product of polynomial functors: p . q.

    Positions: (i, f: B_i -> positions(q))
    Directions at (i,f): disjoint union of directions(q, f(b)) for b in B_i
    """
    result = PolynomialFunctor(name=f"{p.name} . {q.name}")

    for i in p.positions:
        for j in q.positions:
            pos_name = f"({i},{j})"
            dirs = set()
            for d_p in p.directions.get(i, set()):
                for d_q in q.directions.get(j, set()):
                    dirs.add(f"({d_p},{d_q})")
            result.add_position(pos_name, dirs)

    return result


def parallel(p: PolynomialFunctor, q: PolynomialFunctor) -> PolynomialFunctor:
    """
    Cartesian product of polynomial functors: p x q.

    Positions: positions(p) x positions(q)
    Directions at (i,j): directions(p,i) x directions(q,j)
    """
    result = PolynomialFunctor(name=f"{p.name} x {q.name}")

    for i in p.positions:
        for j in q.positions:
            pos_name = f"({i},{j})"
            dirs = set()
            for d_p in p.directions.get(i, set()):
                for d_q in q.directions.get(j, set()):
                    dirs.add(f"({d_p},{d_q})")
            result.add_position(pos_name, dirs)

    return result


def correlated(p: PolynomialFunctor, q: PolynomialFunctor) -> PolynomialFunctor:
    """
    Dirichlet product: sum_{i,j} y^{B_i x C_j} (correlated inputs).
    """
    result = PolynomialFunctor(name=f"{p.name} D {q.name}")

    for i in p.positions:
        for j in q.positions:
            pos_name = f"({i},{j})"
            dirs = set()
            for d_p in p.directions.get(i, set()):
                for d_q in q.directions.get(j, set()):
                    dirs.add(f"({d_p},{d_q})")
            result.add_position(pos_name, dirs)

    return result


def poly_morphism(
    p: PolynomialFunctor,
    q: PolynomialFunctor,
    on_positions: Callable[[str], str],
    on_directions: Callable[[str, str], str],
) -> Dict[str, Any]:
    """
    A morphism of polynomial functors (dependent lens).

    on_positions: positions(p) -> positions(q)
    on_directions: (i, d_q) -> d_p  (contravariant on directions)

    Returns a dict describing the morphism mapping.
    """
    mapping = {"positions": {}, "directions": {}}

    for i in p.positions:
        j = on_positions(i)
        mapping["positions"][i] = j
        mapping["directions"][i] = {}
        for d_q in q.directions.get(j, set()):
            d_p = on_directions(i, d_q)
            mapping["directions"][i][d_q] = d_p

    return mapping


def compose_systems(
    s1: DynamicalSystem, s2: DynamicalSystem
) -> DynamicalSystem:
    """
    Sequential composition of dynamical systems.

    System 1's output feeds into System 2's input.
    """
    combined_states = set()
    for a in s1.state_set:
        for b in s2.state_set:
            combined_states.add(f"({a},{b})")

    def readout(state):
        _, b = state.strip("()").split(",", 1)
        return s2.output(b)

    def update(state, inp):
        a, b = state.strip("()").split(",", 1)
        new_a = s1.step(a, inp)
        mid_out = s1.output(new_a)
        new_b = s2.step(b, mid_out)
        return f"({new_a},{new_b})"

    return DynamicalSystem(
        name=f"{s1.name} >> {s2.name}",
        interface=sequential(s1.interface, s2.interface),
        state_set=combined_states,
        readout=readout,
        update=update,
    )


def register_system(category: Category, system: DynamicalSystem) -> str:
    """Register a dynamical system's states and transitions in a Category."""
    sys_name = f"sys:{system.name}"
    category.add(sys_name, type_name="DynamicalSystem",
                 metadata={"interface": system.interface.name})
    for state in sorted(system.state_set):
        state_name = f"{system.name}:{state}"
        category.add(state_name, type_name="State",
                     metadata={"system": system.name})
        category.connect(sys_name, state_name, name="has_state")
    for state in sorted(system.state_set):
        pos = system.readout(state) if system.readout else state
        for direction in sorted(system.interface.directions.get(pos, set())):
            next_state = system.update(state, direction)
            src = f"{system.name}:{state}"
            tgt = f"{system.name}:{next_state}"
            category.connect(src, tgt, name=direction, confidence=1.0)
    return sys_name


def run_traced(category: Category, system: DynamicalSystem,
               initial_state: str, inputs: list) -> list:
    """Run a dynamical system, recording execution trace in the Category."""
    trace_data = run(system, initial_state, inputs)
    for i in range(len(trace_data) - 1):
        src_state, _ = trace_data[i]
        tgt_state, _ = trace_data[i + 1]
        src_name = f"{system.name}:{src_state}"
        tgt_name = f"{system.name}:{tgt_state}"
        if category.get(src_name) is None:
            category.add(src_name, type_name="TraceState")
        if category.get(tgt_name) is None:
            category.add(tgt_name, type_name="TraceState")
        category.connect(src_name, tgt_name, name=f"step{i}",
                         confidence=1.0, step=i + 1)
    return trace_data


def category_of_systems(systems: list, name: str = "PolySystems") -> Category:
    """Build a Category from multiple dynamical systems."""
    cat = Category(name=name, db_path=":memory:")
    for sys in systems:
        register_system(cat, sys)
    return cat
