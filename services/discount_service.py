"""Business logic for validating and saving B2B discounts."""

from __future__ import annotations

from typing import Any

import pandas as pd

from models.discount import DiscountInput
from repositories.db import get_app_user
from repositories.discount_repo import DiscountRepository, DiscountRepositoryError


class DiscountValidationError(ValueError):
    """Raised when a user submits business data that violates local rules."""

    def __init__(self, messages: list[str]) -> None:
        """Store all validation messages so the UI can display them together."""

        super().__init__("\n".join(messages))
        self.messages = messages


class DiscountServiceError(RuntimeError):
    """Raised when the service cannot complete a database-backed action."""


class DiscountService:
    """Coordinate validation rules and repository calls."""

    def __init__(self, repository: DiscountRepository | None = None) -> None:
        """Create the service with the default repository unless one is injected."""

        self._repository = repository or DiscountRepository()
        self._app_user = get_app_user()

    def list_discounts(
        self,
        search_text: str = "",
        customer_id: int | None = None,
    ) -> pd.DataFrame:
        """Return the discounts shown in the list and edit tabs."""

        try:
            frame = self._repository.list_discounts(
                search_text=search_text,
                customer_id=customer_id,
            )
            return frame.fillna({"Bemerkung": ""})
        except DiscountRepositoryError as exc:
            raise DiscountServiceError(
                f"Could not load the discount overview from SQL Server: {exc}"
            ) from exc

    def get_discount_by_id(self, discount_id: int) -> dict[str, Any] | None:
        """Load one discount record as a plain dictionary for the edit form."""

        try:
            frame = self._repository.get_discount_by_id(discount_id)
            if frame.empty:
                return None
            record = frame.fillna({"Bemerkung": ""}).iloc[0].to_dict()
            return record
        except DiscountRepositoryError as exc:
            raise DiscountServiceError(
                f"Could not load discount {discount_id} from SQL Server: {exc}"
            ) from exc

    def get_customer_options(self) -> list[tuple[int, str]]:
        """Return customer options in a form that works well for Streamlit."""

        try:
            frame = self._repository.get_customer_lov()
            return [
                (int(row.CUSTOMER_ID), str(row.CUSTOMER_LONG))
                for row in frame.itertuples(index=False)
            ]
        except DiscountRepositoryError as exc:
            raise DiscountServiceError(
                f"Could not load the customer list from SQL Server: {exc}"
            ) from exc

    def create_discount(self, discount: DiscountInput) -> int:
        """Validate and insert a new discount."""

        self._validate_discount(discount)
        try:
            return self._repository.create_discount(discount, self._app_user)
        except DiscountRepositoryError as exc:
            raise DiscountServiceError(
                f"SQL Server rejected the new discount: {exc}"
            ) from exc

    def update_discount(self, discount: DiscountInput) -> int:
        """Validate and update an existing discount."""

        if discount.discount_id is None:
            raise DiscountValidationError(
                ["Choose an existing discount before submitting an update."]
            )

        self._validate_discount(discount)
        try:
            return self._repository.update_discount(discount, self._app_user)
        except DiscountRepositoryError as exc:
            raise DiscountServiceError(
                f"SQL Server rejected the update: {exc}"
            ) from exc

    def get_application_user(self) -> str:
        """Expose the audit user so the UI can explain what is stored in the DB."""

        return self._app_user

    def _validate_discount(self, discount: DiscountInput) -> None:
        """Run local business checks before SQL Server sees the data."""

        messages: list[str] = []

        if discount.customer_id is None:
            messages.append("Choose a customer before saving the discount.")

        if discount.minimum_quantity <= 0:
            messages.append("`Minimum quantity` must be greater than zero.")

        if discount.maximum_quantity < discount.minimum_quantity:
            messages.append(
                "`Maximum quantity` must be greater than or equal to `Minimum quantity`."
            )

        if not 0 < discount.discount_percent <= 100:
            messages.append("`Discount percent` must be between 0 and 100.")

        if discount.valid_from > discount.valid_to:
            messages.append("`Valid from` must be on or before `Valid to`.")

        if len(discount.comment.strip()) > 255:
            messages.append("The optional comment must stay within 255 characters.")

        if not messages and discount.customer_id is not None:
            overlap_message = self._build_overlap_message(discount)
            if overlap_message:
                messages.append(overlap_message)

        if messages:
            raise DiscountValidationError(messages)

    def _build_overlap_message(self, discount: DiscountInput) -> str | None:
        """Reject overlapping discount windows for the same customer.

        This rule is not enforced by the database views themselves, so the
        service layer is the right place to explain the business meaning.
        """

        if discount.customer_id is None:
            return None

        try:
            frame = self._repository.list_discounts_for_customer(
                customer_id=discount.customer_id,
                exclude_discount_id=discount.discount_id,
            )
        except DiscountRepositoryError as exc:
            raise DiscountServiceError(
                f"Could not validate overlapping discounts: {exc}"
            ) from exc
        if frame.empty:
            return None

        overlap_frame = frame.copy()
        overlap_frame["GiltVon"] = pd.to_datetime(overlap_frame["GiltVon"]).dt.date
        overlap_frame["GiltBis"] = pd.to_datetime(overlap_frame["GiltBis"]).dt.date

        overlapping = overlap_frame[
            (overlap_frame["MengeVon"] <= discount.maximum_quantity)
            & (overlap_frame["MengeBis"] >= discount.minimum_quantity)
            & (overlap_frame["GiltVon"] <= discount.valid_to)
            & (overlap_frame["GiltBis"] >= discount.valid_from)
        ]

        if overlapping.empty:
            return None

        first_match = overlapping.iloc[0]
        return (
            "The new data overlaps with discount "
            f"{int(first_match['RabattID'])} for the same customer. "
            "Choose a different quantity interval or validity period."
        )
