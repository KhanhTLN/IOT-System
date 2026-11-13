#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <stdio.h>
#include "secrets.h"

// ==============================================================
// 1. CẤU HÌNH WI-FI & MQTT BROKER
// ==============================================================
// Các thông số WIFI_SSID, WIFI_PASSWORD, MQTT_BROKER, MQTT_PORT,
// MQTT_TOPIC_SERVO, MQTT_TOPIC_STATUS được quản lý an toàn trong file "secrets.h"

// ==============================================================
// 2. CẤU HÌNH CHÂN PHẦN CỨNG THỰC TẾ (3 SERVO + 6 CẢM BIẾN IR)
// ==============================================================

// --- TRẠM 1: HỘP ĐỎ (RED) ---
const int SERVO_RED_PIN = 25; // Servo gạt Đỏ
const int IR1_RED_PIN   = 18; // Cảm biến đón vạch gạt Đỏ (3 chân)
const int IR2_RED_PIN   = 19; // Cảm biến miệng thùng Đỏ  (3 chân)

// --- TRẠM 2: HỘP XANH (BLUE / GREEN) ---
const int SERVO_XANH_PIN = 33; // Servo gạt Xanh
const int IR3_XANH_PIN   = 21; // Cảm biến đón vạch gạt Xanh (4 chân - DO)
const int IR4_XANH_PIN   = 22; // Cảm biến miệng thùng Xanh  (4 chân - DO)

// --- TRẠM 3: HỘP VÀNG (YELLOW) ---
const int SERVO_VANG_PIN = 32; // Servo gạt Vàng
const int IR5_VANG_PIN   = 23; // Cảm biến đón vạch gạt Vàng (4 chân - DO)
const int IR6_VANG_PIN   = 34; // Cảm biến miệng thùng Vàng  (4 chân - DO)

// Góc định vị Servo gạt
const int ANGLE_HOME = 0;   // Vị trí nghỉ (mở đường cho hộp đi qua)
const int ANGLE_SORT = 45;  // Góc vươn ra gạt hộp vào thùng

// Thời gian bảo vệ chống kẹt hộp tối đa (5 giây)
const unsigned long TIMEOUT_MS = 5000;
// Thời gian trễ tối thiểu trước khi cho phép cảm biến thùng kích hoạt thu tay (tránh dội tức thì)
const unsigned long MIN_DROP_WAIT_MS = 300; 

// Khởi tạo 3 đối tượng Servo
Servo servoRed;
Servo servoXanh;
Servo servoVang;

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Máy trạng thái hoạt động độc lập cho 3 trạm phân loại (Chạy song song)
enum StationState {
  STATE_IDLE,              // Nghỉ, chờ Camera AI nhận diện màu
  STATE_ARMED,             // Đã nhận diện cờ từ Camera AI, chờ hộp trôi đến vạch đón
  STATE_SORTING_WAIT_DROP  // Đang gạt 45°, chờ hộp rơi qua cảm biến thùng
};

StationState stateRed  = STATE_IDLE;
StationState stateXanh = STATE_IDLE;
StationState stateVang = STATE_IDLE;

// Đồng hồ tính giờ an toàn chống kẹt
unsigned long timerRed  = 0;
unsigned long timerXanh = 0;
unsigned long timerVang = 0;

// Bộ lưu trạng thái bắt sườn xuống (HIGH -> LOW)
int lastIr1 = HIGH, lastIr2 = HIGH;
int lastIr3 = HIGH, lastIr4 = HIGH;
int lastIr5 = HIGH, lastIr6 = HIGH;

// Biến hỗ trợ kiểm thử & giám sát
bool autoTestMode = false;      // false: Tự động hoàn toàn theo Camera AI; true: Test tự do mọi hộp
bool liveMonitorMode = false;   // Bật/tắt in trạng thái 6 cảm biến ra Serial Monitor
unsigned long lastMonitorPrint = 0;
unsigned long lastSerialCmdTime = 0;
unsigned long lastWiFiCheckTime = 0;

