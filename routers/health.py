"""router: saúde"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from services.vision_service import analyze_health
from services.db_service import save_analysis, get_history

router = APIRouter()

@router.post("/analyze")
async def health_analyze(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Envie um arquivo de imagem.")
    data = await file.read()
    result = analyze_health(data, file.filename)
    save_analysis("health", file.filename, result)
    return JSONResponse(result)

@router.get("/history")
async def health_history(limit: int = 20):
    return get_history(limit, "health")
