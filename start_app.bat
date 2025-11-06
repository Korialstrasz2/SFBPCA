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
echo   2 ^) Alternate Relationship Companion ^(default after 2 seconds^)
choice /c 12 /n /t 1 /d 2 /m "Select option (1/2): "

if errorlevel 2 (
    echo Starting alternate Flask application...
    python -m new_impl.main
) else (
    echo Starting original Flask application...
    python app.py
)

ENDLOCAL
