#!/usr/bin/env python3
# apps/app_gui.py
# -*- coding: utf-8 -*-

"""
Carbon Footprint GUI with map visualization.
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import tkintermapview

if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS).resolve()  # type: ignore[attr-defined]
else:
    ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.core.env_loader import load_repo_env

load_repo_env(ROOT / ".env")

from modules.fuel.truck_specs import list_truck_keys
from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal import build_path_geometry, evaluate_path
from modules.plot.cabotage_plot_helper import get_visual_sea_path

_log = get_logger("gui")


class ComparisonApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("EcoFreight Calculator (Thesis Project)")
        self.geometry("1200x800")

        init_logging(level="INFO", write_to_file=True)

        self.map_widget: tkintermapview.TkinterMapView | None = None
        self.txt_output: tk.Text
        self.btn_run: ttk.Button

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_pane.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_pane, padding="10")
        main_pane.add(left_frame, width=400)

        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame)

        ttk.Label(left_frame, text="Logistics Analysis", font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))

        in_group = ttk.LabelFrame(left_frame, text="Shipment Details", padding="10")
        in_group.pack(fill=tk.X, pady=5)

        self._add_input(in_group, 0, "Origin:", "ent_origin", "Pelotas, RS")
        self._add_input(in_group, 1, "Destiny:", "ent_destiny", "Manaus, AM")
        self._add_input(in_group, 2, "Cargo (t):", "ent_cargo", "30.0")

        ttk.Label(in_group, text="Truck Type:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.cb_truck = ttk.Combobox(in_group, values=sorted(list_truck_keys()), state="readonly")
        self.cb_truck.set("auto_by_weight")
        self.cb_truck.grid(row=3, column=1, sticky=tk.EW, padx=5)
        in_group.columnconfigure(1, weight=1)

        self.btn_run = ttk.Button(left_frame, text="Calculate Route", command=self._on_run)
        self.btn_run.pack(fill=tk.X, pady=10)

        res_group = ttk.LabelFrame(left_frame, text="Results", padding="5")
        res_group.pack(fill=tk.BOTH, expand=True)

        self.txt_output = tk.Text(res_group, height=15, state=tk.DISABLED, font=("Consolas", 9))
        self.txt_output.pack(fill=tk.BOTH, expand=True)

        self.map_widget = tkintermapview.TkinterMapView(right_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_position(-14.2350, -51.9253)
        self.map_widget.set_zoom(4)

    def _add_input(self, parent: ttk.Frame, row: int, label: str, var_name: str, default: str) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=5)
        ent = ttk.Entry(parent)
        ent.insert(0, default)
        ent.grid(row=row, column=1, sticky=tk.EW, padx=5)
        setattr(self, var_name, ent)

    def _log_ui(self, msg: str, clear: bool = False) -> None:
        self.txt_output.config(state=tk.NORMAL)
        if clear:
            self.txt_output.delete(1.0, tk.END)
        self.txt_output.insert(tk.END, msg + "\n")
        self.txt_output.see(tk.END)
        self.txt_output.config(state=tk.DISABLED)

    def _log_ui_async(self, msg: str, clear: bool = False) -> None:
        self.after(0, lambda: self._log_ui(msg, clear=clear))

    def _on_run(self) -> None:
        origin = self.ent_origin.get().strip()
        destiny = self.ent_destiny.get().strip()
        truck = self.cb_truck.get()

        try:
            cargo = float(self.ent_cargo.get())
        except ValueError:
            messagebox.showerror("Error", "Cargo must be a number.")
            return

        self.btn_run.config(state=tk.DISABLED)
        self._log_ui("--- Starting Analysis ---", clear=True)

        if self.map_widget is not None:
            self.map_widget.delete_all_marker()
            self.map_widget.delete_all_path()

        worker = threading.Thread(target=self._process, args=(origin, destiny, cargo, truck), daemon=True)
        worker.start()

    def _process(self, origin: str, destiny: str, cargo: float, truck: str) -> None:
        try:
            self._log_ui_async(f"Routing: {origin} -> {destiny} ...")

            geo = build_path_geometry(origin, destiny, ors_profile="driving-hgv", overwrite_road=False)
            if not geo or geo.get("status") != "ok":
                self._log_ui_async("Routing failed. Check addresses/API key.")
                return

            self.after(0, lambda: self._update_map(geo))

            self._log_ui_async("Calculating costs ...")
            res = evaluate_path(geo, cargo_t=cargo, truck_key=truck)
            self.after(0, lambda: self._show_report(res))

        except Exception as e:
            _log.exception("Process failed")
            self._log_ui_async(f"Error: {e}")
        finally:
            self.after(0, lambda: self.btn_run.config(state=tk.NORMAL))

    def _update_map(self, geo: dict) -> None:
        if self.map_widget is None:
            return

        def _loc(pt: dict) -> tuple[float, float]:
            return float(pt["lat"]), float(pt["lon"])

        origin_coords = _loc(geo["origin"])
        dest_coords = _loc(geo["destiny"])

        po = geo["port_origin"]
        pd = geo["port_destiny"]

        po_coords = _loc(po["gate"]) if po.get("gate") else _loc(po)
        pd_coords = _loc(pd["gate"]) if pd.get("gate") else _loc(pd)

        self.map_widget.set_marker(po_coords[0], po_coords[1], text=f"Port: {po['name']}", marker_color_circle="blue")
        self.map_widget.set_marker(pd_coords[0], pd_coords[1], text=f"Port: {pd['name']}", marker_color_circle="blue")

        self.map_widget.set_marker(origin_coords[0], origin_coords[1], text=geo["origin"]["label"])
        self.map_widget.set_marker(dest_coords[0], dest_coords[1], text=geo["destiny"]["label"])

        if origin_coords != po_coords:
            self.map_widget.set_path([origin_coords, po_coords], color="#A020F0", width=5)

        try:
            sea_path = get_visual_sea_path(po_coords, pd_coords)
        except Exception as e:
            _log.error("Failed to render curved sea path: %s", e)
            sea_path = [po_coords, pd_coords]

        if len(sea_path) > 1:
            self.map_widget.set_path(sea_path, color="#0000FF", width=4)

        if pd_coords != dest_coords:
            self.map_widget.set_path([pd_coords, dest_coords], color="#A020F0", width=5)

        self.map_widget.set_path([origin_coords, dest_coords], color="#FF0000", width=2)

        all_points = [origin_coords, dest_coords] + sea_path
        all_lats = [p[0] for p in all_points]
        all_lons = [p[1] for p in all_points]

        min_lat, max_lat = min(all_lats), max(all_lats)
        min_lon, max_lon = min(all_lons), max(all_lons)

        pad = 2.0
        try:
            self.map_widget.fit_bounding_box((max_lat + pad, min_lon - pad), (min_lat - pad, max_lon + pad))
        except Exception:
            pass

    def _show_report(self, res: dict) -> None:
        road = res["road_only"]
        mm = res["multimodal"]
        comp = res["comparison"]

        lines = [
            "COMPARISON RESULT",
            "-" * 35,
            "ROAD ONLY (red)",
            f"  Dist: {road['distance_km']:.0f} km",
            f"  Cost: R$ {road['cost']:,.2f}",
            f"  CO2e: {road['co2e']:.0f} kg",
            "-" * 35,
            "MULTIMODAL (purple + blue)",
            f"  Sea:  {mm['sea']['distance_km']:.0f} km",
            f"  Road: {mm['first_mile']['distance_km'] + mm['last_mile']['distance_km']:.0f} km",
            f"  Cost: R$ {mm['total_cost']:,.2f}",
            f"  CO2e: {mm['total_co2e']:.0f} kg",
            "=" * 35,
        ]

        savings = float(comp.get("savings_pct") or 0.0)
        status = "BETTER" if savings > 0 else "WORSE"
        lines.append(f"{status}: {savings:.1f}%")
        lines.append(f"   R$ {-1 * float(comp['delta_cost']):,.2f}")

        self._log_ui("\n".join(lines))


if __name__ == "__main__":
    app = ComparisonApp()
    app.mainloop()
