"""Repository functions that talk directly to the MSSQL views."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from models.discount import DiscountInput

from .db import get_engine


class DiscountRepositoryError(RuntimeError):
    """Raised when SQL Server rejects a repository operation."""


class DiscountRepository:
    """Hide the SQL details behind a small set of Python methods."""

    def __init__(self, engine: Engine | None = None) -> None:
        """Store the shared SQLAlchemy engine."""

        self._engine = engine or get_engine()

    def list_discounts(
        self,
        search_text: str = "",
        customer_id: int | None = None,
    ) -> pd.DataFrame:
        """Return the list view with optional search and customer filters."""

        statement = text(
            """
            SELECT
                RabattID,
                KundenNr,
                Kunde,
                MengeVon,
                MengeBis,
                RabattProzent,
                GiltVon,
                GiltBis,
                Bemerkung,
                ErfasstAm,
                ErfasstVon,
                GeaendertAm,
                GeaendertVon
            FROM list_views.V_LIST_B2B_DISCOUNT
            WHERE (:customer_id IS NULL OR KundenNr = :customer_id)
              AND (
                    :search_pattern IS NULL
                    OR Kunde LIKE :search_pattern
                    OR COALESCE(Bemerkung, '') LIKE :search_pattern
                    OR CAST(RabattID AS nvarchar(50)) LIKE :search_pattern
                  )
            ORDER BY RabattID DESC;
            """
        )
        pattern = f"%{search_text.strip()}%" if search_text.strip() else None
        return self._read_frame(
            statement,
            {"customer_id": customer_id, "search_pattern": pattern},
        )

    def list_discounts_for_customer(
        self,
        customer_id: int,
        exclude_discount_id: int | None = None,
    ) -> pd.DataFrame:
        """Return all discounts for one customer to support overlap validation."""

        statement = text(
            """
            SELECT
                RabattID,
                KundenNr,
                MengeVon,
                MengeBis,
                RabattProzent,
                GiltVon,
                GiltBis,
                Bemerkung
            FROM list_views.V_LIST_B2B_DISCOUNT
            WHERE KundenNr = :customer_id
              AND (:exclude_discount_id IS NULL OR RabattID <> :exclude_discount_id)
            ORDER BY RabattID DESC;
            """
        )
        return self._read_frame(
            statement,
            {
                "customer_id": customer_id,
                "exclude_discount_id": exclude_discount_id,
            },
        )

    def get_discount_by_id(self, discount_id: int) -> pd.DataFrame:
        """Load one discount row for the edit form."""

        statement = text(
            """
            SELECT TOP (1)
                RabattID,
                KundenNr,
                Kunde,
                MengeVon,
                MengeBis,
                RabattProzent,
                GiltVon,
                GiltBis,
                Bemerkung,
                ErfasstAm,
                ErfasstVon,
                GeaendertAm,
                GeaendertVon
            FROM list_views.V_LIST_B2B_DISCOUNT
            WHERE RabattID = :discount_id;
            """
        )
        return self._read_frame(statement, {"discount_id": discount_id})

    def get_customer_lov(self) -> pd.DataFrame:
        """Read the list-of-values table used by the Streamlit dropdown."""

        statement = text(
            """
            SELECT CUSTOMER_ID, CUSTOMER_LONG
            FROM dbo.LOV_CUSTOMER
            ORDER BY CUSTOMER_LONG;
            """
        )
        return self._read_frame(statement)

    def create_discount(self, discount: DiscountInput, app_user: str) -> int:
        """Insert a new discount through the insert-only view."""

        statement = text(
            """
            INSERT INTO ins_views.V_INS_B2B_DISCOUNT (
                KundenNr,
                MengeVon,
                MengeBis,
                RabattProzent,
                GiltVon,
                GiltBis,
                Bemerkung,
                ErfasstAm,
                GeaendertVon
            )
            OUTPUT inserted.RabattID
            VALUES (
                :customer_id,
                :minimum_quantity,
                :maximum_quantity,
                :discount_percent,
                :valid_from,
                :valid_to,
                :comment,
                :app_user,
                :app_user
            );
            """
        )
        params = self._build_write_params(discount, app_user)

        try:
            with self._engine.begin() as connection:
                result = connection.execute(statement, params)
                return int(result.scalar_one())
        except SQLAlchemyError as exc:
            raise DiscountRepositoryError(str(exc)) from exc

    def update_discount(self, discount: DiscountInput, app_user: str) -> int:
        """Update an existing discount through the update view."""

        if discount.discount_id is None:
            raise DiscountRepositoryError("An update requires a discount_id.")

        statement = text(
            """
            UPDATE upd_views.V_UPD_B2B_DISCOUNT
            SET
                KundenNr = :customer_id,
                MengeVon = :minimum_quantity,
                MengeBis = :maximum_quantity,
                RabattProzent = :discount_percent,
                GiltVon = :valid_from,
                GiltBis = :valid_to,
                Bemerkung = :comment,
                GeaendertAm = CURRENT_TIMESTAMP,
                GeaendertVon = :app_user
            OUTPUT inserted.RabattID
            WHERE RabattID = :discount_id;
            """
        )
        params = self._build_write_params(discount, app_user)
        params["discount_id"] = discount.discount_id

        try:
            with self._engine.begin() as connection:
                result = connection.execute(statement, params)
                updated_id = result.scalar_one_or_none()
                if updated_id is None:
                    raise DiscountRepositoryError(
                        "The selected discount no longer exists in SQL Server."
                    )
                return int(updated_id)
        except SQLAlchemyError as exc:
            raise DiscountRepositoryError(str(exc)) from exc

    def _read_frame(
        self,
        statement: Any,
        params: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        """Run a SELECT statement and return the result as a DataFrame."""

        try:
            with self._engine.connect() as connection:
                return pd.read_sql(statement, connection, params=params)
        except SQLAlchemyError as exc:
            raise DiscountRepositoryError(str(exc)) from exc

    @staticmethod
    def _build_write_params(discount: DiscountInput, app_user: str) -> dict[str, Any]:
        """Translate the clean Python object into SQL parameters.

        The insert view exposes `INS_USER` under the alias `ErfasstAm`, which is
        counterintuitive. We keep the application model readable and isolate that
        odd naming inside the repository.
        """

        return {
            "customer_id": discount.customer_id,
            "minimum_quantity": discount.minimum_quantity,
            "maximum_quantity": discount.maximum_quantity,
            "discount_percent": round(discount.discount_percent, 2),
            "valid_from": discount.valid_from,
            "valid_to": discount.valid_to,
            "comment": discount.comment.strip() or None,
            "app_user": app_user,
        }

