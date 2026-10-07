import sys
import os

# Đảm bảo in tiếng Việt mượt mà trên Windows PowerShell / CMD
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import json
import time
import datetime
import threading
import requests
import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_SERVO_TOPIC, MQTT_STATUS_TOPIC, MQTT_CLIENT_ID,
    API_LOGS_ENDPOINT, HTTP_TIMEOUT_SECONDS
)

class EdgeDispatcher:
    def __init__(self):
        self.client = mqtt.Client(client_id=f"{MQTT_CLIENT_ID}_{int(time.time())}")
        self.is_connected = False
        
        # Thiết lập callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        self._init_mqtt()

    def _init_mqtt(self):
        """Khởi tạo và kết nối MQTT Broker không chặn luồng chính (Non-blocking)"""
        try:
            print(f"[MQTT] Đang kết nối tới Broker: {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            print(f"[MQTT Error] Không thể kết nối tới Broker: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            print(f"[MQTT] ✅ Kết nối Broker thành công (Topic: {MQTT_SERVO_TOPIC})")
            # Gửi tin báo trạng thái Online
            self.publish_status("ONLINE")
        else:
            print(f"[MQTT] ⚠️ Kết nối thất bại với mã code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        print(f"[MQTT] 🔌 Mất kết nối tới Broker (Code: {rc}). Tự động thử lại...")

    def publish_status(self, status: str):
        """Gửi trạng thái hoạt động của Edge Node lên MQTT"""
        payload = {
            "device": "Edge_CV_Detector",
            "status": status,
            "timestamp": datetime.datetime.now().isoformat()
        }
        try:
            self.client.publish(MQTT_STATUS_TOPIC, json.dumps(payload), qos=1)
        except Exception as e:
            print(f"[MQTT Status Error] {e}")

    def _send_cloud_log_async(self, color_label: str, confidence: float):
        """Gửi HTTP POST lên Cloud Backend trong Background Thread để không làm giật lag FPS của Camera"""
        try:
            payload = {
                "color_label": color_label,
                "confidence": round(confidence, 3)
            }
            response = requests.post(
                API_LOGS_ENDPOINT,
                json=payload,
                timeout=HTTP_TIMEOUT_SECONDS
            )
            if response.status_code == 201 or response.status_code == 200:
                print(f"[Cloud Sync] ☁️ Đã lưu log lên Cloud Backend: {color_label} (ID: {response.json().get('id')})")
            else:
                print(f"[Cloud Sync Warning] Phản hồi từ Backend: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[Cloud Sync Error] Không thể gửi HTTP log tới Cloud: {e}")

    def dispatch_sorting_event(self, color_label: str, confidence: float = 1.0):
        """
        Bắn tín hiệu đồng thời:
        1. Gửi MQTT tới ESP32 điều khiển gạt Servo
        2. Gửi HTTP Request lên Cloud Backend lưu Database
        """
        # 1. Bắn bản tin MQTT cho ESP32 / Wokwi
        mqtt_payload = {
            "color": color_label.upper(),
            "confidence": round(confidence, 3),
            "timestamp": datetime.datetime.now().isoformat()
        }
        try:
            self.client.publish(MQTT_SERVO_TOPIC, json.dumps(mqtt_payload), qos=1)
            print(f"[Dispatch] 📡 Bắn MQTT -> ESP32: {mqtt_payload['color']} (Conf: {confidence:.2f})")
        except Exception as e:
            print(f"[Dispatch MQTT Error] {e}")

        # 2. Bắn HTTP Log bất đồng bộ lên Cloud Backend
        thread = threading.Thread(
            target=self._send_cloud_log_async,
            args=(color_label.upper(), confidence),
            daemon=True
        )
        thread.start()

    def close(self):
        """Ngắt kết nối an toàn"""
        self.publish_status("OFFLINE")
        self.client.loop_stop()
        self.client.disconnect()
        print("[MQTT] Đã đóng kết nối.")

# Singleton Dispatcher
dispatcher = EdgeDispatcher()
