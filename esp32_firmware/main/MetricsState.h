#pragma once

#include <math.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace monitoring {

enum Station : uint8_t { RED = 0, BLUE = 1, YELLOW = 2 };
enum HomeReason : uint8_t { BIN_SENSOR, TIMEOUT, EMERGENCY };

struct StationCounters {
  uint64_t sortStarts = 0;
  uint64_t retriggers = 0;
  uint64_t binConfirmations = 0;
  uint64_t timeouts = 0;
  uint64_t emergencyHomes = 0;
  uint64_t homeCommands = 0;
  uint64_t startedMs = 0;
  bool trackingSort = false;
  double lastSortDurationSeconds = -1.0;
};

struct StationSample {
  int state = 0;
  int commandedAngleDegrees = 0;
  bool pwmAttached = false;
};

struct Snapshot {
  uint64_t uptimeMs = 0;
  int wifiRssiDbm = 0;
  uint32_t freeHeapBytes = 0;
  uint32_t minFreeHeapBytes = 0;
  uint32_t cpuFrequencyMhz = 0;
  bool wifiConnected = false;
  bool mqttConnected = false;
  bool autoTestMode = false;
  bool liveMonitorMode = false;
  StationSample stations[3];
  int irLevels[6] = {1, 1, 1, 1, 1, 1};
};

// Fixed storage; JSON keys are constants, never taken from a received command.
// Avoid ArduinoJson's legacy-name macros, which also expand inside namespaces.
class MetricsJsonWriter {
 public:
  MetricsJsonWriter(char* destination, size_t capacity) : data(destination), size(capacity) {}

  void append(const char* format, ...) {
    if (!valid) return;
    va_list arguments;
    va_start(arguments, format);
    const int length = vsnprintf(data + used, size - used, format, arguments);
    va_end(arguments);
    if (length < 0 || static_cast<size_t>(length) >= size - used) {
      valid = false;
      return;
    }
    used += static_cast<size_t>(length);
  }

  void integer(const char* key, uint64_t value, bool first = false) {
    append("%s\"%s\":%llu", first ? "" : ",", key, static_cast<unsigned long long>(value));
  }

  void real(const char* key, double value) {
    append(",\"%s\":%.4f", key, value);
  }

  int length() const { return valid ? static_cast<int>(used) : -1; }

 private:
  char* data;
  size_t size;
  size_t used = 0;
  bool valid = true;
};

struct MetricsState {
  StationCounters stations[3];
  uint64_t irFallingEdges[6] = {};
  int previousIr[6] = {1, 1, 1, 1, 1, 1};
  uint64_t mqttConnectAttempts = 0;
  uint64_t mqttConnections = 0;
  uint64_t mqttConnectFailures = 0;
  uint64_t publishSuccesses = 0;
  uint64_t publishFailures = 0;
  double lastPublishDurationMs = 0.0;
  uint64_t cameraMessages = 0;
  uint64_t cameraRecognizedColors = 0;
  uint64_t cameraUnrecognizedColors = 0;
  uint64_t cameraInvalidConfidence = 0;
  bool cameraMessageSeen = false;
  uint64_t lastCameraMessageMs = 0;
  int lastCameraColorCode = 0;
  double lastCameraConfidence = -1.0;

  void observeInputs(const int* levels) {
    for (size_t i = 0; i < 6; ++i) {
      if (previousIr[i] == 1 && levels[i] == 0) ++irFallingEdges[i];
      previousIr[i] = levels[i];
    }
  }

  // color is the label already parsed by the original callback. No decision is fed back.
  void observeCamera(const char* color, bool confidenceProvided, bool confidenceNumeric,
                     double confidence, uint64_t nowMs) {
    ++cameraMessages;
    cameraMessageSeen = true;
    lastCameraMessageMs = nowMs;
    lastCameraColorCode = 0;
    if (strcmp(color, "RED") == 0) lastCameraColorCode = 1;
    else if (strcmp(color, "BLUE") == 0 || strcmp(color, "GREEN") == 0 ||
             strcmp(color, "XANH") == 0) lastCameraColorCode = 2;
    else if (strcmp(color, "YELLOW") == 0 || strcmp(color, "VANG") == 0) lastCameraColorCode = 3;
    if (lastCameraColorCode != 0) ++cameraRecognizedColors;
    else ++cameraUnrecognizedColors;

    lastCameraConfidence = -1.0;
    if (confidenceProvided) {
      if (confidenceNumeric && isfinite(confidence) && confidence >= 0.0 && confidence <= 1.0) {
        lastCameraConfidence = confidence;
      } else {
        ++cameraInvalidConfidence;
      }
    }
  }

