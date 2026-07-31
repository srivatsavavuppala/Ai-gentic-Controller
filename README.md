# Project ApexMind

Autonomous agentic racing intelligence platform. Full vision and phased roadmap: see
[PROJECT_APEXMIND_PLAN.md](PROJECT_APEXMIND_PLAN.md).

## Status: Phase 0 scaffold

Target game (Phase 0 decision, rationale in `config.py`): **Assetto Corsa**.

## Layout

```
/telemetry   - game telemetry readers, normalization, historical DB (Phase 1)
/control     - SDL2 controller input + ViGEm virtual controller output (Phase 1)
/sim_env     - fast custom training simulator (Phase 2)
/policy      - RL training + inference, the Driving Policy (Phase 2)
/agents      - Claude Agent SDK: Race Director + specialist agents (Phase 4+)
/knowledge   - experiment DB, knowledge base, vector search (Phase 4+)
/dashboard   - web UI (Phase 8)
/experiments - experiment configs + results, nothing ever deleted
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Two things need a manual, one-time step beyond `pip install` (both touch
system-level drivers, so they're not automated here):

- **ViGEmBus driver** (virtual controller output, for AI-driven control):
  https://github.com/ViGEm/ViGEmBus/releases
- **SDL2 gamecontrollerdb.txt** (widens which controllers are recognized by
  name rather than raw joystick axes): drop a copy at
  `control/gamecontrollerdb.txt` from
  https://github.com/mdqinc/SDL_GameControllerDB

## Try it

```
pytest -v
python -c "from control.input_adapter import list_devices; print(list_devices())"
```

The second command is the plug-and-play smoke test -- plug in any
controller/wheel and it should show up by name.
