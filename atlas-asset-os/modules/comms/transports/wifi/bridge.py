import asyncio
import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    import httpx
except Exception:  # pragma: no cover - optional dependency for wifi transport
    httpx = None  # type: ignore

LOGGER = logging.getLogger("modules.comms.wifi")


def _find_repo_root(start: Path) -> Path:
    """Walk up parents to locate the repo root (directory containing .git)."""
    for ancestor in [start] + list(start.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return start

# Try to import shared test environment detection utility
try:
    from framework.utils import is_test_env as _is_test_env_impl
except ImportError:
    # Fallback if framework.utils is not available
    def _is_test_env_impl() -> bool:
            return bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("ATLAS_TEST_MODE"))

# Prefer the in-repo atlas_asset_http_client_python for dev use.
_ROOT = _find_repo_root(Path(__file__).resolve().parent)
_CLIENT_SRC = (
    _ROOT
    / "Atlas_Client_SDKs"
    / "connection_packages"
    / "atlas_asset_http_client_python"
    / "src"
)
if str(_CLIENT_SRC) not in sys.path:
    sys.path.insert(0, str(_CLIENT_SRC))

try:
    from atlas_asset_http_client_python import AtlasCommandHttpClient  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover - optional dependency for wifi transport
    AtlasCommandHttpClient = None  # type: ignore


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _connect_with_windows(ssid: str, interface: Optional[str]) -> bool:
    cmd = ["netsh", "wlan", "connect", f"name={ssid}"]
    if interface:
        cmd.append(f"interface={interface}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return True
    LOGGER.warning(
        "WiFi connect failed for %s: %s", ssid, (result.stderr or result.stdout).strip()
    )
    return False


def _connect_with_nmcli(ssid: str, password: Optional[str]) -> bool:
    """Connect to WiFi network using nmcli.

    Note: nmcli doesn't support reading passwords from stdin or files directly.
    Environment variables are used as a mitigation, though they're still visible
    to processes running as the same user. For production use, consider using
    NetworkManager connection profiles instead.
    """
    env = os.environ.copy()
    if password:
        # Store password in environment variable to avoid command-line exposure
        # While not perfect, this is more secure than passing via command-line arguments
        # SECURITY LIMITATION: Environment variables are still visible to processes
        # running as the same user via /proc/<pid>/environ. For production deployments,
        # consider using NetworkManager connection profiles or other secure credential
        # management systems.
        env["NMCLI_WIFI_PASSWORD"] = password
        # Use shlex.quote to prevent command injection from malicious SSIDs
        ssid_quoted = shlex.quote(ssid)
        script = f'nmcli dev wifi connect {ssid_quoted} password "$NMCLI_WIFI_PASSWORD"'
        result = subprocess.run(
            ["/bin/sh", "-c", script],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    else:
        # When no password, use list form which is safe from command injection
        # as args are passed directly to nmcli without shell interpretation
        cmd = ["nmcli", "dev", "wifi", "connect", ssid]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, env=env
        )

    if result.returncode == 0:
        return True
    LOGGER.warning(
        "WiFi connect failed for %s: %s", ssid, (result.stderr or result.stdout).strip()
    )
    return False


def _connect_with_networksetup(
    ssid: str, password: Optional[str], interface: Optional[str]
) -> bool:
    """Connect to WiFi network using networksetup (macOS).

    Note: networksetup doesn't support reading passwords from stdin or files.
    Environment variables are used as a mitigation, though they're still visible
    to processes running as the same user.
    """
    if not interface:
        LOGGER.warning("WiFi connect skipped for %s: no interface configured", ssid)
        return False

    env = os.environ.copy()
    if password:
        # Store password in environment variable to avoid command-line exposure
        # While not perfect, this is more secure than passing via command-line arguments
        env["NETWORKSETUP_WIFI_PASSWORD"] = password
        # Use shlex.quote to prevent command injection from malicious SSIDs or interface names
        interface_quoted = shlex.quote(interface)
        ssid_quoted = shlex.quote(ssid)
        script = f'networksetup -setairportnetwork {interface_quoted} {ssid_quoted} "$NETWORKSETUP_WIFI_PASSWORD"'
        result = subprocess.run(
            ["/bin/sh", "-c", script],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    else:
        # When no password, use list form which is safe from command injection
        # as args are passed directly to networksetup without shell interpretation
        cmd = ["networksetup", "-setairportnetwork", interface, ssid]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, env=env
        )

    if result.returncode == 0:
        return True
    LOGGER.warning(
        "WiFi connect failed for %s: %s", ssid, (result.stderr or result.stdout).strip()
    )
    return False


def _current_ssid_windows() -> Optional[str]:
    result = subprocess.run(
        ["netsh", "wlan", "show", "interfaces"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "SSID" in line and "BSSID" not in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                ssid = parts[1].strip()
                if ssid and ssid.lower() != "no":
                    return ssid
    return None


def _current_ssid_linux() -> Optional[str]:
    result = subprocess.run(
        ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("yes:"):
            return line.split(":", 1)[1].strip() or None
    return None


def _current_ssid_macos(interface: Optional[str]) -> Optional[str]:
    if not interface:
        return None
    result = subprocess.run(
        ["networksetup", "-getairportnetwork", interface],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    if "Current Wi-Fi Network:" in output:
        return output.split("Current Wi-Fi Network:", 1)[1].strip() or None
    return None


def get_current_ssid(interface: Optional[str]) -> Optional[str]:
    platform = sys.platform
    if platform.startswith("win"):
        return _current_ssid_windows()
    if platform.startswith("linux"):
        return _current_ssid_linux()
    if platform == "darwin":
        return _current_ssid_macos(interface)
    return None


BAD_SSIDS: set[str] = set()


def _try_connect_networks(
    networks: Iterable[Dict[str, str]], interface: Optional[str]
) -> bool:
    platform = sys.platform
    for entry in networks:
        ssid = (entry.get("ssid") or "").strip()
        password = (entry.get("password") or "").strip() or None
        if not ssid:
            continue

        LOGGER.info("Trying WiFi network: %s", ssid)
        if platform.startswith("win"):
            if _connect_with_windows(ssid, interface):
                return True
        elif platform.startswith("linux"):
            if _connect_with_nmcli(ssid, password):
                return True
        elif platform == "darwin":
            if _connect_with_networksetup(ssid, password, interface):
                return True
        else:
            LOGGER.warning("WiFi connect not supported on platform %s", platform)
            return False
    return False


def _disconnect_windows() -> None:
    subprocess.run(
        ["netsh", "wlan", "disconnect"], capture_output=True, text=True, check=False
    )


def _disconnect_linux(interface: Optional[str]) -> None:
    cmd = ["nmcli", "dev", "disconnect"]
    if interface:
        cmd.append(interface)
    subprocess.run(cmd, capture_output=True, text=True, check=False)


def _disconnect_macos(interface: Optional[str]) -> None:
    if not interface:
        return
    subprocess.run(
        ["networksetup", "-setairportpower", interface, "off"],
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        ["networksetup", "-setairportpower", interface, "on"],
        capture_output=True,
        text=True,
        check=False,
    )


def disconnect_current(interface: Optional[str]) -> None:
    platform = sys.platform
    if platform.startswith("win"):
        _disconnect_windows()
    elif platform.startswith("linux"):
        _disconnect_linux(interface)
    elif platform == "darwin":
        _disconnect_macos(interface)


def mark_bad_ssid(ssid: Optional[str]) -> None:
    if ssid:
        BAD_SSIDS.add(ssid)


def is_bad_ssid(ssid: str) -> bool:
    return ssid in BAD_SSIDS


def _scan_open_networks_windows() -> list[str]:
    result = subprocess.run(
        ["netsh", "wlan", "show", "networks", "mode=bssid"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    ssids: list[str] = []
    current_ssid = None
    is_open = False
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("SSID "):
            if current_ssid and is_open:
                ssids.append(current_ssid)
            current_ssid = line.split(":", 1)[1].strip()
            is_open = False
        elif line.lower().startswith("authentication"):
            auth = line.split(":", 1)[1].strip().lower()
            if "open" in auth:
                is_open = True
    if current_ssid and is_open:
        ssids.append(current_ssid)
    return ssids


def _scan_open_networks_linux() -> list[str]:
    result = subprocess.run(
        ["nmcli", "-t", "-f", "SSID,SECURITY", "dev", "wifi"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    ssids: list[str] = []
    for line in result.stdout.splitlines():
        ssid, _, security = line.partition(":")
        if not ssid:
            continue
        sec = security.strip()
        if sec in ("", "--"):
            ssids.append(ssid)
    return ssids


def _scan_open_networks_macos() -> list[str]:
    airport = Path(
        "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
    )
    if not airport.exists():
        return []
    result = subprocess.run(
        [str(airport), "-s"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return []
    ssids: list[str] = []
    lines = result.stdout.splitlines()
    for line in lines[1:]:
        parts = line.strip().split()
        if not parts:
            continue
        ssid = parts[0]
        security = " ".join(parts[5:]) if len(parts) > 5 else ""
        if not security or security.lower() == "none":
            ssids.append(ssid)
    return ssids


def scan_open_networks() -> list[str]:
    platform = sys.platform
    if platform.startswith("win"):
        return _scan_open_networks_windows()
    if platform.startswith("linux"):
        return _scan_open_networks_linux()
    if platform == "darwin":
        return _scan_open_networks_macos()
    return []


def _verify_connectivity(base_url: str, timeout: float) -> bool:
    if httpx is None:
        return False
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/health", timeout=timeout)
        response.raise_for_status()
        return True
    except Exception:
        return False


def _connect_and_verify(
    ssid: str,
    password: Optional[str],
    *,
    base_url: str,
    timeout: float,
    interface: Optional[str],
) -> bool:
    connected = False
    if sys.platform.startswith("win"):
        connected = _connect_with_windows(ssid, interface)
    elif sys.platform.startswith("linux"):
        connected = _connect_with_nmcli(ssid, password)
    elif sys.platform == "darwin":
        connected = _connect_with_networksetup(ssid, password, interface)
    else:
        return False

    if not connected:
        return False
    if _verify_connectivity(base_url, timeout):
        return True

    mark_bad_ssid(ssid)
    disconnect_current(interface)
    return False


class WifiApiClient:
    def __init__(self, base_url: str, *, token: Optional[str], timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    async def _with_client(self, method: str, *args: Any, **kwargs: Any) -> Any:
        async with AtlasCommandHttpClient(
            self._base_url, token=self._token, timeout=self._timeout
        ) as client:
            func = getattr(client, method)
            return await func(*args, **kwargs)

    def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        kwargs.pop("timeout", None)
        kwargs.pop("max_retries", None)
        kwargs.pop("retries", None)
        return _run_async(self._with_client(method, *args, **kwargs))

    def health_check(
        self, *, timeout: float | None = None, max_retries: int | None = None
    ):
        _ = max_retries
        request_timeout = timeout or self._timeout
        if httpx is None:
            raise RuntimeError("httpx is required for wifi health checks")
        response = httpx.get(f"{self._base_url}/health", timeout=request_timeout)
        response.raise_for_status()
        return response.json() if response.content else {"status": "ok"}

    def test_echo(
        self,
        message: Any = "ping",
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        # timeout and max_retries are accepted for API compatibility with meshtastic client
        # but are not used for the simple echo test
        _ = timeout
        _ = max_retries
        return {"echo": message}

    def update_telemetry(self, *, entity_id: str, **kwargs: Any):
        kwargs.pop("timeout", None)
        kwargs.pop("max_retries", None)
        kwargs.pop("retries", None)
        return self._call("update_entity_telemetry", entity_id, **kwargs)

    def current_ssid(self, interface: Optional[str]) -> Optional[str]:
        return get_current_ssid(interface)

    def is_connected(self, interface: Optional[str]) -> bool:
        return get_current_ssid(interface) is not None

    def has_connectivity(self) -> bool:
        return _verify_connectivity(self._base_url, self._timeout)

    def mark_bad_current(self, interface: Optional[str]) -> None:
        mark_bad_ssid(get_current_ssid(interface))

    def disconnect(self, interface: Optional[str]) -> None:
        disconnect_current(interface)

    def __getattr__(self, name: str):
        direct_methods = {
            "list_entities",
            "get_entity",
            "get_entity_by_alias",
            "create_entity",
            "update_entity",
            "delete_entity",
            "checkin_entity",
            "list_tasks",
            "get_task",
            "create_task",
            "update_task",
            "delete_task",
            "get_tasks_by_entity",
            "start_task",
            "complete_task",
            "transition_task_status",
            "fail_task",
            "list_objects",
            "get_object",
            "create_object",
            "update_object",
            "delete_object",
            "get_objects_by_entity",
            "get_objects_by_task",
            "add_object_reference",
            "remove_object_reference",
            "find_orphaned_objects",
            "get_object_references",
            "validate_object_references",
            "cleanup_object_references",
            "get_changed_since",
            "get_full_dataset",
        }
        if name in direct_methods:
            return lambda *args, **kwargs: self._call(name, *args, **kwargs)
        raise AttributeError(f"{type(self).__name__} has no attribute {name}")


def _is_test_env() -> bool:
    """
    Return True when running under automated tests.

    This helper is intentionally only used to guard operations that mutate the
    host network configuration (for example, connecting to or disconnecting from
    Wi-Fi networks). Other code paths that perform network I/O (such as HTTP
    requests) are expected to be controlled via test-time mocking rather than
    this environment flag.

    Detects test environments via:
    - PYTEST_CURRENT_TEST: Set by pytest during test execution
    - ATLAS_TEST_MODE: Can be set manually for test scenarios

    Returns:
        bool: True if running in a test environment, False otherwise
    """
    return _is_test_env_impl()


def build_wifi_client(
    *,
    base_url: str,
    api_token: Optional[str],
    wifi_config: Dict[str, Any],
) -> WifiApiClient:
    if AtlasCommandHttpClient is None:
        raise RuntimeError("atlas_asset_http_client_python is required for wifi comms")
    if not base_url:
        raise RuntimeError("atlas.base_url is required for wifi comms")

    networks = wifi_config.get("networks") or []
    connect_on_start = bool(wifi_config.get("connect_on_start", True))
    timeout = float(wifi_config.get("timeout_s", 10.0))
    if _is_test_env() and not wifi_config.get("allow_network_changes_in_tests", False):
        LOGGER.info("WiFi transport running in test mode; skipping connect/disconnect.")
        return WifiApiClient(base_url, token=api_token, timeout=timeout)
    interface = wifi_config.get("interface")
    scan_public = bool(wifi_config.get("scan_public_networks", True))

    current_ssid = get_current_ssid(interface)
    if current_ssid:
        if _verify_connectivity(base_url, timeout):
            LOGGER.info("WiFi already connected to %s; skipping connect", current_ssid)
            return WifiApiClient(base_url, token=api_token, timeout=timeout)
        LOGGER.warning(
            "WiFi connected to %s but no connectivity; disconnecting", current_ssid
        )
        mark_bad_ssid(current_ssid)
        disconnect_current(interface)

    if connect_on_start:
        for entry in networks:
            ssid = (entry.get("ssid") or "").strip()
            password = (entry.get("password") or "").strip() or None
            if not ssid or is_bad_ssid(ssid):
                continue
            if _connect_and_verify(
                ssid,
                password,
                base_url=base_url,
                timeout=timeout,
                interface=interface,
            ):
                return WifiApiClient(base_url, token=api_token, timeout=timeout)

        if scan_public:
            for ssid in scan_open_networks():
                if not ssid or is_bad_ssid(ssid):
                    continue
                if _connect_and_verify(
                    ssid,
                    None,
                    base_url=base_url,
                    timeout=timeout,
                    interface=interface,
                ):
                    return WifiApiClient(base_url, token=api_token, timeout=timeout)

    raise RuntimeError("No viable WiFi network found")
