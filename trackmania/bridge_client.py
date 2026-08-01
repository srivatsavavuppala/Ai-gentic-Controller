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

    def read_state(self) -> TrackmaniaState:
        buf = self._recv_exact(_TELEMETRY_SIZE)
        values = struct.unpack(_TELEMETRY_FORMAT, buf)
        return TrackmaniaState(*values)

    def send_control(self, frame: ControlFrame) -> None:
        """Maps our shared ControlFrame onto TrackMania's single combined
        gas axis (throttle - brake) and its steer axis, each scaled to the
        game's native [-65536, 65536] integer range."""
        steer = self._to_native_range(frame.steering)
        gas = self._to_native_range(frame.throttle - frame.brake)
        self._sock.sendall(struct.pack(_CONTROL_FORMAT, steer, gas, 0))

    def send_reset(self) -> None:
        """Triggers an in-game Respawn() -- lets a training/driving loop
        recover from a crash without a human pressing backspace."""
        self._sock.sendall(struct.pack(_CONTROL_FORMAT, 0, 0, 1))

    @staticmethod
    def _to_native_range(value: float) -> int:
        clipped = max(-1.0, min(1.0, value))
        return int(clipped * _STEER_GAS_RANGE)

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("TrackMania bridge socket closed unexpectedly")
            buf += chunk
        return buf

    def close(self) -> None:
        self._sock.close()
