from __future__ import annotations

import json
import socket
import threading
from datetime import date, datetime, timedelta
from difflib import get_close_matches
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import numpy as _np
except ImportError:
    _np = None

from pcse import signals
from pcse.base import ParameterProvider, WeatherDataContainer, WeatherDataProvider
from pcse.input import WOFOST81SiteDataProvider_SNOMIN, YAMLCropDataProvider
from pcse.models import Wofost81_NWLP_MLWB_SNOMIN

from data import get_soil_profile, get_site_parameters, get_weather, predict_weather

ModelType = Wofost81_NWLP_MLWB_SNOMIN

class GameWeatherProvider(WeatherDataProvider):
    """Simple in-memory weather provider backed by data.py helpers."""
    def __init__(self, lat: float, lon: float, elev: float, seed_record: Dict) -> None:
        super().__init__()
        self.latitude = lat
        self.longitude = lon
        self.elevation = elev
        self._site = {"LAT": lat, "LON": lon, "ELEV": elev}
        self.add_record(seed_record)
    def _to_container(self, record: Dict) -> WeatherDataContainer:
        payload = dict(self._site)
        item = dict(record)
        day = item["DAY"]
        if isinstance(day, str):
            day = date.fromisoformat(day)
            item["DAY"] = day
        # Ensure all evap terms exist for WeatherDataContainer
        item.setdefault("E0", item.get("ET0", 0.0))
        item.setdefault("ES0", item.get("ET0", 0.0))
        item.setdefault("ET0", item.get("E0", 0.0))
        if "TEMP" not in item and "TMIN" in item and "TMAX" in item:
            item["TEMP"] = (item["TMIN"] + item["TMAX"]) / 2.0
        payload.update(item)
        return WeatherDataContainer(**payload)
    def add_record(self, record: Dict) -> None:
        container = self._to_container(record)
        self._store_WeatherDataContainer(container, container.DAY)
    def ensure_day(self, day: date) -> None:
        key = (self.check_keydate(day), 0)
        if key not in self.store:
            self.add_record(get_weather(self.latitude, self.longitude, day))
    def __call__(self, day, member_id: int = 0):
        self.ensure_day(day)
        return super().__call__(day, member_id)

def resolve_crop_variety(
    user_crop: str,
    user_variety: Optional[str] = None,
    model=ModelType,
) -> Tuple[str, str]:
    cropd = YAMLCropDataProvider(model=model, force_reload=False)
    options = cropd.get_crops_varieties()
    crop_names = list(options.keys())
    crop_key = user_crop if user_crop in crop_names else None
    if crop_key is None:
        matches = get_close_matches(user_crop, crop_names, n=1, cutoff=0.0)
        crop_key = matches[0] if matches else None
    if crop_key is None:
        raise KeyError(f"Crop '{user_crop}' not found. Available options: {crop_names}")
    varieties = list(options[crop_key])
    if not varieties:
        raise KeyError(f"No varieties found for crop '{crop_key}'.")
    if user_variety:
        var_key = user_variety if user_variety in varieties else None
        if var_key is None:
            matches = get_close_matches(user_variety, varieties, n=1, cutoff=0.0)
            var_key = matches[0] if matches else varieties[0]
    else:
        var_key = "generic" if "generic" in varieties else varieties[0]
    return crop_key, var_key

