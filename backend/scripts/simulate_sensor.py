"""Sensor simulation script to pump time-series readings to S-41 endpoint (N3-60).

Acceptance Criteria:
- Reads scenario files (sequence of timestamps and temperatures).
- Calls S-41 telemetry ingestion endpoint (POST /api/v1/telemetry/readings).
- Bundles at least 5 sample scenarios with known violation answers:
  1. No violation (normal)
  2. 10-minute spike (< 30m, filtered)
  3. 45-minute spike (sustained, 1 violation)
  4. Two excursions 5 minutes apart (merged into 1 violation)
  5. Excursion crossing midnight (1 violation)
- Non-functional requirement: Runs faster than real-time (default speedup=0 for instant execution).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure backend root is in python path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("simulate_sensor")

DEFAULT_SCENARIO_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "cold_chain_scenarios.json"
)


def load_scenarios(scenario_file: Path | str | None = None) -> list[dict[str, Any]]:
    """Load scenario definitions from JSON file."""
    path = Path(scenario_file) if scenario_file else DEFAULT_SCENARIO_PATH
    if not path.is_file():
        # Fallback to tests/data
        alt_path = (
            Path(__file__).resolve().parents[1]
            / "tests"
            / "data"
            / "cold_chain_scenarios.json"
        )
        if alt_path.is_file():
            path = alt_path
        else:
            raise FileNotFoundError(f"Scenario file not found at: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("scenarios", [])


def send_readings_http(
    endpoint: str,
    container_code: str,
    readings: list[dict[str, Any]],
    token: str | None = None,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Send a batch of telemetry readings to S-41 endpoint via HTTP POST."""
    payload = {
        "container_code": container_code,
        "readings": readings,
    }
    encoded_data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        endpoint, data=encoded_data, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8") if exc.fp else str(exc)
        logger.error("HTTP error %s from %s: %s", exc.code, endpoint, err_msg)
        raise RuntimeError(f"HTTP {exc.code}: {err_msg}") from exc
    except Exception as exc:
        logger.error("Connection failed to %s: %s", endpoint, exc)
        raise


def run_scenario_simulation(
    scenario: dict[str, Any],
    endpoint: str | None = None,
    token: str | None = None,
    speedup: float = 0.0,
    http_client_fn: Any | None = None,
) -> dict[str, Any]:
    """Run a single scenario through the simulation.

    Args:
        scenario: Scenario dict containing readings, container_code, expected violations.
        endpoint: Target URL for S-41 endpoint.
        token: Bearer JWT token.
        speedup: Speedup factor (0 = instant burst, >0 = simulated delay between batches).
        http_client_fn: Optional custom client function for in-process test injection.

    Returns:
        Simulation result dict with timing and detected violations.
    """
    scenario_id = scenario["id"]
    container_code = scenario.get("container_code", f"CONT-{scenario_id}")
    readings = scenario["readings"]
    expected = scenario.get("expected", {})
    expected_count = expected.get("violation_count", 0)

    logger.info(
        "Starting simulation: %s (%s) - %d readings, expected violations: %d",
        scenario_id,
        scenario.get("name", ""),
        len(readings),
        expected_count,
    )

    t0 = time.perf_counter()

    # If speedup > 0, simulate realistic delay between measurements
    if speedup > 0 and len(readings) > 1:
        # Send reading by reading with scaled delay
        first_dt = datetime.fromisoformat(
            readings[0]["recorded_at"].replace("Z", "+00:00")
        )
        last_dt = datetime.fromisoformat(
            readings[-1]["recorded_at"].replace("Z", "+00:00")
        )
        span_seconds = (last_dt - first_dt).total_seconds()
        scaled_delay = max(0.001, (span_seconds / len(readings)) / speedup)
        for _ in readings:
            time.sleep(min(scaled_delay, 0.05))

    # Perform ingestion
    if http_client_fn is not None:
        response_data = http_client_fn(
            container_code=container_code,
            readings=readings,
            token=token,
        )
    elif endpoint:
        response_data = send_readings_http(
            endpoint=endpoint,
            container_code=container_code,
            readings=readings,
            token=token,
        )
    else:
        # Offline validation mode using internal detector
        from app.services.cold_chain_detector import detect_temperature_violations

        params = scenario.get("parameters", {})
        raw_violations = detect_temperature_violations(
            readings,
            min_temp_celsius=params.get("min_temp_celsius", 2.0),
            max_temp_celsius=params.get("max_temp_celsius", 8.0),
            delay_minutes=params.get("delay_minutes", 30),
            merge_gap_minutes=params.get("merge_gap_minutes", 5),
        )
        response_data = {
            "container_code": container_code,
            "ingested_count": len(readings),
            "duplicate_count": 0,
            "violations_detected": len(raw_violations),
            "violations": [v.to_dict() for v in raw_violations],
        }

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    detected_count = response_data.get(
        "violations_detected", len(response_data.get("violations", []))
    )

    passed = detected_count == expected_count

    result = {
        "scenario_id": scenario_id,
        "name": scenario.get("name", ""),
        "container_code": container_code,
        "readings_count": len(readings),
        "expected_violations": expected_count,
        "detected_violations": detected_count,
        "violations_detail": response_data.get("violations", []),
        "elapsed_ms": round(elapsed_ms, 2),
        "passed": passed,
    }

    status_str = "PASS" if passed else "FAIL"
    logger.info(
        "Completed: %s in %.2f ms | Detected: %d | Expected: %d | [%s]",
        scenario_id,
        elapsed_ms,
        detected_count,
        expected_count,
        status_str,
    )
    return result


