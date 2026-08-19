import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import WCityCoordinator

_LOGGER = logging.getLogger(__name__)

# Definimos las plataformas que soporta la integración
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.CALENDAR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura la integración a partir de una entrada."""
    _LOGGER.debug("Cargando coordinador y plataformas para Obre la Porta")
    
    # Inicializamos el coordinador y lo guardamos en hass.data
    coordinator = WCityCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    # Carga las entidades de sensor.py y calendar.py
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarga las plataformas cuando se elimina o recarga la integración."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
