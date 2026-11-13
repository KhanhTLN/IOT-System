#pragma once

#include <ESP32Servo.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <esp_timer.h>
#include "MetricsState.h"

// Observation only: never sets station state, writes a servo, reads a GPIO,
// connects/disconnects MQTT, subscribes, or changes network/client configuration.
class DeviceMetrics {
 public:
  explicit DeviceMetrics(PubSubClient& client) : mqtt(client) {}
  monitoring::MetricsState state;

  static uint64_t nowMs() {
    return static_cast<uint64_t>(esp_timer_get_time()) / 1000ULL;
  }

  void observeInputs(int ir1, int ir2, int ir3, int ir4, int ir5, int ir6) {
    const int levels[6] = {ir1, ir2, ir3, ir4, ir5, ir6};
    state.observeInputs(levels);
  }

  void publishIfDue(int redState, int blueState, int yellowState,
                    Servo& red, Servo& blue, Servo& yellow,
                    int ir1, int ir2, int ir3, int ir4, int ir5, int ir6,
                    bool autoTest, bool liveMonitor) {
    const uint64_t now = nowMs();
    if (now - lastPublishAttemptMs < 5000ULL) return;
    lastPublishAttemptMs = now;
    if (!mqtt.connected()) return;

    monitoring::Snapshot sample;
    sample.uptimeMs = now;
    sample.wifiRssiDbm = WiFi.RSSI();
    sample.freeHeapBytes = ESP.getFreeHeap();
    sample.minFreeHeapBytes = ESP.getMinFreeHeap();
    sample.cpuFrequencyMhz = ESP.getCpuFreqMHz();
    sample.wifiConnected = WiFi.status() == WL_CONNECTED;
    sample.mqttConnected = mqtt.connected();
    sample.autoTestMode = autoTest;
    sample.liveMonitorMode = liveMonitor;
    Servo* servos[3] = {&red, &blue, &yellow};
    const int states[3] = {redState, blueState, yellowState};
    for (size_t i = 0; i < 3; ++i) {
      sample.stations[i].state = states[i];
      sample.stations[i].commandedAngleDegrees = servos[i]->read();
      sample.stations[i].pwmAttached = servos[i]->attached();
    }
    const int levels[6] = {ir1, ir2, ir3, ir4, ir5, ir6};
    for (size_t i = 0; i < 6; ++i) sample.irLevels[i] = levels[i];

    const uint64_t started = static_cast<uint64_t>(esp_timer_get_time());
    const int length = state.formatPayload(payload, sizeof(payload), sample);
    if (length >= 0 && monitoring::publishPayload(mqtt, topic, payload, static_cast<size_t>(length))) {
      ++state.publishSuccesses;
    } else {
      ++state.publishFailures;
    }
    state.lastPublishDurationMs =
        (static_cast<uint64_t>(esp_timer_get_time()) - started) / 1000.0;
  }

 private:
  PubSubClient& mqtt;
  const char* topic = "factory/esp32/esp32_01/telemetry";
  uint64_t lastPublishAttemptMs = 0;
  char payload[monitoring::PAYLOAD_CAPACITY];
};
