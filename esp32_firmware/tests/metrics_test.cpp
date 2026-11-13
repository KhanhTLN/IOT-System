#include "../main/MetricsState.h"

#include <assert.h>
#include <iostream>
#include <limits>
#include <string>

using namespace monitoring;

struct FakeMqtt {
  bool beginOk = true;
  bool finishOk = true;
  bool shortWrite = false;
  bool retained = true;
  unsigned int expectedLength = 0;
  int beginCalls = 0;
  int writeCalls = 0;
  int finishCalls = 0;
  std::string content;

  bool beginPublish(const char*, unsigned int length, bool retain) {
    ++beginCalls;
    expectedLength = length;
    retained = retain;
    return beginOk;
  }
  size_t write(const uint8_t* payload, size_t length) {
    ++writeCalls;
    const size_t written = shortWrite ? length - 1 : length;
    content.assign(reinterpret_cast<const char*>(payload), written);
    return written;
  }
  int endPublish() { ++finishCalls; return finishOk ? 1 : 0; }
};

static void emit(const MetricsState& metrics, const Snapshot& sample) {
  char payload[PAYLOAD_CAPACITY];
  const int length = metrics.formatPayload(payload, sizeof(payload), sample);
  assert(length > 0 && static_cast<size_t>(length) < sizeof(payload));
  assert(static_cast<size_t>(length) == strlen(payload));
  std::cout << payload << '\n';
}

