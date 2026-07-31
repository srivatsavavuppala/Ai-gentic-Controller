"""Reader for Assetto Corsa's shared-memory telemetry (Windows only).

AC writes three named shared-memory pages while running: physics, graphics,
and static session info (see config.SHARED_MEMORY_NAMES). This module maps
those pages with ctypes and normalizes them into TelemetryFrame.

NOTE: the struct layouts below are transcribed from the publicly documented
AC shared-memory format (the same one third-party overlay tools like SimHub
use). Verify field offsets against the official headers shipped with the
game (under the game install's SDK/python app folder) before relying on this
for real training data -- a single wrong field type shifts every offset
after it.
"""

import ctypes
import mmap
import time

from config import SHARED_MEMORY_NAMES
from telemetry.schema import TelemetryFrame


class SPageFilePhysics(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("gas", ctypes.c_float),
        ("brake", ctypes.c_float),
        ("fuel", ctypes.c_float),
        ("gear", ctypes.c_int),
        ("rpms", ctypes.c_int),
        ("steerAngle", ctypes.c_float),
        ("speedKmh", ctypes.c_float),
        ("velocity", ctypes.c_float * 3),
        ("accG", ctypes.c_float * 3),
        ("wheelSlip", ctypes.c_float * 4),
        ("wheelLoad", ctypes.c_float * 4),
        ("wheelsPressure", ctypes.c_float * 4),
        ("wheelAngularSpeed", ctypes.c_float * 4),
        ("tyreWear", ctypes.c_float * 4),
        ("tyreDirtyLevel", ctypes.c_float * 4),
        ("tyreCoreTemperature", ctypes.c_float * 4),
        ("camberRAD", ctypes.c_float * 4),
        ("suspensionTravel", ctypes.c_float * 4),
        ("drs", ctypes.c_float),
        ("tc", ctypes.c_float),
        ("heading", ctypes.c_float),
        ("pitch", ctypes.c_float),
        ("roll", ctypes.c_float),
        ("cgHeight", ctypes.c_float),
        ("carDamage", ctypes.c_float * 5),
        ("numberOfTyresOut", ctypes.c_int),
        ("pitLimiterOn", ctypes.c_int),
        ("abs", ctypes.c_float),
    ]


class SPageFileGraphic(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("status", ctypes.c_int),
        ("session", ctypes.c_int),
        ("currentTime", ctypes.c_wchar * 15),
        ("lastTime", ctypes.c_wchar * 15),
        ("bestTime", ctypes.c_wchar * 15),
        ("split", ctypes.c_wchar * 15),
        ("completedLaps", ctypes.c_int),
        ("position", ctypes.c_int),
        ("iCurrentTime", ctypes.c_int),
        ("iLastTime", ctypes.c_int),
        ("iBestTime", ctypes.c_int),
        ("sessionTimeLeft", ctypes.c_float),
        ("distanceTraveled", ctypes.c_float),
        ("isInPit", ctypes.c_int),
        ("currentSectorIndex", ctypes.c_int),
        ("lastSectorTime", ctypes.c_int),
        ("numberOfLaps", ctypes.c_int),
        ("tyreCompound", ctypes.c_wchar * 33),
        ("replayTimeMultiplier", ctypes.c_float),
        ("normalizedCarPosition", ctypes.c_float),
    ]


class SPageFileStatic(ctypes.Structure):
    _fields_ = [
        ("smVersion", ctypes.c_wchar * 15),
        ("acVersion", ctypes.c_wchar * 15),
        ("numberOfSessions", ctypes.c_int),
        ("numCars", ctypes.c_int),
        ("carModel", ctypes.c_wchar * 33),
        ("track", ctypes.c_wchar * 33),
        ("playerName", ctypes.c_wchar * 33),
        ("playerSurname", ctypes.c_wchar * 33),
        ("playerNick", ctypes.c_wchar * 33),
        ("sectorCount", ctypes.c_int),
    ]


class AssettoCorsaReader:
    """Opens the AC shared-memory pages and yields normalized TelemetryFrames.

    Must run on Windows while Assetto Corsa is in a live session -- the
    named shared-memory pages only exist while the game is running.
    """

    def __init__(self):
        self._physics_mm = self._open(SHARED_MEMORY_NAMES["physics"], SPageFilePhysics)
        self._graphics_mm = self._open(SHARED_MEMORY_NAMES["graphics"], SPageFileGraphic)
        self._static_mm = self._open(SHARED_MEMORY_NAMES["static"], SPageFileStatic)

    @staticmethod
    def _open(name: str, struct_type):
        size = ctypes.sizeof(struct_type)
        return mmap.mmap(-1, size, tagname=name, access=mmap.ACCESS_READ)

    def _read(self, mm: mmap.mmap, struct_type):
        mm.seek(0)
        buf = mm.read(ctypes.sizeof(struct_type))
        instance = struct_type()
        ctypes.memmove(ctypes.addressof(instance), buf, len(buf))
        return instance

    def read_frame(self, session_id: str) -> TelemetryFrame:
        physics = self._read(self._physics_mm, SPageFilePhysics)
        graphics = self._read(self._graphics_mm, SPageFileGraphic)

        return TelemetryFrame(
            timestamp=time.time(),
            session_id=session_id,
            lap_number=graphics.completedLaps,
            lap_time_ms=graphics.iCurrentTime,
            last_lap_time_ms=graphics.iLastTime,
            best_lap_time_ms=graphics.iBestTime,
            speed_kmh=physics.speedKmh,
            rpm=physics.rpms,
            gear=physics.gear,
            throttle=physics.gas,
            brake=physics.brake,
            steer_angle=physics.steerAngle,
            pos_x=0.0,
            pos_y=0.0,
            pos_z=0.0,
            normalized_car_position=graphics.normalizedCarPosition,
            tyre_core_temp=tuple(physics.tyreCoreTemperature),
            fuel=physics.fuel,
            is_in_pit=bool(graphics.isInPit),
            is_off_track=physics.numberOfTyresOut >= 2,
        )

    def close(self):
        self._physics_mm.close()
        self._graphics_mm.close()
        self._static_mm.close()
