FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose dashboard port
EXPOSE 8000

# Default entry point
ENTRYPOINT ["python", "cli/run_live.py"]
CMD ["--config", "config/config.yaml", "--paper"]
