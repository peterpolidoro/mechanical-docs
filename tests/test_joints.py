"""motion.json: the joints and poses of a scene, and where a joint puts what it moves."""
import json
import math
from types import SimpleNamespace

import pytest

from mechanical_docs import joints
from mechanical_docs import transforms as T
from mechanical_docs.manifest import load_scene_only


def fixture_motion():
    """Joints for the three-part fixture, written by hand: its pair of pins swings about the middle of the base,
    one pin of the pair slides up out of its seat, and the other is driven down by the swing, a millimetre for
    every ten degrees. Synthetic, like the fixture: nothing there is hinged or geared."""
    return {"schema_version": 1, "scene": "scene.json",
            "source": {"kind": "mechanical-cad-motion", "file": "motion.toml", "sha256": "0" * 64},
            "joints": {"swing": {"kind": "revolute", "origin_mm": [0.0, 0.0, 0.0], "direction": [0.0, 0.0, 1.0],
                                 "lower": -30.0, "upper": 60.0, "unit": "deg"},
                       "lift": {"kind": "prismatic", "origin_mm": [-25.0, 0.0, 0.0], "direction": [0.0, 0.0, 1.0],
                                "lower": 0.0, "upper": 20.0, "unit": "mm"},
                       "sink": {"kind": "prismatic", "origin_mm": [25.0, 0.0, 0.0], "direction": [0.0, 0.0, 1.0],
                                "lower": -6.0, "upper": 3.0, "unit": "mm", "follows": {"joint": "swing", "ratio": -0.1}}},
            "moved": {"pin-a": ["swing", "lift"], "pin-b": ["swing", "sink"]},
            "poses": {"open": {"swing": 60.0, "lift": 20.0}, "closed": {"swing": -30.0}}}


def write(project_copy, change=None):
    data = fixture_motion()
    if change is not None:
        change(data)
    (project_copy.dir / joints.FILE).write_text(json.dumps(data, indent=2))
    return project_copy.dir / joints.FILE, load_scene_only(project_copy.dir).scene


def scene_of(units="mm", basis=None, **worlds):
    """What the transforms need of a scene: its units, its basis, and where its occurrences are."""
    return SimpleNamespace(units=units, basis_to_z_up=basis or T.IDENTITY,
                           occurrences={oid: SimpleNamespace(world=w) for oid, w in worlds.items()})


def revolute(origin, direction, lower=-180.0, upper=180.0):
    return {"kind": "revolute", "origin_mm": list(origin), "direction": list(direction), "lower": lower, "upper": upper, "unit": "deg"}


def prismatic(origin, direction, lower=0.0, upper=100.0):
    return {"kind": "prismatic", "origin_mm": list(origin), "direction": list(direction), "lower": lower, "upper": upper, "unit": "mm"}


def motion_of(named, moved, poses=None):
    return joints.Motion({}, named, moved, poses or {}, None, "")


# ------------------------------------------------------------------ what a joint does

def test_a_revolute_joint_turns_about_its_line_the_way_a_screw_advances():
    scene = scene_of()
    quarter = joints.transform(scene, revolute((10, 0, 0), (0, 0, 1)), 90.0)
    assert T.apply(quarter, [20.0, 0.0, 5.0]) == pytest.approx([10.0, 10.0, 5.0])        # counter-clockwise seen from +Z
    assert T.apply(quarter, [10.0, 0.0, -3.0]) == pytest.approx([10.0, 0.0, -3.0])       # a point on the line stays
    other_way = joints.transform(scene, revolute((10, 0, 0), (0, 0, -1)), 90.0)
    assert T.apply(other_way, [20.0, 0.0, 5.0]) == pytest.approx([10.0, -10.0, 5.0])
    # about a line that is not an axis: a third of a turn about the diagonal takes x to y, y to z, z to x
    d = 1 / math.sqrt(3)
    third = joints.transform(scene, revolute((0, 0, 0), (d, d, d)), 120.0)
    assert T.apply(third, [1.0, 0.0, 0.0]) == pytest.approx([0.0, 1.0, 0.0], abs=1e-12)
    for m in (quarter, other_way, third, joints.transform(scene, revolute((3, -4, 5), (0.6, 0.0, 0.8)), 37.0)):
        assert T.check_matrix(m) == m                                                    # rigid: no scale, no reflection
    assert T.close(joints.transform(scene, revolute((10, 0, 0), (0, 0, 1)), 0.0), T.IDENTITY)          # at zero nothing moves


