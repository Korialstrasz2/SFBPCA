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

echo Choose the application to launch:
echo   1 ^) Original Salesforce Relationship Inspector
echo   2 ^) Companion Salesforce moderno
set /p APP_CHOICE=Select option (1/2): 

if /I "!APP_CHOICE!"=="2" (
    echo Avvio del Companion Salesforce moderno...
    python -m modern_app.main
) else (
    echo Starting original Flask application...
    python app.py
)

ENDLOCAL
