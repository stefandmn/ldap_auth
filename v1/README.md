# ldap_auth (custom integration + command_line auth helper)

This package is intended for **Home Assistant OS / Green / Supervised / Container** setups that use the built-in
**command_line authentication provider**.

Home Assistant executes a shell command to validate credentials. It passes two environment variables:
`username` and `password`. Access is granted when the command exits with code `0`.

This custom integration provides:
- a stable file location for the helper script: `/config/custom_components/ldap_auth/auth.py`
- automatic installation of the `ldap3` Python dependency via `manifest.json` (custom integrations must include
  a `version` key).

## Installation

1. Copy the folder `custom_components/ldap_auth/` into your Home Assistant config directory:
   `/config/custom_components/ldap_auth/`

2. Restart Home Assistant.

## Configuration (configuration.yaml)

Add **both** blocks:

```yaml
homeassistant:
  auth_providers:
    - type: command_line
      command: /usr/bin/python3
      args:
        - /config/custom_components/ldap_auth/auth.py
      meta: true
    - type: homeassistant

ldap_auth:
  server: "ldaps://example.com:636"
  helperdn: "uid=integration,cn=users,dc=example,dc=com"
  helperpass: "REPLACE_ME"
  basedn: "dc=example,dc=com"
  attrs: "uid"
  base_filter: "(&(objectClass=person))"
  display_attr: "displayName"
  timeout: 3
```

Notes:
- `meta: true` enables returning display metadata (this script outputs `name = ...`).
- If your Python path differs, adjust the `command` field accordingly.

## Optional environment overrides

- `HASS_CONFIG`: override the config directory (default `/config`)
- `LDAP_AUTH_CONFIG`: override the full path to the YAML file to read (default `$HASS_CONFIG/configuration.yaml`)
