"""
ONNX Model Exporter & Compatibility Verifier
IoT Smart Sorting System - Local Edge Node

Chức năng:
1. Chuyển đổi trọng số PyTorch (.pt) sang định dạng ONNX tối ưu cho Edge CPU.
2. Kiểm tra tính tương thích (Inference Dry-Run) bằng ONNX Runtime & OpenCV DNN.
"""

import argparse
import ast
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np

# Đảm bảo in tiếng Việt mượt mà trên Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_PT_PATH = CURRENT_DIR / "models" / "best.pt"
DEFAULT_ONNX_PATH = CURRENT_DIR / "models" / "best.onnx"
EXPECTED_CLASSES = {"RED", "YELLOW", "BLUE"}


def extract_onnx_metadata(onnx_path: Path) -> Dict[str, Any]:
    """
    Trích xuất metadata ('names', 'imgsz') nhúng trong file ONNX của Ultralytics
    mà không bắt buộc phải cài đặt thư viện 'onnx'.
    """
    meta: Dict[str, Any] = {}
    onnx_path = Path(onnx_path)
    if not onnx_path.exists():
        return meta

    # Ưu tiên đọc qua ONNX Runtime API nếu có sẵn
    try:
        import onnxruntime as ort

        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        custom_meta = sess.get_modelmeta().custom_metadata_map
        if "names" in custom_meta:
            meta["names"] = ast.literal_eval(custom_meta["names"])
        if "imgsz" in custom_meta:
            meta["imgsz"] = ast.literal_eval(custom_meta["imgsz"])
        return meta
    except Exception:
        pass

    # Fallback: Đọc phần metadata_props ở cuối file protobuf ONNX
    try:
        with open(onnx_path, "rb") as f:
            f.seek(max(0, onnx_path.stat().st_size - 65536))
            tail = f.read().decode("latin1", errors="ignore")

        m_names = re.search(r"names[^\w{]*(\{[^}]+\})", tail)
        if m_names:
            meta["names"] = ast.literal_eval(m_names.group(1))

        m_imgsz = re.search(r"imgsz[^\w\[]*(\[[^\]]+\])", tail)
        if m_imgsz:
            meta["imgsz"] = ast.literal_eval(m_imgsz.group(1))
    except Exception:
        pass

    return meta


def verify_onnx_model(onnx_path: Path, imgsz: int = 640) -> bool:
    """Kiểm tra file ONNX có nạp và chạy suy luận giả lập được với OpenCV DNN & ONNX Runtime."""
    onnx_path = Path(onnx_path)
    if not onnx_path.exists():
        print(f"[Verify Error] ❌ Không tìm thấy file ONNX tại: {onnx_path}")
        return False

    file_size_mb = onnx_path.stat().st_size / (1024 * 1024)
    print(f"\n[Verify] 🔍 Đang kiểm tra mô hình ONNX: {onnx_path.name} ({file_size_mb:.2f} MB)...")

    meta = extract_onnx_metadata(onnx_path)
    if "imgsz" in meta and isinstance(meta["imgsz"], list) and meta["imgsz"]:
        imgsz = int(meta["imgsz"][0])
    if "names" in meta:
        names_map = meta["names"]
        print(f"[Metadata]     🏷️ Danh mục lớp nhúng trong model: {names_map}")
        found_classes = {str(v).upper() for v in names_map.values()}
        missing = EXPECTED_CLASSES - found_classes
        if missing:
            print(f"[Metadata]     ⚠️ Cảnh báo: Model hiện đang thiếu lớp {sorted(missing)} (mới train {len(found_classes)}/3 lớp).")
        else:
            print("[Metadata]     ✅ Đủ cả 3 lớp chuẩn: RED, YELLOW, BLUE.")

    dummy_input = np.random.rand(1, 3, imgsz, imgsz).astype(np.float32)

    all_ok = True

    # 1. Kiểm tra bằng ONNX Runtime (nếu đã cài)
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        input_meta = session.get_inputs()[0]
        output_meta = session.get_outputs()[0]

        t0 = time.perf_counter()
        outputs = session.run([output_meta.name], {input_meta.name: dummy_input})
        elapsed_ms = (time.perf_counter() - t0) * 1000

        print(
            f"[ONNX Runtime] ✅ OK | Input: {input_meta.name} {input_meta.shape} "
            f"-> Output: {output_meta.name} {outputs[0].shape} | Dry-run: {elapsed_ms:.1f} ms"
        )
    except ImportError:
        print("[ONNX Runtime] ℹ️ Chưa cài đặt 'onnxruntime' (bỏ qua bước kiểm tra ORT).")
    except Exception as exc:
        print(f"[ONNX Runtime] ❌ Lỗi khi chạy thử ONNX Runtime: {exc}")
        all_ok = False

    # 2. Kiểm tra bằng OpenCV DNN (luôn có sẵn trong venv)
    try:
        net = cv2.dnn.readNetFromONNX(str(onnx_path))
        net.setInput(dummy_input)
        t0 = time.perf_counter()
        cv_out = net.forward()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"[OpenCV DNN]   ✅ OK | Output shape: {cv_out.shape} | Dry-run: {elapsed_ms:.1f} ms")
    except Exception as exc:
        print(f"[OpenCV DNN]   ❌ Lỗi khi nạp bằng OpenCV DNN: {exc}")
        all_ok = False

    return all_ok


