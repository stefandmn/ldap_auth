"""ldap_auth custom integration.

This integration is a lightweight helper to:
- validate/store LDAP configuration in Home Assistant
- ensure the python dependency 'ldap3' is installed (via manifest requirements)
- provide an on-disk location for the command_line auth script:
  /config/custom_components/ldap_auth/auth.py
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_SERVER,
    CONF_HELPERDN,
    CONF_HELPERPASS,
    CONF_BASEDN,
    CONF_ATTRS,
    CONF_BASE_FILTER,
    CONF_DISPLAY_ATTR,
    CONF_TIMEOUT,
    DEFAULT_TIMEOUT,
    DEFAULT_ATTRS,
    DEFAULT_BASE_FILTER,
    DEFAULT_DISPLAY_ATTR,
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_SERVER): cv.string,
                vol.Required(CONF_HELPERDN): cv.string,
                vol.Required(CONF_HELPERPASS): cv.string,
                vol.Required(CONF_BASEDN): cv.string,
                vol.Optional(CONF_ATTRS, default=DEFAULT_ATTRS): cv.string,
                vol.Optional(CONF_BASE_FILTER, default=DEFAULT_BASE_FILTER): cv.string,
                vol.Optional(CONF_DISPLAY_ATTR, default=DEFAULT_DISPLAY_ATTR): cv.string,
                vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(int),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the ldap_auth domain from YAML."""
    hass.data[DOMAIN] = config.get(DOMAIN, {})
    return True
