FROM python:3.11-slim

# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm

# Setup backend
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/ ./

# Setup frontend  
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm install && npm run build

WORKDIR /app
CMD python app.py