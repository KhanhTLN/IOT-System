#pragma once
#include <stdint.h>

constexpr int WL_CONNECTED = 3;
struct FakeWiFi {
  int status() { return WL_CONNECTED; }
  int RSSI() { return -61; }
};
struct FakeEsp {
  uint32_t getFreeHeap() { return 200000; }
  uint32_t getMinFreeHeap() { return 180000; }
  uint32_t getCpuFreqMHz() { return 240; }
};
extern FakeWiFi WiFi;
extern FakeEsp ESP;