def test_a_prismatic_joint_slides_along_its_line_in_millimetres_whatever_the_scene_s_units():
    assert T.apply(joints.transform(scene_of(), prismatic((7, 7, 7), (0, 0, 1)), 12.0), [1.0, 2.0, 3.0]) == pytest.approx([1.0, 2.0, 15.0])
    cm = scene_of("cm")
    assert T.apply(joints.transform(cm, prismatic((0, 0, 0), (1, 0, 0)), 12.0), [1.0, 2.0, 3.0]) == pytest.approx([2.2, 2.0, 3.0])
    # the line of a revolute joint is given in millimetres too: 100 mm is 10 of a scene in centimetres
    quarter = joints.transform(cm, revolute((100, 0, 0), (0, 0, 1)), 90.0)
    assert T.apply(quarter, [20.0, 0.0, 0.0]) == pytest.approx([10.0, 10.0, 0.0])


def test_a_joint_further_out_carries_the_joints_further_in():
    """An arm: a shoulder at the origin, an elbow 10 along it, a hand 20 along it, all turning about +Z."""
    scene = scene_of(upper=T.IDENTITY, hand=T.translate(20.0, 0.0, 0.0))
    arm = motion_of({"shoulder": revolute((0, 0, 0), (0, 0, 1)), "elbow": revolute((10, 0, 0), (0, 0, 1))},
                    {"upper": ["shoulder"], "hand": ["shoulder", "elbow"]})
    def hand(**at):
        return T.translation(joints.world(arm, scene, "hand", at))
    assert hand() == [20.0, 0.0, 0.0]
    assert hand(shoulder=90.0) == pytest.approx([0.0, 20.0, 0.0])
    assert hand(elbow=90.0) == pytest.approx([10.0, 10.0, 0.0])
    # both: the upper arm points along +Y, the elbow is at (0, 10), and the forearm is bent a quarter turn further
    assert hand(shoulder=90.0, elbow=90.0) == pytest.approx([-10.0, 10.0, 0.0])
    # the other order would turn the hand about the elbow's line where it lay before the shoulder moved it
    wrong = T.multiply(joints.transform(scene, arm.joints["elbow"], 90.0),
                       T.multiply(joints.transform(scene, arm.joints["shoulder"], 90.0), scene.occurrences["hand"].world))
    assert T.translation(wrong) == pytest.approx([-10.0, -10.0, 0.0])
    # the hand turns with the arm: a half turn in all leaves it facing the other way
    assert joints.world(arm, scene, "hand", {"shoulder": 90.0, "elbow": 90.0})[0][:3] == pytest.approx([-1.0, 0.0, 0.0])
    # what no joint moves is where the scene has it, and so is everything with every joint at zero
    still = scene_of(base=T.translate(1, 2, 3), hand=T.translate(20.0, 0.0, 0.0))
    assert joints.world(arm, still, "base", {"shoulder": 45.0}) == still.occurrences["base"].world
    assert joints.worlds(arm, scene, {}) == {"upper": T.IDENTITY, "hand": T.translate(20.0, 0.0, 0.0)}
    assert joints.moved_by(arm, "shoulder") == ["upper", "hand"] and joints.moved_by(arm, "elbow") == ["hand"]


def test_a_revolute_joint_carries_a_prismatic_one():
    """A slide on a turning arm goes out along the arm as it lies, not as it lay."""
    scene = scene_of(knob=T.translate(10.0, 0.0, 0.0))
    m = motion_of({"turn": revolute((0, 0, 0), (0, 0, 1)), "slide": prismatic((0, 0, 0), (1, 0, 0))}, {"knob": ["turn", "slide"]})
    assert T.translation(joints.world(m, scene, "knob", {"turn": 90.0, "slide": 5.0})) == pytest.approx([0.0, 15.0, 0.0])


