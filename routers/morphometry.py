"""router: morfometria"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from services.vision_service import analyze_morphometry, analyze_larvae
from services.db_service import save_analysis, get_history

router = APIRouter()

@router.post("/analyze")
async def morphometry_analyze(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Envie um arquivo de imagem.")
    data = await file.read()
    result = analyze_morphometry(data, file.filename)
    save_analysis("morphometry", file.filename, result)
    return JSONResponse(result)

@router.post("/larvae")
async def larvae_analyze(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Envie um arquivo de imagem.")
    data = await file.read()
    result = analyze_larvae(data, file.filename)
    save_analysis("larvae", file.filename, result)
    return JSONResponse(result)

@router.get("/history")
async def morphometry_history(limit: int = 20):
    return get_history(limit, "morphometry")
