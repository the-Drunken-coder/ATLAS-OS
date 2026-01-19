import logging
import threading
from typing import Dict, List, Callable, Any

LOGGER = logging.getLogger("bus")


class MessageBus:
    """
    A lightweight, thread-safe publish/subscribe message bus.

    Handlers are called synchronously by default to ensure ordering,
    but the bus itself is designed to be used across threads.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()
        self._running = True

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Subscribe a handler function to a specific topic."""
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(handler)
            LOGGER.debug(f"Subscribed to '{topic}'")

    def unsubscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Unsubscribe a handler function from a specific topic."""
        with self._lock:
            if topic in self._subscribers:
                try:
                    self._subscribers[topic].remove(handler)
                    LOGGER.debug(f"Unsubscribed from '{topic}'")
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

        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                LOGGER.exception(f"Error in handler for topic '{topic}': {e}")

    def shutdown(self):
        """Stop accepting new publishes (conceptually)."""
        self._running = False
        LOGGER.info("Bus shutting down")
