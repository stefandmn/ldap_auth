# LDAP Auth (command_line) helper

This custom integration provides a UI to store LDAP parameters (in `.storage`) and a helper script used by
Home Assistant's built-in `command_line` auth provider.

## What you get
- Configure LDAP settings in the UI: Settings → Devices & services → Add integration → **LDAP Auth**
- The auth script lives at: `/config/custom_components/ldap_auth/auth.py`
- A service to show the YAML snippet and (optionally) write an include file:
  - `ldap_auth.show_auth_provider_snippet`

## Enabling LDAP login (one-time YAML step)
Home Assistant does not allow integrations to register auth providers dynamically. Add one of the following to
`configuration.yaml` and restart.

**Option 1 (recommended): include file**
```yaml
homeassistant:
  auth_providers: !include ldap_auth_providers.yaml
```

The integration writes `/config/ldap_auth_providers.yaml` file.

**Option 2: inline**
```yaml
homeassistant:
  auth_providers:
    - type: command_line
      command: /usr/bin/python3
      args:
        - /config/custom_components/ldap_auth/auth.py
      meta: true
    - type: homeassistant
```

Adjust the python command path if needed.
