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

def calculate_oee_metrics(
    db: Session,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    shift: Optional[str] = None,
    ideal_run_rate: float = 15.0
) -> Dict[str, Any]:
    """
    Tính toán chỉ số OEE công nghiệp (Overall Equipment Effectiveness) = A x P x Q:
    - Availability (A): Tính sẵn sàng (tỷ lệ thời gian vận hành thực tế / thời gian tổng thể trừ downtime)
    - Performance (P): Hiệu suất vận hành (tốc độ thực tế / tốc độ thiết kế định mức ideal_run_rate)
    - Quality (Q): Tỷ lệ sản phẩm đạt chuẩn chất lượng nhận diện (Confidence >= 0.80)
    """
    query = db.query(SortingLog)
    if start_time:
        query = query.filter(SortingLog.created_at >= start_time)
    if end_time:
        query = query.filter(SortingLog.created_at <= end_time)
    query = apply_shift_filter(query, shift)

    logs: List[SortingLog] = query.order_by(SortingLog.created_at.asc()).all()
    total_logs = len(logs)

    if total_logs == 0:
        return {
            "oee": 0.0,
            "availability": 0.0,
            "performance": 0.0,
            "quality": 100.0,
            "benchmark_status": "NO_DATA",
            "ideal_run_rate": ideal_run_rate,
            "actual_run_rate": 0.0,
            "total_logs": 0,
            "good_count": 0,
            "downtime_minutes": 0.0
        }

    # 1. Tính Availability (A)
    # Phát hiện các khoảng trống gián đoạn (> 120 giây giữa 2 sản phẩm liên tiếp)
    downtime_seconds = 0.0
    for i in range(1, len(logs)):
        delta_sec = (logs[i].created_at - logs[i-1].created_at).total_seconds()
        if delta_sec > 120.0:  # Quá 2 phút không có SP coi là gián đoạn/downtime
            downtime_seconds += (delta_sec - 120.0)

    t_start = logs[0].created_at
    t_end = logs[-1].created_at
    total_span_minutes = max(1.0, (t_end - t_start).total_seconds() / 60.0)
    downtime_minutes = min(total_span_minutes * 0.8, downtime_seconds / 60.0)
    operating_minutes = max(0.5, total_span_minutes - downtime_minutes)

    availability = max(10.0, min(100.0, (operating_minutes / total_span_minutes) * 100.0))

    # 2. Tính Performance (P)
    actual_run_rate = round(total_logs / operating_minutes, 2)
    performance = min(100.0, max(5.0, (actual_run_rate / ideal_run_rate) * 100.0))

    # 3. Tính Quality (Q)
    good_count = sum(1 for log in logs if (log.confidence or 1.0) >= 0.80)
    quality = round((good_count / total_logs) * 100.0, 2)

    # 4. Tổng hợp OEE
    oee = round((availability * performance * quality) / 10000.0, 2)

    # Đánh giá theo chuẩn quốc tế
    if oee >= 85.0:
        benchmark = "WORLD_CLASS"  # Đẳng cấp thế giới
    elif oee >= 65.0:
        benchmark = "TYPICAL"      # Đạt chuẩn sản xuất
    else:
        benchmark = "UNACCEPTABLE" # Cần cải tiến

    return {
        "oee": oee,
        "availability": round(availability, 2),
        "performance": round(performance, 2),
        "quality": round(quality, 2),
        "benchmark_status": benchmark,
        "ideal_run_rate": ideal_run_rate,
        "actual_run_rate": actual_run_rate,
        "total_logs": total_logs,
        "good_count": good_count,
        "downtime_minutes": round(downtime_minutes, 1)
    }

