FROM python:3.10-slim

# Prevent python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (ffmpeg, build tools, curl, gnupg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (needed for Playwright browsers execution)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements first
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and system dependencies
RUN playwright install chromium
RUN playwright install-deps

# Copy backend source code
COPY backend/ .

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
