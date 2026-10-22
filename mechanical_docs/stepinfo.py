"""Read what a STEP file declares about itself without a CAD kernel.

The authoritative length unit is the LENGTH_UNIT entity referenced from
GLOBAL_UNIT_ASSIGNED_CONTEXT; other LENGTH_UNIT entities may exist (an inch
file carries the millimetre unit its inch is defined from). Inventor writes
complex entities across several lines, FreeCAD on one line; both are handled by
splitting the DATA section on ';'.
"""
from __future__ import annotations

import re
from pathlib import Path

_GUAC = re.compile(r"GLOBAL_UNIT_ASSIGNED_CONTEXT\s*\(\s*\(([^)]*)\)\s*\)", re.S)
_ENTITY = re.compile(r"^\s*#(\d+)\s*=\s*(.*)$", re.S)
_SI = re.compile(r"SI_UNIT\s*\(\s*(\$|\.[A-Z]+\.)\s*,\s*\.METRE\.\s*\)")
_CONV = re.compile(r"CONVERSION_BASED_UNIT\s*\(\s*'([^']*)'", re.I)
SI_PREFIX = {"$": "m", ".MILLI.": "mm", ".CENTI.": "cm", ".KILO.": "km", ".MICRO.": "um"}
CONVERSION_NAMES = {"inch": "in", "inches": "in", "in": "in", "foot": "ft", "feet": "ft", "ft": "ft"}


class StepInfoError(ValueError):
    pass


def _entities(text):
    """{id: body} for every '#n = body;' entity in the DATA section."""
    start = text.find("DATA;")
    body = text[start + 5:] if start >= 0 else text
    end = body.find("ENDSEC;")
    if end >= 0:
        body = body[:end]
    out = {}
    for chunk in body.split(";"):
        m = _ENTITY.match(chunk)
        if m:
            out[int(m.group(1))] = " ".join(m.group(2).split())
    return out


def length_unit(path):
    """The declared geometry length unit of a STEP file: 'mm', 'cm', 'm', 'in', 'ft'.

    Raises StepInfoError when there is no unit context, no LENGTH_UNIT among
    its referenced units, or several contexts disagree."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    ents = _entities(text)
    contexts = _GUAC.findall(text)
    if not contexts:
        raise StepInfoError(f"{Path(path).name}: no GLOBAL_UNIT_ASSIGNED_CONTEXT")
    found = set()
    for refs in contexts:
        for ref in refs.split(","):
            ref = ref.strip()
            if not ref.startswith("#"):
                continue
            ent = ents.get(int(ref[1:]), "")
            if "LENGTH_UNIT" not in ent:
                continue
            cm = _CONV.search(ent)
            if cm:
                name = cm.group(1).strip().lower()
                if name not in CONVERSION_NAMES:
                    raise StepInfoError(f"{Path(path).name}: unknown conversion-based length unit {name!r}")
                found.add(CONVERSION_NAMES[name])
                continue
            sm = _SI.search(ent)
            if sm:
                found.add(SI_PREFIX.get(sm.group(1), sm.group(1)))
    if not found:
        raise StepInfoError(f"{Path(path).name}: the unit context references no LENGTH_UNIT")
    if len(found) > 1:
        raise StepInfoError(f"{Path(path).name}: unit contexts disagree: {sorted(found)}")
    return found.pop()
