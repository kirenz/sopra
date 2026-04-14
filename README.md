# B2B Discount CRUD Demo

Use this repository to learn how to build a small enterprise-style CRUD application against Microsoft SQL Server with the help of `uv`, SQLAlchemy, pandas, and Streamlit.

The application demonstrates a B2B discount maintenance workflow with a clear separation between presentation layer, business logic, and data access.

> [!IMPORTANT]
> You need to have uv installed on your machine (go to [this repo](https://github.com/kirenz/uv-setup) for installation instructions).

## Recommended warm-up

Before working in this full project, students should use the two smaller repositories first:

1. [mssql-example](https://github.com/kirenz/mssql-example): test a plain Python connection to Microsoft SQL Server.
2. [streamlit-mssql](https://github.com/kirenz/streamlit-mssql): run a small Streamlit app against SQL Server.
3. [sopra](https://github.com/kirenz/sopra): study the full layered CRUD application.

This order helps separate setup problems from application design problems.

## Step-by-step instructions

If you are on macOS, open the built-in **Terminal** app. On Windows, open **Git Bash**.

1. Clone the repository

   ```bash
   git clone https://github.com/kirenz/sopra.git
   ```

   Change into the repository folder

   ```bash
   cd sopra
   ```

   If you do not use Git, download the project as a ZIP file:

   [Download ZIP](https://github.com/kirenz/sopra/archive/refs/heads/main.zip)

2. Sync the Python environment defined in `pyproject.toml`

   ```bash
   uv sync
   ```

   This installs Streamlit, pandas, SQLAlchemy, the SQL Server driver bindings, and all other required packages in an isolated environment managed by `uv`.

3. Prepare your environment variables

   ```bash
   cp .env.example .env
   ```

   This command copies the example file and creates a new local `.env` file.

4. Open VS Code in the current folder

   ```bash
   code .
   ```

   You can also open the folder manually from within VS Code.

   Open the new `.env` file and replace the placeholder values with the SQL Server hostname, database, username, password, driver, and account information provided by your instructor.

   `APP_USER` should contain your HdM account name. The app writes this value into audit fields when you create or update discount records.

5. Test the SQL Server connection

   ```bash
   uv run python sql_example.py
   ```

   The script prints the SQL Server version and loads sample rows from the views used by the application.

6. Launch the Streamlit CRUD app

   ```bash
   uv run streamlit run app.py
   ```

   If you are asked to provide your email, you can simply press Enter to skip this step.

   Streamlit prints a local URL (typically `http://localhost:8501`). Open it in your browser to load the app.

7. Test the CRUD workflow

   Use the tabs in the app to list, create, and edit B2B discount records. The app validates user input before sending write requests to SQL Server.

## Files

- `app.py` - Streamlit app with the user interface for listing, creating, and editing discounts.
- `sql_example.py` - standalone SQL Server connection test before launching the full app.
- `.env.example` - template with placeholders for your connection parameters. Copy this to `.env` and update the values before running the app.
  `APP_USER` identifies the logical application user written into audit fields during create and edit operations.
- `models/discount.py` - domain data structure for discount records.
- `repositories/db.py` - SQLAlchemy connection setup.
- `repositories/discount_repo.py` - data access code for reading, inserting, and updating discount data.
- `services/discount_service.py` - business logic and validation rules.
- `pyproject.toml` - dependency definition for `uv sync`. Don't edit this file directly; use `uv add <package>` to add new packages.
- `*.qmd` - Quarto book chapters that explain the setup and architecture step by step.

## Database objects used

- `list_views.V_LIST_B2B_DISCOUNT` - read discount overview data.
- `ins_views.V_INS_B2B_DISCOUNT` - insert new discount records.
- `upd_views.V_UPD_B2B_DISCOUNT` - update existing discount records.
- `dbo.LOV_CUSTOMER` - load customer values for dropdown fields.

## Python packages used

- `streamlit` - renders the browser-based user interface.
- `sqlalchemy` - builds the connection engine and executes SQL statements.
- `pyodbc` - provides the ODBC driver bindings that let Python talk to Microsoft SQL Server.
- `pandas` - turns query results into DataFrames so they can be displayed and inspected.
- `python-dotenv` - reads connection values from the `.env` file into environment variables before the scripts run.

## Quarto book

The Quarto book explains the setup and architecture in more detail.

Preview the book locally:

```bash
quarto preview
```

Create the static book output:

```bash
quarto render
```
