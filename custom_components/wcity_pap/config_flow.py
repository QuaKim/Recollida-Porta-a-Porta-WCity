import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from .const import DOMAIN, POBLACIONES, CONF_POBLACION

_LOGGER = logging.getLogger(__name__)

# Token fresco de sesión actual
LOGIN_TOKEN = "MjJkOGU2NTM5MDBkZTIyYjFhZjY2ZmE4ZDVhNTZkY2U3ZDhiODg0OGFkOGI1ZWFjZDdjOWVkY2MwYmMwMWMzMQ=="

class InvalidAuth(Exception):
    """Excepción lanzada cuando las credenciales son incorrectas."""
    pass

async def async_validate_input(data: dict) -> dict:
    """Valida las credenciales realizando el login para la población seleccionada."""
    poblacion_key = data[CONF_POBLACION]
    subdomain = POBLACIONES[poblacion_key]["subdomain"]
    url_base = f"https://{subdomain}.wcity.app"
    
    url_login = f"{url_base}/modules/WCITY/api/v1/login?token={LOGIN_TOKEN}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.1",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{url_base}/",
    }
    
    jar = aiohttp.CookieJar(unsafe=True)
    
    async with aiohttp.ClientSession(headers=headers, cookie_jar=jar) as session:
        async with session.get(f"{url_base}/", timeout=10) as resp_init:
            if resp_init.status != 200:
                _LOGGER.error("Error al acceder a la web base: %s", resp_init.status)
                raise InvalidAuth

        payload = {
            "user": data[CONF_USERNAME],
            "passwd": data[CONF_PASSWORD],
            "lang": "ca",
            "token": LOGIN_TOKEN,
        }
        
        async with session.post(url_login, json=payload, timeout=15) as resp:
            if resp.status != 200:
                _LOGGER.error("Error HTTP al hacer login: %s", resp.status)
                raise InvalidAuth

            json_data = await resp.json(content_type=None)
            
            if not isinstance(json_data, dict) or json_data.get("result") != "OK":
                _LOGGER.error("Respuesta de login no válida: %s", json_data)
                raise InvalidAuth

    return {"title": POBLACIONES[poblacion_key]["name"]}

class ObreLaPortaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input[CONF_USERNAME] = user_input[CONF_USERNAME].strip()
            user_input[CONF_PASSWORD] = user_input[CONF_PASSWORD].strip()

            try:
                info = await async_validate_input(user_input)
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_POBLACION: user_input[CONF_POBLACION],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Error inesperado conectando con Wcity")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_POBLACION, default="obrelaporta"): vol.In(
                    {k: v["name"] for k, v in POBLACIONES.items()}
                ),
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )
