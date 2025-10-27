# Salesforce Relationship Analyzer

A lightweight Flask web application for analysing Salesforce Account, Contact, AccountContactRelation, Individual, ContactPointPhone, and ContactPointEmail exports. Upload the CSV files, recreate the in-memory relationships, and evaluate configurable alerts for common data quality scenarios.

## Getting started

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

   ```bash
   pip install flask
   ```

3. Run the development server:

   ```bash
   flask --app app run --debug
   ```

4. Open the application in your browser at <http://localhost:5000>.

## Usage

1. Navigate to the **Import data** section and provide the CSV exports for each Salesforce object.
2. After a successful import, choose the alerts you would like to evaluate in the **Alerts** section.
3. Review the alert output to identify duplicate roles, missing roles, conflicting assignments, and contact point mismatches.

## Alerts summary

| Identifier | Description |
| ---------- | ----------- |
| `duplicate_role_same_name` | Contacts that share the same first/last name and role within the same account. |
| `missing_role` | Contacts related to an account without a specified role. |
| `conflicting_roles_same_name` | Contacts with matching first/last names but different roles on the same account. |
| `contact_point_mismatch` | Contacts whose phone or email do not match contact point records associated with their Individual. |

## Project structure

```
app.py
services/
  alert_service.py
  import_service.py
static/
  css/styles.css
  js/alerts.js
  js/import.js
storage/
  data_store.py
templates/
  index.html
```

The code is organised so that the import workflow and alerts each have dedicated JavaScript modules and backend service classes, making it easier to extend the application with additional behaviours or alert rules.
