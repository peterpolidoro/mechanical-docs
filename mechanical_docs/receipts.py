"""Build receipts: what went in, what came out, with hashes and versions."""
from __future__ import annotations

import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_entry(path, relative_to=None):
    p = Path(path)
    rel = str(p.relative_to(relative_to)) if relative_to else str(p)
    return {"path": rel, "bytes": p.stat().st_size, "sha256": sha256_file(p)}


def python_info():
    return {"python": sys.version.split()[0], "platform": platform.platform()}


def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return p


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
