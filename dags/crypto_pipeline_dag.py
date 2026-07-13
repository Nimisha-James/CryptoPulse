from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "data_eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="crypto_daily_pipeline",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["crypto", "portfolio-project"],
) as dag:

    install_deps = BashOperator(
        task_id="install_deps",
        bash_command="pip install --quiet boto3 pandas pyarrow psycopg2-binary",
    )

    load_staging = BashOperator(
        task_id="load_raw_to_staging",
        bash_command="python /opt/airflow/dags/scripts/load_parquet_to_staging.py",
    )

    install_deps >> load_staging