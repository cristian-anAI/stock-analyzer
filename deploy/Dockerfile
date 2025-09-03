# Multi-stage build for smaller image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ ./src/
COPY trading.db ./
COPY run_api.py ./
COPY CLAUDE.md ./

# Create logs directory
RUN mkdir -p logs

# Set environment variables for production
ENV ENVIRONMENT=production
ENV AUTOTRADER_ENABLED=true
ENV LOG_LEVEL=INFO
ENV PORT=8080
ENV PYTHONPATH=/app

# Add local packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Start the application
CMD ["python", "run_api.py", "--host", "0.0.0.0", "--port", "8080"]
