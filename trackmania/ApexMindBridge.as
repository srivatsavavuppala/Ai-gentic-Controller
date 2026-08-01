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
 *   Control frame (Python -> plugin), read if available, 8 bytes:
 *     int32 steer, int32 gas   (each in [-65536, 65536])
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

    g_client.WriteFloat(pos.x);
    g_client.WriteFloat(pos.y);
    g_client.WriteFloat(pos.z);
    g_client.WriteFloat(vel.x);
    g_client.WriteFloat(vel.y);
    g_client.WriteFloat(vel.z);
    g_client.WriteFloat(speed);
    g_client.WriteInt32(raceTime);

    if (g_client.Available >= 8) {
        int steer = g_client.ReadInt32();
        int gas = g_client.ReadInt32();
        simManager.SetInputState(InputType::Steer, steer);
        simManager.SetInputState(InputType::Gas, gas);
    }
}
