"""Simple console example for the MSSQL B2B discount views."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from repositories.db import get_engine


LIST_QUERY = text(
    """
    SELECT TOP (5)
        RabattID,
        Kunde,
        MengeVon,
        MengeBis,
        RabattProzent,
        GiltVon,
        GiltBis
    FROM list_views.V_LIST_B2B_DISCOUNT
    ORDER BY RabattID DESC;
    """
)

CUSTOMER_QUERY = text(
    """
    SELECT TOP (5)
        CUSTOMER_ID,
        CUSTOMER_LONG
    FROM dbo.LOV_CUSTOMER
    ORDER BY CUSTOMER_ID;
    """
)


def main() -> None:
    """Connect to SQL Server, print the version, and show sample data."""

    engine = get_engine()

    with engine.connect() as connection:
        version = connection.execute(text("SELECT @@VERSION AS version;")).scalar_one()
        discounts = pd.read_sql(LIST_QUERY, connection)
        customers = pd.read_sql(CUSTOMER_QUERY, connection)

    print("Connection successful.")
    print("SQL Server version:")
    print(version)

    print("\nLatest discounts:")
    print(discounts.to_string(index=False))

    print("\nCustomer LOV sample:")
    print(customers.to_string(index=False))


if __name__ == "__main__":
    main()
