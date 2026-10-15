from airflow.sdk import DAG
import time
from airflow.providers.standard.operators.python import PythonOperator
from datetime import timedelta
import datetime

def task_extract():
    print("data processing ...")
    upload_path = f"s3://var/data/hr/{datetime.datetime.now().strftime('%Y_%m_%d')}"
    print("data uploaded to  {upload_path}")
    return upload_path


def task_transform1(**context):
    path = context["ti"].xcom_pull(task_ids="extract")
    print(f"processing file from {path}")
    row_count = 100
    context["ti"].xcom_push(key = 'rows', value = row_count)
    print("transform")

def task_transform2():
    time.sleep(5)
    print("transform 2")


def task_load(**context):
    row_count_trasnform = context["ti"].xcom_pull(task_ids="transform1",key="rows")

    print(f"loading {row_count_trasnform} data ")

with DAG(dag_id='xcom_demo') as dag:
    extract = PythonOperator(task_id="extract",python_callable=task_extract)
    trasnform1 = PythonOperator(task_id="transform1", python_callable=task_transform1,retries=3,retry_delay=timedelta(seconds= 5))
    trasnform2 = PythonOperator(task_id="transform2",python_callable=task_transform2)

    load = PythonOperator(task_id="load",python_callable=task_load)
    extract >> [trasnform1,trasnform2] >> load
