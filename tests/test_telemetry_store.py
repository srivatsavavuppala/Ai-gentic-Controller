import tempfile
from pathlib import Path

from telemetry.schema import TelemetryFrame
from telemetry.store import TelemetryStore


def _sample_frame(session_id="s1", lap=1):
    return TelemetryFrame(
        timestamp=1.0,
        session_id=session_id,
        lap_number=lap,
        lap_time_ms=90_000,
        last_lap_time_ms=91_000,
        best_lap_time_ms=89_500,
        speed_kmh=210.5,
        rpm=7200,
        gear=5,
        throttle=1.0,
        brake=0.0,
        steer_angle=0.02,
        pos_x=0.0,
        pos_y=0.0,
        pos_z=0.0,
        normalized_car_position=0.42,
        tyre_core_temp=(85.0, 86.0, 84.5, 85.5),
        fuel=42.3,
        is_in_pit=False,
        is_off_track=False,
    )


def test_write_and_read_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = TelemetryStore(db_path=db_path)

        store.write(_sample_frame(lap=1))
        store.write(_sample_frame(lap=2))

        rows = store.laps_for_session("s1")
        assert len(rows) == 2
        assert [r.lap_number for r in rows] == [1, 2]
        assert rows[0].speed_kmh == 210.5

        store.close()
