# Production Dockerfile for Stock Analyzer API
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/
COPY run_api.py .
COPY main.py .
# Copy archive directory for stock lists
COPY archive/ ./archive/

# Create necessary directories
RUN mkdir -p /app/src/logs \
    && mkdir -p /app/data \
    && mkdir -p /app/reports \
    && chmod 755 /app/data

# Create production startup script
RUN echo '#!/bin/bash\n\
echo "🚀 Stock Analyzer API - Production Mode"\n\
echo "Time: $(date)"\n\
echo "Python version: $(python --version)"\n\
echo "Database path: ${SQLITE_DB_PATH:-trading.db}"\n\
echo ""\n\
echo "🔧 Checking dependencies..."\n\
python -c "import yfinance, pandas, fastapi, uvicorn; print(\"✅ All dependencies OK\")" || { echo "❌ Dependency error"; exit 1; }\n\
echo ""\n\
echo "🗄️  Checking database directory..."\n\
mkdir -p "$(dirname "${SQLITE_DB_PATH:-trading.db}")" && echo "✅ Database directory ready"\n\
echo ""\n\
echo "🗄️  Initializing database..."\n\
python -c "from src.api.database.database import init_db, DATABASE_PATH; print(f\"Database location: {DATABASE_PATH}\"); init_db(); print(\"✅ Database ready\")" || { echo "❌ Database error"; exit 1; }\n\
echo ""\n\
echo "🌐 Starting FastAPI server..."\n\
cd /app && python run_api.py\n\
' > /app/start_production.sh && chmod +x /app/start_production.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Add labels for better organization
LABEL maintainer="Stock Analyzer API"
LABEL version="2.0"
LABEL description="Automated stock and crypto trading system with SHORT support"

# Default command
CMD ["/app/start_production.sh"]