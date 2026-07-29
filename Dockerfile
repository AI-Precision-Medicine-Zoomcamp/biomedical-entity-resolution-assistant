FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if any are needed in the future
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging configuration files first to cache layers
COPY pyproject.toml README.md ./

# Install dependencies in editable mode for development, or standard mode
RUN pip install --no-cache-dir .

# Copy everything else
COPY . .

# Expose the API port
EXPOSE 8000

# Set entrypoint to run the FastAPI application
CMD ["python", "main.py"]
