#!/usr/bin/env python3
import os
import sys
import yaml
from ldap3 import Server, Connection, ALL
from ldap3.utils.conv import escape_filter_chars


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def load_cfg():
    cfg_path = "/config/configuration.yaml"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            root = yaml.safe_load(f) or {}
    except Exception as e:
        raise RuntimeError(f"Failed to read/parse {cfg_path}: {e}")

    block = root.get("ldap_auth")
    if not isinstance(block, dict):
        raise RuntimeError("Missing or invalid 'ldap_auth:' block in /config/configuration.yaml")

    # Required keys
    required = ["server", "helperdn", "helperpass", "basedn", "attrs", "base_filter"]
    missing = [k for k in required if not block.get(k)]
    if missing:
        raise RuntimeError(f"Missing required ldap_auth keys: {', '.join(missing)}")

    # Defaults
    block.setdefault("timeout", 3)
    block.setdefault("display_attr", "displayName")

    return block


def main():
    # Validate env vars from HA command_line auth provider
    username = os.environ.get("username")
    password = os.environ.get("password")
    if not username or password is None:
        eprint("Need username and password environment variables!")
        return 1

    try:
        cfg = load_cfg()
    except Exception as e:
        eprint(str(e))
        return 1

    server_url = cfg["server"]
    helperdn = cfg["helperdn"]
    helperpass = cfg["helperpass"]
    basedn = cfg["basedn"]
    attrs = cfg["attrs"]
    base_filter = cfg["base_filter"]
    display_attr = cfg["display_attr"]
    timeout = int(cfg.get("timeout", 3))

    safe_username = escape_filter_chars(username)
    ldap_filter = f"(&{base_filter}({attrs}={safe_username}))"

    # Connect with helper account
    server = Server(server_url, get_info=ALL, connect_timeout=timeout)
    try:
        conn = Connection(server, helperdn, password=helperpass, auto_bind=True, raise_exceptions=True,)
    except Exception as e:
        eprint(f"Initial ldap bind failed: {e}")
        return 1

    try:
        ok = conn.search(basedn, ldap_filter, attributes=[display_attr])
    except Exception as e:
        eprint(f"Search in ldap failed: {e}")
        conn.unbind()
        return 1

    if not ok or len(conn.entries) == 0:
        eprint(f"Search for username {username} yielded empty result")
        conn.unbind()
        return 1

    # Extract DN and display name
    entry = conn.entries[0]
    user_dn = entry.entry_dn
    user_display_name = None
    try:
        # ldap3 returns attribute objects; str(...) is usually safe
        user_display_name = str(getattr(entry, display_attr))
    except Exception:
        user_display_name = username

    conn.unbind()

    # Bind as user with presented password
    server = Server(server_url, get_info=ALL, connect_timeout=timeout)
    try:
        conn = Connection(server, user_dn, password=password, auto_bind=True, raise_exceptions=True,)
    except Exception as e:
        eprint(f"bind as {username} failed: {e}")
        return 1
    finally:
        try:
            conn.unbind()
        except Exception:
            pass

    # Success output for HA meta: true
    print(f"name = {user_display_name}")
    eprint(f"{username} authenticated successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())

