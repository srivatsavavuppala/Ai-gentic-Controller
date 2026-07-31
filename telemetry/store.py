"""SQLite-backed store for telemetry frames.

Deliberately schema-simple for Phase 1. The Knowledge/Experiment agents in
later phases read from this table (or a materialized per-lap summary of it)
rather than a bespoke format, so this is the one place lap data lives.
"""

from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import CONFIG
from telemetry.schema import TelemetryFrame

Base = declarative_base()


class TelemetryFrameRow(Base):
    __tablename__ = "telemetry_frames"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(Float, nullable=False)
    session_id = Column(String, nullable=False, index=True)
    lap_number = Column(Integer, nullable=False)
    lap_time_ms = Column(Integer, nullable=False)
    last_lap_time_ms = Column(Integer, nullable=False)
    best_lap_time_ms = Column(Integer, nullable=False)
    speed_kmh = Column(Float, nullable=False)
    rpm = Column(Float, nullable=False)
    gear = Column(Integer, nullable=False)
    throttle = Column(Float, nullable=False)
    brake = Column(Float, nullable=False)
    steer_angle = Column(Float, nullable=False)
    normalized_car_position = Column(Float, nullable=False)
    fuel = Column(Float, nullable=False)
    is_in_pit = Column(Boolean, nullable=False)
    is_off_track = Column(Boolean, nullable=False)


class TelemetryStore:
    def __init__(self, db_path=None):
        db_path = db_path or CONFIG.paths.telemetry_db
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine)

    def write(self, frame: TelemetryFrame) -> None:
        with self._Session() as session:
            session.add(
                TelemetryFrameRow(
                    timestamp=frame.timestamp,
                    session_id=frame.session_id,
                    lap_number=frame.lap_number,
                    lap_time_ms=frame.lap_time_ms,
                    last_lap_time_ms=frame.last_lap_time_ms,
                    best_lap_time_ms=frame.best_lap_time_ms,
                    speed_kmh=frame.speed_kmh,
                    rpm=frame.rpm,
                    gear=frame.gear,
                    throttle=frame.throttle,
                    brake=frame.brake,
                    steer_angle=frame.steer_angle,
                    normalized_car_position=frame.normalized_car_position,
                    fuel=frame.fuel,
                    is_in_pit=frame.is_in_pit,
                    is_off_track=frame.is_off_track,
                )
            )
            session.commit()

    def laps_for_session(self, session_id: str):
        with self._Session() as session:
            return (
                session.query(TelemetryFrameRow)
                .filter(TelemetryFrameRow.session_id == session_id)
                .order_by(TelemetryFrameRow.timestamp)
                .all()
            )

    def close(self) -> None:
        """Dispose the engine's pooled connections.

        On Windows, SQLite keeps the underlying file handle open for the
        life of the connection pool -- without this, a caller (e.g. a test
        using a temp directory) can't delete the db file right after use.
        """
        self._engine.dispose()
