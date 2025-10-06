from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Tuple

import math
import random

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None

# ---------------------------------------------------------------------------
# Soil profile (SNOMIN compatible)
# ---------------------------------------------------------------------------
_SM_FROM_PF = [
    -1.0, 0.366,
    1.0, 0.338,
    1.3, 0.304,
    1.7, 0.233,
    2.0, 0.179,
    2.3, 0.135,
    2.4, 0.123,
    2.7, 0.094,
    3.0, 0.073,
    3.3, 0.059,
    3.7, 0.046,
    4.0, 0.039,
    4.17, 0.037,
    4.2, 0.036,
    6.0, 0.02,
]

_COND_FROM_PF = [
    -1.0, 1.8451,
    1.0, 1.02119,
    1.3, 0.51055,
    1.7, -0.52288,
    2.0, -1.50864,
    2.3, -2.56864,
    2.4, -2.92082,
    2.7, -4.01773,
    3.0, -5.11919,
    3.3, -6.22185,
    3.7, -7.69897,
    4.0, -8.79588,
    4.17, -9.4318,
    4.2, -9.5376,
    6.0, -11.5376,
]


def _make_layer(thickness: float, fsomi: float) -> Dict[str, float]:
    return {
        "Thickness": thickness,
        "SMfromPF": list(_SM_FROM_PF),
        "CONDfromPF": list(_COND_FROM_PF),
        "CRAIRC": 0.09,
        "CNRatioSOMI": 9.0,
        "FSOMI": fsomi,
        "RHOD": 1.406,
        "Soil_pH": 7.4,
    }


_SOIL_TEMPLATE = {
    "SMFCF": 0.179,
    "SM0": 0.366,
    "SMW": 0.036,
    "CRAIRC": 0.09,
    "RDMSOL": 125.0,
    "K0": 10.0,
    "SOPE": 10.0,
    "KSUB": 10.0,
    "CNSOL": 45.0,
    "SoilProfileDescription": {
        "PFWiltingPoint": 4.2,
        "PFFieldCapacity": 2.0,
        "SurfaceConductivity": 70.0,
        "GroundWater": None,
        "SoilLayers": [
            _make_layer(10.0, 0.02),
            _make_layer(10.0, 0.02),
            _make_layer(10.0, 0.01),
            _make_layer(20.0, 0.00),
            _make_layer(30.0, 0.00),
            _make_layer(45.0, 0.00),
        ],
        "SubSoilType": _make_layer(200.0, 0.00),
    },
}
_SOIL_TEMPLATE["RDMSOL"] = sum(layer["Thickness"] for layer in _SOIL_TEMPLATE["SoilProfileDescription"]["SoilLayers"])


def get_soil_profile() -> Dict:
    """Return a deep copy of the SNOMIN soil profile."""
    return deepcopy(_SOIL_TEMPLATE)


def get_site_parameters(lat: float, lon: float, elev: float, soil: Dict, start_soil_n: float = 60.0) -> Dict:
    """Build keyword arguments for WOFOST81SiteDataProvider_SNOMIN."""
    num_layers = len(soil["SoilProfileDescription"]["SoilLayers"])
    nh4_init = [max(0.2, 2.0 - idx * 0.3) for idx in range(num_layers)]
    no3_init = [max(0.5, 5.0 - idx * 0.7) for idx in range(num_layers)]
    wav = soil["SMFCF"] * soil["RDMSOL"] / 10.0
    return {
        "IFUNRN": 0,
        "NOTINF": 0.0,
        "SSI": 0.0,
        "SSMAX": 0.0,
        "WAV": wav,
        "SMLIM": soil.get("SMFCF", 0.18),
        "CO2": 420.0,
        "A0SOM": 24.0,
        "CNRatioBio": 9.0,
        "FASDIS": 0.5,
        "KDENIT_REF": 0.06,
        "KNIT_REF": 1.0,
        "KSORP": 0.0005,
        "MRCDIS": 0.001,
        "NH4ConcR": 0.0,
        "NO3ConcR": 0.0,
        "WFPS_CRIT": 0.8,
        "NH4I": nh4_init,
        "NO3I": no3_init,
    }


