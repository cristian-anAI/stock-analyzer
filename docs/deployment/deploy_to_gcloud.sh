#!/bin/bash

# Stock Analyzer - Google Cloud Deployment Script
# This script prepares and deploys the application to Google Cloud

set -e  # Exit on any error

echo "🚀 STOCK ANALYZER - GOOGLE CLOUD DEPLOYMENT"
echo "=============================================="

# Configuration
PROJECT_ID="your-gcloud-project-id"  # UPDATE THIS
REGION="us-central1"
SERVICE_NAME="stock-analyzer-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "📋 Configuration:"
echo "   Project ID: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo "   Service: ${SERVICE_NAME}"
echo "   Image: ${IMAGE_NAME}"
echo ""

# Step 1: Check prerequisites
echo "🔍 Checking prerequisites..."
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Step 2: Authenticate and set project
echo "🔐 Setting up Google Cloud authentication..."
gcloud auth configure-docker
gcloud config set project ${PROJECT_ID}
echo "✅ Authentication configured"
echo ""

# Step 3: Clean up project
echo "🧹 Cleaning up project for production..."
if [ -f "cleanup_for_production.py" ]; then
    python cleanup_for_production.py
else
    echo "⚠️  cleanup_for_production.py not found, skipping cleanup"
fi
echo ""

# Step 4: Reset database for production
echo "🗄️  Preparing production database..."
read -p "⚠️  This will reset ALL data (positions, transactions). Continue? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "reset_production_database.py" ]; then
        echo "RESET_PRODUCTION" | python reset_production_database.py
        echo "✅ Database reset complete"
    else
        echo "⚠️  reset_production_database.py not found, creating fresh database on deployment"
    fi
else
    echo "❌ Database reset cancelled. Deployment aborted."
    exit 1
fi
echo ""

# Step 5: Build Docker image
echo "🐋 Building Docker image..."
docker build -t ${IMAGE_NAME}:latest .
echo "✅ Docker image built successfully"
echo ""

# Step 6: Push to Google Container Registry
echo "📤 Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}:latest
echo "✅ Image pushed successfully"
echo ""

# Step 7: Deploy to Cloud Run
echo "☁️  Deploying to Google Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --port 8000 \
    --set-env-vars="ENVIRONMENT=production,AUTOTRADER_ENABLED=true,STOCKS_CAPITAL=10000,CRYPTO_CAPITAL=50000"

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=============================================="

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')
echo "🌐 Service URL: ${SERVICE_URL}"
echo ""

echo "📊 API Endpoints:"
echo "   Health Check: ${SERVICE_URL}/health"
echo "   API Docs: ${SERVICE_URL}/docs"
echo "   Autotrader Positions: ${SERVICE_URL}/api/v1/positions/autotrader"
echo "   Manual Positions: ${SERVICE_URL}/api/v1/positions/manual"
echo ""

echo "🎯 What happens next:"
echo "   1. The autotrader will start automatically"
echo "   2. It begins with \$10k stocks + \$50k crypto capital"
echo "   3. Market data will be populated within 5 minutes"
echo "   4. First trades will execute based on scoring"
echo ""

echo "🔍 Monitor logs with:"
echo "   gcloud logs tail --follow --project=${PROJECT_ID} --resource=cloud_run_revision --resource-labels=service_name=${SERVICE_NAME}"
echo ""

echo "✅ Deployment successful! 🎉"