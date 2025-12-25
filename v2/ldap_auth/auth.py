#!/usr/bin/env python3
"""LDAP authentication helper for Home Assistant command_line auth provider.

Home Assistant's command_line auth provider executes this script in a separate process and passes:
- username / password via environment variables.

Exit codes:
  0  success
  1  invalid credentials / user not found
  2  configuration error
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
except Exception:  # noqa: BLE001
    yaml = None  # type: ignore[assignment]

try:
    from ldap3 import Connection, Server, Tls, ALL, SUBTREE
except Exception as exc:  # noqa: BLE001
    print(f"[ldap_auth] Missing dependency ldap3: {exc}", file=sys.stderr)
    raise


DOMAIN = "ldap_auth"


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
        or "/config"
    )


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
    except Exception:  # noqa: BLE001
        return None
    section = content.get(DOMAIN)
    if isinstance(section, dict):
        return dict(section)
    return None


def load_config() -> Dict[str, Any]:
    config_dir = _config_dir()
    cfg = _load_from_storage(config_dir) or _load_from_yaml(config_dir)
    if not cfg:
        raise ValueError(
            "No LDAP configuration found. Configure the LDAP Auth integration in the UI (Settings → Devices & services). "
            "Optionally, provide a 'ldap_auth:' section in configuration.yaml."
        )
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
    except Exception:  # noqa: BLE001
        return default


def main() -> int:
    username, password = _get_env_cred()
    if not username or not password:
        print("[ldap_auth] Missing username/password env vars", file=sys.stderr)
        return 2

    try:
        cfg = load_config()
    except Exception as exc:  # noqa: BLE001
        print(f"[ldap_auth] Config error: {exc}", file=sys.stderr)
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

    if not server_uri or not basedn:
        print("[ldap_auth] 'server' and 'basedn' are required", file=sys.stderr)
        return 2

    # Build filter: (&(base_filter)(attr=username))
    attr_key = attrs.split(",")[0].strip()
    safe_username = username.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    user_filter = f"({attr_key}={safe_username})"
    search_filter = f"(&{base_filter}{user_filter})"

    try:
        tls = None
        if server_uri.lower().startswith("ldaps://") or (server_uri.lower().startswith("ldap://") and verify_ssl):
            tls = Tls(validate=ssl.CERT_REQUIRED if verify_ssl else ssl.CERT_NONE)  # type: ignore[name-defined]
        server = Server(server_uri, get_info=ALL, connect_timeout=timeout, tls=tls)  # type: ignore[arg-type]

        # If helper DN is provided, search with helper bind; otherwise attempt direct bind with user DN discovered by anonymous search.
        # Anonymous search is often disabled; helper bind is recommended.
        if helperdn:
            with Connection(server, user=helperdn, password=helperpass, auto_bind=True, receive_timeout=timeout) as c:
                if use_starttls:
                    try:
                        c.start_tls()
                    except Exception:
                        pass
                if not c.search(search_base=basedn, search_filter=search_filter, search_scope=SUBTREE, attributes=[display_attr, attr_key]):
                    return 1
                if not c.entries:
                    return 1
                user_dn = c.entries[0].entry_dn
                display_val = None
                try:
                    display_val = c.entries[0][display_attr].value
                except Exception:
                    display_val = None

            # Now bind as user to validate password
            with Connection(server, user=user_dn, password=password, auto_bind=True, receive_timeout=timeout) as _c2:
                pass

            if display_val:
                print(f"name = {display_val}")
            return 0

        # No helper DN: try to bind directly using username as DN (rare) or UPN; if that fails, deny.
        with Connection(server, user=username, password=password, auto_bind=True, receive_timeout=timeout) as c:
            if use_starttls:
                try:
                    c.start_tls()
                except Exception:
                    pass
        return 0

    except Exception as exc:  # noqa: BLE001
        # Avoid leaking credentials; include only error class/message.
        print(f"[ldap_auth] LDAP error: {exc}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    # Import ssl lazily because we only need it for TLS validation flags.
    import ssl  # noqa: E402

    raise SystemExit(main())
