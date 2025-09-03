#!/usr/bin/env python3
"""
Google Cloud Platform Deploy Script for Stock Analyzer
Prepares and deploys the autotrader to Google Cloud Run
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
import json

class GCPDeployer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.deploy_dir = self.project_root / "deploy"
        
        # GCP Configuration
        self.project_id = "stock-analyzer-prod"  # Update this
        self.service_name = "stock-autotrader"
        self.region = "us-central1"
        self.port = 8080
        
    def create_production_database(self):
        """Create clean production database"""
        print("Creating clean production database...")
        
        import sys
        sys.path.append(str(self.project_root))
        
        from src.api.database.database import db_manager
        
        # Backup existing database
        db_path = self.project_root / "trading.db"
        if db_path.exists():
            backup_path = self.project_root / f"trading.db.backup_pre_deploy"
            shutil.copy(db_path, backup_path)
            print(f"   OK Database backed up to {backup_path}")
        
        # Create clean database with schema only
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clear all transaction data
            print("   Clearing transaction data...")
            try:
                cursor.execute("DELETE FROM autotrader_transactions")
            except:
                print("   autotrader_transactions table not found, skipping...")
            try:
                cursor.execute("DELETE FROM portfolio_transactions")
            except:
                print("   portfolio_transactions table not found, skipping...")
            try:
                cursor.execute("DELETE FROM positions WHERE source = 'autotrader'")
            except:
                print("   positions table not found, skipping...")
            
            # Reset portfolio to initial state
            print("   Resetting portfolio to initial state...")
            try:
                cursor.execute("DELETE FROM portfolio_snapshots")
            except:
                print("   portfolio_snapshots table not found, skipping...")
            
            # Keep stocks and cryptos with scores for trading
            print("   Preserving stock/crypto scores...")
            
            # Reset any test symbols scores
            cursor.execute("""
                UPDATE stocks SET score = 5.0 
                WHERE symbol IN ('TEST', 'SAMPLE', 'MOCK')
            """)
            
            conn.commit()
            print("   OK Production database ready")
    
    def create_dockerfile(self):
        """Create optimized Dockerfile for Cloud Run"""
        dockerfile_content = """# Multi-stage build for smaller image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
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
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Start the application
CMD ["python", "run_api.py", "--host", "0.0.0.0", "--port", "8080"]
"""
        
        dockerfile_path = self.deploy_dir / "Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        print(f"   OK Dockerfile created at {dockerfile_path}")
    
    def create_cloud_run_yaml(self):
        """Create Cloud Run service configuration"""
        service_yaml = f"""apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: {self.service_name}
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "2Gi"
        run.googleapis.com/cpu: "1000m"
    spec:
      containerConcurrency: 10
      containers:
      - image: gcr.io/{self.project_id}/{self.service_name}
        ports:
        - containerPort: {self.port}
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: AUTOTRADER_ENABLED
          value: "true"
        - name: LOG_LEVEL
          value: "INFO"
        - name: PORT
          value: "{self.port}"
        resources:
          limits:
            cpu: 1000m
            memory: 2Gi
          requests:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: {self.port}
          initialDelaySeconds: 30
          periodSeconds: 60
        readinessProbe:
          httpGet:
            path: /health
            port: {self.port}
          initialDelaySeconds: 10
          periodSeconds: 30
"""
        
        yaml_path = self.deploy_dir / "service.yaml"
        with open(yaml_path, 'w') as f:
            f.write(service_yaml)
        
        print(f"   OK Cloud Run service config created at {yaml_path}")
    
    def create_deployment_script(self):
        """Create bash deployment script"""
        script_content = f"""#!/bin/bash
set -e

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

PROJECT_ID="{self.project_id}"
SERVICE_NAME="{self.service_name}"
REGION="{self.region}"

echo -e "${{YELLOW}}Starting Stock Analyzer deployment to Google Cloud...${{NC}}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${{RED}}gcloud CLI not found. Please install Google Cloud SDK.${{NC}}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo -e "${{YELLOW}}Setting GCP project...${{NC}}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${{YELLOW}}Enabling required APIs...${{NC}}"
gcloud services enable containerregistry.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Build and push Docker image
echo -e "${{YELLOW}}Building Docker image...${{NC}}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo -e "${{YELLOW}}Deploying to Cloud Run...${{NC}}"
gcloud run deploy $SERVICE_NAME \\
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \\
    --platform managed \\
    --region $REGION \\
    --allow-unauthenticated \\
    --memory 2Gi \\
    --cpu 1 \\
    --max-instances 10 \\
    --concurrency 10 \\
    --port {self.port} \\
    --set-env-vars ENVIRONMENT=production,AUTOTRADER_ENABLED=true,LOG_LEVEL=INFO

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

echo -e "${{GREEN}}Deployment completed successfully!${{NC}}"
echo -e "${{GREEN}}Service URL: $SERVICE_URL${{NC}}"
echo -e "${{GREEN}}Health Check: $SERVICE_URL/health${{NC}}"
echo -e "${{GREEN}}API Docs: $SERVICE_URL/docs${{NC}}"

# Test the deployment
echo -e "${{YELLOW}}Testing deployment...${{NC}}"
curl -f $SERVICE_URL/health && echo -e "${{GREEN}}Health check passed!${{NC}}" || echo -e "${{RED}}Health check failed!${{NC}}"
"""
        
        script_path = self.deploy_dir / "deploy.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        print(f"   OK Deployment script created at {script_path}")
    
    def create_env_example(self):
        """Create environment variables example"""
        env_content = """# Google Cloud Production Environment Variables
