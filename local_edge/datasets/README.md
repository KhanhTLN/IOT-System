giơ# 📦 Hướng Dẫn Thu Thập & Gán Nhãn Dữ Liệu YOLO (Dataset Pipeline)

Thư mục này quản lý tập dữ liệu hình ảnh dùng để huấn luyện mô hình học sâu **YOLOv8** nhận diện 3 dòng sản phẩm màu công nghiệp (**RED**, **YELLOW**, **BLUE**) phục vụ hệ thống phân loại tự động.

---

## 🏷️ 1. Quy định Danh mục Lớp (Class Mapping)

| Class ID | Tên Lớp (`class_name`) | Mô Tả | Màu Bounding Box |
| :---: | :---: | :--- | :--- |
| `0` | **`RED`** | Sản phẩm / Hộp màu đỏ | Đỏ `(0, 0, 255)` |
| `1` | **`YELLOW`** | Sản phẩm / Hộp màu vàng | Vàng `(0, 220, 255)` |
| `2` | **`BLUE`** | Sản phẩm / Hộp màu xanh dương | Xanh dương `(255, 0, 0)` |

---

## 📁 2. Cấu Trúc Thư Mục Dataset

Sau khi thu thập và gán nhãn, cấu trúc thư mục chuẩn được tổ chức như sau:

```text
local_edge/datasets/
├── data.yaml                  # File cấu hình tập dữ liệu cho YOLOv8
├── README.md                  # Tài liệu hướng dẫn này
├── raw/                       # [Tạm thời] Ảnh thô thu thập từ collect_dataset.py
│   ├── RED/
│   ├── YELLOW/
│   └── BLUE/
├── images/                    # Toàn bộ ảnh đã chia theo tập
│   ├── train/                 # Tập huấn luyện (70%)
│   ├── val/                   # Tập xác thực đánh giá (20%)
│   └── test/                  # Tập kiểm thử độc lập (10%)
└── labels/                    # File nhãn YOLO tương ứng (.txt)
    ├── train/
    ├── val/
    └── test/
```

> [!IMPORTANT]
> Thư mục `raw/`, `images/`, `labels/` đã được thêm vào `.gitignore` để tránh commit các file ảnh nặng lên Git repository.

---

## 📸 3. Quy Trình Thu Thập Ảnh Mẫu (`collect_dataset.py`)

1. Chạy công cụ thu thập ảnh:
   ```bash
   python local_edge/collect_dataset.py
   ```
2. Phím tắt điều khiển trên giao diện:
   - **`1`**: Chuyển sang nhãn **RED**
   - **`2`**: Chuyển sang nhãn **YELLOW**
   - **`3`** hoặc **`b`**: Chuyển sang nhãn **BLUE**
   - **`SPACE` (Phím cách)**: Chụp và lưu khung hình hiện tại vào thư mục tương ứng.
   - **`a`**: Bật/Tắt chế độ tự động chụp định kỳ (Auto Capture mỗi 0.8s khi có vật thể).
   - **`s`**: Bật/Tắt chế độ chỉ lưu vùng quan tâm ROI (Cắt ảnh theo ROI hoặc lưu toàn khung hình).
   - **`q`** hoặc **`ESC`**: Thoát chương trình.
3. Mục tiêu số lượng mẫu khuyến nghị:
   - Tối thiểu: **150 - 200 ảnh / lớp** (Tổng 450 - 600 ảnh).
   - Đa dạng hóa: Chụp ở các điều kiện ánh sáng khác nhau (bật đèn, tắt đèn bớt, bóng đổ) và các góc nghiêng khác nhau của sản phẩm.

---

## ✏️ 4. Hướng Dẫn Gán Nhãn (Data Annotation)

### Lựa chọn 1: Sử dụng Roboflow (Khuyến nghị - Nhanh & Trực quan)
1. Truy cập [Roboflow.com](https://roboflow.com), tạo dự án dạng **Object Detection**.
2. Tải toàn bộ ảnh từ `datasets/raw/` lên.
3. Kéo bounding box bao quanh sản phẩm và gán nhãn tương ứng (`RED`, `YELLOW`, `BLUE`).
4. Thêm Data Augmentation (nếu muốn): Lật ngang (Horizontal Flip), xoay nhẹ $\pm 10^\circ$, đổi độ sáng $\pm 15\%$.
5. Xuất dataset: Chọn định dạng **YOLOv8** $\rightarrow$ Tải file zip về giải nén vào thư mục `datasets/` (tự động tạo `images/` và `labels/`).

### Lựa chọn 2: Sử dụng công cụ mã nguồn mở LabelImg
1. Cài đặt: `pip install labelImg`
2. Chạy: `labelImg datasets/raw/RED`
3. Chọn chế độ lưu nhãn dạng **YOLO** (thay vì PascalVOC).
4. Tạo file `classes.txt` với 3 dòng:
   ```text
   RED
   YELLOW
   BLUE
   ```
5. Bounding box sẽ tự động tạo file `.txt` tương ứng với định dạng YOLO:
   ```text
   <class_id> <x_center> <y_center> <width> <height>
   ```
   *(Tất cả tọa độ được chuẩn hóa trong khoảng $0.0 \to 1.0$)*