class CropGame:
    """Lightweight wrapper around WOFOST to support turn-based gameplay."""
    def __init__(self, lat: float, lon: float, elev: float) -> None:
        self.lat = lat
        self.lon = lon
        self.elev = elev
        self.params: Optional[ParameterProvider] = None
        self.weather: Optional[GameWeatherProvider] = None
        self.model: Optional[ModelType] = None
        self.current_day: Optional[date] = None
        self._last_day: Optional[date] = None
        self._action_queue: List[Tuple[date, Callable[[ModelType], None]]] = []
    def plant(self, crop_name: str, sowing_date: date, variety_name: Optional[str] = None) -> None:
        cropd = YAMLCropDataProvider(model=ModelType, force_reload=False)
        crop_key, var_key = resolve_crop_variety(crop_name, variety_name, model=ModelType)
        cropd.set_active_crop(crop_key, var_key)
        soil = get_soil_profile()
        site_kwargs = get_site_parameters(self.lat, self.lon, self.elev, soil)
        site = WOFOST81SiteDataProvider_SNOMIN(**site_kwargs)
        site.update({"LAT": self.lat, "LON": self.lon, "ELEV": self.elev})
        self.params = ParameterProvider(cropd, soil, site)
        seed_day = sowing_date - timedelta(days=1)
        seed_record = get_weather(self.lat, self.lon, seed_day)
        self.weather = GameWeatherProvider(self.lat, self.lon, self.elev, seed_record)
        agroman = {
            "AgroManagement": [
                {
                    sowing_date: {
                        "CropCalendar": {
                            "crop_name": crop_key,
                            "variety_name": var_key,
                            "crop_start_date": sowing_date,
                            "crop_start_type": "sowing",
                            "crop_end_date": None,
                            "crop_end_type": "maturity",
                            "max_duration": 365,
                        },
                        "TimedEvents": None,
                        "StateEvents": None,
                    }
                }
            ]
        }
        self.model = ModelType(self.params, self.weather, agroman)
        self.current_day = sowing_date
        self._last_day = None
        self._action_queue.clear()
    def _schedule_action(self, day: date, callback: Callable[[ModelType], None]) -> None:
        if self.model is None or self.current_day is None:
            raise RuntimeError("Plant a crop before scheduling actions.")
        if day < self.current_day:
            raise ValueError("Cannot schedule an action in the past.")
        self._action_queue.append((day, callback))
        self._action_queue.sort(key=lambda item: item[0])
    def water(self, amount_cm: float, when: Optional[date] = None, efficiency: float = 0.75) -> None:
        if self.model is None or self.current_day is None:
            raise RuntimeError("Plant first.")
        target_day = when or self.current_day
        def _do(engine: ModelType) -> None:
            engine._send_signal(signal=signals.irrigate, amount=amount_cm, efficiency=efficiency)
        self._schedule_action(target_day, _do)
    def fertilize(self, n_kg_ha: float, when: Optional[date] = None, nh4_fraction: float = 0.7) -> None:
        if self.model is None or self.current_day is None:
            raise RuntimeError("Plant first.")
        target_day = when or self.current_day
        nh4 = max(0.0, min(1.0, nh4_fraction))
        no3 = max(0.0, 1.0 - nh4)
        def _do(engine: ModelType) -> None:
            engine._send_signal(
                signal=signals.apply_n_snomin,
                amount=n_kg_ha,
                application_depth=10.0,
                cnratio=8.0,
                initial_age=0.1,
                f_NH4N=nh4,
                f_NO3N=no3,
                f_orgmat=0.0,
            )
        self._schedule_action(target_day, _do)
    def kill(self, when: Optional[date] = None, reason: str = "killed", delete: bool = True) -> None:
        if self.model is None or self.current_day is None:
            raise RuntimeError("Plant first.")
        target_day = when or self.current_day
        def _do(engine: ModelType) -> None:
            engine._send_signal(signal=signals.crop_finish, day=engine.day, finish_type=reason, crop_delete=delete)
        self._schedule_action(target_day, _do)
    def _apply_pending_actions(self, day: date) -> None:
        if self.model is None:
            return
        ready: List[Callable[[ModelType], None]] = []
        future: List[Tuple[date, Callable[[ModelType], None]]] = []
        for action_day, callback in self._action_queue:
            if action_day <= day:
                ready.append(callback)
            else:
                future.append((action_day, callback))
        self._action_queue = future
        for callback in ready:
            callback(self.model)
    def tick(self) -> Tuple[date, Dict[str, float]]:
        if self.model is None:
            raise RuntimeError("Plant first.")
        engine = self.model
        day, delta = engine.timer()
        engine.integrate(day, delta)
        drv = engine._get_driving_variables(day)
        engine.drv = drv
        engine.agromanager(day, drv)
        self._apply_pending_actions(day)
        engine.calc_rates(day, drv)
        if engine.flag_terminate:
            engine._terminate_simulation(day)
        self._last_day = day
        self.current_day = day + timedelta(days=1)
        return day, self.get_state()
    def get_state(self) -> Dict[str, Any]:
        if self.model is None:
            return {}
        variables = ["DVS", "LAI", "SM", "TAGP", "TWSO", "TRA", "EVS"]
        state: Dict[str, Any] = {}
        for name in variables:
            try:
                value = self.model.get_variable(name)
            except Exception:
                value = None
            if value is not None:
                coerced = _coerce_state_value(value)
                state[name] = coerced
                if name == "SM":
                    profile = _numeric_sequence(coerced)
                    if profile:
                        average = sum(profile) / len(profile)
                        state["SM"] = float(average)
                        state["SM_profile"] = profile
        soil_n_value = None
        if self.model is not None:
            for var_name in SOIL_N_VARIABLES:
                try:
                    raw = self.model.get_variable(var_name)
                except Exception:
                    continue
                if raw is not None:
                    soil_n_value = _coerce_state_value(raw)
                    break
        if soil_n_value is not None:
            numeric = _coerce_to_float(soil_n_value)
            if numeric is not None:
                state["soil_n"] = numeric
        if "TAGP" in state:
            try:
                state["biomass"] = float(state["TAGP"])
            except (TypeError, ValueError):
                pass
        yield_candidate = state.get("TWSO") or state.get("TAGP") or state.get("biomass")
        yield_value = _coerce_to_float(yield_candidate)
        if yield_value is not None:
            state["yield_rate"] = yield_value
        return state

