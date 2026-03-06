from __future__ import annotations


def interpolate_leg_intermediate_points(
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
    *,
    n_points: int = 100,
) -> list[tuple[float, float]]:
    count = max(int(n_points), 0)
    if count == 0:
        return []

    start_lat, start_lon = float(start_latlon[0]), float(start_latlon[1])
    end_lat, end_lon = float(end_latlon[0]), float(end_latlon[1])

    points: list[tuple[float, float]] = []
    denominator = count + 1
    for idx in range(count):
        fraction = (idx + 1) / denominator
        lat = start_lat + ((end_lat - start_lat) * fraction)
        lon = start_lon + ((end_lon - start_lon) * fraction)
        points.append((lat, lon))
    return points
