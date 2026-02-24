FROM python:3.12-slim

WORKDIR /app

# System dependencies for PyMuPDF and python-magic
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./services/

# Default: run the data prep script (one-step download + extract + index)
# Override with: docker compose run pipeline python -m services.pipeline --verbose
CMD ["python", "-m", "services.data_prep", "--verbose"]
