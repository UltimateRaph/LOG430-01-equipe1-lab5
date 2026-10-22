FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY locustfiles/ /mnt/locust/
COPY src/ ./src/
COPY pyproject.toml ./

WORKDIR /app/src
CMD ["python", "store_manager.py"]
