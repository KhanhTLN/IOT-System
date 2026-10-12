#pragma once

// ==========================================
// THÔNG TIN BẢO MẬT WI-FI & MQTT (MẪU)
// ==========================================
// Hướng dẫn:
// 1. Sao chép nội dung file này sang file mới tên là `secrets.h` (cùng thư mục).
// 2. Điền thông tin Wi-Fi và IP MQTT Broker của bạn vào `secrets.h`.
// 3. File `secrets.h` đã được thêm vào .gitignore để không bị lộ mật khẩu.
// ==========================================

// Cấu hình Wi-Fi (Chỉ hỗ trợ băng tần 2.4GHz)
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Cấu hình MQTT Broker
// - Dùng máy tính nội bộ LAN: Điền IP máy tính chạy Mosquitto (VD: "192.168.1.15")
// - Dùng Wokwi giả lập hoặc Public Cloud: "broker.hivemq.com"
const char* MQTT_BROKER   = "192.168.1.15";
const int   MQTT_PORT     = 1883;

// Topic MQTT
const char* MQTT_TOPIC_SERVO  = "factory/servo/control";
const char* MQTT_TOPIC_STATUS = "factory/system/status";
