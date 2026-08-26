import logging
import aiohttp
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_change
from .const import POBLACIONES, CONF_USERNAME, CONF_PASSWORD, CONF_POBLACION

_LOGGER = logging.getLogger(__name__)

LOGIN_TOKEN = "MjJkOGU2NTM5MDBkZTIyYjFhZjY2ZmE4ZDVhNTZkY2U3ZDhiODg0OGFkOGI1ZWFjZDdjOWVkY2MwYmMwMWMzMQ=="
TOKEN_PWA = "MjJkOGU2NTM5MDBkZTIyYjFhZjY2ZmE4ZDVhNTZkY2U3ZDhiODg0OGFkOGI1ZWFjZDdjOWVkY2MwYmMwMWMzMQ=="

class WCityCoordinator(DataUpdateCoordinator):
    """Coordinador para gestionar la sesión multi-población de WCity."""

    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name="WCity", update_interval=None)
        self.entry = entry
        self.session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        self.logged_in = False

        # Obtener la URL base correspondiente según la población elegida al configurar
        poblacion_key = self.entry.data.get(CONF_POBLACION, "obrelaporta")
        subdomain = POBLACIONES.get(poblacion_key, POBLACIONES["obrelaporta"])["subdomain"]
        self.url_base = f"https://{subdomain}.wcity.app"

        # Programar actualización automática todos los días a las 00:30
        async_track_time_change(self.hass, self._update_at_scheduled_time, hour=0, minute=30, second=0)

    async def _update_at_scheduled_time(self, now):
        """Ejecuta la actualización a las 00:30."""
        await self.async_request_refresh()

    async def _async_login(self) -> bool:
        """Realiza el login contra el subdominio configurado."""
        if self.logged_in:
            return True

        username = self.entry.data.get(CONF_USERNAME)
        password = self.entry.data.get(CONF_PASSWORD)
        url_login = f"{self.url_base}/modules/WCITY/api/v1/login?token={LOGIN_TOKEN}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.1",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.url_base}/",
        }

        payload = {
            "user": username,
            "passwd": password,
            "lang": "ca",
            "token": LOGIN_TOKEN,
        }

        try:
            async with self.session.get(f"{self.url_base}/", timeout=10) as resp_init:
                if resp_init.status != 200:
                    return False

            async with self.session.post(url_login, json=payload, headers=headers, timeout=15) as resp:
                data = await resp.json(content_type=None)
                if isinstance(data, dict) and data.get("result") == "OK":
                    self.logged_in = True
                    return True
        except Exception as e:
            _LOGGER.error("Excepción en login del coordinador: %s", e)
            
        return False

    async def _async_update_data(self):
        """Descarga los datos usando la URL base y cabeceras correspondientes."""
        
        # --- AÑADE ESTAS LÍNEAS PARA DEPURAR ---
        poblacion_key = self.entry.data.get(CONF_POBLACION, "obrelaporta")
        _LOGGER.error(">>> ACTUALIZANDO COORDINADOR PARA LA POBLACIÓN: %s (URL: %s)", poblacion_key, self.url_base)
        # ---------------------------------------

        if not await self._async_login():
            return None

#    async def _async_update_data(self):
#        """Descarga los datos usando la URL base y cabeceras correspondientes."""
#        if not await self._async_login():
#            return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
            "X-TOKEN": TOKEN_PWA,
            "X-LANG": "ca",
            "Content-Type": "text/plain",
            "Referer": f"{self.url_base}/",
        }

        try:
            # 1. Obtener datos de sector
            async with self.session.get(f"{self.url_base}/modules/WCITY/api/v1/sector", headers=headers, timeout=15) as resp_sector:
                sector_data = await resp_sector.json(content_type=None) if resp_sector.status == 200 else None

            # 2. Obtener datos de calendario
            async with self.session.get(f"{self.url_base}/modules/WCITY/api/v1/sector/calendari?que=mes", headers=headers, timeout=15) as resp_cal:
                calendari_data = await resp_cal.json(content_type=None) if resp_cal.status == 200 else None

            return {
                "sector": sector_data,
                "calendari": calendari_data,
            }

        except Exception as e:
            _LOGGER.error("Error al actualizar datos en coordinador: %s", e)
            return None