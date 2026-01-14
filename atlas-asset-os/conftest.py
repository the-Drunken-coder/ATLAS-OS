"""Shared pytest configuration for asset OS packages."""

import sys
from pathlib import Path

ASSET_OS_ROOT = Path(__file__).resolve().parent
BASEPLATE_OS_ROOT = ASSET_OS_ROOT / "BasePlate_OS"

# BasePlate OS uses module-level imports like `from bus import MessageBus`
# which expect the project root to be on sys.path.
BASEPLATE_PATH = str(BASEPLATE_OS_ROOT)
if BASEPLATE_OS_ROOT.exists() and BASEPLATE_PATH not in sys.path:
    sys.path.insert(0, BASEPLATE_PATH)


def pytest_addoption(parser):
    """Expose command-line overrides for BasePlate Atlas API tests."""

    group = parser.getgroup("baseplate_atlas_api")
    group.addoption(
        "--baseplate-base-url",
        action="store",
        default=None,
        help="Override the Atlas Command base URL used by BasePlate integration tests.",
    )
    group.addoption(
        "--baseplate-asset-id",
        action="store",
        default=None,
        help="Override the asset ID used when exercising the BasePlate Atlas API client.",
    )
    group.addoption(
        "--baseplate-model-id",
        action="store",
        default=None,
        help="Override the model ID used when exercising the BasePlate Atlas API client.",
    )
    group.addoption(
        "--baseplate-use-mock",
        action="store",
        choices=("true", "false", "1", "0"),
        default=None,
        help="Set to 'false' to connect to a live Atlas Command instance instead of the built-in mock.",
    )
