# ATLAS Asset OS Testing

This directory holds automated tests and manual test tools for the BasePlate OS and its modules.

## Structure

- tests/unit/ contains unit tests. Module-specific tests live in subfolders named after each module.
- tests/integration/ contains integration tests that boot or combine components.
- testing_tools/ contains manual or interactive test utilities (for example, comms injector).

## Running tests

From ATLAS_ASSET_OS/:

```bash
pip install -r requirements-test.txt
pytest tests/
```

## Notes

- Unit tests should avoid external hardware dependencies. Prefer fakes or lightweight fixtures.
- Integration tests can exercise boot flows and module wiring.
- If you add a new module, create a matching folder under tests/unit/ and place module tests there.
