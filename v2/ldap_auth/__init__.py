"""LDAP Auth Helper integration.

This integration provides:
- UI configuration (config entry + options) for LDAP parameters stored in .storage
- A helper service to show (and optionally write) the YAML include needed for the
  built-in `command_line` auth provider.

Note:
Home Assistant auth providers are configured at startup and are not extensible by custom
integrations. You must add the command_line auth provider in YAML once.
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.components import persistent_notification
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CCDPATH, SERVICE_SHOW_INCLUDE, NOTIFICATION_ID

_LOGGER = logging.getLogger(__name__)

INCLUDE_FILENAME = "auth_providers.yaml"
SERVICE_FILENAME = "auth.py"
COMMAND_FILEPATH = "/usr/bin/python3"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML (we don't use YAML for configuration, only for auth providers)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["entry_id"] = entry.entry_id

    async def _handle_show_include(call: ServiceCall) -> None:
        write_file = bool(call.data.get("write_file", True))
        python_cmd = str(call.data.get("python_command", COMMAND_FILEPATH))
        msg = _build_instructions(hass)

        if write_file:
            try:
                _write_include_file(hass)
                msg += f"\n\nInclude file written: {_config_path(hass)}/{INCLUDE_FILENAME}"
            except Exception as exc:  
                _LOGGER.warning("Failed writing auth_provider include file: %s", exc)
                msg += f"\n\nWarning: could not write {_config_path(hass)}/{INCLUDE_FILENAME}: {exc}"    
        persistent_notification.async_create(hass, msg, title="LDAP Integration Setup", notification_id=NOTIFICATION_ID,)

    # register configuration service
    hass.services.async_register(DOMAIN, SERVICE_SHOW_INCLUDE, _handle_show_include,)

    # write the include file so the user can simply add a one-line include.
    try:
        created = _write_include_file(hass)
    except Exception as exc:
        _LOGGER.debug("Could not write include file on setup: %s", exc)
        created = False

    # inform the user how to enable the provider if the file was created now.
    if created:
        persistent_notification.async_create(hass, _build_instructions(hass), title="LDAP Integration Setup", notification_id=NOTIFICATION_ID,)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if hass.services.has_service(DOMAIN, SERVICE_SHOW_INCLUDE):
        hass.services.async_remove(DOMAIN, SERVICE_SHOW_INCLUDE)
    return True


def _config_path(hass: HomeAssistant) -> Path:
    # hass.config.path() resolves against /config on HA OS/Green.
    return Path(hass.config.path())


def _write_include_file(hass: HomeAssistant) -> bool:
    """Write /config/auth_providers.yaml containing the auth_providers list."""
    cfg_dir = _config_path(hass)
    file_path = cfg_dir / INCLUDE_FILENAME
    if file_path.exists():
        return False
    script_path = Path(CCDPATH) / SERVICE_FILENAME
    content = (
        "- type: command_line\n"
        "  name: 'LDAP Authentication'\n"
        f"  command: {COMMAND_FILEPATH}\n"
        "  args:\n"
        f"    - {script_path}\n"
        "  meta: true\n"
        "- type: homeassistant\n"
    )
    file_path.write_text(content, encoding="utf-8")
    return True


def _build_instructions(hass: HomeAssistant) -> str:
    script_path = f"{CCDPATH}/{SERVICE_FILENAME}"
    include_file = f"{_config_path(hass)}/{INCLUDE_FILENAME}"
    return (
        "Home Assistant cannot add authentication providers automatically. To enable LDAP login, add ONE of the options below and restart:\n\n"
        "Option 1 (recommended): include a generated file (minimal YAML edit)\n"
        "homeassistant:\n"
        f"  auth_providers: !include {INCLUDE_FILENAME}\n\n"
        f"This integration writes the include file to: {include_file}\n\n"
        "Option 2 (manual config): inline configuration, in case you want to combine it with your custom providers\n"
        "homeassistant:\n"
        "  auth_providers:\n"
        "    - type: command_line\n"
        "       name: 'LDAP Authentication'\n"
        f"      command: {COMMAND_FILEPATH}\n"
        "      args:\n"
        f"        - {script_path}\n"
        "      meta: true\n"
        "    - type: homeassistant\n\n"
        "After restart, you can log in using LDAP credentials. "
        "If the python command path is different on your system, adjust it accordingly."
    )
