# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Bill-of-materials ingestion: free-form input in, honest resolution out.

The gap this closes: every workflow previously required material names typed
from the fixed bridge vocabulary. A real user has a CSV export, a supplier
list, or a pasted table full of brand names ("Kynar 2801"), free-text
("copper foil"), and things this system has never heard of. This module

  1. parses that input tolerantly (CSV / TSV / semicolon / pipe / plain lines,
     with or without a header row),
  2. resolves each name against the bridge vocabularies, alias tables, and the
     PFAS registry, and
  3. reports what it could NOT resolve explicitly, with close-match
     suggestions, instead of dropping or guessing.

The honesty contract mirrors the rest of the system: an unrecognized material
is a first-class outcome, never silently coerced to the nearest known name.
Suggestions are surfaced for a human to confirm; they are not auto-applied.
"""

from __future__ import annotations

import csv
import difflib
import io
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Vocabulary assembly (lazy, cached)
# ---------------------------------------------------------------------------

# canonical_key -> domain  (e.g. "PVDF" -> "polymer"; keys may repeat across
# bridges -- first registration wins for display, all domains are recorded)
_VOCAB: Optional[Dict[str, List[str]]] = None
# lowercase form -> canonical key, only when unambiguous
_LOWER_TO_CANONICAL: Optional[Dict[str, str]] = None
# alias (lowercase) -> canonical key
_ALIAS_TO_CANONICAL: Optional[Dict[str, str]] = None

# Free-text / brand aliases beyond what the bridges already carry. Keys are
# matched case-insensitively on the NORMALIZED name (spaces/hyphens collapsed).
# Only map to names that exist in a bridge vocabulary -- this table must never
# invent a material.
_FREE_TEXT_ALIASES: Dict[str, str] = {
    # collectors / foils
    "cu foil": "Cu_foil", "copper foil": "Cu_foil",
    "al foil": "Al_foil", "aluminum foil": "Al_foil", "aluminium foil": "Al_foil",
    "ni tab": "Ni_tab", "nickel tab": "Ni_tab",
    # brand names -> generic (PFAS registry knows these too; the vocabulary
    # mapping lets the compatibility side use them as well)
    "kynar": "PVDF", "solef": "PVDF", "hylar": "PVDF",
    "teflon": "PTFE", "dyneon": "PTFE",
    # common free-text polymer names
    "polyvinylidene fluoride": "PVDF",
    "polytetrafluoroethylene": "PTFE",
    "polypropylene": "PP", "polyethylene": "PE",
    "polystyrene": "PS", "polycarbonate": "PC",
    "carboxymethyl cellulose": "CMC", "carboxymethylcellulose": "CMC",
    "styrene butadiene rubber": "SBR", "styrene-butadiene rubber": "SBR",
    "polyethylene oxide": "PEO", "polyacrylonitrile": "PAN",
    "n-methyl-2-pyrrolidone": "NMP", "n-methylpyrrolidone": "NMP",
    "ethylene carbonate": "EC", "dimethyl carbonate": "DMC",
    "diethyl carbonate": "DEC", "ethyl methyl carbonate": "EMC",
    # metals free text
    "stainless steel": "SS_316", "stainless": "SS_316",
    "copper": "Cu", "aluminum": "Al", "aluminium": "Al", "nickel": "Ni",
    "titanium": "Ti", "iron": "Fe", "zinc": "Zn", "tin": "Sn",
    "gold": "Au", "silver": "Ag", "platinum": "Pt", "tungsten": "W",
    "lithium metal": "Li_metal", "lithium foil": "Li_metal",
    # ceramics free text
    "alumina": "Al2O3", "aluminum oxide": "Al2O3", "aluminium oxide": "Al2O3",
    "zirconia": "ZrO2_YSZ", "silica": "SiO2", "silicon dioxide": "SiO2",
    "silicon carbide": "SiC", "silicon nitride": "Si3N4",
    "titania": "TiO2", "titanium dioxide": "TiO2",
    "hydroxyapatite": "Hydroxyapatite",
    # graphite variants
    "natural graphite": "Graphite", "artificial graphite": "Graphite",
    "synthetic graphite": "Graphite",
}

_BRIDGE_SOURCES = [
    ("battery_bridge.material_properties", "ALL_MATERIALS", "battery"),
    ("polymer_bridge.material_properties", "ALL_POLYMERS", "polymer"),
    ("ceramic_bridge.material_properties", "ALL_CERAMICS", "ceramic"),
    ("metal_bridge.material_properties", "ALL_METALS", "metal"),
    ("semiconductor_bridge.material_properties", "ALL_SEMICONDUCTORS", "semiconductor"),
    ("glass_bridge.material_properties", "ALL_GLASSES", "glass"),
]
_BRIDGE_ALIAS_TABLES = [
    ("polymer_bridge.material_properties", "_POLYMER_ALIASES"),
    ("metal_bridge.material_properties", "_METAL_ALIASES"),
]


def _normalize(name: str) -> str:
    """Collapse whitespace/hyphens/underscores; lowercase. For matching only."""
    return re.sub(r"[\s\-_]+", " ", name.strip()).lower()


def _build_vocab() -> None:
    global _VOCAB, _LOWER_TO_CANONICAL, _ALIAS_TO_CANONICAL
    if _VOCAB is not None:
        return
    vocab: Dict[str, List[str]] = {}
    for mod_name, attr, domain in _BRIDGE_SOURCES:
        try:
            mod = __import__(mod_name, fromlist=[attr])
            for key in getattr(mod, attr):
                vocab.setdefault(key, []).append(domain)
        except Exception:
            continue

    lower: Dict[str, Optional[str]] = {}
    for key in vocab:
        k = key.lower()
        # ambiguous lowercase forms resolve to None and are dropped below
        lower[k] = key if lower.get(k, key) == key else None
    lower_clean = {k: v for k, v in lower.items() if v is not None}

    aliases: Dict[str, str] = {}
    for mod_name, attr in _BRIDGE_ALIAS_TABLES:
        try:
            mod = __import__(mod_name, fromlist=[attr])
            for alias, target in getattr(mod, attr).items():
                if target in vocab:
                    aliases[_normalize(alias)] = target
        except Exception:
            continue
    for alias, target in _FREE_TEXT_ALIASES.items():
        if target in vocab:
            aliases[_normalize(alias)] = target

    _VOCAB, _LOWER_TO_CANONICAL, _ALIAS_TO_CANONICAL = vocab, lower_clean, aliases


def known_vocabulary() -> Dict[str, List[str]]:
    """canonical material key -> list of domains that recognize it."""
    _build_vocab()
    return dict(_VOCAB or {})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BOMLine:
    """One raw parsed row of a bill of materials."""
    raw_name: str
    function: Optional[str] = None
    quantity_kg: Optional[float] = None
    source_row: int = 0


@dataclass
class ResolvedMaterial:
    """Resolution outcome for one BOM line. Unrecognized is a first-class state."""
    line: BOMLine
    status: str                     # "matched" | "alias" | "pfas_only" | "unrecognized"
    canonical: Optional[str] = None # vocabulary key when matched/alias
    domains: List[str] = field(default_factory=list)
    matched_via: Optional[str] = None   # "exact" | "case" | "bridge_alias" | "free_text_alias"
    pfas_flag: bool = False             # PFAS registry hit (may coexist with matched)
    pfas_base: Optional[str] = None     # e.g. "PVDF" for "Kynar 2801"
    suggestions: List[str] = field(default_factory=list)  # for unrecognized only

    def to_dict(self) -> Dict[str, object]:
        return {
            "raw_name": self.line.raw_name,
            "function": self.line.function,
            "quantity_kg": self.line.quantity_kg,
            "status": self.status,
            "canonical": self.canonical,
            "domains": self.domains,
            "matched_via": self.matched_via,
            "pfas_flag": self.pfas_flag,
            "pfas_base": self.pfas_base,
            "suggestions": self.suggestions,
        }


@dataclass
class IngestResult:
    """Everything parsed, split by resolution outcome. Nothing is dropped."""
    resolved: List[ResolvedMaterial]
    parse_warnings: List[str] = field(default_factory=list)

    @property
    def matched(self) -> List[ResolvedMaterial]:
        return [r for r in self.resolved if r.status in ("matched", "alias")]

    @property
    def pfas_only(self) -> List[ResolvedMaterial]:
        return [r for r in self.resolved if r.status == "pfas_only"]

    @property
    def unrecognized(self) -> List[ResolvedMaterial]:
        return [r for r in self.resolved if r.status == "unrecognized"]

    def to_material_inputs(self, include_unrecognized: bool = True):
        """Convert to the PFAS report's MaterialInput list.

        Unrecognized names are INCLUDED by default: the PFAS report already
        treats unknown materials honestly (they are neither cleared nor
        flagged), and excluding them here would hide part of the user's BOM.
        Matched names are passed under their canonical key so downstream
        scorers recognize them; the raw name is preserved in the function
        text when it differs.
        """
        from reports.pfas_report import MaterialInput
        out = []
        for r in self.resolved:
            if r.status == "unrecognized" and not include_unrecognized:
                continue
            name = r.canonical or (r.pfas_base if r.status == "pfas_only" else None) or r.line.raw_name
            func = r.line.function
            if name != r.line.raw_name:
                func = f"{func or 'unspecified'} (input: {r.line.raw_name})"
            out.append(MaterialInput(name=name, function=func, quantity_kg=r.line.quantity_kg))
        return out

    def summary(self) -> Dict[str, int]:
        return {
            "lines": len(self.resolved),
            "matched": len(self.matched),
            "pfas_only": len(self.pfas_only),
            "unrecognized": len(self.unrecognized),
        }

    def to_dict(self) -> Dict[str, object]:
        return {
            "summary": self.summary(),
            "parse_warnings": self.parse_warnings,
            "materials": [r.to_dict() for r in self.resolved],
        }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_NAME_HEADERS = {"name", "material", "material name", "component", "substance",
                 "item", "part", "chemical", "product"}
_FUNCTION_HEADERS = {"function", "role", "use", "usage", "purpose", "application",
                     "description", "component function"}
_QTY_HEADERS = {"quantity", "quantity kg", "quantity_kg", "qty", "qty kg", "mass",
                "mass kg", "amount", "kg", "weight", "weight kg"}

_UNIT_SUFFIX = re.compile(r"\s*(kg|g|kilograms?|grams?)\s*$", re.IGNORECASE)


def _parse_qty(text: Optional[str]) -> Optional[float]:
    if text is None:
        return None
    t = _UNIT_SUFFIX.sub("", str(text).strip())
    if not t:
        return None
    # Comma disambiguation: "1,500" (thousands) vs European "1,5" (decimal).
    # A single comma followed by 1-2 trailing digits is a decimal separator;
    # commas followed by exactly 3 digits are thousands separators.
    if "," in t and "." not in t:
        if re.fullmatch(r"\d+,\d{1,2}", t):
            t = t.replace(",", ".")
        else:
            t = t.replace(",", "")
    else:
        t = t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def _detect_delimiter(lines: List[str]) -> str:
    """Pick the delimiter that splits the most lines consistently."""
    candidates = ["|", "\t", ";", ","]
    best, best_score = ",", 0
    for d in candidates:
        counts = [ln.count(d) for ln in lines if ln.strip()]
        if not counts:
            continue
        # consistent nonzero split count across lines scores highest
        nonzero = [c for c in counts if c > 0]
        if not nonzero:
            continue
        score = len(nonzero) * (1 + (max(set(nonzero), key=nonzero.count)))
        if score > best_score:
            best, best_score = d, score
    return best


def parse_bom_text(text: str) -> Tuple[List[BOMLine], List[str]]:
    """Parse pasted/CSV BOM text into rows. Returns (lines, warnings).

    Accepts comma/semicolon/tab/pipe separation, with or without a header row,
    or plain one-name-per-line input. Blank lines and #-comments are skipped.
    Rows that cannot be parsed are reported in warnings, never silently lost.
    """
    raw_lines = [ln for ln in text.splitlines()]
    content = [ln for ln in raw_lines if ln.strip() and not ln.strip().startswith("#")]
    if not content:
        return [], ["no content lines found"]

    delim = _detect_delimiter(content)
    reader = csv.reader(io.StringIO("\n".join(content)), delimiter=delim)
    rows = [[c.strip() for c in row] for row in reader]

    warnings: List[str] = []
    name_i, func_i, qty_i = 0, 1, 2
    start = 0
    # normalize header cells: lowercase, drop parenthesized units ("Qty (kg)"),
    # collapse separators
    header = [re.sub(r"\(.*?\)", "", c).strip().lower().replace("_", " ").replace("-", " ")
              for c in rows[0]] if rows else []
    header = [re.sub(r"\s+", " ", h) for h in header]
    if header and (set(header) & (_NAME_HEADERS | _FUNCTION_HEADERS | _QTY_HEADERS)):
        start = 1
        name_i = next((i for i, h in enumerate(header) if h in _NAME_HEADERS), 0)
        func_i = next((i for i, h in enumerate(header) if h in _FUNCTION_HEADERS), -1)
        qty_i = next((i for i, h in enumerate(header) if h in _QTY_HEADERS), -1)

    out: List[BOMLine] = []
    for rownum, row in enumerate(rows[start:], start=start + 1):
        if not row or not any(c for c in row):
            continue
        if name_i >= len(row) or not row[name_i]:
            warnings.append(f"row {rownum}: no material name; skipped ({row})")
            continue
        func = row[func_i] if 0 <= func_i < len(row) and row[func_i] else None
        qty = _parse_qty(row[qty_i]) if 0 <= qty_i < len(row) else None
        # headerless 3-column fallback: col2=function col3=qty already covered
        out.append(BOMLine(raw_name=row[name_i], function=func,
                           quantity_kg=qty, source_row=rownum))
    if not out:
        warnings.append("no parsable material rows")
    return out, warnings


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def resolve_material(name: str) -> ResolvedMaterial:
    """Resolve one material name. Never guesses: close matches are suggestions."""
    _build_vocab()
    assert _VOCAB is not None and _LOWER_TO_CANONICAL is not None
    assert _ALIAS_TO_CANONICAL is not None
    line = BOMLine(raw_name=name)
    stripped = name.strip()
    norm = _normalize(stripped)

    canonical: Optional[str] = None
    via: Optional[str] = None
    if stripped in _VOCAB:
        canonical, via = stripped, "exact"
    elif stripped.lower() in _LOWER_TO_CANONICAL:
        canonical, via = _LOWER_TO_CANONICAL[stripped.lower()], "case"
    elif norm in _ALIAS_TO_CANONICAL:
        canonical, via = _ALIAS_TO_CANONICAL[norm], "free_text_alias"
    else:
        # brand-with-grade forms like "Kynar 2801": try alias on the first token(s)
        tokens = norm.split()
        for cut in range(len(tokens) - 1, 0, -1):
            prefix = " ".join(tokens[:cut])
            if prefix in _ALIAS_TO_CANONICAL:
                canonical, via = _ALIAS_TO_CANONICAL[prefix], "free_text_alias"
                break

    # PFAS registry check runs regardless of vocabulary match (PVDF is both)
    pfas_flag = False
    pfas_base: Optional[str] = None
    try:
        from pfas_bridge.pfas_registry import is_pfas, resolve_base_pfas
        pfas_flag = bool(is_pfas(stripped))
        if pfas_flag:
            pfas_base = resolve_base_pfas(stripped) or (canonical if canonical else None)
    except Exception:
        pass

    if canonical is not None:
        status = "matched" if via == "exact" else "alias"
        return ResolvedMaterial(line=line, status=status, canonical=canonical,
                                domains=list(_VOCAB.get(canonical, [])),
                                matched_via=via, pfas_flag=pfas_flag,
                                pfas_base=pfas_base)
    if pfas_flag:
        # Known to the PFAS registry but not to any compatibility bridge:
        # screenable for PFAS, not scoreable for interfaces.
        return ResolvedMaterial(line=line, status="pfas_only",
                                pfas_flag=True, pfas_base=pfas_base)

    pool = list(_LOWER_TO_CANONICAL.keys()) + list(_ALIAS_TO_CANONICAL.keys())
    close = difflib.get_close_matches(norm, pool, n=3, cutoff=0.75)
    seen: List[str] = []
    for c in close:
        target = _LOWER_TO_CANONICAL.get(c) or _ALIAS_TO_CANONICAL.get(c)
        if target and target not in seen:
            seen.append(target)
    return ResolvedMaterial(line=line, status="unrecognized", suggestions=seen)


def ingest_bom(text: str) -> IngestResult:
    """Parse and resolve a pasted/CSV bill of materials."""
    lines, warnings = parse_bom_text(text)
    resolved = []
    for ln in lines:
        r = resolve_material(ln.raw_name)
        r.line = ln  # keep function/quantity/source_row from the parse
        resolved.append(r)
    return IngestResult(resolved=resolved, parse_warnings=warnings)