HOST = "127.0.0.1"
PORT = 5005
BUFFER_SIZE = 8192
SIM_DAYS = 120
DEFAULT_LAT = 49.104
DEFAULT_LON = -122.66
DEFAULT_ELEV = 36.0

GAME_BASE_YEAR = 2024

FERTILIZER_PRESETS = {
    "none": 0.0,
    "low": 20.0,
    "medium": 40.0,
    "high": 80.0,
}

IRRIGATION_PRESETS = {
    "none": 0.0,
    "drip": 1.5,
    "sprinkler": 2.5,
    "flood": 3.5,
}


SOIL_N_VARIABLES = [
    "NMIN",
    "NSOIL",
    "SMN",
    "NPOOL",
    "ANLV",
    "NO3",
    "NH4",
]

def _coerce_state_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if _np is not None:
        if isinstance(value, _np.generic):
            return value.item()
        if isinstance(value, _np.ndarray):
            if value.ndim == 0:
                return value.item()
            return [_coerce_state_value(item) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_coerce_state_value(item) for item in value]
    if hasattr(value, 'item'):
        try:
            return value.item()
        except Exception:
            pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)

def _numeric_sequence(value: Any) -> List[float]:
    if value is None:
        return []
    stack = [value]
    result: List[float] = []
    while stack:
        current = stack.pop()
        if isinstance(current, (list, tuple)):
            stack.extend(reversed(list(current)))
            continue
        if _np is not None and isinstance(current, _np.ndarray):
            stack.extend(reversed(current.tolist()))
            continue
        try:
            result.append(float(current))
        except (TypeError, ValueError):
            continue
    result.reverse()
    return result