# ---------------------------------------------------------------------------
# Weather handling
# ---------------------------------------------------------------------------
_DEFAULT_WEATHER = {
    "IRRAD": 18_000_000.0,  # J/m2/day
    "TMIN": 10.0,
    "TMAX": 21.0,
    "TEMP": 15.5,
    "VAP": 12.0,            # hPa
    "RAIN": 0.0,            # cm/day
    "E0": 0.42,             # cm/day
    "ES0": 0.40,            # cm/day
    "ET0": 0.41,            # cm/day
    "WIND": 2.0,            # m/s
}


def _normalise_day(value: date | str) -> Tuple[date, str]:
    if isinstance(value, date):
        return value, value.strftime("%Y%m%d")
    if isinstance(value, str):
        value = value.strip()
        try:
            if len(value) == 8:
                day = datetime.strptime(value, "%Y%m%d").date()
            else:
                day = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported date format: {value}") from exc
        return day, day.strftime("%Y%m%d")
    raise TypeError("Date must be datetime.date or YYYYMMDD string")


def _calc_vap(qv2m: Optional[float], ps: Optional[float]) -> Optional[float]:
    if qv2m is None or ps is None:
        return None
    # QV2M is g/kg, convert to kg/kg
    q = (qv2m / 1000.0)
    # PS is kPa -> convert to hPa after calculation
    vap_kpa = (q * ps) / (0.622 + 0.378 * q)
    return vap_kpa * 10.0  # hPa


def _nasa_power_weather(lat: float, lon: float, day_str: str) -> Optional[Dict[str, float]]:
    if requests is None:
        return None

    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,T2M_MAX,T2M_MIN,PRECTOTCORR,QV2M,PS,WS2M,ET0",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": day_str,
        "end": day_str,
        "format": "JSON",
        "time-standard": "UTC",
    }
    base = "https://power.larc.nasa.gov/api/temporal/daily/point"
    try:
        resp = requests.get(base, params=params, timeout=12)
        resp.raise_for_status()
        payload = resp.json()["properties"]["parameter"]
    except Exception:
        return None

    def pick(name: str) -> Optional[float]:
        series = payload.get(name)
        if not series:
            return None
        value = series.get(day_str)
        return None if value is None else float(value)

    irr = pick("ALLSKY_SFC_SW_DWN")
    if irr is not None:
        # NASA POWER delivers kWh/m2/day, convert to J/m2/day
        irr *= 3_600_000.0

    tmax = pick("T2M_MAX")
    tmin = pick("T2M_MIN")
    rain = pick("PRECTOTCORR")
    qv2m = pick("QV2M")
    ps = pick("PS")
    wind = pick("WS2M")
    et0 = pick("ET0")

    if irr is None and tmax is None and rain is None:
        return None

    temp = None
    if tmax is not None and tmin is not None:
        temp = 0.5 * (tmax + tmin)

    rain_cm = (rain / 10.0) if rain is not None else None
    vap = _calc_vap(qv2m, ps)

    if et0 is not None:
        et0_cm = et0 / 10.0
    else:
        et0_cm = None

    snow_cm = None
    if rain_cm is not None and tmax is not None:
        if tmax <= 0.0:  # below freezing
            snow_cm = rain_cm
            rain_cm = 0.0  # all precip counted as snow

    return {
        "IRRAD": irr,
        "TMAX": tmax,
        "TMIN": tmin,
        "TEMP": temp,
        "RAIN": rain_cm,
        "SNOW": snow_cm,
        "VAP": vap,
        "WIND": wind,
        "E0": et0_cm,
        "ES0": et0_cm,
        "ET0": et0_cm,
    }




