"""
Dataset Collector Tool for YOLOv8 Model Training
IoT Smart Sorting System - Local Edge Node

Hỗ trợ:
- Bắt hình từ Camera thật hoặc giả lập Synthetic Conveyor khi không có phần cứng
- Đổi nhãn linh hoạt bằng phím nóng (1: RED, 2: YELLOW, 3: GREEN)
- Chụp thủ công (Phím SPACE) hoặc Tự động định kỳ (Phím 'a')
- Lưu trữ vào local_edge/datasets/raw/{CLASS_NAME}/
"""

import cv2
import numpy as np
import time
import os
import sys
from datetime import datetime
from pathlib import Path

# Đảm bảo in tiếng Việt chuẩn trên Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Thêm đường dẫn thư mục hiện tại để nạp config
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.append(str(CURRENT_DIR))

from config import (
    CAMERA_SOURCE, FRAME_WIDTH, FRAME_HEIGHT, FPS_LIMIT,
    ROI_X_START, ROI_X_END, ROI_Y_START, ROI_Y_END
)

# Danh sách lớp hỗ trợ
CLASSES = {
    1: {"name": "RED", "color_bgr": (0, 0, 240)},
    2: {"name": "YELLOW", "color_bgr": (0, 220, 255)},
    3: {"name": "BLUE", "color_bgr": (240, 60, 0)}
}

# Thư mục lưu trữ dataset
DATASET_DIR = CURRENT_DIR / "datasets" / "raw"


