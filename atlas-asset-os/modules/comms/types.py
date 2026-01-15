from __future__ import annotations

from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from atlas_meshtastic_bridge.client import MeshtasticClient  # type: ignore[import-not-found]
else:
    class MeshtasticClient(Protocol):
        """Protocol defining the interface for communication clients (WiFi or Meshtastic).
        
        This protocol allows duck typing for clients that may have different implementations
        but share a common interface for connectivity and transport operations.
        """
        transport: Any  # Meshtastic-specific: has radio, receive_message, process_outbox
        
        def is_connected(self, interface: Any) -> bool:
            """Check if the transport is connected."""
            ...
        
        def has_connectivity(self) -> bool:
            """Check if the transport has actual network connectivity."""
            ...
        
        def mark_bad_current(self, interface: Any) -> None:
            """Mark the current connection as bad/unreliable."""
            ...
        
        def disconnect(self, interface: Any) -> None:
            """Disconnect from the current transport."""
            ...
