"""Provider result validation for ULPF M4."""

from app.errors.exceptions import ProviderResponseError
from app.providers.base import ProviderOutput

FORBIDDEN_KEYS = {"__proto__", "prototype", "constructor", "event", "provenance", "integrity"}


class ResultValidator:
    """Validates data returned by providers before it is merged into the event."""

    @classmethod
    def validate_output(cls, provider_id: str, output: ProviderOutput) -> None:
        """Ensure provider output complies with type and security constraints."""
        if not isinstance(output.data, dict):
            raise ProviderResponseError(
                f"Provider '{provider_id}' returned non-dict data: {type(output.data).__name__}"
            )

        for k in output.data:
            if not isinstance(k, str):
                raise ProviderResponseError(
                    f"Provider '{provider_id}' returned non-string key: {k!r}"
                )
            if k.lower() in FORBIDDEN_KEYS:
                raise ProviderResponseError(
                    f"Provider '{provider_id}' returned forbidden key name: {k}"
                )
