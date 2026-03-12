#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from modules.infra.log_manager import init_logging
from modules.multimodal.bulk import run_bulk_evaluation


class _FakeORS:
    def __init__(self, *, route_delay_s: float) -> None:
        self.route_delay_s = route_delay_s
        self._metrics = {
            "fake": {
                "route_road": {
                    "attempts": 0.0,
                    "successes": 0.0,
                    "failures": 0.0,
                    "duration_s": 0.0,
                }
            }
        }

    def route_road(self, origin, destiny, profile: str | None = None):
        started = time.perf_counter()
        time.sleep(self.route_delay_s)
        self._metrics["fake"]["route_road"]["attempts"] += 1.0
        self._metrics["fake"]["route_road"]["successes"] += 1.0
        self._metrics["fake"]["route_road"]["duration_s"] += time.perf_counter() - started
        return {
            "distance_m": 100000.0,
            "duration_s": 7200.0,
            "profile_used": str(profile or "driving-hgv"),
            "source": "fake",
            "provider": "fake",
        }

    def reset_metrics(self) -> None:
        self._metrics["fake"]["route_road"] = {
            "attempts": 0.0,
            "successes": 0.0,
            "failures": 0.0,
            "duration_s": 0.0,
        }

    def metrics_snapshot(self):
        return {"fake": {"route_road": dict(self._metrics["fake"]["route_road"])}}


class _FakeSeaMatrix:
    def km_with_source(self, _origin, _destiny):
        return 1500.0, "benchmark"


def _fake_resolve_point(delay_s: float):
    def _resolver(value, _ors):
        text = str(value).strip()
        time.sleep(delay_s)
        seed = abs(hash(text)) % 1000
        return {
            "label": text,
            "lat": -30.0 + (seed / 1000.0),
            "lon": -51.0 + (seed / 1000.0),
            "uf": "RS",
        }

    return _resolver


def _fake_prepare_context(**_kwargs):
    return {"benchmark": True}


def _fake_evaluate_and_flatten(geo, *, origin_name: str, destiny_name: str, evaluation_kwargs):
    road_km = float(geo["road_direct"]["distance_km"] or 0.0)
    res = {
        "comparison": {"savings_pct": 12.5},
        "inputs": {
            "cargo_t": evaluation_kwargs["cargo_t"],
            "diesel_price_source": "benchmark",
            "port_ops_scenario_resolved": evaluation_kwargs["port_ops_scenario"],
            "allocation_mode_used": evaluation_kwargs.get("allocation_mode") or "auto",
        },
    }
    flat = {
        "road_distance_km": road_km,
        "road_fuel_liters": road_km / 2.0,
        "road_fuel_kg": road_km / 2.0,
        "road_fuel_cost_r": road_km * 3.0,
        "road_co2e_kg": road_km * 4.0,
        "mm_road_fuel_liters": 10.0,
        "mm_road_fuel_kg": 10.0,
        "mm_road_fuel_cost_r": 10.0,
        "mm_road_co2e_kg": 10.0,
        "sea_km": 1500.0,
        "sea_fuel_kg": 20.0,
        "sea_fuel_cost_r": 30.0,
        "sea_co2e_kg": 40.0,
        "total_fuel_kg": 50.0,
        "total_fuel_cost_r": road_km * 2.0,
        "total_co2e_kg": road_km * 1.5,
        "delta_cost_r": road_km,
        "delta_co2e_kg": road_km * 0.5,
    }
    return res, flat


def _ports():
    return [
        {"name": "Rio Grande", "lat": -32.0, "lon": -52.0},
        {"name": "Santos", "lat": -24.0, "lon": -46.3},
        {"name": "Manaus", "lat": -3.1, "lon": -60.0},
    ]


