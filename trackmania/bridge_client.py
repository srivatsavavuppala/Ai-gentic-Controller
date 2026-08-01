"""Python side of the ApexMind <-> TrackMania Nations Forever bridge.

Talks to `ApexMindBridge.as` (copy that file into
Documents\\TMInterface\\Plugins\\) over a local TCP socket -- the plugin
listens on 127.0.0.1:9000, we connect as the client, matching how
TMInterface's own (now-removed) Python API worked.

Wire protocol (little-endian), must match ApexMindBridge.as exactly:
    Telemetry frame (plugin -> us), every tick, 32 bytes:
        float posX, posY, posZ, velX, velY, velZ, speed; int32 raceTimeMs
    Control frame (us -> plugin), 12 bytes:
        int32 steer, int32 gas, int32 reset
        (steer/gas each in [-65536, 65536]; reset != 0 triggers an
        in-game Respawn() instead of applying steer/gas that tick)
"""

import socket
import struct
from dataclasses import dataclass

from control.schema import ControlFrame

_TELEMETRY_FORMAT = "<7fi"
_TELEMETRY_SIZE = struct.calcsize(_TELEMETRY_FORMAT)
_CONTROL_FORMAT = "<3i"
_STEER_GAS_RANGE = 65536


@dataclass
class TrackmaniaState:
    pos_x: float
    pos_y: float
    pos_z: float
    vel_x: float
    vel_y: float
    vel_z: float
    speed: float
    race_time_ms: int


class TrackmaniaBridge:
    def __init__(self, host: str = "127.0.0.1", port: int = 9000, timeout: float = 10.0):
        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._sock.settimeout(None)
        self._recv_buffer = b""

    def read_state(self) -> TrackmaniaState:
        buf = self._recv_latest_frame()
        values = struct.unpack(_TELEMETRY_FORMAT, buf)
        return TrackmaniaState(*values)

    def _recv_latest_frame(self) -> bytes:
        """Returns the MOST RECENT telemetry frame, draining any backlog --
        same lesson learned from the DualSense controller earlier in this
        project: reading one frame at a time without draining falls further
        behind real time on every call once Python's loop is faster than
        the game's tick rate, or any backlog accumulates. A plain recv loop
        would silently train on stale, lagged state."""
        while len(self._recv_buffer) < _TELEMETRY_SIZE:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("TrackMania bridge socket closed unexpectedly")
            self._recv_buffer += chunk

        self._sock.setblocking(False)
        try:
            while True:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                self._recv_buffer += chunk
        except BlockingIOError:
            pass
        finally:
            self._sock.setblocking(True)

        num_complete = len(self._recv_buffer) // _TELEMETRY_SIZE
        latest_start = (num_complete - 1) * _TELEMETRY_SIZE
        frame = self._recv_buffer[latest_start : latest_start + _TELEMETRY_SIZE]
        self._recv_buffer = self._recv_buffer[num_complete * _TELEMETRY_SIZE :]
        return frame

    def send_control(self, frame: ControlFrame) -> None:
        """Maps our shared ControlFrame onto TrackMania's single combined
        gas axis (throttle - brake) and its steer axis, each scaled to the
        game's native [-65536, 65536] integer range.

        Confirmed live (2026-08-01): positive InputType::Gas is REVERSE, not
        forward -- opposite of the usual racing-game convention we assumed.
        Hence the negation below."""
        steer = self._to_native_range(frame.steering)
        gas = self._to_native_range(-(frame.throttle - frame.brake))
        self._sock.sendall(struct.pack(_CONTROL_FORMAT, steer, gas, 0))

    def send_reset(self) -> None:
        """Triggers an in-game Respawn() -- lets a training/driving loop
        recover from a crash without a human pressing backspace."""
        self._sock.sendall(struct.pack(_CONTROL_FORMAT, 0, 0, 1))

    @staticmethod
    def _to_native_range(value: float) -> int:
        clipped = max(-1.0, min(1.0, value))
        return int(clipped * _STEER_GAS_RANGE)

    def close(self) -> None:
        self._sock.close()
