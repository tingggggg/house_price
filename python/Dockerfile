FROM python:3.11-slim

WORKDIR /app

COPY python/requirements.txt python/requirements.txt
RUN pip install --no-cache-dir -r python/requirements.txt

COPY python/ python/

WORKDIR /app/python

ENTRYPOINT ["python", "run_pipeline.py"]
