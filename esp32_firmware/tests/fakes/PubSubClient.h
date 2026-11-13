#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string>

// Deliberately exposes no connect/disconnect/configuration/subscription API.
class PubSubClient {
 public:
  bool online = true;
  bool beginOk = true;
  int publications = 0;
  unsigned int declaredLength = 0;
  std::string topic;
  std::string payload;
  bool connected() { return online; }
  bool beginPublish(const char* name, unsigned int length, bool retained) {
    if (!beginOk || retained) return false;
    ++publications;
    topic = name;
    declaredLength = length;
    return true;
  }
  size_t write(const uint8_t* data, size_t length) {
    payload.assign(reinterpret_cast<const char*>(data), length);
    return length;
  }
  int endPublish() { return 1; }
};
