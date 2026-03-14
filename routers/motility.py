"""router: motilidade"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from services.video_service import analyze_video
from services.db_service import save_analysis, get_history

router = APIRouter()

ALLOWED_VIDEO = {"video/mp4","video/mpeg","video/x-msvideo","video/quicktime",
                 "video/x-matroska","video/webm","application/octet-stream"}

@router.post("/analyze")
async def motility_analyze(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_VIDEO:
        raise HTTPException(400, f"Formato de vídeo não suportado: {file.content_type}")
    data = await file.read()
    result = analyze_video(data, file.filename)
    if "error" not in result:
        save_analysis("motility", file.filename, result)
    return JSONResponse(result)

@router.get("/history")
async def motility_history(limit: int = 20):
    return get_history(limit, "motility")
