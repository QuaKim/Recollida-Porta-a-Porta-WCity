import logging
from datetime import datetime, date, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_POBLACION, CONF_USERNAME

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ObreLaPortaCalendar(coordinator, entry)], update_before_add=True)

class ObreLaPortaCalendar(CoordinatorEntity, CalendarEntity):
    """Entidad de Calendario para Wcity usando el coordinador."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        
        # unique_id único combinando población y usuario para evitar duplicados
        poblacion_key = entry.data.get(CONF_POBLACION, "obrelaporta")
        username = entry.data.get(CONF_USERNAME, "")
        
        self._attr_unique_id = f"{poblacion_key}_{username}_calendar"
        
        # Nombre dinámico personalizado incluyendo la población en mayúsculas (ej: ObrelaPorta, Girones)
        poblacion_nombre = poblacion_key.replace("_", " ").title()
        self._attr_name = f"Calendario Recogida {poblacion_nombre}"
        
        # Eliminamos la clave de traducción fija para que respete este nombre personalizado por ciudad
        # self._attr_translation_key = "calendar"

    def _parse_event_date(self, key_date: str) -> date | None:
        if not key_date or str(key_date).startswith("0000"):
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(str(key_date).strip(), fmt).date()
            except (ValueError, TypeError):
                continue
        return None

    def _extract_residuos(self, day_info: dict, tipus_recollides: dict) -> list[str]:
        residuos = []
        if not isinstance(day_info, dict):
            return residuos

        for key in ("types", "tipus", "residuos", "recollides", "fraccions", "items", "tipus_rec"):
            val = day_info.get(key)
            if val:
                lista = list(val.values()) if isinstance(val, dict) else (val if isinstance(val, list) else [val])
                for item in lista:
                    if isinstance(item, dict):
                        nom = item.get("desc") or item.get("nom") or item.get("description")
                        if nom:
                            residuos.append(str(nom).strip())
                    elif isinstance(item, (str, int)):
                        str_id = str(item).strip()
                        if str_id in tipus_recollides:
                            t_info = tipus_recollides[str_id]
                            nom = t_info.get("desc") or t_info.get("nom") if isinstance(t_info, dict) else t_info
                            residuos.append(str(nom).strip())
                        else:
                            residuos.append(str_id)

        if not residuos:
            for k, v in day_info.items():
                if k in ("dia_setmana", "date", "today", "t1", "t2"):
                    continue
                str_val = str(v).strip() if v is not None else ""
                str_k = str(k).strip()

                if str_val in tipus_recollides:
                    t_info = tipus_recollides[str_val]
                    nom = t_info.get("desc") or t_info.get("nom") if isinstance(t_info, dict) else t_info
                    residuos.append(str(nom).strip())
                elif str_k in tipus_recollides:
                    t_info = tipus_recollides[str_k]
                    nom = t_info.get("desc") or t_info.get("nom") if isinstance(t_info, dict) else t_info
                    residuos.append(str(nom).strip())

        return list(set(residuos))

    @property
    def event(self) -> CalendarEvent | None:
        data = self.coordinator.data
        if not data or not isinstance(data, dict):
            return None

        cal_json = data.get("calendari")
        if not isinstance(cal_json, dict) or cal_json.get("result") != "OK":
            return None

        data_content = cal_json.get("data", {})
        dates_data = data_content.get("dates", {})
        tipus_recollides = data_content.get("tipus_recollides", {})

        today_date = date.today()
        for key_date, day_info in dates_data.items():
            event_date = self._parse_event_date(key_date)
            if event_date == today_date:
                residuos = self._extract_residuos(day_info, tipus_recollides)
                if residuos:
                    return CalendarEvent(
                        start=today_date,
                        end=today_date + timedelta(days=1),
                        summary=f"Recogida: {', '.join(residuos)}",
                        description=f"Día: {day_info.get('dia_setmana', '') if isinstance(day_info, dict) else ''}",
                    )
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        events = []
        data = self.coordinator.data
        if not data or not isinstance(data, dict):
            return events

        cal_json = data.get("calendari")
        if not isinstance(cal_json, dict) or cal_json.get("result") != "OK":
            return events

        data_content = cal_json.get("data", {})
        dates_data = data_content.get("dates", {})
        tipus_recollides = data_content.get("tipus_recollides", {})

        start_d = start_date.date() if isinstance(start_date, datetime) else start_date
        end_d = end_date.date() if isinstance(end_date, datetime) else end_d

        for key_date, day_info in dates_data.items():
            event_date = self._parse_event_date(key_date)
            if not event_date:
                continue

            if start_d <= event_date <= end_d:
                residuos = self._extract_residuos(day_info, tipus_recollides)
                dia_semana = day_info.get("dia_setmana", "") if isinstance(day_info, dict) else ""

                if residuos:
                    for residuo in residuos:
                        events.append(
                            CalendarEvent(
                                start=event_date,
                                end=event_date + timedelta(days=1),
                                summary=f"Recogida: {residuo}",
                                description=f"Fracción: {residuo} | Día: {dia_semana}",
                            )
                        )
        return events
