#!/usr/bin/env python3
# apps/app_gui.py
# -*- coding: utf-8 -*-

"""
Carbon Footprint GUI with Map.
==============================

A Tkinter interface for the Single Route Comparator.
Features:
  - Inputs for Origin/Destiny/Cargo
  - Interactive Map (OpenStreetMap) visualization
  - Route drawing (Straight line or approximated)
"""

import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# --- Path Bootstrap ---
if getattr(sys, 'frozen', False):
    # If running as a compiled .exe (PyInstaller)
    ROOT = Path(sys._MEIPASS).resolve() # type: ignore
else:
    # If running as a script: carbon-footprint/apps/app_gui.py -> parent -> carbon-footprint/
    ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Imports ---
from modules.infra.log_manager import init_logging, get_logger
from modules.multimodal import build_path_geometry, evaluate_path
from modules.fuel.truck_specs import list_truck_keys

# Import the visual renderer
# We use the new dynamic renderer we just built
from modules.plot.cabotage_plot_helper import get_visual_sea_path

# Map Widget
try:
    import tkintermapview
except ImportError:
    print("Please run: pip install tkintermapview")
    sys.exit(1)

_log = get_logger("gui")

class ComparisonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("EcoFreight Calculator (Thesis Project)")
        self.geometry("1200x800") # Wider for map
        
        # Initialize logs to file
        init_logging(level="INFO", write_to_file=True)
        
        # Config
        self.map_widget = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        # --- Layout: Left Panel (Controls) | Right Panel (Map) ---
        main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel
        left_frame = ttk.Frame(main_pane, padding="10")
        main_pane.add(left_frame, width=400)
        
        # Right Panel (Map container)
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame)
        
        # --- Left Panel Content ---
        ttk.Label(left_frame, text="Logistics Analysis", font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))
        
        # Input Group
        in_group = ttk.LabelFrame(left_frame, text="Shipment Details", padding="10")
        in_group.pack(fill=tk.X, pady=5)
        
        self._add_input(in_group, 0, "Origin:", "ent_origin", "Pelotas, RS")
        self._add_input(in_group, 1, "Destiny:", "ent_destiny", "Manaus, AM")
        self._add_input(in_group, 2, "Cargo (t):", "ent_cargo", "30.0")
        
        # Truck Select
        ttk.Label(in_group, text="Truck Type:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.cb_truck = ttk.Combobox(in_group, values=sorted(list_truck_keys()), state="readonly")
        self.cb_truck.set("auto_by_weight")
        self.cb_truck.grid(row=3, column=1, sticky=tk.EW, padx=5)
        in_group.columnconfigure(1, weight=1)

        # Button
        self.btn_run = ttk.Button(left_frame, text="▶ Calculate Route", command=self._on_run)
        self.btn_run.pack(fill=tk.X, pady=10)
        
        # Results Text
        res_group = ttk.LabelFrame(left_frame, text="Results", padding="5")
        res_group.pack(fill=tk.BOTH, expand=True)
        
        self.txt_output = tk.Text(res_group, height=15, state=tk.DISABLED, font=("Consolas", 9))
        self.txt_output.pack(fill=tk.BOTH, expand=True)
        
        # --- Map Setup ---
        self.map_widget = tkintermapview.TkinterMapView(right_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        
        # Default View: Brazil Centroid
        self.map_widget.set_position(-14.2350, -51.9253) 
        self.map_widget.set_zoom(4)
        
        # Optional: Google Maps Tiles (Comment out if blocked)
        # self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22) 

    def _add_input(self, parent, row, label, var_name, default):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=5)
        ent = ttk.Entry(parent)
        ent.insert(0, default)
        ent.grid(row=row, column=1, sticky=tk.EW, padx=5)
        setattr(self, var_name, ent)

    def _log_ui(self, msg: str, clear=False):
        self.txt_output.config(state=tk.NORMAL)
        if clear:
            self.txt_output.delete(1.0, tk.END)
        self.txt_output.insert(tk.END, msg + "\n")
        self.txt_output.see(tk.END)
        self.txt_output.config(state=tk.DISABLED)

    def _on_run(self):
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
        
        # Clear Map
        self.map_widget.delete_all_marker()
        self.map_widget.delete_all_path()
        
        # Run Thread
        t = threading.Thread(target=self._process, args=(origin, destiny, cargo, truck), daemon=True)
        t.start()

    def _process(self, origin, destiny, cargo, truck):
        try:
            self._log_ui(f"Routing: {origin} -> {destiny}...")
            
            # 1. Build Geometry
            #    Use 'driving-hgv' but assume cache is okay unless testing
            geo = build_path_geometry(origin, destiny, ors_profile="driving-hgv", overwrite_road=False)
            
            if not geo or geo["status"] != "ok":
                self._log_ui("❌ Routing Failed. Check addresses/API key.")
                return

            # Update Map safely on main thread
            self.after(0, lambda: self._update_map(geo))

            # 2. Evaluate
            self._log_ui("Calculating costs...")
            res = evaluate_path(geo, cargo_t=cargo, truck_key=truck)
            
            # 3. Show Results
            self.after(0, lambda: self._show_report(res))
            
        except Exception as e:
            _log.exception("Process failed")
            self.after(0, lambda: self._log_ui(f"Error: {e}"))
        finally:
            self.after(0, lambda: self.btn_run.config(state=tk.NORMAL))

    def _update_map(self, geo):
        """
        Draws markers and path on the map widget.
        """
        # Helper to extract (lat, lon) tuples
        def _loc(pt):
            return float(pt["lat"]), float(pt["lon"])

        # Extract Coordinates
        origin_coords = _loc(geo["origin"])
        dest_coords = _loc(geo["destiny"])
        
        # Multimodal Path: O -> Port -> Port -> D
        po = geo["port_origin"]
        pd = geo["port_destiny"]
        
        # Use gate coords if available, else centroid
        po_coords = _loc(po["gate"]) if po.get("gate") else _loc(po)
        pd_coords = _loc(pd["gate"]) if pd.get("gate") else _loc(pd)

        # 1. Add Markers
        self.map_widget.set_marker(origin_coords[0], origin_coords[1], text=geo["origin"]["label"])
        self.map_widget.set_marker(dest_coords[0], dest_coords[1], text=geo["destiny"]["label"])
        self.map_widget.set_marker(po_coords[0], po_coords[1], text=f"Port: {po['name']}", marker_color_circle="blue")
        self.map_widget.set_marker(pd_coords[0], pd_coords[1], text=f"Port: {pd['name']}", marker_color_circle="blue")
        
        # 2. Draw Paths
        
        # ROAD 1 (Origin -> Port Origin)
        # Use set_path with a list of coordinate tuples
        if origin_coords != po_coords:
             self.map_widget.set_path([origin_coords, po_coords], color="#800080", width=3) # Purple

        # SEA (Port Origin -> Port Destiny)
        # Use the new curved renderer
        sea_path = get_visual_sea_path(po_coords, pd_coords)
        if sea_path and len(sea_path) > 1:
             self.map_widget.set_path(sea_path, color="#0000FF", width=4) # Blue

        # ROAD 2 (Port Destiny -> Destiny)
        if pd_coords != dest_coords:
             self.map_widget.set_path([pd_coords, dest_coords], color="#800080", width=3) # Purple

        # ROAD DIRECT (Origin -> Destiny)
        # This is the pure road comparison leg. Draw it in RED.
        # We check if it's distinct from the multimodal path to avoid clutter, 
        # but usually it's nice to see the "straight line" alternative.
        self.map_widget.set_path([origin_coords, dest_coords], color="#FF0000", width=2) # Red

        # 3. Set View
        # Include all waypoints so the whole curve is seen
        all_points = [origin_coords, dest_coords] + sea_path
        all_lats = [p[0] for p in all_points]
        all_lons = [p[1] for p in all_points]

        min_lat, max_lat = min(all_lats), max(all_lats)
        min_lon, max_lon = min(all_lons), max(all_lons)

        # Pad the view slightly so markers aren't on the absolute edge
        pad = 1.0
        
        try:
            self.map_widget.fit_bounding_box(
                (max_lat + pad, min_lon - pad), 
                (min_lat - pad, max_lon + pad)
            )
        except Exception as e:
             _log.warning(f"Could not fit bounding box: {e}")

    def _show_report(self, res):
        rd = res["road_only"]
        mm = res["multimodal"]
        cp = res["comparison"]
        
        l = []
        l.append("📊 COMPARISON RESULT")
        l.append("-" * 35)
        l.append(f"ROAD ONLY ({rd['distance_km']:.0f} km)")
        l.append(f"  Fuel: {rd['liters']:.0f} L")
        l.append(f"  Cost: R$ {rd['cost']:,.2f}")
        l.append(f"  CO2e: {rd['co2e']:.0f} kg")
        l.append("-" * 35)
        l.append(f"MULTIMODAL (Sea: {mm['sea']['distance_km']:.0f} km)")
        l.append(f"  Road Legs: {mm['first_mile']['distance_km'] + mm['last_mile']['distance_km']:.0f} km")
        l.append(f"  Cost: R$ {mm['total_cost']:,.2f}")
        l.append(f"  CO2e: {mm['total_co2e']:.0f} kg")
        l.append("=" * 35)
        
        savings = cp['savings_pct']
        emoji = "✅" if savings > 0 else "❌"
        l.append(f"{emoji} SAVINGS: {savings:.1f}%")
        l.append(f"   R$ {cp['delta_cost']*-1:,.2f}")
        
        self._log_ui("\n".join(l))

if __name__ == "__main__":
    app = ComparisonApp()
    app.mainloop()