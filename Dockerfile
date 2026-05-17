FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/        ./app/
COPY alembic.ini ./alembic.ini
COPY migrations/ ./migrations/

EXPOSE 8000

# --reload lets uvicorn pick up source changes mounted via docker-compose volume
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
