"""router: geração de laudos PDF"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from services.db_service import get_full_result
from services.pdf_service import generate_pdf
import datetime

router = APIRouter()

@router.get("/analysis/{analysis_id}")
async def pdf_from_history(analysis_id: int):
    """Gera PDF de uma análise salva no histórico."""
    result = get_full_result(analysis_id)
    if result is None:
        raise HTTPException(404, "Análise não encontrada.")
    try:
        pdf_bytes = generate_pdf(result)
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar PDF: {str(e)}")
    filename = f"shrimpscan_{result.get('module','analysis')}_{analysis_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.post("/generate")
async def pdf_from_payload(result: dict):
    """Gera PDF a partir de um payload JSON de resultado (sem salvar)."""
    if "module" not in result:
        raise HTTPException(400, "Campo 'module' obrigatório.")
    try:
        pdf_bytes = generate_pdf(result)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar PDF: {str(e)}")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"shrimpscan_{result.get('module','report')}_{ts}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
