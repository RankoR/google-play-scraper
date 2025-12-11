from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


class ElementSpec:
    """
    Defines how to locate a piece of data within the complex nested arrays.
    """

    def __init__(
            self,
            path: list[int | str],
            transformer: Optional[Callable[[Any], Any]] = None,
            fallback_path: Optional[list[int | str]] = None
    ):
        self.path = path
        self.transformer = transformer
        self.fallback_path = fallback_path

    def extract(self, source: dict | list) -> Any:
        value = self._lookup(source, self.path)

        if value is None and self.fallback_path:
            value = self._lookup(source, self.fallback_path)

        if value is None:
            return None

        if self.transformer:
            try:
                return self.transformer(value)
            except Exception:
                return None
        return value

    def _lookup(self, source: Any, path: list[int | str]) -> Any:
        current = source
        try:
            for key in path:
                if isinstance(key, str):
                    if not isinstance(current, dict):
                        return None
                    current = current.get(key)
                elif isinstance(key, int):
                    if not isinstance(current, list) or len(current) <= key:
                        return None
                    current = current[key]
                else:
                    return None

                if current is None:
                    return None
            return current
        except Exception:
            return None


def extract_from_spec(source: Any, specs: dict[str, ElementSpec]) -> dict[str, Any]:
    """Applies a dictionary of ElementSpecs to a source object."""
    return {key: spec.extract(source) for key, spec in specs.items()}
