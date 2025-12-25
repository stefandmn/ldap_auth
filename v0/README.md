# ldap_auth (python_scrips )

This package is designed for **Home Assistant OS / Green / Supervised / Container** setups that uses the built-in
**command_line authentication provider**.

Home Assistant executes a shell command to validate credentials. It passes two environment variables:
`username` and `password`. Access is granted when the command exits with code `0`.

This simple integration provides:
- a stable file location for the auth script: `/config/python_scripts/ldap_auth/auth.py` (includes all dependecies)
- configuration for the provider and for ldap server directly within `configuration.yaml` - see it below.

## Installation

1. Copy the folder `python_scripts/ldap_auth/` into your Home Assistant config directory:
   `/config/python_scripts/ldap_auth/`

2. Restart Home Assistant.

## Configuration (configuration.yaml)

Add **both** blocks:

```yaml
homeassistant:
  auth_providers:
    - type: command_line
      command: /usr/bin/python3
      args:
        - /config/python_scripts/ldap_auth/auth.py
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
- If your Python path differs (in case you have a custom HAS setup), adjust the `command` field accordingly.
- in case you have additional providers like `trusted_networks` you can add them before or after, 
  depending by your needs
- configure LDAP connections and related details (it was tested for standard LDAP server like ApacheDS)
  but can be adapted for Active Directory also.
