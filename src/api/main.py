"""
FastAPI backend for Stock Analyzer application
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import List, Optional, Dict, Any
import uvicorn

from .routers import stocks, cryptos, positions, cache, scheduler, diagnostics, portfolio, reports, short_monitoring, symbol_search, market_status, position_monitoring, mtss_analysis, unified_scoring, mtss_bulk_scores, strategy_config
from .database.database import init_db
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.logging_middleware import LoggingMiddleware

# Configure logging
import os
log_handlers = [logging.StreamHandler()]
if os.path.exists('logs') or os.makedirs('logs', exist_ok=True):
    try:
        log_handlers.append(logging.FileHandler('logs/api.log'))
    except:
        pass  # Skip file logging if directory creation fails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Stock Analyzer API",
    description="Complete backend for stock analysis and automated trading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration based on environment
environment = os.getenv("ENVIRONMENT", "development").lower()

if environment == "production":
    # Production CORS - specific domains only
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        # Add your production domain here when deployed
        # "https://your-production-domain.com"
    ]
else:
    # Development CORS - allow all origins
    allowed_origins = ["*"]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add custom middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(stocks.router, prefix="/api/v1", tags=["stocks"])
app.include_router(cryptos.router, prefix="/api/v1", tags=["cryptos"])
app.include_router(positions.router, prefix="/api/v1", tags=["positions"])
app.include_router(cache.router, prefix="/api/v1", tags=["cache"])
app.include_router(scheduler.router, prefix="/api/v1", tags=["scheduler"])
app.include_router(diagnostics.router, prefix="/api/v1", tags=["diagnostics"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["portfolio"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(short_monitoring.router, prefix="/api/v1", tags=["short-monitoring"])
app.include_router(symbol_search.router, prefix="/api/v1", tags=["symbol-search"])
app.include_router(market_status.router, prefix="/api/v1", tags=["market-status"])
app.include_router(position_monitoring.router)
app.include_router(mtss_analysis.router, tags=["mtss-analysis"])
app.include_router(unified_scoring.router, tags=["unified-scoring"])
app.include_router(mtss_bulk_scores.router, tags=["mtss-bulk-scores"])
app.include_router(strategy_config.router, tags=["strategy-config"])

@app.on_event("startup")
async def startup_event():
    """Initialize database and start background scheduler on startup"""
    logger.info("Starting Stock Analyzer API...")
    init_db()
    logger.info("Database initialized successfully")
    
    # Auto-start background scheduler
    try:
        from .services.background_scheduler import background_scheduler
        await background_scheduler.start()
        logger.info("Background autotrader scheduler started automatically")
    except Exception as e:
        logger.error(f"Failed to start background scheduler: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Stock Analyzer API...")
    try:
        from .services.background_scheduler import background_scheduler
        await background_scheduler.stop()
        logger.info("Background scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping background scheduler: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Stock Analyzer API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "stock-analyzer-api"}

@app.get("/api/v1/health")
async def health_check_v1():
    """Health check endpoint - v1 alias for frontend compatibility"""
    return {"status": "healthy", "service": "stock-analyzer-api"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )