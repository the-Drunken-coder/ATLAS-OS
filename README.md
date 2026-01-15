# ATLAS OS

Collection of operating-system packages for Atlas assets and tools. This repo currently ships the BasePlate asset OS framework/modules plus a gateway tool OS for Meshtastic connectivity.

## Structure

- `atlas-asset-os/` - BasePlate Asset OS framework, shared modules, and tests. See `atlas-asset-os/README.md`.
- `atlas-tool-os/` - Tool-side OS implementations. Currently includes `Gateway_OS` for Meshtastic bridging.
- `conftest.py` - Shared pytest options (mostly for BasePlate/Atlas API tests).

## atlas-asset-os

BasePlate OS provides:
- Core framework (`framework/`) with `OSManager` and `MessageBus`
- Module infrastructure (`modules/`) plus built-in modules like `comms` and `operations`
- A module catalog in `atlas-asset-os/modules/MODULES.md`
- Unit/integration tests in `atlas-asset-os/tests/`

Run tests from the repo root:

```bash
pip install -r atlas-asset-os/requirements-test.txt
pytest atlas-asset-os/tests/
```

## atlas-tool-os (Gateway OS)

`atlas-tool-os/Gateway_OS/master.py` launches a Meshtastic gateway that bridges to Atlas Command. Configuration lives in `atlas-tool-os/Gateway_OS/config.json`.

The gateway expects local source checkouts of the Atlas Command connection packages:

```
ATLAS-OS/
  Atlas_Command/
    connection_packages/
      atlas_meshtastic_bridge/
      atlas_asset_http_client_python/
```

Run the gateway:

```bash
python atlas-tool-os/Gateway_OS/master.py
```

If you need deeper details for the asset OS, start with `atlas-asset-os/README.md`.
