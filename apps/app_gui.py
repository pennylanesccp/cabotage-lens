#!/usr/bin/env python3
# apps/app_gui.py
# -*- coding: utf-8 -*-

"""
Carbon Footprint GUI.
=====================

A simple Tkinter interface for the Single Route Comparator.
Allows users to input Origin/Destiny/Cargo and see the comparison results.
"""

import sys
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Path Bootstrap (Ensure we can import modules)
# If running as a script, we need to add the repo root to sys.path
if getattr(sys, 'frozen', False):
    # If running as a compiled .exe
    ROOT = Path(sys._MEIPASS).resolve() # type: ignore
else:
    ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import our logic
from modules.infra.log_manager import init_logging, get_logger
from modules.multimodal import build_path_geometry, evaluate_path
from modules.fuel.truck_specs import list_truck_keys

_log = get_logger("gui")

class ComparisonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Carbon Footprint Comparator")
        self.geometry("600x700")
        
        # Initialize Logging (File only, to keep console clean if any)
        init_logging(level="INFO", write_to_file=True)
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Main Frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Multimodal Logistics Analysis", font=("Helvetica", 16, "bold")).pack(pady=(0, 20))
        
        # --- Inputs ---
        input_frame = ttk.LabelFrame(main_frame, text="Inputs", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Origin
        ttk.Label(input_frame, text="Origin (City/Address):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ent_origin = ttk.Entry(input_frame, width=40)
        self.ent_origin.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.ent_origin.insert(0, "Avenida Professor Luciano Gualberto, São Paulo")
        
        # Destiny
        ttk.Label(input_frame, text="Destiny (City/Address):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ent_destiny = ttk.Entry(input_frame, width=40)
        self.ent_destiny.grid(row=1, column=1, sticky=tk.W, padx=5)
        self.ent_destiny.insert(0, "Manaus, AM")
        
        # Cargo
        ttk.Label(input_frame, text="Cargo (tonnes):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.ent_cargo = ttk.Entry(input_frame, width=10)
        self.ent_cargo.grid(row=2, column=1, sticky=tk.W, padx=5)
        self.ent_cargo.insert(0, "30.0")
        
        # Truck Selector
        ttk.Label(input_frame, text="Truck Type:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.cb_truck = ttk.Combobox(input_frame, values=sorted(list_truck_keys()), state="readonly")
        self.cb_truck.set("semi_27t")
        self.cb_truck.grid(row=3, column=1, sticky=tk.W, padx=5)

        # --- Actions ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        self.btn_run = ttk.Button(btn_frame, text="Calculate Comparison", command=self._on_run)
        self.btn_run.pack(side=tk.RIGHT)
        
        # --- Results ---
        result_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.txt_output = tk.Text(result_frame, height=15, width=60, state=tk.DISABLED, font=("Consolas", 10))
        self.txt_output.pack(fill=tk.BOTH, expand=True)
        
        # Status Bar
        self.lbl_status = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    def _log_ui(self, msg: str):
        self.txt_output.config(state=tk.NORMAL)
        self.txt_output.insert(tk.END, msg + "\n")
        self.txt_output.see(tk.END)
        self.txt_output.config(state=tk.DISABLED)
        self.lbl_status.config(text=msg)

    def _on_run(self):
        # Disable button
        self.btn_run.config(state=tk.DISABLED)
        self.txt_output.config(state=tk.NORMAL)
        self.txt_output.delete(1.0, tk.END)
        self.txt_output.config(state=tk.DISABLED)
        
        origin = self.ent_origin.get().strip()
        destiny = self.ent_destiny.get().strip()
        try:
            cargo = float(self.ent_cargo.get())
        except ValueError:
            messagebox.showerror("Input Error", "Cargo must be a number.")
            self.btn_run.config(state=tk.NORMAL)
            return
            
        truck = self.cb_truck.get()
        
        # Run in thread to keep UI responsive
        threading.Thread(target=self._run_process, args=(origin, destiny, cargo, truck), daemon=True).start()

    def _run_process(self, origin, destiny, cargo, truck):
        try:
            self._log_ui(f"📍 Routing: {origin} -> {destiny}...")
            
            # 1. Build Geometry
            geo = build_path_geometry(
                origin, destiny, 
                ors_profile="driving-hgv", 
                overwrite_road=False # Use cache by default for GUI speed
            )
            
            if not geo or geo["status"] != "ok":
                self._log_ui("❌ Error: Could not build route geometry.")
                return

            self._log_ui(f"✅ Geometry Found! (Direct Road: {geo['road_direct']['distance_km']:.1f} km)")
            self._log_ui("⚙️ Calculating costs & emissions...")

            # 2. Evaluate
            res = evaluate_path(geo, cargo_t=cargo, truck_key=truck)
            
            # 3. Display
            self._display_results(res, geo)
            
        except Exception as e:
            self._log_ui(f"💥 Critical Error: {e}")
            _log.exception("GUI process failed")
        finally:
            # Re-enable button in main thread
            self.after(0, lambda: self.btn_run.config(state=tk.NORMAL))
            self.after(0, lambda: self.lbl_status.config(text="Done."))

    def _display_results(self, res: dict, geo: dict):
        rd = res["road_only"]
        mm = res["multimodal"]
        cp = res["comparison"]
        
        out = []
        out.append("="*40)
        out.append(f"COMPARISON REPORT")
        out.append("="*40)
        out.append(f"Origin:  {geo['origin']['label']}")
        out.append(f"Destiny: {geo['destiny']['label']}")
        out.append(f"Cargo:   {res['inputs']['cargo_t']} t  ({res['inputs']['truck']})")
        out.append("-" * 40)
        
        out.append(f"TRUCK ONLY ({rd['distance_km']:.0f} km)")
        out.append(f"  Fuel: {rd['liters']:.0f} L")
        out.append(f"  Cost: R$ {rd['cost']:,.2f}")
        out.append(f"  CO2e: {rd['co2e']:.1f} kg")
        
        out.append("-" * 40)
        
        out.append(f"MULTIMODAL (Sea: {mm['sea']['distance_km']:.0f} km)")
        out.append(f"  Road Legs: {mm['first_mile']['distance_km'] + mm['last_mile']['distance_km']:.0f} km")
        out.append(f"  Cost: R$ {mm['total_cost']:,.2f}")
        out.append(f"  CO2e: {mm['total_co2e']:.1f} kg")
        
        out.append("=" * 40)
        
        savings = cp['savings_pct']
        sign = "+" if savings > 0 else ""
        out.append(f"SAVINGS: {sign}{savings:.1f}%")
        out.append(f"DELTA:   R$ {cp['delta_cost']*-1:,.2f}")
        out.append("=" * 40)

        final_text = "\n".join(out)
        
        # Update UI on main thread
        self.after(0, lambda: self._log_ui(final_text))

if __name__ == "__main__":
    app = ComparisonApp()
    app.mainloop()