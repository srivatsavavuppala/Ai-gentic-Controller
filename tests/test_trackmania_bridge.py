import struct

from control.schema import ControlFrame
from trackmania.bridge_client import (
    _CONTROL_FORMAT,
    _TELEMETRY_FORMAT,
    TrackmaniaBridge,
    TrackmaniaState,
)


def test_telemetry_format_matches_dataclass_field_count():
    dummy = struct.pack(_TELEMETRY_FORMAT, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8)
    values = struct.unpack(_TELEMETRY_FORMAT, dummy)
    state = TrackmaniaState(*values)
    assert state.pos_x == 1.0
    assert state.race_time_ms == 8


def test_full_right_steering_maps_to_positive_max():
    assert TrackmaniaBridge._to_native_range(1.0) == 65536


def test_full_left_steering_maps_to_negative_max():
    assert TrackmaniaBridge._to_native_range(-1.0) == -65536


def test_steering_out_of_range_is_clipped():
    assert TrackmaniaBridge._to_native_range(2.5) == 65536
    assert TrackmaniaBridge._to_native_range(-2.5) == -65536


def test_control_frame_gas_combines_throttle_and_brake():
    # Full throttle, no brake -> gas should map to full positive range.
    frame = ControlFrame(steering=0.0, throttle=1.0, brake=0.0)
    gas_value = TrackmaniaBridge._to_native_range(frame.throttle - frame.brake)
    assert gas_value == 65536

    # Full brake, no throttle -> full negative range.
    frame = ControlFrame(steering=0.0, throttle=0.0, brake=1.0)
    gas_value = TrackmaniaBridge._to_native_range(frame.throttle - frame.brake)
    assert gas_value == -65536


def test_control_wire_format_packs_three_int32s():
    packed = struct.pack(_CONTROL_FORMAT, 32768, -16384, 0)
    assert struct.unpack(_CONTROL_FORMAT, packed) == (32768, -16384, 0)
