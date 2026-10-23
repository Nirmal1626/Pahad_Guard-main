from pathlib import Path

import numpy as np
import pandas as pd


# Representative real-world coordinates for towns/areas in Sikkim.
# These are used as geographic anchors so the demo map is not randomly
# scattered across a rectangle. Live coordinate analysis queries the selected
# coordinate directly from public data services.
SIKKIM_LOCATIONS = [
    ("Gangtok", 27.3389, 88.6065),
    ("Rangpo", 27.1773, 88.5336),
    ("Singtam", 27.2340, 88.5010),
    ("Pakyong", 27.2300, 88.6130),
    ("Aritar", 27.1550, 88.6800),
    ("Rorathang", 27.1900, 88.7000),
    ("Nathu La", 27.3860, 88.8300),
    ("Zuluk", 27.2700, 88.7600),
    ("Mangan", 27.5090, 88.5330),
    ("Chungthang", 27.6060, 88.6430),
    ("Lachen", 27.7200, 88.5560),
    ("Lachung", 27.6880, 88.7420),
    ("Dzongu", 27.5000, 88.6200),
    ("Namchi", 27.1660, 88.3630),
    ("Ravangla", 27.3130, 88.3630),
    ("Jorethang", 27.1060, 88.3240),
    ("Melli", 27.0700, 88.4400),
    ("Temi", 27.2800, 88.3700),
    ("Sadam", 27.2000, 88.3900),
    ("Nayabazar", 27.1300, 88.3400),
    ("Pelling", 27.3170, 88.2390),
    ("Gyalshing", 27.2900, 88.2600),
    ("Yuksom", 27.3700, 88.2200),
    ("Soreng", 27.1700, 88.1900),
    ("Jorethang", 27.1065, 88.3235),
    ("Legship", 27.2400, 88.2500),
    ("Rinchenpong", 27.2000, 88.1800),
    ("Dentam", 27.2200, 88.1700),
    ("Hee Gaon", 27.3000, 88.2000),
    ("Tashiding", 27.3500, 88.3000),
    ("Sikkim-Manipur border area", 27.7500, 88.2500),
    ("Singhik", 27.5400, 88.5600),
    ("Kabi", 27.4400, 88.5900),
    ("Phodong", 27.4500, 88.6000),
    ("Ravangla East", 27.3000, 88.3900),
    ("Namthang", 27.1300, 88.5200),
    ("Yangang", 27.2400, 88.4100),
    ("Rolep", 27.2100, 88.6500),
    ("Gnathang", 27.3500, 88.7500),
]


def generate_demo_dataset(
    output_path: str | Path,
    rows: int = 180,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    locations = SIKKIM_LOCATIONS
    location_indices = np.arange(rows) % len(locations)
    selected = [locations[index] for index in location_indices]

    # Keep the first pass for every anchor at its actual coordinate. If more
    # rows are requested, create small nearby monitoring points around the
    # same real locations rather than random points across the whole state.
    latitudes = np.array([item[1] for item in selected], dtype=float)
    longitudes = np.array([item[2] for item in selected], dtype=float)
    repeated = np.arange(rows) // len(locations)
    latitudes += np.where(repeated > 0, rng.normal(0, 0.0025, rows), 0)
    longitudes += np.where(repeated > 0, rng.normal(0, 0.0025, rows), 0)
    names = [item[0] for item in selected]

    rainfall_24h = np.clip(rng.gamma(shape=2.5, scale=35, size=rows), 2, 280)
    rainfall_3day = rainfall_24h + rng.gamma(shape=2.5, scale=45, size=rows)
    rainfall_7day = rainfall_3day + rng.gamma(shape=2.5, scale=65, size=rows)

    soil_moisture = np.clip(
        0.25 + rainfall_7day / 650 + rng.normal(0, 0.08, rows),
        0.05,
        0.98,
    )

    elevation = np.clip(
        rng.normal(1450, 480, rows),
        150,
        3600,
    )

    slope = np.clip(
        5 + elevation / 125 + rng.normal(0, 8, rows),
        1,
        55,
    )

    land_covers = rng.choice(
        ["forest", "agriculture", "grassland", "bare_land", "urban"],
        size=rows,
        p=[0.48, 0.22, 0.14, 0.10, 0.06],
    )

    historical_landslide = rng.binomial(1, 0.20, rows)

    raw_score = (
        0.035 * rainfall_24h
        + 0.012 * rainfall_3day
        + 0.006 * rainfall_7day
        + 42 * soil_moisture
        + 1.15 * slope
        + 0.004 * elevation
        + 15 * historical_landslide
        + np.where(land_covers == "bare_land", 8, 0)
        + np.where(land_covers == "urban", 5, 0)
        + rng.normal(0, 8, rows)
    )

    probability = 1 / (1 + np.exp(-(raw_score - 78) / 14))
    labels = rng.binomial(1, probability)

    dates = pd.date_range(
        end=pd.Timestamp.today().normalize(),
        periods=rows,
        freq="D",
    )

    dataframe = pd.DataFrame(
        {
            "zone_id": [f"SIKKIM-{index + 1:03d}" for index in range(rows)],
            "location_name": names,
            "latitude": latitudes.round(6),
            "longitude": longitudes.round(6),
            "date": dates,
            "rainfall_24h": rainfall_24h.round(2),
            "rainfall_3day": rainfall_3day.round(2),
            "rainfall_7day": rainfall_7day.round(2),
            "soil_moisture": soil_moisture.round(3),
            "elevation": elevation.round(2),
            "slope": slope.round(2),
            "land_cover": land_covers,
            "historical_landslide": historical_landslide,
            "label": labels,
        }
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False)

    return dataframe


if __name__ == "__main__":
    from src.config import DATA_FILE

    generate_demo_dataset(DATA_FILE)
