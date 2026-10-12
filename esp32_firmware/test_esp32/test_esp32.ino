/*
 * =====================================================================
 * ESP32 STANDALONE TEST SCRIPT (Dành riêng để kiểm tra board ESP32)
 * =====================================================================
 * Mục đích:
 * 1. Kiểm tra phần cứng board: Chip ID, Flash, RAM, đèn LED tích hợp (GPIO 2).
 * 2. Quét mạng Wi-Fi xung quanh để test Anten bắt sóng.
 * 3. Kết nối Wi-Fi & MQTT Broker (nhận lệnh từ máy tính).
 * 4. Hỗ trợ gõ lệnh trực tiếp qua Serial Monitor (RED, YELLOW, GREEN)
 *    để test phản hồi ngay cả khi chưa bật MQTT!
 * 
 * Lưu ý quan trọng: File này nằm trong thư mục riêng `test_esp32/`
 * để tránh bị xung đột hàm setup()/loop() với file main.ino trong Arduino IDE.
 * =====================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "secrets.h"

// ==========================================
// 1. CẤU HÌNH THÔNG SỐ
// ==========================================
// Các thông số WIFI_SSID, WIFI_PASSWORD, MQTT_BROKER, MQTT_PORT,
// TOPIC_CONTROL, TOPIC_STATUS được quản lý an toàn trong file "secrets.h"

// Chân đèn LED tích hợp sẵn trên board ESP32 (Hầu hết các board ESP32 là GPIO 2)
const int ONBOARD_LED_PIN = 2;

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Biến quản lý nháy LED không gây chặn (Non-blocking Blink)
unsigned long lastBlinkTime = 0;
bool ledState = false;

// ==========================================
// 2. HÀM IN THÔNG TIN PHẦN CỨNG ESP32
// ==========================================
void printChipInfo() {
  Serial.println("\n--------------------------------------------------");
  Serial.println("🔍 [HARDWARE INFO] THÔNG TIN PHẦN CỨNG BOARD ESP32:");
  Serial.printf(" - Chip Model: %s (Rev %d)\n", ESP.getChipModel(), ESP.getChipRevision());
  Serial.printf(" - Số nhân CPU: %d Cores\n", ESP.getChipCores());
  Serial.printf(" - Tần số CPU: %d MHz\n", ESP.getCpuFreqMHz());
  Serial.printf(" - Flash Size: %d MB\n", ESP.getFlashChipSize() / (1024 * 1024));
  Serial.printf(" - Free Heap RAM: %d KB\n", ESP.getFreeHeap() / 1024);
  Serial.printf(" - Địa chỉ MAC Wi-Fi: %s\n", WiFi.macAddress().c_str());
  Serial.println("--------------------------------------------------");
}

// ==========================================
// 3. HÀM QUÉT WI-FI XUNG QUANH (Test Anten)
// ==========================================
void scanNearbyWiFi() {
  Serial.println("\n📡 [WiFi Scan] Đang quét sóng Wi-Fi xung quanh...");
  int n = WiFi.scanNetworks();
  if (n == 0) {
    Serial.println("⚠️ Không tìm thấy mạng Wi-Fi nào!");
  } else {
    Serial.printf("✅ Đã tìm thấy %d mạng Wi-Fi:\n", n);
    for (int i = 0; i < min(n, 5); ++i) { // In tối đa 5 mạng mạnh nhất
      Serial.printf("  %d. %-20s (RSSI: %d dBm)\n", i + 1, WiFi.SSID(i).c_str(), WiFi.RSSI(i));
    }
  }
}

// ==========================================
// 4. HÀM NHÁY ĐÈN LED BÁO PHẢN HỒI LỆNH
// ==========================================
void blinkFeedback(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(ONBOARD_LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(ONBOARD_LED_PIN, LOW);
    delay(delayMs);
  }
}

// ==========================================
// 5. XỬ LÝ LỆNH MÀU PHÂN LOẠI (GIẢ LẬP SERVO)
// ==========================================
void executeColorCommand(String color) {
  color.toUpperCase();
  Serial.println("\n==================================================");
  Serial.print("📥 [XỬ LÝ LỆNH] Nhận yêu cầu phân loại: ");
  Serial.println(color);

  if (color == "RED") {
    Serial.println("🔴 [ĐỎ]: Servo SẼ quay tới 45° | Đèn LED nháy 1 lần");
    blinkFeedback(1, 400);
  } else if (color == "YELLOW") {
    Serial.println("🟡 [VÀNG]: Servo SẼ quay tới 90° | Đèn LED nháy 2 lần");
    blinkFeedback(2, 250);
  } else if (color == "GREEN") {
    Serial.println("🟢 [XANH LÁ]: Servo SẼ quay tới 135° | Đèn LED nháy 3 lần");
    blinkFeedback(3, 180);
  } else {
    Serial.printf("⚠️ [KHÁC]: Không rõ màu '%s' | Đèn LED nháy nhanh cảnh báo\n", color.c_str());
    blinkFeedback(5, 100);
    return;
  }

  // Gửi thông báo ACK xác nhận lại lên MQTT
  if (mqttClient.connected()) {
    String ackMsg = "{\"device\":\"ESP32_Test\",\"color\":\"" + color + "\",\"status\":\"PROCESSED_OK\"}";
    mqttClient.publish(TOPIC_STATUS, ackMsg.c_str());
    Serial.println("📤 [MQTT Tx] Đã gửi bản tin xác nhận lên topic: " + String(TOPIC_STATUS));
  }
  Serial.println("==================================================");
}

// ==========================================
// 6. XỬ LÝ BẢN TIN MQTT NHẬN ĐƯỢC
// ==========================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.printf("\n[MQTT Rx] Topic [%s]: %s\n", topic, message.c_str());

  // Phân tích JSON hoặc chuỗi chữ
  String color = "";
  #if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument doc;
  #else
    StaticJsonDocument<256> doc;
  #endif

  DeserializationError err = deserializeJson(doc, message);
  if (!err && doc["color"]) {
    color = String(doc["color"].as<const char*>());
  } else {
    // Dự phòng tìm từ khóa
    String upper = message;
    upper.toUpperCase();
    if (upper.indexOf("RED") >= 0) color = "RED";
    else if (upper.indexOf("YELLOW") >= 0) color = "YELLOW";
    else if (upper.indexOf("GREEN") >= 0) color = "GREEN";
  }

  if (color.length() > 0) {
    executeColorCommand(color);
  }
}

// ==========================================
// 7. KẾT NỐI WI-FI & MQTT
// ==========================================
void setupWiFi() {
  Serial.printf("\n[WiFi] Đang kết nối tới: %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] ✅ Kết nối thành công!");
    Serial.print("[WiFi] Địa chỉ IP ESP32: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WiFi] ⚠️ Chưa kết nối được Wi-Fi. Bạn vẫn có thể test bằng Serial Monitor bên dưới!");
  }
}

void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;

  while (!mqttClient.connected()) {
    Serial.printf("[MQTT] Đang kết nối broker %s:%d ... ", MQTT_BROKER, MQTT_PORT);
    String clientId = "ESP32_Test_" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("✅ Thành công!");
      mqttClient.subscribe(TOPIC_CONTROL);
      Serial.printf("[MQTT] Đã Subscribe: %s\n", TOPIC_CONTROL);
    } else {
      Serial.printf("❌ Thất bại (rc=%d). Thử lại sau 3 giây...\n", mqttClient.state());
      delay(3000);
      break; // Không treo vòng lặp để Serial vẫn nhận lệnh
    }
  }
}

// ==========================================
// 8. SETUP & LOOP CHÍNH
// ==========================================
void setup() {
  Serial.begin(115200);
  pinMode(ONBOARD_LED_PIN, OUTPUT);
  digitalWrite(ONBOARD_LED_PIN, LOW);

  delay(500);
  Serial.println("\n\n==================================================");
  Serial.println("🚀 CHƯƠNG TRÌNH KIỂM TRA ĐỘC LẬP BOARD ESP32");
  Serial.println("==================================================");

  // 1. In thông tin chip
  printChipInfo();

  // 2. Nháy LED chào mừng 3 lần để test đèn LED trên board
  Serial.println("💡 [LED Test] Đang nháy đèn LED tích hợp (GPIO 2) 3 lần...");
  blinkFeedback(3, 150);

  // 3. Quét mạng Wi-Fi
  scanNearbyWiFi();

  // 4. Kết nối mạng Wi-Fi đã cấu hình
  setupWiFi();

  // 5. Cấu hình MQTT
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  Serial.println("\n--------------------------------------------------");
  Serial.println("💡 HƯỚNG DẪN TEST NHANH QUA SERIAL MONITOR:");
  Serial.println(" 👉 Bạn có thể gõ trực tiếp RED, YELLOW hoặc GREEN vào ô gửi");
  Serial.println("    của Serial Monitor rồi ấn Enter để test phản hồi!");
  Serial.println("--------------------------------------------------\n");
}

void loop() {
  // Duy trì kết nối MQTT nếu có Wi-Fi
  if (WiFi.status() == WL_CONNECTED) {
    if (!mqttClient.connected()) {
      reconnectMQTT();
    }
    mqttClient.loop();
  }

  // Đọc lệnh từ Serial Monitor (cho phép test trực tiếp bằng bàn phím máy tính)
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() > 0) {
      executeColorCommand(input);
    }
  }

  // Nhịp tim (Heartbeat): Nháy LED nhẹ mỗi 2 giây để biết ESP32 vẫn đang chạy mượt mà
  unsigned long now = millis();
  if (now - lastBlinkTime >= 2000) {
    lastBlinkTime = now;
    digitalWrite(ONBOARD_LED_PIN, HIGH);
    delay(40); // Chớp nhẹ 40ms
    digitalWrite(ONBOARD_LED_PIN, LOW);
  }
}
