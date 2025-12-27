#!/usr/bin/env python3
"""LDAP Authentication helper for Home Assistant command_line auth provider.

Home Assistant's command_line auth provider passes two environment variables:
  - username
  - password

This script:
  - reads the 'ldap_auth:' section from Home Assistant configuration.yaml
  - performs an LDAP bind as a helper/service account to locate the user DN
  - performs a second bind with the user's DN and provided password
  - exits 0 on success, non-zero on failure
  - optionally prints "name = <display name>" when meta=true is configured

References:
  - Home Assistant command_line auth provider docs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import yaml  # Home Assistant already depends on PyYAML

# allow bundling deps under custom_components/ldap_auth/libs
_HERE = Path(__file__).resolve().parent
_LIBS_PATH = _HERE / "libs"
if _LIBS_PATH.is_dir():
    sys.path.insert(0, str(_LIBS_PATH))

from ldap3 import ALL, Connection, Server
from ldap3.utils.conv import escape_filter_chars


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def _config_path() -> Path:
    # In HA OS / Supervised / Container, config is typically mounted at /config
    config_dir = os.environ.get("HASS_CONFIG", "/config")
    return Path(config_dir) / "configuration.yaml"


def load_cfg() -> dict:
    cfg_path = os.environ.get("LDAP_AUTH_CONFIG", str(_config_path()))
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError as exc:
        raise RuntimeError(f"Configuration file not found: {cfg_path}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to read/parse YAML: {cfg_path}: {exc}") from exc

    cfg = data.get("ldap_auth")
    if not isinstance(cfg, dict):
        raise RuntimeError("Missing or invalid 'ldap_auth:' section in configuration.yaml")

    required = ["server", "helperdn", "helperpass", "basedn", "attrs", "base_filter", "display_attr"]
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        raise RuntimeError(f"Missing required ldap_auth settings: {', '.join(missing)}")

    return cfg


def main() -> int:
    # Validate env vars from HA command_line auth provider
    username = os.environ.get("username")
    password = os.environ.get("password")
    if not username or password is None:
        eprint("Need username and password environment variables!")
        return 1

    try:
        cfg = load_cfg()
    except Exception as exc:
        eprint(str(exc))
        return 1

    server_url = cfg["server"]
    helperdn = cfg["helperdn"]
    helperpass = cfg["helperpass"]
    basedn = cfg["basedn"]
    attrs = cfg.get("attrs", "uid")
    base_filter = cfg.get("base_filter", "(&(objectClass=person))")
    display_attr = cfg.get("display_attr", "displayName")
    timeout = int(cfg.get("timeout", 3))

    safe_username = escape_filter_chars(username)
    ldap_filter = f"(&{base_filter}({attrs}={safe_username}))"

    server = Server(server_url, get_info=ALL, connect_timeout=timeout)

    # Bind with helper account
    try:
        conn = Connection(server, helperdn, password=helperpass, auto_bind=True, raise_exceptions=True,)
    except Exception as exc:
        eprint(f"Initial LDAP bind failed: {exc}")
        return 1

    try:
        ok = conn.search(basedn, ldap_filter, attributes=[display_attr])
    except Exception as exc:
        eprint(f"LDAP search failed: {exc}")
        try:
            conn.unbind()
        except Exception:
            pass
        return 1

    if not ok or not conn.entries:
        eprint("No user found.")
        try:
            conn.unbind()
        except Exception:
            pass
        return 1

    entry = conn.entries[0]
    user_dn = entry.entry_dn

    try:
        user_display_name = str(entry[display_attr].value) if display_attr in entry else username
    except Exception:
        user_display_name = username

    try:
        conn.unbind()
    except Exception:
        pass

    # Bind with user DN and provided password
    try:
        user_conn = Connection(server, user_dn, password=password, auto_bind=True, raise_exceptions=True,)
    except Exception:
        eprint("Invalid credentials.")
        return 1
    finally:
        try:
            user_conn.unbind()
        except Exception:
            pass

    # Success. If command_line provider uses meta: true, it parses "key = value" lines.
    print(f"name = {user_display_name}")
    eprint(f"{username} authenticated successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
