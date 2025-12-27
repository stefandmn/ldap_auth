"""Config flow for ldap_auth.

Stores LDAP parameters in config entries (.storage) so they can be edited in the UI.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

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
    CONF_VERIFY_SSL,
    CONF_USE_STARTTLS,
    DEFAULT_TIMEOUT,
    DEFAULT_ATTRS,
    DEFAULT_BASE_FILTER,
    DEFAULT_DISPLAY_ATTR,
    DEFAULT_VERIFY_SSL,
    DEFAULT_USE_STARTTLS,
)


def _schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SERVER, default=defaults.get(CONF_SERVER, "")): str,
            vol.Optional(CONF_HELPERDN, default=defaults.get(CONF_HELPERDN, "")): str,
            vol.Optional(CONF_HELPERPASS, default=defaults.get(CONF_HELPERPASS, "")): str,
            vol.Required(CONF_BASEDN, default=defaults.get(CONF_BASEDN, "")): str,
            vol.Optional(CONF_ATTRS, default=defaults.get(CONF_ATTRS, DEFAULT_ATTRS)): str,
            vol.Optional(CONF_BASE_FILTER, default=defaults.get(CONF_BASE_FILTER, DEFAULT_BASE_FILTER)): str,
            vol.Optional(CONF_DISPLAY_ATTR, default=defaults.get(CONF_DISPLAY_ATTR, DEFAULT_DISPLAY_ATTR)): str,
            vol.Optional(CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): vol.Coerce(int),
            vol.Optional(CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)): bool,
            vol.Optional(CONF_USE_STARTTLS, default=defaults.get(CONF_USE_STARTTLS, DEFAULT_USE_STARTTLS)): bool,
        }
    )


class LdapAuthConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        if user_input is not None:
            # Store everything as data; options flow will allow edits too.
            return self.async_create_entry(title="LDAP Auth", data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema({}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return LdapAuthOptionsFlow(config_entry)


class LdapAuthOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        defaults = dict(self._config_entry.data)
        defaults.update(self._config_entry.options or {})
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=_schema(defaults), errors=errors)
