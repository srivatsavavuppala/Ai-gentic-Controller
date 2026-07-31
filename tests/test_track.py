import numpy as np

from sim_env.track import Track, generate_oval_track


def _square_track():
    # Simple 100x100 closed-loop square, counterclockwise, width 10.
    centerline = np.array([[0, 0], [100, 0], [100, 100], [0, 100]])
    return Track(centerline, width=10.0)


def test_total_length_of_square():
    track = _square_track()
    assert track.total_length == 400.0


def test_point_on_centerline_has_zero_lateral_offset():
    track = _square_track()
    progress, lateral, _heading, seg = track.locate((50, 0))
    assert progress == 50.0
    assert abs(lateral) < 1e-9
    assert seg == 0


def test_point_to_the_left_has_positive_lateral_offset():
    track = _square_track()
    # travelling in +x on the bottom edge, "left" is +y
    _, lateral, _, _ = track.locate((50, 5))
    assert lateral > 0


def test_point_to_the_right_has_negative_lateral_offset():
    track = _square_track()
    _, lateral, _, _ = track.locate((50, -5))
    assert lateral < 0


def test_progress_wraps_around_closed_loop():
    track = _square_track()
    # (0, 99) sits just past the (0, 100) corner along the left edge (segment
    # 3 runs from (0,100) to (0,0)), so progress should be just past 300, not
    # near the full 400 -- the corner itself is progress=300.
    progress, _, _, seg = track.locate((0, 99))
    assert seg == 3
    assert 300 <= progress < 310


def test_oval_track_is_closed_and_reasonably_sized():
    track = generate_oval_track(straight_length=200.0, radius=60.0)
    # two straights + two semicircles
    expected = 2 * 200.0 + 2 * np.pi * 60.0
    assert abs(track.total_length - expected) < 5.0
