"""Streamlit presentation layer for the B2B discount CRUD demo."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from models.discount import DiscountInput
from repositories.db import DatabaseConfigurationError
from services.discount_service import (
    DiscountService,
    DiscountServiceError,
    DiscountValidationError,
)


st.set_page_config(page_title="B2B Discount Demo", page_icon="💼", layout="wide")


def main() -> None:
    """Render the three-tab Streamlit application."""

    st.title("B2B Discount Maintenance Demo")
    st.caption(
        "This demo uses a three-layer architecture: Streamlit UI, business logic, and MSSQL repositories."
    )

    try:
        service = DiscountService()
    except DatabaseConfigurationError as exc:
        st.error(str(exc))
        st.info("Copy `.env.example` to `.env` and add the course credentials.")
        st.stop()

    _render_flash_message()

    st.write(
        f"The audit columns will use the application user `{service.get_application_user()}`."
    )

    list_tab, create_tab, edit_tab = st.tabs(
        ["List Discounts", "Create Discount", "Edit Discount"]
    )

    with list_tab:
        render_list_tab(service)

    with create_tab:
        render_create_tab(service)

    with edit_tab:
        render_edit_tab(service)


def render_list_tab(service: DiscountService) -> None:
    """Show the searchable list of existing discounts."""

    st.subheader("Existing Discounts")
    st.write(
        "The table refreshes automatically whenever a filter changes. "
        "This makes Streamlit reruns visible to students without adding extra button logic."
    )

    try:
        customer_lookup = _build_customer_lookup(service, placeholder_label="All customers")
    except DiscountServiceError as exc:
        st.error(str(exc))
        return

    customer_labels = list(customer_lookup.keys())

    filter_column, search_column = st.columns([1, 2])
    with filter_column:
        selected_customer_label = st.selectbox(
            "Customer filter",
            options=customer_labels,
            key="list_customer_filter",
        )
    with search_column:
        search_text = st.text_input(
            "Search",
            value="",
            placeholder="Search by customer, comment, or discount id",
            key="list_search_text",
        )

    try:
        discounts = service.list_discounts(
            search_text=search_text,
            customer_id=customer_lookup[selected_customer_label],
        )
    except DiscountServiceError as exc:
        st.error(str(exc))
        return

    st.metric("Rows returned", len(discounts))
    st.dataframe(
        _prepare_discount_frame_for_display(discounts),
        use_container_width=True,
        hide_index=True,
    )


def render_create_tab(service: DiscountService) -> None:
    """Show the form that inserts a new discount."""

    st.subheader("Create a New Discount")
    st.write(
        "The customer dropdown reads from `dbo.LOV_CUSTOMER`, while the actual INSERT goes through "
        "`ins_views.V_INS_B2B_DISCOUNT`."
    )

    try:
        customer_lookup = _build_customer_lookup(
            service,
            placeholder_label="Choose a customer...",
        )
    except DiscountServiceError as exc:
        st.error(str(exc))
        return

    customer_labels = list(customer_lookup.keys())

    with st.form("create_discount_form", clear_on_submit=False):
        left_column, right_column = st.columns(2)

        with left_column:
            selected_customer_label = st.selectbox(
                "Customer",
                options=customer_labels,
                key="create_customer",
            )
            minimum_quantity = st.number_input(
                "Minimum quantity",
                min_value=1,
                step=1,
                value=1,
                key="create_minimum_quantity",
            )
            maximum_quantity = st.number_input(
                "Maximum quantity",
                min_value=1,
                step=1,
                value=10,
                key="create_maximum_quantity",
            )

        with right_column:
            discount_percent = st.number_input(
                "Discount percent",
                min_value=0.1,
                max_value=100.0,
                step=0.5,
                value=5.0,
                key="create_discount_percent",
            )
            valid_from = st.date_input(
                "Valid from",
                value=date.today(),
                key="create_valid_from",
            )
            valid_to = st.date_input(
                "Valid to",
                value=date.today() + timedelta(days=30),
                key="create_valid_to",
            )

        comment = st.text_area(
            "Comment",
            value="",
            max_chars=255,
            placeholder="Optional explanation for business users",
            key="create_comment",
        )
        submitted = st.form_submit_button("Create discount")

    if not submitted:
        return

    discount = DiscountInput(
        customer_id=customer_lookup[selected_customer_label],
        minimum_quantity=int(minimum_quantity),
        maximum_quantity=int(maximum_quantity),
        discount_percent=float(discount_percent),
        valid_from=valid_from,
        valid_to=valid_to,
        comment=comment,
    )

    try:
        created_id = service.create_discount(discount)
    except DiscountValidationError as exc:
        for message in exc.messages:
            st.error(message)
        return
    except DiscountServiceError as exc:
        st.error(str(exc))
        return

    _set_flash_message(
        "success",
        f"Discount {created_id} was created successfully.",
    )
    st.session_state["selected_edit_discount_id"] = created_id
    st.rerun()


def render_edit_tab(service: DiscountService) -> None:
    """Show the edit workflow for one existing discount."""

    st.subheader("Edit an Existing Discount")
    try:
        discounts = service.list_discounts()
    except DiscountServiceError as exc:
        st.error(str(exc))
        return

    if discounts.empty:
        st.info("No discounts are available for editing.")
        return

    discount_labels = {
        int(row.RabattID): (
            f"{int(row.RabattID)} | {row.Kunde} | "
            f"{int(row.MengeVon)}-{int(row.MengeBis)} units | "
            f"{float(row.RabattProzent):.2f}%"
        )
        for row in discounts.itertuples(index=False)
    }
    discount_ids = list(discount_labels.keys())

    default_discount_id = st.session_state.get("selected_edit_discount_id", discount_ids[0])
    if default_discount_id not in discount_labels:
        default_discount_id = discount_ids[0]

    selected_discount_id = st.selectbox(
        "Choose the discount you want to edit",
        options=discount_ids,
        format_func=lambda discount_id: discount_labels[discount_id],
        index=discount_ids.index(default_discount_id),
        key="selected_edit_discount_id",
    )

    try:
        discount_record = service.get_discount_by_id(selected_discount_id)
        customer_lookup = _build_customer_lookup(service)
    except DiscountServiceError as exc:
        st.error(str(exc))
        return

    if discount_record is None:
        st.error("The selected discount could not be loaded from SQL Server.")
        return

    st.caption(
        "Created: "
        f"{_format_timestamp(discount_record['ErfasstAm'])} by {discount_record['ErfasstVon']} | "
        "Last updated: "
        f"{_format_timestamp(discount_record['GeaendertAm'])} by {discount_record['GeaendertVon']}"
    )

    customer_labels = list(customer_lookup.keys())
    reverse_lookup = {value: key for key, value in customer_lookup.items() if value is not None}
    selected_customer_label = reverse_lookup.get(int(discount_record["KundenNr"]), customer_labels[0])

    with st.form(f"edit_discount_form_{selected_discount_id}", clear_on_submit=False):
        left_column, right_column = st.columns(2)

        with left_column:
            customer_label = st.selectbox(
                "Customer",
                options=customer_labels,
                index=customer_labels.index(selected_customer_label),
                key=f"edit_customer_{selected_discount_id}",
            )
            minimum_quantity = st.number_input(
                "Minimum quantity",
                min_value=1,
                step=1,
                value=int(discount_record["MengeVon"]),
                key=f"edit_minimum_quantity_{selected_discount_id}",
            )
            maximum_quantity = st.number_input(
                "Maximum quantity",
                min_value=1,
                step=1,
                value=int(discount_record["MengeBis"]),
                key=f"edit_maximum_quantity_{selected_discount_id}",
            )

        with right_column:
            discount_percent = st.number_input(
                "Discount percent",
                min_value=0.1,
                max_value=100.0,
                step=0.5,
                value=float(discount_record["RabattProzent"]),
                key=f"edit_discount_percent_{selected_discount_id}",
            )
            valid_from = st.date_input(
                "Valid from",
                value=_coerce_to_date(discount_record["GiltVon"]),
                key=f"edit_valid_from_{selected_discount_id}",
            )
            valid_to = st.date_input(
                "Valid to",
                value=_coerce_to_date(discount_record["GiltBis"]),
                key=f"edit_valid_to_{selected_discount_id}",
            )

        comment = st.text_area(
            "Comment",
            value=str(discount_record.get("Bemerkung", "")),
            max_chars=255,
            key=f"edit_comment_{selected_discount_id}",
        )
        submitted = st.form_submit_button("Update discount")

    if not submitted:
        return

    discount = DiscountInput(
        discount_id=selected_discount_id,
        customer_id=customer_lookup[customer_label],
        minimum_quantity=int(minimum_quantity),
        maximum_quantity=int(maximum_quantity),
        discount_percent=float(discount_percent),
        valid_from=valid_from,
        valid_to=valid_to,
        comment=comment,
    )

    try:
        updated_id = service.update_discount(discount)
    except DiscountValidationError as exc:
        for message in exc.messages:
            st.error(message)
        return
    except DiscountServiceError as exc:
        st.error(str(exc))
        return

    _set_flash_message(
        "success",
        f"Discount {updated_id} was updated successfully.",
    )
    st.session_state["selected_edit_discount_id"] = updated_id
    st.rerun()


def _build_customer_lookup(
    service: DiscountService,
    placeholder_label: str | None = None,
) -> dict[str, int | None]:
    """Map readable labels to customer IDs for Streamlit widgets."""

    lookup: dict[str, int | None] = {}
    if placeholder_label is not None:
        lookup[placeholder_label] = None

    for customer_id, customer_label in service.get_customer_options():
        lookup[customer_label] = customer_id
    return lookup


def _prepare_discount_frame_for_display(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert dates into readable strings before Streamlit renders the table."""

    display_frame = frame.copy()
    for column_name in ["GiltVon", "GiltBis"]:
        if column_name in display_frame:
            display_frame[column_name] = pd.to_datetime(display_frame[column_name]).dt.strftime(
                "%Y-%m-%d"
            )

    for column_name in ["ErfasstAm", "GeaendertAm"]:
        if column_name in display_frame:
            display_frame[column_name] = pd.to_datetime(display_frame[column_name]).dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    return display_frame


def _coerce_to_date(value: Any) -> date:
    """Turn pandas timestamps into `datetime.date` values for Streamlit widgets."""

    return pd.to_datetime(value).date()


def _format_timestamp(value: Any) -> str:
    """Format a database timestamp for compact UI output."""

    return pd.to_datetime(value).strftime("%Y-%m-%d %H:%M:%S")


def _set_flash_message(kind: str, text: str) -> None:
    """Store one message in session state so it survives a rerun."""

    st.session_state["flash_message"] = {"kind": kind, "text": text}


def _render_flash_message() -> None:
    """Display and clear the message that was stored before a rerun."""

    flash_message = st.session_state.pop("flash_message", None)
    if flash_message is None:
        return
    getattr(st, flash_message["kind"])(flash_message["text"])


if __name__ == "__main__":
    main()
