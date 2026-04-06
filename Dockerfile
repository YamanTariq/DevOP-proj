# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1

WORKDIR /app

# Create a non-root user for safer container runtime.
RUN groupadd --system app && useradd --system --gid app --create-home app

# Install Python dependencies first to maximize Docker layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip && \
	pip install -r requirements.txt && \
	pip install gunicorn

COPY . .

RUN chown -R app:app /app
USER app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "60", "app:app"]