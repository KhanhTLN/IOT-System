"""Build the portable Classic JSON dashboard. Only Python's standard library is needed."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "grafana-iot-layer4-devices.json"
DS = {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}
SELECTOR = 'job=~"${job:regex}",instance=~"${instance:regex}",sensor=~"${device:regex}"'
UPTIME = f"esp32_uptime_seconds{{{SELECTOR}}}"
FRESH = f"(max(time() - timestamp({UPTIME})) < 30)"
COLORS = {"red": "#F2495C", "blue": "#5794F2", "yellow": "#FFCB7D", "cyan": "#6ED0E0"}
STATIONS = {"red": "01 · RED", "blue": "02 · BLUE", "yellow": "03 · YELLOW"}


def metric(name):
    return f"{name}{{{SELECTOR}}}"


def current(name, valid=None):
    expression = f"max({metric(name)})"
    if valid:
        expression = f"({expression} {valid})"
    return f"({expression}) and on() {FRESH}"


def delta(name):
    return f"sum(increase({metric(name)}[$__range]))"


def target(ref, expression, legend="", instant=True, table=False):
    return {
        "refId": ref, "datasource": copy.deepcopy(DS), "editorMode": "code",
        "expr": expression, "legendFormat": legend, "instant": instant,
        "range": not instant, "format": "table" if table else "time_series",
        "exemplar": False,
    }


def mapping(values):
    return [{"type": "value", "options": {
        str(number): {"text": text, "color": color, "index": index}
        for index, (number, text, color) in enumerate(values)
    }}]


def thresholds(*steps):
    return {"mode": "absolute", "steps": [
        {"color": color, "value": value} for value, color in steps
    ]}


def override(name, **properties):
    return {"matcher": {"id": "byName", "options": name}, "properties": [
        {"id": key, "value": value} for key, value in properties.items()
    ]}


def panel(identifier, title, kind, x, y, width, height, description, queries):
    return {
        "id": identifier, "title": title, "type": kind,
        "gridPos": {"x": x, "y": y, "w": width, "h": height},
        "description": description, "transparent": False,
        "datasource": copy.deepcopy(DS), "targets": queries,
        "fieldConfig": {"defaults": {
            "color": {"mode": "fixed", "fixedColor": COLORS["cyan"]},
            "mappings": [], "noValue": "Không có dữ liệu",
            "thresholds": thresholds((None, "green")),
        }, "overrides": []},
        "options": {},
    }


def stat(identifier, title, x, description, queries):
    result = panel(identifier, title, "stat", x, 3, 6, 5, description, queries)
    result["options"] = {
        "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
        "orientation": "auto", "textMode": "value_and_name", "colorMode": "value",
        "graphMode": "none", "justifyMode": "auto", "wideLayout": True,
        "text": {"titleSize": 12, "valueSize": 24}, "showPercentChange": False,
    }
    return result


def timeseries(identifier, title, x, y, width, description, queries):
    result = panel(identifier, title, "timeseries", x, y, width, 8, description, queries)
    result["fieldConfig"]["defaults"]["custom"] = {
        "drawStyle": "line", "lineInterpolation": "linear", "lineWidth": 2,
        "fillOpacity": 8, "gradientMode": "opacity", "showPoints": "never",
        "pointSize": 4, "spanNulls": False, "insertNulls": False,
        "axisPlacement": "auto", "axisLabel": "", "axisColorMode": "text",
        "axisBorderShow": False, "scaleDistribution": {"type": "linear"},
        "stacking": {"mode": "none", "group": "A"},
        "hideFrom": {"tooltip": False, "viz": False, "legend": False},
        "thresholdsStyle": {"mode": "off"},
    }
    result["options"] = {
        "tooltip": {"mode": "multi", "sort": "desc"},
        "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True,
                   "calcs": []},
    }
    return result


def build():
    panels = [{
        "id": 1, "title": "", "type": "text", "transparent": True,
        "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3},
        "options": {"mode": "markdown", "content": (
            "## IOT / DEVICE OPERATIONS\n"
            "**LAYER 4 OBSERVABILITY** &nbsp; · &nbsp; ESP32 / **${device}** &nbsp; · &nbsp; "
            "3 trạm servo &nbsp; · &nbsp; Camera Edge\n\n"
            "Sensing → MQTT → Cloud monitoring &nbsp; | &nbsp; "
            "Dữ liệu thiết bị được lấy mẫu mỗi 5 giây; không có mẫu mới sau 30 giây sẽ hiện STALE."
        )},
    }]

    health = stat(2, "01 / EDGE · Liên kết & chế độ", 0,
        "FRESH: telemetry không quá 30 giây. STALE: không có mẫu mới; chưa xác định lỗi ở board, "
        "mạng, MQTT hay exporter. SCRAPE là up của exporter, không phải up của ESP32. "
        "TEST/CAMERA là chế độ chạy hiện tại; TEST cũng tạo counters vận hành.", [
            target("A", f"((max(time() - timestamp({UPTIME})) < bool 30)) or on() vector(0)", "TELEMETRY"),
            target("B", 'min(up{job=~"${job:regex}",instance=~"${instance:regex}"})', "SCRAPE"),
            target("C", current("esp32_auto_test_mode"), "MODE"),
        ])
    health["fieldConfig"]["overrides"] = [
        override("TELEMETRY", mappings=mapping([(0, "STALE", "#F2495C"), (1, "FRESH", "#73BF69")])),
        override("SCRAPE", mappings=mapping([(0, "DOWN", "#F2495C"), (1, "UP", "#73BF69")])),
        override("MODE", mappings=mapping([(0, "CAMERA", COLORS["cyan"]), (1, "TEST", COLORS["yellow"])])),
    ]
    panels.append(health)

    system = stat(3, "ESP32 · Uptime & Wi-Fi", 6,
        "Uptime tính từ boot, RSSI tại lúc gửi. Không suy ra CPU utilization hay độ trễ mạng. "
        "Màu RSSI là ngưỡng vận hành tham khảo: dưới -80 dBm đỏ, -80…-67 vàng, từ -67 xanh.", [
            target("A", current("esp32_uptime_seconds"), "UPTIME"),
            target("B", current("esp32_wifi_rssi_dbm"), "WI-FI RSSI"),
        ])
    system["fieldConfig"]["overrides"] = [
        override("UPTIME", unit="dtdurations", decimals=0),
        override("WI-FI RSSI", unit="dBm", decimals=0,
                 color={"mode": "thresholds"},
                 thresholds=thresholds((None, "red"), (-80, "orange"), (-67, "green"))),
    ]
    panels.append(system)

    memory = stat(4, "ESP32 · Bộ nhớ", 12,
        "Heap hiện tại và mức thấp nhất kể từ boot, không phải RAM tổng. Cả hai giá trị cùng đơn vị byte; "
        "khoảng trống dữ liệu không được thay bằng 0. Ngưỡng heap tham khảo 20/50 kB, cần chỉnh theo board.", [
            target("A", current("esp32_free_heap_bytes"), "HEAP TRỐNG"),
            target("B", current("esp32_min_free_heap_bytes"), "THẤP NHẤT / BOOT"),
        ])
    memory["fieldConfig"]["defaults"].update({"unit": "bytes", "decimals": 1})
    memory["fieldConfig"]["overrides"] = [override("HEAP TRỐNG", color={"mode": "thresholds"},
        thresholds=thresholds((None, "red"), (20000, "orange"), (50000, "green")))]
    panels.append(memory)

    confidence = f"({current('camera_edge_last_confidence', '>= 0')}) and on() " \
                 f"(max({metric('camera_edge_last_message_age_seconds')}) <= 30)"
    camera = stat(5, "03 / CAMERA EDGE · Bản tin gần nhất", 18,
        "Confidence do Edge gửi, không phải accuracy. Ẩn confidence khi không có giá trị hợp lệ hoặc "
        "bản tin đã quá 30 giây. Tuổi bản tin dài có thể do không có sản phẩm. Màu là nhãn parser gốc nhận biết.", [
            target("A", confidence, "CONFIDENCE"),
            target("B", current("camera_edge_last_message_age_seconds", ">= 0"), "TUỔI BẢN TIN"),
            target("C", current("camera_edge_last_color_code"), "NHÃN GẦN NHẤT"),
        ])
    camera["options"]["text"]["valueSize"] = 22
    camera["fieldConfig"]["overrides"] = [
        override("CONFIDENCE", unit="percentunit", decimals=1, min=0, max=1, noValue="Chưa có mẫu mới"),
        override("TUỔI BẢN TIN", unit="s", decimals=0),
        override("NHÃN GẦN NHẤT", mappings=mapping([
            (0, "UNKNOWN", "#8E8E8E"), (1, "RED", COLORS["red"]),
            (2, "BLUE", COLORS["blue"]), (3, "YELLOW", COLORS["yellow"])])),
    ]
    panels.append(camera)

    flow_queries = [target("A", f"(sum(rate({metric('camera_edge_messages_total')}[$__rate_interval])) * 60) and on() {FRESH}",
                           "Camera Edge · bản tin/phút", False)]
    for index, station in enumerate(STATIONS, 1):
        flow_queries.append(target(chr(65 + index),
            f"(sum(rate({metric('servo_' + station + '_bin_confirmations_total')}[$__rate_interval])) * 60) and on() {FRESH}",
            f"{station.upper()} · IR thùng/phút", False))
    flow = timeseries(6, "Luồng xử lý · Camera Edge → IR miệng thùng", 0, 8, 14,
        "Đối chiếu tốc độ bản tin nhận và nhánh IR thùng thực thi. Hai tín hiệu có thể lệch thời gian; "
        "không dùng tỷ lệ của chúng làm accuracy/OEE. rate xử lý counter reset; cần ít nhất hai mẫu. "
        "Khoảng trống là thiếu mẫu, không được tự điền thành 0.", flow_queries)
    flow["fieldConfig"]["defaults"].update({"unit": "suffix: /min", "min": 0, "decimals": 1})
    flow["fieldConfig"]["overrides"] = [
        override(f"{station.upper()} · IR thùng/phút", color={"mode": "fixed", "fixedColor": color})
        for station, color in COLORS.items() if station in STATIONS
    ]
    panels.append(flow)

    timeline = panel(7, "02 / SERVO · Trạng thái 3 trạm", "state-timeline", 14, 8, 10, 8,
        "State phần mềm: IDLE → ARMED → WAIT DROP. Lấy mẫu 5 giây có thể bỏ qua chuyển trạng thái ngắn. "
        "Không có mẫu mới thì để khoảng trống, không kéo dài trạng thái tốt qua lúc mất telemetry.", [
            target(chr(65 + i), current(f"servo_{station}_state"), label, False)
            for i, (station, label) in enumerate(STATIONS.items())
        ])
    timeline["fieldConfig"]["defaults"].update({
        "mappings": mapping([(0, "IDLE", "#506171"), (1, "ARMED", COLORS["blue"]),
                             (2, "WAIT DROP", COLORS["yellow"])]),
        "custom": {"lineWidth": 0, "fillOpacity": 95, "spanNulls": False,
                   "hideFrom": {"legend": False, "tooltip": False, "viz": False}},
    })
    timeline["options"] = {
        "mergeValues": True, "showValue": "auto", "alignValue": "left", "rowHeight": 0.65,
        "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
        "tooltip": {"mode": "single", "sort": "none"},
    }
    panels.append(timeline)

    columns = [
        ("state", "Trạng thái", False),
        ("commanded_angle_degrees", "Góc lệnh", False),
        ("pwm_attached", "PWM", False),
        ("bin_confirmations_total", "IR thùng / Δ", True),
        ("timeouts_total", "Timeout / Δ", True),
        ("sort_retriggers_total", "Gạt lại / Δ", True),
        ("last_sort_duration_seconds", "Gạt → home", False),
    ]
    cells = []
    for station, label in STATIONS.items():
        for suffix, column, counter in columns:
            name = f"servo_{station}_{suffix}"
            value = delta(name) if counter else current(name, ">= 0" if suffix == "last_sort_duration_seconds" else None)
            cells.append(f'label_replace(label_replace(({value}), "station", "{label}", "", ""), '
                         f'"metric", "{column}", "", "")')
    table = panel(8, "Servo · Sổ vận hành 3 trạm", "table", 0, 16, 16, 7,
        "State/góc/PWM là mẫu mới nhất ≤30s; cột Δ là increase trong khoảng thời gian đang chọn. "
        "Increase là ước lượng Prometheus có extrapolation và xử lý reset, được làm tròn khi hiển thị. "
        "PWM không chứng minh dây servo đã cắm; góc là lệnh, không đo từ trục. Gạt → home là thời gian quan sát, "
        "không phải tốc độ quay vật lý. Ô thiếu dữ liệu hiển thị —.",
        [target("A", " or ".join(cells), instant=True, table=True)])
    table["transformations"] = [
        {"id": "groupingToMatrix", "options": {
            "columnField": "metric", "rowField": "station", "valueField": "Value", "emptyValue": "null"}},
        {"id": "organize", "options": {
            "excludeByName": {},
            "indexByName": {"station\\metric": 0, **{column: i + 1 for i, (_, column, _) in enumerate(columns)}},
            "renameByName": {"station\\metric": "Trạm"}}},
        {"id": "sortBy", "options": {"fields": {}, "sort": [{"field": "Trạm", "desc": False}]}},
    ]
    table["options"] = {"showHeader": True, "cellHeight": "lg", "footer": {"show": False}}
    table["fieldConfig"]["defaults"].update({"noValue": "—", "decimals": 0,
        "custom": {"align": "center", "cellOptions": {"type": "auto"}, "inspect": False,
                   "filterable": False}})
    table["fieldConfig"]["overrides"] = [
        override("Trạm", **{"custom.width": 125, "custom.align": "left"}),
        override("Trạng thái", mappings=mapping([(0, "IDLE", "#8E9BA8"),
            (1, "ARMED", COLORS["blue"]), (2, "WAIT DROP", COLORS["yellow"])]),
            **{"custom.cellOptions": {"type": "color-text"}, "custom.width": 115}),
        override("Góc lệnh", unit="degree", **{"custom.width": 90}),
        override("PWM", mappings=mapping([(0, "OFF", COLORS["red"]), (1, "ON", "#73BF69")]),
                 **{"custom.cellOptions": {"type": "color-text"}, "custom.width": 70}),
        override("Gạt → home", unit="s", decimals=2),
        *[override(column, color={"mode": "thresholds"},
                   thresholds=thresholds((None, "green"), (1, "orange")),
                   **{"custom.cellOptions": {"type": "color-text"}})
          for column in ("Timeout / Δ", "Gạt lại / Δ")],
    ]
    panels.append(table)

    ir_names = ["IR1 · RED / Đón", "IR2 · RED / Thùng", "IR3 · BLUE / Đón",
                "IR4 · BLUE / Thùng", "IR5 · YELLOW / Đón", "IR6 · YELLOW / Thùng"]
    infrared = panel(9, "Cảm biến IR · 6 điểm quan sát", "stat", 16, 16, 8, 7,
        "LOW = CHẮN, HIGH = THÔNG. Đây là giá trị lấy mẫu, không phải chẩn đoán sensor lỗi. "
        "Một xung ngắn hơn 5 giây có thể không hiện trên panel; counters IR vẫn ghi nhận theo vòng lặp firmware.", [
            target(chr(65 + i), current(f"esp32_ir{i + 1}_blocked"), name)
            for i, name in enumerate(ir_names)
        ])
    infrared["options"] = {
        "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
        "orientation": "horizontal", "textMode": "value_and_name", "colorMode": "value",
        "graphMode": "none", "justifyMode": "auto", "wideLayout": True,
        "text": {"titleSize": 11, "valueSize": 18},
    }
    infrared["fieldConfig"]["defaults"]["mappings"] = mapping([
        (0, "THÔNG", "#8E9BA8"), (1, "CHẮN", COLORS["yellow"])])
    panels.append(infrared)

    camera_chart = timeseries(10, "Camera Edge · Confidence bản tin nhận được", 0, 23, 14,
        "Giá trị confidence 0..1 do Edge gửi, bao gồm lệnh test publish thủ công. Không đo FPS/accuracy "
        "hay trạng thái webcam. Giá trị -1 bị loại, 0 được giữ; chỉ hiển thị bản tin ≤30s và telemetry còn mới. "
        "Khoảng trống cũng có thể là không có sản phẩm; không kết luận camera offline.",
        [target("A", confidence, "Confidence nhận được", False)])
    camera_chart["fieldConfig"]["defaults"].update({
        "unit": "percentunit", "min": 0, "max": 1, "decimals": 1})
    camera_chart["fieldConfig"]["defaults"]["custom"].update({"lineInterpolation": "stepAfter", "fillOpacity": 15})
    panels.append(camera_chart)

    alarms = panel(11, "Sự kiện cần xem xét · Khoảng thời gian chọn", "stat", 14, 23, 10, 8,
        "Số sự kiện ước lượng bằng increase trong toàn khoảng chọn, gồm dữ liệu lịch sử cả khi thiết bị "
        "hiện mất telemetry. Không điền 0 khi thiếu series. Giá trị cần ít nhất hai mẫu. "
        "Home khẩn là lệnh Serial 0 đã được thực thi, không tự kết luận lỗi cơ khí. "
        "Mỗi lần Serial 0 phát home cho cả 3 trạm nên tổng home khẩn tăng 3.", [
            target("A", delta("esp32_mqtt_connect_failures_total"), "MQTT · Kết nối lỗi"),
            target("B", delta("esp32_telemetry_publish_failures_total"), "Telemetry · Gửi lỗi"),
            target("C", delta("camera_edge_unrecognized_colors_total"), "Edge · Nhãn không nhận biết"),
            target("D", delta("camera_edge_invalid_confidence_total"), "Edge · Confidence không hợp lệ"),
            target("E", " + ".join(delta(f"servo_{station}_emergency_home_commands_total")
                                     for station in STATIONS), "Servo · Lệnh home khẩn / trạm"),
        ])
    alarms["options"] = copy.deepcopy(infrared["options"])
    alarms["options"]["text"] = {"titleSize": 12, "valueSize": 24}
    alarms["fieldConfig"]["defaults"].update({"decimals": 0, "noValue": "Thiếu mẫu",
        "color": {"mode": "thresholds"},
        "thresholds": thresholds((None, "green"), (1, "orange"))})
    panels.append(alarms)

    def variable(name, label, query, description):
        return {"name": name, "label": label, "description": description, "type": "query",
                "datasource": copy.deepcopy(DS), "definition": query,
                "query": {"query": query, "refId": f"VariableQuery_{name}"},
                "refresh": 2, "sort": 1, "multi": False, "includeAll": False,
                "hide": 0, "options": [], "current": {"text": "", "value": ""},
                "skipUrlSync": False, "regex": ""}

    return {
        "__inputs": [{"name": "DS_PROMETHEUS", "label": "Prometheus", "type": "datasource",
                      "description": "Nguồn Prometheus đang scrape mqtt2prometheus.",
                      "pluginId": "prometheus", "pluginName": "Prometheus"}],
        "__requires": [
            {"type": "grafana", "id": "grafana", "name": "Grafana", "version": "10.4.0"},
            {"type": "datasource", "id": "prometheus", "name": "Prometheus", "version": "1.0.0"},
            *[{"type": "panel", "id": name, "name": name, "version": ""}
              for name in ("text", "stat", "timeseries", "state-timeline", "table")],
        ],
        "id": None, "uid": "iot-l4-device-ops", "title": "IoT / Device Operations · Layer 4",
        "description": "Device observability cho ESP32, 3 trạm servo + 6 IR và luồng Camera Edge. "
                       "Dựa trên 66 metrics firmware; không tuyên bố chứng nhận kiến trúc hay độ chính xác AI.",
        "tags": ["iot", "layer4", "esp32", "servo", "camera-edge", "mqtt", "operations"],
        "timezone": "Asia/Bangkok", "style": "dark", "editable": True, "graphTooltip": 1,
        "schemaVersion": 39, "version": 1, "refresh": "5s", "liveNow": False,
        "fiscalYearStartMonth": 0, "weekStart": "monday", "links": [],
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {"refresh_intervals": ["5s", "10s", "30s", "1m", "5m"],
                       "time_options": [5, 15, 30, 60, 180, 360, 720, 1440]},
        "annotations": {"list": [{"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
            "enable": True, "hide": True, "iconColor": COLORS["cyan"],
            "name": "Annotations & Alerts", "type": "dashboard"}]},
        "templating": {"list": [
            variable("job", "Collector job", "label_values(esp32_uptime_seconds, job)",
                     "Chọn job đang scrape exporter telemetry."),
            variable("instance", "Exporter", 'label_values(esp32_uptime_seconds{job=~"${job:regex}"}, instance)',
                     "Chọn đúng exporter để không gộp các bản sao dữ liệu."),
            variable("device", "ESP32", 'label_values(esp32_uptime_seconds{job=~"${job:regex}",instance=~"${instance:regex}"}, sensor)',
                     "Chọn một board; RED/BLUE/YELLOW là 3 trạm trên board này."),
        ]},
        "panels": panels,
    }


if __name__ == "__main__":
    dashboard = build()
    OUTPUT.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {OUTPUT.name}: {len(dashboard['panels']) - 1} data panels + 1 header")
