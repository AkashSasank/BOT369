```shell
pip install -r requirements.txt
```

```shell
alembic revision --autogenerate
```

```shell
alembic upgrade head
```

```shell
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --reload
```