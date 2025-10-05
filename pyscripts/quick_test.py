from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from game import CropGame


def run_scenario(
    name: str,
    days: int,
    irrig_strategy: str = "none",
    fert_strategy: str = "baseline",
) -> pd.DataFrame:
    """Run a scenario with configurable irrigation and fertilisation strategies."""
    g = CropGame(lat=49.104, lon=-122.66, elev=36.0)
    sow = date(2024, 1, 1)
    g.plant(crop_name="wheat", sowing_date=sow)

    rows: List[Dict] = []
    emerged = False
    overwater_counter = 0
    last_rftra = 1.0
    last_dvs: float | None = None
    fert_primary_done = False
    fert_secondary_done = False

    for _ in range(days):
        # Water strategies
        if irrig_strategy == "threshold" and last_rftra < 0.8:
            g.water(2.0)
        elif irrig_strategy == "overwater" and emerged and overwater_counter < 12:
            g.water(5.0)
            overwater_counter += 1
        elif irrig_strategy == "underwater" and last_rftra < 0.6:
            g.water(0.5)

        # Fertiliser strategies
        if fert_strategy in {"baseline", "heavy"} and emerged and not fert_primary_done:
            g.fertilize(40.0 if fert_strategy == "baseline" else 80.0, nh4_fraction=0.65)
            fert_primary_done = True
        if (
            fert_strategy == "heavy"
            and emerged
            and last_dvs is not None
            and last_dvs >= 0.75
            and not fert_secondary_done
        ):
            g.fertilize(80.0, nh4_fraction=0.7)
            fert_secondary_done = True

        d, st = g.tick()
        rftra = g.model.get_variable("RFTRA") or 1.0
        dvs = st.get("DVS")
        lai = st.get("LAI")
        yield_kg = st.get("TWSO") or 0.0
        sm = st.get("SM")
        if isinstance(sm, np.ndarray) and sm.size:
            sm_top = float(sm[0])
            sm_mean = float(sm.mean())
        else:
            sm_top = float(sm) if sm is not None else np.nan
            sm_mean = sm_top
        navail = g.model.get_variable("NAVAIL")
        rows.append(
            {
                "day": d,
                "doy": d.timetuple().tm_yday,
                "scenario": name,
                "dvs": dvs,
                "lai": lai,
                "yield": yield_kg,
                "rftra": rftra,
                "sm_top": sm_top,
                "sm_mean": sm_mean,
                "navail": navail,
            }
        )
        last_rftra = rftra
        last_dvs = dvs if isinstance(dvs, (int, float)) else last_dvs
        if not emerged and dvs is not None and dvs >= 0.0:
            emerged = True
            overwater_counter = 0

    return pd.DataFrame(rows)


def main():
    days = 300
    scenarios: List[Tuple[str, str, str]] = [
        ("Dry - no N", "none", "none"),
        ("Dry - baseline N", "none", "baseline"),
        ("Irrigation - no N", "threshold", "none"),
        ("Irrigation - baseline N", "threshold", "baseline"),
        ("Irrigation - heavy N", "threshold", "heavy"),
        ("Underwater - baseline N", "underwater", "baseline"),
        ("Overwater - baseline N", "overwater", "baseline"),
    ]

    frames = [run_scenario(name, days, irrig, fert) for name, irrig, fert in scenarios]
    df = pd.concat(frames, ignore_index=True)

    fig, axes = plt.subplots(4, 1, figsize=(11, 12), sharex=True)
    for name, grp in df.groupby("scenario"):
        axes[0].plot(grp["day"], grp["yield"], label=name)
    axes[0].set_ylabel("Yield TWSO (kg/ha)")
    axes[0].set_title("Yield trajectory")
    axes[0].legend(ncol=2, fontsize="small")

    for name, grp in df.groupby("scenario"):
        axes[1].plot(grp["day"], grp["rftra"], label=name)
    axes[1].set_ylabel("RFTRA (1=no stress)")
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("Water stress reduction factor")

    for name, grp in df.groupby("scenario"):
        axes[2].plot(grp["day"], grp["navail"], label=name)
    axes[2].set_ylabel("NAVAIL (kg N/ha)")
    axes[2].set_title("Soil N availability")

    for name, grp in df.groupby("scenario"):
        axes[3].plot(grp["day"], grp["sm_top"], label=name)
    axes[3].set_ylabel("Top-layer SM (m3/m3)")
    axes[3].set_title("Soil moisture (top layer)")
    axes[3].set_xlabel("Date")

    fig.tight_layout()
    outdir = Path("img")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "pcse_water_nitrogen_scenarios.png"
    fig.savefig(outfile, dpi=150)
    print(f"Saved figure -> {outfile}")

    summary = df.groupby("scenario").tail(1)[["scenario", "yield", "rftra", "navail", "sm_top"]]
    print("\nFinal-day snapshot:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
