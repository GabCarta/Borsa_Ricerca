FROM python:3.9-slim

WORKDIR /app


COPY ./Service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./Service/ .



CMD ["python", "./app.py"]