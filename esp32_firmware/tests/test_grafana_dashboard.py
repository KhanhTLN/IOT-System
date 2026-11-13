"""Validate the portable dashboard and optionally execute PromQL tests with promtool.

python esp32_firmware/tests/test_grafana_dashboard.py
python esp32_firmware/tests/test_grafana_dashboard.py --promtool-image prom/prometheus:v3.5.0
The second command uses an isolated --rm Docker container; no running service is changed.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
MONITORING = ROOT / "monitoring"


def load_builder():
    spec = importlib.util.spec_from_file_location("dashboard_builder", MONITORING / "build_grafana_dashboard.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def expand(expression):
    for variable, value in {"${job:regex}": "iot", "${instance:regex}": "collector:9641",
                            "${device:regex}": "esp32_01", "$__rate_interval": "1m",
                            "$__range": "1m"}.items():
        expression = expression.replace(variable, value)
    assert "$" not in expression
    return expression


def validate(dashboard):
    builder = load_builder()
    assert dashboard == builder.build(), "Regenerate JSON after changing the builder"
    panels = dashboard["panels"]
    assert len(panels) == 11 and sum(panel["type"] != "text" for panel in panels) == 10
    assert len({panel["id"] for panel in panels}) == len(panels)
    assert dashboard["__inputs"][0]["pluginId"] == "prometheus"
    assert dashboard["id"] is None
    assert dashboard["refresh"] == "5s"
    assert [variable["name"] for variable in dashboard["templating"]["list"]] == ["job", "instance", "device"]
    for variable in dashboard["templating"]["list"]:
        assert not variable["multi"] and not variable["includeAll"]
        assert variable["datasource"] == builder.DS
    for index, panel in enumerate(panels):
        position = panel["gridPos"]
        assert 0 <= position["x"] and position["x"] + position["w"] <= 24
        assert position["y"] >= 0 and position["w"] > 0 and position["h"] > 0
        for other in panels[index + 1:]:
            right = other["gridPos"]
            assert (position["x"] + position["w"] <= right["x"] or
                    right["x"] + right["w"] <= position["x"] or
                    position["y"] + position["h"] <= right["y"] or
                    right["y"] + right["h"] <= position["y"]), "Overlapping panels"

    catalog = yaml.safe_load((MONITORING / "mqtt2prometheus.example.yaml").read_text())
    known = {item["prom_name"] for item in catalog["metrics"]} | {"up"}
    expressions = []
    for panel in panels:
        if panel["type"] == "text":
            continue
        assert panel["datasource"] == builder.DS
        assert len({target["refId"] for target in panel["targets"]}) == len(panel["targets"])
        for target in panel["targets"]:
            expression = target["expr"]
            expressions.append(expression)
            selectors = re.findall(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^}]+)\}", expand(expression))
            assert selectors
            for name, labels in selectors:
                assert name in known, f"Unmapped metric: {name}"
                assert 'job=~"iot"' in labels and 'instance=~"collector:9641"' in labels
                if name != "up":
                    assert 'sensor=~"esp32_01"' in labels
            for name in re.findall(r"(?:rate|increase)\(([a-zA-Z_:][a-zA-Z0-9_:]*)\{", expression):
                assert name.endswith("_total"), f"Counter function used on gauge: {name}"
            assert target["datasource"] == builder.DS
            expand(expression)
    serialized = json.dumps(dashboard)
    assert "lastNotNull" in serialized and '"spanNulls": false' in serialized
    assert "histogram_quantile" not in serialized and "accuracy" not in {panel["title"].lower() for panel in panels}
    assert sum("vector(0)" in expression for expression in expressions) == 1, "Unexpected missing-data zero fallback"
    matrix = next(panel for panel in panels if panel["id"] == 8)
    assert matrix["targets"][0]["format"] == "table" and matrix["targets"][0]["instant"]
    assert matrix["transformations"][0]["id"] == "groupingToMatrix"
    assert len(re.findall(r'"metric", "[^"]+"', matrix["targets"][0]["expr"])) == 21
    used = set(re.findall(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\{", "\n".join(expressions)))
    print(f"PASS: 10 data panels, non-overlapping layout, portable datasource and 3 selector variables")
    print(f"PASS: {len(expressions)} queries reference {len(used) - 1} mapped firmware metrics plus exporter up")
    print("PASS: fresh-data guards, missing confidence, counter functions, 3-station matrix and all 6 IR")
    return expressions, catalog


def promtool_tests(expressions, catalog, image):
    selector = '{job="iot",instance="collector:9641",sensor="esp32_01"}'
    input_series = []
    for item in catalog["metrics"]:
        name = item["prom_name"]
        values = "0+0x12 _x12 stale"
        if name == "esp32_uptime_seconds":
            values = "0+5x12 _x12 stale"
        elif name == "camera_edge_last_confidence":
            values = "-1+0x6 0+0x5 _x12 stale"
        elif name.endswith("_pwm_attached"):
            values = "1+0x12 _x12 stale"
        elif name == "servo_red_bin_confirmations_total":
            values = "0+1x6 0+1x5 _x12 stale"
        elif name.endswith("_last_sort_duration_seconds"):
            values = "-1+0x12 _x12 stale"
        input_series.append({"series": name + selector, "values": values})
    input_series.append({"series": 'up{job="iot",instance="collector:9641"}', "values": "1+0x40"})
    builder = load_builder()
    health = expressions[0]
    zero_confidence = next(panel for panel in builder.build()["panels"] if panel["id"] == 5)["targets"][0]["expr"]
    state = next(panel for panel in builder.build()["panels"] if panel["id"] == 7)["targets"][0]["expr"]
    table = next(panel for panel in builder.build()["panels"] if panel["id"] == 8)["targets"][0]["expr"]
    value_test = lambda expression, time, value: {
        "expr": expand(expression), "eval_time": time,
        "exp_samples": [] if value is None else [{"labels": "{}", "value": value}],
    }
    tests = {
        "rule_files": [], "evaluation_interval": "5s", "tests": [{
            "name": "Fresh samples, absent/zero confidence, stale device with healthy exporter",
            "interval": "5s", "input_series": input_series,
            "promql_expr_test": [
                value_test(health, "1m", 1),
                value_test(health, "95s", 0),
                value_test(health.replace("${device:regex}", "missing_board"), "1m", 0),
                value_test(zero_confidence, "15s", None),
                value_test(zero_confidence, "1m", 0),
                value_test(zero_confidence, "95s", None),
                value_test(state, "1m", 0),
                value_test(state, "95s", None),
                value_test('min(up{job=~"${job:regex}",instance=~"${instance:regex}"})', "95s", 1),
                value_test('(sum(rate(servo_red_bin_confirmations_total' + selector + '[1m])) > bool 0)', "1m", 1),
                value_test(f"count({table})", "1m", 18),
                value_test(f"count(count by (station) ({table}))", "1m", 3),
                value_test(f"count({table})", "95s", 9),
            ],
        }],
    }
    rules = {"groups": [{"name": "dashboard-syntax", "rules": [
        {"record": f"dashboard_validation:query_{index}", "expr": expand(expression)}
        for index, expression in enumerate(expressions)
    ]}]}
    with tempfile.TemporaryDirectory(prefix="grafana-dashboard-") as temporary:
        directory = Path(temporary)
        (directory / "rules.yaml").write_text(yaml.safe_dump(rules, allow_unicode=True), encoding="utf-8")
        (directory / "tests.yaml").write_text(yaml.safe_dump(tests, allow_unicode=True), encoding="utf-8")
        command = ["docker", "run", "--rm", "--network", "none", "--entrypoint", "/bin/promtool",
                   "--mount", f"type=bind,source={directory},target=/work,readonly", image]
        subprocess.run(command + ["check", "rules", "/work/rules.yaml"], check=True)
        subprocess.run(command + ["test", "rules", "/work/tests.yaml"], check=True)
    print("PASS: real promtool query parsing and 13 freshness/confidence/reset/table behavior assertions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--promtool-image", help="Optional Docker image containing /bin/promtool")
    args = parser.parse_args()
    dashboard = json.loads((MONITORING / "grafana-iot-layer4-devices.json").read_text(encoding="utf-8"))
    expressions, catalog = validate(dashboard)
    if args.promtool_image:
        promtool_tests(expressions, catalog, args.promtool_image)
