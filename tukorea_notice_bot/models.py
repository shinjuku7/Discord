"""Data models for the Tukorea notice crawler."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Notice:
    """Represents a single notice entry on the university board."""

    id: str
    title: str
    url: str
    category: str
    writer: str
    date: date
    views: Optional[int]
    has_attachment: bool

