"""router: dashboard"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from services.db_service import get_stats, get_history, delete_analysis, export_csv

router = APIRouter()

@router.get("/stats")
async def dashboard_stats():
    return JSONResponse(get_stats())

@router.get("/history")
async def dashboard_history(limit: int = 50, type: str = None):
    return JSONResponse(get_history(limit, type))

@router.delete("/analysis/{analysis_id}")
async def delete_entry(analysis_id: int):
    ok = delete_analysis(analysis_id)
    if not ok:
        raise HTTPException(404, "Análise não encontrada.")
    return {"deleted": True, "id": analysis_id}

@router.get("/export/csv")
async def export_to_csv():
    csv_data = export_csv()
    return PlainTextResponse(csv_data, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shrimpscan_export.csv"})
