import io
import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import extract
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from models import SortingLog, SystemConfig
from analytics import (
    calculate_stats, calculate_oee_metrics,
    calculate_target_vs_actual, calculate_servo_health,
    apply_shift_filter, parse_datetime
)

# Palettes màu SCADA chuẩn Excel
COLOR_NAVY_DARK = "0F172A"
COLOR_NAVY_MED = "1E293B"
COLOR_NAVY_LIGHT = "334155"
COLOR_TEXT_WHITE = "FFFFFF"
COLOR_TEXT_DARK = "0F172A"
COLOR_TEXT_MUTED = "64748B"

# Màu nhãn sản phẩm (Pastel Fills + Text)
FILL_RED = PatternFill(start_color="FFE4E6", end_color="FFE4E6", fill_type="solid")
FONT_RED = Font(name="Segoe UI", size=10, bold=True, color="BE123C")

FILL_YELLOW = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
FONT_YELLOW = Font(name="Segoe UI", size=10, bold=True, color="B45309")

FILL_GREEN = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
FONT_GREEN = Font(name="Segoe UI", size=10, bold=True, color="047857")

# Borders
THIN_GRAY = Side(border_style="thin", color="CBD5E1")
DOUBLE_BOTTOM = Side(border_style="double", color="0F172A")
BORDER_CELL = Border(left=THIN_GRAY, right=THIN_GRAY, top=THIN_GRAY, bottom=THIN_GRAY)
BORDER_TOTAL = Border(top=THIN_GRAY, bottom=DOUBLE_BOTTOM)

def style_header_cell(cell, text: str, fill_color: str = COLOR_NAVY_MED, font_size: int = 11):
    """Định dạng ô tiêu đề bảng"""
    cell.value = text
    cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
    cell.font = Font(name="Segoe UI", size=font_size, bold=True, color=COLOR_TEXT_WHITE)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

def auto_fit_column_widths(ws, min_width: int = 12, max_width: int = 40):
    """Tự động co giãn độ rộng cột dựa theo độ dài nội dung"""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if cell.number_format and "%" in cell.number_format:
                val_str += "%"
            lines = val_str.split("\n")
            for line in lines:
                if len(line) > max_len:
                    max_len = len(line)
        ws.column_dimensions[col_letter].width = max(min_width, min(max_len + 3, max_width))

