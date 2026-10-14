from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
import time
from datetime import timedelta
import datetime

def task_extract():
    print("extract")


def task_transform1():
    print("transform")

def task_transform2():
    time.sleep(5)
    print("transform 2")


def task_load():
    print("load")

    
with DAG(dag_id='my_first_dag', schedule='*/1 * * * *',start_date=datetime.datetime(2026, 10, 13, 16, 0),) as dag:
    extract = BashOperator(task_id="extract",bash_command="echo 'extracting from bash'")
    trasnform1 = PythonOperator(task_id="transform1", python_callable=task_transform1,retries=3,retry_delay=timedelta(seconds= 5))
    trasnform2 = PythonOperator(task_id="transform2",python_callable=task_transform2)

    load = SQLExecuteQueryOperator(task_id="load",sql=["select 'load from sql'"],conn_id="ride_sharing_warehouse")
    extract >> [trasnform1,trasnform2] >> load
    # load(trasnform(extract()))