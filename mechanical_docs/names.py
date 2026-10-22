"""File-system-safe names for identifiers that may contain anything.

Production identifiers are Vault paths, model states and occurrence paths
(`DATA\\COMMON\\x.ipt|[Primary]`, `CAMERA FRAME:1/MCMASTER 5537T293:1`). They
stay as they are in manifests and receipts; images and Blender objects get a
slug: lower-case, ASCII letters/digits/hyphens, plus a short hash so distinct
ids never collide.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

_NON = re.compile(r"[^a-z0-9]+")


def slug(identifier, length=48):
    text = unicodedata.normalize("NFKD", str(identifier)).encode("ascii", "ignore").decode("ascii").lower()
    base = _NON.sub("-", text).strip("-")
    digest = hashlib.sha256(str(identifier).encode("utf-8")).hexdigest()[:8]
    if base == text and len(base) <= length and base:
        return base                                  # already a clean slug: unchanged (fixture ids)
    return (base[:length].rstrip("-") or "id") + "-" + digest


def valid_identifier(value, max_len=200):
    """Non-empty, no control characters, no surrounding whitespace, bounded length."""
    return (isinstance(value, str) and 0 < len(value) <= max_len and value == value.strip()
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))
