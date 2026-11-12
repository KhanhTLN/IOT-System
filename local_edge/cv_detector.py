"""
Dual-Engine Edge Computer Vision Detector & Object Tracker
IoT Smart Sorting System - Local Edge Node (Giai đoạn 3)

Hỗ trợ 2 chế độ nhận diện linh hoạt:
1. YOLO (Deep Learning ONNX): Chạy qua ONNX Runtime hoặc OpenCV DNN, kết hợp Centroid Tracker.
2. HSV (Color Masking): Thuật toán lọc màu truyền thống làm phương án dự phòng tự động (Fallback).
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# Đảm bảo in tiếng Việt mượt mà trên Windows PowerShell / CMD
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.append(str(CURRENT_DIR))

from config import (
    CAMERA_SOURCE, COLOR_THRESHOLDS, DETECTOR_BACKEND, DISPLAY_COLORS,
    FPS_LIMIT, FRAME_HEIGHT, FRAME_WIDTH, MIN_CONTOUR_AREA,
    ROI_X_END, ROI_X_START, ROI_Y_END, ROI_Y_START,
    TRACKER_MAX_DISAPPEARED, TRACKER_MAX_DISTANCE, TRACKER_MIN_HITS,
    TRIGGER_COOLDOWN_SECONDS, YOLO_CLASSES_FALLBACK,
    YOLO_CONF_THRESHOLD, YOLO_IOU_THRESHOLD, YOLO_MODEL_PATH
)
from export_onnx import extract_onnx_metadata
from mqtt_publisher import dispatcher
from tracker import CentroidTracker, TrackedObject


class HsvColorDetector:
    """Engine 1 (Fallback): Nhận diện màu sắc truyền thống bằng không gian màu HSV."""

    def __init__(self):
        self.kernel = np.ones((5, 5), np.uint8)

    def detect(self, frame: np.ndarray, roi_bounds: Tuple[int, int, int, int]) -> Tuple[List[Dict], float]:
        """Quét vùng ROI theo các dải màu HSV và trả về danh sách vật thể."""
        t0 = time.perf_counter()
        roi_xmin, roi_ymin, roi_xmax, roi_ymax = roi_bounds
        roi_frame = frame[roi_ymin:roi_ymax, roi_xmin:roi_xmax]

        hsv_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
        hsv_roi = cv2.GaussianBlur(hsv_roi, (5, 5), 0)

        detections: List[Dict] = []

        for color_name, ranges in COLOR_THRESHOLDS.items():
            mask = None
            for r in ranges:
                current_mask = cv2.inRange(hsv_roi, r["lower"], r["upper"])
                mask = current_mask if mask is None else cv2.bitwise_or(mask, current_mask)

            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel, iterations=1)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area <= MIN_CONTOUR_AREA:
                    continue

                x, y, cw, ch = cv2.boundingRect(cnt)
                confidence = min(0.99, 0.75 + (area / max(1.0, cw * ch * 2.0)))
                full_x = roi_xmin + x
                full_y = roi_ymin + y
                detections.append({
                    "class_name": color_name,
                    "confidence": float(confidence),
                    "bbox": (full_x, full_y, cw, ch),
                    "center": (full_x + cw // 2, full_y + ch // 2),
                })

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return detections, elapsed_ms


class YoloOnnxDetector:
    """Engine 2 (Primary): Nhận diện đối tượng bằng mô hình YOLOv8 ONNX (ORT / OpenCV DNN)."""

    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.65,
        iou_threshold: float = 0.45,
        fallback_names: Optional[List[str]] = None,
    ):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file model ONNX: {self.model_path}")

        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

        # Tự động đọc tên lớp & kích thước đầu vào từ metadata của file ONNX
        meta = extract_onnx_metadata(self.model_path)
        raw_names = meta.get("names")
        if isinstance(raw_names, dict) and raw_names:
            self.class_names = {int(k): str(v).upper() for k, v in raw_names.items()}
        elif isinstance(raw_names, list) and raw_names:
            self.class_names = {idx: str(v).upper() for idx, v in enumerate(raw_names)}
        else:
            names_list = fallback_names or ["RED", "YELLOW", "BLUE"]
            self.class_names = {idx: name.upper() for idx, name in enumerate(names_list)}

        imgsz_meta = meta.get("imgsz")
        if isinstance(imgsz_meta, list) and len(imgsz_meta) >= 2:
            self.input_size = (int(imgsz_meta[0]), int(imgsz_meta[1]))
        else:
            self.input_size = (640, 640)

        self.ort_session = None
        self.ort_input_name = None
        self.cv_net = None
        self.runtime_name = ""

        self._init_runtime()

    def _init_runtime(self) -> None:
        """Ưu tiên ONNX Runtime cho tốc độ CPU tốt nhất, tự động lùi về OpenCV DNN nếu chưa cài ORT."""
        try:
            import onnxruntime as ort

            self.ort_session = ort.InferenceSession(
                str(self.model_path),
                providers=["CPUExecutionProvider"],
            )
            self.ort_input_name = self.ort_session.get_inputs()[0].name
            self.runtime_name = "ONNX Runtime"
            return
        except ImportError:
            pass
        except Exception as exc:
            print(f"[YOLO Warning] Không khởi tạo được ONNX Runtime ({exc}), chuyển sang OpenCV DNN...")

        self.cv_net = cv2.dnn.readNetFromONNX(str(self.model_path))
        self.runtime_name = "OpenCV DNN"

    def _letterbox(
        self, image: np.ndarray, new_shape: Tuple[int, int]
    ) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        """Resize giữ nguyên tỷ lệ ảnh và thêm viền xám (chuẩn tiền xử lý YOLOv8)."""
        h, w = image.shape[:2]
        target_h, target_w = new_shape

        ratio = min(target_w / w, target_h / h)
        new_unpad_w = int(round(w * ratio))
        new_unpad_h = int(round(h * ratio))

        dw = (target_w - new_unpad_w) / 2.0
        dh = (target_h - new_unpad_h) / 2.0

        if (w, h) != (new_unpad_w, new_unpad_h):
            resized = cv2.resize(image, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)
        else:
            resized = image

        top = int(round(dh - 0.1))
        bottom = int(round(dh + 0.1))
        left = int(round(dw - 0.1))
        right = int(round(dw + 0.1))

        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )
        return padded, ratio, (dw, dh)

    def _preprocess(self, frame: np.ndarray) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        """Tiền xử lý khung hình BGR -> Tensor NCHW float32 [0.0, 1.0]."""
        padded, ratio, pad = self._letterbox(frame, self.input_size)
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        blob = np.transpose(rgb, (2, 0, 1)).astype(np.float32) / 255.0
        blob = np.expand_dims(blob, axis=0)
        return np.ascontiguousarray(blob), ratio, pad

    def _postprocess(
        self,
        raw_output: np.ndarray,
        frame_shape: Tuple[int, int],
        ratio: float,
        pad: Tuple[float, float],
    ) -> List[Dict]:
        """Giải mã tensor đầu ra YOLOv8 (1, 4+C, 8400) kèm lọc NMS."""
        pred = np.squeeze(raw_output, axis=0)
        if pred.ndim != 2:
            return []

        # YOLOv8 xuất mặc định dạng (4 + num_classes, num_anchors) -> chuyển về (num_anchors, 4 + num_classes)
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T

        if pred.shape[1] < 5:
            return []

        boxes_cxcywh = pred[:, :4]
        class_scores = pred[:, 4:]

        class_ids = np.argmax(class_scores, axis=1)
        confidences = class_scores[np.arange(len(class_scores)), class_ids]

        valid_mask = confidences >= self.conf_threshold
        if not np.any(valid_mask):
            return []

        filtered_boxes = boxes_cxcywh[valid_mask]
        filtered_scores = confidences[valid_mask]
        filtered_classes = class_ids[valid_mask]

        frame_h, frame_w = frame_shape
        dw, dh = pad

        # Quy đổi tọa độ từ không gian letterbox về khung hình gốc
        cx = (filtered_boxes[:, 0] - dw) / ratio
        cy = (filtered_boxes[:, 1] - dh) / ratio
        bw = filtered_boxes[:, 2] / ratio
        bh = filtered_boxes[:, 3] / ratio

        x1 = np.clip(cx - bw / 2.0, 0, frame_w - 1)
        y1 = np.clip(cy - bh / 2.0, 0, frame_h - 1)
        x2 = np.clip(cx + bw / 2.0, 0, frame_w - 1)
        y2 = np.clip(cy + bh / 2.0, 0, frame_h - 1)

        nms_boxes = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1).astype(int).tolist()
        nms_scores = filtered_scores.astype(float).tolist()

        indices = cv2.dnn.NMSBoxes(nms_boxes, nms_scores, self.conf_threshold, self.iou_threshold)
        if len(indices) == 0:
            return []

        detections: List[Dict] = []
        for idx in np.array(indices).flatten():
            bx, by, w_box, h_box = nms_boxes[idx]
            if w_box <= 2 or h_box <= 2:
                continue
            cls_id = int(filtered_classes[idx])
            cls_name = self.class_names.get(cls_id, f"CLASS_{cls_id}")
            detections.append({
                "class_name": cls_name,
                "confidence": float(nms_scores[idx]),
                "bbox": (int(bx), int(by), int(w_box), int(h_box)),
                "center": (int(bx + w_box // 2), int(by + h_box // 2)),
            })

        return detections

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], float]:
        """Thực thi suy luận ONNX trên một khung hình và trả về danh sách detections + thời gian (ms)."""
        t0 = time.perf_counter()
        blob, ratio, pad = self._preprocess(frame)

        if self.ort_session is not None:
            raw_output = self.ort_session.run(None, {self.ort_input_name: blob})[0]
        else:
            self.cv_net.setInput(blob)
            raw_output = self.cv_net.forward()

        detections = self._postprocess(raw_output, frame.shape[:2], ratio, pad)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return detections, elapsed_ms


class ColorSortingDetector:
    """Bộ điều khiển Dual-Engine (YOLO ONNX + HSV Fallback) kết hợp Centroid Object Tracking."""

    def __init__(self, source=CAMERA_SOURCE):
        self.source = source
        self.cap = None
        self.last_trigger_time = 0.0
        self.last_detected_color = None
        self.last_confidence = 0.0
        self.last_inference_ms = 0.0
        self.current_fps = 0.0

        # Thống kê số lượng phát hiện trong phiên
        self.stats = {"RED": 0, "YELLOW": 0, "BLUE": 0, "TOTAL": 0}

        # Khởi tạo các Engine nhận diện & Object Tracker
        self.hsv_detector = HsvColorDetector()
        self.yolo_detector: Optional[YoloOnnxDetector] = None
        self.active_backend = "HSV"

        self._init_dual_engine()

        self.tracker = CentroidTracker(
            max_disappeared=TRACKER_MAX_DISAPPEARED,
            max_distance=TRACKER_MAX_DISTANCE,
            min_hits=TRACKER_MIN_HITS,
        )

    def _init_dual_engine(self) -> None:
        """Khởi tạo YOLO ONNX nếu được cấu hình; tự động Fallback sang HSV khi thiếu model."""
        if DETECTOR_BACKEND == "YOLO":
            try:
                self.yolo_detector = YoloOnnxDetector(
                    model_path=YOLO_MODEL_PATH,
                    conf_threshold=YOLO_CONF_THRESHOLD,
                    iou_threshold=YOLO_IOU_THRESHOLD,
                    fallback_names=YOLO_CLASSES_FALLBACK,
                )
                self.active_backend = "YOLO"
                print(
                    f"[AI Engine] ✅ Đã nạp YOLOv8 ONNX ({self.yolo_detector.runtime_name}) | "
                    f"Classes: {list(self.yolo_detector.class_names.values())} | "
                    f"Conf >= {YOLO_CONF_THRESHOLD:.2f}"
                )
                return
            except Exception as exc:
                print(f"[AI Engine Warning] ⚠️ Không thể khởi tạo YOLO ONNX ({exc}).")
                print("[AI Engine Fallback] 🔄 Tự động lùi về chế độ HSV Color Masking.")
                self.yolo_detector = None
                self.active_backend = "HSV"
        else:
            self.active_backend = "HSV"
            print("[AI Engine] 🎨 Đang chạy ở chế độ cấu hình: HSV Color Masking.")

    def toggle_backend(self) -> None:
        """Chuyển đổi trực tiếp giữa YOLO và HSV (nếu model ONNX khả dụng)."""
        if self.active_backend == "YOLO":
            self.active_backend = "HSV"
            self.tracker.reset()
            print("[AI Engine] 🔄 Đã chuyển sang chế độ: HSV")
            return

        if self.yolo_detector is None:
            try:
                self.yolo_detector = YoloOnnxDetector(
                    model_path=YOLO_MODEL_PATH,
                    conf_threshold=YOLO_CONF_THRESHOLD,
                    iou_threshold=YOLO_IOU_THRESHOLD,
                    fallback_names=YOLO_CLASSES_FALLBACK,
                )
            except Exception as exc:
                print(f"[AI Engine Warning] ⚠️ Không thể chuyển sang YOLO ({exc}). Vẫn giữ HSV.")
                return

        self.active_backend = "YOLO"
        self.tracker.reset()
        print(f"[AI Engine] 🔄 Đã chuyển sang chế độ: YOLO ({self.yolo_detector.runtime_name})")

    def init_camera(self) -> bool:
        """Khởi động Camera hoặc Fallback sang Video giả lập nếu không có Webcam."""
        print(f"[Camera] Đang mở nguồn Camera: {self.source}...")
        if isinstance(self.source, int) and sys.platform.startswith("win"):
            # Trên Windows, mở qua DirectShow (CAP_DSHOW) trước để tương thích webcam USB ngoài
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.source)
        else:
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            print(f"[Camera Warning] Không thể mở Camera ID {self.source}. Chuyển sang chế độ giả lập trực quan (Synthetic Feed)...")
            self.cap = None
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        print("[Camera] ✅ Đã kết nối Camera thành công.")
        return True

    def _generate_synthetic_frame(self, frame_idx: int) -> np.ndarray:
        """Tạo khung hình giả lập băng chuyền có vật thể chuyển động phục vụ test khi không có camera vật lý."""
        frame = np.full((FRAME_HEIGHT, FRAME_WIDTH, 3), 35, dtype=np.uint8)

        # Vẽ băng chuyền màu xám đậm
        cv2.rectangle(frame, (0, int(FRAME_HEIGHT * 0.2)), (FRAME_WIDTH, int(FRAME_HEIGHT * 0.8)), (50, 50, 50), -1)
        for x in range(0, FRAME_WIDTH, 60):
            cv2.line(frame, (x, int(FRAME_HEIGHT * 0.2)), (x, int(FRAME_HEIGHT * 0.8)), (70, 70, 70), 2)

        # Mô phỏng vật thể chạy ngang qua màn hình
        cycle = frame_idx % 240
        obj_x = int((cycle / 240.0) * (FRAME_WIDTH + 100)) - 50
        obj_y = int(FRAME_HEIGHT * 0.5)

        color_type = (frame_idx // 240) % 3
        if color_type == 0:
            color_bgr = (0, 0, 230)    # RED
        elif color_type == 1:
            color_bgr = (0, 220, 255)  # YELLOW
        else:
            color_bgr = (240, 60, 0)   # BLUE

        cv2.circle(frame, (obj_x, obj_y), 45, color_bgr, -1)
        cv2.putText(frame, "CHE DO MO PHONG (SYNTHETIC CONVEYOR)", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        return frame

    def _draw_tracked_object(self, frame: np.ndarray, obj: TrackedObject) -> None:
        """Vẽ Bounding Box, quỹ đạo tâm và Track ID lên khung hình."""
        bx, by, bw, bh = obj.bbox
        cx, cy = obj.centroid
        box_color = DISPLAY_COLORS.get(obj.class_name, (255, 255, 255))

        # Vẽ quỹ đạo di chuyển gần nhất
        if len(obj.history) >= 2:
            pts = list(obj.history)
            for i in range(1, len(pts)):
                cv2.line(frame, pts[i - 1], pts[i], box_color, 2)

        thickness = 2 if obj.has_triggered else 3
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), box_color, thickness)
        cv2.circle(frame, (cx, cy), 6, (0, 0, 0), -1)
        cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)

        sent_tag = " [SENT]" if obj.has_triggered else ""
        label = f"[ID:{obj.track_id}] {obj.class_name} {obj.confidence * 100:.0f}%{sent_tag}"
        cv2.putText(frame, label, (bx, max(25, by - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2, cv2.LINE_AA)

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Xử lý suy luận AI/HSV, cập nhật Centroid Tracker và kích hoạt phân loại trong ROI."""
        h, w, _ = frame.shape

        # 1. Tính toán vùng ROI Trigger Zone
        roi_xmin = int(w * ROI_X_START)
        roi_xmax = int(w * ROI_X_END)
        roi_ymin = int(h * ROI_Y_START)
        roi_ymax = int(h * ROI_Y_END)
        roi_bounds = (roi_xmin, roi_ymin, roi_xmax, roi_ymax)

        # 2. Chạy suy luận theo Engine hiện hành
        if self.active_backend == "YOLO" and self.yolo_detector is not None:
            detections, inf_ms = self.yolo_detector.detect(frame)
        else:
            detections, inf_ms = self.hsv_detector.detect(frame, roi_bounds)
        self.last_inference_ms = inf_ms

        # 3. Cập nhật bộ theo dõi đối tượng (Centroid Tracker)
        tracked_objects = self.tracker.update(detections)

        # 4. Kiểm tra điều kiện kích hoạt phân loại (0% Duplicate Trigger theo Track ID)
        just_triggered = False
        for obj in tracked_objects.values():
            if obj.disappeared > 0:
                continue

            if self.tracker.is_ready_to_trigger(obj, roi_bounds):
                obj.has_triggered = True
                just_triggered = True
                self.last_trigger_time = time.time()
                self.last_detected_color = obj.class_name
                self.last_confidence = obj.confidence

                if obj.class_name not in self.stats:
                    self.stats[obj.class_name] = 0
                self.stats[obj.class_name] += 1
                self.stats["TOTAL"] += 1

                print(
                    f"\n[EVENT TRIGGER] 🎯 [ID:{obj.track_id}] Phát hiện {obj.class_name} "
                    f"({obj.confidence * 100:.1f}%) - Bắn tín hiệu sang ESP32 & Cloud..."
                )
                dispatcher.dispatch_sorting_event(
                    obj.class_name,
                    obj.confidence,
                    track_id=obj.track_id,
                )

            self._draw_tracked_object(frame, obj)

        # 5. Vẽ khung ROI Trigger Zone
        recently_triggered = just_triggered or ((time.time() - self.last_trigger_time) < 0.45)
        roi_border_color = (0, 255, 0) if recently_triggered else DISPLAY_COLORS["ROI_LINE"]
        cv2.rectangle(frame, (roi_xmin, roi_ymin), (roi_xmax, roi_ymax), roi_border_color, 2)

        roi_text = "ROI TRIGGER ZONE [TRIGGERED!]" if recently_triggered else f"ROI TRIGGER ZONE [{self.active_backend}]"
        cv2.putText(frame, roi_text, (roi_xmin + 5, roi_ymin - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, roi_border_color, 1, cv2.LINE_AA)

        # 6. Vẽ HUD thông tin SCADA
        self._draw_hud(frame)
        return frame

    def _draw_hud(self, frame: np.ndarray) -> None:
        """Vẽ bảng điều khiển HUD giám sát số liệu trực tiếp trên màn hình."""
        h, w, _ = frame.shape

        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (315, 148), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (10, 10), (315, 148), (80, 80, 80), 1)

        engine_tag = self.active_backend
        if self.active_backend == "YOLO" and self.yolo_detector is not None:
            engine_tag = f"YOLO ({self.yolo_detector.runtime_name})"

        cv2.putText(frame, f"ENGINE: {engine_tag}", (20, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # Đếm số lượng
        cv2.putText(frame, f"RED: {self.stats.get('RED', 0)}", (20, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, f"YELLOW: {self.stats.get('YELLOW', 0)}", (105, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 2)
        cv2.putText(frame, f"BLUE: {self.stats.get('BLUE', 0)}", (210, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 60, 0), 2)

        cv2.putText(
            frame,
            f"TOTAL: {self.stats['TOTAL']} | FPS: {self.current_fps:.1f} | INF: {self.last_inference_ms:.1f}ms",
            (20, 86),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (255, 255, 255),
            1,
        )

        last_event = (
            f"LAST: {self.last_detected_color} ({self.last_confidence:.2f})"
            if self.last_detected_color
            else "LAST: WAITING..."
        )
        cv2.putText(frame, last_event, (20, 112),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        cv2.putText(frame, f"ACTIVE TRACKS: {len(self.tracker.objects)}", (20, 136),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.43, (150, 220, 150), 1)

        # Hướng dẫn phím tắt góc dưới
        cv2.putText(
            frame,
            "[Q]: Thoat | [E]: Doi YOLO/HSV | [M]: Resize | [R/Y/B]: Test | [C]: Reset",
            (10, h - 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (180, 180, 180),
            1,
        )

    def run(self) -> None:
        """Vòng lặp chính xử lý video theo thời gian thực."""
        has_real_camera = self.init_camera()
        window_name = "IoT Smart Sorting - Dual-Engine Edge Vision"

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        initial_w, initial_h = 640, 480
        cv2.resizeWindow(window_name, initial_w, initial_h)
        is_mini_mode = False

        print("\n" + "=" * 65)
        print("🚀 SCADA COLOR SORTING - DUAL-ENGINE COMPUTER VISION RUNNING")
        print(f"   - Engine hiện tại : {self.active_backend}")
        print("   - Phím [E]: Chuyển đổi trực tiếp giữa YOLO <-> HSV")
        print("   - Phím [M]: Thu nhỏ (480x360) / Phóng to (640x480)")
        print("   - Phím [Q]: Thoát ứng dụng")
        print("   - Phím [R]: Bắn test màu ĐỎ (RED)")
        print("   - Phím [Y]: Bắn test màu VÀNG (YELLOW)")
        print("   - Phím [B]: Bắn test màu XANH DƯƠNG (BLUE)")
        print("   - Phím [C]: Xóa bộ đếm & reset Tracker")
        if not has_real_camera and self.active_backend == "YOLO":
            print("   💡 Gợi ý: Đang chạy giả lập Synthetic, bấm [E] sang HSV để test hình tròn giả lập!")
        print("=" * 65 + "\n")

        frame_idx = 0
        prev_time = time.time()

        try:
            while True:
                if has_real_camera and self.cap:
                    ret, frame = self.cap.read()
                    if not ret:
                        print("[Camera Error] Mất kết nối Camera, chuyển sang chế độ giả lập...")
                        has_real_camera = False
                        continue
                else:
                    frame = self._generate_synthetic_frame(frame_idx)
                    time.sleep(1.0 / FPS_LIMIT)

                now = time.time()
                dt = max(1e-6, now - prev_time)
                self.current_fps = 0.85 * self.current_fps + 0.15 * (1.0 / dt) if self.current_fps > 0 else (1.0 / dt)
                prev_time = now

                processed_frame = self.process_frame(frame)
                cv2.imshow(window_name, processed_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    break
                elif key == ord("e"):
                    self.toggle_backend()
                elif key == ord("m"):
                    is_mini_mode = not is_mini_mode
                    if is_mini_mode:
                        cv2.resizeWindow(window_name, 480, 360)
                        print("[Window] 🔍 Chuyển sang kích thước thu nhỏ (480x360)")
                    else:
                        cv2.resizeWindow(window_name, 640, 480)
                        print("[Window] 🔍 Chuyển sang kích thước gốc (640x480)")
                elif key == ord("r"):
                    print("[Manual Trigger] 🔴 Bắn test màu RED")
                    dispatcher.dispatch_sorting_event("RED", 0.99)
                elif key == ord("y"):
                    print("[Manual Trigger] 🟡 Bắn test màu YELLOW")
                    dispatcher.dispatch_sorting_event("YELLOW", 0.99)
                elif key == ord("b"):
                    print("[Manual Trigger] 🔵 Bắn test màu BLUE")
                    dispatcher.dispatch_sorting_event("BLUE", 0.99)
                elif key == ord("g"):
                    print("[Manual Trigger] 🟢 Bắn test màu GREEN")
                    dispatcher.dispatch_sorting_event("GREEN", 0.99)
                elif key == ord("c"):
                    self.stats = {"RED": 0, "YELLOW": 0, "BLUE": 0, "TOTAL": 0}
                    self.tracker.reset()
                    print("[Stats] Đã xóa bộ đếm và đặt lại Tracker.")

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