def _json_default(value: Any):
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (bool, int, float, str)):
        return value
    if _np is not None:
        if isinstance(value, _np.generic):
            return value.item()
        if isinstance(value, _np.ndarray):
            return [_json_default(item) for item in value.tolist()]
    if isinstance(value, (list, tuple, set)):
        return [_json_default(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_default(val) for key, val in value.items()}
    if hasattr(value, "__dict__"):
        try:
            return {key: _json_default(val) for key, val in value.__dict__.items()}
        except Exception:
            pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _coerce_to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    if _np is not None and isinstance(value, _np.ndarray):
        if value.size == 0:
            return None
        return _coerce_to_float(value.flatten()[-1])
    if isinstance(value, (list, tuple)):
        numeric = _numeric_sequence(value)
        if numeric:
            return float(numeric[-1])
        return None
    if hasattr(value, "item"):
        try:
            return float(value.item())
        except Exception:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _parse_date(value: str) -> date:
    text_value = str(value).strip()
    if not text_value:
        raise ValueError("Missing sowing date.")
    if text_value.isdigit() and len(text_value) == 8:
        parsed = datetime.strptime(text_value, "%Y%m%d").date()
    else:
        try:
            parsed = date.fromisoformat(text_value)
        except ValueError:
            for fmt in ("%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    parsed = datetime.strptime(text_value, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Unsupported date format: {value}")
    return date(GAME_BASE_YEAR, parsed.month, parsed.day)

def _resolve_amount(value: Any, presets: Dict[str, float], label: str) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text_value = str(value).strip()
    if not text_value:
        return 0.0
    try:
        return float(text_value)
    except ValueError:
        key = text_value.lower()
        if key in presets:
            return presets[key]
    raise ValueError(f"Unknown {label} option: {value}")

def _parse_payload(raw: str) -> Dict[str, Any]:
    content = raw.strip()
    if not content:
        raise ValueError("Empty payload")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        parts = [segment.strip() for segment in content.split(",")]
        if len(parts) != 4:
            raise ValueError("Expected date,fertilizer,irrigation,crop")
        sow_date, fertilizer, irrigation, crop = parts
        payload = {
            "date": sow_date,
            "fertilizer": fertilizer,
            "irrigation": irrigation,
            "crop": crop,
        }
    else:
        if not isinstance(payload, dict):
            raise ValueError("Payload JSON must be an object")
    return payload






def _summarize_weather(record: Any) -> Optional[str]:
    if record is None:
        return None
    if isinstance(record, str):
        return record
    if isinstance(record, dict):
        keys = ["DAY", "RAIN", "TMIN", "TAVG", "TMAX", "IRRAD", "ET0", "E0", "ES0"]
        parts = []
        for key in keys:
            if key in record:
                value = record[key]
                if isinstance(value, (int, float)):
                    parts.append(f"{key}={value:.2f}")
                else:
                    parts.append(f"{key}={value}")
        if not parts:
            parts = [json.dumps(record, default=_json_default)]
        return ", ".join(parts)
    try:
        return str(record)
    except Exception:
        return None



def _build_weather_payload(game: CropGame, day: date, state: Dict[str, Any]) -> Dict[str, Any]:
    current_weather = None
    if game.weather is not None:
        try:
            record = get_weather(game.lat, game.lon, day)
            current_weather = record
        except Exception:
            current_weather = None
    if current_weather is None and game.weather is not None:
        try:
            key = (game.weather.check_keydate(day), 0)
            container = game.weather.store.get(key)
            if container is not None:
                current_weather = container.__dict__
        except Exception:
            current_weather = None

    forecast = None
    if current_weather is not None:
        try:
            forecast = predict_weather(current_weather)
        except Exception:
            forecast = None

    summary = _summarize_weather(current_weather)
    try:
        current_json = json.dumps(current_weather, default=_json_default) if current_weather is not None else None
    except Exception:
        current_json = None

    return {
        "current_summary": summary,
        "current_json": current_json,
        "forecast": forecast or [],
    }

def _build_metrics(state: Dict[str, Any]) -> Dict[str, float]:
    soil_moisture = _coerce_to_float(state.get("SM")) or 0.0
    soil_n = _coerce_to_float(state.get("soil_n")) or 0.0
    yield_rate = _coerce_to_float(state.get("yield_rate") or state.get("TWSO") or state.get("TAGP") or state.get("biomass")) or 0.0
    return {"soil_moisture": float(soil_moisture), "soil_n": float(soil_n), "yield_rate": float(yield_rate)}


def simulate_game(payload: Dict[str, Any]) -> Dict[str, Any]:
    sowing_date = _parse_date(payload.get("date"))
    crop_name = str(payload.get("crop") or "wheat").strip() or "wheat"
    fertilizer_amount = _resolve_amount(payload.get("fertilizer"), FERTILIZER_PRESETS, "fertilizer")
    irrigation_amount = _resolve_amount(payload.get("irrigation"), IRRIGATION_PRESETS, "irrigation")
    irrigation_eff = payload.get("irrigation_efficiency")
    if irrigation_eff is None:
        irrigation_eff = 0.75
    else:
        irrigation_eff = max(0.0, min(1.0, float(irrigation_eff)))
    lat = float(payload.get("lat", DEFAULT_LAT))
    lon = float(payload.get("lon", DEFAULT_LON))
    elev = float(payload.get("elev", DEFAULT_ELEV))

    game = CropGame(lat=lat, lon=lon, elev=elev)
    game.plant(crop_name=crop_name, sowing_date=sowing_date)

    if irrigation_amount > 0.0:
        game.water(irrigation_amount, efficiency=irrigation_eff)
    if fertilizer_amount > 0.0:
        game.fertilize(fertilizer_amount)

    final_day = sowing_date
    final_state: Dict[str, float] = {}
    days_simulated = 0

    for _ in range(SIM_DAYS):
        day, state = game.tick()
        days_simulated += 1
        final_day = day
        final_state = state
        if game.model is not None and game.model.flag_terminate:
            break

    return {
        "crop": crop_name,
        "sowing_date": sowing_date.isoformat(),
        "days_simulated": days_simulated,
        "final_day": final_day.isoformat(),
        "fertilizer_applied": fertilizer_amount,
        "irrigation_applied": irrigation_amount,
        "final_state": final_state,
    }
    fertilizer_amount = _resolve_amount(payload.get("fertilizer"), FERTILIZER_PRESETS, "fertilizer")
    irrigation_amount = _resolve_amount(payload.get("irrigation"), IRRIGATION_PRESETS, "irrigation")
    irrigation_eff = payload.get("irrigation_efficiency")
    if irrigation_eff is None:
        irrigation_eff = 0.75
    else:
        irrigation_eff = max(0.0, min(1.0, float(irrigation_eff)))
    lat = float(payload.get("lat", DEFAULT_LAT))
    lon = float(payload.get("lon", DEFAULT_LON))
    elev = float(payload.get("elev", DEFAULT_ELEV))
    game = CropGame(lat=lat, lon=lon, elev=elev)
    game.plant(crop_name=crop_name, sowing_date=sowing_date)
    if irrigation_amount > 0.0:
        game.water(irrigation_amount, efficiency=irrigation_eff)
    if fertilizer_amount > 0.0:
        game.fertilize(fertilizer_amount)
    final_day = sowing_date
    final_state: Dict[str, float] = {}
    days_simulated = 0
    for _ in range(SIM_DAYS):
        day, state = game.tick()
        days_simulated += 1
        final_day = day
        final_state = state
        if game.model is not None and game.model.flag_terminate:
            break
    return {
        "crop": crop_name,
        "sowing_date": sowing_date.isoformat(),
        "days_simulated": days_simulated,
        "final_day": final_day.isoformat(),
        "fertilizer_applied": fertilizer_amount,
        "irrigation_applied": irrigation_amount,
        "final_state": final_state,
    }


def _handle_request(session: Dict[str, Any], raw: str) -> Dict[str, Any]:
    payload = _parse_payload(raw)
    action_value = payload.get("action")
    if action_value is None:
        raise ValueError("Missing 'action' field in request")
    action = str(action_value).lower()
    if action in {"init", "initialize", "reset"}:
        return _handle_init(session, payload)
    if action in {"tick", "step", "advance"}:
        steps = int(payload.get("steps") or 1)
        return _handle_tick(session, steps)
    if action in {"status", "state"}:
        return _handle_status(session)
    if action == "water":
        return _handle_water(session, payload)
    if action in {"fertilize", "fertilise"}:
        return _handle_fertilize(session, payload)
    if action == "simulate":
        return simulate_game(payload)
    raise ValueError(f"Unsupported action: {action}")



def _handle_init(session: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    date_value = payload.get("date")
    if not date_value:
        previous = session.get("payload") or {}
        date_value = previous.get("date") or session.get("sowing_date")
    if not date_value:
        raise ValueError("Missing sowing date in init payload")
    sowing_date = _parse_date(date_value)
    crop_name = str(payload.get("crop") or (session.get("payload") or {}).get("crop") or "wheat").strip() or "wheat"
    fertilizer_amount = _resolve_amount(payload.get("fertilizer"), FERTILIZER_PRESETS, "fertilizer")
    irrigation_amount = _resolve_amount(payload.get("irrigation"), IRRIGATION_PRESETS, "irrigation")
    irrigation_eff = payload.get("irrigation_efficiency")
    if irrigation_eff is None:
        irrigation_eff = 0.75
    else:
        irrigation_eff = max(0.0, min(1.0, float(irrigation_eff)))
    lat = float(payload.get("lat", DEFAULT_LAT))
    lon = float(payload.get("lon", DEFAULT_LON))
    elev = float(payload.get("elev", DEFAULT_ELEV))

    game = CropGame(lat=lat, lon=lon, elev=elev)
    game.plant(crop_name=crop_name, sowing_date=sowing_date)

    if irrigation_amount > 0.0:
        game.water(irrigation_amount, efficiency=irrigation_eff)
    if fertilizer_amount > 0.0:
        game.fertilize(fertilizer_amount)



    session.clear()
    cached_payload = dict(payload)
    cached_payload["date"] = sowing_date.isoformat()
    cached_payload["crop"] = crop_name
    session.update({
        "game": game,
        "ticks": 0,
        "payload": cached_payload,
        "sowing_date": sowing_date.isoformat(),
        "crop": crop_name,
    })

    return {"message": "initialized", "crop": crop_name, "sowing_date": sowing_date.isoformat(), "fertilizer_applied": fertilizer_amount, "irrigation_applied": irrigation_amount, "location": {"lat": lat, "lon": lon, "elev": elev}}


def _handle_tick(session: Dict[str, Any], steps: int) -> Dict[str, Any]:
    game: CropGame = session.get("game")
    if game is None:
        raise RuntimeError("Initialize the simulation before requesting ticks.")

    steps = max(1, int(steps))
    executed = 0
    last_day = None
    last_state: Dict[str, Any] = {}
    finished = False

    for _ in range(steps):
        day, state = game.tick()
        executed += 1
        session["ticks"] = session.get("ticks", 0) + 1
        last_day = day
        last_state = state
        finished = bool(game.model.flag_terminate if game.model is not None else False)
        if finished:
            break

    if last_day is None:
        raise RuntimeError("No ticks executed.")

    metrics = _build_metrics(last_state)
    weather = _build_weather_payload(game, last_day, last_state)
    return {
        "tick": session.get("ticks", 0),
        "steps": executed,
        "day": last_day.isoformat(),
        "state": last_state,
        "metrics": metrics,
        "finished": finished,
        "weather": weather,
    }




def _require_game(session: Dict[str, Any]) -> CropGame:
    game = session.get("game")
    if not isinstance(game, CropGame):
        raise RuntimeError("Initialize the simulation before sending actions.")
    return game




def _handle_water(session: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    game = _require_game(session)
    amount = payload.get("amount_cm")
    if amount is None:
        raise ValueError("Water action requires 'amount_cm' in centimetres.")
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("Water amount must be numeric in centimetres.")

    efficiency = payload.get("efficiency")
    if efficiency is None:
        eff_value = 0.75
    else:
        try:
            eff_value = float(efficiency)
        except (TypeError, ValueError):
            raise ValueError("Water efficiency must be numeric in [0,1].")
    eff_value = max(0.0, min(1.0, eff_value))

    when_value = payload.get("date") or payload.get("day") or payload.get("when")
    target_day = None
    if when_value:
        try:
            parsed = _parse_date(when_value)
        except ValueError:
            parsed = None
        if parsed is not None and game.current_day is not None and parsed < game.current_day:
            target_day = game.current_day
        else:
            target_day = parsed

    game.water(amount_value, when=target_day, efficiency=eff_value)

    auto_steps = payload.get("auto_steps")
    try:
        auto_steps_int = int(auto_steps) if auto_steps is not None else 1
    except (TypeError, ValueError):
        auto_steps_int = 1
    auto_steps_int = max(0, auto_steps_int)

    if auto_steps_int > 0:
        result = _handle_tick(session, auto_steps_int)
        if "weather" not in result:
            result["weather"] = _build_weather_payload(game, game._last_day or (game.current_day - timedelta(days=1) if game.current_day else day), state)
        result.update({
            "action": "water",
            "message": "water applied",
            "amount_cm": amount_value,
            "efficiency": eff_value,
        })
        return result

    state = game.get_state()
    metrics = _build_metrics(state)
    last_day = game._last_day or (game.current_day - timedelta(days=1) if game.current_day else None)
    day_str = last_day.isoformat() if last_day else datetime.utcnow().date().isoformat()

    return {
        "action": "water",
        "message": "water scheduled",
        "tick": session.get("ticks", 0),
        "steps": 0,
        "day": day_str,
        "state": state,
        "metrics": metrics,
        "weather": _build_weather_payload(game, last_day or day, state),
        "finished": bool(game.model.flag_terminate if game.model is not None else False),
        "amount_cm": amount_value,
        "efficiency": eff_value,
    }




def _handle_fertilize(session: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    game = _require_game(session)
    amount = payload.get("amount_kg_ha")
    if amount is None:
        raise ValueError("Fertilize action requires 'amount_kg_ha' in kilograms per hectare.")
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("Fertilizer amount must be numeric in kg/ha.")

    nh4_fraction = payload.get("nh4_fraction")
    if nh4_fraction is None:
        nh4_value = 0.7
    else:
        try:
            nh4_value = float(nh4_fraction)
        except (TypeError, ValueError):
            raise ValueError("nh4_fraction must be numeric in [0,1].")
    nh4_value = max(0.0, min(1.0, nh4_value))

    when_value = payload.get("date") or payload.get("day") or payload.get("when")
    target_day = None
    if when_value:
        try:
            parsed = _parse_date(when_value)
        except ValueError:
            parsed = None
        if parsed is not None and game.current_day is not None and parsed < game.current_day:
            target_day = game.current_day
        else:
            target_day = parsed

    game.fertilize(amount_value, when=target_day, nh4_fraction=nh4_value)

    auto_steps = payload.get("auto_steps")
    try:
        auto_steps_int = int(auto_steps) if auto_steps is not None else 1
    except (TypeError, ValueError):
        auto_steps_int = 1
    auto_steps_int = max(0, auto_steps_int)

    if auto_steps_int > 0:
        result = _handle_tick(session, auto_steps_int)
        if "weather" not in result:
            result["weather"] = _build_weather_payload(game, game._last_day or (game.current_day - timedelta(days=1) if game.current_day else day), state)
        result.update({
            "action": "fertilize",
            "message": "fertilizer applied",
            "amount_kg_ha": amount_value,
            "nh4_fraction": nh4_value,
        })
        return result

    state = game.get_state()
    metrics = _build_metrics(state)
    last_day = game._last_day or (game.current_day - timedelta(days=1) if game.current_day else None)
    day_str = last_day.isoformat() if last_day else datetime.utcnow().date().isoformat()

    return {
        "action": "fertilize",
        "message": "fertilizer scheduled",
        "tick": session.get("ticks", 0),
        "steps": 0,
        "day": day_str,
        "state": state,
        "metrics": metrics,
        "weather": _build_weather_payload(game, last_day or day, state),
        "finished": bool(game.model.flag_terminate if game.model is not None else False),
        "amount_kg_ha": amount_value,
        "nh4_fraction": nh4_value,
    }


def _handle_status(session: Dict[str, Any]) -> Dict[str, Any]:
    game: CropGame = session.get("game")
    if game is None:
        return {"initialized": False}

    state = game.get_state()
    metrics = _build_metrics(state)
    last_day = game._last_day or (game.current_day - timedelta(days=1) if game.current_day else datetime.utcnow().date())
    weather = _build_weather_payload(game, last_day, state)
    return {
        "initialized": True,
        "tick": session.get("ticks", 0),
        "state": state,
        "metrics": metrics,
        "weather": weather,
    }


def _handle_client(connection: socket.socket, address) -> None:
    print(f"Client connected: {address}")
    session: Dict[str, Any] = {"game": None, "ticks": 0}
    try:
        with connection:
            greeting = json.dumps({"ok": True, "message": "ready"}, default=_json_default) + "\n"
            connection.sendall(greeting.encode("utf-8"))
            print(f"Handshake to {address}: {greeting.strip()}", flush=True)
            buffer = b""
            while True:
                chunk = connection.recv(BUFFER_SIZE)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    raw = line.decode("utf-8").strip()
                    if not raw:
                        continue
                    print(f"Request from {address}: {raw}", flush=True)
                    try:
                        result = _handle_request(session, raw)
                        response = {"ok": True, "result": result}
                    except Exception as exc:
                        response = {"ok": False, "error": str(exc)}
                    payload = json.dumps(response, default=_json_default) + "\n"
                    connection.sendall(payload.encode("utf-8"))
                    print(f"Response to {address}: {payload}", flush=True)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"Unhandled error for {address}: {exc}", flush=True)
    finally:
        print(f"Client disconnected: {address}")

def serve_forever(host: str = HOST, port: int = PORT) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        print(f"Python crop server listening on {host}:{port}")
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=_handle_client, args=(conn, addr), daemon=True)
            thread.start()

if __name__ == "__main__":
    serve_forever()
