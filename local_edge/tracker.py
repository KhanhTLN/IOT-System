"""
Centroid Object Tracker - IoT Smart Sorting System
Local Edge Node - Giai đoạn 3

Nhiệm vụ:
- Theo dõi các vật thể qua từng khung hình liên tiếp bằng khoảng cách Euclidean giữa tâm (Centroid).
- Cấp phát Track ID duy nhất cho từng sản phẩm đi qua băng chuyền.
- Quản lý cờ 'has_triggered' và lịch sử tọa độ để chống kích hoạt trùng lặp (0% Duplicate Trigger).
"""

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple

import numpy as np


@dataclass
class TrackedObject:
    """Thông tin trạng thái của một vật thể đang được theo dõi."""

    track_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    centroid: Tuple[int, int]        # (cx, cy)
    disappeared: int = 0
    hit_count: int = 1
    has_triggered: bool = False
    history: Deque[Tuple[int, int]] = field(default_factory=lambda: deque(maxlen=20))

    def __post_init__(self):
        if not self.history:
            self.history.append(self.centroid)


class CentroidTracker:
    """Bộ theo dõi đối tượng theo tâm hình học (Euclidean Centroid Matching)."""

    def __init__(self, max_disappeared: int = 15, max_distance: float = 85.0, min_hits: int = 2):
        self.next_object_id: int = 1
        self.objects: OrderedDict[int, TrackedObject] = OrderedDict()
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.min_hits = min_hits

    def reset(self) -> None:
        """Đặt lại toàn bộ trạng thái tracker (dùng khi nhấn Reset hoặc đổi Engine)."""
        self.objects.clear()
        self.next_object_id = 1

    def _register(self, detection: Dict) -> TrackedObject:
        """Đăng ký một vật thể mới và cấp phát Track ID tăng dần."""
        obj = TrackedObject(
            track_id=self.next_object_id,
            class_name=detection["class_name"],
            confidence=float(detection["confidence"]),
            bbox=tuple(detection["bbox"]),
            centroid=tuple(detection["center"]),
        )
        self.objects[self.next_object_id] = obj
        self.next_object_id += 1
        return obj

    def _deregister(self, track_id: int) -> None:
        """Hủy theo dõi vật thể đã rời khỏi khung hình."""
        if track_id in self.objects:
            del self.objects[track_id]

    def update(self, detections: List[Dict]) -> Dict[int, TrackedObject]:
        """
        Cập nhật danh sách vật thể từ kết quả nhận diện của khung hình hiện tại.
        Mỗi phần tử trong 'detections' cần có: {'class_name', 'confidence', 'bbox', 'center'}.
        """
        # Trường hợp không phát hiện vật thể nào trong frame hiện tại
        if not detections:
            for track_id in list(self.objects.keys()):
                self.objects[track_id].disappeared += 1
                if self.objects[track_id].disappeared > self.max_disappeared:
                    self._deregister(track_id)
            return self.objects

        # Trường hợp chưa có vật thể nào đang theo dõi -> đăng ký toàn bộ
        if not self.objects:
            for det in detections:
                self._register(det)
            return self.objects

        object_ids = list(self.objects.keys())
        object_centroids = np.array([self.objects[tid].centroid for tid in object_ids], dtype=np.float32)
        input_centroids = np.array([det["center"] for det in detections], dtype=np.float32)

        # Tính ma trận khoảng cách Euclidean (M x N) thuần NumPy
        diff = object_centroids[:, np.newaxis, :] - input_centroids[np.newaxis, :, :]
        dist_matrix = np.linalg.norm(diff, axis=2)

        # Ghép cặp theo thứ tự khoảng cách nhỏ nhất trước (Greedy matching 1-1)
        rows = dist_matrix.min(axis=1).argsort()
        cols = dist_matrix.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue
            if dist_matrix[row, col] > self.max_distance:
                continue

            track_id = object_ids[row]
            det = detections[col]
            tracked = self.objects[track_id]

            tracked.centroid = tuple(det["center"])
            tracked.bbox = tuple(det["bbox"])
            tracked.confidence = float(det["confidence"])
            # Giữ nguyên class đã trigger để tránh nhấp nháy nhãn sau khi đã phân loại
            if not tracked.has_triggered:
                tracked.class_name = det["class_name"]
            tracked.disappeared = 0
            tracked.hit_count += 1
            tracked.history.append(tracked.centroid)

            used_rows.add(row)
            used_cols.add(col)

        # Tăng bộ đếm biến mất cho các track không ghép được cặp
        unused_rows = set(range(dist_matrix.shape[0])) - used_rows
        for row in unused_rows:
            track_id = object_ids[row]
            self.objects[track_id].disappeared += 1
            if self.objects[track_id].disappeared > self.max_disappeared:
                self._deregister(track_id)

        # Đăng ký vật thể mới cho các detection chưa ghép cặp
        unused_cols = set(range(dist_matrix.shape[1])) - used_cols
        for col in unused_cols:
            self._register(detections[col])

        return self.objects

    def is_ready_to_trigger(self, obj: TrackedObject, roi_bounds: Tuple[int, int, int, int]) -> bool:
        """
        Kiểm tra vật thể đủ điều kiện kích hoạt phân loại hay chưa:
        1. Chưa từng kích hoạt trước đó (has_triggered == False)
        2. Đã xuất hiện ổn định tối thiểu >= min_hits frames liên tiếp
        3. Tâm vật thể đang nằm trong vùng ROI Trigger Zone
        """
        if obj.has_triggered or obj.disappeared > 0 or obj.hit_count < self.min_hits:
            return False

        roi_xmin, roi_ymin, roi_xmax, roi_ymax = roi_bounds
        cx, cy = obj.centroid
        return (roi_xmin <= cx <= roi_xmax) and (roi_ymin <= cy <= roi_ymax)

