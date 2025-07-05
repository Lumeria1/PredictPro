FROM python:alpine
WORKDIR /app
COPY requirements.txt ./
COPY alembic.ini ./
COPY alembic/ ./alembic/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]