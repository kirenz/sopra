# B2B Discount CRUD Demo

This repository contains a complete classroom demo for a small enterprise-style Python application. The example uses Microsoft SQL Server, a clear three-layer architecture, and a Streamlit frontend so students can see how a real CRUD workflow is structured.

## Tech Stack

- Python 3.13
- `uv` for dependency and environment management
- `pandas` for tabular reads
- `sqlalchemy` + `pyodbc` for the MSSQL connection
- `python-dotenv` for credential management
- Streamlit for the presentation layer
- Quarto for the accompanying step-by-step book

## Project Structure

```text
.
├── app.py
├── main.py
├── models/
│   └── discount.py
├── repositories/
│   ├── db.py
│   └── discount_repo.py
├── services/
│   └── discount_service.py
├── sql_example.py
├── .env.example
└── *.qmd
```

## Setup

1. Install Python 3.13, `uv`, and the Microsoft ODBC Driver 18 for SQL Server.
2. Sync the project dependencies:

   ```bash
   uv sync
   ```

3. Create your local credential file:

   ```bash
   cp .env.example .env
   ```

4. Open `.env` and add the course-specific SQL Server credentials.
5. Test the connection from the terminal:

   ```bash
   uv run python sql_example.py
   ```

6. Start the Streamlit application:

   ```bash
   uv run streamlit run app.py
   ```

## What the Demo Shows

- `List`: reads discount data from `list_views.V_LIST_B2B_DISCOUNT`
- `Create`: inserts new discounts through `ins_views.V_INS_B2B_DISCOUNT`
- `Edit`: updates existing discounts through `upd_views.V_UPD_B2B_DISCOUNT`
- `LOV`: loads dropdown values from `dbo.LOV_CUSTOMER`

The business layer validates quantity ranges, date ranges, percentage values, and overlapping discounts before SQL Server receives a write request.

## Quarto Book

The Quarto book explains the setup and architecture in more detail.

```bash
quarto preview
```

To create the static book output:

```bash
quarto render
```
