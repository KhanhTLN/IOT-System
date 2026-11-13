# Metrics cho hệ thống 3 trạm trên nhánh test/metrics

Firmware gửi 66 trường số trong JSON, mỗi 5 giây khi MQTT đang kết nối:

```text
factory/esp32/esp32_01/telemetry
```

## Phạm vi thay đổi

`main.ino` chỉ được thêm 18 khối đánh dấu `METRICS_BEGIN` / `METRICS_END`.
Các điều kiện, gán state, chân GPIO, góc servo, lệnh Serial, parser MQTT, timeout,
debounce, thứ tự đọc IR, xử lý bin sensor và logic Wi-Fi/MQTT ban đầu giữ nguyên.
Metrics không được dùng làm điều kiện để chạy thiết bị.

- `MetricsState.h`: bộ đếm, thời gian quan sát và serializer JSON dùng bộ nhớ cố định.
- `DeviceMetrics.h`: đọc trạng thái đã có và gửi telemetry ở cuối `loop()`.
- Không đọc GPIO thêm; sử dụng chính 6 giá trị IR mà chương trình đã đọc.
- Không đổi buffer, keepalive, socket timeout, Last Will hoặc subscription MQTT.
- Không gọi reconnect, không đổi state trạm và không phát lệnh servo từ module metrics.

