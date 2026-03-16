# ─────────────────────────────────────────────────────────────
# EYEQ – Production Dockerfile
# Multi-stage: builder → runtime
# ─────────────────────────────────────────────────────────────

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools (needed for some C extensions like bcrypt, OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --user --no-cache-dir -r requirements.txt


# Stage 2: Runtime image
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application source
COPY . .

# Create required runtime directories
RUN mkdir -p alert_images logs detection/models

# Expose API and dashboard ports
EXPOSE 8000 8501

# Default: start FastAPI backend
# Override CMD in docker-compose to run Streamlit
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
