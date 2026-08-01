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


class _FakeSocket:
    def __init__(self):
        self.sent = b""

    def sendall(self, data):
        self.sent += data


def _bridge_with_fake_socket():
    bridge = object.__new__(TrackmaniaBridge)
    bridge._sock = _FakeSocket()
    return bridge


def test_full_throttle_sends_negative_gas():
    # Confirmed live (2026-08-01): positive InputType::Gas is reverse, so
    # full throttle must send a NEGATIVE gas value, not positive.
    bridge = _bridge_with_fake_socket()
    bridge.send_control(ControlFrame(steering=0.0, throttle=1.0, brake=0.0))
    _steer, gas, _reset = struct.unpack(_CONTROL_FORMAT, bridge._sock.sent)
    assert gas == -65536


def test_full_brake_sends_positive_gas():
    bridge = _bridge_with_fake_socket()
    bridge.send_control(ControlFrame(steering=0.0, throttle=0.0, brake=1.0))
    _steer, gas, _reset = struct.unpack(_CONTROL_FORMAT, bridge._sock.sent)
    assert gas == 65536


def test_send_reset_sets_reset_flag():
    bridge = _bridge_with_fake_socket()
    bridge.send_reset()
    steer, gas, reset = struct.unpack(_CONTROL_FORMAT, bridge._sock.sent)
    assert (steer, gas, reset) == (0, 0, 1)


def test_control_wire_format_packs_three_int32s():
    packed = struct.pack(_CONTROL_FORMAT, 32768, -16384, 0)
    assert struct.unpack(_CONTROL_FORMAT, packed) == (32768, -16384, 0)
