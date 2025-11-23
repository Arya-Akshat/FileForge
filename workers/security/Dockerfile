FROM python:3.11-slim

WORKDIR /app

# Install ClamAV
RUN apt-get update && apt-get install -y \
    clamav \
    clamav-daemon \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY . .

# Update ClamAV database and start daemon in background
RUN freshclam || true

# Create ClamAV socket directory with proper permissions
RUN mkdir -p /var/run/clamav && chown -R clamav:clamav /var/run/clamav

CMD ["sh", "-c", "clamd & python worker.py"]