def main() -> int:
    """CLI entrypoint for sensor simulation."""
    parser = argparse.ArgumentParser(
        description="Cold Chain Sensor Simulation Script (N3-60 / S-42)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--file",
        "-f",
        default=str(DEFAULT_SCENARIO_PATH),
        help="Path to scenarios JSON file",
    )
    parser.add_argument(
        "--scenario",
        "-s",
        default="all",
        help="Scenario ID to run ('all' or specific ID like 'scenario_1_normal')",
    )
    parser.add_argument(
        "--endpoint",
        "-e",
        default=None,
        help="S-41 Telemetry Ingestion API endpoint (e.g. http://localhost:8000/api/v1/telemetry/readings)",
    )
    parser.add_argument(
        "--token",
        "-t",
        default=None,
        help="Bearer JWT authentication token",
    )
    parser.add_argument(
        "--speedup",
        type=float,
        default=0.0,
        help="Speedup multiplier (0 = instant burst, 60 = 60x real-time)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify detected violations against expected oracle answers",
    )

    args = parser.parse_args()

    try:
        scenarios = load_scenarios(args.file)
    except Exception as exc:
        logger.error("Failed to load scenarios: %s", exc)
        return 1

    if args.scenario != "all":
        scenarios = [
            s
            for s in scenarios
            if s["id"] == args.scenario
            or str(s.get("name", "")).startswith(args.scenario)
        ]
        if not scenarios:
            logger.error("No scenario matched identifier '%s'", args.scenario)
            return 1

    print("\n" + "=" * 80)
    print(" BỘ GIẢ LẬP CẢM BIẾN NHIỆT ĐỘ CHUỖI LẠNH (N3-60 SPRINT 6 ORACLE TEST)")
    print("=" * 80)
    print(f"Tổng số kịch bản: {len(scenarios)}")
    print(
        f"Chế độ chạy: {'Tức thì (Instant Burst - NFR Passed)' if args.speedup <= 0 else f'{args.speedup}x thời gian thực'}"
    )
    if args.endpoint:
        print(f"Target API Endpoint: {args.endpoint}")
    else:
        print("Target: Internal TDD Validation Engine")
    print("-" * 80)

    results = []
    all_passed = True

    for sc in scenarios:
        res = run_scenario_simulation(
            scenario=sc,
            endpoint=args.endpoint,
            token=args.token,
            speedup=args.speedup,
        )
        results.append(res)
        if not res["passed"]:
            all_passed = False

    print("\n" + "=" * 80)
    print(
        f"{'MÃ KỊCH BẢN':<30} | {'SỐ ĐO':<6} | {'KỲ VỌNG':<8} | {'PHÁT HIỆN':<9} | {'THỜI GIAN':<10} | {'KẾT QUẢ'}"
    )
    print("-" * 80)
    for r in results:
        status_symbol = "✓ PASS" if r["passed"] else "✗ FAIL"
        print(
            f"{r['scenario_id']:<30} | "
            f"{r['readings_count']:<6} | "
            f"{r['expected_violations']:<8} | "
            f"{r['detected_violations']:<9} | "
            f"{r['elapsed_ms']:>7.2f} ms | "
            f"{status_symbol}"
        )
    print("=" * 80)

    if all_passed:
        print(" KẾT QUẢ: 100% KỊCH BẢN ĐẠT ĐÁP ÁN CHUẨN XÁC.")
        return 0
    else:
        print(" KẾT QUẢ: CÓ KỊCH BẢN KHÔNG KHỚP ĐÁP ÁN.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
