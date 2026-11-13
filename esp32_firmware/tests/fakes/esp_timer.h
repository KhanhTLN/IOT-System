#pragma once
#include <stdint.h>
extern int64_t fakeTimeUs;
inline int64_t esp_timer_get_time() { return fakeTimeUs; }
