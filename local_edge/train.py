"""
YOLOv8n Transfer Learning Script - IoT Smart Sorting System
Local Edge Node - Giai đoạn 2

Chức năng:
1. Kiểm tra tính toàn vẹn dữ liệu (ảnh & nhãn chuẩn YOLO trong datasets/).
2. Huấn luyện mô hình YOLOv8 Nano (yolov8n.pt) nhận diện 3 lớp: RED, YELLOW, BLUE.
3. Đánh giá mAP@50, Confusion Matrix và tự động lưu trọng số tốt nhất vào local_edge/models/best.pt.
4. Tự động xuất mô hình sang định dạng ONNX (local_edge/models/best.onnx) tối ưu cho Edge CPU.
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Tuple

# Đảm bảo in tiếng Việt mượt mà trên Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.append(str(CURRENT_DIR))

from export_onnx import export_pt_to_onnx

DEFAULT_DATA_YAML = CURRENT_DIR / "datasets" / "data.yaml"
DEFAULT_MODELS_DIR = CURRENT_DIR / "models"
DEFAULT_RUNS_DIR = CURRENT_DIR / "runs" / "detect"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _load_yaml(yaml_path: Path) -> Dict:
    """Đọc cấu hình dataset từ file YAML (hỗ trợ fallback nếu chưa cài PyYAML)."""
    try:
        import yaml

        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        cfg: Dict = {"names": {}}
        in_names = False
        with open(yaml_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.split("#", 1)[0].rstrip()
                if not line.strip():
                    continue
                if line.startswith("names:"):
                    in_names = True
                    continue
                if in_names and (line.startswith(" ") or line.startswith("\t")):
                    k, _, v = line.strip().partition(":")
                    if k.strip().isdigit():
                        cfg["names"][int(k.strip())] = v.strip().strip("'\"")
                    continue
                in_names = False
                k, _, v = line.partition(":")
                if v.strip():
                    cfg[k.strip()] = v.strip().strip("'\"")
        return cfg


def _count_split_files(dataset_root: Path, split_rel: str) -> Tuple[int, int]:
    """Đếm số lượng ảnh và file nhãn .txt tương ứng trong một phân tập (train/val/test)."""
    img_dir = (dataset_root / split_rel).resolve()
    if not img_dir.exists():
        return 0, 0

    images = [p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]

    # Thư mục labels tương ứng (thay 'images' -> 'labels' theo chuẩn YOLO)
    parts = list(Path(split_rel).parts)
    if "images" in parts:
        idx = parts.index("images")
        parts[idx] = "labels"
        lbl_dir = (dataset_root / Path(*parts)).resolve()
    else:
        lbl_dir = dataset_root / "labels"

    labeled_count = 0
    if lbl_dir.exists():
        for img_path in images:
            if (lbl_dir / f"{img_path.stem}.txt").exists():
                labeled_count += 1

    return len(images), labeled_count


def validate_dataset(data_yaml: Path) -> Tuple[bool, Dict]:
    """Kiểm tra cấu trúc dữ liệu, số lượng ảnh và file nhãn trước khi train."""
    data_yaml = Path(data_yaml).resolve()
    if not data_yaml.exists():
        print(f"[Dataset Error] ❌ Không tìm thấy file cấu hình: {data_yaml}")
        return False, {}

    cfg = _load_yaml(data_yaml)
    raw_path = cfg.get("path", ".")
    dataset_root = (data_yaml.parent / raw_path).resolve()

    names = cfg.get("names", {})
    print("\n" + "=" * 62)
    print("📦 KIỂM TRA DỮ LIỆU HUẤN LUYỆN (DATASET PRE-FLIGHT CHECK)")
    print("=" * 62)
    print(f"  • File YAML   : {data_yaml}")
    print(f"  • Thư mục gốc : {dataset_root}")
    print(f"  • Danh mục lớp: {names}")

    split_stats = {}
    for split in ("train", "val", "test"):
        rel = cfg.get(split)
        if not rel:
            continue
        img_cnt, lbl_cnt = _count_split_files(dataset_root, rel)
        split_stats[split] = (img_cnt, lbl_cnt)
        status = "✅" if (split == "test" or (img_cnt > 0 and lbl_cnt > 0)) else "⚠️"
        print(f"  • Tập {split:<5}   : {img_cnt:>4} ảnh | {lbl_cnt:>4} file nhãn (.txt) {status}")

    print("=" * 62)

    train_imgs, train_lbls = split_stats.get("train", (0, 0))
    val_imgs, val_lbls = split_stats.get("val", (0, 0))

    if train_imgs == 0 or train_lbls == 0:
        print("\n[Dataset Warning] ⚠️ Chưa có dữ liệu ảnh hoặc file nhãn trong tập 'train'!")
        print("👉 Hướng dẫn chuẩn bị dữ liệu:")
        print("   1. Upload ảnh từ điện thoại vào local_edge/datasets/raw/{RED, YELLOW, BLUE}/")
        print("   2. Gán nhãn trên Roboflow (3 lớp: RED, YELLOW, BLUE) -> Export định dạng YOLOv8")
        print("   3. Giải nén thư mục images/ và labels/ vào local_edge/datasets/")
        print("   4. Chạy lại lệnh: python local_edge/train.py --check-only")
        return False, cfg

    if val_imgs == 0 or val_lbls == 0:
        print("\n[Dataset Warning] ⚠️ Tập 'val' hiện đang trống! Hãy chia ít nhất 15-20% dữ liệu vào val.")
        return False, cfg

    return True, cfg


def _build_resolved_yaml(cfg: Dict, data_yaml: Path, target_dir: Path) -> Path:
    """Tạo bản sao YAML với đường dẫn tuyệt đối để tránh lỗi thư mục làm việc của Ultralytics."""
    import yaml

    resolved_cfg = dict(cfg)
    dataset_root = (data_yaml.parent / cfg.get("path", ".")).resolve()
    resolved_cfg["path"] = str(dataset_root)

    target_dir.mkdir(parents=True, exist_ok=True)
    temp_yaml = target_dir / "resolved_data.yaml"
    with open(temp_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(resolved_cfg, f, allow_unicode=True, sort_keys=False)
    return temp_yaml


def train_model(args) -> int:
    """Thực thi quy trình Transfer Learning YOLOv8n và xuất model ONNX."""
    is_valid, cfg = validate_dataset(args.data)
    if args.check_only:
        return 0 if is_valid else 1
    if not is_valid:
        return 1

    try:
        from ultralytics import YOLO
        import torch
    except ImportError:
        print("\n[Train Error] ❌ Chưa cài đặt thư viện huấn luyện ('ultralytics', 'torch').")
        print("👉 Cài đặt cục bộ: pip install -r local_edge/requirements-train.txt")
        print("👉 Hoặc sử dụng Google Colab GPU miễn phí với file: local_edge/train_colab.ipynb")
        return 1

    device = args.device
    if not device:
        device = "0" if torch.cuda.is_available() else "cpu"

    print(f"\n[Train] 🚀 Bắt đầu huấn luyện {args.model} trên thiết bị: {device.upper()}")
    print(f"        Epochs: {args.epochs} | Batch: {args.batch} | ImgSz: {args.imgsz} | Optimizer: {args.optimizer}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        resolved_yaml = _build_resolved_yaml(cfg, args.data.resolve(), Path(tmp_dir))

        model = YOLO(args.model)
        results = model.train(
            data=str(resolved_yaml),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            optimizer=args.optimizer,
            lr0=args.lr0,
            patience=args.patience,
            device=device,
            project=str(DEFAULT_RUNS_DIR),
            name=args.name,
            exist_ok=True,
            plots=True,
            verbose=True,
        )

    save_dir = Path(results.save_dir)
    best_pt_src = save_dir / "weights" / "best.pt"
    if not best_pt_src.exists():
        print(f"[Train Error] ❌ Không tìm thấy trọng số best.pt sau khi train tại: {best_pt_src}")
        return 1

    # Sao chép trọng số tốt nhất vào local_edge/models/best.pt
    DEFAULT_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    best_pt_dst = DEFAULT_MODELS_DIR / "best.pt"
    shutil.copy2(best_pt_src, best_pt_dst)

    print("\n" + "=" * 62)
    print("🏆 HOÀN TẤT HUẤN LUYỆN MÔ HÌNH YOLOv8n")
    print("=" * 62)
    print(f"  • Trọng số tốt nhất : {best_pt_dst}")
    print(f"  • Biểu đồ & Matrix  : {save_dir}")

    # In tóm tắt chỉ số nghiệm thu nếu có
    try:
        metrics = getattr(results, "results_dict", {})
        map50 = metrics.get("metrics/mAP50(B)")
        map50_95 = metrics.get("metrics/mAP50-95(B)")
        if map50 is not None:
            status = "✅ ĐẠT CHUẨN (>= 0.95)" if map50 >= 0.95 else "⚠️ CHƯA ĐẠT MỤC TIÊU (< 0.95 - Cần thêm dữ liệu)"
            print(f"  • mAP@50            : {map50:.4f} -> {status}")
        if map50_95 is not None:
            print(f"  • mAP@50-95         : {map50_95:.4f}")
    except Exception:
        pass
    print("=" * 62)

    # Tự động export sang ONNX cho Edge inference
    if not args.no_export:
        onnx_dst = DEFAULT_MODELS_DIR / "best.onnx"
        export_pt_to_onnx(
            weights_path=best_pt_dst,
            output_path=onnx_dst,
            imgsz=args.imgsz,
            opset=12,
            simplify=True,
            verify=True,
        )

    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Huấn luyện mô hình YOLOv8n phân loại màu RED / YELLOW / BLUE.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_YAML, help="Đường dẫn tới file data.yaml")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Mô hình nền pretrained (mặc định: yolov8n.pt)")
    parser.add_argument("--epochs", type=int, default=80, help="Số vòng lặp huấn luyện (mặc định: 80)")
    parser.add_argument("--batch", type=int, default=16, help="Kích thước batch (mặc định: 16)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh đầu vào (mặc định: 640)")
    parser.add_argument("--lr0", type=float, default=0.001, help="Learning rate khởi tạo (mặc định: 0.001)")
    parser.add_argument("--optimizer", type=str, default="AdamW", help="Thuật toán tối ưu (mặc định: AdamW)")
    parser.add_argument("--patience", type=int, default=20, help="Số epoch dừng sớm nếu val không cải thiện")
    parser.add_argument("--device", type=str, default="", help="Thiết bị: '0' (GPU), 'cpu', hoặc để trống tự động")
    parser.add_argument("--name", type=str, default="smart_sorting_yolov8n", help="Tên thư mục lưu kết quả train")
    parser.add_argument("--no-export", action="store_true", help="Không tự động xuất ONNX sau khi train xong")
    parser.add_argument("--check-only", action="store_true", help="Chỉ kiểm tra dữ liệu dataset mà không train")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(train_model(parse_args()))
