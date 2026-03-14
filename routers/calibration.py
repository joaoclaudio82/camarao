"""router: calibração de escala"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from services.calibration_service import (
    calibrate_with_reference, calibrate_manual, COIN_DIAMETERS_MM
)

router = APIRouter()

@router.get("/references")
async def list_references():
    """Lista os tipos de referência disponíveis."""
    return {
        "references": [
            {"key": k, "label": k, "mm": v}
            for k, v in COIN_DIAMETERS_MM.items()
        ]
    }

@router.post("/auto")
async def calibrate_auto(
    file: UploadFile = File(...),
    reference_type: str = Query("R$0,25", description="Tipo de referência (moeda/régua)"),
    custom_mm: Optional[float] = Query(None, description="Tamanho real em mm (apenas para 'custom')"),
):
    """Detecta automaticamente um círculo ou linha na imagem e calcula px/cm."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Envie um arquivo de imagem.")
    data = await file.read()
    result = calibrate_with_reference(data, reference_type, custom_mm)
    return JSONResponse(result)

@router.post("/manual")
async def calibrate_manual_endpoint(
    file: UploadFile = File(...),
    x1: int = Query(..., description="X do ponto 1"),
    y1: int = Query(..., description="Y do ponto 1"),
    x2: int = Query(..., description="X do ponto 2"),
    y2: int = Query(..., description="Y do ponto 2"),
    known_cm: float = Query(..., description="Distância real em cm"),
):
    """Calibração manual: dois pontos + distância real."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Envie um arquivo de imagem.")
    data = await file.read()
    result = calibrate_manual(data, (x1, y1), (x2, y2), known_cm)
    return JSONResponse(result)
