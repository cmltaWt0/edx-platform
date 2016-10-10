from celery.task import task

from api_calls import APICalls


@task()
def send_api_request(data):
    APICalls().api_call(**data)
