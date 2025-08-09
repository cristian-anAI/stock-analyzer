FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV SQLITE_DB_PATH=/app/data/trading.db

# Expose port for potential web interface
EXPOSE 8080

# Create startup script
RUN echo '#!/bin/bash\necho "🚀 Starting Trading System..."\necho "Time: $(date)"\necho "Python version: $(python --version)"\necho "Available modules:"\npython -c "import yfinance, pandas, requests; print(\"✅ All modules loaded\")" || echo "❌ Module error"\necho "Starting automated trader..."\npython automated_trader.py --mode=cloud\n' > /app/start.sh && chmod +x /app/start.sh

# Default command
CMD ["/app/start.sh"]