class DatasetCollector:
    def __init__(self, source=CAMERA_SOURCE):
        self.source = source
        self.cap = None
        self.is_synthetic = False
        
        # Trạng thái thu thập
        self.current_class_id = 1
        self.auto_capture = False
        self.auto_interval_seconds = 0.8
        self.last_auto_capture_time = 0.0
        self.crop_roi_only = False
        
        # Hiệu ứng chụp ảnh (Flash visual feedback)
        self.flash_counter = 0
        
        # Thống kê số lượng ảnh đã có sẵn trong thư mục
        self.counts = self._init_and_scan_storage()
        
    def _init_and_scan_storage(self):
        """Khởi tạo thư mục và đếm số lượng ảnh hiện có cho mỗi lớp"""
        counts = {cls_info["name"]: 0 for cls_info in CLASSES.values()}
        counts["TOTAL"] = 0
        
        for cls_info in CLASSES.values():
            folder = DATASET_DIR / cls_info["name"]
            folder.mkdir(parents=True, exist_ok=True)
            # Đếm số file ảnh .jpg/.png
            existing_imgs = [f for f in folder.glob("*.*") if f.suffix.lower() in [".jpg", ".jpeg", ".png"]]
            counts[cls_info["name"]] = len(existing_imgs)
            counts["TOTAL"] += len(existing_imgs)
            
        return counts

    def init_camera(self):
        """Mở Camera thật hoặc tự động lùi về Synthetic Feed"""
        print(f"[Dataset Collector] 🎥 Đang kết nối nguồn Camera: {self.source}...")
        if isinstance(self.source, int) and sys.platform.startswith("win"):
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.source)
        else:
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            print(f"[Dataset Collector] ⚠️ Không mở được Camera ID {self.source}.")
            print("[Dataset Collector] 🔄 Tự động chuyển sang chế độ GIẢ LẬP BĂNG CHUYỀN (Synthetic Mode)...")
            self.cap = None
            self.is_synthetic = True
            return True
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        print(f"[Dataset Collector] ✅ Kết nối Camera thành công ({FRAME_WIDTH}x{FRAME_HEIGHT}).")
        return True

    def _generate_synthetic_frame(self, frame_idx):
        """Mô phỏng băng chuyền có sản phẩm màu chạy ngang để test khi không có camera thật"""
        frame = np.full((FRAME_HEIGHT, FRAME_WIDTH, 3), 35, dtype=np.uint8)
        
        # Băng chuyền công nghiệp
        conveyor_y1 = int(FRAME_HEIGHT * 0.25)
        conveyor_y2 = int(FRAME_HEIGHT * 0.75)
        cv2.rectangle(frame, (0, conveyor_y1), (FRAME_WIDTH, conveyor_y2), (50, 50, 50), -1)
        for x in range(0, FRAME_WIDTH, 60):
            cv2.line(frame, (x, conveyor_y1), (x, conveyor_y2), (70, 70, 70), 2)
            
        # Vị trí vật thể trượt ngang
        cycle = (frame_idx % 240)
        obj_x = int((cycle / 240.0) * (FRAME_WIDTH + 100)) - 50
        obj_y = int(FRAME_HEIGHT * 0.5)
        
        # Màu vật thể hiển thị theo lớp đang chọn
        cls_color = CLASSES[self.current_class_id]["color_bgr"]
        
        # Vẽ hộp sản phẩm mô phỏng (hình chữ nhật có bo góc nhẹ)
        w_box, h_box = 80, 80
        x1 = max(0, obj_x - w_box // 2)
        y1 = max(0, obj_y - h_box // 2)
        x2 = min(FRAME_WIDTH, obj_x + w_box // 2)
        y2 = min(FRAME_HEIGHT, obj_y + h_box // 2)
        
        if x2 > x1 and y2 > y1:
            cv2.rectangle(frame, (x1, y1), (x2, y2), cls_color, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
            
        return frame

    def save_sample(self, raw_frame):
        """Lưu ảnh vào thư mục tương ứng với nhãn hiện tại"""
        class_name = CLASSES[self.current_class_id]["name"]
        save_folder = DATASET_DIR / class_name
        
        # Cắt theo ROI nếu người dùng bật chế độ Crop
        if self.crop_roi_only:
            h, w = raw_frame.shape[:2]
            x1 = int(w * ROI_X_START)
            x2 = int(w * ROI_X_END)
            y1 = int(h * ROI_Y_START)
            y2 = int(h * ROI_Y_END)
            target_image = raw_frame[y1:y2, x1:x2]
        else:
            target_image = raw_frame.copy()
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        self.counts[class_name] += 1
        self.counts["TOTAL"] += 1
        file_name = f"{class_name}_{timestamp}_{self.counts[class_name]:04d}.jpg"
        file_path = save_folder / file_name
        
        # Lưu ảnh định dạng JPG chất lượng cao
        success = cv2.imwrite(str(file_path), target_image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        if success:
            self.flash_counter = 4  # Hiển thị viền trắng nhấp nháy 4 frames
            print(f"[Dataset Collector] 📸 Đã lưu ảnh: {file_name} (Lớp: {class_name} | Tổng: {self.counts['TOTAL']})")
        else:
            print(f"[Dataset Collector] ❌ Lỗi khi lưu ảnh vào: {file_path}")

    def render_hud(self, display_frame):
        """Vẽ thông tin điều khiển, thống kê và phím nóng lên màn hình trực quan"""
        h, w = display_frame.shape[:2]
        
        # 1. Vẽ Vùng ROI
        roi_x1 = int(w * ROI_X_START)
        roi_x2 = int(w * ROI_X_END)
        roi_y1 = int(h * ROI_Y_START)
        roi_y2 = int(h * ROI_Y_END)
        cv2.rectangle(display_frame, (roi_x1, roi_y1), (roi_x2, roi_y2), (255, 165, 0), 2)
        cv2.putText(display_frame, "ROI REGION", (roi_x1 + 6, roi_y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 165, 0), 1, cv2.LINE_AA)
                    
        # 2. Thanh Banner Header hiển thị Class đang chọn
        cls_info = CLASSES[self.current_class_id]
        cls_name = cls_info["name"]
        cls_color = cls_info["color_bgr"]
        
        # Header background bar
        cv2.rectangle(display_frame, (0, 0), (w, 42), (20, 20, 20), -1)
        cv2.line(display_frame, (0, 42), (w, 42), cls_color, 2)
        
        cv2.putText(display_frame, f"CLASS: {cls_name} [Key 1:RED, 2:YEL, 3:BLU]", (15, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, cls_color, 2, cv2.LINE_AA)
                    
        # Mode indicators (Manual vs Auto)
        mode_text = "[AUTO REC]" if self.auto_capture else "[MANUAL: SPACE]"
        mode_color = (0, 255, 0) if self.auto_capture else (200, 200, 200)
        cv2.putText(display_frame, mode_text, (w - 230, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2, cv2.LINE_AA)

        # 3. Thanh Footer hiển thị Thống kê & Phím tắt
        cv2.rectangle(display_frame, (0, h - 35), (w, h), (20, 20, 20), -1)
        
        stats_text = f"RED: {self.counts['RED']} | YELLOW: {self.counts['YELLOW']} | BLUE: {self.counts['BLUE']} | TOTAL: {self.counts['TOTAL']}"
        cv2.putText(display_frame, stats_text, (15, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
                    
        controls_text = "SPACE: Chup | a: Auto | c: Crop ROI | q: Thoat"
        cv2.putText(display_frame, controls_text, (w - 380, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 170, 170), 1, cv2.LINE_AA)

        # 4. Hiệu ứng Flash khi bấm chụp ảnh
        if self.flash_counter > 0:
            cv2.rectangle(display_frame, (0, 0), (w, h), (255, 255, 255), 8)
            self.flash_counter -= 1

    def run(self):
        """Vòng lặp chính thu thập dữ liệu"""
        if not self.init_camera():
            return
            
        print("\n" + "=" * 60)
        print("🎯 BỘ CÔNG CỤ THU THẬP DỮ LIỆU YOLOv8 (DATA COLLECTOR)")
        print("=" * 60)
        print("  - Phím 1, 2, 3 : Đổi nhãn tương ứng (RED, YELLOW, BLUE)")
        print("  - Phím SPACE   : Chụp và lưu ảnh")
        print("  - Phím 'a'     : Bật/Tắt chế độ tự động chụp liên tục")
        print("  - Phím 'c'     : Bật/Tắt cắt chỉ lưu vùng ROI (Crop)")
        print("  - Phím 'q'/ESC : Lưu và Thoát")
        print(f"  - Thư mục lưu  : {DATASET_DIR.resolve()}")
        print("=" * 60 + "\n")
        
        frame_idx = 0
        window_name = "YOLOv8 Dataset Collector - IoT Sorting System"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        
        try:
            while True:
                # 1. Đọc khung hình
                if self.is_synthetic:
                    raw_frame = self._generate_synthetic_frame(frame_idx)
                    time.sleep(1.0 / FPS_LIMIT)
                else:
                    ret, raw_frame = self.cap.read()
                    if not ret:
                        print("[Dataset Collector] ⚠️ Không nhận được tín hiệu camera. Đang thử lại...")
                        time.sleep(0.1)
                        continue
                        
                frame_idx += 1
                
                # 2. Xử lý chụp tự động
                current_time = time.time()
                if self.auto_capture:
                    if (current_time - self.last_auto_capture_time) >= self.auto_interval_seconds:
                        self.save_sample(raw_frame)
                        self.last_auto_capture_time = current_time
                        
                # 3. Tạo khung hình hiển thị HUD
                display_frame = raw_frame.copy()
                self.render_hud(display_frame)
                
                # 4. Hiển thị lên màn hình
                cv2.imshow(window_name, display_frame)
                
                # 5. Bắt phím điều khiển
                key = cv2.waitKey(1) & 0xFF
                if key in [ord('q'), 27]: # 'q' hoặc ESC
                    print("\n[Dataset Collector] Đang dừng chương trình...")
                    break
                elif key in [ord('1'), ord('r'), ord('R')]:
                    self.current_class_id = 1
                    print("[Dataset Collector] 🏷️ Đã chuyển nhãn: RED")
                elif key in [ord('2'), ord('y'), ord('Y')]:
                    self.current_class_id = 2
                    print("[Dataset Collector] 🏷️ Đã chuyển nhãn: YELLOW")
                elif key in [ord('3'), ord('b'), ord('B')]:
                    self.current_class_id = 3
                    print("[Dataset Collector] 🏷️ Đã chuyển nhãn: BLUE")
                elif key == 32: # SPACE
                    self.save_sample(raw_frame)
                elif key in [ord('a'), ord('A')]:
                    self.auto_capture = not self.auto_capture
                    status = "BẬT" if self.auto_capture else "TẮT"
                    print(f"[Dataset Collector] ⏱️ Chế độ tự động chụp (Auto): {status}")
                elif key in [ord('c'), ord('C')]:
                    self.crop_roi_only = not self.crop_roi_only
                    status = "CẮT THEO ROI" if self.crop_roi_only else "LƯU TOÀN KHUNG HÌNH"
                    print(f"[Dataset Collector] 🖼️ Định dạng ảnh lưu: {status}")
                    
        finally:
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            print("\n" + "=" * 60)
            print("📊 TỔNG KẾT DỮ LIỆU ĐÃ THU THẬP:")
            print(f"  - RED    : {self.counts['RED']} ảnh")
            print(f"  - YELLOW : {self.counts['YELLOW']} ảnh")
            print(f"  - BLUE   : {self.counts['BLUE']} ảnh")
            print(f"  - TỔNG SỐ: {self.counts['TOTAL']} ảnh")
            print("=" * 60)


if __name__ == "__main__":
    collector = DatasetCollector()
    collector.run()

