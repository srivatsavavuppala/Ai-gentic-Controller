# Project ApexMind — Build Plan

Source vision: `Master Orchestrator Prompt.pdf`, `Project ApexMind.pdf`.
Decisions locked in: target = existing racing sim/game, goal = fully autonomous driver, compute = laptop only (no dedicated GPU), scope = full multi-agent platform (phased).

## 1. Key architecture decision: two tiers

**Tier 1 — Real-time control layer (plain code, not LLM)**
- Controller input adapter, virtual controller output, telemetry capture, the RL Driving Policy inference.
- Runs at 60Hz+, sub-16ms budget. No LLM call belongs in this loop.

**Tier 2 — Agentic reasoning layer (Claude-based, per-lap / per-session)**
- Race Director, Telemetry Analyst, Performance Scientist, Experiment Manager, Critic, Knowledge Agent,
  Learning Agent, Simulation Manager, Race Strategy Agent, Evaluation Agent.
- Implemented as Claude Agent SDK agents/subagents with tool access to the telemetry DB, experiment DB,
  and knowledge base. The "Master Orchestrator Prompt" becomes the literal system prompt for the
  top-level Race Director agent.
- Runs between laps or sessions, not inside the control loop. This is the "agentic" part of the system.

**Training vs. deployment split**
- Train the Driving Policy in a **fast custom simulator** (Gymnasium + bicycle/dynamics model, vectorized,
  runs thousands of laps/sec on CPU). Consumer sim games (ACC/iRacing/rFactor2/F1 24-25) only run in
  real time — unusable for bulk RL training on a laptop.
- **Deploy/validate** the trained policy inside the real sim game via a virtual controller, for visual
  proof, human-vs-AI racing, and real telemetry capture.

## 2. Controller plug-and-play design

- **Input (human driving):** SDL2 (via `pysdl2`) as the universal gamepad/wheel abstraction layer.
  SDL2's community-maintained `gamecontrollerdb.txt` covers thousands of devices (Xbox, PS4/PS5
  DualSense, generic USB wheels/pedals) with one uniform API — this is what most game engines use
  under the hood for "any controller works."
- **Output (AI driving):** ViGEmBus + `vgamepad` (Python) to create a virtual Xbox360/DS4 controller.
  The Driving Policy's steering/throttle/brake outputs get written to this virtual device, so from the
  sim game's point of view, the AI "is" a controller — no game-specific control-injection hacks needed,
  and it composes with human hand-off (AI drives, human takes over instantly on the same device path).

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration/backend | Python | ML ecosystem, fastest to iterate |
| Controller I/O | SDL2 (`pysdl2`) + ViGEmBus (`vgamepad`) | universal input + virtual output on Windows |
| Telemetry ingestion | game-specific reader (shared memory / UDP) normalized to one schema | keeps rest of system game-agnostic |
| Fast training sim | custom Gymnasium env (bicycle model), vectorized | CPU-only bulk RL training |
| RL algorithm | PPO or SAC via Stable-Baselines3 | CPU-friendly, well-supported, easy to swap later |
| Experiment/knowledge store | SQLite to start (zero infra) + embeddings for semantic search | matches "knowledge should be searchable"; migrate to Postgres only if needed |
| Agentic layer | Claude Agent SDK | Race Director + specialist agents, tool-calling into the stores above |
| Dashboard | FastAPI + lightweight frontend (or Streamlit for v1) | lap times, sector deltas, experiment results, agent reports |

## 4. Repo layout (proposed)

```
/telemetry      - game readers, normalization, historical DB
/control        - SDL2 input adapter, ViGEm virtual output, shared controller schema
/sim_env        - fast custom Gymnasium training environment
/policy         - RL training + inference (Driving Policy)
/agents         - Claude Agent SDK: Race Director + specialists, tool definitions
/knowledge      - experiment DB, knowledge base, vector search
/dashboard      - web UI
/experiments    - experiment configs + results (nothing ever deleted)
```

## 5. Phased roadmap

**Phase 0 — Foundations**
Repo scaffold, pick the target sim game (recommend starting with one that has a solid Python-accessible
telemetry/shared-memory API and no online-anti-cheat conflict — e.g. Assetto Corsa or rFactor2, not
iRacing, for the AI-control phase), dev environment, CI.

**Phase 1 — Controller & telemetry plumbing**
Universal controller input working end-to-end into the chosen game; telemetry capture into the
historical DB. *Value delivered here already: you can drive with any controller and get structured
lap/telemetry data, even before any AI exists.*

**Phase 2 — Fast simulator + baseline Driving Policy**
Build the custom Gymnasium track/car env; train a first PPO/SAC policy that can complete laps without
crashing. All training happens here, not in the real game.

**Phase 3 — Sim-to-game transfer**
Get the trained policy driving the real game through the virtual controller; validate it actually
drives sanely under real rendering/physics, not just the simplified training model.

**Phase 4 — Agentic layer v1**
Race Director, Telemetry Analyst, Critic, Knowledge Agent wired to the real telemetry DB, producing
per-lap performance reports and a first searchable knowledge base.

**Phase 5 — Experimentation loop**
Performance Scientist + Experiment Manager + Evaluation Agent: hypothesis → design experiment → run
in the fast sim → statistical significance check → accept/reject → update baseline + knowledge base.

**Phase 6 — Learning Agent + Simulation Manager**
Meta-learning (reward shaping, exploration tuning, overfitting checks) and scenario generation (rain,
traffic, safety car, low grip, old tires).

**Phase 7 — Race Strategy Agent**
Pit timing, tire/fuel/ERS strategy, opponent modeling — relevant once the target game models tire wear/fuel.

**Phase 8 — Continuous loop + reporting**
Automate "Observe → Analyze → Hypothesize → Experiment → Train → Evaluate → Update Knowledge → Deploy
→ Repeat," scheduled runs, auto-generated research reports (key findings / successful & failed
experiments / open questions / next actions), dashboard polish.

## 6. Risks and constraints to keep in view

- **Anti-cheat/ToS:** never run the autonomous driver in online/ranked multiplayer on games that
  prohibit bots (iRacing explicitly does). Keep AI driving to offline/practice/time-trial modes, or
  games that permit it.
- **Compute ceiling:** laptop-only is fine for everything except bulk RL training runs and large
  knowledge-base embedding jobs — plan to burst those to a cloud GPU (rented per-run) rather than
  trying to run them locally; nothing else in the architecture needs a GPU.
- **Scope honesty:** the full org chart in the docs is a multi-month build. Phases 0–3 are the part
  worth getting solid before layering on the rest — everything downstream depends on telemetry and
  the training sim being reliable.