def _benchmark_once(
    *,
    destination_count: int,
    geocode_delay_s: float,
    route_delay_s: float,
    geocode_workers: int,
    route_workers: int,
    persist_batch_size: int,
) -> dict:
    fake_ors = _FakeORS(route_delay_s=route_delay_s)
    fake_destinations = [f"City {index}, RS" for index in range(destination_count)]
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.sqlite"
        with patch(
            "modules.multimodal.bulk_pipeline.load_routing_assets",
            return_value=(fake_ors, _ports(), _FakeSeaMatrix(), db_path),
        ), patch(
            "modules.multimodal.bulk._resolve_point_without_db",
            side_effect=_fake_resolve_point(geocode_delay_s),
        ), patch(
            "modules.multimodal.bulk_pipeline._resolve_point_without_db",
            side_effect=_fake_resolve_point(geocode_delay_s),
        ), patch(
            "modules.multimodal.bulk.prepare_evaluation_context",
            side_effect=_fake_prepare_context,
        ), patch(
            "modules.multimodal.bulk_pipeline.prepare_evaluation_context",
            side_effect=_fake_prepare_context,
        ), patch(
            "modules.multimodal.bulk._evaluate_and_flatten",
            side_effect=_fake_evaluate_and_flatten,
        ), patch(
            "modules.multimodal.bulk_pipeline._evaluate_and_flatten",
            side_effect=_fake_evaluate_and_flatten,
        ):
            started = time.perf_counter()
            outcome = run_bulk_evaluation(
                origin="Pelotas, RS",
                dest_list=fake_destinations,
                cargo_t=30.0,
                truck_key="semi_27t",
                profile="driving-hgv",
                overwrite_road=False,
                db_path=db_path,
                results_table="bulk_evaluation_results",
                runs_table="bulk_evaluation_runs",
                run_results_table="bulk_evaluation_run_results",
                destination_set_id="benchmark",
                vessel_class="container_small",
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=True,
                port_moves_per_call=None,
                cargo_teu=None,
                t_per_teu_default=14.0,
                allocation_mode=None,
                allocation_load_factor=0.8,
                full_call_mode=False,
                port_ops_scenario="baseline",
                shuffle_destinations=False,
                approximation_fallback=False,
                max_geocode_workers=geocode_workers,
                max_route_workers=route_workers,
                persist_batch_size=persist_batch_size,
            )
            elapsed_s = time.perf_counter() - started
    return {
        "elapsed_s": elapsed_s,
        "outcome": outcome,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic benchmark for staged bulk execution")
    parser.add_argument("--destinations", type=int, default=120)
    parser.add_argument("--geocode-delay-ms", type=float, default=15.0)
    parser.add_argument("--route-delay-ms", type=float, default=35.0)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    init_logging(level=args.log_level)
    geocode_delay_s = max(float(args.geocode_delay_ms), 0.0) / 1000.0
    route_delay_s = max(float(args.route_delay_ms), 0.0) / 1000.0

    serial = _benchmark_once(
        destination_count=int(args.destinations),
        geocode_delay_s=geocode_delay_s,
        route_delay_s=route_delay_s,
        geocode_workers=1,
        route_workers=1,
        persist_batch_size=1,
    )
    optimized = _benchmark_once(
        destination_count=int(args.destinations),
        geocode_delay_s=geocode_delay_s,
        route_delay_s=route_delay_s,
        geocode_workers=4,
        route_workers=8,
        persist_batch_size=64,
    )

    speedup = (
        float(serial["elapsed_s"]) / float(optimized["elapsed_s"])
        if float(optimized["elapsed_s"]) > 0.0
        else 0.0
    )
    print("Bulk benchmark")
    print(f"  destinations: {int(args.destinations)}")
    print(f"  serial_s:     {serial['elapsed_s']:.3f}")
    print(f"  optimized_s:  {optimized['elapsed_s']:.3f}")
    print(f"  speedup_x:    {speedup:.2f}")
    print(f"  serial_perf:  {serial['outcome'].get('performance')}")
    print(f"  optimized_perf: {optimized['outcome'].get('performance')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
