FROM python:3.12-slim

WORKDIR /app

# System dependencies for PyMuPDF and python-magic
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./services/

# Run as module so relative imports work
CMD ["python", "-m", "services.pipeline", "--verbose"]
