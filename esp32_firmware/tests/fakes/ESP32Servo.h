#pragma once

// No write/attach methods: the metrics adapter must only observe a servo.
class Servo {
 public:
  int angle = 0;
  bool pwmAttached = true;
  int reads = 0;
  int read() { ++reads; return angle; }
  bool attached() { return pwmAttached; }
};
