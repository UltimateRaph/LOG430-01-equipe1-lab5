FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY locustfiles/ /mnt/locust/
COPY singleton.py ./
COPY src/ ./src/
COPY pyproject.toml ./

WORKDIR /app/src
CMD ["python", "store_manager.py"]