def export_pt_to_onnx(
    weights_path: Path,
    output_path: Optional[Path] = None,
    imgsz: int = 640,
    opset: int = 12,
    simplify: bool = True,
    verify: bool = True,
) -> Optional[Path]:
    """Xuất mô hình YOLOv8 từ PyTorch (.pt) sang định dạng ONNX chuẩn Edge."""
    weights_path = Path(weights_path).resolve()
    target_onnx = Path(output_path).resolve() if output_path else weights_path.with_suffix(".onnx")

    if not weights_path.exists():
        print(f"[Export Error] ❌ Không tìm thấy file trọng số PyTorch: {weights_path}")
        print("👉 Hãy chạy huấn luyện trước (train.py hoặc Google Colab) và đặt file vào local_edge/models/best.pt")
        return None

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[Export Error] ❌ Chưa cài đặt thư viện 'ultralytics'.")
        print("👉 Chạy lệnh: pip install -r local_edge/requirements-train.txt")
        return None

    print(f"[Export] ⚙️ Đang chuyển đổi {weights_path.name} -> ONNX (imgsz={imgsz}, opset={opset}, simplify={simplify})...")
    model = YOLO(str(weights_path))
    exported_file = Path(
        model.export(
            format="onnx",
            imgsz=imgsz,
            simplify=simplify,
            opset=opset,
            dynamic=False,
        )
    )

    target_onnx.parent.mkdir(parents=True, exist_ok=True)
    if exported_file.resolve() != target_onnx:
        shutil.copy2(exported_file, target_onnx)

    print(f"[Export] ✅ Đã xuất thành công mô hình ONNX tại: {target_onnx}")

    if verify:
        verify_onnx_model(target_onnx, imgsz=imgsz)

    return target_onnx


def parse_args():
    parser = argparse.ArgumentParser(description="Xuất mô hình YOLOv8 (.pt) sang ONNX và kiểm tra tương thích Edge.")
    parser.add_argument("--weights", type=Path, default=DEFAULT_PT_PATH, help="Đường dẫn file .pt nguồn")
    parser.add_argument("--output", type=Path, default=DEFAULT_ONNX_PATH, help="Đường dẫn lưu file .onnx đích")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh đầu vào (mặc định: 640)")
    parser.add_argument("--opset", type=int, default=12, help="Phiên bản ONNX opset (mặc định: 12 để tương thích OpenCV)")
    parser.add_argument("--no-simplify", action="store_true", help="Tắt tối ưu đồ thị ONNX simplify")
    parser.add_argument("--verify-only", action="store_true", help="Chỉ kiểm tra file ONNX đã có sẵn (không cần .pt)")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.verify_only:
        ok = verify_onnx_model(args.output, imgsz=args.imgsz)
        sys.exit(0 if ok else 1)

    exported = export_pt_to_onnx(
        weights_path=args.weights,
        output_path=args.output,
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=not args.no_simplify,
        verify=True,
    )
    sys.exit(0 if exported is not None else 1)


if __name__ == "__main__":
    main()

