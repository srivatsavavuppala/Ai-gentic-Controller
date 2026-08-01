/*
 * ApexMind <-> TrackMania Nations Forever bridge.
 *
 * TMInterface 2.0+ removed its built-in Python API in favor of AngelScript
 * plugins; this plugin is the replacement bridge it deliberately leaves
 * room for ("inter-process communication with Python ... via AngelScript's
 * Net::Socket API"). It listens on a local TCP socket, streams vehicle
 * state out every physics tick, and applies steering/gas commands read
 * back from the same socket.
 *
 * Install: copy this file into Documents\TMInterface\Plugins\
 *
 * Wire protocol (little-endian), matches trackmania/bridge_client.py:
 *   Telemetry frame  (plugin -> Python), sent every tick, 32 bytes:
 *     float posX, posY, posZ, velX, velY, velZ, speed; int32 raceTimeMs
 *   Control frame (Python -> plugin), read if available, 12 bytes:
 *     int32 steer, int32 gas, int32 reset
 *     (steer/gas each in [-65536, 65536]; reset != 0 triggers Respawn()
 *     instead of applying steer/gas that tick -- lets Python auto-reset
 *     after a crash without a human pressing backspace)
 */

Net::Socket@ g_listener;
Net::Socket@ g_client;

PluginInfo@ GetPluginInfo() {
    auto info = PluginInfo();
    info.Name = "ApexMind Bridge";
    info.Author = "ApexMind";
    info.Version = "1.0";
    info.Description = "Streams telemetry to and reads control input from a local Python process.";
    return info;
}

void Main() {
    @g_listener = Net::Socket();
    if (!g_listener.Listen("127.0.0.1", 9000)) {
        log("ApexMind Bridge: failed to listen on port 9000");
    } else {
        log("ApexMind Bridge: listening on 127.0.0.1:9000");
    }
}

void OnRunStep(SimulationManager@ simManager) {
    if (g_client is null) {
        @g_client = g_listener.Accept(0);
        if (g_client !is null) {
            log("ApexMind Bridge: Python client connected");
        }
        return;
    }

    vec3 pos = simManager.Dyna.CurrentState.Location.Position;
    vec3 vel = simManager.Dyna.CurrentState.LinearSpeed;
    float speed = simManager.PlayerInfo.DisplaySpeed;
    int raceTime = simManager.PlayerInfo.RaceTime;

    // Net::Socket doesn't notify us when the remote end closes -- Write()
    // just starts returning false. Treat that as a disconnect and drop back
    // to listening for a new client, or every future tick fails silently
    // and no new Python process can ever connect again.
    bool ok = true;
    ok = ok && g_client.Write(pos.x);
    ok = ok && g_client.Write(pos.y);
    ok = ok && g_client.Write(pos.z);
    ok = ok && g_client.Write(vel.x);
    ok = ok && g_client.Write(vel.y);
    ok = ok && g_client.Write(vel.z);
    ok = ok && g_client.Write(speed);
    ok = ok && g_client.Write(raceTime);

    if (!ok) {
        log("ApexMind Bridge: client disconnected, waiting for a new connection");
        @g_client = null;
        return;
    }

    if (g_client.Available >= 12) {
        int steer = g_client.ReadInt32();
        int gas = g_client.ReadInt32();
        int reset = g_client.ReadInt32();
        if (reset != 0) {
            // Respawn() resets position but NOT whatever steer/gas was last
            // applied -- without this, the car can start the new episode
            // still receiving stale input from the moment it crashed
            // (plausibly reverse, if that's what the policy happened to be
            // outputting right before the stall).
            simManager.SetInputState(InputType::Steer, 0);
            simManager.SetInputState(InputType::Gas, 0);
            simManager.Respawn();
        } else {
            simManager.SetInputState(InputType::Steer, steer);
            simManager.SetInputState(InputType::Gas, gas);
        }
    }
}
