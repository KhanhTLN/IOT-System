import os
import sys
import json
import threading
from typing import List

# Đảm bảo Python nhận diện các module trong thư mục cloud_server/backend khi chạy từ thư mục gốc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, get_db, SessionLocal
from models import SortingLog
from schemas import SortingLogCreate, SortingLogResponse
from analytics import calculate_stats

# Khởi tạo cơ sở dữ liệu nếu chưa có bảng
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="IoT Sorting System Cloud API",
    description="API quản lý và phân tích hệ thống phân loại 3 màu (Đỏ, Vàng, Xanh lá)",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "system": "IoT Sorting System Backend",
        "status": "online",
        "docs_url": "/docs"
    }

@app.post("/api/v1/logs", response_model=SortingLogResponse, status_code=status.HTTP_201_CREATED)
def create_sorting_log(log_data: SortingLogCreate, db: Session = Depends(get_db)):
    """
    Endpoint nhận dữ liệu log phân loại từ Local Edge / Client.
    """
    valid_colors = ["RED", "YELLOW", "GREEN"]
    color_upper = log_data.color_label.upper()
    if color_upper not in valid_colors:
        raise HTTPException(
            status_code=400, 
            detail=f"Màu không hợp lệ. Chỉ chấp nhận các màu: {valid_colors}"
        )

    new_log = SortingLog(
        color_label=color_upper,
        confidence=log_data.confidence
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log

@app.get("/api/v1/logs", response_model=List[SortingLogResponse])
def get_sorting_logs(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """
    Lấy danh sách các log phân loại mới nhất.
    """
    logs = db.query(SortingLog).order_by(SortingLog.id.desc()).offset(offset).limit(limit).all()
    return logs

@app.get("/api/v1/stats")
def get_sorting_stats(db: Session = Depends(get_db)):
    """
    Lấy dữ liệu thống kê tổng hợp (Số lượng từng màu, tỷ lệ %, năng suất, cảnh báo).
    """
    return calculate_stats(db)

# Option: MQTT Consumer tích hợp chạy background
def start_mqtt_consumer():
    mqtt_broker = os.getenv("MQTT_BROKER", "broker.hivemq.com")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic = os.getenv("MQTT_TOPIC", "factory/sorting/logs")

    try:
        import paho.mqtt.client as mqtt

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"[MQTT Cloud Consumer] Kết nối MQTT Broker thành công! Listening on {mqtt_topic}")
                client.subscribe(mqtt_topic)
            else:
                print(f"[MQTT Cloud Consumer] Kết nối MQTT Broker thất bại, rc={rc}")

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
                color = payload.get("color") or payload.get("color_label")
                confidence = payload.get("confidence", 1.0)
                if color and color.upper() in ["RED", "YELLOW", "GREEN"]:
                    db = SessionLocal()
                    new_log = SortingLog(color_label=color.upper(), confidence=float(confidence))
                    db.add(new_log)
                    db.commit()
                    db.close()
                    print(f"[MQTT Cloud Consumer] Đã lưu log từ MQTT: {color.upper()}")
            except Exception as e:
                print(f"[MQTT Cloud Consumer] Lỗi xử lý MQTT message: {e}")

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(mqtt_broker, mqtt_port, 60)
        client.loop_start()
    except Exception as e:
        print(f"[MQTT Cloud Consumer] Không thể khởi chạy MQTT listener: {e}")

@app.on_event("startup")
def startup_event():
    # Khởi động MQTT Consumer trong luồng phụ khi khởi động server
    threading.Thread(target=start_mqtt_consumer, daemon=True).start()
