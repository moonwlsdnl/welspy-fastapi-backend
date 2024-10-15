FROM python:3.12.7

RUN pip install poetry

WORKDIR /fastapi_backend

COPY pyproject.toml poetry.lock /fastapi_backend/

RUN poetry install --no-root

COPY ./app /fastapi_backend/app

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

