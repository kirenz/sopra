"""Typed domain objects for the B2B discount demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class DiscountInput:
    """Collect the business fields that belong to one discount record."""

    customer_id: int | None
    minimum_quantity: int
    maximum_quantity: int
    discount_percent: float
    valid_from: date
    valid_to: date
    comment: str = ""
    discount_id: int | None = None

