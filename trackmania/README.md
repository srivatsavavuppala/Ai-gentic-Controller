# TrackMania Nations Forever integration

Bridges telemetry + control between TrackMania Nations Forever and Python,
via a TMInterface AngelScript plugin talking over a local TCP socket. Chosen
over building Assetto Corsa/TORCS support further because it needs zero
C++ compilation -- see memory `torcs-scr-build-paused` for why TORCS was
abandoned.

## Setup

1. Install [TrackMania ModLoader](https://tomashu.dev/software/tmloader/),
   then install and activate the **TMInterface** mod through it, and launch
   the game via ModLoader's Play button.
2. Copy `ApexMindBridge.as` into `Documents\TMInterface\Plugins\`.
3. Start a race. The plugin listens on `127.0.0.1:9000` and logs to
   TMInterface's console when it's ready and when a client connects.

## Try it

```
python -m trackmania.live_test
```

Prints live telemetry (position, speed, race time) for 10 seconds -- confirms
the plugin is loaded, the socket handshake works, and the wire format decodes
correctly.

## Protocol

See the docstrings in `ApexMindBridge.as` and `bridge_client.py` -- both
must be kept in sync if the wire format ever changes. Telemetry flows
plugin -> Python every physics tick; control flows Python -> plugin
whenever a `ControlFrame` is sent, mapped onto TrackMania's single combined
gas axis (`throttle - brake`) and its steer axis.

## Open questions (verify live, once actually driving)

- Sign convention for `steering`/`Steer`: assumed positive = right, matching
  our own `ControlFrame` convention -- flip if it turns out reversed.
- `Net::Socket.Accept(0)` is assumed non-blocking (returns null immediately
  if no client is pending) -- if `OnRunStep` instead stalls waiting for a
  connection, this needs revisiting.
