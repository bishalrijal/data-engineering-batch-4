import time
import datetime
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG


def slow_task():
    print("working...")
    time.sleep(20)
    print("done")


# Fixed start date (not a runtime-computed one) so DAG parsing is
# deterministic; catchup=True still backfills everything since this date.
with DAG(
    dag_id="max_active_runs_demo_1",
    schedule="*/1 * * * *",
    start_date=datetime.datetime(2026, 10, 13, 16, 0),
    catchup=True,
    max_active_runs=1,
) as dag:
    step1 = PythonOperator(task_id="step1", python_callable=slow_task)
    step2 = PythonOperator(task_id="step2", python_callable=slow_task)
    step1 >> step2
