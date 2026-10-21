import pytest

from mechanical_docs import transforms as T
from mechanical_docs.manifest import Instructions, Step, load_project
from mechanical_docs.procedure import ProcedureError, approach_pose, derive_states


def test_states_are_cumulative(fixture_dir):
    pr = load_project(fixture_dir)
    states = derive_states(pr.instructions, pr.scene)
    assert [s.before for s in states] == [[], ["base-1"], ["base-1", "pin-a"]]
    assert [s.added for s in states] == [["base-1"], ["pin-a"], ["pin-b"]]
    assert states[0].hidden == ["pin-a", "pin-b"]
    assert states[2].hidden == []
    assert states[1].parts_needed == {"pin": 1}
    assert states[0].parts_needed == {"base": 1}


def test_approach_pose_uses_canonical_end(fixture_dir):
    pr = load_project(fixture_dir)
    states = derive_states(pr.instructions, pr.scene)
    assert approach_pose(pr.scene, states[0]) is None
    oid, start, end = approach_pose(pr.scene, states[1])
    assert oid == "pin-a"
    assert T.translation(start) == [-25, 0, 40]
    assert end == pr.scene.occurrences["pin-a"].world


def test_derive_rejects_unordered_prerequisite(fixture_dir):
    pr = load_project(fixture_dir)
    ins = pr.instructions
    bad = Instructions(ins.id, ins.title, ins.review_state, ins.views,
                       [Step("a", ["b"], ["base-1"], "overview", ""), Step("b", [], ["pin-a", "pin-b"], "overview", "")], ins.file, ins.sha256)
    with pytest.raises(ProcedureError, match="requires"):
        derive_states(bad, pr.scene)


def test_derive_rejects_incomplete_install(fixture_dir):
    pr = load_project(fixture_dir)
    ins = pr.instructions
    bad = Instructions(ins.id, ins.title, ins.review_state, ins.views, [Step("a", [], ["base-1"], "overview", "")], ins.file, ins.sha256)
    with pytest.raises(ProcedureError, match="never installed"):
        derive_states(bad, pr.scene)
