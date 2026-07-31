from control.dualsense_hid import parse_report


def _report(lx=128, ly=128, rx=128, ry=128, l2=0, r2=0):
    # index 0 is the HID report ID; only indices 1-6 matter to parse_report.
    return bytes([1, lx, ly, rx, ry, l2, r2] + [0] * 57)


def test_centered_stick_and_untouched_triggers_read_as_zero():
    frame = parse_report(_report())
    assert frame.steering == 0.0
    assert frame.throttle == 0.0
    assert frame.brake == 0.0


def test_full_right_trigger_is_full_throttle():
    frame = parse_report(_report(r2=255))
    assert frame.throttle == 1.0


def test_full_left_trigger_is_full_brake():
    frame = parse_report(_report(l2=255))
    assert frame.brake == 1.0


def test_stick_deadzone_swallows_small_offsets():
    # 128 +/- 3 is well inside the default deadzone (0.05 * 127 ~= 6).
    frame = parse_report(_report(lx=130))
    assert frame.steering == 0.0


def test_stick_past_deadzone_reads_proportionally():
    frame = parse_report(_report(lx=128 + 64))  # halfway to full right
    assert 0.4 < frame.steering < 0.6


def test_stick_extremes_clip_to_unit_range():
    assert parse_report(_report(lx=255)).steering == 1.0
    assert parse_report(_report(lx=0)).steering == -1.0
