#include "../main/DeviceMetrics.h"
#include <assert.h>
#include <iostream>

int64_t fakeTimeUs = 0;
FakeWiFi WiFi;
FakeEsp ESP;

int main() {
  PubSubClient mqtt;
  DeviceMetrics observer(mqtt);
  Servo red, blue, yellow;
  red.angle = 45;
  blue.angle = 0;
  yellow.angle = 45;
  blue.pwmAttached = false;
  const auto tick = [&]() {
    observer.publishIfDue(2, 1, 2, red, blue, yellow, 0, 1, 0, 1, 0, 1, true, false);
  };
  fakeTimeUs = 4999999;
  tick();
  assert(mqtt.publications == 0 && red.reads == 0);
  fakeTimeUs = 5000000;
  tick();
  assert(mqtt.publications == 1 && observer.state.publishSuccesses == 1);
  assert(mqtt.topic == "factory/esp32/esp32_01/telemetry");
  assert(mqtt.declaredLength == mqtt.payload.size());
  assert(red.angle == 45 && blue.angle == 0 && yellow.angle == 45);
  std::cout << mqtt.payload << '\n';

  // Offline telemetry is skipped; the adapter has no API to reconnect the client.
  mqtt.online = false;
  fakeTimeUs = 10000000;
  tick();
  assert(mqtt.publications == 1 && observer.state.publishFailures == 0);
  assert(red.reads == 1);
  mqtt.online = true;
  mqtt.beginOk = false;
  fakeTimeUs = 15000000;
  tick();
  assert(observer.state.publishFailures == 1 && mqtt.publications == 1);
  mqtt.beginOk = true;
  fakeTimeUs = 20000000;
  tick();
  assert(observer.state.publishSuccesses == 2 && mqtt.publications == 2);
  std::cout << mqtt.payload << '\n';
}
