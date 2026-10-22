#pragma once

// ==========================================
// THÔNG TIN BẢO MẬT TEST SKETCH (MẪU)
// ==========================================
// Hướng dẫn:
// 1. Sao chép nội dung file này sang file mới tên là `secrets.h` (cùng thư mục).
// 2. Điền thông tin Wi-Fi của bạn vào `secrets.h`.
// 3. File `secrets.h` đã được thêm vào .gitignore để không bị lộ mật khẩu.
// ==========================================

// Cấu hình Wi-Fi (Chỉ hỗ trợ băng tần 2.4GHz)
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Cấu hình MQTT Broker (Mặc định dùng cloud broker miễn phí để test)
const char* MQTT_BROKER   = "broker.hivemq.com";
const int   MQTT_PORT     = 1883;

// Topic MQTT
const char* TOPIC_CONTROL = "factory/servo/control";
const char* TOPIC_STATUS  = "factory/system/status";
