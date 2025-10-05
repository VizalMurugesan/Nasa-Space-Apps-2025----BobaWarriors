from __future__ import annotations

from datetime import date, timedelta
from difflib import get_close_matches
from typing import Callable, Dict, List, Optional, Tuple

from pcse import signals
from pcse.base import ParameterProvider, WeatherDataContainer, WeatherDataProvider
from pcse.input import WOFOST81SiteDataProvider_SNOMIN, YAMLCropDataProvider
from pcse.models import Wofost81_NWLP_MLWB_SNOMIN

from data import get_soil_profile, get_site_parameters, get_weather

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

    def get_state(self) -> Dict[str, float]:
        if self.model is None:
            return {}
        variables = ["DVS", "LAI", "SM", "TAGP", "TWSO", "TRA", "EVS"]
        state: Dict[str, float] = {}
        for name in variables:
            try:
                value = self.model.get_variable(name)
            except Exception:
                value = None
            if value is not None:
                state[name] = value
        if "TAGP" in state:
            state["biomass"] = state["TAGP"]
        return state


if __name__ == "__main__":
    demo = CropGame(lat=49.104, lon=-122.66, elev=36.0)
    # Sow date and seeds should be from the user
    demo.plant(crop_name="wheat", sowing_date=date(2025, 5, 1))

    print("First week:")
    for _ in range(7):
        day, state = demo.tick()
        print(day, state)

    demo.water(2.0)
    demo.fertilize(40.0, nh4_fraction=0.6)

    print("\nAfter irrigation and fertiliser:")
    for _ in range(240):
        day, state = demo.tick()
        print(day, state)
