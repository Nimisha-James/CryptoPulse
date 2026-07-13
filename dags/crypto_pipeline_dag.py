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

    check_setup = BashOperator(
        task_id="check_setup",
        bash_command="echo 'Airflow is wired up and can run tasks' && date",
    )
