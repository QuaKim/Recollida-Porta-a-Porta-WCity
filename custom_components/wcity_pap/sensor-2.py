import logging
from homeassistant.components.sensor import SensorEntity
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
    async_add_entities([ObreLaPortaHoySensor(coordinator, entry)], update_before_add=True)

class ObreLaPortaHoySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        
        # unique_id único combinando población y usuario para evitar duplicados
        poblacion_key = entry.data.get(CONF_POBLACION, "obrelaporta")
        username = entry.data.get(CONF_USERNAME, "")
        
        self._attr_name = "Basura Hoy"
        self._attr_unique_id = f"{poblacion_key}_{username}_basura_hoy"
        self._attr_icon = "mdi:trash-can"
        self._attr_translation_key = "basura_hoy"

    @property
    def native_value(self) -> str:
        data = self.coordinator.data
        if not data or not isinstance(data, dict):
            return "Error de datos"

        json_sector = data.get("sector")
        if isinstance(json_sector, dict) and json_sector.get("result") == "OK":
            rec_data = json_sector.get("data", {})
            recollides = rec_data.get("recollides", [])

            if recollides:
                nombres = [item.get("desc") for item in recollides if item.get("desc")]
                return ", ".join(nombres) if nombres else "Ninguna"
            else:
                return "Sin recogida hoy"
        return "Error API Sector"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        if data and isinstance(data, dict):
            json_sector = data.get("sector")
            if isinstance(json_sector, dict) and json_sector.get("result") == "OK":
                rec_data = json_sector.get("data", {})
                recollides = rec_data.get("recollides", [])
                return {
                    "recollides_detall": recollides,
                    "total_recogidas_hoy": len(recollides),
                }
        return {"recollides_detall": []}