// ==============================================================
// 3. HÀM KẾT NỐI WI-FI (TỰ ĐỘNG CHẨN ĐOÁN LỖI)
// ==============================================================
void printWiFiStatus(wl_status_t status) {
  switch (status) {
    case WL_NO_SSID_AVAIL:
      Serial.println("\n❌ [LỖI WIFI] Không tìm thấy tên mạng SSID này! (Sai tên hoặc router ở quá xa).");
      break;
    case WL_CONNECT_FAILED:
      Serial.println("\n❌ [LỖI WIFI] Sai mật khẩu Wi-Fi hoặc router từ chối kết nối.");
      break;
    case WL_CONNECTION_LOST:
      Serial.println("\n❌ [LỖI WIFI] Mất kết nối sóng giữa chừng.");
      break;
    case WL_DISCONNECTED:
      Serial.println("\n❌ [LỖI WIFI] Mạch bị ngắt kết nối khỏi mạng.");
      break;
    default:
      Serial.printf("\n❌ [LỖI WIFI] Mã trạng thái lỗi: %d\n", (int)status);
      break;
  }
}

void scanNearbyNetworks() {
  Serial.println("\n🔍 [WiFi Scanner] Đang quét các mạng Wi-Fi 2.4GHz xung quanh...");
  WiFi.disconnect();
  delay(100);
  int n = WiFi.scanNetworks();
  if (n == 0) {
    Serial.println("⚠️ Không tìm thấy mạng Wi-Fi 2.4GHz nào ở xung quanh!");
  } else {
    Serial.printf("✅ Tìm thấy %d mạng Wi-Fi 2.4GHz xung quanh:\n", n);
    for (int i = 0; i < n; ++i) {
      Serial.printf("   👉 \"%s\" (Sóng: %d dBm)\n", 
                    WiFi.SSID(i).c_str(), 
                    WiFi.RSSI(i));
      delay(10);
    }
  }
}

void setupWiFi() {
  delay(100);
  Serial.println("\n----------------------------------------");
  Serial.print("[WiFi] Đang thử kết nối tới SSID: \"");
  Serial.print(WIFI_SSID);
  Serial.println("\"");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true);
  delay(200);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int retryCount = 0;
  const int maxRetries = 25; // Chờ tối đa 12.5 giây lúc khởi động

  while (WiFi.status() != WL_CONNECTED && retryCount < maxRetries) {
    delay(500);
    Serial.print(".");
    retryCount++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] ✅ ĐÃ KẾT NỐI WI-FI THÀNH CÔNG!");
    Serial.print("[WiFi] Địa chỉ IP ESP32 trong mạng: ");
    Serial.println(WiFi.localIP());
  } else {
    printWiFiStatus(WiFi.status());
    scanNearbyNetworks();
  }
}

// ==============================================================
// 4. HÀM XỬ LÝ BẢN TIN MQTT TỪ CAMERA AI (EDGE NODE)
// ==============================================================
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

  // 1. Phân tích JSON từ Camera Edge Node
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
    // Dự phòng quét trực tiếp chuỗi chữ nếu JSON bị lỗi định dạng
    String upperMsg = message;
    upperMsg.toUpperCase();
    if (upperMsg.indexOf("RED") >= 0) colorStr = "RED";
    else if (upperMsg.indexOf("BLUE") >= 0 || upperMsg.indexOf("GREEN") >= 0 || upperMsg.indexOf("XANH") >= 0) colorStr = "BLUE";
    else if (upperMsg.indexOf("YELLOW") >= 0 || upperMsg.indexOf("VANG") >= 0) colorStr = "YELLOW";
  }

  colorStr.toUpperCase();

  // 2. Kích hoạt cờ ARMED cho trạm tương ứng
  if (colorStr.length() > 0) {
    if (colorStr == "RED") {
      stateRed = STATE_ARMED;
      Serial.printf("🔴 [Camera AI] Nhận diện HỘP ĐỎ (Tin cậy: %.2f) -> Kích hoạt TRẠM 1!\n", confidence);
      Serial.println("   👉 Chờ hộp Đỏ trôi tới vạch đón IR1 trên băng chuyền...");
    } else if (colorStr == "BLUE" || colorStr == "GREEN" || colorStr == "XANH") {
      stateXanh = STATE_ARMED;
      Serial.printf("🔵 [Camera AI] Nhận diện HỘP XANH (Tin cậy: %.2f) -> Kích hoạt TRẠM 2!\n", confidence);
      Serial.println("   👉 Hộp trôi qua Trạm 1 (Servo 1 ở 0°) và chờ tới vạch đón IR3...");
    } else if (colorStr == "YELLOW" || colorStr == "VANG") {
      stateVang = STATE_ARMED;
      Serial.printf("🟡 [Camera AI] Nhận diện HỘP VÀNG (Tin cậy: %.2f) -> Kích hoạt TRẠM 3!\n", confidence);
      Serial.println("   👉 Hộp trôi qua Trạm 1 & 2 (Servo ở 0°) và chờ tới vạch đón IR5...");
    } else {
      Serial.print("⚠️ [Camera AI] Màu không nằm trong danh mục phân loại: ");
      Serial.println(colorStr);
    }
  } else {
    Serial.println("⚠️ [Action] Không tìm thấy nhãn màu hợp lệ trong bản tin!");
  }
}

