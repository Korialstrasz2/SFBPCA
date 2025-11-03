@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

IF NOT EXIST venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

CALL venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo Updating repository...
git pull

echo Starting Salesforce Relationship Inspector (select Legacy or Airflow mode)...
python app.py

ENDLOCAL
