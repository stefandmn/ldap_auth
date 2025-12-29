"""LDAP Auth Helper integration.

This integration provides:
- UI configuration (config entry + options) for LDAP parameters stored in .storage
- A helper service to show (and optionally write) the YAML snippet needed for the
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

from .const import DOMAIN, SERVICE_SHOW_SNIPPET, NOTIFICATION_ID

_LOGGER = logging.getLogger(__name__)

SNIPPET_FILENAME = "ldap_auth_providers.yaml"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML (we don't use YAML for configuration, only for auth providers)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["entry_id"] = entry.entry_id

    async def _handle_show_snippet(call: ServiceCall) -> None:
        write_file = bool(call.data.get("write_file", True))
        python_cmd = str(call.data.get("python_command", "/usr/bin/python3"))
        msg = _build_auth_provider_instructions(python_cmd=python_cmd)

        if write_file:
            try:
                _write_snippet_file(hass, python_cmd=python_cmd)
                msg += f"\n\nSnippet file written: /config/{SNIPPET_FILENAME}"
            except Exception as exc:  
                _LOGGER.warning("Failed writing snippet include file: %s", exc)
                msg += f"\n\nWarning: could not write /config/{SNIPPET_FILENAME}: {exc}"

        persistent_notification.async_create(hass, msg, title="LDAP Auth Setup", notification_id=NOTIFICATION_ID,)

    hass.services.async_register(DOMAIN, SERVICE_SHOW_SNIPPET, _handle_show_snippet,)

    # Best-effort: write the include file so the user can simply add a one-line include.
    try:
        _write_snippet_file(hass, python_cmd="/usr/bin/python3")
    except Exception as exc:
        _LOGGER.debug("Could not write snippet include file on setup: %s", exc)

    # Always inform the user how to enable the provider.
    persistent_notification.async_create(hass, _build_auth_provider_instructions(python_cmd="/usr/bin/python3"), title="LDAP Auth Setup", notification_id=NOTIFICATION_ID,)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if hass.services.has_service(DOMAIN, SERVICE_SHOW_SNIPPET):
        hass.services.async_remove(DOMAIN, SERVICE_SHOW_SNIPPET)
    return True


def _config_path(hass: HomeAssistant) -> Path:
    # hass.config.path() resolves against /config on HA OS/Green.
    return Path(hass.config.path())


def _write_snippet_file(hass: HomeAssistant, *, python_cmd: str) -> None:
    """Write /config/ldap_auth_providers.yaml containing the auth_providers list."""
    cfg_dir = _config_path(hass)
    file_path = cfg_dir / SNIPPET_FILENAME
    script_path = "/config/custom_components/ldap_auth/auth.py"
    content = (
        "- type: command_line\n"
        "  name: 'LDAP Authentication'\n"
        f"  command: {python_cmd}\n"
        "  args:\n"
        f"    - {script_path}\n"
        "  meta: true\n"
        "- type: homeassistant\n"
    )
    file_path.write_text(content, encoding="utf-8")


def _build_auth_provider_instructions(*, python_cmd: str) -> str:
    script_path = "/config/custom_components/ldap_auth/auth.py"
    include_file = f"/config/{SNIPPET_FILENAME}"
    return (
        "Home Assistant cannot add authentication providers automatically. To enable LDAP login, add ONE of the options below and restart:\n\n"
        "Option 1 (recommended): include a generated file (minimal YAML edit)\n"
        "homeassistant:\n"
        f"  auth_providers: !include {SNIPPET_FILENAME}\n\n"
        f"This integration writes the include file to: {include_file}\n\n"
        "Option 2: inline configuration\n"
        "homeassistant:\n"
        "  auth_providers:\n"
        "    - type: command_line\n"
        "       name: 'LDAP Authentication'\n"
        f"      command: {python_cmd}\n"
        "      args:\n"
        f"        - {script_path}\n"
        "      meta: true\n"
        "    - type: homeassistant\n\n"
        "After restart, you can log in using LDAP credentials. "
        "If the python command path is different on your system, adjust it accordingly."
    )