def calculate_target_vs_actual(
    db: Session,
    target_shift: int = 500,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    shift: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tính toán tiến độ hoàn thành Kế hoạch Sản Xuất (Target vs Actual)
    và dự báo thời gian cán đích (ETA).
    """
    query = db.query(SortingLog)
    if start_time:
        query = query.filter(SortingLog.created_at >= start_time)
    if end_time:
        query = query.filter(SortingLog.created_at <= end_time)
    query = apply_shift_filter(query, shift)

    logs: List[SortingLog] = query.all()
    actual_count = len(logs)
    completion_pct = min(100.0, round((actual_count / max(1, target_shift)) * 100.0, 2))
    variance_units = actual_count - target_shift

    # Đếm theo từng màu
    red_c = sum(1 for l in logs if l.color_label.upper() == "RED")
    yellow_c = sum(1 for l in logs if l.color_label.upper() == "YELLOW")
    green_c = sum(1 for l in logs if l.color_label.upper() == "GREEN")

    target_per_color = round(target_shift / 3.0)

    # Tính tốc độ 15 phút gần nhất để dự báo thời gian cán đích ETA
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    fifteen_mins_ago = now - datetime.timedelta(minutes=15)
    recent_count = db.query(SortingLog).filter(SortingLog.created_at >= fifteen_mins_ago).count()
    speed_per_min = recent_count / 15.0

    eta_minutes = None
    eta_timestamp_str = None

    if actual_count < target_shift:
        remaining_units = target_shift - actual_count
        if speed_per_min > 0.1:
            eta_minutes = round(remaining_units / speed_per_min, 1)
            eta_dt = now + datetime.timedelta(minutes=eta_minutes)
            eta_timestamp_str = eta_dt.strftime("%H:%M (%d/%m/%Y)")
        else:
            eta_timestamp_str = "Chưa xác định (Dây chuyền đang tạm dừng)"
    else:
        eta_timestamp_str = "Đã hoàn thành mục tiêu ca"

    return {
        "target_shift": target_shift,
        "actual_count": actual_count,
        "completion_pct": completion_pct,
        "variance_units": variance_units,
        "is_achieved": actual_count >= target_shift,
        "speed_per_minute": round(speed_per_min, 2),
        "eta_minutes": eta_minutes,
        "eta_timestamp": eta_timestamp_str,
        "color_targets": {
            "RED": {"actual": red_c, "target": target_per_color, "pct": round(red_c / max(1, target_per_color) * 100, 1)},
            "YELLOW": {"actual": yellow_c, "target": target_per_color, "pct": round(yellow_c / max(1, target_per_color) * 100, 1)},
            "GREEN": {"actual": green_c, "target": target_per_color, "pct": round(green_c / max(1, target_per_color) * 100, 1)}
        }
    }

def calculate_hourly_heatmap_matrix(db: Session, days: int = 7) -> Dict[str, Any]:
    """
    Tạo ma trận nhiệt 2D (24 Hours x 7 Days of Week & 24 Hours x 3 Colors)
    cho biểu đồ Heatmap trực quan hóa điểm nghẽn năng suất.
    """
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    cutoff = now - datetime.timedelta(days=days)
    
    logs = db.query(SortingLog).filter(SortingLog.created_at >= cutoff).all()
    
    # 1. Ma trận 24 Giờ x 7 Ngày trong tuần
    # Thứ 2 (index 0) -> Chủ Nhật (index 6)
    days_labels = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    hours_labels = [f"{h:02d}:00" for h in range(24)]
    
    # Khởi tạo ma trận 7x24 bằng 0
    matrix_days = [[0 for _ in range(24)] for _ in range(7)]
    
    # 2. Ma trận 24 Giờ x 3 Màu
    colors_labels = ["Đỏ (RED)", "Vàng (YELLOW)", "Xanh (GREEN)"]
    color_map_idx = {"RED": 0, "YELLOW": 1, "GREEN": 2}
    matrix_colors = [[0 for _ in range(24)] for _ in range(3)]

    for log in logs:
        if log.created_at:
            weekday_idx = log.created_at.weekday() # 0 = Monday, 6 = Sunday
            hour_idx = log.created_at.hour
            if 0 <= weekday_idx < 7 and 0 <= hour_idx < 24:
                matrix_days[weekday_idx][hour_idx] += 1
            
            c_label = log.color_label.upper()
            if c_label in color_map_idx and 0 <= hour_idx < 24:
                matrix_colors[color_map_idx[c_label]][hour_idx] += 1

    return {
        "days_heatmap": {
            "y_labels": days_labels,
            "x_labels": hours_labels,
            "z_matrix": matrix_days
        },
        "colors_heatmap": {
            "y_labels": colors_labels,
            "x_labels": hours_labels,
            "z_matrix": matrix_colors
        },
        "analyzed_days": days,
        "total_records": len(logs)
    }

