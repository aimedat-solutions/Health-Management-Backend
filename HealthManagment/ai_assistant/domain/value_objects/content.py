from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentItem:
    type: str  # "text", "image_url", "file", "structured_data"
    text: Optional[str] = None
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    data: dict = field(default_factory=dict)
