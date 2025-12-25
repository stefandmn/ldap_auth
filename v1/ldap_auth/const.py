"""Constants for ldap_auth."""

DOMAIN = "ldap_auth"

CONF_SERVER = "server"
CONF_HELPERDN = "helperdn"
CONF_HELPERPASS = "helperpass"
CONF_BASEDN = "basedn"
CONF_ATTRS = "attrs"
CONF_BASE_FILTER = "base_filter"
CONF_DISPLAY_ATTR = "display_attr"
CONF_TIMEOUT = "timeout"

DEFAULT_TIMEOUT = 3
DEFAULT_ATTRS = "uid"
DEFAULT_BASE_FILTER = "(&(objectClass=person))"
DEFAULT_DISPLAY_ATTR = "displayName"
