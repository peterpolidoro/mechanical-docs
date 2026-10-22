import json

import pytest

from mechanical_docs.render_settings import DEFAULTS, SettingsError, load_settings


def test_defaults_without_file(tmp_path):
    s, p = load_settings(tmp_path)
    assert p is None and s["engine"] == DEFAULTS["engine"] and s["looks"] == {}


def test_fixture_settings_override_looks_groups_and_joints(fixture_dir):
    s, p = load_settings(fixture_dir)
    assert p.name == "render.json"
    assert s["looks"] == {"base": "aluminium", "pin": "blue-anodized"}
    assert s["samples"] == DEFAULTS["samples"]
    assert s["inspection_groups"] == ["pin-pair"]
    assert s["joint_views"] == [{"id": None, "joint_id": "pin_to_base", "occurrence_ids": ["pin-a", "base-1"], "direction": [1.0, -1.2, 0.8],
                                 "context": None, "context_style": "faded"}]


def test_joint_views_are_validated_structurally(tmp_path):
    def settings(jv):
        (tmp_path / "render.json").write_text(json.dumps({"joint_views": jv}))
        return load_settings(tmp_path)
    with pytest.raises(SettingsError, match="joint_views must be a list"):
        settings({"joint_id": "x"})
    with pytest.raises(SettingsError, match="unsupported field"):
        settings([{"joint_id": "x", "occurrence_ids": ["a"], "explode": 2}])
    with pytest.raises(SettingsError, match="occurrence_ids: expected a non-empty list"):
        settings([{"joint_id": "x", "occurrence_ids": []}])
    with pytest.raises(SettingsError, match="listed twice"):
        settings([{"joint_id": "x", "occurrence_ids": ["a", "a"]}])
    with pytest.raises(SettingsError, match="direction: expected three numbers"):
        settings([{"joint_id": "x", "occurrence_ids": ["a"], "direction": [1, 2]}])
    with pytest.raises(SettingsError, match="context_style: expected one of"):
        settings([{"joint_id": "x", "occurrence_ids": ["a"], "context_style": "exploded"}])
    with pytest.raises(SettingsError, match="context: expected an assembly or occurrence id, or a list"):
        settings([{"joint_id": "x", "occurrence_ids": ["a"], "context": ["G", 3]}])
    s, _ = settings([{"joint_id": "x", "occurrence_ids": ["a", "b"], "context": "G", "context_style": "hidden", "id": "x-1"}])
    assert s["joint_views"] == [{"id": "x-1", "joint_id": "x", "occurrence_ids": ["a", "b"], "direction": None, "context": "G", "context_style": "hidden"}]
    s, _ = settings([{"joint_id": "x", "occurrence_ids": ["a"], "context": ["G", "occ-1"]}])
    assert s["joint_views"][0]["context"] == ["G", "occ-1"]


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
