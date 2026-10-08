import os
import sys
import json
import io
import csv
import threading
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Đảm bảo Python nhận diện các module trong thư mục cloud_server/backend khi chạy từ thư mục gốc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, get_db, SessionLocal
from models import SortingLog, User, SystemConfig
from schemas import (
    SortingLogCreate, SortingLogResponse,
    UserCreate, UserLogin, UserResponse, TokenResponse, ConfigUpdate
)
from analytics import (
    calculate_stats, calculate_servo_health,
    calculate_oee_metrics, calculate_target_vs_actual, calculate_hourly_heatmap_matrix,
    parse_datetime, apply_shift_filter
)
from auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, require_role
)

# Khởi tạo cơ sở dữ liệu nếu chưa có bảng
Base.metadata.create_all(bind=engine)

def init_default_data():
    db = SessionLocal()
    try:
        # 1. Khởi tạo tài khoản admin nếu chưa có
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("[Init DB] Creating default admin user (admin / admin123)...")
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="Quan Ly Nha May",
                role="MANAGER"
            )
            db.add(admin_user)

        # 2. Khởi tạo tài khoản worker nếu chưa có
        worker_user = db.query(User).filter(User.username == "worker").first()
        if not worker_user:
            print("[Init DB] Creating default worker user (worker / worker123)...")
            worker_user = User(
                username="worker",
                hashed_password=get_password_hash("worker123"),
                full_name="Cong Nhan Van Hanh",
                role="WORKER"
            )
            db.add(worker_user)

        # 3. Khởi tạo cấu hình mặc định nếu chưa có
        default_configs = [
            ("anomaly_threshold", "10", "Nguong canh bao bat thuong"),
            ("servo_red_angle", "45", "Goc xoay Servo Mau Do"),
            ("servo_yellow_angle", "90", "Goc xoay Servo Mau Vang"),
            ("servo_green_angle", "135", "Goc xoay Servo Mau Xanh"),
            ("target_total_shift", "500", "Muc tieu san luong toan ca"),
            ("ideal_run_rate", "15.0", "Toc do thiet ke dinh muc (sp/phut)")
        ]
        for k, v, d in default_configs:
            cfg = db.query(SystemConfig).filter(SystemConfig.key == k).first()
            if not cfg:
                db.add(SystemConfig(key=k, value=v, description=d))

        db.commit()
        print("[Init DB] Default users and configs created successfully!")
    except Exception as e:
        print(f"[Init DB] Error creating default data: {e}")
    finally:
        db.close()


# Gọi tạo dữ liệu mặc định ngay khi load module
init_default_data()

app = FastAPI(
    title="IoT Sorting System Cloud API (RBAC Enabled)",
    description="API quản lý, xác thực phân quyền và phân tích hệ thống phân loại 3 màu",
    version="2.0.0"
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
        "version": "2.0 (RBAC & Auth Enabled)",
        "status": "online",
        "docs_url": "/docs"
    }

# --- AUTHENTICATION ROUTES ---
@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Endpoint đăng nhập lấy JWT Access Token (hỗ trợ JSON payload).
    """
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác"
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản đã bị vô hiệu hóa")

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/api/v1/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Lấy thông tin tài khoản đang đăng nhập.
    """
    return current_user

@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MANAGER"]))
):
    """
    Tạo tài khoản mới (Chỉ dành cho Quản lý / MANAGER).
    """
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")

    new_user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role.upper()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/api/v1/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MANAGER"]))
):
    """
    Danh sách toàn bộ người dùng (Chỉ MANAGER).
    """
    return db.query(User).all()

# --- LOGS & STATS ROUTES ---
@app.post("/api/v1/logs", response_model=SortingLogResponse, status_code=status.HTTP_201_CREATED)
def create_sorting_log(log_data: SortingLogCreate, db: Session = Depends(get_db)):
    """
    Endpoint nhận dữ liệu phân loại từ Edge Node / Mock Producer.
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
def get_sorting_logs(
    limit: int = 50, 
    offset: int = 0, 
    color_label: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    shift: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các log phân loại với bộ lọc tùy chọn (màu sắc, ngày giờ, ca làm việc).
    """
    query = db.query(SortingLog)
    
    if color_label and color_label.upper() not in ["ALL", "TAT_CA", ""]:
        query = query.filter(SortingLog.color_label == color_label.upper())
    
    dt_start = parse_datetime(start_time)
    dt_end = parse_datetime(end_time)
    if dt_start:
        query = query.filter(SortingLog.created_at >= dt_start)
    if dt_end:
        query = query.filter(SortingLog.created_at <= dt_end)
        
    query = apply_shift_filter(query, shift)
    
    logs = query.order_by(SortingLog.id.desc()).offset(offset).limit(limit).all()
    return logs

