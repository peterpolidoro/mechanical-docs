import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIXTURE = ROOT / "examples" / "three-part-fixture"


@pytest.fixture
def fixture_dir():
    return FIXTURE


@pytest.fixture
def project_copy(tmp_path):
    """A writable copy of the synthetic fixture, with a helper to mutate one manifest."""
    dst = tmp_path / "project"
    shutil.copytree(FIXTURE, dst, ignore=shutil.ignore_patterns("__pycache__"))

    class Copy:
        dir = dst

        @staticmethod
        def edit(name, fn):
            p = dst / name
            data = json.loads(p.read_text())
            fn(data)
            p.write_text(json.dumps(data, indent=2))
            return p

    return Copy
