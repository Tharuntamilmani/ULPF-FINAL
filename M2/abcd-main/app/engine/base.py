from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseParser(ABC):
    """
    Standard Parser Interface for Member 2 Parser Execution Engine.
    All registered parsers (Cisco, Fortinet, Palo Alto, CEF, LEEF, JSON, KV, Grok, Regex)
    must implement this contract.
    """

    parser_id: str = "generic-parser"
    name: str = "Generic Base Parser"
    version: str = "1.0.0"
    vendor: str = "Generic"
    product: str = "Generic"
    format: str = "plain_text"
    priority: int = 100

    @abstractmethod
    def can_parse(self, event: Dict[str, Any]) -> bool:
        """
        Check whether this parser can process the given envelope dict or payload.
        """
        pass

    @abstractmethod
    def parse(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured source-specific fields from the event payload.
        Returns a dict of extracted key-value fields.
        """
        pass
