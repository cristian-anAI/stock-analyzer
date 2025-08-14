"""
Reports API endpoints
Generate Excel reports for trading analysis
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import logging
from ..services.excel_reports_service import excel_reports_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/reports/generate")
async def generate_excel_reports(background_tasks: BackgroundTasks):
    """Generate all Excel reports in background"""
    try:
        # Run report generation in background
        background_tasks.add_task(excel_reports_service.generate_all_reports)
        
        return {
            "message": "Excel reports generation started",
            "status": "processing",
            "reports": [
                "Trading_History_YYYYMMDD_HHMM.xlsx",
                "Current_Positions_YYYYMMDD_HHMM.xlsx", 
                "Buy_Signals_YYYYMMDD_HHMM.xlsx",
                "Portfolio_Summary_YYYYMMDD_HHMM.xlsx"
            ],
            "output_directory": str(excel_reports_service.output_dir)
        }
        
    except Exception as e:
        logger.error(f"Error starting Excel reports generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating reports: {str(e)}")

@router.get("/reports/status")
async def get_reports_status():
    """Get status of available reports"""
    try:
        reports_dir = excel_reports_service.output_dir
        
        if not reports_dir.exists():
            return {"available_reports": [], "total_reports": 0}
        
        excel_files = list(reports_dir.glob("*.xlsx"))
        
        reports_info = []
        for file_path in excel_files:
            stat = file_path.stat()
            reports_info.append({
                "filename": file_path.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": stat.st_mtime,
                "full_path": str(file_path)
            })
        
        # Sort by creation time (newest first)
        reports_info.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "available_reports": reports_info,
            "total_reports": len(reports_info),
            "output_directory": str(reports_dir)
        }
        
    except Exception as e:
        logger.error(f"Error getting reports status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting reports status: {str(e)}")

@router.delete("/reports/cleanup")
async def cleanup_old_reports(days_to_keep: int = 7):
    """Cleanup old Excel reports"""
    try:
        excel_reports_service.cleanup_old_reports(days_to_keep)
        
        return {
            "message": f"Cleaned up reports older than {days_to_keep} days",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up reports: {str(e)}")

@router.post("/reports/generate-sync")
async def generate_excel_reports_sync():
    """Generate all Excel reports synchronously (for testing)"""
    try:
        success = excel_reports_service.generate_all_reports()
        
        if success:
            return {
                "message": "Excel reports generated successfully",
                "status": "completed",
                "output_directory": str(excel_reports_service.output_dir)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate reports")
        
    except Exception as e:
        logger.error(f"Error generating Excel reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating reports: {str(e)}")