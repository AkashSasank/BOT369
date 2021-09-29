import json
from celery import shared_task


@shared_task(name='save json file')
def save_json(filename, data):
    with open(filename, mode='w') as f:
        json.dump(data, f)
