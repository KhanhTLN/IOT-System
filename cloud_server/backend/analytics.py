import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import SortingLog

def calculate_stats(db: Session) -> Dict[str, Any]:
    """
    Tính toán thống kê:
    - Tổng số lượng các sản phẩm
    - Số lượng phân loại theo 3 màu (RED, YELLOW, GREEN)
    - Tỷ lệ phần trăm % từng màu
    - Năng suất (sản phẩm / phút) dựa trên dữ liệu trong 10 phút gần nhất
    - Cảnh báo bất thường (Nếu 1 màu xuất hiện liên tục > 10 lần gần nhất)
    """
    logs: List[SortingLog] = db.query(SortingLog).order_by(SortingLog.id.asc()).all()
    total_count = len(logs)
    
    color_counts = {"RED": 0, "YELLOW": 0, "GREEN": 0, "OTHER": 0}
    for log in logs:
        label = log.color_label.upper()
        if label in color_counts:
            color_counts[label] += 1
        else:
            color_counts["OTHER"] += 1
            
    # Tỷ lệ %
    percentage = {}
    for color in ["RED", "YELLOW", "GREEN"]:
        percentage[color] = round((color_counts[color] / total_count * 100), 2) if total_count > 0 else 0.0

    # Năng suất sản phẩm / phút trong 10 phút gần nhất
    now = datetime.datetime.utcnow()
    ten_mins_ago = now - datetime.timedelta(minutes=10)
    recent_logs_count = db.query(SortingLog).filter(SortingLog.created_at >= ten_mins_ago).count()
    productivity_per_minute = round(recent_logs_count / 10.0, 2)

    # Cảnh báo bất thường: Kiểm tra 10 log gần nhất có cùng 1 màu hay không
    recent_10_logs = db.query(SortingLog).order_by(SortingLog.id.desc()).limit(10).all()
    anomaly_alert = None
    if len(recent_10_logs) >= 10:
        first_color = recent_10_logs[0].color_label.upper()
        if all(log.color_label.upper() == first_color for log in recent_10_logs):
            anomaly_alert = f"CẢNH BÁO BẤT THƯỜNG: Phát hiện màu '{first_color}' xuất hiện liên tục {len(recent_10_logs)} lần!"

    return {
        "total_count": total_count,
        "counts": {
            "RED": color_counts["RED"],
            "YELLOW": color_counts["YELLOW"],
            "GREEN": color_counts["GREEN"]
        },
        "percentages": percentage,
        "productivity_per_minute": productivity_per_minute,
        "anomaly_alert": anomaly_alert
    }
