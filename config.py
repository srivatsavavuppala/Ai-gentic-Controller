"""Central configuration for ApexMind.

Target game decision (Phase 0): Assetto Corsa (original, not Competizione).

Why: AC exposes a well-documented, stable shared-memory telemetry layout
(SPageFilePhysics / SPageFileGraphic / SPageFileStatic) that's been the de
facto standard for third-party tools (SimHub, overlays, etc.) for years, it
accepts input from any registered Windows controller/virtual controller with
no anti-cheat blocking offline/practice sessions, and it's inexpensive and
light enough to run alongside training/analysis code on a single laptop.

iRacing was ruled out for the autonomous-driving phase: its ToS prohibits
bot/AI control outside of a small set of sanctioned contexts. rFactor2 is a
solid second choice (it additionally exposes a plugin API that can hook the
physics loop directly) if AC's telemetry format ever proves limiting.
"""

from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).parent

TARGET_GAME = "assetto_corsa"

SHARED_MEMORY_NAMES = {
    "physics": "acpmf_physics",
    "graphics": "acpmf_graphics",
    "static": "acpmf_static",
}


@dataclass
class Paths:
    telemetry_db: Path = REPO_ROOT / "telemetry" / "telemetry.db"
    experiments_dir: Path = REPO_ROOT / "experiments" / "runs"
    knowledge_db: Path = REPO_ROOT / "knowledge" / "knowledge.db"
    gamecontrollerdb: Path = REPO_ROOT / "control" / "gamecontrollerdb.txt"


@dataclass
class ControlConfig:
    poll_hz: int = 60
    deadzone: float = 0.05


@dataclass
class AppConfig:
    target_game: str = TARGET_GAME
    paths: Paths = field(default_factory=Paths)
    control: ControlConfig = field(default_factory=ControlConfig)


CONFIG = AppConfig()
