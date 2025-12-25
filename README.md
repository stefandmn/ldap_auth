# Home Assistant LDAP Auth – Options (v0 / v1 / v2)

This repository contains three packaged variants of the same goal: allow Home Assistant to authenticate users against LDAP using the built-in **command_line** auth provider (which executes an external script and interprets the exit code).

Because Home Assistant loads `auth_providers` at startup and does not expose a supported API for integrations to modify authentication configuration, **enabling the provider still requires a one-time YAML configuration step** (either inline or via `!include`). LDAP connection parameters can be managed either in YAML (v0/v1) or via UI config flow and `.storage` (v2).

## Compatibility

- Target: Home Assistant Green / HA OS / Container deployments
- Auth mechanism: Home Assistant `command_line` auth provider executing a Python script
- LDAP library: typically `ldap3` (bundled or installed depending on version)

---

# Version Overview

## v0 – Standalone Script + YAML Parameters
**Intent:** simplest deployment; a script reads LDAP parameters from `configuration.yaml` and is called by the `command_line` auth provider.

### What you get
- A standalone `auth.py` intended to be referenced directly from `configuration.yaml`
- LDAP settings read from the `ldap_auth:` YAML section
- It includes a bundled all dependencies, ainly containing `ldap3` and related dependencies.

### Pros
- Very easy to understand and debug
- No Home Assistant integration packaging required

### Cons
- Not a “real” custom integration (no `manifest.json`, no UI)
- Config changes are YAML-only

### Typical setup
1. Copy the `v0/ldap_auth` folder into `/config/python-scripts` (or a subfolder you control)
2. Add the command_line auth provider to `configuration.yaml`
3. Add the `ldap_auth:` configuration block to `configuration.yaml`
4. Restart Home Assistant

---

## v1 – Custom Integration (YAML-configured)
**Intent:** package the solution as a proper custom integration under `custom_components/`, while still keeping LDAP parameters in YAML.

### What you get
- A Home Assistant custom integration directory (domain folder under `custom_components/`)
- `manifest.json` present (integration is discoverable by HA)
- `auth.py` lives inside the integration folder
- LDAP settings still read from `configuration.yaml` (`ldap_auth:` section)

### Pros
- Clean packaging under `custom_components/`
- Easier upgrades/rollbacks than a loose script
- More “Home Assistant-native” structure

### Cons
- LDAP parameters are still YAML-only (no UI)
- `auth_providers` still requires manual YAML configuration

### Typical setup
1. Copy `v1/custom_components/<domain>` to `/config/custom_components/<domain>`
2. Add the command_line auth provider block in `configuration.yaml` (pointing to the `auth.py` path)
3. Add/maintain the LDAP YAML configuration section
4. Restart Home Assistant

---

## v2 – Custom Integration + UI Configuration + Include File Helper
**Intent:** move LDAP parameters out of YAML and into the Home Assistant UI (stored in `.storage`), while assisting the user by generating an include file for auth providers.

### What you get
- Custom integration with:
  - Config Flow (UI setup via Settings → Devices & services)
  - Options Flow (edit LDAP parameters in UI)
- LDAP settings stored in `.storage` (not `configuration.yaml`)
- Helper behavior: generates `/config/ldap_auth_providers.yaml` (or similarly named include file)
- Persistent notification and/or a service to show the required auth provider snippet

### Pros
- LDAP parameters are managed in UI (no YAML edits for LDAP settings)
- Cleaner configuration management and safer secrets handling
- Include-file generation reduces copy/paste errors

### Cons
- You still must add the `auth_providers` include (or snippet) to `configuration.yaml` once
- Auth provider changes only take effect after restart (Home Assistant behavior)

### Typical setup (recommended on HA Green)
1. Copy `v2/custom_components/<domain>` to `/config/custom_components/<domain>`
2. Restart Home Assistant
3. Add the integration in the UI: Settings → Devices & services → Add Integration → LDAP Auth
4. The integration will create an include file (example):
   - `/config/ldap_auth_providers.yaml`
5. Add **one line** to `configuration.yaml`:
   ```yaml
   homeassistant:
     auth_providers: !include ldap_auth_providers.yaml
