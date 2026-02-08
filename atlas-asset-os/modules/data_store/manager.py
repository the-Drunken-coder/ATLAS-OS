import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.module_base import ModuleBase

LOGGER = logging.getLogger("modules.data_store")


class DataStoreManager(ModuleBase):
    """General-purpose in-memory data store with optional persistence."""

    MODULE_NAME = "data_store"
    MODULE_VERSION = "1.0.0"
    DEPENDENCIES: List[str] = []

    def __init__(self, bus, config):
        super().__init__(bus, config)
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._persist_enabled = False
        self._persist_path: Optional[Path] = None
        self._persist_interval_s = 30.0
        self._last_persist = 0.0
        self._persist_on_change = False

        cfg = self.get_module_config()
        persistence = cfg.get("persistence", {}) if isinstance(cfg, dict) else {}
        self._persist_enabled = bool(persistence.get("enabled", False))
        self._persist_on_change = bool(persistence.get("persist_on_change", False))
        self._persist_interval_s = float(persistence.get("interval_s", 30.0))
        path_value = persistence.get("path")
        if path_value:
            self._persist_path = Path(path_value).expanduser()

    def start(self) -> None:
        self._logger.info("Starting Data Store Manager")
        self.running = True
        self._load_persisted()

        self.bus.subscribe("data_store.put", self._handle_put)
        self.bus.subscribe("data_store.get", self._handle_get)
        self.bus.subscribe("data_store.delete", self._handle_delete)
        self.bus.subscribe("data_store.list", self._handle_list)
        self.bus.subscribe("data_store.snapshot.request", self._handle_snapshot)

    def stop(self) -> None:
        self._logger.info("Stopping Data Store Manager")
        self.running = False
        self._persist()

    def _handle_put(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        namespace = str(data.get("namespace", "default"))
        key = data.get("key")
        if not key:
            return
        value = data.get("value")
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        record = {"value": value, "meta": meta, "updated_at": time.time()}
        with self._lock:
            bucket = self._store.setdefault(namespace, {})
            bucket[str(key)] = record
        self.bus.publish(
            "data_store.updated",
            {"namespace": namespace, "key": str(key), "record": record},
        )
        if self._persist_on_change:
            self._persist()

    def _handle_get(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        namespace = str(data.get("namespace", "default"))
        key = data.get("key")
        if not key:
            return
        with self._lock:
            record = self._store.get(namespace, {}).get(str(key))
        self.bus.publish(
            "data_store.response",
            {
                "namespace": namespace,
                "key": str(key),
                "record": record,
                "request_id": data.get("request_id"),
            },
        )

    def _handle_delete(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        namespace = str(data.get("namespace", "default"))
        key = data.get("key")
        if not key:
            return
        removed = None
        with self._lock:
            bucket = self._store.get(namespace)
            if bucket and str(key) in bucket:
                removed = bucket.pop(str(key))
        self.bus.publish(
            "data_store.deleted",
            {"namespace": namespace, "key": str(key), "record": removed},
        )
        if self._persist_on_change:
            self._persist()

    def _handle_list(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        namespace = str(data.get("namespace", "default"))
        with self._lock:
            keys = list(self._store.get(namespace, {}).keys())
        self.bus.publish(
            "data_store.response",
            {
                "namespace": namespace,
                "keys": keys,
                "request_id": data.get("request_id"),
            },
        )

    def _handle_snapshot(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        namespace = data.get("namespace")
        with self._lock:
            if namespace:
                snapshot = {str(namespace): self._store.get(str(namespace), {}).copy()}
            else:
                snapshot = {name: bucket.copy() for name, bucket in self._store.items()}
        self.bus.publish(
            "data_store.snapshot",
            {"snapshot": snapshot, "request_id": data.get("request_id")},
        )

    def _load_persisted(self) -> None:
        if not self._persist_enabled or not self._persist_path:
            return
        if not self._persist_path.exists():
            return
        try:
            payload = json.loads(self._persist_path.read_text())
            if isinstance(payload, dict):
                with self._lock:
                    self._store = payload
                self._logger.info("Loaded data store from %s", self._persist_path)
        except Exception as exc:
            self._logger.warning("Failed to load data store: %s", exc)

    def _persist(self) -> None:
        if not self._persist_enabled or not self._persist_path:
            return
        now = time.time()
        if (
            not self._persist_on_change
            and now - self._last_persist < self._persist_interval_s
        ):
            return
        self._last_persist = now
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = json.dumps(self._store, indent=2)
            self._persist_path.write_text(data)
        except Exception as exc:
            self._logger.warning("Failed to persist data store: %s", exc)

    def system_check(self) -> Dict[str, Any]:
        """
        Run diagnostics on the data_store module.

        Returns:
            Dictionary with diagnostic results.
        """
        healthy = self.running

        # Count total records
        with self._lock:
            total_records = sum(len(bucket) for bucket in self._store.values())
            num_namespaces = len(self._store)

        result = {
            "healthy": healthy,
            "status": "running" if healthy else "stopped",
            "namespaces": num_namespaces,
            "total_records": total_records,
            "persistence_enabled": self._persist_enabled,
        }

        return result
