#!/usr/bin/env python3
"""LDAP authentication helper for Home Assistant command_line auth provider.

Home Assistant's command_line auth provider executes this script in a separate process and passes:
- username / password via environment variables.

Exit codes:
  0  success
  1  invalid credentials
  2  configuration error
  3  connection error
  5  LDAP error / other runtime error

If meta: true is set in the command_line auth provider, Home Assistant parses stdout for metadata.
This script prints (on success) a single line:
  name = <display name>
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except Exception:
    yaml = None

from .const import DOMAIN
from .ldap import InvalidConfiguration, InvalidConnection, InvalidAuthentication, InvalidOperation, LDAP


def _get_env_cred() -> tuple[str, str]:
    username = os.environ.get("username") or os.environ.get("USERNAME") or ""
    password = os.environ.get("password") or os.environ.get("PASSWORD") or ""
    return username, password


def _config_dir() -> Path:
    # Common env vars for HA containers / scripts; default to /config on HA OS/Green.
    return Path(
        os.environ.get("HASS_CONFIG")
        or os.environ.get("HASS_CONFIG_DIR")
        or os.environ.get("HOMEASSISTANT_CONFIG")
        or "/config")


def _load_from_storage(config_dir: Path) -> Optional[Dict[str, Any]]:
    storage_file = config_dir / ".storage" / "core.config_entries"
    if not storage_file.exists():
        return None
    try:
        raw = json.loads(storage_file.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None

    entries = raw.get("data", {}).get("entries", [])
    for e in entries:
        if e.get("domain") != DOMAIN:
            continue
        # Ignore removed/disabled entries
        if e.get("disabled_by") is not None:
            continue
        data = dict(e.get("data") or {})
        options = dict(e.get("options") or {})
        data.update(options)  # options override
        return data
    return None


def _load_from_yaml(config_dir: Path) -> Optional[Dict[str, Any]]:
    if yaml is None:
        return None
    cfg_file = config_dir / "configuration.yaml"
    if not cfg_file.exists():
        return None
    try:
        content = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    except Exception as errex:
        print("[ldap_auth] Error reading {cfg_file} configuration file: {errex}", file=sys.stderr)
        return None
    section = content.get(DOMAIN)
    if isinstance(section, dict):
        return dict(section)
    return None


def load_config() -> Dict[str, Any]:
    config_dir = _config_dir()
    cfg = _load_from_storage(config_dir) or _load_from_yaml(config_dir)
    if not cfg:
        raise ValueError("No LDAP configuration found. Configure the LDAP Auth integration in the UI (Settings → Devices & services). "
            "Optionally, provide a 'ldap_auth:' section in configuration.yaml")
    return cfg


def _bool(v: Any, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "on"}


def _int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def main() -> int:
    username, password = _get_env_cred()
    if not username or not password:
        print("[ldap_auth] Missing username/password env vars", file=sys.stderr)
        return 2

    try:
        cfg = load_config()
    except Exception as exc:
        print(f"[ldap_auth] Configuration error: {exc}", file=sys.stderr)
        return 2

    server_uri = str(cfg.get("server", "")).strip()
    helperdn = str(cfg.get("helperdn", "")).strip()
    helperpass = str(cfg.get("helperpass", ""))
    basedn = str(cfg.get("basedn", "")).strip()
    attrs = str(cfg.get("attrs", "uid")).strip() or "uid"
    base_filter = str(cfg.get("base_filter", "(&(objectClass=person))")).strip() or "(&(objectClass=person))"
    display_attr = str(cfg.get("display_attr", "displayName")).strip() or "displayName"
    timeout = _int(cfg.get("timeout"), 3)
    verify_ssl = _bool(cfg.get("verify_ssl"), True)
    use_starttls = _bool(cfg.get("use_starttls"), False)

    try:
        ldap = LDAP(server_uri=server_uri, base_dn=basedn, base_filter=base_filter, binding_user=helperdn, binding_password=helperpass, verify_ssl=verify_ssl, use_starttls=use_starttls, timeout=timeout)
        user_attr = attrs.split(",")[0].strip()
        safe_username = username.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ldap.login(safe_username, password, user_attr, display_attr)
        return 0
    except InvalidAuthentication as auth:
        print(f"[ldap_auth] invalid authentication: {str(auth)}", file=sys.stderr)
        return 1
    except InvalidConfiguration as conf:
        print(f"[ldap_auth] invalid configuration: {str(conf)}", file=sys.stderr)
        return 2
    except InvalidConnection as conn:
        print(f"[ldap_auth] invalid connection: {str(conn)}", file=sys.stderr)
        return 3
    except InvalidOperation as ops:
        print(f"[ldap_auth] invalid operation: {str(ops)}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
