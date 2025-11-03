# Salesforce Relationship Inspector

This project now offers two complementary interfaces for managing Salesforce data quality:

1. **Legacy Flask tool** &ndash; the original guided web workflow for uploading CSV extracts and
   reviewing alerts inline.
2. **Airflow application** &ndash; a fully orchestrated data pipeline that automates ingestion,
   alert generation, reporting, backups, and placeholders for upcoming data change tooling.

## Features

- Guided two-step workflow: upload CSV extracts, then review generated alerts (legacy).
- Airflow DAG (`sfbpca_data_quality`) that ingests CSV extracts, refreshes the shared data store,
  runs the alert engine, generates operational reports, prepares backup archives, and creates
  placeholders for still-to-be-implemented data change operations.
- Dedicated importer that rebuilds relationships between Accounts, Contacts, Individuals,
  AccountContactRelations, ContactPointPhones, and ContactPointEmails entirely in memory.
- Alert engine that highlights:
  - Contacts on the same account who share the same role and full name.
  - Account-contact links that are missing a role.
  - Contacts with the same name but different roles on a single account.
  - Duplicate phone numbers or email addresses for a contact via Contact Points.
- Airflow reports that summarise account coverage and surface candidate contacts whose accounts
  share names with `CustomerMarking__c = "D1"` peers. These candidates are flagged with
  `"STILL TO BE IMPLEMENTED"` to illustrate the upcoming data change tooling.
- Responsive UI built with HTML, CSS, and vanilla JavaScript modules for the import flow and alert board.

## Running the application

1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Start the entry point: `python app.py`
4. Choose between **Legacy** and **Airflow** modes when prompted (or pass `--mode legacy` /
   `--mode airflow`).

### Legacy mode

The behaviour matches prior versions of the project. After choosing legacy mode the Flask server is
available at `http://localhost:5000`.

### Airflow mode

The entry point initialises an isolated Airflow home and launches `airflow standalone`. The key
resources are:

- **DAG ID**: `sfbpca_data_quality`
- **DAG folder**: `airflow_app/dags`
- **Configuration**: `airflow_app/config/sfbpca_config.json` (override with the `SFBPCA_CONFIG`
  environment variable or the Airflow Variable `sfbpca_config_path`).

The default configuration expects CSV files named after each entity (for example `accounts.csv`,
`contacts.csv`, etc.) placed inside the configured `source_dir`. Outputs such as alert payloads,
reports, manifests, and timestamped backups are written under the `reports_dir` and `backup_dir`
paths respectively.

The Airflow DAG performs the following steps:

1. Load configuration and ensure the runtime directories exist.
2. Read CSV extracts for every supported entity.
3. Rebuild the in-memory data store and persist it as a JSON snapshot.
4. Execute the existing alert engine and store the results under `reports/alerts.json`.
5. Produce operational reports (`reports/account_report.json`).
6. Create `reports/data_change_candidates.json`, identifying contacts that could be reassigned to
   accounts with the same name and a `CustomerMarking__c` of `D1`. Every candidate is marked with
   a `"STILL TO BE IMPLEMENTED"` status to highlight future work.
7. Package the snapshot and generated artifacts into a timestamped backup folder.
8. Emit a manifest describing the run inputs and outputs.

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

Use `start_app.bat` to set up the virtual environment (if needed), update dependencies, and start the
entry point script. The batch file accepts the same `--mode` flag as `python app.py`.
