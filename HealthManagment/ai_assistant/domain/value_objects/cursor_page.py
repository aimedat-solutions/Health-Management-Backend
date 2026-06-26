import base64
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


def encode_cursor(obj_id: int, created_at: datetime) -> str:
    """Encode an opaque pagination cursor from a record's identity tuple.

    The cursor is a base64-encoded JSON blob containing ``id`` and
    ``created_at``.  Clients treat it as an opaque string — they must never
    inspect or modify it.
    """
    payload = json.dumps(
        {"id": obj_id, "created_at": created_at.isoformat()},
        default=str,
    )
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> dict:
    """Decode a cursor back to its ``{id, created_at}`` components.

    Raises ``ValueError`` if the cursor is malformed.
    """
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(payload)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return data
    except (ValueError, json.JSONDecodeError, KeyError) as exc:
        raise ValueError("Invalid pagination cursor.") from exc


@dataclass
class CursorPage(Generic[T]):
    """Generic page of results returned by cursor-based pagination.

    Attributes:
        items:       Records on this page (at most *limit*).
        next_cursor: Pass this as ``?cursor=`` to fetch the next page.
                     ``None`` when there are no more results.
        has_more:    ``True`` when subsequent pages exist.
    """

    items: list[T] = field(default_factory=list)
    next_cursor: Optional[str] = None
    has_more: bool = False