int main() {
  MetricsState metrics;
  Snapshot sample;
  sample.wifiRssiDbm = -64;
  sample.freeHeapBytes = 200000;
  sample.minFreeHeapBytes = 180000;
  sample.cpuFrequencyMhz = 240;
  sample.wifiConnected = sample.mqttConnected = true;
  emit(metrics, sample);

  // Each station is observed independently; the observer never requests a transition.
  metrics.observeSortStart(RED, 1000);
  metrics.observeSortStart(BLUE, 1100);
  metrics.observeSortStart(YELLOW, 1200);
  metrics.observeHome(BLUE, BIN_SENSOR, 1700);
  metrics.observeHome(YELLOW, EMERGENCY, 2050);
  metrics.observeHome(RED, TIMEOUT, 6000);
  assert(metrics.stations[RED].timeouts == 1);
  assert(metrics.stations[RED].binConfirmations == 0);
  assert(metrics.stations[BLUE].binConfirmations == 1);
  assert(fabs(metrics.stations[BLUE].lastSortDurationSeconds - 0.6) < 0.0001);
  assert(metrics.stations[YELLOW].emergencyHomes == 1);
  assert(metrics.stations[RED].lastSortDurationSeconds == 5.0);

  metrics.observeSortStart(BLUE, 8000);
  metrics.observeSortStart(BLUE, 8100);
  assert(metrics.stations[BLUE].retriggers == 1);
  assert(metrics.stations[BLUE].sortStarts == 3);
  metrics.observeHome(BLUE, BIN_SENSOR, 8500);
  assert(fabs(metrics.stations[BLUE].lastSortDurationSeconds - 0.4) < 0.0001);
  metrics.observeHome(YELLOW, EMERGENCY, 8600);
  assert(metrics.stations[YELLOW].lastSortDurationSeconds == -1.0);

  const int clear[6] = {1, 1, 1, 1, 1, 1};
  const int blocked[6] = {0, 0, 0, 0, 0, 0};
  metrics.observeInputs(clear);
  metrics.observeInputs(blocked);
  metrics.observeInputs(blocked);
  for (size_t i = 0; i < 6; ++i) assert(metrics.irFallingEdges[i] == 1);
  metrics.observeInputs(clear);
  metrics.observeInputs(blocked);
  for (size_t i = 0; i < 6; ++i) assert(metrics.irFallingEdges[i] == 2);

  metrics.observeCamera("RED", true, true, 0.0, 9000);
  assert(metrics.lastCameraConfidence == 0.0 && metrics.lastCameraColorCode == 1);
  metrics.observeCamera("GREEN", false, false, 0, 9100);
  assert(metrics.lastCameraConfidence == -1.0 && metrics.lastCameraColorCode == 2);
  metrics.observeCamera("XANH", true, true, 0.8, 9200);
  assert(metrics.lastCameraColorCode == 2);
  metrics.observeCamera("VANG", true, true, 0.95, 9300);
  assert(metrics.lastCameraColorCode == 3);
  metrics.observeCamera("UNKNOWN", true, false, 0, 9400);
  metrics.observeCamera("RED", true, true, 2.0, 9500);
  metrics.observeCamera("BLUE", true, true, std::numeric_limits<double>::quiet_NaN(), 9600);
  assert(metrics.cameraMessages == 7 && metrics.cameraRecognizedColors == 6);
  assert(metrics.cameraUnrecognizedColors == 1 && metrics.cameraInvalidConfidence == 3);
  sample.uptimeMs = 10000;
  emit(metrics, sample);

  const uint64_t rollover = 1ULL << 32;
  metrics.observeSortStart(RED, rollover - 500);
  metrics.observeHome(RED, BIN_SENSOR, rollover + 500);
  metrics.observeCamera("YELLOW", true, true, 0.99, rollover - 1000);
  sample.uptimeMs = rollover + 2000;
  assert(metrics.stations[RED].lastSortDurationSeconds == 1.0);
  emit(metrics, sample);

  // The largest counter values must fit even though the MQTT default buffer is only 256B.
  const uint64_t maximum = std::numeric_limits<uint64_t>::max();
  metrics.mqttConnectAttempts = metrics.mqttConnections = metrics.mqttConnectFailures = maximum;
  metrics.publishSuccesses = metrics.publishFailures = maximum;
  metrics.cameraMessages = metrics.cameraRecognizedColors = metrics.cameraUnrecognizedColors = maximum;
  metrics.cameraInvalidConfidence = maximum;
  metrics.lastPublishDurationMs = 999999.0;
  for (size_t i = 0; i < 3; ++i) {
    StationCounters& station = metrics.stations[i];
    station.sortStarts = station.retriggers = station.binConfirmations = maximum;
    station.timeouts = station.emergencyHomes = station.homeCommands = maximum;
    station.lastSortDurationSeconds = maximum / 1000.0;
  }
  for (size_t i = 0; i < 6; ++i) metrics.irFallingEdges[i] = maximum;
  sample.uptimeMs = maximum;
  sample.freeHeapBytes = sample.minFreeHeapBytes = std::numeric_limits<uint32_t>::max();
  emit(metrics, sample);

  char small[8];
  assert(metrics.formatPayload(small, sizeof(small), sample) == -1);
  assert(small[sizeof(small) - 1] == '\0');
  assert(metrics.formatPayload(nullptr, 0, sample) == -1);

  char payload[PAYLOAD_CAPACITY];
  const int length = metrics.formatPayload(payload, sizeof(payload), sample);
  FakeMqtt mqtt;
  assert(publishPayload(mqtt, "factory/esp32/esp32_01/telemetry", payload, length));
  assert(!mqtt.retained && mqtt.expectedLength == static_cast<unsigned int>(length));
  assert(mqtt.content == payload && mqtt.writeCalls == 1 && mqtt.finishCalls == 1);
  FakeMqtt beginFailure;
  beginFailure.beginOk = false;
  assert(!publishPayload(beginFailure, "topic", payload, length));
  assert(beginFailure.writeCalls == 0 && beginFailure.finishCalls == 0);
  FakeMqtt shortWrite;
  shortWrite.shortWrite = true;
  assert(!publishPayload(shortWrite, "topic", payload, length));
  FakeMqtt finishFailure;
  finishFailure.finishOk = false;
  assert(!publishPayload(finishFailure, "topic", payload, length));
}
