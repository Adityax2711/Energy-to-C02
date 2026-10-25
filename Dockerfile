FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL="sqlite:///./energy_to_co2.db"
ENV DEFAULT_REGION="US-EAST"
ENV DEFAULT_PUE=1.20

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