def test_the_joints_of_a_scene_declared_y_up_are_turned_with_it():
    """The loader turns such a scene to +Z up once; a joint written in the scene's own frame has to follow."""
    y_up_to_z_up = [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    scene = scene_of(basis=y_up_to_z_up)
    # a slide along the scene's own up, +Y, is a slide along +Z of the loaded scene
    assert T.translation(joints.transform(scene, prismatic((0, 0, 0), (0, 1, 0)), 7.0)) == pytest.approx([0.0, 0.0, 7.0])
    # a turn about the vertical through native (10, 5, 0), which is (10, 0, 5) once turned
    quarter = joints.transform(scene, revolute((10, 5, 0), (0, 1, 0)), 90.0)
    assert T.apply(quarter, [20.0, 0.0, 5.0]) == pytest.approx([10.0, 10.0, 5.0])


def test_a_joint_that_follows_another_is_where_that_one_puts_it():
    """A lever's gear and the pinion it meshes with: the pinion turns two and a half times as far, the other way."""
    scene = scene_of(gear=T.translate(0.0, 0.0, 0.0), pinion=T.translate(0.0, 30.0, 0.0), mark=T.translate(5.0, 30.0, 0.0))
    lever = revolute((0, 0, 0), (0, 0, 1), -20.0, 35.0)
    pinion = dict(revolute((0, 30, 0), (0, 0, 1), -87.5, 50.0), follows={"joint": "lever", "ratio": -2.5})
    m = motion_of({"lever": lever, "pinion": pinion}, {"gear": ["lever"], "pinion": ["pinion"], "mark": ["pinion"]},
                  {"pressed": {"lever": 12.0}})
    assert joints.settled(m, {"lever": 10.0}) == {"lever": 10.0, "pinion": -25.0}
    assert joints.settled(m, {}) == {"lever": 0.0, "pinion": 0.0}
    # whatever else is said of it: a value given to a follower does not hold
    assert joints.settled(m, {"lever": 10.0, "pinion": 99.0})["pinion"] == -25.0
    assert joints.values(m, "pressed") == {"lever": 12.0, "pinion": -30.0}
    # with the lever at 36 the pinion has turned a quarter turn the other way: a mark 5 off its line along +X is 5 off along -Y
    assert T.translation(joints.world(m, scene, "mark", {"lever": 36.0})) == pytest.approx([0.0, 25.0, 0.0])
    assert T.translation(joints.worlds(m, scene, {"lever": 36.0})["mark"]) == pytest.approx([0.0, 25.0, 0.0])
    assert joints.followers(m, "lever") == ["pinion"] and joints.followers(m, "pinion") == []


def test_a_joint_in_several_places_is_meant_by_its_bare_name():
    hinge = revolute((0, 0, 0), (0, 0, 1))
    m = motion_of({"pin@FIXTURE ROOT:1/PIN PAIR:1": hinge, "pin@FIXTURE ROOT:1/PIN PAIR:2": hinge, "lid": hinge}, {})
    assert joints.meant(m, "pin") == ["pin@FIXTURE ROOT:1/PIN PAIR:1", "pin@FIXTURE ROOT:1/PIN PAIR:2"]
    assert joints.meant(m, "pin@FIXTURE ROOT:1/PIN PAIR:2") == ["pin@FIXTURE ROOT:1/PIN PAIR:2"]
    assert joints.meant(m, "lid") == ["lid"] and joints.meant(m, "door") == []


def test_where_the_joints_are_for_a_picture_is_zero_a_pose_or_what_is_given(project_copy):
    """A still takes `--pose NAME` and `--at JOINT=VALUE,...`: the pose, and over it the values that are given."""
    path, scene = write(project_copy)
    m = joints.load(path, scene)
    assert joints.where(m) == {"swing": 0.0, "lift": 0.0, "sink": 0.0}
    assert joints.where(m, "open") == joints.values(m, "open")
    assert joints.where(m, "open", {"lift": 5}) == {"swing": 60.0, "lift": 5.0, "sink": -6.0}      # the follower from the swing
    assert joints.where(m, at=joints.given("swing=-30, lift = 2.5")) == {"swing": -30.0, "lift": 2.5, "sink": 3.0}
    assert joints.given("") == {} and joints.given(None) == {}
    assert joints.given("pin@ROOT:1/PAIR:1=2") == {"pin@ROOT:1/PAIR:1": 2.0}       # a name may hold what a place holds
    with pytest.raises(joints.PoseError, match="'lift': expected JOINT=VALUE with a number"):
        joints.given("lift")
    with pytest.raises(joints.PoseError, match="expected JOINT=VALUE with a number"):
        joints.given("=3")
    with pytest.raises(joints.PoseError, match="no pose 'ajar'; motion.json has closed, open"):
        joints.where(m, "ajar")
    with pytest.raises(joints.PoseError, match="'door' is not a joint of motion.json; it has lift, sink, swing"):
        joints.where(m, at={"door": 1})
    with pytest.raises(joints.PoseError, match="'sink' follows 'swing' and is where that joint puts it; say where that joint is"):
        joints.where(m, at={"sink": 1})
    with pytest.raises(joints.PoseError, match="lift = 21 mm is outside the joint's limits, 0 to 20"):
        joints.where(m, "open", {"lift": 21})


def test_a_joint_in_several_places_is_given_by_its_bare_name_for_all_of_them():
    hinge = dict(revolute((0, 0, 0), (0, 0, 1)), lower=-10.0, upper=10.0)
    m = motion_of({"pin@A:1": hinge, "pin@A:2": hinge, "lid": hinge}, {})
    assert joints.where(m, at={"pin": 4}) == {"pin@A:1": 4.0, "pin@A:2": 4.0, "lid": 0.0}
    assert joints.where(m, at={"pin@A:2": -4, "lid": 1}) == {"pin@A:1": 0.0, "pin@A:2": -4.0, "lid": 1.0}


# ------------------------------------------------------------------ the file

def test_the_file_is_read_against_its_scene(project_copy):
    path, scene = write(project_copy)
    m = joints.load(path, scene)
    assert set(m.joints) == {"swing", "lift", "sink"} and m.joints["lift"]["unit"] == "mm"
    assert m.joints["sink"]["follows"] == {"joint": "swing", "ratio": -0.1} and "follows" not in m.joints["swing"]
    assert m.moved == {"pin-a": ["swing", "lift"], "pin-b": ["swing", "sink"]}
    assert m.poses == {"open": {"swing": 60.0, "lift": 20.0}, "closed": {"swing": -30.0}}
    assert m.source["kind"] == "mechanical-cad-motion" and len(m.sha256) == 64 and m.file == path
    # a pose gives every joint a value: the ones it does not name are at zero, a follower is where the joint it
    # follows puts it, and without a pose every joint is at zero
    assert joints.values(m, "closed") == {"swing": -30.0, "lift": 0.0, "sink": 3.0}
    assert joints.values(m, "open") == {"swing": 60.0, "lift": 20.0, "sink": -6.0}
    assert joints.values(m) == {"swing": 0.0, "lift": 0.0, "sink": 0.0}
    with pytest.raises(joints.PoseError, match="no pose 'ajar'; motion.json has closed, open"):
        joints.values(m, "ajar")
    # the pins are 25 either side of the middle; a quarter turn of the swing puts them on the other axis, the
    # one lifted as far as it was told and the other 9 down, a tenth of a millimetre for every degree
    at = {"swing": 90.0, "lift": 20.0}
    assert T.translation(joints.world(m, scene, "pin-b", at)) == pytest.approx([0.0, 25.0, -9.0])
    assert T.translation(joints.world(m, scene, "pin-a", at)) == pytest.approx([0.0, -25.0, 20.0])
    assert joints.world(m, scene, "base-1", at) == scene.occurrences["base-1"].world


def test_a_file_without_poses_or_without_a_source_is_whole(project_copy):
    path, scene = write(project_copy, lambda d: (d.pop("poses"), d.pop("source")))
    m = joints.load(path, scene)
    assert m.poses == {} and m.source == {} and joints.values(m) == {"swing": 0.0, "lift": 0.0, "sink": 0.0}
    path, scene = write(project_copy, lambda d: d.update(poses={"rest": {}}))
    assert joints.values(joints.load(path, scene), "rest") == {"swing": 0.0, "lift": 0.0, "sink": 0.0}


@pytest.mark.parametrize("change, said", [
    (lambda d: d.update(schema_version=2), "schema_version must be the integer 1"),
    (lambda d: d.update(schema_version=True), "schema_version must be the integer 1"),
    (lambda d: d.update(scene="other.json"), "is not the loaded scene"),
    (lambda d: d.update(views={}), r"unsupported field\(s\) \['views'\]"),
    (lambda d: d.pop("moved"), "missing field 'moved'"),
    (lambda d: d["moved"].update({"pin-c": ["swing"]}), "moved\\['pin-c'\\]: not an occurrence of the scene"),
    (lambda d: d["moved"].update({"pin-b": ["swing", "tilt"]}), r"moved\['pin-b'\]: \['tilt'\] is not among the joints"),
    (lambda d: d["moved"].update({"pin-b": []}), r"moved\['pin-b'\]: expected the names of the joints"),
    (lambda d: d["moved"].update({"pin-b": ["swing", "swing"]}), "a joint moves an occurrence once"),
    (lambda d: d["poses"]["open"].update(tilt=3.0), r"poses\['open'\]: 'tilt' is not among the joints"),
    (lambda d: d["poses"]["open"].update(swing=60.5), r"poses\['open'\]\['swing'\]: 60.5 is outside the joint's limits, -30 to 60 deg"),
    (lambda d: d["poses"]["open"].update(lift="up"), r"poses\['open'\]\['lift'\]: expected a number"),
    (lambda d: d["joints"]["lift"].update(lower=20.0), "lower must be below upper"),
    (lambda d: d["joints"]["lift"].update(upper=float("inf")), "lower and upper are numbers"),
    (lambda d: d["joints"]["swing"].update(direction=[0.0, 0.0, 2.0]), "expected a unit vector"),
    (lambda d: d["joints"]["swing"].update(direction=[0.0, 1.0]), "direction: expected three numbers"),
    (lambda d: d["joints"]["swing"].update(origin_mm="middle"), "origin_mm: expected three numbers"),
    (lambda d: d["joints"]["swing"].update(kind="hinge"), r"kind: expected one of \['prismatic', 'revolute'\]"),
    (lambda d: d["joints"]["swing"].update(unit="rad"), "a revolute joint is measured in 'deg'"),
    (lambda d: d["joints"]["lift"].update(unit="deg"), "a prismatic joint is measured in 'mm'"),
    (lambda d: d["joints"]["lift"].pop("lower"), r"missing field\(s\) \['lower'\]"),
    (lambda d: d["joints"]["lift"].update(parent="swing"), r"unsupported field\(s\) \['parent'\]"),
    # a joint that follows another: which one, and how far it goes for one unit of it
    (lambda d: d["joints"]["sink"].update(follows="swing"), r"joints\['sink'\].follows: expected the joint it follows and the ratio"),
    (lambda d: d["joints"]["sink"]["follows"].update(ratio=0), "a number that is not 0"),
    (lambda d: d["joints"]["sink"]["follows"].update(ratio="1:10"), "a number that is not 0"),
    (lambda d: d["joints"]["sink"]["follows"].update(gear="spur"), "expected the joint it follows and the ratio"),
    (lambda d: d["joints"]["sink"]["follows"].update(joint="tilt"), r"follows: 'tilt' is not among the joints"),
    (lambda d: d["joints"]["lift"].update(follows={"joint": "sink", "ratio": 2.0}, lower=-12.0, upper=6.0),
     r"joints\['lift'\].follows: 'sink' follows a joint itself"),
    (lambda d: d["joints"]["sink"]["follows"].update(joint="sink"), "'sink' follows a joint itself"),
    (lambda d: d["joints"]["sink"].update(lower=-3.0, upper=6.0), "it follows 'swing' at -0.1 to one, so its limits are -6 to 3 mm, got -3 to 6"),
    (lambda d: d["poses"]["open"].update(sink=-6.0), r"poses\['open'\]: 'sink' follows 'swing' and is where that joint puts it"),
])
def test_what_is_wrong_with_a_file_is_said(project_copy, change, said):
    path, scene = write(project_copy, change)
    with pytest.raises(joints.MotionError, match=said):
        joints.load(path, scene)


def test_every_problem_is_said_at_once_and_a_file_that_is_not_there_is_one(project_copy):
    def change(d):
        d["joints"]["lift"]["direction"] = [1.0, 1.0, 0.0]
        d["moved"]["nobody"] = ["swing"]
        d["poses"]["closed"]["swing"] = -31.0
    path, scene = write(project_copy, change)
    with pytest.raises(joints.MotionError) as e:
        joints.load(path, scene)
    assert len(e.value.problems) == 3 and str(e.value).startswith("invalid motion.json:")
    path.unlink()
    with pytest.raises(joints.MotionError, match="file not found"):
        joints.load(path, scene)
    path.write_text("{ not json")
    with pytest.raises(joints.MotionError, match="cannot parse"):
        joints.load(path, scene)


def test_a_scene_reads_as_before_with_the_file_beside_it(project_copy, fixture_dir):
    """motion.json is nobody's input but a joint's or a pose's video: the hashes a manual is built on do not see it."""
    from mechanical_docs.manifest import load_project
    before = load_project(fixture_dir).input_hashes()
    write(project_copy)
    assert load_project(project_copy.dir).input_hashes() == before
