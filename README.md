# Salesforce Relationship Inspector

This project provides a small Flask web application that guides the user through importing
Salesforce CSV extracts and reviewing relationship-driven data quality alerts.

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
3. Launch the development server: `python app.py`
4. Open `http://localhost:5000` in your browser.

## Data requirements

The importer expects CSV files exported from Salesforce that contain the following columns:

- **Account**: `Id`, `Name`
- **Contact**: `Id`, `FirstName`, `LastName`, `IndividualId`
- **Individual**: `Id`, `FirstName`, `LastName`
- **AccountContactRelation**: `Id`, `AccountId`, `ContactId`, `Role`
- **ContactPointPhone**: `Id`, `ParentId`, `PhoneNumber`
- **ContactPointEmail**: `Id`, `ParentId`, `EmailAddress`

Each upload fully refreshes the in-memory store and recalculates all relationships.

## Windows helper script

Use `start_app.bat` to set up the virtual environment (if needed), update dependencies, and start the Flask server.