// ==============================================================
// 5. HÀM KẾT NỐI & TỰ PHỤC HỒI MQTT
// ==============================================================
void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;

  Serial.print("[MQTT] Đang kết nối tới Broker Mosquitto...");
  String clientId = "ESP32_Sorting_Actuator_" + String(random(0xffff), HEX);

  if (mqttClient.connect(clientId.c_str())) {
    Serial.println(" ✅ Đã kết nối!");
    
    // Báo cáo trạng thái Online của Actuator 3 Trạm
    #if ARDUINOJSON_VERSION_MAJOR >= 7
      JsonDocument statusDoc;
    #else
      StaticJsonDocument<128> statusDoc;
    #endif
    statusDoc["device"] = "ESP32_Actuator";
    statusDoc["status"] = "ONLINE";
    statusDoc["stations"] = 3;
    char statusBuf[128];
    serializeJson(statusDoc, statusBuf);
    mqttClient.publish(MQTT_TOPIC_STATUS, statusBuf);

    // Đăng ký nhận lệnh điều khiển Servo từ Camera Edge
    mqttClient.subscribe(MQTT_TOPIC_SERVO);
    Serial.print("[MQTT] Đã Subscribe Topic: ");
    Serial.println(MQTT_TOPIC_SERVO);
  } else {
    Serial.print(" ❌ Thất bại, mã lỗi rc=");
    Serial.print(mqttClient.state());
    Serial.println(" Sẽ tự thử lại...");
  }
}