  void observeSortStart(Station station, uint64_t nowMs) {
    StationCounters& counters = stations[station];
    if (counters.trackingSort) ++counters.retriggers;
    ++counters.sortStarts;
    counters.trackingSort = true;
    counters.startedMs = nowMs;
  }

  void observeHome(Station station, HomeReason reason, uint64_t nowMs) {
    StationCounters& counters = stations[station];
    ++counters.homeCommands;
    if (reason == BIN_SENSOR) ++counters.binConfirmations;
    if (reason == TIMEOUT) ++counters.timeouts;
    if (reason == EMERGENCY) ++counters.emergencyHomes;
    counters.lastSortDurationSeconds = counters.trackingSort
        ? (nowMs - counters.startedMs) / 1000.0 : -1.0;
    counters.trackingSort = false;
  }

  int formatPayload(char* buffer, size_t capacity, const Snapshot& sample) const {
    if (capacity == 0) return -1;
    MetricsJsonWriter out(buffer, capacity);
    out.append("{");
    out.integer("schema_version", 1, true);
    out.integer("uptime_seconds", sample.uptimeMs / 1000ULL);
    out.append(",\"wifi_rssi_dbm\":%d", sample.wifiRssiDbm);
    out.integer("free_heap_bytes", sample.freeHeapBytes);
    out.integer("min_free_heap_bytes", sample.minFreeHeapBytes);
    out.integer("cpu_frequency_mhz", sample.cpuFrequencyMhz);
    out.integer("wifi_connected", sample.wifiConnected);
    out.integer("mqtt_connected", sample.mqttConnected);
    out.integer("mqtt_connect_attempts_total", mqttConnectAttempts);
    out.integer("mqtt_connections_total", mqttConnections);
    out.integer("mqtt_connect_failures_total", mqttConnectFailures);
    out.integer("telemetry_publish_success_total", publishSuccesses);
    out.integer("telemetry_publish_failures_total", publishFailures);
    out.real("telemetry_last_publish_duration_ms", lastPublishDurationMs);
    out.integer("auto_test_mode", sample.autoTestMode);
    out.integer("live_monitor_mode", sample.liveMonitorMode);
    out.integer("camera_messages_total", cameraMessages);
    out.integer("camera_recognized_colors_total", cameraRecognizedColors);
    out.integer("camera_unrecognized_colors_total", cameraUnrecognizedColors);
    out.integer("camera_invalid_confidence_total", cameraInvalidConfidence);
    out.integer("camera_message_seen", cameraMessageSeen);
    out.real("camera_last_message_age_seconds", cameraMessageSeen
        ? (sample.uptimeMs - lastCameraMessageMs) / 1000.0 : -1.0);
    out.real("camera_last_confidence", lastCameraConfidence);
    out.integer("camera_last_color_code", lastCameraColorCode);

    const char* names[3] = {"red", "blue", "yellow"};
    for (size_t i = 0; i < 3; ++i) {
      const StationCounters& counters = stations[i];
      out.append(",\"%s\":{", names[i]);
      out.integer("state", sample.stations[i].state, true);
      out.integer("servo_commanded_angle_degrees", sample.stations[i].commandedAngleDegrees);
      out.integer("servo_pwm_attached", sample.stations[i].pwmAttached);
      out.integer("sort_starts_total", counters.sortStarts);
      out.integer("sort_retriggers_total", counters.retriggers);
      out.integer("bin_confirmations_total", counters.binConfirmations);
      out.integer("timeouts_total", counters.timeouts);
      out.integer("emergency_home_commands_total", counters.emergencyHomes);
      out.integer("home_commands_total", counters.homeCommands);
      out.real("last_sort_duration_seconds", counters.lastSortDurationSeconds);
      out.append("}");
    }
    for (size_t i = 0; i < 6; ++i) {
      out.append(",\"ir%u\":{", static_cast<unsigned int>(i + 1));
      out.integer("blocked", sample.irLevels[i] == 0, true);
      out.integer("falling_edges_total", irFallingEdges[i]);
      out.append("}");
    }
    out.append("}");
    return out.length();
  }
};

constexpr size_t PAYLOAD_CAPACITY = 4096;

// Use PubSubClient's large-payload API without changing its existing packet buffer/settings.
template <typename Client>
bool publishPayload(Client& client, const char* topic, const char* payload, size_t length) {
  if (!client.beginPublish(topic, static_cast<unsigned int>(length), false)) return false;
  const size_t written = client.write(reinterpret_cast<const uint8_t*>(payload), length);
  const bool finished = client.endPublish() != 0;
  return written == length && finished;
}

}  // namespace monitoring
