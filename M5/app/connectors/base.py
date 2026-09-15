"""
Abstract base class definition for all M5 Destination Connectors.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class DestinationConnector(ABC):
    """
    Standard interface contract for ULPF destination connectors.
    Each connector manages connection state, delivery execution, and health checks.
    """

    @abstractmethod
    async def send(self, event: Dict[str, Any]) -> None:
        """
        Deliver a canonical UES event to the target destination.
        Must raise an Exception on delivery failure to trigger retry/DLQ handling.
        """
        pass

    @abstractmethod
    async def health(self) -> bool:
        """
        Check connectivity and health of the target destination.
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """
        Unique destination connector identifier name (e.g. 'siem', 'data_lake', 'ai_stream').
        """
        pass