// ==============================================================
// 6. SETUP & LOOP CHÍNH (ĐỒNG BỘ 3 TRẠM + CAMERA AI)
// ==============================================================
void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n==================================================================");
  Serial.println("🏭 DÂY CHUYỀN PHÂN LOẠI 3 TRẠM (ESP32 + CAMERA AI + IR SENSOR)");
  Serial.println("==================================================================");

  // 1. Cấu hình chân cảm biến hồng ngoại
  pinMode(IR1_RED_PIN,  INPUT_PULLUP);
  pinMode(IR2_RED_PIN,  INPUT_PULLUP);
  pinMode(IR3_XANH_PIN, INPUT_PULLUP);
  pinMode(IR4_XANH_PIN, INPUT_PULLUP);
  pinMode(IR5_VANG_PIN, INPUT_PULLUP);
  pinMode(IR6_VANG_PIN, INPUT); // GPIO 34 không có trở kéo nội trên ESP32

  // 2. Cấp phát Timer PWM độc lập cho 3 Servo
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);

  servoRed.setPeriodHertz(50);
  servoXanh.setPeriodHertz(50);
  servoVang.setPeriodHertz(50);

  servoRed.attach(SERVO_RED_PIN, 500, 2400);
  servoXanh.attach(SERVO_XANH_PIN, 500, 2400);
  servoVang.attach(SERVO_VANG_PIN, 500, 2400);

  // Đưa cả 3 Servo về góc nghỉ 0° sẵn sàng
  servoRed.write(ANGLE_HOME);
  servoXanh.write(ANGLE_HOME);
  servoVang.write(ANGLE_HOME);

  Serial.println("  [TRẠM 1 - ĐỎ]  : Servo (Pin 25) | IR Đón (Pin 18) | IR Thùng (Pin 19)");
  Serial.println("  [TRẠM 2 - XANH]: Servo (Pin 33) | IR Đón (Pin 21) | IR Thùng (Pin 22)");
  Serial.println("  [TRẠM 3 - VÀNG]: Servo (Pin 32) | IR Đón (Pin 23) | IR Thùng (Pin 34)");
  Serial.println("------------------------------------------------------------------");
  Serial.println("  🤖 HỆ THỐNG SẴN SÀNG NHẬN LỆNH TỰ ĐỘNG TỪ CAMERA AI QUA MQTT!");
  Serial.println("  👉 Gõ [ t ] : Bật/Tắt chế độ Test tự do (mọi hộp đi qua đều gạt)");
  Serial.println("  👉 Gõ [ m ] : Bật/Tắt màn hình Live Monitor soi trực tiếp 6 cảm biến");
  Serial.println("  👉 Gõ [ 0 ] : Dừng khẩn cấp đưa cả 3 Servo về 0°");
  Serial.println("==================================================================\n");

  // 3. Kết nối Wi-Fi & MQTT
  setupWiFi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  // 1. Quản lý kết nối Wi-Fi & MQTT định kỳ (Non-blocking)
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWiFiCheckTime >= 4000) {
      lastWiFiCheckTime = millis();
      Serial.println("[WiFi Warning] Mất kết nối Wi-Fi, đang thử kết nối lại...");
      WiFi.reconnect();
    }
  } else {
    if (!mqttClient.connected()) {
      if (millis() - lastWiFiCheckTime >= 3000) {
        lastWiFiCheckTime = millis();
        reconnectMQTT();
      }
    } else {
      mqttClient.loop();
    }
  }

  // 2. Đọc tín hiệu 6 cảm biến (LOW = Có vật cản, HIGH = Thông thoáng)
  int ir1 = digitalRead(IR1_RED_PIN);
  int ir2 = digitalRead(IR2_RED_PIN);
  int ir3 = digitalRead(IR3_XANH_PIN);
  int ir4 = digitalRead(IR4_XANH_PIN);
  int ir5 = digitalRead(IR5_VANG_PIN);
  int ir6 = digitalRead(IR6_VANG_PIN);

  // Màn hình Live Monitor kiểm tra tín hiệu cảm biến theo thời gian thực (Khi bấm 'm')
  if (liveMonitorMode && (millis() - lastMonitorPrint >= 400)) {
    lastMonitorPrint = millis();
    Serial.printf("[ĐỎ: IR1=%d IR2=%d]  |  [XANH: IR3=%d IR4=%d]  |  [VÀNG: IR5=%d IR6=%d]\n",
                  ir1, ir2, ir3, ir4, ir5, ir6);
  }

  // ==============================================================
  // 3. LOGIC TRẠM 1: HỘP ĐỎ (RED)
  // ==============================================================
  if (lastIr1 == HIGH && ir1 == LOW) {
    if (stateRed == STATE_ARMED || autoTestMode) {
      Serial.println("🔴 [TRẠM 1 - ĐỎ] >>> Hộp Đỏ chạm IR1: SERVO 1 GẠT 45°!");
      servoRed.write(ANGLE_SORT);
      stateRed = STATE_SORTING_WAIT_DROP;
      timerRed = millis();
    }
  }
  lastIr1 = ir1;

  if (stateRed == STATE_SORTING_WAIT_DROP) {
    if (millis() - timerRed >= MIN_DROP_WAIT_MS && lastIr2 == HIGH && ir2 == LOW) {
      Serial.println("📥 [TRẠM 1 - ĐỎ] >>> Hộp rơi vào thùng: SERVO 1 THU VỀ 0°!\n");
      servoRed.write(ANGLE_HOME);
      stateRed = STATE_IDLE;
    } else if (millis() - timerRed >= TIMEOUT_MS) {
      Serial.println("🚨 [TRẠM 1] Hết 5s an toàn -> Tự thu Servo 1 về 0°!\n");
      servoRed.write(ANGLE_HOME);
      stateRed = STATE_IDLE;
    }
  }
  lastIr2 = ir2;

  // ==============================================================
  // 4. LOGIC TRẠM 2: HỘP XANH (BLUE / GREEN)
  // ==============================================================
  if (lastIr3 == HIGH && ir3 == LOW) {
    if (stateXanh == STATE_ARMED || autoTestMode) {
      Serial.println("🔵 [TRẠM 2 - XANH] >>> Hộp Xanh chạm IR3: SERVO 2 GẠT 45°!");
      servoXanh.write(ANGLE_SORT);
      stateXanh = STATE_SORTING_WAIT_DROP;
      timerXanh = millis();
    }
  }
  lastIr3 = ir3;

  if (stateXanh == STATE_SORTING_WAIT_DROP) {
    if (millis() - timerXanh >= MIN_DROP_WAIT_MS && lastIr4 == HIGH && ir4 == LOW) {
      Serial.println("📥 [TRẠM 2 - XANH] >>> Hộp rơi vào thùng: SERVO 2 THU VỀ 0°!\n");
      servoXanh.write(ANGLE_HOME);
      stateXanh = STATE_IDLE;
    } else if (millis() - timerXanh >= TIMEOUT_MS) {
      Serial.println("🚨 [TRẠM 2] Hết 5s an toàn -> Tự thu Servo 2 về 0°!\n");
      servoXanh.write(ANGLE_HOME);
      stateXanh = STATE_IDLE;
    }
  }
  lastIr4 = ir4;

  // ==============================================================
  // 5. LOGIC TRẠM 3: HỘP VÀNG (YELLOW)
  // ==============================================================
  if (lastIr5 == HIGH && ir5 == LOW) {
    if (stateVang == STATE_ARMED || autoTestMode) {
      Serial.println("🟡 [TRẠM 3 - VÀNG] >>> Hộp Vàng chạm IR5: SERVO 3 GẠT 45°!");
      servoVang.write(ANGLE_SORT);
      stateVang = STATE_SORTING_WAIT_DROP;
      timerVang = millis();
    }
  }
  lastIr5 = ir5;

  if (stateVang == STATE_SORTING_WAIT_DROP) {
    if (millis() - timerVang >= MIN_DROP_WAIT_MS && lastIr6 == HIGH && ir6 == LOW) {
      Serial.println("📥 [TRẠM 3 - VÀNG] >>> Hộp rơi vào thùng: SERVO 3 THU VỀ 0°!\n");
      servoVang.write(ANGLE_HOME);
      stateVang = STATE_IDLE;
    } else if (millis() - timerVang >= TIMEOUT_MS) {
      Serial.println("🚨 [TRẠM 3] Hết 5s an toàn -> Tự thu Servo 3 về 0°!\n");
      servoVang.write(ANGLE_HOME);
      stateVang = STATE_IDLE;
    }
  }
  lastIr6 = ir6;

  // ==============================================================
  // 6. NHẬN LỆNH ĐIỀU KHIỂN DỰ PHÒNG TỪ SERIAL MONITOR
  // ==============================================================
  if (Serial.available() > 0) {
    char key = tolower(Serial.read());
    if (key == '\n' || key == '\r' || key == ' ') return;

    if (millis() - lastSerialCmdTime < 250) {
      while (Serial.available() > 0) Serial.read();
      return;
    }
    lastSerialCmdTime = millis();
    while (Serial.available() > 0) Serial.read();

    switch (key) {
      case 'm':
        liveMonitorMode = !liveMonitorMode;
        Serial.println(liveMonitorMode ? "\n🔍 [LIVE MONITOR: BẬT] Đang in trạng thái 6 cảm biến..."
                                       : "\n🛑 [LIVE MONITOR: TẮT]");
        break;

      case 't':
        autoTestMode = !autoTestMode;
        Serial.println(autoTestMode ? "\n⚡ [TEST TỰ DO: BẬT] Mọi hộp qua trạm nào trạm đó gạt (Không cần Camera)." 
                                    : "\n🔒 [CHẾ ĐỘ CAMERA: BẬT] Chỉ gạt khi Camera AI phát hiện đúng màu.");
        break;

      case 'r':
        stateRed = STATE_ARMED;
        Serial.println("🔴 [Thủ công] Đã kích hoạt cờ Trạm 1 (ĐỎ).");
        break;

      case 'x':
      case 'b':
        stateXanh = STATE_ARMED;
        Serial.println("🔵 [Thủ công] Đã kích hoạt cờ Trạm 2 (XANH).");
        break;

      case 'v':
      case 'y':
        stateVang = STATE_ARMED;
        Serial.println("🟡 [Thủ công] Đã kích hoạt cờ Trạm 3 (VÀNG).");
        break;

      case '0':
        stateRed  = STATE_IDLE;
        stateXanh = STATE_IDLE;
        stateVang = STATE_IDLE;
        servoRed.write(ANGLE_HOME);
        servoXanh.write(ANGLE_HOME);
        servoVang.write(ANGLE_HOME);
        Serial.println("🛑 [DỪNG KHẨN CẤP] Cả 3 Servo về góc 0°!\n");
        break;
    }
  }
}
