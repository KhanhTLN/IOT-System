import time
import random
import requests
import argparse

API_URL = "http://localhost:8000/api/v1/logs"
COLORS = ["RED", "YELLOW", "GREEN"]

def send_single_log(color=None, confidence=None, api_url=API_URL):
    if not color:
        color = random.choice(COLORS)
    if confidence is None:
        confidence = round(random.uniform(0.85, 0.99), 2)
        
    payload = {
        "color_label": color,
        "confidence": confidence
    }
    try:
        response = requests.post(api_url, json=payload, timeout=3)
        if response.status_code == 201:
            data = response.json()
            print(f"✅ [GỬI THÀNH CÔNG] ID: {data['id']} | Màu: {data['color_label']} | Confidence: {data['confidence']}")
        else:
            print(f"❌ [LỖI API {response.status_code}]: {response.text}")
    except Exception as e:
        print(f"❌ [KHÔNG THỂ KẾT NỐI API]: {e}")

def run_simulation(interval=2, count=None, force_color=None, api_url=API_URL):
    print(f"🚀 Bắt đầu giả lập gửi dữ liệu phân loại tới API: {api_url}")
    print(f"⏱️ Tần suất: {interval} giây/lần | Chế độ: {'Màu chỉ định: ' + force_color if force_color else 'Ngẫu nhiên 3 màu'}")
    print("Nhấn Ctrl+C để dừng giả lập.\n")
    
    sent = 0
    try:
        while True:
            color = force_color if force_color else random.choice(COLORS)
            send_single_log(color=color, api_url=api_url)
            sent += 1
            if count and sent >= count:
                print(f"\n🎉 Đã gửi đủ {count} mẩu tin giả lập!")
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng giả lập.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script Giả Lập Gửi Log Phân Loại Tới Backend API")
    parser.add_argument("--url", type=str, default=API_URL, help="URL endpoint API FastAPI")
    parser.add_argument("--interval", type=float, default=2.0, help="Thời gian giãn cách giữa các lần gửi (giây)")
    parser.add_argument("--count", type=int, default=None, help="Số lượng log cần gửi (mặc định lặp vô tận)")
    parser.add_argument("--color", type=str, default=None, help="Ép buộc gửi 1 màu duy nhất (RED, YELLOW, GREEN) để test cảnh báo bất thường")
    
    args = parser.parse_args()
    run_simulation(interval=args.interval, count=args.count, force_color=args.color, api_url=args.url)
