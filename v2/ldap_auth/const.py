"""Constants for ldap_auth."""

DOMAIN = "ldap_auth"

# Config keys
CONF_SERVER = "server"
CONF_HELPERDN = "helperdn"
CONF_HELPERPASS = "helperpass"
CONF_BASEDN = "basedn"
CONF_ATTRS = "attrs"
CONF_BASE_FILTER = "base_filter"
CONF_DISPLAY_ATTR = "display_attr"
CONF_TIMEOUT = "timeout"
CONF_VERIFY_SSL = "verify_ssl"
CONF_USE_STARTTLS = "use_starttls"

DEFAULT_TIMEOUT = 3
DEFAULT_ATTRS = "uid"
DEFAULT_BASE_FILTER = "(&(objectClass=person))"
DEFAULT_DISPLAY_ATTR = "displayName"
DEFAULT_VERIFY_SSL = True
DEFAULT_USE_STARTTLS = False

# Services / notifications
SERVICE_SHOW_SNIPPET = "show_auth_provider_snippet"
NOTIFICATION_ID = "ldap_auth_setup"
