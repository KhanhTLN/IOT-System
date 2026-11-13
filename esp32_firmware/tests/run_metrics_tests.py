"""Host tests, including a regression check that all original main.ino code is unchanged.

Run from repo root: python esp32_firmware/tests/run_metrics_tests.py
Requires g++ (or CXX) and PyYAML. No board or MQTT connection is used.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "cb0a50f11d3d0752ccfe18ae9e9eb048a75cfe14"


def check_original_logic():
    original = subprocess.run(
        ["git", "show", f"{BASELINE}:esp32_firmware/main/main.ino"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout.decode("utf-8").replace("\r\n", "\n")
    current = (ROOT / "main" / "main.ino").read_text(encoding="utf-8")
    stripped, count = re.subn(
        r"^[ \t]*// METRICS_BEGIN[^\n]*\n.*?^[ \t]*// METRICS_END[^\n]*\n",
        "", current, flags=re.MULTILINE | re.DOTALL,
    )
    assert count == 18, f"Unexpected number of metrics hook blocks: {count}"
    assert stripped == original, "Original device logic changed outside the metrics blocks"
    adapter = (ROOT / "main" / "DeviceMetrics.h").read_text(encoding="utf-8")
    for forbidden in (".connect(", ".disconnect(", ".subscribe(", ".setBufferSize(",
                      ".setKeepAlive(", ".setSocketTimeout(", "digitalRead(", "digitalWrite("):
        assert forbidden not in adapter, f"Unexpected control/config call: {forbidden}"
    print("PASS: original main.ino is unchanged after removing the 18 added metrics blocks")


def flatten(value, prefix=""):
    result = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result


def main():
    check_original_logic()
    with tempfile.TemporaryDirectory(prefix="esp32-metrics-") as temporary:
        executable = Path(temporary) / ("metrics_test.exe" if os.name == "nt" else "metrics_test")
        subprocess.run(
            [os.getenv("CXX", "g++"), "-std=c++11", "-Wall", "-Wextra", "-Werror",
             str(ROOT / "tests" / "metrics_test.cpp"), "-o", str(executable)], check=True,
        )
        result = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
        adapter_executable = Path(temporary) / ("adapter_test.exe" if os.name == "nt" else "adapter_test")
        subprocess.run(
            [os.getenv("CXX", "g++"), "-std=c++11", "-Wall", "-Wextra", "-Werror",
             "-I", str(ROOT / "tests" / "fakes"),
             str(ROOT / "tests" / "metrics_adapter_test.cpp"), "-o", str(adapter_executable)],
            check=True,
        )
        adapter_result = subprocess.run(
            [str(adapter_executable)], capture_output=True, text=True, check=True,
        )
    first_adapter, recovered_adapter = [json.loads(line) for line in adapter_result.stdout.splitlines()]
    assert first_adapter["red"]["servo_commanded_angle_degrees"] == 45
    assert first_adapter["blue"]["state"] == 1
    assert first_adapter["blue"]["servo_pwm_attached"] == 0
    assert first_adapter["ir1"]["blocked"] == 1 and first_adapter["ir2"]["blocked"] == 0
    assert first_adapter["auto_test_mode"] == 1 and first_adapter["live_monitor_mode"] == 0
    assert recovered_adapter["telemetry_publish_success_total"] == 1
    assert recovered_adapter["telemetry_publish_failures_total"] == 1
    samples = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(samples) == 4
    initial, observed, rollover, largest = samples
    assert initial["camera_last_message_age_seconds"] == -1
    assert initial["camera_last_confidence"] == -1
    assert observed["red"]["timeouts_total"] == 1
    assert observed["blue"]["bin_confirmations_total"] == 2
    assert observed["yellow"]["emergency_home_commands_total"] == 2
    assert observed["camera_invalid_confidence_total"] == 3
    assert observed["ir6"]["falling_edges_total"] == 2
    assert rollover["camera_last_message_age_seconds"] == 3
    assert rollover["uptime_seconds"] == ((1 << 32) + 2000) // 1000
    assert largest["blue"]["sort_starts_total"] == (1 << 64) - 1
    config = yaml.safe_load((ROOT / "monitoring" / "mqtt2prometheus.example.yaml").read_text())
    mappings = config["metrics"]
    flat = flatten(initial)
    assert {item["mqtt_name"] for item in mappings} == set(flat)
    assert len({item["prom_name"] for item in mappings}) == len(mappings)
    for item in mappings:
        assert item["type"] == ("counter" if item["mqtt_name"].endswith("_total") else "gauge")
    assert all(isinstance(value, (int, float)) for value in flatten(largest).values())
    print("PASS: independent station counters, IR edges, timeout/bin/emergency, camera confidence")
    print("PASS: 64-bit time, bounded JSON, streaming MQTT success/failures")
    print("PASS: adapter schedule, offline skip, snapshots, send failure and recovery with read-only fakes")
    print(f"PASS: {len(flat)} metrics match the exporter mapping")
    print(f"Largest tested payload: {max(len(line) for line in result.stdout.splitlines())} bytes")


if __name__ == "__main__":
    main()