Payload dùng API `beginPublish` / `write` / `endPublish` của
[PubSubClient](https://pubsubclient.knolleary.net/api.html), tránh đổi giới hạn buffer
nhận lệnh hiện tại. Telemetry không retain và không có ACK ứng dụng.
Đây vẫn là gửi dữ liệu mạng đồng bộ, có chi phí CPU/RAM và thời gian gửi; không
cam kết thời gian vòng lặp giống hệt khi chưa bật metrics. Trường
`telemetry_last_publish_duration_ms` cho phép quan sát chi phí lần gửi trước.
Nếu `loop()` bị chặn trong logic gốc hoặc return sớm khi xử lý Serial, mẫu có thể
đến chậm hơn 5 giây; module không thay đổi những hành vi đó.

## Nhóm metrics

| Nhóm | Nội dung |
|---|---|
| ESP32 | Uptime, RSSI, heap hiện tại/thấp nhất, xung CPU MHz, Wi-Fi/MQTT tại lúc lấy mẫu |
| MQTT | Số lần thử kết nối, thành công/thất bại trong hàm reconnect gốc |
| Telemetry | Gửi thành công/thất bại cục bộ, thời gian lần gửi trước |
| Camera Edge | Số callback, màu được nhận biết/không nhận biết, confidence lỗi, tuổi bản tin, confidence và mã màu gần nhất |
| Mỗi trạm RED/BLUE/YELLOW | State, góc servo được yêu cầu, PWM attached, số lần gạt, gạt lại khi chưa thu tay, bin confirmation, timeout, home do Serial `0`, tổng home và thời gian từ gạt đến home |
| 6 IR | Trạng thái bị chắn (LOW=1) và số sườn HIGH → LOW quan sát được |
| Chế độ | `autoTestMode` và `liveMonitorMode` hiện có |

JSON dùng các object con `red`, `blue`, `yellow`, `ir1`…`ir6`; ba trường cơ bản
`uptime_seconds`, `wifi_rssi_dbm`, `free_heap_bytes` ở cấp gốc.

Diễn giải đúng dữ liệu:

- State trạm: `0=IDLE`, `1=ARMED`, `2=SORTING_WAIT_DROP`.
- Mã màu Camera: `0=không nhận biết`, `1=RED`, `2=BLUE/GREEN/XANH`, `3=YELLOW/VANG`.
- Confidence và tuổi bản tin = `-1` khi chưa có dữ liệu tương ứng. Confidence `0`
  được ghi đúng giá trị nhận vào. Việc quan sát confidence không sửa cách parser
  gốc sử dụng confidence để in Serial hay nhận lệnh.
- Camera metrics phản ánh **bản tin đến ESP32**, bao gồm lệnh publish thủ công.
  Không thể suy ra FPS, webcam đã mở hay accuracy từ những bản tin này.
  Băng chuyền không có sản phẩm cũng có thể không phát bản tin.
- `servo_pwm_attached` và góc servo là dữ liệu phần mềm, không phát hiện dây bị
  rút hay đo góc trục thực tế.
- `bin_confirmations_total` tăng khi nhánh IR miệng thùng trong logic gốc được thực
  thi. Đây là tín hiệu xác nhận tại cảm biến thùng; không tự chứng minh màu phân loại
  đúng hay hộp đã nằm hoàn toàn trong thùng.
- `timeouts_total` ghi nhận nhánh timeout an toàn 5 giây; không khẳng định servo
  hỏng. `last_sort_duration_seconds` là khoảng từ lệnh gạt gần nhất đến lệnh home,
  không phải thời gian chuyển động cơ học; `-1` nếu không có lần gạt đang được theo dõi.
- IR edges đếm mẫu mà vòng lặp quan sát được, không phải bộ đếm ngắt phần cứng.
  Trạng thái trước mẫu đầu tiên là HIGH, cùng khởi tạo với logic gốc.
- Các lần gạt trong chế độ test vẫn được đếm. Các lệnh home lúc setup không được
  tính vào counters vận hành. Counters ở RAM, reset khi ESP32 reboot.
- Counters gửi telemetry trong JSON phản ánh kết quả **trước mẫu hiện tại**, vì
  chỉ biết kết quả gửi sau khi đã tạo và gửi payload.

## Nạp và nối với Prometheus/Grafana

1. Mở `esp32_firmware/main/main.ino`; giữ hai header mới trong cùng thư mục `main`
   và giữ `secrets.h` đang dùng. Nếu dùng Wokwi, thêm cả hai tab header mới.
2. Cấu hình exporter theo `mqtt2prometheus.example.yaml`, đổi `mqtt.server` thành
   broker mà exporter truy cập được. Nếu chạy container, `127.0.0.1` là chính
   container đó; có thể dùng `tcp://mosquitto:1883` nếu cùng Docker network phù hợp.
3. Cho Prometheus scrape exporter với chu kỳ khoảng 5 giây; Grafana dùng Prometheus
   làm data source. Các file trong đây là mẫu, chưa được triển khai vào server.
4. Regex trong mẫu tạo label `sensor="esp32_01"`. Nếu có nhiều ESP32, đổi device ID
   trong topic của `DeviceMetrics.h` cho mỗi board.

File YAML ánh xạ đủ 66 trường sang `gauge`/`counter`, dựa trên
[cấu hình mqtt2prometheus](https://github.com/hikhvar/mqtt2prometheus#configuration).
Ví dụ tên metric: `esp32_free_heap_bytes`, `camera_edge_last_confidence`,
`servo_red_sort_starts_total`, `servo_blue_bin_confirmations_total`,
`servo_yellow_timeouts_total`, `esp32_ir6_blocked`.

| Panel | PromQL |
|---|---|
| RAM trống | `esp32_free_heap_bytes{sensor="esp32_01"}` |
| Sóng Wi-Fi | `esp32_wifi_rssi_dbm{sensor="esp32_01"}` |
| State trạm đỏ | `servo_red_state{sensor="esp32_01"}` |
| Góc yêu cầu trạm xanh | `servo_blue_commanded_angle_degrees{sensor="esp32_01"}` |
| Lần gạt đỏ/phút | `rate(servo_red_sort_starts_total{sensor="esp32_01"}[1m]) * 60` |
| Hộp qua IR thùng xanh trong 5 phút | `increase(servo_blue_bin_confirmations_total{sensor="esp32_01"}[5m])` |
| Timeout vàng trong 5 phút | `increase(servo_yellow_timeouts_total{sensor="esp32_01"}[5m])` |
| IR6 bị chắn | `esp32_ir6_blocked{sensor="esp32_01"}` |
| Confidence gần nhất, bỏ mẫu không có | `camera_edge_last_confidence{sensor="esp32_01"} >= 0` |
| Tuổi bản tin Camera | `camera_edge_last_message_age_seconds{sensor="esp32_01"} >= 0` |
| Thời gian gửi telemetry | `esp32_telemetry_last_publish_duration_ms{sensor="esp32_01"}` |

Mất MQTT thì ESP32 không gửi được mẫu có `mqtt_connected=0`; vì thế không dùng
trường này hay `up` của exporter làm trạng thái sống/chết của board. Mẫu cấu hình
đặt cache 30 giây và giữ timestamp mặc định của exporter. Với một board được chọn,
có thể dùng panel freshness:

```promql
((time() - timestamp(esp32_uptime_seconds{sensor="esp32_01"})) < bool 30)
or on() vector(0)
```

`1` nghĩa là còn mẫu trong 30 giây; `0` nghĩa là không có mẫu mới. Với nhiều board,
cần inventory/label riêng để hiển thị từng board mất tín hiệu.

## Kiểm thử

Từ thư mục gốc, chạy:

```powershell
python esp32_firmware/tests/run_metrics_tests.py
```

Cần `g++` (hoặc biến `CXX` trỏ đến compiler) và PyYAML. Kiểm thử gồm:

- Bỏ các khối `METRICS` rồi so với commit gốc `cb0a50f11d3d0752ccfe18ae9e9eb048a75cfe14`:
  toàn bộ nội dung chương trình cũ phải khớp, kể cả điều kiện và câu lệnh điều khiển.
- Bộ đếm 3 trạm độc lập, gạt lại, bin/timeout/emergency, 6 IR và confidence.
- Thời gian 64-bit qua mốc tràn `millis()`, JSON, giới hạn buffer và 66 mapping YAML.
- Adapter dùng phần cứng giả chỉ cho phép đọc servo/Wi-Fi và gửi metrics; không có
  API điều khiển servo hay cấu hình/kết nối lại MQTT. Kiểm tra chu kỳ 5 giây, bỏ qua
  khi offline, ghi nhận lỗi gửi và phục hồi.

Đây là kiểm thử trên máy, không phải compile bằng ESP32 toolchain hay thử trên
board thật. Sau khi nạp, cần kiểm tra Serial, topic telemetry, `/metrics` của exporter
và thời gian vòng lặp thực tế khi mạng chậm.
