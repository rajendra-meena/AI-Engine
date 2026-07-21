"""
MarketMind AI — Serialization Utilities

Shared helpers for converting domain models to/from dicts and JSON.
All models should use these to ensure consistent serialization.
"""

import json
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")


def to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass or object to a dict using its to_dict() method if available."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "_asdict"):
        return obj._asdict()  # namedtuple
    if hasattr(obj, "__dataclass_fields__"):
        return {f.name: getattr(obj, f.name) for f in obj.__dataclass_fields__.values()}
    raise ValueError(f"Cannot serialize {type(obj).__name__}")


def to_json(obj: Any, indent: int | None = None) -> str:
    """Serialize an object to a JSON string."""
    return json.dumps(to_dict(obj), indent=indent, default=str)


def from_dict(cls: type[T], data: dict[str, Any]) -> T:
    """Create a model instance from a dict.

    Only works for dataclasses with matching field names.
    Fields not present in the dict use their defaults.
    """
    import dataclasses
    if not dataclasses.is_dataclass(cls):
        raise ValueError(f"{cls.__name__} is not a dataclass")
    field_names = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


def datetime_to_iso(dt: datetime | None) -> str | None:
    """Safely convert a datetime to ISO string."""
    if dt is None:
        return None
    return dt.isoformat(timespec="milliseconds")


def iso_to_datetime(s: str | None) -> datetime | None:
    """Safely convert an ISO string to datetime."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
