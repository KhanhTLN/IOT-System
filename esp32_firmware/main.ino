#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>

// ==========================================
// 1. CẤU HÌNH WI-FI & MQTT BROKER
// ==========================================
// Nếu dùng Wokwi: giữ "Wokwi-GUEST", pass ""
// Nếu dùng Mạch ESP32 thật: Điền SSID và mật khẩu Wi-Fi của bạn (2.4GHz)
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// CẤU HÌNH ECLIPSE MOSQUITTO BROKER:
// - Với Mạch Thật: Điền IP máy tính chạy Mosquitto trong mạng LAN (Lệnh Windows: ipconfig, VD: "192.168.1.15")
// - Với Wokwi giả lập: Điền "broker.hivemq.com" (Do máy ảo cloud Wokwi không nhìn thấy IP LAN cá nhân)
const char* MQTT_BROKER = "192.168.1.15";
const int   MQTT_PORT = 1883;
const char* MQTT_TOPIC_SERVO = "factory/servo/control";
const char* MQTT_TOPIC_STATUS = "factory/system/status";

// ==========================================
// 2. CẤU HÌNH CHÂN PHẦN CỨNG & SERVO
// ==========================================
const int SERVO_PIN = 18;  // Chân PWM điều khiển Servo SG90

// Góc quay định vị phân loại từng màu
const int ANGLE_HOME   = 0;    // Vị trí nghỉ / Chờ ban đầu
const int ANGLE_RED    = 45;   // Góc gạt hàng màu ĐỎ
const int ANGLE_YELLOW = 90;   // Góc gạt hàng màu VÀNG
const int ANGLE_GREEN  = 135;  // Góc gạt hàng màu XANH LÁ

const unsigned long SERVO_RESET_DELAY_MS = 2000; // Thời gian giữ góc gạt trước khi về 0 độ (2 giây)

// Khởi tạo đối tượng
Servo sortingServo;
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Biến quản lý thời gian hồi vị không gây chặn chương trình (Non-blocking timer)
unsigned long servoActionStartTime = 0;
bool isServoActive = false;

// ==========================================
// 3. HÀM KẾT NỐI WI-FI
// ==========================================
void setupWiFi() {
  delay(10);
  Serial.println("\n----------------------------------------");
  Serial.print("[WiFi] Đang kết nối tới SSID: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n[WiFi] ✅ Đã kết nối Wi-Fi thành công!");
  Serial.print("[WiFi] Địa chỉ IP ESP32: ");
  Serial.println(WiFi.localIP());
}

// ==========================================
// 4. HÀM XỬ LÝ NHẬN BẢN TIN MQTT TỪ EDGE
// ==========================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("\n[MQTT Rx] Nhận bản tin từ Topic [");
  Serial.print(topic);
  Serial.print("]: ");

  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  String colorStr = "";
  float confidence = 1.0;

  // 1. Thử phân tích JSON (Tương thích cả ArduinoJson v6 và v7)
  #if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument doc;
  #else
    StaticJsonDocument<256> doc;
  #endif

  DeserializationError error = deserializeJson(doc, message);
  if (!error && doc["color"]) {
    colorStr = String(doc["color"].as<const char*>());
    if (doc["confidence"]) {
      confidence = doc["confidence"].as<float>();
    }
  } else {
    // 2. Dự phòng: Quét trực tiếp chuỗi chữ nếu JSON bị lỗi format
    String upperMsg = message;
    upperMsg.toUpperCase();
    if (upperMsg.indexOf("RED") >= 0) colorStr = "RED";
    else if (upperMsg.indexOf("YELLOW") >= 0) colorStr = "YELLOW";
    else if (upperMsg.indexOf("GREEN") >= 0) colorStr = "GREEN";
  }

  colorStr.toUpperCase();

  if (colorStr.length() > 0) {
    int targetAngle = ANGLE_HOME;
    if (colorStr == "RED") {
      targetAngle = ANGLE_RED;
      Serial.println("🔴 [Action] KÍCH HOẠT GẠT SẢN PHẨM: ĐỎ (RED) -> Quay 45°");
    } else if (colorStr == "YELLOW") {
      targetAngle = ANGLE_YELLOW;
      Serial.println("🟡 [Action] KÍCH HOẠT GẠT SẢN PHẨM: VÀNG (YELLOW) -> Quay 90°");
    } else if (colorStr == "GREEN") {
      targetAngle = ANGLE_GREEN;
      Serial.println("🟢 [Action] KÍCH HOẠT GẠT SẢN PHẨM: XANH LÁ (GREEN) -> Quay 135°");
    } else {
      Serial.print("⚠️ [Action] Màu không xác định: ");
      Serial.println(colorStr);
      return;
    }

    // Xoay Servo tới góc phân loại
    sortingServo.write(targetAngle);
    servoActionStartTime = millis();
    isServoActive = true;
    Serial.print("⚙️ [Servo] Đang quay tới góc: ");
    Serial.print(targetAngle);
    Serial.println("°");
  } else {
    Serial.println("⚠️ [Action] Không tìm thấy nhãn màu hợp lệ trong payload!");
  }
}

