from celery.task import task

from api_calls import APICalls


# Uncomment this after demo
# @task()
def send_api_request(data):
    APICalls().api_call(**data)
