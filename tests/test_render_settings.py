import json

import pytest

from mechanical_docs.render_settings import DEFAULTS, SettingsError, load_settings


def test_defaults_without_file(tmp_path):
    s, p = load_settings(tmp_path)
    assert p is None and s["engine"] == DEFAULTS["engine"] and s["looks"] == {}


def test_fixture_settings_override_looks_only(fixture_dir):
    s, p = load_settings(fixture_dir)
    assert p.name == "render.json"
    assert s["looks"] == {"base": "aluminium", "pin": "blue-anodized"}
    assert s["samples"] == DEFAULTS["samples"]


def test_unknown_field_rejected(tmp_path):
    (tmp_path / "render.json").write_text(json.dumps({"schema_version": "draft-1", "transform_scale": 2}))
    with pytest.raises(SettingsError, match="unsupported field"):
        load_settings(tmp_path)


def test_unknown_look_rejected(tmp_path):
    (tmp_path / "render.json").write_text(json.dumps({"looks": {"base": "chrome-ish"}}))
    with pytest.raises(SettingsError, match="unknown look"):
        load_settings(tmp_path)


def test_palette_entries_can_be_added(tmp_path):
    (tmp_path / "render.json").write_text(json.dumps({"palette": {"teal": {"base": [0, 0.5, 0.5]}}, "looks": {"base": "teal"}}))
    s, _ = load_settings(tmp_path)
    assert "aluminium" in s["palette"] and s["palette"]["teal"]["base"] == [0, 0.5, 0.5]