def _synthetic_weather(lat: float, lon: float, day: date) -> Dict[str, float]:
    """Generate a deterministic synthetic weather profile when NASA POWER data is unavailable."""
    doy = day.timetuple().tm_yday
    phase = 2.0 * math.pi * (doy - 80) / 365.0
    rnd = random.Random((hash((round(lat, 4), round(lon, 4), day.toordinal())) & 0xFFFFFFFF))

    base_temp = 12.0 + 10.0 * math.sin(phase)
    diurnal_amp = 6.0 + 2.0 * math.cos(phase)
    tmax = base_temp + diurnal_amp + rnd.uniform(-1.0, 1.0)
    tmin = base_temp - diurnal_amp + rnd.uniform(-1.0, 1.0)
    temp = 0.5 * (tmax + tmin)

    irr = 16_000_000.0 + 6_000_000.0 * math.sin(phase) + rnd.uniform(-1_000_000.0, 1_000_000.0)
    irr = max(6_000_000.0, irr)

    rain_base = 0.8 * (1.0 + math.sin(phase - math.pi / 3.0))
    rain = max(0.0, rain_base + rnd.uniform(-0.3, 0.3)) * 0.8

    vap = 8.0 + 6.0 * (1.0 - math.sin(phase)) + rnd.uniform(-1.0, 1.0)
    wind = 2.0 + 0.5 * math.cos(phase) + rnd.uniform(-0.5, 0.5)
    et0 = 0.35 + 0.25 * math.sin(phase) + rnd.uniform(-0.05, 0.05)

    rain_cm = rain
    et0_cm = max(0.0, et0)

    return {
        "IRRAD": irr,
        "TMAX": tmax,
        "TMIN": tmin,
        "TEMP": temp,
        "RAIN": rain_cm,
        "VAP": max(0.0, vap),
        "WIND": max(0.0, wind),
        "E0": et0_cm,
        "ES0": et0_cm,
        "ET0": et0_cm,
    }

def _merge_weather(record: Optional[Dict[str, float]]) -> Dict[str, float]:
    merged = dict(_DEFAULT_WEATHER)
    if record:
        for key, value in record.items():
            if value is not None:
                merged[key] = value
    # Ensure TEMP exists even if only one of TMIN/TMAX came through
    if merged.get("TEMP") is None:
        tmin = merged.get("TMIN")
        tmax = merged.get("TMAX")
        if tmin is not None and tmax is not None:
            merged["TEMP"] = 0.5 * (tmin + tmax)
        else:
            merged["TEMP"] = _DEFAULT_WEATHER["TEMP"]
    # Guarantee evaporation defaults if still None
    for key in ("E0", "ES0", "ET0"):
        if merged.get(key) is None:
            merged[key] = _DEFAULT_WEATHER[key]
    return merged



def get_weather(lat: float, lon: float, day: date | str) -> Dict[str, float]:
    """Return a PCSE-compatible weather record for the given day."""
    day_obj, day_str = _normalise_day(day)
    record = _nasa_power_weather(lat, lon, day_str)
    if record is None:
        record = _synthetic_weather(lat, lon, day_obj)
    merged = _merge_weather(record)
    merged["DAY"] = day_obj
    return merged


def predict_weather(weather_data: Optional[Dict[str, float]]) -> Optional[List[str]]:
    if not weather_data:
        return None

    # Thresholds
    snow_thresh = 0.5    # cm/day — adjust as needed
    rain_thresh = 0.1    # cm/day (~1 mm)
    humid_thresh_hpa = 15.0
    wind_thresh = 5.0
    warm_thresh = 20.0

    # Collect detected conditions
    detected = set()

    snow = weather_data.get("SNOW")
    if isinstance(snow, (int, float)) and snow >= snow_thresh:
        detected.add("snowy")

    rain = weather_data.get("RAIN")
    if isinstance(rain, (int, float)) and rain >= rain_thresh:
        detected.add("rainy")

    vap = weather_data.get("VAP")
    if isinstance(vap, (int, float)) and vap >= humid_thresh_hpa:
        detected.add("humid")

    wind = weather_data.get("WIND")
    if isinstance(wind, (int, float)) and wind >= wind_thresh:
        detected.add("windy")

    tmax = weather_data.get("TMAX")
    if isinstance(tmax, (int, float)) and tmax >= warm_thresh:
        detected.add("sunny")

    if not detected:
        return None

    # Priority order (highest → lowest)
    priority = ["snowy", "rainy", "sunny", "windy", "humid"]

    # Sort detected conditions by priority
    ordered_predictions = [cond for cond in priority if cond in detected]

    return ordered_predictions


if __name__ == "__main__":  # pragma: no cover
    print("Soil profile cheque:")
    print(get_soil_profile()["SoilProfileDescription"]["SoilLayers"][0])

    # Date from the user's input
    today = date(2024, 5, 1)

    # Coordinates should be same as the soil profile dataset
    w = get_weather(49.104, -122.66, today)
    print("Weather record:", w)
    print("Forecast tags:", predict_weather(w))
