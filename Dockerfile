# Stage 1: Build the Vite frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
RUN npm run build
# output is at /app/frontend/dist

# Stage 2: Python backend + serve static frontend
FROM python:3.11-slim

WORKDIR /app

# System deps required by scanpy / leidenalg / h5py
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libhdf5-dev \
    pkg-config \
    libigraph-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer-cached)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy built frontend into static/ so FastAPI can serve it
COPY --from=frontend-builder /app/frontend/dist ./static

# Railway / Render inject $PORT at runtime
ENV PORT=8000
EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
