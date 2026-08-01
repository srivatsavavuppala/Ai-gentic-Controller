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


class _FakeStreamSocket:
    """Simulates a TCP stream with pre-queued bytes -- recv() drains it
    incrementally, and raises BlockingIOError once exhausted while in
    non-blocking mode (mirroring real socket semantics)."""

    def __init__(self, data: bytes):
        self._data = data
        self._blocking = True

    def setblocking(self, value):
        self._blocking = value

    def recv(self, bufsize):
        if not self._data:
            if self._blocking:
                return b""  # mirrors a real closed socket
            raise BlockingIOError()  # mirrors "no more data available right now"
        chunk = self._data[:bufsize]
        self._data = self._data[len(chunk) :]
        return chunk


def _frame_bytes(race_time_ms: int) -> bytes:
    return struct.pack(_TELEMETRY_FORMAT, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, race_time_ms)


def test_read_state_returns_latest_frame_draining_any_backlog():
    # Three frames arrive before we ever call read_state() -- must return
    # the last one (race_time_ms=3000), not the first (a stale backlog).
    queued = _frame_bytes(1000) + _frame_bytes(2000) + _frame_bytes(3000)
    bridge = object.__new__(TrackmaniaBridge)
    bridge._sock = _FakeStreamSocket(queued)
    bridge._recv_buffer = b""

    state = bridge.read_state()

    assert state.race_time_ms == 3000


def test_read_state_keeps_partial_trailing_bytes_for_next_call():
    # A full frame plus a partial next frame -- the partial bytes must be
    # preserved in the buffer, not discarded, so the next call reassembles
    # it correctly instead of desyncing the stream.
    partial_next = _frame_bytes(2000)[:10]
    queued = _frame_bytes(1000) + partial_next
    bridge = object.__new__(TrackmaniaBridge)
    bridge._sock = _FakeStreamSocket(queued)
    bridge._recv_buffer = b""

    first = bridge.read_state()
    assert first.race_time_ms == 1000
    assert bridge._recv_buffer == partial_next

    # Now the rest of the second frame arrives.
    bridge._sock = _FakeStreamSocket(_frame_bytes(2000)[10:])
    second = bridge.read_state()
    assert second.race_time_ms == 2000
    assert bridge._recv_buffer == b""


def test_read_state_raises_on_closed_socket_with_no_data():
    bridge = object.__new__(TrackmaniaBridge)
    bridge._sock = _FakeStreamSocket(b"")
    bridge._recv_buffer = b""

    try:
        bridge.read_state()
        raise AssertionError("expected ConnectionError")
    except ConnectionError:
        pass