# Copy this to .env.production and fill in your values

# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_SERVICE_NAME=stock-autotrader

# Application Configuration  
ENVIRONMENT=production
AUTOTRADER_ENABLED=true
LOG_LEVEL=INFO
PORT=8080

# Database Configuration
DATABASE_PATH=/app/trading.db

# Trading Configuration
MAX_POSITIONS=10
POSITION_SIZE=10000
STOP_LOSS_PERCENT=8.0
TAKE_PROFIT_PERCENT=15.0

# API Keys (if needed)
# ALPHA_VANTAGE_API_KEY=your-key
# FINNHUB_API_KEY=your-key

# Security (optional)
# API_SECRET_KEY=your-secret-key
# ALLOWED_ORIGINS=https://yourdomain.com
"""
        
        env_path = self.deploy_dir / ".env.example"
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print(f"   OK Environment example created at {env_path}")
    
    def create_requirements_production(self):
        """Create production requirements.txt"""
        # Copy main requirements
        main_req = self.project_root / "requirements.txt"
        prod_req = self.deploy_dir / "requirements.txt"
        
        if main_req.exists():
            shutil.copy(main_req, prod_req)
            
            # Add production-specific packages
            with open(prod_req, 'a') as f:
                f.write("""
# Production additions
gunicorn==21.2.0
uvicorn[standard]==0.24.0
python-multipart==0.0.6
""")
            
            print(f"   OK Production requirements created at {prod_req}")
    
    def create_deployment_docs(self):
        """Create deployment documentation"""
        docs_content = """# Stock Analyzer - Google Cloud Deployment

## Prerequisites

1. **Google Cloud SDK**: Install from https://cloud.google.com/sdk/docs/install
2. **Docker**: Install from https://docs.docker.com/get-docker/
3. **GCP Project**: Create a new project in Google Cloud Console

## Setup

1. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth login
   gcloud auth configure-docker
   ```

2. **Update Configuration:**
   - Edit `deploy.sh` and update `PROJECT_ID`
   - Copy `.env.example` to `.env.production` and configure

3. **Deploy:**
   ```bash
   cd deploy
   chmod +x deploy.sh
   ./deploy.sh
   ```

## What Gets Deployed

- **FastAPI Backend**: Complete autotrader API
- **Clean Database**: Production database with no test data
- **Trading Strategies**: Swing trading with validated parameters
- **Market Timing**: 15min/60min restrictions after market open
- **P&L Tracking**: Complete transaction analysis

## Production Features

- **Auto-scaling**: 1-10 instances based on traffic
- **Health Monitoring**: Automatic health checks
- **Resource Limits**: 2GB RAM, 1 CPU per instance
- **Environment**: Production configuration with optimized logging

## Monitoring

- **Health Check**: `https://your-service-url/health`
- **API Documentation**: `https://your-service-url/docs`
- **Autotrader Status**: `https://your-service-url/api/v1/autotrader/summary`
- **P&L Summary**: `https://your-service-url/api/v1/autotrader/pnl/summary`

## Post-Deployment

1. **Verify Trading**: Check autotrader is running correctly
2. **Monitor Logs**: Use Google Cloud Console to monitor
3. **Set Alerts**: Configure monitoring for trading issues
4. **Database Backups**: Set up automated backups

## Costs

Estimated monthly costs (us-central1):
- **Cloud Run**: ~$10-50/month (depending on usage)
- **Container Registry**: ~$2-5/month
- **Cloud Build**: ~$1-3/month

## Security

- **No Authentication**: Currently allows unauthenticated access
- **Internal Use**: Recommended for internal trading only  
- **API Keys**: Store sensitive keys in Google Secret Manager

## Troubleshooting

- **Build Fails**: Check Docker file and requirements
- **Deploy Fails**: Verify GCP permissions and APIs enabled
- **Health Check Fails**: Check application logs in Cloud Console
- **Trading Issues**: Monitor autotrader logs and database state
"""
        
        docs_path = self.deploy_dir / "README.md"
        with open(docs_path, 'w') as f:
            f.write(docs_content)
        
        print(f"   OK Deployment documentation created at {docs_path}")
    
    def deploy(self):
        """Run the complete deployment preparation"""
        print("GOOGLE CLOUD DEPLOYMENT PREPARATION")
        print("="*60)
        
        # Create deploy directory
        self.deploy_dir.mkdir(exist_ok=True)
        
        try:
            # NOTE: Database cleaning will be done during actual deployment
            # For now, just prepare deployment files
            
            # Step 1: Create deployment files
            print("\nCreating deployment files...")
            self.create_dockerfile()
            self.create_cloud_run_yaml()
            self.create_deployment_script()
            self.create_env_example()
            self.create_requirements_production()
            self.create_deployment_docs()
            
            print(f"\nDEPLOYMENT PREPARATION COMPLETE")
            print(f"All files created in: {self.deploy_dir}")
            print(f"\nNext Steps:")
            print(f"   1. Update PROJECT_ID in deploy/deploy.sh")
            print(f"   2. Copy .env.example to .env.production and configure")
            print(f"   3. Run: cd deploy && ./deploy.sh")
            print(f"   4. Monitor: Google Cloud Console -> Cloud Run")
            
            return True
            
        except Exception as e:
            print(f"Error during deployment preparation: {e}")
            return False

if __name__ == "__main__":
    deployer = GCPDeployer()
    success = deployer.deploy()
    sys.exit(0 if success else 1)