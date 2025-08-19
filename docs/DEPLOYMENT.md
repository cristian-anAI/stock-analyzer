# Stock Analyzer - Production Deployment Guide

## 🚀 Google Cloud Deployment

### Prerequisites

1. **Google Cloud SDK** installed and configured
2. **Docker** installed and running
3. **Google Cloud Project** with billing enabled
4. **Required APIs** enabled:
   - Cloud Run API
   - Container Registry API

### Quick Deployment

1. **Update Configuration**
   ```bash
   # Edit deploy_to_gcloud.sh
   PROJECT_ID="your-actual-project-id"  # Change this line
   ```

2. **Run Deployment Script**
   ```bash
   chmod +x deploy_to_gcloud.sh
   ./deploy_to_gcloud.sh
   ```

3. **Monitor Deployment**
   ```bash
   gcloud logs tail --follow --project=your-project-id --resource=cloud_run_revision
   ```

### Manual Deployment Steps

If you prefer manual deployment:

#### 1. Clean Project
```bash
python cleanup_for_production.py
```

#### 2. Reset Database
```bash
echo "RESET_PRODUCTION" | python reset_production_database.py
```

#### 3. Build & Deploy
```bash
# Build image
docker build -t gcr.io/your-project-id/stock-analyzer-api .

# Push to registry
docker push gcr.io/your-project-id/stock-analyzer-api

# Deploy to Cloud Run
gcloud run deploy stock-analyzer-api \
    --image gcr.io/your-project-id/stock-analyzer-api \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --port 8000
```

## 🏗️ Architecture

### Production Setup
- **Platform**: Google Cloud Run
- **Database**: SQLite (ephemeral, resets on redeploy)
- **Memory**: 1GB allocated
- **CPU**: 1 vCPU
- **Auto-scaling**: 0-10 instances
- **Port**: 8000

### Key Features
- ✅ **Autotrader**: Runs automatically in background
- ✅ **SHORT Positions**: Full support for crypto/stock shorts
- ✅ **Portfolio Management**: $10k stocks + $50k crypto capital
- ✅ **Real-time Data**: Yahoo Finance integration
- ✅ **Health Monitoring**: Built-in health checks
- ✅ **REST API**: Complete FastAPI interface

## 📊 Monitoring & Management

### API Endpoints
```
GET  /health                           # Service health
GET  /docs                            # API documentation
GET  /api/v1/positions/autotrader     # Autotrader positions
GET  /api/v1/positions/manual         # Manual positions
POST /api/v1/positions/refresh        # Force price refresh
GET  /api/v1/autotrader/summary       # Trading performance
```

### Logs
```bash
# View real-time logs
gcloud logs tail --follow --project=your-project-id \
    --resource=cloud_run_revision \
    --resource-labels=service_name=stock-analyzer-api

# Search specific logs
gcloud logs read --project=your-project-id \
    --filter="resource.type=cloud_run_revision AND textPayload:ERROR"
```

## 🔧 Configuration

### Environment Variables
- `ENVIRONMENT=production`
- `AUTOTRADER_ENABLED=true`
- `STOCKS_CAPITAL=10000`
- `CRYPTO_CAPITAL=50000`
- `LOG_LEVEL=INFO`

### Database Persistence
⚠️ **Important**: Cloud Run uses ephemeral storage. The database resets on each deployment.

For persistent data, consider:
- Google Cloud SQL
- Cloud Firestore
- External database service

## 🛠️ Development vs Production

### Files Excluded from Production
- `reports/` - Excel reports (200+ files)
- `logs/` - Local log files
- `backups/` - Database backups
- `legacy/` - Old scripts
- `scripts/testing/` - Test scripts
- `*.db`, `*.backup` - Local databases
- `__pycache__/` - Python cache

### Production Optimizations
- Multi-stage Docker build
- Health checks enabled
- Resource limits set
- Logging configured
- Auto-scaling enabled

## 🔒 Security

### Best Practices Implemented
- Non-root container user
- Minimal base image (Python slim)
- No hardcoded secrets
- Health check endpoints
- Resource constraints

### Access Control
- Service runs with `--allow-unauthenticated` for public API
- For private use, remove this flag and configure IAM

## 📈 Scaling

### Current Limits
- **Memory**: 1GB (sufficient for current workload)
- **CPU**: 1 vCPU (handles API + background tasks)
- **Instances**: 0-10 (auto-scales based on traffic)
- **Timeout**: 300 seconds (5 minutes max request time)

### Performance Monitoring
- Monitor response times in Cloud Console
- Watch memory usage patterns
- Scale up if needed for high-frequency trading

## 🆘 Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   gcloud logs read --project=your-project-id --limit=50
   ```

2. **Database errors**
   ```bash
   # Database resets on deployment - this is normal
   # Check if migrations are running properly
   ```

3. **API timeouts**
   ```bash
   # Increase timeout or optimize slow endpoints
   gcloud run services update stock-analyzer-api --timeout=600
   ```

4. **Memory issues**
   ```bash
   # Increase memory allocation
   gcloud run services update stock-analyzer-api --memory=2Gi
   ```

### Emergency Reset
```bash
# Redeploy with fresh database
./deploy_to_gcloud.sh
```

## 📞 Support

- Check logs first: `gcloud logs tail --follow`
- Monitor Cloud Run metrics in Google Cloud Console
- Review API health: `https://your-service-url/health`
- Test autotrader: `https://your-service-url/api/v1/autotrader/summary`