import logging
import logging.handlers
import queue
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

LOGGER = logging.getLogger("bus")
DEFAULT_LOG_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 5


class MessageBus:
    """
    A lightweight, thread-safe publish/subscribe message bus.

    Handlers are called synchronously by default to ensure ordering,
    but the bus itself is designed to be used across threads.
    """

    def __init__(self, logging_config: Optional[dict] = None):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()
        self._running = True
        self._bus_logger: Optional[logging.Logger] = None
        self._bus_log_listener: Optional[logging.handlers.QueueListener] = None
        self._configure_logging(logging_config)

    def _configure_logging(self, logging_config: Optional[dict]) -> None:
        if not logging_config or not logging_config.get("enabled"):
            return

        log_file = logging_config.get("log_file", "~/.atlas_bus.log")
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            max_bytes = int(logging_config.get("max_bytes", DEFAULT_LOG_MAX_BYTES))
        except (TypeError, ValueError):
            max_bytes = DEFAULT_LOG_MAX_BYTES
        try:
            backup_count = int(logging_config.get("backup_count", DEFAULT_LOG_BACKUP_COUNT))
        except (TypeError, ValueError):
            backup_count = DEFAULT_LOG_BACKUP_COUNT

        log_queue: queue.Queue = queue.Queue()
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            mode="a",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        formatter = logging.Formatter("%(asctime)s %(message)s")
        file_handler.setFormatter(formatter)

        bus_logger = logging.getLogger("bus.events")
        bus_logger.setLevel(logging.INFO)
        bus_logger.propagate = False
        bus_logger.handlers.clear()
        queue_handler = logging.handlers.QueueHandler(log_queue)
        bus_logger.addHandler(queue_handler)

        listener = logging.handlers.QueueListener(log_queue, file_handler)
        listener.start()

        self._bus_logger = bus_logger
        self._bus_log_listener = listener

    def _log_event(self, operation: str, topic: str, data: Any = None) -> None:
        if not self._bus_logger:
            return
        try:
            payload = f"{operation} topic={topic}"
            if data is not None:
                payload += f" data={data}"
            self._bus_logger.info(payload)
        except Exception:
            # Avoid impacting bus execution if logging fails
            LOGGER.debug("Failed to log bus event", exc_info=True)

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Subscribe a handler function to a specific topic."""
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(handler)
            LOGGER.debug(f"Subscribed to '{topic}'")
            self._log_event("subscribe", topic)

    def unsubscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Unsubscribe a handler function from a specific topic."""
        with self._lock:
            if topic in self._subscribers:
                try:
                    self._subscribers[topic].remove(handler)
                    LOGGER.debug(f"Unsubscribed from '{topic}'")
                    self._log_event("unsubscribe", topic)
                    # Clean up empty topic lists
                    if not self._subscribers[topic]:
                        del self._subscribers[topic]
                except ValueError:
                    # Handler not in list, ignore
                    LOGGER.debug(
                        f"Handler not subscribed to '{topic}', ignoring unsubscribe"
                    )

    def publish(self, topic: str, data: Any = None) -> None:
        """Publish data to a specific topic. Handlers are invoked immediately."""
        if not self._running:
            return

        with self._lock:
            handlers = self._subscribers.get(topic, [])[
                :
            ]  # Copy list to avoid modification during iteration

        if not handlers:
            # LOGGER.debug(f"No subscribers for '{topic}'")
            return

        self._log_event("publish", topic, data)

        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                LOGGER.exception(f"Error in handler for topic '{topic}': {e}")

    def shutdown(self):
        """Stop accepting new publishes (conceptually)."""
        self._running = False
        LOGGER.info("Bus shutting down")
        if self._bus_log_listener:
            self._bus_log_listener.stop()
