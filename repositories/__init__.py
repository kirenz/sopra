"""Data-access helpers for the MSSQL demo application."""

from .discount_repo import DiscountRepository, DiscountRepositoryError

__all__ = ["DiscountRepository", "DiscountRepositoryError"]

