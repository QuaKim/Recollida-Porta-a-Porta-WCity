import logging
import aiohttp
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import URL_BASE, CONF_USERNAME, CONF_PASSWORD

_LOGGER = logging.getLogger(__name__)

LOGIN_TOKEN = "NzMwMDA0ZjFjOGMyMGIyOGJkOWM1Njc2NmZmZDIxYzBkYmQzM2M3NGZhNjQwZGRlODUzZWJjMzZmNDlhMWI0Mw=="
TOKEN_PWA = "NzMwMDA0ZjFjOGMyMGIyOGJkOWM1Njc2NmZmZDIxYzBkYmQzM2M3NGZhNjQwZGRlODUzZWJjMzZmNDlhMWI0Mw=="

class WCityCoordinator(DataUpdateCoordinator):
    """Coordinador para gestionar la sesión y recopilar los datos de WCity."""

    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name="WCity", update_interval=timedelta(hours=4))
        self.entry = entry
        self.session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        self.logged_in = False

    async def _async_login(self) -> bool:
        """Realiza el login si aún no se ha hecho."""
        if self.logged_in:
            return True

        username = self.entry.data.get(CONF_USERNAME)
        password = self.entry.data.get(CONF_PASSWORD)
        url_login = f"{URL_BASE}/modules/WCITY/api/v1/login?token={LOGIN_TOKEN}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.1",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{URL_BASE}/",
        }

        payload = {
            "user": username,
            "passwd": password,
            "lang": "ca",
            "token": LOGIN_TOKEN,
        }

        try:
            async with self.session.get(f"{URL_BASE}/", timeout=10) as resp_init:
                if resp_init.status != 200:
                    return False

            async with self.session.post(url_login, json=payload, headers=headers, timeout=15) as resp:
                data = await resp.json(content_type=None)
                if isinstance(data, dict) and data.get("result") == "OK":
                    self.logged_id = True
                    self.logged_in = True
                    return True
        except Exception as e:
            _LOGGER.error("Excepción en login del coordinador: %s", e)
            
        return False

    async def _async_update_data(self):
        """Descarga los datos usando las cabeceras y TOKEN_PWA originales."""
        if not await self._async_login():
            return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 OPR/133.0.0.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
            "X-TOKEN": TOKEN_PWA,
            "X-LANG": "ca",
            "Content-Type": "text/plain",
            "Referer": f"{URL_BASE}/",
        }

        try:
            # 1. Obtener datos de sector
            async with self.session.get(f"{URL_BASE}/modules/WCITY/api/v1/sector", headers=headers, timeout=15) as resp_sector:
                sector_data = await resp_sector.json(content_type=None) if resp_sector.status == 200 else None

            # 2. Obtener datos de calendario
            async with self.session.get(f"{URL_BASE}/modules/WCITY/api/v1/sector/calendari?que=mes", headers=headers, timeout=15) as resp_cal:
                calendari_data = await resp_cal.json(content_type=None) if resp_cal.status == 200 else None

            return {
                "sector": sector_data,
                "calendari": calendari_data,
            }

        except Exception as e:
            _LOGGER.error("Error al actualizar datos en coordinador: %s", e)
            return None