// ==========================================
// 5. HÀM KẾT NỐI & TỰ PHỤC HỒI MQTT
// ==========================================
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Đang kết nối tới Broker HiveMQ...");
    String clientId = "ESP32_Sorting_Actuator_" + String(random(0xffff), HEX);

    if (mqttClient.connect(clientId.c_str())) {
      Serial.println(" ✅ Đã kết nối!");
      
      // Báo cáo trạng thái Online
      #if ARDUINOJSON_VERSION_MAJOR >= 7
        JsonDocument statusDoc;
      #else
        StaticJsonDocument<128> statusDoc;
      #endif
      statusDoc["device"] = "ESP32_Actuator";
      statusDoc["status"] = "ONLINE";
      statusDoc["servo_pin"] = SERVO_PIN;
      char statusBuf[128];
      serializeJson(statusDoc, statusBuf);
      mqttClient.publish(MQTT_TOPIC_STATUS, statusBuf);

      // Đăng ký nhận lệnh điều khiển Servo
      mqttClient.subscribe(MQTT_TOPIC_SERVO);
      Serial.print("[MQTT] Đã Subscribe Topic: ");
      Serial.println(MQTT_TOPIC_SERVO);
    } else {
      Serial.print(" ❌ Thất bại, mã lỗi rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Thử lại sau 2 giây...");
      delay(2000);
    }
  }
}

// ==========================================
// 6. SETUP & LOOP CHÍNH
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n==========================================");
  Serial.println("🏭 ESP32 INDUSTRIAL SORTING CONTROLLER");
  Serial.println("==========================================");

  // Cấu hình Timer cho ESP32 Servo trên Wokwi
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  sortingServo.setPeriodHertz(50); // Chu kỳ chuẩn 50Hz cho Servo SG90
  sortingServo.attach(SERVO_PIN, 500, 2400); // Độ rộng xung 500us - 2400us
  
  // TỰ KIỂM TRA SERVO (Self-test) KHI VỪA KHỞI ĐỘNG
  Serial.println("[Servo] Đang tự kiểm tra góc quay Servo...");
  sortingServo.write(45);
  delay(400);
  sortingServo.write(90);
  delay(400);
  sortingServo.write(ANGLE_HOME);
  Serial.println("[Servo] ✅ Khởi tạo Servo tại vị trí nghỉ 0° sẵn sàng!");

  // Kết nối mạng
  setupWiFi();

  // Cấu hình MQTT
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  // Kiểm tra thời gian hồi vị Servo về 0 độ (Non-blocking)
  if (isServoActive && (millis() - servoActionStartTime >= SERVO_RESET_DELAY_MS)) {
    sortingServo.write(ANGLE_HOME);
    isServoActive = false;
    Serial.println("🔄 [Servo] Đã hồi vị về góc ban đầu 0° (Sẵn sàng nhận lượt tiếp theo)\n");
  }
}