@app.get("/api/v1/stats")
def get_sorting_stats(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    shift: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy dữ liệu thống kê tổng hợp (Số lượng từng màu, tỷ lệ %, năng suất, cảnh báo) có hỗ trợ bộ lọc.
    """
    dt_start = parse_datetime(start_time)
    dt_end = parse_datetime(end_time)
    return calculate_stats(db, start_time=dt_start, end_time=dt_end, shift=shift)

@app.get("/api/v1/analytics/servo-health")
def get_servo_health(
    max_rated_cycles: int = 10000,
    db: Session = Depends(get_db)
):
    """
    Lấy chỉ số phân tích vòng đời và mức độ hao mòn cơ cấu Servo SG90.
    """
    return calculate_servo_health(db, max_rated_cycles=max_rated_cycles)

@app.get("/api/v1/analytics/oee")
def get_oee_analytics(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    shift: Optional[str] = None,
    ideal_run_rate: float = 15.0,
    db: Session = Depends(get_db)
):
    """
    Lấy bộ chỉ số OEE công nghiệp (Overall Equipment Effectiveness = A x P x Q)
    hỗ trợ bộ lọc thời gian và ca sản xuất.
    """
    dt_start = parse_datetime(start_time)
    dt_end = parse_datetime(end_time)
    return calculate_oee_metrics(
        db, start_time=dt_start, end_time=dt_end, shift=shift, ideal_run_rate=ideal_run_rate
    )

@app.get("/api/v1/analytics/target-vs-actual")
def get_target_vs_actual_analytics(
    target_shift: int = 500,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    shift: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy dữ liệu đối chiếu tiến độ kế hoạch Target vs Actual & dự báo thời gian cán đích.
    """
    dt_start = parse_datetime(start_time)
    dt_end = parse_datetime(end_time)
    return calculate_target_vs_actual(
        db, target_shift=target_shift, start_time=dt_start, end_time=dt_end, shift=shift
    )

@app.get("/api/v1/analytics/heatmap-matrix")
def get_heatmap_matrix_analytics(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Lấy ma trận nhiệt 24h x 7 ngày & 24h x 3 màu để biểu diễn Heatmap.
    """
    return calculate_hourly_heatmap_matrix(db, days=days)


# --- EXPORT & CONFIG ROUTES (MANAGER ONLY) ---
@app.get("/api/v1/export/csv")
def export_logs_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MANAGER"]))
):
    """
    Xuất file CSV toàn bộ lịch sử phân loại (Chỉ MANAGER).
    """
    logs = db.query(SortingLog).order_by(SortingLog.id.asc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nhan Mau", "Do Tin Cay", "Thoi Gian"])
    
    for log in logs:
        writer.writerow([
            log.id, 
            log.color_label, 
            log.confidence, 
            log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else ""
        ])
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sorting_logs_report.csv"}
    )

@app.post("/api/v1/config")
def update_config(
    config_data: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MANAGER"]))
):
    """
    Cập nhật cấu hình hệ thống (Chỉ MANAGER).
    """
    config = db.query(SystemConfig).filter(SystemConfig.key == config_data.key).first()
    if not config:
        config = SystemConfig(key=config_data.key, value=config_data.value)
        db.add(config)
    else:
        config.value = config_data.value
    db.commit()
    return {"message": "Cap nhat cau hinh thanh cong", "key": config_data.key, "value": config_data.value}

@app.get("/api/v1/config")
def get_configs(db: Session = Depends(get_db)):
    """
    Lấy danh sách cấu hình hệ thống.
    """
    configs = db.query(SystemConfig).all()
    return {c.key: c.value for c in configs}

# --- MQTT CONSUMER ---
def start_mqtt_consumer():
    mqtt_broker = os.getenv("MQTT_BROKER", "broker.hivemq.com")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic = os.getenv("MQTT_TOPIC", "factory/sorting/logs")

    try:
        import paho.mqtt.client as mqtt

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"[MQTT Cloud Consumer] Connected to MQTT Broker! Topic: {mqtt_topic}")
                client.subscribe(mqtt_topic)

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
                    print(f"[MQTT Cloud Consumer] Saved log from MQTT: {color.upper()}")
            except Exception as e:
                print(f"[MQTT Cloud Consumer] Error processing message: {e}")

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(mqtt_broker, mqtt_port, 60)
        client.loop_start()
    except Exception as e:
        print(f"[MQTT Cloud Consumer] Unable to start MQTT: {e}")

@app.on_event("startup")
def startup_event():
    init_default_data()
    threading.Thread(target=start_mqtt_consumer, daemon=True).start()
