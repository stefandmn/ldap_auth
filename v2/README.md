# ldap-auth (custom integration)

This custom integration is intentionally minimal. Its purpose is to provide a stable location to store
third-party Python dependencies under:

`custom_components/ldap_auth/libs/`

Your `command_line` auth script can then add that directory to `sys.path` to import bundled libraries
(e.g., `ldap3`, and optionally `PyYAML`).

## Where to put libraries

Create:

`custom_components/ldap_auth/libs/`

Then copy the installed package folders into that directory, for example:

- `ldap3/`
- `pyasn1/`
- `pyasn1_modules/`
- `yaml/` (PyYAML) if you use YAML parsing

This repository/zip intentionally excludes those dependencies.
