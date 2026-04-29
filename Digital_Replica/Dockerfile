FROM python:3.9-slim

WORKDIR /app


COPY ./Digital_Replica/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./Digital_Replica/ .


COPY . .

EXPOSE 5000

CMD ["python", "app.py"]