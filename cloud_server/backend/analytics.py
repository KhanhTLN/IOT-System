import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract
from models import SortingLog, SystemConfig

def parse_datetime(dt_str: Optional[str]) -> Optional[datetime.datetime]:
    """Chuyển đổi chuỗi ngày giờ sang đối tượng datetime"""
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(dt_str.strip(), fmt)
        except ValueError:
            continue
    return None

def apply_shift_filter(query, shift: Optional[str]):
    """
    Lọc query theo ca làm việc (dựa trên giờ trong ngày của trường created_at):
    - SHIFT_1 (Ca 1): 06:00 - 13:59:59 (6 <= hour < 14)
    - SHIFT_2 (Ca 2): 14:00 - 21:59:59 (14 <= hour < 22)
    - SHIFT_3 (Ca 3): 22:00 - 05:59:59 (hour >= 22 hoặc hour < 6)
    """
    if not shift or shift.upper() in ["ALL", "TAT_CA", ""]:
        return query
    
    shift_upper = shift.upper()
    hour_col = extract('hour', SortingLog.created_at)
    
    if shift_upper in ["SHIFT_1", "CA_1"]:
        return query.filter(hour_col >= 6, hour_col < 14)
    elif shift_upper in ["SHIFT_2", "CA_2"]:
        return query.filter(hour_col >= 14, hour_col < 22)
    elif shift_upper in ["SHIFT_3", "CA_3"]:
        return query.filter((hour_col >= 22) | (hour_col < 6))
    return query

def calculate_stats(
    db: Session, 
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    shift: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tính toán thống kê với bộ lọc thời gian và ca làm việc:
    - Tổng số lượng các sản phẩm
    - Số lượng phân loại theo 3 màu (RED, YELLOW, GREEN)
    - Tỷ lệ phần trăm % từng màu
    - Năng suất (sản phẩm / phút)
    - Cảnh báo bất thường
    """
    query = db.query(SortingLog)
    
    if start_time:
        query = query.filter(SortingLog.created_at >= start_time)
    if end_time:
        query = query.filter(SortingLog.created_at <= end_time)
    
    query = apply_shift_filter(query, shift)
    
    logs: List[SortingLog] = query.order_by(SortingLog.id.asc()).all()
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

    # Năng suất sản phẩm / phút trong 10 phút gần nhất (GMT+7)
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
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

def calculate_servo_health(db: Session, max_rated_cycles: int = 10000) -> Dict[str, Any]:
    """
    Tính toán chỉ số sức khỏe và mức độ hao mòn của cơ cấu chấp hành Servo SG90
    dựa trên tổng số chu kỳ gạt của từng góc (45° Đỏ, 90° Vàng, 135° Xanh).
    """
    all_logs = db.query(SortingLog).all()
    total_cycles = len(all_logs)
    
    red_cycles = sum(1 for l in all_logs if l.color_label.upper() == "RED")
    yellow_cycles = sum(1 for l in all_logs if l.color_label.upper() == "YELLOW")
    green_cycles = sum(1 for l in all_logs if l.color_label.upper() == "GREEN")

    def get_status(wear_pct: float) -> str:
        if wear_pct >= 90.0:
            return "CRITICAL"
        elif wear_pct >= 70.0:
            return "WARNING"
        return "HEALTHY"

    overall_wear = min(100.0, round((total_cycles / max_rated_cycles) * 100, 2))
    
    red_wear = min(100.0, round((red_cycles / (max_rated_cycles / 3)) * 100, 2))
    yellow_wear = min(100.0, round((yellow_cycles / (max_rated_cycles / 3)) * 100, 2))
    green_wear = min(100.0, round((green_cycles / (max_rated_cycles / 3)) * 100, 2))

    # Đánh giá cân bằng tải trọng (Load Balancing)
    imbalance_warning = None
    if total_cycles > 20:
        max_c = max(red_cycles, yellow_cycles, green_cycles)
        if (max_c / total_cycles) > 0.65:
            heaviest_color = "ĐỎ (45°)" if max_c == red_cycles else ("VÀNG (90°)" if max_c == yellow_cycles else "XANH (135°)")
            imbalance_warning = f"Tải trọng cơ khí đang lệch nhiều về khay {heaviest_color} ({max_c/total_cycles*100:.1f}% tổng số lần gạt)."

    return {
        "max_rated_cycles": max_rated_cycles,
        "total_cycles": total_cycles,
        "overall_wear_pct": overall_wear,
        "overall_status": get_status(overall_wear),
        "servo_details": {
            "RED": {
                "angle": 45,
                "cycles": red_cycles,
                "wear_pct": red_wear,
                "status": get_status(red_wear)
            },
            "YELLOW": {
                "angle": 90,
                "cycles": yellow_cycles,
                "wear_pct": yellow_wear,
                "status": get_status(yellow_wear)
            },
            "GREEN": {
                "angle": 135,
                "cycles": green_cycles,
                "wear_pct": green_wear,
                "status": get_status(green_wear)
            }
        },
        "imbalance_warning": imbalance_warning
    }
