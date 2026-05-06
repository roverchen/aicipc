# Stage 1: Build Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install sqlalchemy uvicorn fastapi typer rich requests # Ensure all deps

COPY src/ ./src/
COPY --from=frontend-builder /app/frontend/dist ./static

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Start command (serving static files via FastAPI)
CMD ["python", "-m", "src.control_plane.server"]
