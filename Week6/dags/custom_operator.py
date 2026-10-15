from airflow.sdk import dag, BaseOperator, task
from datetime import datetime


class SlackMessageOperator(BaseOperator):
    def __init__(self, message, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def execute(self, context):
        print(f"Sending slack message: {self.message}")


@dag(dag_id="custom_operator_trigger_logic")
def demo_dag():
    @task(task_id="extract_data")
    def extract():
        print("data processing ...")
        upload_path = f"s3://var/data/hr/{datetime.now().strftime('%Y_%m_%d')}"
        print(f"data uploaded to {upload_path}")
        return upload_path

    @task(task_id="transform_csv_data")
    def transform_csv(upload_path):
        print("data processing ...")
        print(f"transforming csv from {upload_path}")
        return f"{upload_path}/csv"

    @task(task_id="transform_json_data")
    def transform_json(upload_path):
        print("data processing ...")
        print(f"transforming json from {upload_path}")
        return f"{upload_path}/json"

    @task(task_id="load_data")
    def load(csv_path, json_path):
        print(f"load {csv_path}")
        print(f"load {json_path}")

    notify = SlackMessageOperator(task_id="notify", message="pipeline done")

    # fan-out: both transforms depend on the same extract() result
    # fan-in: load waits for both transforms and receives both results
    path = extract()
    load_result = load(transform_csv(path), transform_json(path))

    # notify has no data dependency on load, so >> is the only way
    # to express "run after load" here
    load_result >> notify

demo_dag()