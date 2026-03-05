from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from app.main.utils.formatters import fmt_currency_brl, fmt_emissions_kg, safe_float


def build_port_and_endpoint_points(
    *,
    origin: Tuple[float, float],
    destiny: Tuple[float, float],
    po_coords: Tuple[float, float],
    pd_coords: Tuple[float, float],
    origin_name: str,
    destiny_name: str,
    port_origin_name: str,
    port_destiny_name: str,
    maritime: Mapping[str, float],
    radius_base: float,
    show_ports: bool,
) -> List[Dict[str, Any]]:
    points: list[dict[str, Any]] = [
        {
            "kind": "Origin",
            "label": origin_name,
            "position": [origin[1], origin[0]],
            "lat": origin[0],
            "lon": origin[1],
            "color": [192, 57, 43, 245],
            "radius": radius_base,
            "tooltip": f"Origin: {origin_name}",
        },
        {
            "kind": "Destination",
            "label": destiny_name,
            "position": [destiny[1], destiny[0]],
            "lat": destiny[0],
            "lon": destiny[1],
            "color": [192, 57, 43, 245],
            "radius": radius_base,
            "tooltip": f"Destination: {destiny_name}",
        },
    ]

    if not show_ports:
        return points

    port_ops_cost_each = safe_float(maritime.get("port_ops_cost_brl")) / 2.0
    port_ops_co2_each = safe_float(maritime.get("port_ops_co2e_kg")) / 2.0
    hoteling_cost_each = safe_float(maritime.get("hoteling_cost_brl")) / 2.0
    hoteling_co2_each = safe_float(maritime.get("hoteling_co2e_kg")) / 2.0

    points.extend(
        [
            {
                "kind": "Port",
                "label": port_origin_name,
                "position": [po_coords[1], po_coords[0]],
                "lat": po_coords[0],
                "lon": po_coords[1],
                "color": [39, 174, 96, 245],
                "radius": radius_base * 1.1,
                "tooltip": (
                    f"Origin port: {port_origin_name}\n"
                    f"Port ops: {fmt_currency_brl(port_ops_cost_each)} | {fmt_emissions_kg(port_ops_co2_each)}\n"
                    f"Hoteling: {fmt_currency_brl(hoteling_cost_each)} | {fmt_emissions_kg(hoteling_co2_each)}\n"
                    f"Port total: {fmt_currency_brl(port_ops_cost_each + hoteling_cost_each)} | "
                    f"{fmt_emissions_kg(port_ops_co2_each + hoteling_co2_each)}"
                ),
            },
            {
                "kind": "Port",
                "label": port_destiny_name,
                "position": [pd_coords[1], pd_coords[0]],
                "lat": pd_coords[0],
                "lon": pd_coords[1],
                "color": [39, 174, 96, 245],
                "radius": radius_base * 1.1,
                "tooltip": (
                    f"Destination port: {port_destiny_name}\n"
                    f"Port ops: {fmt_currency_brl(port_ops_cost_each)} | {fmt_emissions_kg(port_ops_co2_each)}\n"
                    f"Hoteling: {fmt_currency_brl(hoteling_cost_each)} | {fmt_emissions_kg(hoteling_co2_each)}\n"
                    f"Port total: {fmt_currency_brl(port_ops_cost_each + hoteling_cost_each)} | "
                    f"{fmt_emissions_kg(port_ops_co2_each + hoteling_co2_each)}"
                ),
            },
        ]
    )

    return points