def generate_excel_report(
    db: Session,
    start_time_str: Optional[str] = None,
    end_time_str: Optional[str] = None,
    shift: Optional[str] = None,
    color_label: Optional[str] = None,
    target_shift: int = 500,
    ideal_run_rate: float = 15.0,
    user_name: str = "Administrator"
) -> io.BytesIO:
    """
    Sinh toàn bộ Workbook Excel (.xlsx) đa Sheet chuẩn SCADA / MES:
    - Sheet 1: Executive Summary (Tổng quan KPI, OEE, Target vs Actual, Servo Health)
    - Sheet 2: Shift & Hourly Analysis (Phân bổ theo 24h & 3 Ca)
    - Sheet 3: Raw Logs (Nhật ký phân loại chi tiết)
    """
    start_dt = parse_datetime(start_time_str)
    end_dt = parse_datetime(end_time_str)

    # 1. Truy vấn dữ liệu từ DB
    query = db.query(SortingLog)
    if start_dt:
        query = query.filter(SortingLog.created_at >= start_dt)
    if end_dt:
        query = query.filter(SortingLog.created_at <= end_dt)
    query = apply_shift_filter(query, shift)
    if color_label and color_label.upper() in ["RED", "YELLOW", "GREEN"]:
        query = query.filter(SortingLog.color_label == color_label.upper())

    logs: List[SortingLog] = query.order_by(SortingLog.id.asc()).all()

    # Tính toán các chỉ số thống kê & OEE
    stats = calculate_stats(db, start_time=start_dt, end_time=end_dt, shift=shift)
    oee = calculate_oee_metrics(db, start_time=start_dt, end_time=end_dt, shift=shift, ideal_run_rate=ideal_run_rate)
    target_act = calculate_target_vs_actual(db, target_shift=target_shift, start_time=start_dt, end_time=end_dt, shift=shift)
    servo = calculate_servo_health(db, max_rated_cycles=10000)

    # Tạo Workbook
    wb = openpyxl.Workbook()
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"
    ws_shifts = wb.create_sheet(title="Shift & Hourly Analysis")
    ws_raw = wb.create_sheet(title="Raw Sorting Logs")

    now_vn = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    now_str = now_vn.strftime("%H:%M:%S - %d/%m/%Y")

    # =========================================================================
    # SHEET 1: EXECUTIVE SUMMARY (TỔNG QUAN SẢN XUẤT)
    # =========================================================================
    ws_summary.views.sheetView[0].showGridLines = True

    # 1.1. Title Banner
    ws_summary.merge_cells("A1:F1")
    ws_summary["A1"] = "BÁO CÁO HIỆU SUẤT VẬN HÀNH & PHÂN LOẠI SCADA"
    ws_summary["A1"].font = Font(name="Segoe UI", size=15, bold=True, color=COLOR_TEXT_WHITE)
    ws_summary["A1"].fill = PatternFill(start_color=COLOR_NAVY_DARK, end_color=COLOR_NAVY_DARK, fill_type="solid")
    ws_summary["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_summary.row_dimensions[1].height = 36

    ws_summary.merge_cells("A2:F2")
    ws_summary["A2"] = "DÂY CHUYỀN PHÂN LOẠI SẢN PHẨM IOT TỰ ĐỘNG - NHÀ MÁY THÔNG MINH"
    ws_summary["A2"].font = Font(name="Segoe UI", size=10, italic=True, color="94A3B8")
    ws_summary["A2"].fill = PatternFill(start_color=COLOR_NAVY_MED, end_color=COLOR_NAVY_MED, fill_type="solid")
    ws_summary["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws_summary.row_dimensions[2].height = 22

    # 1.2. Metadata Bar
    scope_str = "Toàn bộ lịch sử"
    if start_dt and end_dt:
        scope_str = f"{start_dt.strftime('%d/%m/%Y')} - {end_dt.strftime('%d/%m/%Y')}"
    elif start_dt:
        scope_str = f"Từ {start_dt.strftime('%d/%m/%Y %H:%M')}"
    if shift:
        scope_str += f" | {shift}"

    ws_summary["A3"] = f"Thời Gian Xuất: {now_str}  |  Người Xuất Báo Cáo: {user_name}  |  Phạm Vi Dữ Liệu: {scope_str}"
    ws_summary.merge_cells("A3:F3")
    ws_summary["A3"].font = Font(name="Segoe UI", size=9, bold=True, color=COLOR_NAVY_LIGHT)
    ws_summary["A3"].alignment = Alignment(horizontal="left", vertical="center")
    ws_summary.row_dimensions[3].height = 20

    # 1.3. Section 1: Thống Kê Sản Lượng
    ws_summary["A5"] = "1. TỔNG QUAN SẢN LƯỢNG & CƠ CẤU PHÂN LOẠI MÀU SẮC"
    ws_summary["A5"].font = Font(name="Segoe UI", size=11, bold=True, color=COLOR_NAVY_DARK)

    headers_s1 = ["Hạng Mục Khay Chứa", "Góc Servo", "Số Lượng (SP)", "Tỷ Lệ (%)", "Định Mức Kế Hoạch (SP)", "Trạng Thái"]
    for col_idx, h in enumerate(headers_s1, start=1):
        cell = ws_summary.cell(row=6, column=col_idx)
        style_header_cell(cell, h, fill_color=COLOR_NAVY_MED)

    counts = stats.get("counts", {})
    pcts = stats.get("percentages", {})
    total_cnt = stats.get("total_count", 0)

    rows_s1 = [
        ("Khay Đỏ (RED)", "45°", counts.get("RED", 0), pcts.get("RED", 0.0), round(target_shift / 3), FILL_RED, FONT_RED),
        ("Khay Vàng (YELLOW)", "90°", counts.get("YELLOW", 0), pcts.get("YELLOW", 0.0), round(target_shift / 3), FILL_YELLOW, FONT_YELLOW),
        ("Khay Xanh (GREEN)", "135°", counts.get("GREEN", 0), pcts.get("GREEN", 0.0), round(target_shift / 3), FILL_GREEN, FONT_GREEN),
    ]

    for idx, (label, angle, count, pct, tgt, fill, font) in enumerate(rows_s1, start=7):
        c_label = ws_summary.cell(row=idx, column=1, value=label)
        c_label.fill = fill
        c_label.font = font
        c_label.border = BORDER_CELL

        c_angle = ws_summary.cell(row=idx, column=2, value=angle)
        c_angle.alignment = Alignment(horizontal="center")
        c_angle.border = BORDER_CELL

        c_count = ws_summary.cell(row=idx, column=3, value=count)
        c_count.number_format = "#,##0"
        c_count.alignment = Alignment(horizontal="right")
        c_count.font = Font(name="Segoe UI", bold=True)
        c_count.border = BORDER_CELL

        c_pct = ws_summary.cell(row=idx, column=4, value=pct / 100.0)
        c_pct.number_format = "0.0%"
        c_pct.alignment = Alignment(horizontal="right")
        c_pct.border = BORDER_CELL

        c_tgt = ws_summary.cell(row=idx, column=5, value=tgt)
        c_tgt.number_format = "#,##0"
        c_tgt.alignment = Alignment(horizontal="right")
        c_tgt.border = BORDER_CELL

        status_txt = "Đạt mục tiêu" if count >= tgt else "Đang sản xuất"
        c_status = ws_summary.cell(row=idx, column=6, value=status_txt)
        c_status.alignment = Alignment(horizontal="center")
        c_status.border = BORDER_CELL

    # Dòng Tổng Cộng
    tot_row = 10
    ws_summary.cell(row=tot_row, column=1, value="TỔNG SẢN PHẨM TOÀN CA").font = Font(name="Segoe UI", bold=True, color=COLOR_NAVY_DARK)
    ws_summary.cell(row=tot_row, column=1).border = BORDER_TOTAL
    ws_summary.cell(row=tot_row, column=2, value="-").alignment = Alignment(horizontal="center")
    ws_summary.cell(row=tot_row, column=2).border = BORDER_TOTAL

    c_tot = ws_summary.cell(row=tot_row, column=3, value=total_cnt)
    c_tot.font = Font(name="Segoe UI", bold=True, size=11, color="0284C7")
    c_tot.number_format = "#,##0"
    c_tot.alignment = Alignment(horizontal="right")
    c_tot.border = BORDER_TOTAL

    c_tot_pct = ws_summary.cell(row=tot_row, column=4, value=1.0 if total_cnt > 0 else 0.0)
    c_tot_pct.font = Font(name="Segoe UI", bold=True)
    c_tot_pct.number_format = "0.0%"
    c_tot_pct.alignment = Alignment(horizontal="right")
    c_tot_pct.border = BORDER_TOTAL

    c_tot_tgt = ws_summary.cell(row=tot_row, column=5, value=target_shift)
    c_tot_tgt.font = Font(name="Segoe UI", bold=True)
    c_tot_tgt.number_format = "#,##0"
    c_tot_tgt.alignment = Alignment(horizontal="right")
    c_tot_tgt.border = BORDER_TOTAL

    comp_pct = (total_cnt / max(1, target_shift))
    c_tot_st = ws_summary.cell(row=tot_row, column=6, value=f"Tiến độ: {comp_pct*100:.1f}%")
    c_tot_st.font = Font(name="Segoe UI", bold=True, color="047857" if comp_pct >= 1.0 else "B45309")
    c_tot_st.alignment = Alignment(horizontal="center")
    c_tot_st.border = BORDER_TOTAL

    # 1.4. Section 2: Chỉ Số OEE Công Nghiệp
    ws_summary["A12"] = "2. HIỆU SUẤT THIẾT BỊ TỔNG THỂ (OEE = A x P x Q)"
    ws_summary["A12"].font = Font(name="Segoe UI", size=11, bold=True, color=COLOR_NAVY_DARK)

    headers_s2 = ["Chỉ Số Thành Phần", "Ký Hiệu", "Giá Trị Đo Lường", "Ý Nghĩa & Định Mức", "Tiêu Chuẩn Đạt", "Đánh Giá"]
    for col_idx, h in enumerate(headers_s2, start=1):
        cell = ws_summary.cell(row=13, column=col_idx)
        style_header_cell(cell, h, fill_color=COLOR_NAVY_LIGHT)

    a_val = oee.get("availability", 0.0)
    p_val = oee.get("performance", 0.0)
    q_val = oee.get("quality", 100.0)
    oee_val = oee.get("oee", 0.0)
    oee_status = oee.get("benchmark_status", "TYPICAL")
    downtime_m = oee.get("downtime_minutes", 0.0)
    act_rate = oee.get("actual_run_rate", 0.0)
    good_cnt = oee.get("good_count", 0)

    rows_s2 = [
        ("Tính Sẵn Sàng", "Availability (A)", a_val / 100.0, f"Downtime: {downtime_m} phút", "≥ 90.0%", "Tốt" if a_val >= 90 else "Chấp nhận"),
        ("Hiệu Suất Vận Hành", "Performance (P)", p_val / 100.0, f"Vận tốc: {act_rate}/{ideal_run_rate} sp/p", "≥ 95.0%", "Tốt" if p_val >= 85 else "Cần cải tiến"),
        ("Chất Lượng Phân Loại", "Quality (Q)", q_val / 100.0, f"Đạt chuẩn: {good_cnt}/{total_cnt} sp", "≥ 99.0%", "Đạt chuẩn" if q_val >= 90 else "Cần chỉnh AI"),
    ]

    for idx, (name, sym, val, note, bench, eval_txt) in enumerate(rows_s2, start=14):
        ws_summary.cell(row=idx, column=1, value=name).border = BORDER_CELL
        ws_summary.cell(row=idx, column=2, value=sym).font = Font(name="Segoe UI", bold=True)
        ws_summary.cell(row=idx, column=2).border = BORDER_CELL

        c_v = ws_summary.cell(row=idx, column=3, value=val)
        c_v.number_format = "0.0%"
        c_v.alignment = Alignment(horizontal="right")
        c_v.font = Font(name="Segoe UI", bold=True)
        c_v.border = BORDER_CELL

        ws_summary.cell(row=idx, column=4, value=note).border = BORDER_CELL
        ws_summary.cell(row=idx, column=5, value=bench).alignment = Alignment(horizontal="center")
        ws_summary.cell(row=idx, column=5).border = BORDER_CELL
        ws_summary.cell(row=idx, column=6, value=eval_txt).alignment = Alignment(horizontal="center")
        ws_summary.cell(row=idx, column=6).border = BORDER_CELL

    # Dòng OEE Tổng thể
    oee_row = 17
    ws_summary.cell(row=oee_row, column=1, value="CHỈ SỐ OEE TỔNG THỂ").font = Font(name="Segoe UI", bold=True, size=11, color="0284C7")
    ws_summary.cell(row=oee_row, column=1).border = BORDER_TOTAL
    ws_summary.cell(row=oee_row, column=2, value="OEE = A x P x Q").font = Font(name="Segoe UI", bold=True)
    ws_summary.cell(row=oee_row, column=2).border = BORDER_TOTAL

    c_oee = ws_summary.cell(row=oee_row, column=3, value=oee_val / 100.0)
    c_oee.font = Font(name="Segoe UI", bold=True, size=12, color="0284C7")
    c_oee.number_format = "0.0%"
    c_oee.alignment = Alignment(horizontal="right")
    c_oee.border = BORDER_TOTAL

    ws_summary.cell(row=oee_row, column=4, value="World Class ≥ 85%").border = BORDER_TOTAL
    ws_summary.cell(row=oee_row, column=5, value="≥ 85.0%").alignment = Alignment(horizontal="center")
    ws_summary.cell(row=oee_row, column=5).border = BORDER_TOTAL

    status_vn = "ĐẲNG CẤP THẾ GIỚI" if oee_status == "WORLD_CLASS" else ("ĐẠT CHUẨN SẢN XUẤT" if oee_status == "TYPICAL" else "CẦN CẢI TIẾN")
    c_oee_st = ws_summary.cell(row=oee_row, column=6, value=status_vn)
    c_oee_st.font = Font(name="Segoe UI", bold=True, color="047857" if oee_status == "WORLD_CLASS" else ("B45309" if oee_status == "TYPICAL" else "BE123C"))
    c_oee_st.alignment = Alignment(horizontal="center")
    c_oee_st.border = BORDER_TOTAL

    # 1.5. Section 3: Sức Khỏe Cơ Cấu Servo SG90
    ws_summary["A19"] = "3. GIÁM SÁT VÒNG ĐỜI & SỨC KHỎE CƠ CẤU SERVO SG90"
    ws_summary["A19"].font = Font(name="Segoe UI", size=11, bold=True, color=COLOR_NAVY_DARK)

    headers_s3 = ["Cơ Cấu Khay Chứa", "Góc Quay (°)", "Số Chu Kỳ Đã Gạt", "Định Mức Vòng Đời", "Mức Hao Mòn (%)", "Tình Trạng Thiết Bị"]
    for col_idx, h in enumerate(headers_s3, start=1):
        cell = ws_summary.cell(row=20, column=col_idx)
        style_header_cell(cell, h, fill_color=COLOR_NAVY_MED)

    details_sv = servo.get("servo_details", {})
    rows_s3 = [
        ("Khay Đỏ (RED)", "45°", details_sv.get("RED", {}).get("cycles", 0), "10,000 chu kỳ", details_sv.get("RED", {}).get("wear_pct", 0.0), details_sv.get("RED", {}).get("status", "HEALTHY")),
        ("Khay Vàng (YELLOW)", "90°", details_sv.get("YELLOW", {}).get("cycles", 0), "10,000 chu kỳ", details_sv.get("YELLOW", {}).get("wear_pct", 0.0), details_sv.get("YELLOW", {}).get("status", "HEALTHY")),
        ("Khay Xanh (GREEN)", "135°", details_sv.get("GREEN", {}).get("cycles", 0), "10,000 chu kỳ", details_sv.get("GREEN", {}).get("wear_pct", 0.0), details_sv.get("GREEN", {}).get("status", "HEALTHY")),
    ]

    for idx, (label, angle, cyc, rated, wear, st_sv) in enumerate(rows_s3, start=21):
        ws_summary.cell(row=idx, column=1, value=label).border = BORDER_CELL
        ws_summary.cell(row=idx, column=2, value=angle).alignment = Alignment(horizontal="center")
        ws_summary.cell(row=idx, column=2).border = BORDER_CELL

        c_cyc = ws_summary.cell(row=idx, column=3, value=cyc)
        c_cyc.number_format = "#,##0"
        c_cyc.alignment = Alignment(horizontal="right")
        c_cyc.border = BORDER_CELL

        ws_summary.cell(row=idx, column=4, value=rated).alignment = Alignment(horizontal="center")
        ws_summary.cell(row=idx, column=4).border = BORDER_CELL

        c_w = ws_summary.cell(row=idx, column=5, value=wear / 100.0)
        c_w.number_format = "0.0%"
        c_w.alignment = Alignment(horizontal="right")
        c_w.font = Font(name="Segoe UI", bold=True)
        c_w.border = BORDER_CELL

        st_label = "Hoạt động tốt (Healthy)" if st_sv == "HEALTHY" else ("Cảnh báo bảo dưỡng (Warning)" if st_sv == "WARNING" else "Nguy cấp (Critical)")
        c_st = ws_summary.cell(row=idx, column=6, value=st_label)
        c_st.font = Font(name="Segoe UI", bold=True, color="047857" if st_sv == "HEALTHY" else ("B45309" if st_sv == "WARNING" else "BE123C"))
        c_st.alignment = Alignment(horizontal="center")
        c_st.border = BORDER_CELL

    auto_fit_column_widths(ws_summary)

    # =========================================================================
    # SHEET 2: SHIFT & HOURLY ANALYSIS (PHÂN BỔ GIỜ & CA)
    # =========================================================================
    ws_shifts.views.sheetView[0].showGridLines = True

    # Header Sheet 2
    ws_shifts.merge_cells("A1:E1")
    ws_shifts["A1"] = "PHÂN BỔ NĂNG SUẤT THEO 24 KHUNG GIỜ VÀ CÁC CA LÀM VIỆC"
    ws_shifts["A1"].font = Font(name="Segoe UI", size=13, bold=True, color=COLOR_TEXT_WHITE)
    ws_shifts["A1"].fill = PatternFill(start_color=COLOR_NAVY_DARK, end_color=COLOR_NAVY_DARK, fill_type="solid")
    ws_shifts["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_shifts.row_dimensions[1].height = 30

    # 2.1. Bảng 3 Ca sản xuất
    ws_shifts["A3"] = "1. TỔNG HỢP SẢN LƯỢNG THEO 3 CA SẢN XUẤT"
    ws_shifts["A3"].font = Font(name="Segoe UI", size=11, bold=True, color=COLOR_NAVY_DARK)

    headers_shift = ["Ca Sản Xuất", "Khung Giờ Hoạt Động", "Đỏ (RED)", "Vàng (YELLOW)", "Xanh (GREEN)", "Tổng Ca (SP)"]
    for col_idx, h in enumerate(headers_shift, start=1):
        cell = ws_shifts.cell(row=4, column=col_idx)
        style_header_cell(cell, h, fill_color=COLOR_NAVY_MED)

    # Gom nhóm theo Ca
    shift_counts = {
        "SHIFT_1": {"RED": 0, "YELLOW": 0, "GREEN": 0},
        "SHIFT_2": {"RED": 0, "YELLOW": 0, "GREEN": 0},
        "SHIFT_3": {"RED": 0, "YELLOW": 0, "GREEN": 0}
    }
    for log in logs:
        hr = log.created_at.hour
        lbl = log.color_label.upper()
        if 6 <= hr < 14:
            s_key = "SHIFT_1"
        elif 14 <= hr < 22:
            s_key = "SHIFT_2"
        else:
            s_key = "SHIFT_3"
        if lbl in shift_counts[s_key]:
            shift_counts[s_key][lbl] += 1

    shift_rows = [
        ("Ca 1 (Sáng)", "06:00 - 14:00", shift_counts["SHIFT_1"]["RED"], shift_counts["SHIFT_1"]["YELLOW"], shift_counts["SHIFT_1"]["GREEN"]),
        ("Ca 2 (Chiều)", "14:00 - 22:00", shift_counts["SHIFT_2"]["RED"], shift_counts["SHIFT_2"]["YELLOW"], shift_counts["SHIFT_2"]["GREEN"]),
        ("Ca 3 (Đêm)", "22:00 - 06:00", shift_counts["SHIFT_3"]["RED"], shift_counts["SHIFT_3"]["YELLOW"], shift_counts["SHIFT_3"]["GREEN"]),
    ]

    for idx, (s_name, s_time, r_c, y_c, g_c) in enumerate(shift_rows, start=5):
        ws_shifts.cell(row=idx, column=1, value=s_name).font = Font(name="Segoe UI", bold=True)
        ws_shifts.cell(row=idx, column=1).border = BORDER_CELL

        ws_shifts.cell(row=idx, column=2, value=s_time).alignment = Alignment(horizontal="center")
        ws_shifts.cell(row=idx, column=2).border = BORDER_CELL

        for c_idx, val in enumerate([r_c, y_c, g_c], start=3):
            c_cell = ws_shifts.cell(row=idx, column=c_idx, value=val)
            c_cell.number_format = "#,##0"
            c_cell.alignment = Alignment(horizontal="right")
            c_cell.border = BORDER_CELL

        tot_s = ws_shifts.cell(row=idx, column=6, value=r_c + y_c + g_c)
        tot_s.font = Font(name="Segoe UI", bold=True, color="0284C7")
        tot_s.number_format = "#,##0"
        tot_s.alignment = Alignment(horizontal="right")
        tot_s.border = BORDER_CELL

    # 2.2. Bảng 24 Khung giờ
    ws_shifts["A9"] = "2. PHÂN BỔ SẢN LƯỢNG CHI TIẾT THEO 24 KHUNG GIỜ (00:00 - 23:00)"
    ws_shifts["A9"].font = Font(name="Segoe UI", size=11, bold=True, color=COLOR_NAVY_DARK)

    headers_hr = ["Khung Giờ", "Đỏ (RED)", "Vàng (YELLOW)", "Xanh (GREEN)", "Tổng Giờ (SP)", "Tỷ Lệ Giờ / Tổng Ca"]
    for col_idx, h in enumerate(headers_hr, start=1):
        cell = ws_shifts.cell(row=10, column=col_idx)
        style_header_cell(cell, h, fill_color=COLOR_NAVY_LIGHT)

    hour_counts = {h: {"RED": 0, "YELLOW": 0, "GREEN": 0} for h in range(24)}
    for log in logs:
        hr = log.created_at.hour
        lbl = log.color_label.upper()
        if lbl in hour_counts[hr]:
            hour_counts[hr][lbl] += 1

    for h in range(24):
        row_h = 11 + h
        h_str = f"{h:02d}:00 - {h:02d}:59"
        r_v = hour_counts[h]["RED"]
        y_v = hour_counts[h]["YELLOW"]
        g_v = hour_counts[h]["GREEN"]
        tot_h = r_v + y_v + g_v

        ws_shifts.cell(row=row_h, column=1, value=h_str).alignment = Alignment(horizontal="center")
        ws_shifts.cell(row=row_h, column=1).border = BORDER_CELL

        for c_idx, val in enumerate([r_v, y_v, g_v], start=2):
            cell = ws_shifts.cell(row=row_h, column=c_idx, value=val)
            cell.number_format = "#,##0"
            cell.alignment = Alignment(horizontal="right")
            cell.border = BORDER_CELL

        c_tot = ws_shifts.cell(row=row_h, column=5, value=tot_h)
        c_tot.font = Font(name="Segoe UI", bold=True)
        c_tot.number_format = "#,##0"
        c_tot.alignment = Alignment(horizontal="right")
        c_tot.border = BORDER_CELL

        pct_h = (tot_h / total_cnt) if total_cnt > 0 else 0.0
        c_pct = ws_shifts.cell(row=row_h, column=6, value=pct_h)
        c_pct.number_format = "0.0%"
        c_pct.alignment = Alignment(horizontal="right")
        c_pct.border = BORDER_CELL

    auto_fit_column_widths(ws_shifts)

    # =========================================================================
    # SHEET 3: RAW SORTING LOGS (NHẬT KÝ CHI TIẾT)
    # =========================================================================
    ws_raw.views.sheetView[0].showGridLines = True

    # Title Sheet 3
    ws_raw.merge_cells("A1:E1")
    ws_raw["A1"] = f"NHẬT KÝ PHÂN LOẠI CHI TIẾT ({len(logs):,} BẢN GHI THỎA MÃN BỘ LỌC)"
    ws_raw["A1"].font = Font(name="Segoe UI", size=13, bold=True, color=COLOR_TEXT_WHITE)
    ws_raw["A1"].fill = PatternFill(start_color=COLOR_NAVY_DARK, end_color=COLOR_NAVY_DARK, fill_type="solid")
    ws_raw["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_raw.row_dimensions[1].height = 30

    headers_raw = ["Mã Bản Ghi (ID)", "Nhãn Màu Nhận Diện", "Góc Servo Thực Thi", "Độ Tin Cậy AI (Confidence)", "Thời Gian Gạt (GMT+7)"]
    for col_idx, h in enumerate(headers_raw, start=1):
        cell = ws_raw.cell(row=2, column=col_idx)
        style_header_cell(cell, h, fill_color=COLOR_NAVY_MED)

    angle_map = {"RED": "45° (Khay Đỏ)", "YELLOW": "90° (Khay Vàng)", "GREEN": "135° (Khay Xanh)"}

    for idx, log in enumerate(logs, start=3):
        lbl = log.color_label.upper()
        
        # Cột ID
        c_id = ws_raw.cell(row=idx, column=1, value=log.id)
        c_id.alignment = Alignment(horizontal="center")
        c_id.border = BORDER_CELL

        # Cột Màu (Kèm Fill màu)
        c_lbl = ws_raw.cell(row=idx, column=2, value=lbl)
        c_lbl.border = BORDER_CELL
        if lbl == "RED":
            c_lbl.fill = FILL_RED
            c_lbl.font = FONT_RED
        elif lbl == "YELLOW":
            c_lbl.fill = FILL_YELLOW
            c_lbl.font = FONT_YELLOW
        elif lbl == "GREEN":
            c_lbl.fill = FILL_GREEN
            c_lbl.font = FONT_GREEN

        # Cột Góc Servo
        c_ang = ws_raw.cell(row=idx, column=3, value=angle_map.get(lbl, "-"))
        c_ang.alignment = Alignment(horizontal="center")
        c_ang.border = BORDER_CELL

        # Cột Độ tin cậy AI
        c_conf = ws_raw.cell(row=idx, column=4, value=log.confidence)
        c_conf.number_format = "0.0%"
        c_conf.alignment = Alignment(horizontal="right")
        c_conf.border = BORDER_CELL

        # Cột Thời gian
        time_str = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else ""
        c_time = ws_raw.cell(row=idx, column=5, value=time_str)
        c_time.alignment = Alignment(horizontal="center")
        c_time.border = BORDER_CELL

    auto_fit_column_widths(ws_raw)

    # 4. Xuất in-memory buffer
    output_stream = io.BytesIO()
    wb.save(output_stream)
    output_stream.seek(0)
    return output_stream
