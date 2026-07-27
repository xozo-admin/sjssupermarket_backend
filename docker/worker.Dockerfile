FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY app ./app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["celery", "-A", "app.jobs.celery_app:celery_app", "worker", "--loglevel=info"]
