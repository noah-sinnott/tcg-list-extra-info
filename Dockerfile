# Multi-stage build for Google Cloud Run
# Stage 1: Build frontend
FROM node:18-alpine AS frontend-build

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy frontend source
COPY frontend/ ./

# Build the React app
RUN npm run build

# Stage 2: Setup Python backend and serve frontend
FROM python:3.11-slim

# Install Chrome and ChromeDriver dependencies for Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend from previous stage
COPY --from=frontend-build /frontend/build ./static

# Create cache directory
RUN mkdir -p cache

EXPOSE 8080

# Run the Flask app
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
