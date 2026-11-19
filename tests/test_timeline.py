"""Moving pictures without Blender: where a turntable's camera stands, the scale that holds a whole turn, how far
apart an exploded sequence is at each frame, and where a step's additions come from."""
import math

import pytest

from mechanical_docs import timeline, views
from mechanical_docs.manifest import load_project
from mechanical_docs.procedure import derive_states


def test_a_movement_starts_and_ends_slowly():
    assert timeline.smooth(0) == 0.0 and timeline.smooth(1) == 1.0 and timeline.smooth(0.5) == 0.5
    assert timeline.smooth(-3) == 0.0 and timeline.smooth(7) == 1.0                  # never beyond its ends
    steps = [timeline.smooth(k / 10) for k in range(11)]
    assert steps == sorted(steps)
    assert steps[1] - steps[0] < steps[5] - steps[4] > steps[10] - steps[9]         # slow, fast, slow
    assert timeline.smooth(0.25) + timeline.smooth(0.75) == pytest.approx(1.0)       # the same going as coming


def test_a_turntable_goes_once_round_and_closes():
    path = timeline.turntable(8)
    assert len(path) == 8 and path[0][0] == 0.0
    # the first frame is where the view `iso` stands, the camera's height never changes
    first, iso = path[0][1], views.stands("iso")[0]
    n = math.sqrt(sum(c * c for c in iso))
    assert first == pytest.approx([c / n for c in iso])
    assert all(stands[2] == pytest.approx(first[2]) for _, stands in path)
    assert all(sum(c * c for c in stands) == pytest.approx(1.0) for _, stands in path)
    # counter-clockwise seen from above: a quarter of a turn takes (+x, -y) to (+x, +y), half a turn to the far side
    assert path[2][0] == pytest.approx(math.pi / 2) and path[2][1][:2] == pytest.approx([first[0], -first[1]])
    assert path[4][1][:2] == pytest.approx([-first[0], -first[1]])
    # the last frame is one step short of the first, so the turn closes when it is played again
    assert path[-1][0] == pytest.approx(2 * math.pi * 7 / 8)
    level = timeline.turntable(4, elevation_deg=0.0, start_deg=0.0)
    assert [tuple(round(c, 9) for c in stands) for _, stands in level] == [(1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0)]
    for wrong in (0, -3, 2.5, True):
        with pytest.raises(timeline.TimelineError, match="frames"):
            timeline.turntable(wrong)
    with pytest.raises(timeline.TimelineError, match="elevation"):
        timeline.turntable(8, elevation_deg=90.0)


def test_a_camera_s_axes_are_those_the_renderer_gives_it():
    # standing at +X and looking back with Z up: +Y runs to the right, +Z upwards
    assert timeline.camera_axes((1, 0, 0)) == ([0.0, 1.0, 0.0], [0.0, 0.0, 1.0])
    assert timeline.camera_axes((0, -5, 0)) == ([1.0, 0.0, 0.0], [0.0, 0.0, 1.0])
    # straight above with Y up it is a plan: X to the right, Y upwards
    right, up = timeline.camera_axes((0, 0, 1), (0, 1, 0))
    assert right == pytest.approx([1.0, 0.0, 0.0]) and up == pytest.approx([0.0, 1.0, 0.0])
    with pytest.raises(timeline.TimelineError, match="up axis"):
        timeline.camera_axes((0, 0, 1))
    with pytest.raises(timeline.TimelineError, match="stand somewhere"):
        timeline.camera_axes((0, 0, 0))


