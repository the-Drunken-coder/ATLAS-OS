"""Shared pytest configuration for asset OS packages."""

import sys
from pathlib import Path

ASSET_OS_ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK_DIR = ASSET_OS_ROOT / "framework"
MODULES_DIR = ASSET_OS_ROOT / "modules"

# Add ATLAS_ASSET_OS root, framework, and modules to path for imports
# Root must be added first so we can import framework and modules as packages
for path_dir in (ASSET_OS_ROOT, FRAMEWORK_DIR, MODULES_DIR):
    if path_dir.exists() and str(path_dir) not in sys.path:
        sys.path.insert(0, str(path_dir))


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
