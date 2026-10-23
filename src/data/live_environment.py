"""Free live environmental data for Pahad Guard.

This module replaces the previous Google Earth Engine dependency with public,
keyless services:

- Open-Meteo: hourly precipitation, soil moisture and elevation.
- OpenTopoData (SRTM 30m): elevation samples used to estimate terrain slope.

The functions intentionally return the same feature names expected by the
existing prediction pipeline, so app.py does not need a second ML pipeline.
"""

from __future__ import annotations

import math
from typing import Any

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_TOPO_URL = "https://api.opentopodata.org/v1/srtm30m"
USER_AGENT = "PahadGuard-LandslideRiskApp/2.0"


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("The data service returned an unexpected response.")
    return payload


def _rolling_precipitation(values: list[Any], hours: int) -> float:
    """Sum the most recent `hours` hourly precipitation observations."""
    numeric = []
    for value in values[-hours:]:
        try:
            numeric.append(float(value))
        except (TypeError, ValueError):
            continue
    return round(sum(numeric), 2)


def get_open_meteo_features(latitude: float, longitude: float) -> dict[str, float | None]:
    """Get live/modelled weather, soil moisture and elevation for a point.

    Open-Meteo returns hourly precipitation for the previous 7 days plus the
    current forecast period. We derive 24h/3-day/7-day rolling rainfall totals
    from those hourly values.
    """
    payload = _get_json(
        OPEN_METEO_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "precipitation,soil_moisture_0_to_1cm",
            "past_days": 7,
            "forecast_days": 1,
            "timezone": "UTC",
        },
    )

    hourly = payload.get("hourly", {})
    precipitation = hourly.get("precipitation") or []
    soil_values = hourly.get("soil_moisture_0_to_1cm") or []

    soil_moisture = None
    for value in reversed(soil_values):
        try:
            if value is not None:
                soil_moisture = float(value)
                break
        except (TypeError, ValueError):
            pass

    elevation = payload.get("elevation")
    try:
        elevation = float(elevation) if elevation is not None else None
    except (TypeError, ValueError):
        elevation = None

    return {
        "rainfall_24h": _rolling_precipitation(precipitation, 24),
        "rainfall_3day": _rolling_precipitation(precipitation, 72),
        "rainfall_7day": _rolling_precipitation(precipitation, 168),
        "soil_moisture": soil_moisture,
        "elevation": elevation,
    }


def _offset_coordinate(latitude: float, longitude: float, north_m: float, east_m: float):
    """Move approximately north/east by metres on the WGS84 surface."""
    lat_delta = north_m / 111_320.0
    lon_scale = 111_320.0 * max(math.cos(math.radians(latitude)), 0.01)
    lon_delta = east_m / lon_scale
    return latitude + lat_delta, longitude + lon_delta


def get_srtm_slope(latitude: float, longitude: float) -> float | None:
    """Estimate slope angle from SRTM 30m elevation samples.

    Four points are sampled roughly 30 m north/south/east/west of the target.
    The central differences give horizontal elevation gradients, which are
    converted to degrees. This is an estimate, not a survey-grade slope.
    """
    points = [
        (latitude, longitude),
        _offset_coordinate(latitude, longitude, 30, 0),
        _offset_coordinate(latitude, longitude, -30, 0),
        _offset_coordinate(latitude, longitude, 0, 30),
        _offset_coordinate(latitude, longitude, 0, -30),
    ]

    locations = "|".join(f"{lat:.7f},{lon:.7f}" for lat, lon in points)
    payload = _get_json(OPEN_TOPO_URL, {"locations": locations})
    results = payload.get("results", [])

    elevations = []
    for item in results:
        value = item.get("elevation") if isinstance(item, dict) else None
        try:
            elevations.append(float(value) if value is not None else None)
        except (TypeError, ValueError):
            elevations.append(None)

    if len(elevations) != 5 or any(value is None for value in elevations):
        return None

    _, north, south, east, west = elevations
    dz_dnorth = (north - south) / 60.0
    dz_deast = (east - west) / 60.0
    gradient = math.sqrt(dz_dnorth**2 + dz_deast**2)
    slope_degrees = math.degrees(math.atan(gradient))

    return round(max(0.0, min(90.0, slope_degrees)), 2)


def get_dynamic_features(latitude: float, longitude: float) -> dict[str, float | None]:
    """Return the live feature set expected by Pahad Guard."""
    weather = get_open_meteo_features(latitude, longitude)

    try:
        slope = get_srtm_slope(latitude, longitude)
    except requests.RequestException:
        slope = None

    return {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "rainfall_24h": weather["rainfall_24h"],
        "rainfall_3day": weather["rainfall_3day"],
        "rainfall_7day": weather["rainfall_7day"],
        "elevation": weather["elevation"],
        "slope": slope,
        "soil_moisture": weather["soil_moisture"],
    }