def test_one_scale_holds_everything_all_the_way_round():
    # a bar 4 long, 1 wide and 1 high about the origin: seen along its length it is 1 wide, across it 4 wide
    points = [(x, y, z) for x in (-2, 2) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
    along = timeline.ortho_scale(points, (0, 0, 0), [((1, 0, 0), timeline.UP)], 400, 300, 1.0)
    across = timeline.ortho_scale(points, (0, 0, 0), [((0, 1, 0), timeline.UP)], 400, 300, 1.0)
    assert along == pytest.approx(max(1.0, 1.0 * 400 / 300)) and across == pytest.approx(4.0)
    level = [(stands, timeline.UP) for _, stands in timeline.turntable(72, elevation_deg=0.0)]
    whole = timeline.ortho_scale(points, (0, 0, 0), level, 400, 300, 1.0)
    assert whole == pytest.approx(2 * math.hypot(2, 0.5), rel=1e-3)          # the diagonal of its plan, seen square on
    assert whole >= across and timeline.ortho_scale(points, (0, 0, 0), level, 400, 300, 0.8) == pytest.approx(whole / 0.8)
    # an upright picture spans its scale from top to bottom
    assert timeline.ortho_scale(points, (0, 0, 0), [((0, 1, 0), timeline.UP)], 300, 400, 1.0) == pytest.approx(4.0 * 400 / 300)
    # the middle of the picture is the target: a point twice as far to one side asks for twice the scale
    assert timeline.ortho_scale([(3, 0, 0)], (1, 0, 0), [((0, -1, 0), timeline.UP)], 400, 300, 1.0) == pytest.approx(4.0)
    with pytest.raises(timeline.TimelineError, match="nothing to frame"):
        timeline.ortho_scale([], (0, 0, 0), level, 400, 300, 1.0)
    with pytest.raises(timeline.TimelineError, match="fill"):
        timeline.ortho_scale(points, (0, 0, 0), level, 400, 300, 0.0)


def test_an_exploded_sequence_rests_moves_apart_rests_and_may_come_back():
    out = timeline.exploded_fractions(4, 2)
    assert out == [0.0, 0.0, timeline.smooth(0.25), 0.5, timeline.smooth(0.75), 1.0, 1.0, 1.0]
    back = timeline.exploded_fractions(4, 2, back=True)
    assert back[:8] == out and back[8:] == [timeline.smooth(0.75), 0.5, timeline.smooth(0.25)]
    assert back[-1] > back[0]                                    # one frame short of the first: it closes when played again
    assert timeline.exploded_fractions(1, 0) == [1.0]
    with pytest.raises(timeline.TimelineError, match="frames"):
        timeline.exploded_fractions(0, 2)
    with pytest.raises(timeline.TimelineError, match="hold"):
        timeline.exploded_fractions(4, -1)
    assert timeline.duration_s(len(back), 24) == pytest.approx(11 / 24)


def test_each_step_brings_its_additions_in_and_lets_them_rest():
    frames = timeline.step_frames(2, 3, 2)
    assert frames == [(0, 0.0), (0, timeline.smooth(1 / 3)), (0, timeline.smooth(2 / 3)), (0, 1.0), (0, 1.0),
                      (1, 0.0), (1, timeline.smooth(1 / 3)), (1, timeline.smooth(2 / 3)), (1, 1.0), (1, 1.0)]
    with pytest.raises(timeline.TimelineError, match="hold"):
        timeline.step_frames(2, 3, 0)                            # a step's additions are seen seated at least once
    with pytest.raises(timeline.TimelineError, match="steps"):
        timeline.step_frames(0, 3, 2)


def test_where_a_step_s_additions_come_from(fixture_dir, project_copy):
    project = load_project(fixture_dir)
    states = derive_states(project.instructions, project.scene)
    exploded = {"pin-pair": [0.0, 0.0, 30.0], "root-parts": [0.0, 0.0, -11.0]}
    starts = timeline.step_starts(project.scene, states, exploded, 50.0)
    # the pins have approach hints, 40 above their seats; the base has none and comes from where the exploded view has it
    assert starts == {"base-1": ([0.0, 0.0, -11.0], "exploded"), "pin-a": ([0.0, 0.0, 40.0], "approach"),
                      "pin-b": ([0.0, 0.0, 40.0], "approach")}
    # a group that does not move in the exploded view, or no exploded view at all: straight up by the lift
    still = timeline.step_starts(project.scene, states, {"pin-pair": [0.0, 0.0, 30.0], "root-parts": [0.0, 0.0, 0.0]}, 50.0)
    assert still["base-1"] == ([0.0, 0.0, 50.0], "lift")
    assert timeline.step_starts(project.scene, states, {}, 50.0)["base-1"] == ([0.0, 0.0, 50.0], "lift")
    # a hint is for one occurrence: without it the pin comes with its group
    project_copy.edit("instructions.json", lambda d: d["steps"][1].pop("approach"))
    project = load_project(project_copy.dir)
    starts = timeline.step_starts(project.scene, derive_states(project.instructions, project.scene), exploded, 50.0)
    assert starts["pin-a"] == ([0.0, 0.0, 30.0], "exploded") and starts["pin-b"][1] == "approach"
    assert set(s for _, s in starts.values()) <= set(timeline.SOURCES)


def test_an_approach_offset_is_in_the_scene_s_units():
    """The two-bases fixture is written in centimetres; a hint of 4 there is 40 mm."""
    from pathlib import Path
    project = load_project(Path(__file__).resolve().parents[1] / "examples" / "two-bases-fixture")
    states = derive_states(project.instructions, project.scene)
    hinted = [st for st in states if st.step.approach is not None]
    if not hinted:
        pytest.skip("the two-bases fixture has no approach hint")
    starts = timeline.step_starts(project.scene, states, {}, 50.0)
    ap = hinted[0].step.approach
    assert project.scene.units == "cm"
    assert starts[ap.occurrence_id] == ([10.0 * v for v in ap.start_offset], "approach")
