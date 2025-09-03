# Stock Analyzer - Google Cloud Deployment

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

3. **Clean Database (ONLY for production):**
   ```bash
   python deploy/clean_production_db.py
   ```

4. **Deploy:**
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
