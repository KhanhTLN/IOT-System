import cv2
import time
import numpy as np
import sys
import os

# Đảm bảo in tiếng Việt mượt mà trên Windows PowerShell / CMD
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Đảm bảo nhận diện các module cùng thư mục
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import (
    CAMERA_SOURCE, FRAME_WIDTH, FRAME_HEIGHT, FPS_LIMIT,
    COLOR_THRESHOLDS, DISPLAY_COLORS, MIN_CONTOUR_AREA,
    ROI_X_START, ROI_X_END, ROI_Y_START, ROI_Y_END,
    TRIGGER_COOLDOWN_SECONDS
)
from mqtt_publisher import dispatcher

class ColorSortingDetector:
    def __init__(self, source=CAMERA_SOURCE):
        self.source = source
        self.cap = None
        self.last_trigger_time = 0
        self.last_detected_color = None
        self.last_confidence = 0.0
        
        # Thống kê số lượng phát hiện trong phiên
        self.stats = {"RED": 0, "YELLOW": 0, "GREEN": 0, "TOTAL": 0}
        
        # Kernel khử nhiễu hình thái học (Morphological Filter)
        self.kernel = np.ones((5, 5), np.uint8)

    def init_camera(self):
        """Khởi động Camera hoặc Fallback sang Video giả lập nếu không có Webcam"""
        print(f"[Camera] Đang mở nguồn Camera: {self.source}...")
        self.cap = cv2.VideoCapture(self.source)
        
        # Thử mở camera thực tế
        if not self.cap.isOpened():
            print(f"[Camera Warning] Không thể mở Camera ID {self.source}. Chuyển sang chế độ giả lập trực quan (Synthetic Feed)...")
            self.cap = None
            return False
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        print("[Camera] ✅ Đã kết nối Camera thành công.")
        return True

    def _generate_synthetic_frame(self, frame_idx):
        """Tạo khung hình giả lập băng chuyền có vật thể chuyển động phục vụ test khi không có camera vật lý"""
        frame = np.full((FRAME_HEIGHT, FRAME_WIDTH, 3), 35, dtype=np.uint8)
        
        # Vẽ băng chuyền màu xám đậm
        cv2.rectangle(frame, (0, int(FRAME_HEIGHT * 0.2)), (FRAME_WIDTH, int(FRAME_HEIGHT * 0.8)), (50, 50, 50), -1)
        # Vạch kẻ băng chuyền
        for x in range(0, FRAME_WIDTH, 60):
            cv2.line(frame, (x, int(FRAME_HEIGHT * 0.2)), (x, int(FRAME_HEIGHT * 0.8)), (70, 70, 70), 2)
            
        # Mô phỏng vật thể chạy ngang qua màn hình
        cycle = (frame_idx % 240)
        obj_x = int((cycle / 240.0) * (FRAME_WIDTH + 100)) - 50
        obj_y = int(FRAME_HEIGHT * 0.5)
        
        # Đổi màu vật thể theo chu kỳ
        color_type = (frame_idx // 240) % 3
        if color_type == 0:
            color_bgr = (0, 0, 230) # RED
        elif color_type == 1:
            color_bgr = (0, 220, 255) # YELLOW
        else:
            color_bgr = (0, 220, 0) # GREEN
            
        cv2.circle(frame, (obj_x, obj_y), 45, color_bgr, -1)
        cv2.putText(frame, "CHẾ ĐỘ MÔ PHỎNG (SYNTHETIC CONVEYOR)", (20, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        return frame

    def process_frame(self, frame):
        """Xử lý hình ảnh nhận diện màu sắc qua không gian màu HSV và vùng ROI"""
        h, w, _ = frame.shape
        
        # 1. Tính toán tọa độ Vùng Nhận Diện ROI (Region of Interest)
        roi_xmin = int(w * ROI_X_START)
        roi_xmax = int(w * ROI_X_END)
        roi_ymin = int(h * ROI_Y_START)
        roi_ymax = int(h * ROI_Y_END)
        
        # Cắt lấy vùng ROI để phân tích
        roi_frame = frame[roi_ymin:roi_ymax, roi_xmin:roi_xmax]
        
        # Chuyển sang không gian màu HSV và làm mượt
        hsv_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
        hsv_roi = cv2.GaussianBlur(hsv_roi, (5, 5), 0)
        
        best_detection = None
        max_area = 0

        # 2. Duyệt qua từng màu đã định nghĩa trong cấu hình
        for color_name, ranges in COLOR_THRESHOLDS.items():
            mask = None
            for r in ranges:
                current_mask = cv2.inRange(hsv_roi, r["lower"], r["upper"])
                if mask is None:
                    mask = current_mask
                else:
                    mask = cv2.bitwise_or(mask, current_mask)
            
            # Khử nhiễu lọc hình thái học (Morphological Opening & Closing)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel, iterations=1)
            
            # Tìm đường biên dạng (Contours)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > MIN_CONTOUR_AREA and area > max_area:
                    max_area = area
                    x, y, cw, ch = cv2.boundingRect(cnt)
                    
                    # Tính độ tin cậy ước tính dựa trên tỷ lệ lấp đầy
                    confidence = min(0.99, 0.75 + (area / (cw * ch * 2.0)))
                    
                    best_detection = {
                        "color": color_name,
                        "area": area,
                        "confidence": confidence,
                        "bbox": (roi_xmin + x, roi_ymin + y, cw, ch),
                        "center": (roi_xmin + x + cw // 2, roi_ymin + y + ch // 2)
                    }

        # 3. Vẽ Vùng ROI lên khung hình chính
        is_cooldown = (time.time() - self.last_trigger_time) < TRIGGER_COOLDOWN_SECONDS
        roi_border_color = (0, 0, 255) if is_cooldown else DISPLAY_COLORS["ROI_LINE"]
        cv2.rectangle(frame, (roi_xmin, roi_ymin), (roi_xmax, roi_ymax), roi_border_color, 2)
        
        status_roi_text = "ROI TRIGGER ZONE [COOLDOWN...]" if is_cooldown else "ROI TRIGGER ZONE [READY]"
        cv2.putText(frame, status_roi_text, (roi_xmin + 5, roi_ymin - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, roi_border_color, 1, cv2.LINE_AA)

        # 4. Kích hoạt phân loại khi có vật thể thỏa điều kiện
        if best_detection:
            color = best_detection["color"]
            conf = best_detection["confidence"]
            bx, by, bw, bh = best_detection["bbox"]
            cx, cy = best_detection["center"]
            
            # Vẽ Bounding box và tâm vật thể
            box_color = DISPLAY_COLORS.get(color, (255, 255, 255))
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), box_color, 3)
            cv2.circle(frame, (cx, cy), 6, (0, 0, 0), -1)
            cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)
            
            # Hiển thị nhãn màu và độ tin cậy
            label = f"{color} ({conf*100:.1f}%)"
            cv2.putText(frame, label, (bx, max(25, by - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2, cv2.LINE_AA)
            
            # Kiểm tra xem vật thể có nằm trọn trong vùng kích hoạt và hết thời gian chờ (Cooldown) chưa
            if not is_cooldown:
                self.last_trigger_time = time.time()
                self.last_detected_color = color
                self.last_confidence = conf
                
                # Cập nhật số liệu thống kê
                self.stats[color] += 1
                self.stats["TOTAL"] += 1
                
                # GỬI LỆNH PHÂN LOẠI (MQTT + HTTP CLOUD)
                print(f"\n[EVENT TRIGGER] 🎯 Phát hiện {color} - Bắn tín hiệu sang ESP32 & Cloud...")
                dispatcher.dispatch_sorting_event(color, conf)

        # 5. Vẽ HUD thông tin SCADA
        self._draw_hud(frame)
        return frame

    def _draw_hud(self, frame):
        """Vẽ bảng điều khiển HUD giám sát số liệu trực tiếp trên màn hình"""
        h, w, _ = frame.shape
        
        # Bảng điều khiển góc trên bên trái
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (280, 130), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (10, 10), (280, 130), (80, 80, 80), 1)

        cv2.putText(frame, "SCADA EDGE CV DETECTOR", (20, 32), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        
        # Đếm số lượng
        cv2.putText(frame, f"RED: {self.stats['RED']}", (20, 58), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, f"YELLOW: {self.stats['YELLOW']}", (105, 58), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 2)
        cv2.putText(frame, f"GREEN: {self.stats['GREEN']}", (200, 58), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.putText(frame, f"TOTAL SORTED: {self.stats['TOTAL']}", (20, 85), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        last_event = f"LAST: {self.last_detected_color} ({self.last_confidence:.2f})" if self.last_detected_color else "LAST: WAITING..."
        cv2.putText(frame, last_event, (20, 112), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        # Hướng dẫn phím tắt góc dưới
        cv2.putText(frame, "[Q]: Thoat | [M]: Thu nho/Phong to | [R/Y/G]: Mau | [C]: Reset", (15, h - 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)

    def run(self):
        """Vòng lặp chính xử lý video theo thời gian thực"""
        has_real_camera = self.init_camera()
        window_name = "IoT Smart Sorting - OpenCV Edge Node"

        # Khởi tạo cửa sổ cho phép co giãn tự do (WINDOW_NORMAL) thay vì khóa cứng (WINDOW_AUTOSIZE)
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        # Kích thước khởi động mặc định nhỏ gọn để tiện chia màn hình khi demo
        initial_w, initial_h = 480, 360
        cv2.resizeWindow(window_name, initial_w, initial_h)
        is_mini_mode = True

        print("\n" + "="*60)
        print("🚀 SCADA COLOR SORTING - COMPUTER VISION RUNNING")
        print("   - Kéo viền cửa sổ bằng chuột để co giãn tự do")
        print("   - Phím [M]: Thu nhỏ (480x360) / Phóng to (640x480)")
        print("   - Phím [Q]: Thoát ứng dụng")
        print("   - Phím [R]: Bắn test màu ĐỎ (RED)")
        print("   - Phím [Y]: Bắn test màu VÀNG (YELLOW)")
        print("   - Phím [G]: Bắn test màu XANH (GREEN)")
        print("   - Phím [C]: Xóa bộ đếm số lượng")
        print("="*60 + "\n")

        frame_idx = 0
        prev_time = time.time()

        try:
            while True:
                if has_real_camera and self.cap:
                    ret, frame = self.cap.read()
                    if not ret:
                        print("[Camera] Mất tín hiệu luồng video. Đang thử lại...")
                        time.sleep(0.5)
                        continue
                else:
                    # Chế độ giả lập băng chuyền đồ họa
                    frame = self._generate_synthetic_frame(frame_idx)
                    time.sleep(1.0 / FPS_LIMIT)

                # Xử lý hình ảnh
                output_frame = self.process_frame(frame)
                
                # Tính toán FPS thực tế
                curr_time = time.time()
                fps = 1.0 / max(1e-5, (curr_time - prev_time))
                prev_time = curr_time
                cv2.putText(output_frame, f"FPS: {int(fps)}", (FRAME_WIDTH - 90, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

                # Hiển thị cửa sổ
                cv2.imshow(window_name, output_frame)
                
                # Bắt phím điều khiển
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' hoặc ESC
                    break
                elif key == ord('m'):
                    is_mini_mode = not is_mini_mode
                    if is_mini_mode:
                        cv2.resizeWindow(window_name, 480, 360)
                        print("[Window] 🔍 Chuyển sang kích thước thu nhỏ (480x360)")
                    else:
                        cv2.resizeWindow(window_name, 640, 480)
                        print("[Window] 🔍 Chuyển sang kích thước gốc (640x480)")
                elif key == ord('r'):
                    print("[Manual Trigger] 🔴 Bắn test màu RED")
                    dispatcher.dispatch_sorting_event("RED", 0.99)
                elif key == ord('y'):
                    print("[Manual Trigger] 🟡 Bắn test màu YELLOW")
                    dispatcher.dispatch_sorting_event("YELLOW", 0.99)
                elif key == ord('g'):
                    print("[Manual Trigger] 🟢 Bắn test màu GREEN")
                    dispatcher.dispatch_sorting_event("GREEN", 0.99)
                elif key == ord('c'):
                    self.stats = {"RED": 0, "YELLOW": 0, "GREEN": 0, "TOTAL": 0}
                    print("[Stats] Đã xóa bộ đếm về 0.")

                frame_idx += 1

        except KeyboardInterrupt:
            print("\n[Edge] Dừng bởi người dùng (Ctrl+C).")
        finally:
            if self.cap:
                self.cap.release()
            cv2.destroyAllWindows()
            dispatcher.close()
            print("[Edge] Đã giải phóng tài nguyên.")

if __name__ == "__main__":
    detector = ColorSortingDetector()
    detector.run()
