
"""
LDAP connectivity flow for ldap_auth.
Create connection, execute binding, test autehtication for specific user account.
"""

from __future__ import annotations

import os
import ssl
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# allow bundling deps (ldap3) under custom_components/ldap_auth/libs
_HERE = Path(__file__).resolve().parent
_LIBS_PATH = _HERE / "libs"
if _LIBS_PATH.is_dir():
    sys.path.insert(0, str(_LIBS_PATH))

try:
    from ldap3 import Connection, Server, Tls, ALL, SUBTREE
except Exception as exc:
    print(f"[ldap_auth] Missing dependency ldap3: {exc}", file=sys.stderr)
    raise


class InvalidConnection(Exception):
    pass


class InvalidAuthentication(Exception):
    pass


class InvalidConfiguration(Exception):
    pass


class InvalidOperation(Exception):
    pass


class LDAP():
    _tls = None
    _server: Server
    _connection = None
    _bidning_uri: str
    _base_dn: str
    _base_filter: str
    _binding_user = None
    _binding_password = None
    _use_starttls = False
    _verify_ssl = False
    _timeout = 10

    def __init__(self, server_uri: str, base_dn: str, base_filter: str, binding_user: str, binding_password: str, verify_ssl=False, use_starttls=False, timeout=10):
        self._server_uri = server_uri
        self._base_dn = base_dn
        self._base_filter = base_filter
        self._binding_user = binding_user
        self._binding_password = binding_password
        self._verify_ssl = verify_ssl
        self._use_starttls = use_starttls
        self._timeout = timeout
        if not self._server_uri or not self._base_dn:
            raise InvalidConfiguration("LDAP server URI and base DN are required")
        try:
            if self._server_uri.lower().startswith("ldaps://") or (self._server_uri.lower().startswith("ldap://") and self._verify_ssl):
                self._tls = Tls(validate=ssl.CERT_REQUIRED if self._verify_ssl else ssl.CERT_NONE)
            self._server = Server(self._server_uri, get_info=ALL, connect_timeout=self._timeout, tls=self._tls)
        except Exception as e:
            raise InvalidConnection(str(e)) from e
    
    def connect(self)-> Connection:
        try:
            if self._server is not None:
                self._connection = Connection(self._server, user=self._binding_user, password=self._binding_password, auto_bind=True, receive_timeout=self._timeout)
                if self._use_starttls:
                    try:
                        self._connection.start_tls()
                    except Exception:
                        pass
                return self._connection
            else:
                raise InvalidConfiguration("Invalid server configuration")
        except Exception as exc:
            msg = str(exc).lower()
            if "invalid credentials" in msg or "bind" in msg:
                raise InvalidAuthentication(str(exc)) from exc
            else:
                raise InvalidConnection(str(exc)) from exc
    
    def search(self, search_filter: str, attributes: list[str]) -> list:
        if self._connection is None:
            self._connection = self.connect()
        try:
            if search_filter is None or search_filter == "":
                search_filter = f"{self._base_filter}"
            else:
                search_filter = f"(&{self._base_filter}{search_filter})"
            searchcode = self._connection.search(search_base=self._base_dn, search_filter=search_filter, search_scope=SUBTREE, attributes=attributes)
            if searchcode != True:
                raise InvalidAuthentication("Invalid binding options")
            else:
                return self._connection.entries
        except Exception as exc:
            raise InvalidOperation(str(exc)) from exc

    def bind(self, userid: str, search_attr="uid", display_attr="displayName") -> str:
        # build filter: (&(base_filter)(attr=user))
        safe_userid = userid.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        user_filter = f"({search_attr}={safe_userid})"
        entries = self.search(search_filter=user_filter, attributes=[display_attr])
        if entries is None or len(entries) != 1:
             raise InvalidOperation("User didn't match")
        else:
            return entries[0].entry_dn
        
    def login(self, userid, password, search_attr="uid", display_attr="displayName"):
        if not userid or not password:
            raise InvalidOperation("Missing username/password")
        userdn = self.bind(userid, search_attr, display_attr)
        try:
            Connection(self._server, user=userdn, password=password, auto_bind=True, receive_timeout=self._timeout)
        except Exception as exc:
            raise InvalidAuthentication(str(exc)) from exc