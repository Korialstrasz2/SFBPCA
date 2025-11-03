# Salesforce Relationship Inspector

This project provides two complementary experiences for inspecting Salesforce
relationship data quality:

1. **Legacy Flask tool** – the original browser-based workflow for importing
   CSV extracts and reviewing alerts.
2. **Airflow application** – a configurable orchestration pipeline that loads
   Salesforce data, refreshes alerts, produces operational reports, creates
   backups, and stages future data-change automation tasks.

## Features

- Guided two-step workflow: upload CSV extracts, then review generated alerts.
- Dedicated importer that rebuilds relationships between Accounts, Contacts, Individuals,
  AccountContactRelations, ContactPointPhones, and ContactPointEmails entirely in memory.
- Alert engine that highlights:
  - Contacts on the same account who share the same role and full name.
  - Account-contact links that are missing a role.
  - Contacts with the same name but different roles on a single account.
  - Duplicate phone numbers or email addresses for a contact via Contact Points.
- Responsive UI built with HTML, CSS, and vanilla JavaScript modules for the import flow and alert board.

## Running the application

1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Launch the entry point: `python app.py`
4. Choose between the **Legacy Flask tool** or the **Airflow interactive
   console** when prompted (set `SRI_APP_MODE=legacy` or `SRI_APP_MODE=airflow`
   to skip the prompt).

The Airflow experience reuses the same core importer and alert engine while
adding orchestration-specific features:

- **Data loading** – reads CSV locations defined in `airflow_runtime/config/dataset_manifest.yml`.
- **Alert configuration & triggering** – leverages the existing alert logic and
  persists results in `airflow_runtime/artifacts/alerts.json`.
- **Reporting** – writes human-friendly Markdown and machine-readable JSON
  summaries to `airflow_runtime/reports/`.
- **Backups** – archives state, configuration, and latest artifacts into
  timestamped ZIP files under `airflow_runtime/backups/`.
- **Data changes (STILL TO BE IMPLEMENTED)** – prepares a catalog of contacts
  that could be reassigned to accounts marked with `CustomerMarking__c = "D1"`.

Run `python -m airflow_app.cli --run-once` to execute the full Airflow pipeline
without using the interactive menu.

## Data requirements

The importer expects CSV files exported from Salesforce that contain the following columns:

- **Account**: `Id`, `Name`
- **Contact**: `Id`, `FirstName`, `LastName`, `IndividualId`
- **Individual**: `Id`, `FirstName`, `LastName`
- **AccountContactRelation**: `Id`, `AccountId`, `ContactId`, `Roles`
- **ContactPointPhone**: `Id`, `ParentId`, `TelephoneNumber`
- **ContactPointEmail**: `Id`, `ParentId`, `EmailAddress`

Each upload fully refreshes the in-memory store and recalculates all relationships.

## Windows helper script

Use `start_app.bat` to set up the virtual environment (if needed), update dependencies, and start the Flask server.
