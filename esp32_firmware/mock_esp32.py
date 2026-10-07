import json
import time
import datetime
import paho.mqtt.client as mqtt
import sys

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_SERVO = "factory/servo/control"
MQTT_TOPIC_STATUS = "factory/system/status"

ANGLE_HOME = 0
ANGLE_RED = 45
ANGLE_YELLOW = 90
ANGLE_GREEN = 135

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("\n=======================================================")
        print("🤖 [MOCK ESP32 ACTUATOR] ĐÃ KẾT NỐI BROKER THÀNH CÔNG!")
        print(f"📡 Lắng nghe Topic: {MQTT_TOPIC_SERVO}")
        print("⚙️  Servo SG90 sẵn sàng tại vị trí nghỉ: 0°")
        print("=======================================================\n")
        
        # Báo cáo Online
        status_payload = {
            "device": "Mock_ESP32_Actuator",
            "status": "ONLINE",
            "servo_pin": 18
        }
        client.publish(MQTT_TOPIC_STATUS, json.dumps(status_payload))
        client.subscribe(MQTT_TOPIC_SERVO)
    else:
        print(f"❌ Kết nối thất bại với mã lỗi: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        color = payload.get("color", "").upper()
        confidence = payload.get("confidence", 1.0)
        
        target_angle = ANGLE_HOME
        emoji = "❓"
        
        if color == "RED":
            target_angle = ANGLE_RED
            emoji = "🔴"
        elif color == "YELLOW":
            target_angle = ANGLE_YELLOW
            emoji = "🟡"
        elif color == "GREEN":
            target_angle = ANGLE_GREEN
            emoji = "🟢"
        else:
            print(f"⚠️ [ESP32] Nhận màu không hợp lệ: {color}")
            return
            
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {emoji} [MQTT NHẬN ĐƯỢC] -> SẢN PHẨM: {color} (Độ tin cậy: {confidence*100:.1f}%)")
        print(f"          ⚙️ [SERVO SG90] -> QUAY GÓC: {target_angle}° ĐỂ GẠT SẢN PHẨM...")
        
        # Giả lập giữ góc gạt trong 2 giây rồi hồi vị
        time.sleep(2)
        print(f"          🔄 [SERVO SG90] -> HỒI VỊ VỀ GÓC NGHỈ: 0° (Sẵn sàng lượt tiếp theo)\n")
        
    except Exception as e:
        print(f"❌ Lỗi xử lý bản tin MQTT: {e}")

def main():
    client = mqtt.Client(client_id=f"Mock_ESP32_{int(time.time())}")
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"[*] Đang kết nối tới MQTT Broker ({MQTT_BROKER}:{MQTT_PORT})...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[!] Đã dừng giả lập ESP32.")
        client.disconnect()

if __name__ == "__main__":
    main()
