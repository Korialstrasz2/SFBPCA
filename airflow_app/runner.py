"""Helper to run the Airflow application in standalone mode."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from airflow_app.config import AirflowAppConfig, DEFAULT_CONFIG_PATH


def launch_airflow_app(config_path: Optional[str] = None) -> None:
    """Launch the Airflow webserver and scheduler in standalone mode."""

    config = AirflowAppConfig.load(config_path or DEFAULT_CONFIG_PATH)
    dags_folder = Path(__file__).resolve().parent / "dags"

    env = os.environ.copy()
    env["AIRFLOW_HOME"] = str(config.airflow_home)
    env.setdefault("SFBPCA_CONFIG", str(config_path or DEFAULT_CONFIG_PATH))
    env.setdefault("AIRFLOW__CORE__DAGS_FOLDER", str(dags_folder))
    env.setdefault("AIRFLOW__CORE__LOAD_DEFAULT_CONNECTIONS", "False")
    env.setdefault("AIRFLOW__CORE__UNIT_TEST_MODE", "False")

    print("Starting Airflow standalone environment...")
    print(f" - AIRFLOW_HOME: {env['AIRFLOW_HOME']}")
    print(f" - DAGs folder: {env['AIRFLOW__CORE__DAGS_FOLDER']}")
    print(f" - Configuration: {env['SFBPCA_CONFIG']}")
    print("Airflow credentials will be printed by the standalone command if this is the first run.")

    try:
        subprocess.run([sys.executable, "-m", "airflow", "standalone"], check=True, env=env)
    except FileNotFoundError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "Unable to start Airflow. Ensure apache-airflow is installed and available in this environment."
        ) from exc
    except subprocess.CalledProcessError as exc:  # pragma: no cover - surfaced to the CLI
        raise RuntimeError("Airflow standalone exited with a non-zero status") from exc


__all__ = ["launch_airflow_app"]
