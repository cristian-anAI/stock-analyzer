"""
PupupuV3 Standalone API Server
Run only PupupuV3 endpoints for debugging + Telegram bot
"""
import uvicorn
import threading
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create minimal FastAPI app with only PupupuV3 routes
app = FastAPI(
    title="PupupuV3 API",
    description="Trading strategy API for PupupuV3",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import only PupupuV3 router
from src.api.routers import pupupuv3

# Register routes - el router ya tiene el prefix en su definición
app.include_router(pupupuv3.router, tags=["PupupuV3"])

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "PupupuV3 API",
        "version": "3.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/api/v1/pupupuv3/status",
            "current_analysis": "/api/v1/pupupuv3/current-analysis",
            "recent_signals": "/api/v1/pupupuv3/signals/recent",
            "pending_trades": "/api/v1/pupupuv3/trades/pending",
            "active_trades": "/api/v1/pupupuv3/trades/active",
            "config": "/api/v1/pupupuv3/config",
            "debug_filters": "/api/v1/pupupuv3/debug-filters",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pupupuv3"}


def run_telegram_bot():
    """Run PupupuV3 Telegram bot in background thread"""
    try:
        print("\n[Telegram Bot] Starting PupupuV3 Telegram Bot...")
        import sys
        sys.path.insert(0, 'c:/repos/stock-analyzer')

        from pupupuv3_bot import PupupuV3Bot

        # Create bot instance
        bot = PupupuV3Bot(
            symbol='BTC/USDT',
            capital=30000
        )

        # Run in continuous monitor mode
        print("[Telegram Bot] Running in continuous monitor mode (60s interval)")
        bot.run_continuous_monitor(check_interval=60)

    except KeyboardInterrupt:
        print("\n[Telegram Bot] Shutting down...")
        bot.close()
    except Exception as e:
        print(f"[Telegram Bot] ERROR: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("startup")
async def startup_event():
    """Start background services on API startup"""
    print("\n[Startup] Initializing background services...")

    # Start Telegram bot in background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("[Startup] Telegram bot thread started")


if __name__ == "__main__":
    print("=" * 80)
    print("Starting PupupuV3 Standalone API Server + Telegram Bot")
    print("=" * 80)
    print("\nEndpoints available:")
    print("  - http://localhost:8001/")
    print("  - http://localhost:8001/health")
    print("  - http://localhost:8001/api/v1/pupupuv3/status")
    print("  - http://localhost:8001/api/v1/pupupuv3/current-analysis")
    print("  - http://localhost:8001/api/v1/pupupuv3/signals/recent")
    print("  - http://localhost:8001/api/v1/pupupuv3/trades/pending [NEW - Limit orders waiting]")
    print("  - http://localhost:8001/api/v1/pupupuv3/trades/active")
    print("  - http://localhost:8001/api/v1/pupupuv3/config")
    print("  - http://localhost:8001/api/v1/pupupuv3/debug-filters")
    print("  - http://localhost:8001/docs (Swagger UI)")
    print("\nBackground services:")
    print("  - Telegram Bot (signal monitoring + notifications, 60s interval)")
    print("\n" + "=" * 80)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # Different port from main API (8000)
        log_level="info"
    )
